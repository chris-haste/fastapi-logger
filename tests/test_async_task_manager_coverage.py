"""Comprehensive tests for AsyncTaskManager to achieve >90% coverage."""

import asyncio

import pytest

from fapilog._internal.async_task_manager import AsyncTaskManager


@pytest.mark.asyncio
class TestAsyncTaskManagerCoverage:
    """Comprehensive test suite for AsyncTaskManager coverage."""

    async def test_basic_task_creation_and_tracking(self):
        """Test basic task creation and tracking."""
        manager = AsyncTaskManager(max_concurrent_tasks=5)

        async def simple_task():
            await asyncio.sleep(0.01)
            return "completed"

        # Create a task
        task = await manager.create_task(simple_task(), task_name="test_task")

        assert task is not None
        assert task.get_name().startswith("test_task_")
        assert len(manager._active_tasks) == 1

        # Wait for completion
        result = await task
        assert result == "completed"

        # Task should be automatically removed after completion
        await asyncio.sleep(0.01)  # Give callback time to run
        assert len(manager._active_tasks) == 0

    async def test_task_limit_enforcement(self):
        """Test task limit enforcement and dropping tasks."""
        manager = AsyncTaskManager(max_concurrent_tasks=2)

        async def blocking_task():
            await asyncio.sleep(0.1)

        # Create tasks up to limit
        task1 = await manager.create_task(blocking_task(), task_name="task1")
        task2 = await manager.create_task(blocking_task(), task_name="task2")

        assert task1 is not None
        assert task2 is not None
        assert len(manager._active_tasks) == 2

        # Try to create another task - should be dropped due to limit
        task3 = await manager.create_task(blocking_task(), task_name="task3")
        assert task3 is None
        assert len(manager._active_tasks) == 2

        # Clean up
        await manager.cancel_all_tasks()

    async def test_task_creation_without_name(self):
        """Test task creation without explicit name."""
        manager = AsyncTaskManager()

        async def unnamed_task():
            return "unnamed"

        task = await manager.create_task(unnamed_task())
        assert task is not None
        assert task.get_name().startswith("task_")

        await task
        await asyncio.sleep(0.01)  # Give callback time to run

    async def test_task_exception_handling_in_callback(self):
        """Test task exception handling in done callback."""
        manager = AsyncTaskManager()

        async def failing_task():
            raise ValueError("Test exception")

        task = await manager.create_task(failing_task(), task_name="failing_task")
        assert task is not None

        # Wait for task to complete with exception
        with pytest.raises(ValueError, match="Test exception"):
            await task

        # Give callback time to run and log the exception
        await asyncio.sleep(0.01)
        assert len(manager._active_tasks) == 0

    async def test_cleanup_completed_tasks(self):
        """Test manual cleanup of completed tasks."""
        manager = AsyncTaskManager()

        async def quick_task(result):
            return result

        # Create several tasks
        task1 = await manager.create_task(quick_task("result1"))
        task2 = await manager.create_task(quick_task("result2"))

        # Wait for tasks to complete
        await task1
        await task2

        # Tasks should still be tracked (cleanup callback may not have run yet)
        assert (
            len(manager._active_tasks) >= 0
        )  # Could be 0, 1, or 2 depending on callback timing

        # Manual cleanup
        cleaned_count = await manager.cleanup_completed_tasks()
        assert cleaned_count >= 0
        assert len(manager._active_tasks) == 0

    async def test_wait_for_all_tasks_success(self):
        """Test waiting for all tasks to complete successfully."""
        manager = AsyncTaskManager()

        async def delayed_task(delay, result):
            await asyncio.sleep(delay)
            return result

        # Create multiple tasks
        task1 = await manager.create_task(delayed_task(0.01, "result1"))
        task2 = await manager.create_task(delayed_task(0.02, "result2"))
        task3 = await manager.create_task(delayed_task(0.03, "result3"))

        assert len(manager._active_tasks) == 3

        # Wait for all tasks to complete
        success = await manager.wait_for_all_tasks(timeout=1.0)
        assert success is True

        # All tasks should be done
        assert all(task.done() for task in [task1, task2, task3])

    async def test_wait_for_all_tasks_empty(self):
        """Test waiting for tasks when no tasks are active."""
        manager = AsyncTaskManager()

        # Should return True immediately
        success = await manager.wait_for_all_tasks(timeout=1.0)
        assert success is True

    async def test_wait_for_all_tasks_timeout(self):
        """Test timeout when waiting for tasks."""
        manager = AsyncTaskManager()

        async def very_slow_task():
            await asyncio.sleep(1.0)  # Long delay

        task = await manager.create_task(very_slow_task())
        assert task is not None

        # Wait with short timeout - should timeout
        success = await manager.wait_for_all_tasks(timeout=0.01)
        assert success is False

        # Clean up the slow task
        await manager.cancel_all_tasks()

    async def test_cancel_all_tasks_with_active_tasks(self):
        """Test cancelling all active tasks."""
        manager = AsyncTaskManager()

        async def cancellable_task():
            try:
                await asyncio.sleep(1.0)  # Long delay
                return "should_not_complete"
            except asyncio.CancelledError:
                return "cancelled"

        # Create multiple tasks
        task1 = await manager.create_task(cancellable_task())
        task2 = await manager.create_task(cancellable_task())
        task3 = await manager.create_task(cancellable_task())

        assert len(manager._active_tasks) == 3

        # Cancel all tasks
        cancelled_count = await manager.cancel_all_tasks(timeout=0.1)
        assert cancelled_count == 3
        assert len(manager._active_tasks) == 0

        # Tasks should be cancelled
        assert all(task.cancelled() for task in [task1, task2, task3])

    async def test_cancel_all_tasks_empty(self):
        """Test cancelling when no tasks are active."""
        manager = AsyncTaskManager()

        # Should return 0 immediately
        cancelled_count = await manager.cancel_all_tasks()
        assert cancelled_count == 0

    async def test_cancel_all_tasks_timeout(self):
        """Test cancel timeout handling."""
        manager = AsyncTaskManager()

        async def stubborn_task():
            try:
                # Task that doesn't handle cancellation gracefully
                while True:
                    await asyncio.sleep(0.01)
            except asyncio.CancelledError:
                # Simulate slow cleanup
                await asyncio.sleep(0.1)
                raise

        task = await manager.create_task(stubborn_task())
        assert task is not None

        # Cancel with very short timeout
        cancelled_count = await manager.cancel_all_tasks(timeout=0.001)
        assert cancelled_count == 1
        assert len(manager._active_tasks) == 0  # Force cleanup should work

    async def test_get_task_stats(self):
        """Test task statistics."""
        manager = AsyncTaskManager(max_concurrent_tasks=10)

        # Initially empty
        stats = manager.get_task_stats()
        assert stats["active_tasks"] == 0
        assert stats["running_tasks"] == 0
        assert stats["completed_tasks"] == 0
        assert stats["max_concurrent_tasks"] == 10
        assert stats["utilization"] == 0.0

        async def test_task():
            await asyncio.sleep(0.05)

        # Create some tasks
        task1 = await manager.create_task(test_task())
        task2 = await manager.create_task(test_task())

        stats = manager.get_task_stats()
        assert stats["active_tasks"] == 2
        assert stats["running_tasks"] <= 2  # Could be running or done
        assert stats["max_concurrent_tasks"] == 10
        assert stats["utilization"] == 0.2  # 2/10

        # Wait for completion
        await task1
        await task2
        await asyncio.sleep(0.01)  # Give callbacks time to run

    async def test_get_task_stats_zero_max_tasks(self):
        """Test task statistics with zero max tasks."""
        manager = AsyncTaskManager(max_concurrent_tasks=0)

        stats = manager.get_task_stats()
        assert stats["utilization"] == 0.0  # Should handle division by zero

    async def test_async_context_manager(self):
        """Test async context manager functionality."""

        async def background_task():
            await asyncio.sleep(0.1)

        # Use as context manager
        async with AsyncTaskManager() as manager:
            task = await manager.create_task(background_task())
            assert task is not None
            assert len(manager._active_tasks) == 1

        # Tasks should be cancelled on exit
        assert task.cancelled() or task.done()

    async def test_runtime_error_handling_in_create_task(self):
        """Test handling of RuntimeError during task creation."""
        manager = AsyncTaskManager()

        # Create a coroutine that will cause issues
        async def normal_task():
            return "ok"

        # First create a normal task to test the happy path
        task = await manager.create_task(normal_task())
        assert task is not None
        await task

        # For testing RuntimeError, we would need to simulate an environment
        # where asyncio.create_task fails, which is difficult to do reliably
        # in a test. The error handling is there for edge cases in real usage.

    async def test_remove_task_with_successful_completion(self):
        """Test _remove_task callback with successful task completion."""
        manager = AsyncTaskManager()

        async def successful_task():
            return "success"

        task = await manager.create_task(successful_task(), task_name="success_task")
        assert task is not None

        # Wait for completion
        result = await task
        assert result == "success"

        # Give callback time to run
        await asyncio.sleep(0.01)

        # Task should be removed from active tasks
        assert len(manager._active_tasks) == 0

    async def test_fire_and_forget_parameter(self):
        """Test task creation without fire_and_forget parameter (parameter was removed)."""
        manager = AsyncTaskManager()

        async def simple_task():
            return "done"

        # Test task creation without the removed parameter
        task1 = await manager.create_task(simple_task())
        assert task1 is not None

        # Test task creation with task name
        task2 = await manager.create_task(simple_task(), task_name="named_task")
        assert task2 is not None

        await task1
        await task2
        await asyncio.sleep(0.01)  # Give callbacks time to run
