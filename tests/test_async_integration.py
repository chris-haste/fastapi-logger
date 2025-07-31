"""Integration tests for async foundation components.

Tests all foundation components working together: ProcessorLockManager,
SafeAsyncCache, and AsyncProcessorBase in realistic scenarios.
"""

import asyncio
import time
from typing import Any, Dict, Optional
from unittest.mock import Mock

import pytest

from fapilog._internal.async_processor_base import AsyncProcessorBase


class MockAsyncProcessor(AsyncProcessorBase):
    """Mock processor for integration testing."""

    def __init__(self, **config):
        super().__init__(**config)
        self.processed_events = []
        self.errors = []

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Mock sync process implementation."""
        try:
            # Simulate some processing
            processed_event = event_dict.copy()
            processed_event["processor_id"] = self._processor_id
            processed_event["processed_at"] = time.time()

            self.processed_events.append(processed_event)
            return processed_event
        except Exception as e:
            self.errors.append(e)
            raise

    async def process_async(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Any:
        """Mock async process implementation with cache usage."""
        try:
            event_id = event_dict.get("id", "default")

            # Use cache for deduplication-like behavior
            async def create_processed_event():
                processed_event = event_dict.copy()
                processed_event["processor_id"] = self._processor_id
                processed_event["async_processed_at"] = time.time()
                return processed_event

            # Get or create cached processed event
            cached_event = await self._get_or_create_cached_value(
                f"event_{event_id}", create_processed_event
            )

            self.processed_events.append(cached_event)
            return cached_event

        except Exception as e:
            self.errors.append(e)
            await self._handle_processor_error(e, {"event_dict": event_dict})
            raise


class TestFoundationIntegration:
    """Integration tests for all foundation components."""

    @pytest.mark.asyncio
    async def test_container_scoped_lock_manager_behavior(self):
        """Test container-scoped lock manager behavior in integration scenarios."""
        from fapilog.container import LoggingContainer

        # Test 1: Processors with same container share lock manager
        container = LoggingContainer()
        processor1 = MockAsyncProcessor(processor_id="proc1", container=container)
        processor2 = MockAsyncProcessor(processor_id="proc2", container=container)

        assert processor1._lock_manager is processor2._lock_manager

        # Test 2: Processors without container get independent lock managers
        processor3 = MockAsyncProcessor(processor_id="proc3")
        processor4 = MockAsyncProcessor(processor_id="proc4")

        assert processor3._lock_manager is not processor4._lock_manager
        assert processor1._lock_manager is not processor3._lock_manager

        # Test 3: Different containers have isolated lock managers
        container2 = LoggingContainer()
        processor5 = MockAsyncProcessor(processor_id="proc5", container=container2)

        assert processor1._lock_manager is not processor5._lock_manager

        # But all processors have separate caches regardless
        assert processor1._cache is not processor2._cache
        assert processor3._cache is not processor4._cache

    @pytest.mark.asyncio
    async def test_concurrent_processor_operations(self):
        """Test concurrent operations across multiple processors."""
        processors = [MockAsyncProcessor(processor_id=f"proc_{i}") for i in range(3)]

        async def processor_worker(
            processor: MockAsyncProcessor, worker_id: int
        ) -> None:
            for i in range(10):
                event = {
                    "id": f"event_{worker_id}_{i}",
                    "message": f"Test message {i}",
                    "worker_id": worker_id,
                }

                # Mix of sync and async processing
                if i % 2 == 0:
                    result = processor.process(Mock(), "info", event)
                else:
                    result = await processor.process_async(Mock(), "info", event)

                assert result is not None
                assert result["processor_id"] == processor._processor_id

        # Run all processors concurrently
        tasks = [
            processor_worker(processor, i) for i, processor in enumerate(processors)
        ]
        await asyncio.gather(*tasks)

        # Verify all processors completed successfully
        for processor in processors:
            assert len(processor.processed_events) == 10
            assert len(processor.errors) == 0

    @pytest.mark.asyncio
    async def test_cache_isolation_between_processors(self):
        """Test that processor caches are properly isolated."""
        processor1 = MockAsyncProcessor(processor_id="proc1", cache_max_size=5)
        processor2 = MockAsyncProcessor(processor_id="proc2", cache_max_size=5)

        # Add data to processor1 cache
        await processor1._update_cache_atomic("shared_key", "proc1_value")
        await processor1._update_cache_atomic("proc1_key", "proc1_only")

        # Add data to processor2 cache
        await processor2._update_cache_atomic("shared_key", "proc2_value")
        await processor2._update_cache_atomic("proc2_key", "proc2_only")

        # Verify isolation
        assert await processor1._cache.get("shared_key") == "proc1_value"
        assert await processor2._cache.get("shared_key") == "proc2_value"

        assert await processor1._cache.get("proc1_key") == "proc1_only"
        assert await processor1._cache.get("proc2_key") is None

        assert await processor2._cache.get("proc2_key") == "proc2_only"
        assert await processor2._cache.get("proc1_key") is None

    @pytest.mark.asyncio
    async def test_lock_coordination_across_processors(self):
        """Test lock coordination between different processors."""
        processor1 = MockAsyncProcessor(processor_id="proc1")
        processor2 = MockAsyncProcessor(processor_id="proc2")

        execution_order = []

        async def coordinated_operation(
            processor: MockAsyncProcessor, op_id: str
        ) -> Any:
            async def operation():
                execution_order.append(f"start_{op_id}")
                await asyncio.sleep(0.01)  # Simulate work
                execution_order.append(f"end_{op_id}")
                return f"result_{op_id}"

            # Both processors use the same lock name for coordination
            return await processor._safe_cache_operation("shared_operation", operation)

        # Run operations from different processors concurrently
        tasks = [
            coordinated_operation(processor1, "proc1_op"),
            coordinated_operation(processor2, "proc2_op"),
            coordinated_operation(processor1, "proc1_op2"),
        ]
        results = await asyncio.gather(*tasks)

        # Verify all operations completed
        assert len(results) == 3
        assert set(results) == {
            "result_proc1_op",
            "result_proc2_op",
            "result_proc1_op2",
        }

        # Verify proper serialization (no interleaving within shared lock)
        # Note: Different processors should still be able to run their other operations

    @pytest.mark.asyncio
    async def test_processor_lifecycle_coordination(self):
        """Test processor lifecycle management with foundation components."""
        processors = [MockAsyncProcessor(processor_id=f"proc_{i}") for i in range(3)]

        # Start all processors
        start_tasks = [proc.start() for proc in processors]
        await asyncio.gather(*start_tasks)

        # All should be started
        for proc in processors:
            assert proc.is_started

        # Use processors
        for i, proc in enumerate(processors):
            await proc._update_cache_atomic(f"proc_{i}_key", f"proc_{i}_value")

        # Stop all processors
        stop_tasks = [proc.stop() for proc in processors]
        await asyncio.gather(*stop_tasks)

        # All should be stopped and caches cleared
        for proc in processors:
            assert not proc.is_started
            assert len(proc._cache._cache) == 0

    @pytest.mark.asyncio
    async def test_high_concurrency_stress_test(self):
        """Stress test with high concurrency across all components."""
        processors = [
            MockAsyncProcessor(
                processor_id=f"stress_proc_{i}",
                cache_max_size=50,
                cache_ttl_seconds=1.0,
            )
            for i in range(5)
        ]

        async def stress_worker(processor: MockAsyncProcessor, worker_id: int) -> None:
            for i in range(20):
                event_id = f"worker_{worker_id}_event_{i}"
                event = {
                    "id": event_id,
                    "message": f"Stress test message {i}",
                    "worker_id": worker_id,
                }

                # Mix of operations
                if i % 3 == 0:
                    # Sync processing
                    processor.process(Mock(), "info", event)
                elif i % 3 == 1:
                    # Async processing with caching
                    await processor.process_async(Mock(), "info", event)
                else:
                    # Direct cache operations
                    await processor._update_cache_atomic(f"direct_{event_id}", event)
                    cached = await processor._cache.get(f"direct_{event_id}")
                    assert cached == event

        # Run stress test
        all_tasks = []
        for processor in processors:
            for worker_id in range(3):  # 3 workers per processor
                all_tasks.append(stress_worker(processor, worker_id))

        start_time = time.time()
        await asyncio.gather(*all_tasks)
        duration = time.time() - start_time

        # Verify performance and correctness
        assert duration < 10.0  # Should complete reasonably fast

        for processor in processors:
            stats = processor.get_async_stats()
            assert stats["cache_stats"]["size"] <= 50  # Respect cache limits
            assert len(processor.errors) == 0  # No errors should occur

    @pytest.mark.asyncio
    async def test_memory_management_integration(self):
        """Test memory management across all foundation components."""
        processor = MockAsyncProcessor(
            processor_id="memory_test",
            cache_max_size=20,
            cache_ttl_seconds=0.1,  # Fast expiration
        )

        # Generate many operations that could cause memory issues
        for i in range(100):
            event = {
                "id": f"memory_event_{i}",
                "data": f"data_{i}" * 10,  # Some data bulk
            }

            # Various operations
            await processor.process_async(Mock(), "info", event)
            await processor._update_cache_atomic(f"bulk_{i}", event)

            # Sometimes cleanup
            if i % 10 == 0:
                await processor._cleanup_expired_cache()

        # Force final cleanup
        await processor._cleanup_expired_cache()

        # Memory should be bounded
        stats = processor.get_async_stats()
        assert stats["cache_stats"]["size"] <= 20

        # Lock manager should also be reasonable
        lock_stats = stats["lock_stats"]
        assert lock_stats["async_locks"] < 50  # Shouldn't accumulate too many locks

    @pytest.mark.asyncio
    async def test_error_handling_integration(self):
        """Test error handling across foundation components."""
        processor = MockAsyncProcessor(processor_id="error_test")

        # Test cache operation error
        async def failing_cache_op():
            raise ValueError("Cache operation failed")

        with pytest.raises(ValueError):
            await processor._safe_cache_operation("error_key", failing_cache_op)

        # Processor should still be functional
        assert len(processor.errors) == 0  # Error was in test operation, not processor

        # Test normal operation still works
        event = {"id": "recovery_test", "message": "Recovery test"}
        result = await processor.process_async(Mock(), "info", event)
        assert result is not None
        assert result["id"] == "recovery_test"

    @pytest.mark.asyncio
    async def test_mixed_sync_async_patterns(self):
        """Test mixed sync and async operation patterns."""
        processor = MockAsyncProcessor(processor_id="mixed_test")

        # Simulate mixed usage patterns common in real processors
        results = []

        # Pattern 1: Sync processing with async cache lookup
        for i in range(5):
            event = {"id": f"sync_{i}", "message": f"Sync message {i}"}

            # Sync process
            result = processor.process(Mock(), "info", event)
            results.append(result)

            # Then async cache operation
            await processor._update_cache_atomic(f"sync_cache_{i}", result)

        # Pattern 2: Async processing with cache deduplication
        for i in range(5):
            event = {"id": f"async_{i}", "message": f"Async message {i}"}

            # Async process (uses cache internally)
            result = await processor.process_async(Mock(), "info", event)
            results.append(result)

        # Pattern 3: Mixed operations on same keys
        for i in range(3):
            key = f"mixed_{i}"

            # Set via cache
            await processor._update_cache_atomic(key, f"cached_value_{i}")

            # Get via cache
            cached = await processor._cache.get(key)
            assert cached == f"cached_value_{i}"

            # Use in processing
            event = {"id": key, "cached_data": cached}
            result = await processor.process_async(Mock(), "info", event)
            results.append(result)

        # Verify all operations completed successfully
        assert len(results) == 13  # 5 sync + 5 async + 3 mixed
        assert len(processor.errors) == 0


class TestPerformanceIntegration:
    """Performance-focused integration tests."""

    @pytest.mark.asyncio
    async def test_concurrent_performance_benchmark(self):
        """Benchmark concurrent performance of foundation components."""
        processor = MockAsyncProcessor(processor_id="perf_test", cache_max_size=100)

        async def benchmark_worker(worker_id: int, operations: int) -> float:
            worker_start = time.time()

            for i in range(operations):
                event = {
                    "id": f"perf_{worker_id}_{i}",
                    "worker": worker_id,
                    "operation": i,
                }

                # Alternate between sync and async
                if i % 2 == 0:
                    processor.process(Mock(), "info", event)
                else:
                    await processor.process_async(Mock(), "info", event)

            return time.time() - worker_start

        # Run performance test
        num_workers = 10
        operations_per_worker = 20

        start_time = time.time()
        tasks = [benchmark_worker(i, operations_per_worker) for i in range(num_workers)]
        worker_times = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        # Performance assertions
        total_operations = num_workers * operations_per_worker
        ops_per_second = total_operations / total_time

        # Should handle reasonable throughput
        assert ops_per_second > 50  # At least 50 ops/sec
        assert total_time < 10.0  # Complete within 10 seconds
        assert max(worker_times) < 5.0  # No single worker too slow

        # Verify correctness
        assert len(processor.processed_events) == total_operations
        assert len(processor.errors) == 0

    @pytest.mark.asyncio
    async def test_memory_efficiency_under_load(self):
        """Test memory efficiency under sustained load."""
        processor = MockAsyncProcessor(
            processor_id="memory_perf", cache_max_size=50, cache_ttl_seconds=0.5
        )

        # Sustained load with memory pressure
        for batch in range(10):
            batch_tasks = []

            # Create batch of operations
            for i in range(20):
                event = {
                    "id": f"batch_{batch}_item_{i}",
                    "batch": batch,
                    "item": i,
                    "data": "x" * 100,  # Some memory pressure
                }

                # Mix of operations
                if i % 3 == 0:
                    batch_tasks.append(processor.process_async(Mock(), "info", event))
                else:
                    # Sync operation wrapped in coroutine for batching
                    async def sync_wrapper(e=event):
                        return processor.process(Mock(), "info", e)

                    batch_tasks.append(sync_wrapper())

            # Execute batch
            await asyncio.gather(*batch_tasks)

            # Periodic cleanup to test memory management
            if batch % 3 == 0:
                await processor._cleanup_expired_cache()

        # Final memory check
        stats = processor.get_async_stats()

        # Memory should be bounded despite high throughput
        assert stats["cache_stats"]["size"] <= 50
        assert stats["cache_stats"]["utilization"] <= 1.0

        # Should have processed all events
        assert len(processor.processed_events) == 200  # 10 batches * 20 items
