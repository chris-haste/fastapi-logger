"""Async-safe processor base class with foundation components.

This module provides a base class for processors that need async-safe
operations, using the ProcessorLockManager and SafeAsyncCache foundation
components.
"""

import asyncio
import logging
from abc import abstractmethod
from typing import Any, Awaitable, Callable, Dict, Optional

from ..async_components.cache.safe_async_cache import SafeAsyncCache
from ..async_components.concurrency.lock_manager import ProcessorLockManager
from ..processors.base import Processor

logger = logging.getLogger(__name__)


class AsyncProcessorBase(Processor):
    """Base class for processors with async-safe operations.

    Provides foundation components (lock manager and cache) to eliminate
    race conditions and ensure consistent async patterns across processors.
    """

    def __init__(
        self, lock_manager: Optional[ProcessorLockManager] = None, **config: Any
    ):
        """Initialize async processor with foundation components.

        Args:
            lock_manager: Optional ProcessorLockManager instance. If not provided,
                         will try to get from container in config, or create a new instance.
            **config: Configuration parameters for the processor
        """
        super().__init__(**config)

        # Get lock manager from parameter, container, or create new instance
        if lock_manager is not None:
            self._lock_manager = lock_manager
        elif "container" in config and hasattr(config["container"], "get_lock_manager"):
            self._lock_manager = config["container"].get_lock_manager()
        else:
            # Fallback: create a new instance for backward compatibility
            self._lock_manager = ProcessorLockManager()

        # Configure cache with processor-specific settings
        cache_max_size = config.get("cache_max_size", 1000)
        cache_ttl_seconds = config.get("cache_ttl_seconds", None)
        self._cache = SafeAsyncCache(
            max_size=cache_max_size, ttl_seconds=cache_ttl_seconds
        )

        # Processor-specific lock names
        self._processor_id = config.get("processor_id", self.__class__.__name__)
        self._cache_lock_name = f"{self._processor_id}_cache"
        self._update_lock_name = f"{self._processor_id}_update"

        logger.debug(f"Initialized AsyncProcessorBase: {self._processor_id}")

    async def _safe_cache_operation(
        self, key: str, operation: Callable[[], Awaitable[Any]]
    ) -> Any:
        """Execute cache operation with proper locking.

        Args:
            key: Cache key for lock management
            operation: Async operation to execute

        Returns:
            Any: Result of the operation
        """
        lock_name = f"{self._cache_lock_name}_{key}"
        async with self._lock_manager.get_async_lock(lock_name):
            return await operation()

    async def _atomic_update(
        self, update_key: str, update_func: Callable[[], Awaitable[Any]]
    ) -> Any:
        """Atomic update operation with proper locking.

        Args:
            update_key: Update key for lock management
            update_func: Async function to execute atomically

        Returns:
            Any: Result of the update operation
        """
        lock_name = f"{self._update_lock_name}_{update_key}"
        async with self._lock_manager.get_async_lock(lock_name):
            return await update_func()

    async def _get_or_create_cached_value(
        self, cache_key: str, factory: Callable[[], Awaitable[Any]]
    ) -> Any:
        """Get or create cached value with atomic operations.

        Args:
            cache_key: Key for caching
            factory: Async function to create value if not cached

        Returns:
            Any: Cached or newly created value
        """
        return await self._cache.get_or_create(cache_key, factory)

    async def _update_cache_atomic(self, cache_key: str, new_value: Any) -> None:
        """Update cache entry atomically.

        Args:
            cache_key: Key to update
            new_value: New value to store
        """
        await self._cache.set(cache_key, new_value)

    async def _remove_from_cache(self, cache_key: str) -> bool:
        """Remove entry from cache atomically.

        Args:
            cache_key: Key to remove

        Returns:
            bool: True if key was removed, False if not found
        """
        return await self._cache.delete(cache_key)

    async def _cleanup_expired_cache(self) -> int:
        """Clean up expired cache entries.

        Returns:
            int: Number of entries removed
        """
        return await self._cache.cleanup_expired()

    async def _start_impl(self) -> None:
        """Async processor startup with cache initialization.

        Override this method to implement custom async initialization logic.
        Always call super()._start_impl() to ensure proper initialization.
        """
        logger.info(f"Starting async processor: {self._processor_id}")
        # Perform any cache warmup or initialization here
        # Subclasses can override this method

    async def _stop_impl(self) -> None:
        """Async processor cleanup with cache cleanup.

        Override this method to implement custom async cleanup logic.
        Always call super()._stop_impl() to ensure proper cleanup.
        """
        logger.info(f"Stopping async processor: {self._processor_id}")
        # Clean up cache and resources
        await self._cache.clear()
        # Subclasses can override this method

    def get_async_stats(self) -> Dict[str, Any]:
        """Get async processor statistics.

        Returns:
            Dict with processor and cache statistics
        """
        lock_stats = self._lock_manager.get_lock_stats()
        cache_stats = self._cache.get_stats()

        return {
            "processor_id": self._processor_id,
            "is_started": self.is_started,
            "lock_stats": lock_stats,
            "cache_stats": cache_stats,
        }

    async def _handle_processor_error(
        self, error: Exception, context: Dict[str, Any]
    ) -> None:
        """Handle processor errors with proper logging.

        Args:
            error: The exception that occurred
            context: Context information for debugging
        """
        logger.error(
            f"Error in async processor {self._processor_id}: {error}",
            extra={
                "processor_id": self._processor_id,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "context": context,
            },
            exc_info=True,
        )

    @abstractmethod
    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Process a log event with async-safe operations.

        This method should use the async-safe operations provided by this base class
        to ensure proper locking and race condition prevention.

        Args:
            logger: The logger instance
            method_name: The logging method name (e.g., 'info', 'error')
            event_dict: The event dictionary to process

        Returns:
            The processed event dictionary, or None to drop the event
        """
        pass

    async def process_async(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Async version of process method for processors that need async operations.

        Override this method instead of process() if your processor needs
        to perform async operations during processing.

        Args:
            logger: The logger instance
            method_name: The logging method name (e.g., 'info', 'error')
            event_dict: The event dictionary to process

        Returns:
            The processed event dictionary, or None to drop the event
        """
        # Default implementation calls the sync process method
        # Subclasses can override this for true async processing
        return self.process(logger, method_name, event_dict)

    def _create_processor_task(
        self, coro: Awaitable[Any], task_name: Optional[str] = None
    ) -> Optional[asyncio.Task]:
        """Create an async task safely for processor operations.

        Args:
            coro: Coroutine to execute
            task_name: Optional name for the task

        Returns:
            Optional[asyncio.Task]: Created task or None if no event loop
        """
        try:
            task = asyncio.create_task(coro)
            if task_name:
                task.set_name(f"{self._processor_id}_{task_name}")
            logger.debug(f"Created async task: {task_name or 'unnamed'}")
            return task
        except RuntimeError as e:
            logger.warning(f"Could not create async task for {self._processor_id}: {e}")
            return None

    @property
    def is_started(self) -> bool:
        """Check if processor is started.

        Returns:
            True if the processor has been started, False otherwise
        """
        return self._started

    def get_metrics(self) -> Dict[str, Any]:
        """Get base processor metrics.

        Returns:
            Dictionary with base processor metrics
        """
        return {
            "processor_id": self._processor_id,
            "is_started": self.is_started,
            "cache_stats": self._cache.get_stats(),
        }
