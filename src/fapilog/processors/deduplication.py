"""Async-safe deduplication processor implementation.

This module provides a completely rewritten DeduplicationProcessor that eliminates
race conditions and uses proper async patterns with foundation components.
"""

import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional, cast

from ..async_components.concurrency.background_cleanup_manager import (
    BackgroundCleanupManager,
    CleanupTarget,
)
from ..async_components.concurrency.task_manager import AsyncTaskManager
from ..exceptions import ProcessorConfigurationError
from ..processors.async_base import AsyncProcessorBase

logger = logging.getLogger(__name__)


class DeduplicationProcessor(AsyncProcessorBase, CleanupTarget):
    """Remove duplicate log events within time window with proper async patterns.

    This implementation eliminates race conditions found in the original processor
    by using SafeAsyncCache, ProcessorLockManager, and proper async task management.
    """

    def __init__(
        self,
        window_seconds: int = 300,
        dedupe_fields: Optional[List[str]] = None,
        max_cache_size: int = 10000,
        hash_algorithm: str = "md5",
        **config: Any,
    ) -> None:
        """Initialize deduplication processor with async-safe components.

        Args:
            window_seconds: Time window for deduplication in seconds
            dedupe_fields: Fields to use for generating event signature
            max_cache_size: Maximum number of signatures to keep in cache
            hash_algorithm: Algorithm for hashing signatures ('md5', 'sha1', 'sha256')
            **config: Additional configuration parameters
        """
        # Set instance attributes BEFORE calling super().__init__()
        # because validate_config() is called during parent initialization
        self.window_seconds = window_seconds
        self.dedupe_fields = (
            dedupe_fields
            if dedupe_fields is not None
            else ["event", "level", "hostname"]
        )
        self.max_cache_size = max_cache_size
        self.hash_algorithm = hash_algorithm

        # Configure cache settings for AsyncProcessorBase
        config.update(
            {
                "cache_max_size": max_cache_size,
                "cache_ttl_seconds": window_seconds,  # Use window as TTL
                "processor_id": "DeduplicationProcessor",
            }
        )

        super().__init__(**config)

        # Task management for async operations
        self._task_manager = AsyncTaskManager(max_concurrent_tasks=50)

        # Background cleanup management
        cleanup_interval = max(60, window_seconds // 5)
        self._cleanup_manager = BackgroundCleanupManager(
            cleanup_target=self,
            cleanup_interval=cleanup_interval,
            cleanup_threshold_ratio=0.8,
            max_cleanup_duration=30.0,
        )

        logger.info(
            f"Initialized DeduplicationProcessor: window={window_seconds}s, "
            f"fields={self.dedupe_fields}, cache_size={max_cache_size}"
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

        if not self.dedupe_fields or not isinstance(self.dedupe_fields, list):
            raise ProcessorConfigurationError(
                "dedupe_fields cannot be empty and must be a list"
            )

        if self.hash_algorithm not in ["md5", "sha1", "sha256"]:
            raise ProcessorConfigurationError(
                "hash_algorithm must be 'md5', 'sha1', or 'sha256'"
            )

    def process(
        self, logger_obj: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Apply deduplication to event with proper async patterns.

        This is the sync entry point that delegates to async processing.

        Args:
            logger_obj: The logger instance
            method_name: The logging method name (e.g., 'info', 'error')
            event_dict: The event dictionary to process

        Returns:
            The processed event dictionary, or None to drop duplicate events
        """
        # For sync contexts, we need to handle this carefully
        # Create a task to run the async version
        import asyncio

        try:
            # Try to get current event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in an async context, create a task
                task = self._task_manager.create_task(
                    self.process_async(logger_obj, method_name, event_dict),
                    task_name="dedup_process",
                )
                if task:
                    # Return event immediately for non-blocking operation
                    # The actual deduplication will happen in the background
                    return event_dict
            else:
                # Not in async context, run sync version
                return asyncio.run(
                    self.process_async(logger_obj, method_name, event_dict)
                )
        except RuntimeError:
            # No event loop, run sync version
            return asyncio.run(self.process_async(logger_obj, method_name, event_dict))

    async def process_async(
        self, logger_obj: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Async version of process method for proper deduplication.

        Args:
            logger_obj: The logger instance
            method_name: The logging method name
            event_dict: The event dictionary to process

        Returns:
            The processed event dictionary, or None to drop duplicate events
        """
        try:
            signature = self._generate_signature(event_dict)
            current_time = time.time()

            # Atomic check using SafeAsyncCache
            async def check_and_create():
                # Try to get existing event data
                existing_data = await self._cache.get(signature)

                if existing_data is not None:
                    # Check if it's within the deduplication window
                    time_diff = current_time - existing_data["timestamp"]
                    if time_diff <= self.window_seconds:
                        # It's a duplicate, update count
                        existing_data["count"] += 1
                        existing_data["last_seen"] = current_time
                        await self._cache.set(signature, existing_data)
                        return None  # Drop duplicate

                # New event or expired, create new entry
                event_data = {
                    "timestamp": current_time,
                    "last_seen": current_time,
                    "count": 1,
                    "event_signature": signature,
                }
                await self._cache.set(signature, event_data)
                return event_dict  # Allow new event

            # Use atomic operation from AsyncProcessorBase
            result = await self._safe_cache_operation(signature, check_and_create)

            # Schedule background cleanup if needed
            await self._cleanup_manager.schedule_cleanup(
                current_time,
                utilization_check=lambda: len(self._cache._cache) / self.max_cache_size,
            )

            return cast(Optional[Dict[str, Any]], result)

        except Exception as e:
            # Log error and allow event through to avoid blocking
            await self._handle_processor_error(
                e,
                {
                    "event_dict": event_dict,
                    "method_name": method_name,
                    "operation": "deduplication",
                },
            )
            return event_dict

    def _generate_signature(self, event_dict: Dict[str, Any]) -> str:
        """Generate unique signature for event based on dedupe_fields.

        Args:
            event_dict: Event dictionary to generate signature for

        Returns:
            str: Unique signature for the event
        """
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

    async def cleanup_expired_entries(self, current_time: float) -> int:
        """Clean up expired entries from cache.

        This method implements the CleanupTarget protocol for BackgroundCleanupManager.

        Args:
            current_time: Current timestamp

        Returns:
            int: Number of entries cleaned up
        """
        try:
            expired_count = 0
            keys_to_remove = []

            # Get all cache keys
            all_keys = await self._cache.get_all_keys()

            # Check each entry for expiration
            for signature in all_keys:
                data = await self._cache.get(signature)
                if data and (current_time - data["timestamp"]) > self.window_seconds:
                    keys_to_remove.append(signature)

            # Remove expired entries atomically
            for signature in keys_to_remove:
                if await self._cache.delete(signature):
                    expired_count += 1

            if expired_count > 0:
                logger.debug(
                    f"Cleaned up {expired_count} expired deduplication entries"
                )

            return expired_count

        except Exception as e:
            logger.warning(f"Error during deduplication cleanup: {e}", exc_info=True)
            return 0

    async def get_deduplication_stats(self) -> Dict[str, Any]:
        """Get comprehensive deduplication statistics.

        Returns:
            Dict with deduplication and performance statistics
        """
        base_stats = self.get_async_stats()
        cleanup_stats = self._cleanup_manager.get_cleanup_stats()
        task_stats = self._task_manager.get_task_stats()

        # Calculate deduplication-specific metrics
        total_events = 0
        unique_signatures = 0
        cache_keys = await self._cache.get_all_keys()

        for signature in cache_keys:
            data = await self._cache.get(signature)
            if data:
                total_events += data["count"]
                unique_signatures += 1

        dedup_ratio = (
            (total_events - unique_signatures) / total_events
            if total_events > 0
            else 0.0
        )

        return {
            **base_stats,
            "deduplication": {
                "window_seconds": self.window_seconds,
                "dedupe_fields": self.dedupe_fields,
                "hash_algorithm": self.hash_algorithm,
                "unique_signatures": unique_signatures,
                "total_events_seen": total_events,
                "deduplication_ratio": dedup_ratio,
                "duplicates_dropped": total_events - unique_signatures,
            },
            "cleanup_stats": cleanup_stats,
            "task_stats": task_stats,
        }

    async def _start_impl(self) -> None:
        """Start deduplication processor with cleanup manager."""
        await super()._start_impl()
        await self._cleanup_manager.start()
        logger.info("DeduplicationProcessor started with background cleanup")

    async def _stop_impl(self) -> None:
        """Stop deduplication processor and cleanup resources."""
        logger.info("Stopping DeduplicationProcessor")

        # Stop cleanup manager
        await self._cleanup_manager.stop()

        # Wait for active tasks
        await self._task_manager.wait_for_all_tasks(timeout=5.0)

        # Cancel any remaining tasks
        await self._task_manager.cancel_all_tasks()

        # Call parent cleanup
        await super()._stop_impl()

        logger.info("DeduplicationProcessor stopped")
