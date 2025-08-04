"""Async task lifecycle management for processors.

This module provides proper async task management to eliminate memory leaks
and task abandonment patterns found in current processor implementations.
"""

import asyncio
import logging
from typing import Any, Awaitable, Optional, Set

logger = logging.getLogger(__name__)


class AsyncTaskManager:
    """Manage async task lifecycle to prevent memory leaks.

    Provides proper task tracking, cleanup, and error handling to replace
    the dangerous weakref.finalize and task abandonment patterns.
    """

    def __init__(self, max_concurrent_tasks: int = 100):
        """Initialize task manager with concurrent task limits.

        Args:
            max_concurrent_tasks: Maximum number of concurrent tasks to track
        """
        self._active_tasks: Set[asyncio.Task] = set()
        self._lock = asyncio.Lock()
        self._max_concurrent_tasks = max_concurrent_tasks
        self._task_counter = 0

    async def create_task(
        self,
        coro: Awaitable[Any],
        task_name: Optional[str] = None,
    ) -> Optional[asyncio.Task]:
        """Create and track async task with proper lifecycle management.

        Args:
            coro: Coroutine to execute
            task_name: Optional name for the task

        Returns:
            Optional[asyncio.Task]: Created task or None if limit exceeded
        """
        async with self._lock:
            # Check concurrent task limit
            if len(self._active_tasks) >= self._max_concurrent_tasks:
                logger.warning(
                    f"Task limit reached ({self._max_concurrent_tasks}), "
                    f"dropping task: {task_name or 'unnamed'}"
                )
                return None

            # Create task with proper naming
            self._task_counter += 1
            task_id = f"{task_name or 'task'}_{self._task_counter}"

            try:
                task = asyncio.create_task(coro, name=task_id)
                self._active_tasks.add(task)

                # Set up automatic cleanup when task completes
                task.add_done_callback(self._remove_task)

                logger.debug(f"Created async task: {task_id}")
                return task

            except RuntimeError as e:
                logger.warning(f"Could not create async task {task_id}: {e}")
                return None

    def _remove_task(self, task: asyncio.Task) -> None:
        """Remove completed task from tracking.

        Args:
            task: Completed task to remove
        """
        self._active_tasks.discard(task)

        # Log any exceptions that occurred
        if task.done() and not task.cancelled():
            try:
                # This will raise the exception if one occurred
                task.result()
                logger.debug(f"Task completed successfully: {task.get_name()}")
            except Exception as e:
                logger.warning(f"Task failed: {task.get_name()}: {e}", exc_info=True)

    async def cleanup_completed_tasks(self) -> int:
        """Clean up completed tasks from tracking.

        Returns:
            int: Number of tasks cleaned up
        """
        async with self._lock:
            completed_tasks = {task for task in self._active_tasks if task.done()}
            self._active_tasks -= completed_tasks

            cleaned_count = len(completed_tasks)
            if cleaned_count > 0:
                logger.debug(f"Cleaned up {cleaned_count} completed tasks")

            return cleaned_count

    async def wait_for_all_tasks(self, timeout: float = 5.0) -> bool:
        """Wait for all active tasks to complete.

        Args:
            timeout: Maximum time to wait for task completion

        Returns:
            bool: True if all tasks completed, False if timeout occurred
        """
        if not self._active_tasks:
            return True

        try:
            logger.info(
                f"Waiting for {len(self._active_tasks)} active tasks to complete"
            )
            await asyncio.wait_for(
                asyncio.gather(*list(self._active_tasks), return_exceptions=True),
                timeout=timeout,
            )
            logger.info("All tasks completed successfully")
            return True

        except asyncio.TimeoutError:
            logger.warning(
                f"Timeout waiting for {len(self._active_tasks)} tasks to complete"
            )
            return False

    async def cancel_all_tasks(self, timeout: float = 2.0) -> int:
        """Cancel all active tasks with graceful shutdown.

        Args:
            timeout: Time to wait for graceful cancellation

        Returns:
            int: Number of tasks cancelled
        """
        if not self._active_tasks:
            return 0

        cancelled_count = 0
        tasks_to_cancel = list(self._active_tasks)

        logger.info(f"Cancelling {len(tasks_to_cancel)} active tasks")

        # Cancel all tasks
        for task in tasks_to_cancel:
            if not task.done():
                task.cancel()
                cancelled_count += 1

        # Wait for cancellation to complete
        try:
            await asyncio.wait_for(
                asyncio.gather(*tasks_to_cancel, return_exceptions=True),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.warning("Some tasks did not cancel gracefully")

        # Force cleanup
        async with self._lock:
            self._active_tasks.clear()

        logger.info(f"Cancelled {cancelled_count} tasks")
        return cancelled_count

    def get_task_stats(self) -> dict[str, Any]:
        """Get task manager statistics.

        Returns:
            Dict with task statistics
        """
        active_count = len(self._active_tasks)
        running_count = sum(1 for task in self._active_tasks if not task.done())

        return {
            "active_tasks": active_count,
            "running_tasks": running_count,
            "completed_tasks": active_count - running_count,
            "max_concurrent_tasks": self._max_concurrent_tasks,
            "utilization": active_count / self._max_concurrent_tasks
            if self._max_concurrent_tasks > 0
            else 0.0,
        }

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        if exc_type is not None:
            logger.warning(
                f"AsyncTaskManager context exit with exception: {exc_type.__name__}: {exc_val}"
            )
        await self.cancel_all_tasks()
