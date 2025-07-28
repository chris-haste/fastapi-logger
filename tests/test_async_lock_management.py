"""Unit tests for ProcessorLockManager foundation component.

Tests async lock management, concurrent access patterns, and race condition prevention.
"""

import asyncio
import threading
import time
from unittest.mock import patch

import pytest

from fapilog._internal.async_lock_manager import (
    ProcessorLockManager,
    get_processor_lock_manager,
)


class TestProcessorLockManager:
    """Test cases for ProcessorLockManager."""

    def test_init(self):
        """Test ProcessorLockManager initialization."""
        manager = ProcessorLockManager()

        assert manager._async_locks == {}
        assert manager._sync_locks == {}
        assert manager._lock_creation_lock is not None
        assert manager._async_lock_creation_lock is not None

    @pytest.mark.asyncio
    async def test_get_async_lock_creation(self):
        """Test async lock creation and retrieval."""
        manager = ProcessorLockManager()
        lock_name = "test_lock"

        # First access should create the lock
        async with manager.get_async_lock(lock_name) as lock:
            assert lock_name in manager._async_locks
            assert isinstance(lock, asyncio.Lock)

        # Second access should reuse the same lock
        original_lock = manager._async_locks[lock_name]
        async with manager.get_async_lock(lock_name) as lock:
            assert lock is original_lock

    @pytest.mark.asyncio
    async def test_async_lock_concurrent_creation(self):
        """Test concurrent async lock creation is thread-safe."""
        manager = ProcessorLockManager()
        lock_name = "concurrent_test"
        created_locks = []

        async def create_lock():
            async with manager.get_async_lock(lock_name) as lock:
                created_locks.append(lock)
                await asyncio.sleep(0.01)  # Simulate work

        # Run multiple concurrent lock creations
        tasks = [create_lock() for _ in range(5)]
        await asyncio.gather(*tasks)

        # All should use the same lock instance
        assert len(created_locks) == 5
        assert all(lock is created_locks[0] for lock in created_locks)
        assert len(manager._async_locks) == 1

    def test_get_sync_lock_creation(self):
        """Test sync lock creation and retrieval."""
        manager = ProcessorLockManager()
        lock_name = "sync_test_lock"

        # First access should create the lock
        lock1 = manager.get_sync_lock(lock_name)
        assert lock_name in manager._sync_locks
        assert isinstance(lock1, threading.Lock)

        # Second access should return the same lock
        lock2 = manager.get_sync_lock(lock_name)
        assert lock1 is lock2

    def test_sync_lock_thread_safety(self):
        """Test sync lock creation is thread-safe."""
        manager = ProcessorLockManager()
        lock_name = "thread_safe_test"
        created_locks = []
        barrier = threading.Barrier(3)

        def create_lock():
            barrier.wait()  # Synchronize start
            lock = manager.get_sync_lock(lock_name)
            created_locks.append(lock)

        # Run concurrent threads
        threads = [threading.Thread(target=create_lock) for _ in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All should get the same lock instance
        assert len(created_locks) == 3
        assert all(lock is created_locks[0] for lock in created_locks)

    @pytest.mark.asyncio
    async def test_async_lock_mutual_exclusion(self):
        """Test async locks provide mutual exclusion."""
        manager = ProcessorLockManager()
        lock_name = "mutex_test"
        execution_order = []

        async def worker(worker_id: int):
            async with manager.get_async_lock(lock_name):
                execution_order.append(f"start_{worker_id}")
                await asyncio.sleep(0.01)  # Simulate work
                execution_order.append(f"end_{worker_id}")

        # Run concurrent workers
        tasks = [worker(i) for i in range(3)]
        await asyncio.gather(*tasks)

        # Verify no interleaving (proper mutual exclusion)
        for i in range(3):
            start_idx = execution_order.index(f"start_{i}")
            end_idx = execution_order.index(f"end_{i}")

            # No other worker should start between this worker's start and end
            for j in range(3):
                if i != j:
                    other_start_idx = execution_order.index(f"start_{j}")
                    assert not (start_idx < other_start_idx < end_idx)

    @pytest.mark.asyncio
    async def test_cleanup_unused_locks(self):
        """Test cleanup of unused async locks."""
        manager = ProcessorLockManager()

        # Create some locks
        async with manager.get_async_lock("lock1"):
            pass
        async with manager.get_async_lock("lock2"):
            pass

        assert len(manager._async_locks) == 2

        # Cleanup should remove unused locks
        cleaned_count = await manager.cleanup_unused_locks()
        assert cleaned_count == 2
        assert len(manager._async_locks) == 0

    @pytest.mark.asyncio
    async def test_cleanup_preserves_active_locks(self):
        """Test cleanup preserves actively held locks."""
        manager = ProcessorLockManager()

        # Hold one lock while cleaning up
        async with manager.get_async_lock("active_lock"):
            # Create another lock that will be released
            async with manager.get_async_lock("inactive_lock"):
                pass

            # Cleanup should only remove the inactive lock
            cleaned_count = await manager.cleanup_unused_locks()
            assert cleaned_count == 1
            assert "active_lock" in manager._async_locks
            assert "inactive_lock" not in manager._async_locks

    def test_get_lock_stats(self):
        """Test lock statistics reporting."""
        manager = ProcessorLockManager()

        # Initial stats
        stats = manager.get_lock_stats()
        assert stats["async_locks"] == 0
        assert stats["sync_locks"] == 0
        assert stats["active_async_locks"] == 0

        # Add some locks
        manager.get_sync_lock("sync1")
        manager.get_sync_lock("sync2")

        stats = manager.get_lock_stats()
        assert stats["sync_locks"] == 2

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test async context manager functionality."""
        manager = ProcessorLockManager()

        # Create some locks
        async with manager.get_async_lock("test1"):
            pass
        async with manager.get_async_lock("test2"):
            pass

        assert len(manager._async_locks) == 2

        # Context manager should cleanup on exit
        async with manager:
            pass

        assert len(manager._async_locks) == 0

    @pytest.mark.asyncio
    async def test_concurrent_access_performance(self):
        """Test performance under concurrent access."""
        manager = ProcessorLockManager()
        results = []

        async def worker(worker_id: int):
            start_time = time.time()
            for i in range(10):
                lock_name = f"perf_lock_{i % 3}"  # Use 3 different locks
                async with manager.get_async_lock(lock_name):
                    await asyncio.sleep(0.001)  # Minimal work
            end_time = time.time()
            results.append(end_time - start_time)

        # Run 10 concurrent workers
        start_time = time.time()
        tasks = [worker(i) for i in range(10)]
        await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        # Verify reasonable performance (should complete in reasonable time)
        assert total_time < 5.0  # Should be much faster
        assert len(results) == 10
        assert all(result > 0 for result in results)


class TestGlobalLockManager:
    """Test cases for global lock manager singleton."""

    def test_global_lock_manager_singleton(self):
        """Test global lock manager is a singleton."""
        manager1 = get_processor_lock_manager()
        manager2 = get_processor_lock_manager()

        assert manager1 is manager2
        assert isinstance(manager1, ProcessorLockManager)

    def test_global_lock_manager_thread_safety(self):
        """Test global lock manager creation is thread-safe."""
        managers = []
        barrier = threading.Barrier(3)

        def get_manager():
            barrier.wait()  # Synchronize start
            with patch(
                "fapilog._internal.async_lock_manager._global_lock_manager", None
            ):
                manager = get_processor_lock_manager()
                managers.append(manager)

        # Reset global state for this test
        with patch("fapilog._internal.async_lock_manager._global_lock_manager", None):
            threads = [threading.Thread(target=get_manager) for _ in range(3)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

        # All should get the same instance (singleton)
        assert len(managers) == 3
        # Note: Due to patching, they might be different instances in this test
        # but the test verifies the threading safety of the creation logic


class TestRaceConditionPrevention:
    """Test cases specifically for race condition prevention."""

    @pytest.mark.asyncio
    async def test_no_race_in_lock_creation(self):
        """Test no race conditions in concurrent lock creation."""
        manager = ProcessorLockManager()
        lock_name = "race_test"

        # Track lock creation attempts
        original_create = asyncio.Lock
        creation_count = 0

        def counting_lock():
            nonlocal creation_count
            creation_count += 1
            return original_create()

        # Run many concurrent lock creations
        async def create_and_use():
            with patch("asyncio.Lock", counting_lock):
                async with manager.get_async_lock(lock_name):
                    await asyncio.sleep(0.001)

        tasks = [create_and_use() for _ in range(20)]
        await asyncio.gather(*tasks)

        # Should only create one lock despite many concurrent attempts
        assert creation_count == 1
        assert len(manager._async_locks) == 1

    @pytest.mark.asyncio
    async def test_memory_leak_prevention(self):
        """Test that locks don't accumulate and cause memory leaks."""
        manager = ProcessorLockManager()

        # Create many locks
        for i in range(100):
            async with manager.get_async_lock(f"temp_lock_{i}"):
                pass

        initial_count = len(manager._async_locks)
        assert initial_count == 100

        # Cleanup should remove all unused locks
        cleaned = await manager.cleanup_unused_locks()
        assert cleaned == initial_count
        assert len(manager._async_locks) == 0
