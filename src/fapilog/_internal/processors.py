"""Concrete processor implementations for fapilog structured logging."""

import asyncio
import hashlib
import json
import random
import re
import threading
import time
from typing import Any, Dict, List, Optional

from ..exceptions import ProcessorConfigurationError
from ..redactors import _should_redact_at_level
from .processor import Processor
from .processor_registry import ProcessorRegistry


class RedactionProcessor(Processor):
    """Processor that redacts values matching regex patterns."""

    def __init__(
        self,
        patterns: Optional[List[str]] = None,
        redact_level: str = "INFO",
        **config: Any,
    ) -> None:
        """Initialize redaction processor.

        Args:
            patterns: List of regex patterns to match for redaction
            redact_level: Minimum log level for redaction to be applied
            **config: Additional configuration parameters
        """
        self.patterns = patterns or []
        self.redact_level = redact_level
        self.compiled_patterns: List[re.Pattern[str]] = []
        super().__init__(patterns=patterns, redact_level=redact_level, **config)

    async def _start_impl(self) -> None:
        """Initialize compiled regex patterns."""
        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.patterns
        ]

    def validate_config(self) -> None:
        """Validate configuration parameters."""
        if not isinstance(self.patterns, list):
            raise ValueError("patterns must be a list of strings")

        for pattern in self.patterns:
            if not isinstance(pattern, str):
                raise ValueError("All patterns must be strings")
            try:
                re.compile(pattern)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern '{pattern}': {e}") from e

        if not isinstance(self.redact_level, str):
            raise ValueError("redact_level must be a string")

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Redact sensitive information from log entries."""
        # Check if redaction should be applied based on log level
        event_level = event_dict.get("level", "INFO")
        if not _should_redact_at_level(event_level, self.redact_level):
            return event_dict

        if not self.compiled_patterns:
            return event_dict

        return self._redact_recursive(event_dict)

    def _redact_recursive(self, data: Any) -> Any:
        """Recursively redact values in nested structures."""
        if isinstance(data, dict):
            redacted_dict = data.copy()
            for key, value in data.items():
                if isinstance(value, str):
                    for pattern in self.compiled_patterns:
                        if pattern.search(key) or pattern.search(value):
                            redacted_dict[key] = "[REDACTED]"
                            break
                elif isinstance(value, dict):
                    redacted_dict[key] = self._redact_recursive(value)
            return redacted_dict
        return data


class SamplingProcessor(Processor):
    """Processor that drops events probabilistically for sampling."""

    def __init__(self, rate: float = 1.0, **config: Any) -> None:
        """Initialize sampling processor.

        Args:
            rate: Sampling rate between 0.0 and 1.0
            **config: Additional configuration parameters
        """
        self.rate = rate
        super().__init__(rate=rate, **config)

    def validate_config(self) -> None:
        """Validate configuration parameters."""
        if not isinstance(self.rate, (int, float)):
            raise ValueError("rate must be a number")

        if not 0.0 <= self.rate <= 1.0:
            raise ValueError("rate must be between 0.0 and 1.0")

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Sample log events based on the configured rate."""
        if self.rate >= 1.0:
            return event_dict

        if random.random() >= self.rate:
            return None  # Drop this event
        return event_dict


class FilterNoneProcessor(Processor):
    """Processor that filters out None events."""

    def __init__(self, **config: Any) -> None:
        """Initialize filter processor.

        Args:
            **config: Configuration parameters (not used by this processor)
        """
        super().__init__(**config)

    def process(
        self, logger: Any, method_name: str, event_dict: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Filter out None events."""
        if event_dict is None:
            return None
        return event_dict


class ThrottleProcessor(Processor):
    """Rate-limit log events per source/key to prevent log flooding."""

    def __init__(
        self,
        max_rate: int = 100,
        window_seconds: int = 60,
        key_field: str = "source",
        strategy: str = "drop",
        cleanup_interval: int = 300,
        max_cache_size: int = 10000,
        **config: Any,
    ) -> None:
        """Initialize throttle processor.

        Args:
            max_rate: Maximum events per window per key
            window_seconds: Time window in seconds for rate limiting
            key_field: Field to use as throttling key
            strategy: Throttling strategy ('drop', 'sample')
            cleanup_interval: Background cleanup interval in seconds
            max_cache_size: Maximum number of keys to track
            **config: Additional configuration parameters
        """
        self.max_rate = max_rate
        self.window_seconds = window_seconds
        self.key_field = key_field
        self.strategy = strategy
        self.cleanup_interval = cleanup_interval
        self.max_cache_size = max_cache_size
        self._rate_tracker: Dict[str, List[float]] = {}
        self._key_access_times: Dict[str, float] = {}  # For LRU tracking
        self._lock = threading.Lock()
        self._sample_rate = 0.1  # For sample strategy
        self._cleanup_task: Optional[asyncio.Task[None]] = None
        self._stopping = False
        super().__init__(
            max_rate=max_rate,
            window_seconds=window_seconds,
            key_field=key_field,
            strategy=strategy,
            cleanup_interval=cleanup_interval,
            max_cache_size=max_cache_size,
            **config,
        )

    def validate_config(self) -> None:
        """Validate throttle configuration."""
        if not isinstance(self.max_rate, int) or self.max_rate <= 0:
            raise ProcessorConfigurationError("max_rate must be a positive integer")

        if not isinstance(self.window_seconds, int) or self.window_seconds <= 0:
            raise ProcessorConfigurationError(
                "window_seconds must be a positive integer"
            )

        if not isinstance(self.key_field, str) or not self.key_field.strip():
            raise ProcessorConfigurationError("key_field must be a non-empty string")

        if self.strategy not in ["drop", "sample"]:
            raise ProcessorConfigurationError("strategy must be 'drop' or 'sample'")

        if not isinstance(self.cleanup_interval, int) or self.cleanup_interval <= 0:
            raise ProcessorConfigurationError(
                "cleanup_interval must be a positive integer"
            )

        if not isinstance(self.max_cache_size, int) or self.max_cache_size <= 0:
            raise ProcessorConfigurationError(
                "max_cache_size must be a positive integer"
            )

    async def _start_impl(self) -> None:
        """Start the background cleanup task."""
        self._stopping = False
        self._cleanup_task = asyncio.create_task(self._background_cleanup())

    async def _stop_impl(self) -> None:
        """Stop the background cleanup task."""
        self._stopping = True
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        self._cleanup_task = None

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Apply throttling rules to event."""
        key = self._extract_key(event_dict)
        current_time = time.time()

        with self._lock:
            if self._should_throttle(key, current_time):
                return self._apply_strategy(event_dict, key)
            else:
                self._record_event(key, current_time)
                return event_dict

    def _extract_key(self, event_dict: Dict[str, Any]) -> str:
        """Extract throttling key from event."""
        return str(event_dict.get(self.key_field, "default"))

    def _should_throttle(self, key: str, current_time: float) -> bool:
        """Check if event should be throttled."""
        if key not in self._rate_tracker:
            return False

        # Clean old entries first
        self._cleanup_old_entries_for_key(key, current_time)

        # Check if we're over the rate limit
        event_count = len(self._rate_tracker.get(key, []))
        return event_count >= self.max_rate

    def _apply_strategy(
        self, event_dict: Dict[str, Any], key: str
    ) -> Optional[Dict[str, Any]]:
        """Apply throttling strategy."""
        if self.strategy == "drop":
            return None
        elif self.strategy == "sample":
            # Return 1 in N events when throttling
            return event_dict if random.random() < self._sample_rate else None
        return event_dict

    def _record_event(self, key: str, timestamp: float) -> None:
        """Record event for rate tracking."""
        if key not in self._rate_tracker:
            self._rate_tracker[key] = []

        self._rate_tracker[key].append(timestamp)
        # Update LRU access time
        self._key_access_times[key] = timestamp

        # Keep only recent events to prevent memory growth
        self._cleanup_old_entries_for_key(key, timestamp)

        # Enforce memory limits synchronously
        if len(self._rate_tracker) > self.max_cache_size:
            self._enforce_memory_limits_sync()

    def _enforce_memory_limits_sync(self) -> None:
        """Synchronously enforce maximum cache size with LRU eviction."""
        if len(self._rate_tracker) <= self.max_cache_size:
            return

        # Calculate how many entries to remove (remove 10% when over limit)
        excess_count = len(self._rate_tracker) - self.max_cache_size
        remove_count = max(excess_count, len(self._rate_tracker) // 10)

        # Sort keys by access time (LRU first)
        sorted_keys = sorted(
            self._key_access_times.items(),
            key=lambda x: x[1],  # Sort by access time
        )

        # Remove oldest keys
        for i in range(min(remove_count, len(sorted_keys))):
            key_to_remove = sorted_keys[i][0]
            self._rate_tracker.pop(key_to_remove, None)
            self._key_access_times.pop(key_to_remove, None)

    def _cleanup_old_entries_for_key(self, key: str, current_time: float) -> None:
        """Clean up old entries for a specific key."""
        if key not in self._rate_tracker:
            return

        cutoff_time = current_time - self.window_seconds
        self._rate_tracker[key] = [
            ts for ts in self._rate_tracker[key] if ts >= cutoff_time
        ]

        # Remove empty key entries to prevent memory leaks
        if not self._rate_tracker[key]:
            del self._rate_tracker[key]
            # Also cleanup LRU tracking for removed keys
            self._key_access_times.pop(key, None)

    async def _cleanup_old_entries(self) -> None:
        """Background cleanup of old rate tracking entries.

        This method is designed to be called periodically by background
        tasks to prevent memory leaks from accumulated rate tracking data.
        """
        current_time = time.time()
        with self._lock:
            for key in list(self._rate_tracker.keys()):
                self._cleanup_old_entries_for_key(key, current_time)

    async def _background_cleanup(self) -> None:
        """Background task that periodically cleans up expired entries."""
        while not self._stopping:
            try:
                await asyncio.sleep(self.cleanup_interval)
                if not self._stopping:
                    await self._cleanup_old_entries()
                    await self._enforce_memory_limits()
            except asyncio.CancelledError:
                break
            except Exception:
                # Log error but continue cleanup task
                pass

    async def _enforce_memory_limits(self) -> None:
        """Enforce maximum cache size with LRU eviction (async version for background task)."""
        with self._lock:
            self._enforce_memory_limits_sync()

    def get_current_rates(self) -> Dict[str, int]:
        """Get current event rates for all tracked keys.

        Returns:
            Dictionary mapping keys to their current event counts
            within the time window.
        """
        current_time = time.time()
        rates = {}

        with self._lock:
            for key in list(self._rate_tracker.keys()):
                self._cleanup_old_entries_for_key(key, current_time)
                if key in self._rate_tracker:
                    rates[key] = len(self._rate_tracker[key])

        return rates

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics for monitoring.

        Returns:
            Dictionary with cache size, memory usage, and performance metrics
        """
        with self._lock:
            total_events = sum(len(events) for events in self._rate_tracker.values())
            return {
                "tracked_keys": len(self._rate_tracker),
                "total_events_tracked": total_events,
                "max_cache_size": self.max_cache_size,
                "cache_utilization": len(self._rate_tracker) / self.max_cache_size,
                "cleanup_interval": self.cleanup_interval,
                "window_seconds": self.window_seconds,
                "average_events_per_key": (
                    total_events / len(self._rate_tracker) if self._rate_tracker else 0
                ),
            }


class DeduplicationProcessor(Processor):
    """Remove duplicate log events within time window."""

    def __init__(
        self,
        window_seconds: int = 300,
        dedupe_fields: Optional[List[str]] = None,
        max_cache_size: int = 10000,
        hash_algorithm: str = "md5",
        **config: Any,
    ) -> None:
        """Initialize deduplication processor.

        Args:
            window_seconds: Time window for deduplication in seconds
            dedupe_fields: Fields to use for generating event signature
            max_cache_size: Maximum number of signatures to keep in cache
            hash_algorithm: Algorithm for hashing signatures ('md5', 'sha1', 'sha256')
            **config: Additional configuration parameters
        """
        self.window_seconds = window_seconds
        # Handle None vs empty list properly
        if dedupe_fields is None:
            self.dedupe_fields = ["event", "level", "hostname"]
        else:
            self.dedupe_fields = dedupe_fields
        self.max_cache_size = max_cache_size
        self.hash_algorithm = hash_algorithm
        self._event_cache: Dict[
            str, tuple[float, int]
        ] = {}  # signature -> (timestamp, count)
        self._lock = threading.Lock()
        super().__init__(
            window_seconds=window_seconds,
            dedupe_fields=dedupe_fields,
            max_cache_size=max_cache_size,
            hash_algorithm=hash_algorithm,
            **config,
        )

    def validate_config(self) -> None:
        """Validate deduplication configuration."""
        if not isinstance(self.window_seconds, int) or self.window_seconds <= 0:
            raise ProcessorConfigurationError(
                "window_seconds must be a positive integer"
            )

        if not isinstance(self.max_cache_size, int) or self.max_cache_size <= 0:
            raise ProcessorConfigurationError(
                "max_cache_size must be a positive integer"
            )

        # Check both None and empty list cases
        if not self.dedupe_fields:
            raise ProcessorConfigurationError(
                "dedupe_fields cannot be empty and must be a list"
            )

        if not isinstance(self.dedupe_fields, list):
            raise ProcessorConfigurationError(
                "dedupe_fields cannot be empty and must be a list"
            )

        if self.hash_algorithm not in ["md5", "sha1", "sha256"]:
            raise ProcessorConfigurationError(
                "hash_algorithm must be 'md5', 'sha1', or 'sha256'"
            )

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Apply deduplication to event."""
        signature = self._generate_signature(event_dict)
        current_time = time.time()

        with self._lock:
            if self._is_duplicate(signature, current_time):
                self._update_duplicate_count(signature, current_time)
                return None  # Drop duplicate
            else:
                self._record_new_event(signature, current_time)
                self._cleanup_expired_entries(current_time)
                return event_dict

    def _generate_signature(self, event_dict: Dict[str, Any]) -> str:
        """Generate unique signature for event based on dedupe_fields."""
        signature_data = {}
        for field in self.dedupe_fields:
            if field in event_dict:
                signature_data[field] = event_dict[field]

        # Create deterministic string representation
        signature_str = json.dumps(signature_data, sort_keys=True)

        # Hash for efficiency
        if self.hash_algorithm == "md5":
            return hashlib.md5(signature_str.encode()).hexdigest()
        elif self.hash_algorithm == "sha1":
            return hashlib.sha1(signature_str.encode()).hexdigest()
        else:  # sha256
            return hashlib.sha256(signature_str.encode()).hexdigest()

    def _is_duplicate(self, signature: str, current_time: float) -> bool:
        """Check if event is a duplicate within window."""
        if signature not in self._event_cache:
            return False

        last_seen, _ = self._event_cache[signature]
        return (current_time - last_seen) <= self.window_seconds

    def _update_duplicate_count(self, signature: str, current_time: float) -> None:
        """Update count for duplicate event."""
        if signature in self._event_cache:
            _, count = self._event_cache[signature]
            self._event_cache[signature] = (current_time, count + 1)

    def _record_new_event(self, signature: str, current_time: float) -> None:
        """Record new unique event."""
        self._event_cache[signature] = (current_time, 1)

        # Enforce cache size limit
        if len(self._event_cache) > self.max_cache_size:
            self._evict_oldest_entries()

    def _cleanup_expired_entries(self, current_time: float) -> None:
        """Remove expired entries from cache."""
        expired_keys = []
        for signature, (timestamp, _) in self._event_cache.items():
            if (current_time - timestamp) > self.window_seconds:
                expired_keys.append(signature)

        for key in expired_keys:
            del self._event_cache[key]

    def _evict_oldest_entries(self) -> None:
        """Evict oldest entries when cache is full."""
        # Remove 10% of oldest entries
        sorted_entries = sorted(
            self._event_cache.items(),
            key=lambda x: x[1][0],  # Sort by timestamp
        )

        evict_count = max(1, len(sorted_entries) // 10)
        for i in range(evict_count):
            signature, _ = sorted_entries[i]
            del self._event_cache[signature]

    @property
    def cache_stats(self) -> Dict[str, int]:
        """Get cache statistics for monitoring."""
        with self._lock:
            total_events = sum(count for _, count in self._event_cache.values())
            return {
                "unique_signatures": len(self._event_cache),
                "total_events_seen": total_events,
                "cache_size": len(self._event_cache),
                "max_cache_size": self.max_cache_size,
            }


# Register built-in processors in the ProcessorRegistry
ProcessorRegistry.register("redaction", RedactionProcessor)
ProcessorRegistry.register("sampling", SamplingProcessor)
ProcessorRegistry.register("filter_none", FilterNoneProcessor)
ProcessorRegistry.register("throttle", ThrottleProcessor)
ProcessorRegistry.register("deduplication", DeduplicationProcessor)
