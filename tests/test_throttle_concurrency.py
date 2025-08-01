"""Concurrency tests for optimized ThrottleProcessor.

This module tests concurrent access patterns, async-safe operations,
and race condition prevention in the optimized implementation.
"""

import asyncio
import random
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from fapilog._internal.throttle_processor import ThrottleProcessor


@pytest.mark.asyncio
class TestThrottleProcessorConcurrency:
    """Test concurrent access patterns and async safety."""

    @pytest.fixture
    def concurrency_processor(self):
        """Create processor for concurrency testing."""
        return ThrottleProcessor(
            max_rate=20,
            window_seconds=60,
            max_cache_size=100,
        )

    async def test_concurrent_same_key_throttling(
        self, concurrency_processor: ThrottleProcessor
    ) -> None:
        """Test concurrent access to same throttling key."""
        processor = concurrency_processor
        await processor.start()

        async def worker(worker_id: int) -> list[bool]:
            """Worker that processes events for the same key."""
            results = []
            for i in range(10):
                event = {
                    "source": "shared_key",  # Same key for all workers
                    "message": f"worker_{worker_id}_event_{i}",
                }
                result = await processor.process_async(None, "info", event)
                results.append(result is not None)
            return results

        # Run 10 concurrent workers accessing same key
        tasks = [worker(i) for i in range(10)]
        worker_results = await asyncio.gather(*tasks)

        # Count total allowed events across all workers
        total_allowed = sum(sum(results) for results in worker_results)

        # Should respect rate limit despite concurrent access
        assert total_allowed <= processor.max_rate, (
            f"Rate limit violated: {total_allowed} > {processor.max_rate}"
        )
        assert total_allowed > 0, "At least some events should be allowed"

        await processor.stop()

    async def test_concurrent_different_keys(
        self, concurrency_processor: ThrottleProcessor
    ) -> None:
        """Test concurrent access to different throttling keys."""
        processor = concurrency_processor
        await processor.start()

        async def worker(worker_id: int) -> None:
            """Worker that processes events for unique keys."""
            for i in range(5):
                event = {
                    "source": f"unique_key_{worker_id}",
                    "message": f"event_{i}",
                }
                result = await processor.process_async(None, "info", event)
                assert result is not None, "Unique keys should not throttle each other"

        # Run 20 concurrent workers with unique keys
        tasks = [worker(i) for i in range(20)]
        await asyncio.gather(*tasks)

        # Verify all keys are tracked
        stats = await processor.get_cache_stats()
        assert stats["tracked_keys"] == 20

        await processor.stop()

    async def test_mixed_concurrent_access(self, concurrency_processor):
        """Test mixed concurrent access patterns."""
        processor = concurrency_processor
        await processor.start()

        async def mixed_worker(worker_id: int) -> None:
            """Worker with mixed access patterns."""
            for i in range(20):
                # 50% chance to use shared key, 50% unique key
                if random.random() < 0.5:
                    source = "shared_key"
                else:
                    source = f"unique_{worker_id}_{i}"

                event = {"source": source, "message": f"mixed_event_{i}"}
                await processor.process_async(None, "info", event)

        # Run 15 concurrent workers with mixed patterns
        tasks = [mixed_worker(i) for i in range(15)]
        await asyncio.gather(*tasks)

        # Should handle mixed patterns without errors
        stats = await processor.get_cache_stats()
        assert stats["tracked_keys"] > 0
        assert stats["cache_utilization"] >= 0

        await processor.stop()

    async def test_concurrent_cache_operations(self, concurrency_processor):
        """Test concurrent cache operations for data consistency."""
        processor = concurrency_processor
        await processor.start()

        results = []

        async def cache_worker(worker_id: int) -> list[bool]:
            """Worker that performs intensive cache operations."""
            worker_results = []
            for i in range(50):
                event = {
                    "source": f"cache_key_{i % 10}",  # 10 shared keys
                    "message": f"worker_{worker_id}_event_{i}",
                }
                result = await processor.process_async(None, "info", event)
                worker_results.append(result)

                # Occasionally check cache stats
                if i % 10 == 0:
                    await processor.get_cache_stats()

            return worker_results

        # Run 12 concurrent workers
        tasks = [cache_worker(i) for i in range(12)]
        worker_results = await asyncio.gather(*tasks)

        # Verify cache consistency
        stats = await processor.get_cache_stats()
        assert stats["tracked_keys"] <= 10  # Should have at most 10 keys
        assert stats["cache_utilization"] >= 0

        # Verify no data corruption
        for results in worker_results:
            for result in results:
                assert result is None or isinstance(result, dict)

        await processor.stop()

    async def test_concurrent_start_stop(self):
        """Test concurrent start/stop operations."""
        processor = ThrottleProcessor(max_rate=10, window_seconds=60)

        async def start_stop_worker():
            """Worker that starts and stops processor."""
            await processor.start()
            await asyncio.sleep(0.1)
            await processor.stop()

        async def event_worker():
            """Worker that processes events during start/stop."""
            for i in range(10):
                event = {"source": "test", "message": f"event_{i}"}
                try:
                    await processor.process_async(None, "info", event)
                except Exception:
                    pass  # Expected during start/stop transitions
                await asyncio.sleep(0.05)

        # Run concurrent start/stop and event processing
        start_stop_tasks = [start_stop_worker() for _ in range(3)]
        event_tasks = [event_worker() for _ in range(2)]

        await asyncio.gather(*start_stop_tasks, *event_tasks)

        # Should not crash or corrupt state
        await processor.start()
        stats = await processor.get_cache_stats()
        assert isinstance(stats, dict)
        await processor.stop()

    async def test_concurrent_cleanup_operations(self, concurrency_processor):
        """Test concurrent cleanup operations."""
        processor = concurrency_processor
        await processor.start()

        async def cleanup_trigger_worker():
            """Worker that triggers cleanup operations."""
            for i in range(30):
                event = {
                    "source": f"cleanup_source_{i}",
                    "message": f"cleanup_event_{i}",
                }
                await processor.process_async(None, "info", event)

        async def stats_worker():
            """Worker that requests stats during cleanup."""
            for _ in range(20):
                await processor.get_cache_stats()
                await processor.get_current_rates()
                await asyncio.sleep(0.05)

        # Run cleanup triggering and stats collection concurrently
        cleanup_tasks = [cleanup_trigger_worker() for _ in range(3)]
        stats_tasks = [stats_worker() for _ in range(2)]

        await asyncio.gather(*cleanup_tasks, *stats_tasks)

        # Should maintain consistency
        stats = await processor.get_cache_stats()
        assert stats["tracked_keys"] >= 0
        assert stats["cache_utilization"] >= 0

        await processor.stop()

    async def test_high_concurrency_stress(self, concurrency_processor):
        """Test high concurrency stress scenarios."""
        processor = concurrency_processor
        await processor.start()

        async def stress_worker(worker_id: int) -> tuple[int, int]:
            """High-intensity worker for stress testing."""
            operations = 0
            errors = 0

            for i in range(100):
                try:
                    event = {
                        "source": f"stress_{worker_id}_{i % 20}",
                        "message": f"stress_event_{i}",
                    }
                    await processor.process_async(None, "info", event)
                    operations += 1

                    # Random stats checking
                    if random.random() < 0.1:
                        await processor.get_cache_stats()

                except Exception:
                    errors += 1

            return operations, errors

        # Run 25 high-intensity concurrent workers
        tasks = [stress_worker(i) for i in range(25)]
        results = await asyncio.gather(*tasks)

        total_operations = sum(ops for ops, _ in results)
        total_errors = sum(errors for _, errors in results)
        error_rate = total_errors / total_operations if total_operations > 0 else 0

        print(f"Stress test: {total_operations} ops, {total_errors} errors")
        print(f"Error rate: {error_rate:.2%}")

        # Should handle high concurrency with low error rate
        assert total_operations > 2000, "Should complete significant operations"
        assert error_rate < 0.05, f"Error rate {error_rate:.2%} too high"

        # Verify final state consistency
        stats = await processor.get_cache_stats()
        assert isinstance(stats["tracked_keys"], int)
        assert stats["tracked_keys"] >= 0

        await processor.stop()


@pytest.mark.asyncio
class TestAsyncSafetyPatterns:
    """Test async safety patterns in the optimized implementation."""

    async def test_async_lock_safety(self):
        """Test async lock safety in LRU cache."""
        from fapilog._internal.lru_cache import LRUCache

        cache = LRUCache(maxsize=10)

        async def concurrent_cache_worker(worker_id: int) -> None:
            """Worker that performs concurrent cache operations."""
            for i in range(50):
                key = f"key_{i % 5}"  # Shared keys to test locking
                value = [time.time() + worker_id]

                # Concurrent put and get operations
                await cache.put(key, value)
                result = await cache.get(key)
                assert result is not None or key not in await cache.get_all_keys()

        # Run 10 concurrent workers
        tasks = [concurrent_cache_worker(i) for i in range(10)]
        await asyncio.gather(*tasks)

        # Cache should maintain consistency
        stats = cache.get_stats()
        assert stats["size"] <= 10  # Shouldn't exceed maxsize
        assert stats["hits"] + stats["misses"] > 0

    async def test_processor_async_safety(self):
        """Test processor-level async safety."""
        processor = ThrottleProcessor(
            max_rate=15,
            window_seconds=60,
            max_cache_size=50,
        )
        await processor.start()

        async def async_safety_worker(worker_id: int) -> None:
            """Worker testing async safety patterns."""
            for i in range(30):
                # Interleave different async operations
                event = {
                    "source": f"async_test_{i % 10}",
                    "message": f"worker_{worker_id}_event_{i}",
                }

                # Process event
                await processor.process_async(None, "info", event)

                # Interleave with stats operations
                if i % 5 == 0:
                    await processor.get_cache_stats()

                if i % 7 == 0:
                    await processor.get_current_rates()

        # Run many concurrent async workers
        tasks = [async_safety_worker(i) for i in range(20)]
        await asyncio.gather(*tasks)

        # Should maintain async safety
        final_stats = await processor.get_cache_stats()
        assert isinstance(final_stats, dict)
        assert final_stats["tracked_keys"] >= 0

        await processor.stop()

    async def test_mixed_sync_async_safety(self):
        """Test mixed sync/async operation safety."""
        processor = ThrottleProcessor(max_rate=10, window_seconds=60)
        await processor.start()

        results = []

        def sync_worker():
            """Sync worker using sync interface."""
            for i in range(20):
                event = {"source": f"sync_{i}", "message": f"sync_event_{i}"}
                result = processor.process(None, "info", event)
                results.append(("sync", result))

        async def async_worker():
            """Async worker using async interface."""
            for i in range(20):
                event = {"source": f"async_{i}", "message": f"async_event_{i}"}
                result = await processor.process_async(None, "info", event)
                results.append(("async", result))

        # Run sync workers in thread pool and async workers concurrently
        with ThreadPoolExecutor(max_workers=3) as executor:
            sync_futures = [executor.submit(sync_worker) for _ in range(3)]
            async_tasks = [async_worker() for _ in range(3)]

            # Wait for both sync and async operations
            await asyncio.gather(*async_tasks)
            for future in sync_futures:
                future.result()

        # Should handle mixed patterns safely
        sync_results = [r for r in results if r[0] == "sync"]
        async_results = [r for r in results if r[0] == "async"]

        assert len(sync_results) > 0, "Should have sync results"
        assert len(async_results) > 0, "Should have async results"

        # All results should be valid
        for _, result in results:
            assert result is None or isinstance(result, dict)

        await processor.stop()
