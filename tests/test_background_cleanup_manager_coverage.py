"""Comprehensive tests for BackgroundCleanupManager to achieve >90% coverage."""

import asyncio
import time

import pytest

from fapilog._internal.background_cleanup_manager import (
    BackgroundCleanupManager,
)


class MockCleanupTarget:
    """Mock implementation of CleanupTarget for testing."""

    def __init__(self, cleanup_count: int = 5, cleanup_delay: float = 0.01):
        self.cleanup_count = cleanup_count
        self.cleanup_delay = cleanup_delay
        self.cleanup_calls = []
        self.should_raise = False
        self.should_timeout = False

    async def cleanup_expired_entries(self, current_time: float) -> int:
        """Mock cleanup that can simulate various scenarios."""
        self.cleanup_calls.append(current_time)

        if self.should_raise:
            raise ValueError("Mock cleanup error")

        if self.should_timeout:
            await asyncio.sleep(10)  # Long delay to trigger timeout

        await asyncio.sleep(self.cleanup_delay)
        return self.cleanup_count


class MockUtilizationCheck:
    """Mock utilization check function."""

    def __init__(self, utilization: float = 0.5):
        self.utilization = utilization
        self.call_count = 0
        self.should_raise = False

    def __call__(self) -> float:
        self.call_count += 1
        if self.should_raise:
            raise RuntimeError("Mock utilization check error")
        return self.utilization


@pytest.mark.asyncio
class TestBackgroundCleanupManagerCoverage:
    """Comprehensive test suite for BackgroundCleanupManager coverage."""

    async def test_initialization(self):
        """Test BackgroundCleanupManager initialization."""
        cleanup_target = MockCleanupTarget()

        manager = BackgroundCleanupManager(
            cleanup_target=cleanup_target,
            cleanup_interval=30.0,
            cleanup_threshold_ratio=0.9,
            max_cleanup_duration=15.0,
        )

        assert manager.cleanup_target is cleanup_target
        assert manager.cleanup_interval == 30.0
        assert manager.cleanup_threshold_ratio == 0.9
        assert manager.max_cleanup_duration == 15.0
        assert not manager._is_running
        assert manager._cleanup_task is None

    async def test_default_initialization(self):
        """Test BackgroundCleanupManager with default parameters."""
        cleanup_target = MockCleanupTarget()
        manager = BackgroundCleanupManager(cleanup_target)

        assert manager.cleanup_interval == 60.0
        assert manager.cleanup_threshold_ratio == 0.8
        assert manager.max_cleanup_duration == 30.0

    async def test_schedule_cleanup_success(self):
        """Test successful cleanup scheduling."""
        cleanup_target = MockCleanupTarget(cleanup_count=3)
        manager = BackgroundCleanupManager(cleanup_target, cleanup_interval=0.01)

        current_time = time.time()

        # Schedule cleanup (should succeed due to time elapsed)
        scheduled = await manager.schedule_cleanup(current_time + 1.0)
        assert scheduled is True

        # Wait for cleanup to complete
        if manager._cleanup_task:
            await manager._cleanup_task

        assert len(cleanup_target.cleanup_calls) == 1
        await manager.stop()

    async def test_schedule_cleanup_force(self):
        """Test forced cleanup scheduling."""
        cleanup_target = MockCleanupTarget(cleanup_count=2)
        manager = BackgroundCleanupManager(cleanup_target, cleanup_interval=1000.0)

        current_time = time.time()

        # Force cleanup (should succeed even with long interval)
        scheduled = await manager.schedule_cleanup(current_time, force=True)
        assert scheduled is True

        # Wait for cleanup to complete
        if manager._cleanup_task:
            await manager._cleanup_task

        assert len(cleanup_target.cleanup_calls) == 1
        await manager.stop()

    async def test_schedule_cleanup_utilization_based(self):
        """Test utilization-based cleanup scheduling."""
        cleanup_target = MockCleanupTarget()
        manager = BackgroundCleanupManager(
            cleanup_target, cleanup_interval=1000.0, cleanup_threshold_ratio=0.7
        )

        current_time = time.time()
        utilization_check = MockUtilizationCheck(utilization=0.8)  # Above threshold

        # Should schedule due to high utilization
        scheduled = await manager.schedule_cleanup(
            current_time, utilization_check=utilization_check
        )
        assert scheduled is True
        assert utilization_check.call_count == 1

        # Wait for cleanup to complete
        if manager._cleanup_task:
            await manager._cleanup_task

        await manager.stop()

    async def test_schedule_cleanup_no_trigger(self):
        """Test cleanup not scheduled when conditions not met."""
        cleanup_target = MockCleanupTarget()
        manager = BackgroundCleanupManager(
            cleanup_target, cleanup_interval=1000.0, cleanup_threshold_ratio=0.9
        )

        current_time = time.time()
        utilization_check = MockUtilizationCheck(utilization=0.5)  # Below threshold

        # Should not schedule (time not elapsed, utilization low)
        scheduled = await manager.schedule_cleanup(
            current_time, utilization_check=utilization_check
        )
        assert scheduled is False

    async def test_schedule_cleanup_already_running(self):
        """Test cleanup not scheduled when already running."""
        cleanup_target = MockCleanupTarget(cleanup_delay=0.1)  # Slow cleanup
        manager = BackgroundCleanupManager(cleanup_target, cleanup_interval=0.01)

        current_time = time.time()

        # Schedule first cleanup
        scheduled1 = await manager.schedule_cleanup(current_time + 1.0)
        assert scheduled1 is True

        # Try to schedule second cleanup while first is running
        scheduled2 = await manager.schedule_cleanup(current_time + 2.0)
        assert scheduled2 is False

        # Wait for first cleanup to complete
        if manager._cleanup_task:
            await manager._cleanup_task

        await manager.stop()

    async def test_schedule_cleanup_task_manager_capacity(self):
        """Test cleanup scheduling when task manager is at capacity."""
        cleanup_target = MockCleanupTarget()
        manager = BackgroundCleanupManager(cleanup_target)

        # Fill up task manager capacity
        async def long_task():
            await asyncio.sleep(0.1)

        # Create tasks to fill capacity
        for _ in range(15):  # More than the default max_concurrent_tasks=10
            await manager._task_manager.create_task(long_task())

        current_time = time.time()
        scheduled = await manager.schedule_cleanup(current_time, force=True)

        # Should fail due to task manager capacity
        assert scheduled is False

        await manager.stop()

    async def test_perform_cleanup_success(self):
        """Test successful cleanup performance."""
        cleanup_target = MockCleanupTarget(cleanup_count=7)
        manager = BackgroundCleanupManager(cleanup_target)

        current_time = time.time()

        # Perform cleanup directly
        await manager._perform_cleanup(current_time)

        assert len(cleanup_target.cleanup_calls) == 1
        assert cleanup_target.cleanup_calls[0] == current_time
        assert manager._last_cleanup == current_time

    async def test_perform_cleanup_timeout(self):
        """Test cleanup timeout handling."""
        cleanup_target = MockCleanupTarget()
        cleanup_target.should_timeout = True

        manager = BackgroundCleanupManager(cleanup_target, max_cleanup_duration=0.01)

        original_last_cleanup = manager._last_cleanup
        current_time = time.time() + 1.0  # Ensure different time

        # Should complete without raising exception (timeout handled)
        await manager._perform_cleanup(current_time)

        # Last cleanup time should not be updated on timeout
        assert manager._last_cleanup == original_last_cleanup

    async def test_perform_cleanup_exception(self):
        """Test cleanup exception handling."""
        cleanup_target = MockCleanupTarget()
        cleanup_target.should_raise = True

        manager = BackgroundCleanupManager(cleanup_target)

        original_last_cleanup = manager._last_cleanup
        current_time = time.time() + 1.0  # Ensure different time

        # Should complete without raising exception (error handled)
        await manager._perform_cleanup(current_time)

        # Last cleanup time should not be updated on error
        assert manager._last_cleanup == original_last_cleanup

    async def test_should_cleanup_force(self):
        """Test _should_cleanup with force flag."""
        cleanup_target = MockCleanupTarget()
        manager = BackgroundCleanupManager(cleanup_target, cleanup_interval=1000.0)

        current_time = time.time()

        # Should return True when forced
        assert manager._should_cleanup(current_time, force=True) is True

    async def test_should_cleanup_time_based(self):
        """Test _should_cleanup time-based logic."""
        cleanup_target = MockCleanupTarget()
        manager = BackgroundCleanupManager(cleanup_target, cleanup_interval=0.01)

        current_time = time.time()

        # Should return False immediately
        assert manager._should_cleanup(current_time) is False

        # Should return True after interval
        future_time = current_time + 1.0
        assert manager._should_cleanup(future_time) is True

    async def test_should_cleanup_utilization_based(self):
        """Test _should_cleanup utilization-based logic."""
        cleanup_target = MockCleanupTarget()
        manager = BackgroundCleanupManager(
            cleanup_target, cleanup_interval=1000.0, cleanup_threshold_ratio=0.7
        )

        current_time = time.time()

        # Low utilization - should return False
        low_util_check = MockUtilizationCheck(utilization=0.5)
        assert (
            manager._should_cleanup(current_time, utilization_check=low_util_check)
            is False
        )

        # High utilization - should return True
        high_util_check = MockUtilizationCheck(utilization=0.8)
        assert (
            manager._should_cleanup(current_time, utilization_check=high_util_check)
            is True
        )

    async def test_should_cleanup_utilization_exception(self):
        """Test _should_cleanup with utilization check exception."""
        cleanup_target = MockCleanupTarget()
        manager = BackgroundCleanupManager(cleanup_target, cleanup_interval=1000.0)

        current_time = time.time()

        # Utilization check that raises exception
        error_util_check = MockUtilizationCheck()
        error_util_check.should_raise = True

        # Should return False and handle exception gracefully
        result = manager._should_cleanup(
            current_time, utilization_check=error_util_check
        )
        assert result is False

    async def test_force_cleanup_success(self):
        """Test successful force cleanup."""
        cleanup_target = MockCleanupTarget(cleanup_count=8)
        manager = BackgroundCleanupManager(cleanup_target)

        original_last_cleanup = manager._last_cleanup

        # Force cleanup with explicit time (ensure different from original)
        current_time = time.time() + 1.0  # Add 1 second to ensure difference
        result = await manager.force_cleanup(current_time)

        assert result == 8
        assert len(cleanup_target.cleanup_calls) == 1
        assert manager._last_cleanup == current_time
        assert manager._last_cleanup != original_last_cleanup

    async def test_force_cleanup_default_time(self):
        """Test force cleanup with default current time."""
        cleanup_target = MockCleanupTarget(cleanup_count=3)
        manager = BackgroundCleanupManager(cleanup_target)

        # Force cleanup without explicit time
        result = await manager.force_cleanup()

        assert result == 3
        assert len(cleanup_target.cleanup_calls) == 1

    async def test_force_cleanup_timeout(self):
        """Test force cleanup with timeout."""
        cleanup_target = MockCleanupTarget()
        cleanup_target.should_timeout = True

        manager = BackgroundCleanupManager(cleanup_target, max_cleanup_duration=0.01)

        # Should return 0 on timeout
        result = await manager.force_cleanup()
        assert result == 0

    async def test_force_cleanup_exception(self):
        """Test force cleanup with exception."""
        cleanup_target = MockCleanupTarget()
        cleanup_target.should_raise = True

        manager = BackgroundCleanupManager(cleanup_target)

        # Should return 0 on exception
        result = await manager.force_cleanup()
        assert result == 0

    async def test_start_stop_lifecycle(self):
        """Test start/stop lifecycle."""
        cleanup_target = MockCleanupTarget()
        manager = BackgroundCleanupManager(cleanup_target)

        # Initially not running
        assert not manager._is_running

        # Start manager
        await manager.start()
        assert manager._is_running

        # Starting again should be no-op
        await manager.start()
        assert manager._is_running

        # Stop manager
        await manager.stop()
        assert not manager._is_running

        # Stopping again should be no-op
        await manager.stop()
        assert not manager._is_running

    async def test_stop_with_running_cleanup(self):
        """Test stopping manager with running cleanup task."""
        cleanup_target = MockCleanupTarget(cleanup_delay=0.1)
        manager = BackgroundCleanupManager(cleanup_target)

        await manager.start()

        # Schedule a cleanup
        current_time = time.time()
        await manager.schedule_cleanup(current_time, force=True)

        # Stop manager while cleanup is running
        await manager.stop(timeout=0.5)

        assert not manager._is_running

    async def test_get_cleanup_stats(self):
        """Test cleanup statistics."""
        cleanup_target = MockCleanupTarget()
        manager = BackgroundCleanupManager(
            cleanup_target,
            cleanup_interval=30.0,
            cleanup_threshold_ratio=0.85,
        )

        await manager.start()

        stats = manager.get_cleanup_stats()

        assert stats["is_running"] is True
        assert "last_cleanup" in stats
        assert "time_since_last_cleanup" in stats
        assert stats["cleanup_interval"] == 30.0
        assert stats["cleanup_threshold_ratio"] == 0.85
        assert stats["current_cleanup_active"] is False
        assert "task_manager_stats" in stats

        await manager.stop()

    async def test_get_cleanup_stats_with_active_cleanup(self):
        """Test cleanup statistics with active cleanup."""
        cleanup_target = MockCleanupTarget(cleanup_delay=0.1)
        manager = BackgroundCleanupManager(cleanup_target)

        # Schedule cleanup
        current_time = time.time()
        await manager.schedule_cleanup(current_time, force=True)

        # Get stats while cleanup is running
        stats = manager.get_cleanup_stats()
        assert stats["current_cleanup_active"] is True

        # Wait for cleanup to complete
        if manager._cleanup_task:
            await manager._cleanup_task

        await manager.stop()

    async def test_async_context_manager(self):
        """Test async context manager functionality."""
        cleanup_target = MockCleanupTarget()

        # Use as context manager
        async with BackgroundCleanupManager(cleanup_target) as manager:
            assert manager._is_running is True

            # Test functionality within context
            stats = manager.get_cleanup_stats()
            assert stats["is_running"] is True

        # Should be stopped after exiting context
        assert manager._is_running is False

    async def test_context_manager_with_cleanup(self):
        """Test context manager with active cleanup."""
        cleanup_target = MockCleanupTarget(cleanup_delay=0.05)

        async with BackgroundCleanupManager(cleanup_target) as manager:
            # Schedule cleanup
            current_time = time.time()
            await manager.schedule_cleanup(current_time, force=True)

            # Manager should still be running
            assert manager._is_running is True

        # Should be properly stopped even with active cleanup
        assert manager._is_running is False

    async def test_cleanup_target_protocol_compliance(self):
        """Test that CleanupTarget protocol is properly defined."""
        # This test ensures the protocol is properly structured
        cleanup_target = MockCleanupTarget()

        # Should be able to call the protocol method
        result = await cleanup_target.cleanup_expired_entries(time.time())
        assert isinstance(result, int)
        assert result >= 0
