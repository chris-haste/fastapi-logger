"""Concrete processor implementations for fapilog structured logging."""

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
        **config: Any,
    ) -> None:
        """Initialize throttle processor.

        Args:
            max_rate: Maximum events per window per key
            window_seconds: Time window in seconds for rate limiting
            key_field: Field to use as throttling key
            strategy: Throttling strategy ('drop', 'sample')
            **config: Additional configuration parameters
        """
        self.max_rate = max_rate
        self.window_seconds = window_seconds
        self.key_field = key_field
        self.strategy = strategy
        self._rate_tracker: Dict[str, List[float]] = {}
        self._lock = threading.Lock()
        self._sample_rate = 0.1  # For sample strategy
        super().__init__(
            max_rate=max_rate,
            window_seconds=window_seconds,
            key_field=key_field,
            strategy=strategy,
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

        # Keep only recent events to prevent memory growth
        self._cleanup_old_entries_for_key(key, timestamp)

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

    async def _cleanup_old_entries(self) -> None:
        """Background cleanup of old rate tracking entries.

        This method is designed to be called periodically by background
        tasks to prevent memory leaks from accumulated rate tracking data.
        """
        current_time = time.time()
        with self._lock:
            keys_to_remove = []
            for key in list(self._rate_tracker.keys()):
                self._cleanup_old_entries_for_key(key, current_time)
                if key not in self._rate_tracker:  # Was removed in cleanup
                    keys_to_remove.append(key)

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


# Register built-in processors in the ProcessorRegistry
ProcessorRegistry.register("redaction", RedactionProcessor)
ProcessorRegistry.register("sampling", SamplingProcessor)
ProcessorRegistry.register("filter_none", FilterNoneProcessor)
ProcessorRegistry.register("throttle", ThrottleProcessor)
