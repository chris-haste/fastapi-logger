"""Background cleanup management for processors.

This module provides safe background cleanup operations to replace the
dangerous patterns in the current processor implementations.
"""

import asyncio
import logging
import time
from typing import Any, Callable, Optional, Protocol

from .task_manager import AsyncTaskManager

logger = logging.getLogger(__name__)


class CleanupTarget(Protocol):
    """Protocol for objects that support cleanup operations."""

    async def cleanup_expired_entries(self, current_time: float) -> int:
        """Clean up expired entries.

        Args:
            current_time: Current timestamp

        Returns:
            int: Number of entries cleaned up
        """
        ...


class BackgroundCleanupManager:
    """Manage background cleanup operations safely.

    Provides proper scheduling, error handling, and task management for
    background cleanup operations to replace unsafe patterns.
    """

    def __init__(
        self,
        cleanup_target: CleanupTarget,
        cleanup_interval: float = 60.0,
        cleanup_threshold_ratio: float = 0.8,
        max_cleanup_duration: float = 30.0,
    ):
        """Initialize background cleanup manager.

        Args:
            cleanup_target: Object that implements cleanup operations
            cleanup_interval: Minimum time between cleanup operations (seconds)
            cleanup_threshold_ratio: Trigger cleanup when utilization exceeds this
            max_cleanup_duration: Maximum time for cleanup operation
        """
        self.cleanup_target = cleanup_target
        self.cleanup_interval = cleanup_interval
        self.cleanup_threshold_ratio = cleanup_threshold_ratio
        self.max_cleanup_duration = max_cleanup_duration

        self._task_manager = AsyncTaskManager(max_concurrent_tasks=10)
        self._last_cleanup = time.time()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._is_running = False

    async def schedule_cleanup(
        self,
        current_time: float,
        force: bool = False,
        utilization_check: Optional[Callable[[], float]] = None,
    ) -> bool:
        """Schedule background cleanup if needed.

        Args:
            current_time: Current timestamp
            force: Force cleanup regardless of conditions
            utilization_check: Optional function to check current utilization

        Returns:
            bool: True if cleanup was scheduled, False otherwise
        """
        if not self._should_cleanup(current_time, force, utilization_check):
            return False

        # Check if cleanup is already running
        if self._cleanup_task and not self._cleanup_task.done():
            logger.debug("Cleanup already in progress, skipping")
            return False

        # Schedule new cleanup
        self._cleanup_task = await self._task_manager.create_task(
            self._perform_cleanup(current_time), task_name="background_cleanup"
        )

        if self._cleanup_task:
            logger.debug("Scheduled background cleanup")
            return True
        else:
            logger.warning("Could not schedule cleanup - task manager at capacity")
            return False

    async def _perform_cleanup(self, current_time: float) -> None:
        """Perform cleanup with proper error handling and timeout.

        Args:
            current_time: Current timestamp
        """
        cleanup_start = time.time()

        try:
            logger.debug("Starting background cleanup")

            # Perform cleanup with timeout
            cleaned_count = await asyncio.wait_for(
                self.cleanup_target.cleanup_expired_entries(current_time),
                timeout=self.max_cleanup_duration,
            )

            # Update last cleanup time
            self._last_cleanup = current_time

            cleanup_duration = time.time() - cleanup_start
            logger.debug(
                f"Background cleanup completed: {cleaned_count} entries, "
                f"{cleanup_duration:.2f}s"
            )

            # Clean up completed tasks in task manager
            await self._task_manager.cleanup_completed_tasks()

        except asyncio.TimeoutError:
            logger.warning(
                f"Background cleanup timed out after {self.max_cleanup_duration}s"
            )

        except Exception as e:
            logger.warning(f"Background cleanup error: {e}", exc_info=True)

    def _should_cleanup(
        self,
        current_time: float,
        force: bool = False,
        utilization_check: Optional[Callable[[], float]] = None,
    ) -> bool:
        """Determine if cleanup should be performed.

        Args:
            current_time: Current timestamp
            force: Force cleanup regardless of conditions
            utilization_check: Optional function to check current utilization

        Returns:
            bool: True if cleanup should be performed
        """
        if force:
            return True

        # Check time-based cleanup
        time_elapsed = (current_time - self._last_cleanup) > self.cleanup_interval

        # Check utilization-based cleanup
        utilization_high = False
        if utilization_check:
            try:
                utilization = utilization_check()
                utilization_high = utilization > self.cleanup_threshold_ratio
            except Exception as e:
                logger.warning(f"Error checking utilization: {e}")

        return time_elapsed or utilization_high

    async def force_cleanup(self, current_time: Optional[float] = None) -> int:
        """Force immediate cleanup operation.

        Args:
            current_time: Optional timestamp, defaults to current time

        Returns:
            int: Number of entries cleaned up
        """
        if current_time is None:
            current_time = time.time()

        try:
            logger.info("Forcing immediate cleanup")
            cleaned_count = await asyncio.wait_for(
                self.cleanup_target.cleanup_expired_entries(current_time),
                timeout=self.max_cleanup_duration,
            )

            self._last_cleanup = current_time
            logger.info(f"Force cleanup completed: {cleaned_count} entries")
            return cleaned_count

        except asyncio.TimeoutError:
            logger.error(f"Force cleanup timed out after {self.max_cleanup_duration}s")
            return 0

        except Exception as e:
            logger.error(f"Force cleanup error: {e}", exc_info=True)
            return 0

    async def start(self) -> None:
        """Start the background cleanup manager."""
        if self._is_running:
            return

        self._is_running = True
        self._last_cleanup = time.time()
        logger.info("Background cleanup manager started")

    async def stop(self, timeout: float = 5.0) -> None:
        """Stop cleanup manager and wait for tasks.

        Args:
            timeout: Maximum time to wait for task completion
        """
        if not self._is_running:
            return

        logger.info("Stopping background cleanup manager")
        self._is_running = False

        # Cancel current cleanup task if running
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await asyncio.wait_for(self._cleanup_task, timeout=1.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

        # Wait for all tasks to complete
        success = await self._task_manager.wait_for_all_tasks(timeout)
        if not success:
            await self._task_manager.cancel_all_tasks()

        logger.info("Background cleanup manager stopped")

    def get_cleanup_stats(self) -> dict[str, Any]:
        """Get cleanup manager statistics.

        Returns:
            Dict with cleanup statistics
        """
        current_time = time.time()
        time_since_last = current_time - self._last_cleanup

        task_stats = self._task_manager.get_task_stats()

        return {
            "is_running": self._is_running,
            "last_cleanup": self._last_cleanup,
            "time_since_last_cleanup": time_since_last,
            "cleanup_interval": self.cleanup_interval,
            "cleanup_threshold_ratio": self.cleanup_threshold_ratio,
            "current_cleanup_active": (
                self._cleanup_task is not None and not self._cleanup_task.done()
            ),
            "task_manager_stats": task_stats,
        }

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        if exc_type is not None:
            logger.warning(
                f"BackgroundCleanupManager context exit with exception: "
                f"{exc_type.__name__}: {exc_val}"
            )
        await self.stop()
