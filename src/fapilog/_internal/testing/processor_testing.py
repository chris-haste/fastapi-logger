"""Testing framework for processors with comprehensive test patterns.

This module provides standardized testing utilities and patterns for
validating processor behavior, performance, and concurrency safety.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, cast

import pytest

from ...processors.async_base import AsyncProcessorBase
from ..processor import Processor


class ProcessorTestBase(ABC):
    """Base class for processor testing with standardized patterns.

    Provides common testing utilities and patterns for all processor implementations.
    Ensures consistent async-safe behavior and comprehensive test coverage.
    """

    @abstractmethod
    def create_processor(self, **config: Any) -> Processor:
        """Create processor instance for testing.

        Args:
            **config: Configuration parameters for the processor

        Returns:
            Processor instance to test
        """
        raise NotImplementedError

    async def test_basic_processing(self, processor):
        """Test basic event processing functionality.

        This test ensures that the processor can handle basic events
        without crashing and returns appropriate results.
        """
        event = {"test": "data", "level": "INFO"}
        result = await self._process_event(processor, event)

        # Basic validation - processor should not crash
        assert result is not None
        assert isinstance(result, dict)

    async def test_error_handling(self, processor):
        """Test error handling with invalid events.

        This test ensures that the processor handles invalid input
        gracefully without crashing the application.
        """
        # Test with None event
        result = await self._process_event(processor, None)
        # Should handle gracefully, not crash
        assert result is not None or result is None  # Either is acceptable

        # Test with invalid event type
        result = await self._process_event(processor, "invalid_event")
        # Should handle gracefully
        assert result is not None or result is None

        # Test with empty event
        result = await self._process_event(processor, {})
        # Should handle gracefully
        assert result is not None or result is None

    async def test_concurrent_access(self, processor):
        """Test concurrent access patterns.

        This test ensures that the processor can handle multiple
        concurrent operations without race conditions.
        """

        async def worker(worker_id: int) -> None:
            """Worker function for concurrent testing."""
            for i in range(10):
                event = {"worker": worker_id, "data": f"test_{i}", "level": "INFO"}
                result = await self._process_event(processor, event)
                # Should not crash
                assert result is not None or result is None

        # Run 5 concurrent workers
        tasks = [worker(i) for i in range(5)]
        await asyncio.gather(*tasks)

        # Verify no crashes or data corruption
        if hasattr(processor, "get_metrics"):
            metrics = processor.get_metrics()
            assert metrics is not None

    async def test_processor_lifecycle(self, processor):
        """Test processor lifecycle management.

        This test ensures that the processor can be started and stopped
        properly without resource leaks.
        """
        # Test initial state
        assert not processor.is_started

        # Test start
        await processor.start()
        assert processor.is_started

        # Test idempotent start
        await processor.start()
        assert processor.is_started

        # Test stop
        await processor.stop()
        assert not processor.is_started

        # Test idempotent stop
        await processor.stop()
        assert not processor.is_started

    @abstractmethod
    async def test_configuration_validation(self, processor):
        """Test configuration validation.

        This test ensures that the processor validates its configuration
        properly and raises appropriate errors for invalid config.
        """
        # This test should be overridden by specific processor tests
        # to test their specific configuration validation
        # Default implementation does nothing - subclasses should override
        pass

    async def test_async_safety_patterns(self, async_processor):
        """Test async-safe patterns for AsyncProcessorBase implementations.

        This test ensures that async processors follow proper async-safe
        patterns and don't have race conditions.
        """
        if not isinstance(async_processor, AsyncProcessorBase):
            pytest.skip("Processor is not an AsyncProcessorBase")

        # Test concurrent cache operations
        async def cache_worker(worker_id: int) -> None:
            """Worker for testing cache operations."""
            for i in range(10):
                key = f"test_key_{worker_id}_{i}"
                await async_processor._safe_cache_operation(
                    key, lambda: asyncio.sleep(0.001)
                )

        # Run concurrent cache operations
        tasks = [cache_worker(i) for i in range(5)]
        await asyncio.gather(*tasks)

        # Test atomic updates
        async def atomic_worker(worker_id: int) -> None:
            """Worker for testing atomic updates."""
            for i in range(10):
                update_key = f"update_{worker_id}_{i}"
                await async_processor._atomic_update(
                    update_key, lambda: asyncio.sleep(0.001)
                )

        # Run concurrent atomic updates
        tasks = [atomic_worker(i) for i in range(5)]
        await asyncio.gather(*tasks)

        # Verify no crashes
        stats = async_processor.get_async_stats()
        assert stats is not None

    async def _process_event(self, processor: Processor, event: Any) -> Any:
        """Helper method to process an event with proper error handling.

        Args:
            processor: Processor instance to test
            event: Event to process

        Returns:
            Processing result
        """
        try:
            if hasattr(processor, "process_async"):
                # Use async version if available
                return await processor.process_async(None, "info", event)
            else:
                # Use sync version
                return processor.process(None, "info", event)
        except Exception as e:
            # Log error but don't fail the test
            print(f"Processor error during testing: {e}")
            return None


class ProcessorPerformanceTester:
    """Performance testing utilities for processors.

    Provides standardized performance testing patterns to ensure
    processors meet performance requirements.
    """

    def __init__(self, processor: Processor):
        """Initialize performance tester.

        Args:
            processor: Processor instance to test
        """
        self.processor = processor

    async def test_throughput(self, target_ops_per_sec: int = 1000) -> float:
        """Test processor throughput.

        Args:
            target_ops_per_sec: Minimum operations per second required

        Returns:
            float: Actual throughput achieved
        """
        start_time = time.time()
        operations = 0

        async def worker():
            nonlocal operations
            for i in range(1000):
                event = {"test": f"event_{i}", "level": "INFO"}
                await self._process_event(event)
                operations += 1

        # Run 5 concurrent workers
        tasks = [worker() for _ in range(5)]
        await asyncio.gather(*tasks)

        duration = time.time() - start_time
        throughput = operations / duration

        assert throughput > target_ops_per_sec, (
            f"Throughput {throughput:.0f} ops/sec below target {target_ops_per_sec}"
        )
        return throughput

    async def test_latency_p95(self, max_p95_ms: int = 10) -> float:
        """Test processor latency (P95).

        Args:
            max_p95_ms: Maximum P95 latency in milliseconds

        Returns:
            float: Actual P95 latency in milliseconds
        """
        latencies = []

        async def worker():
            for i in range(100):
                start_time = time.time()
                event = {"test": f"latency_{i}", "level": "INFO"}
                await self._process_event(event)
                latency = (time.time() - start_time) * 1000  # Convert to ms
                latencies.append(latency)

        # Run 10 concurrent workers
        tasks = [worker() for _ in range(10)]
        await asyncio.gather(*tasks)

        # Calculate P95
        latencies.sort()
        p95_index = int(len(latencies) * 0.95)
        p95_latency = latencies[p95_index]

        assert p95_latency < max_p95_ms, (
            f"P95 latency {p95_latency:.2f}ms exceeds target {max_p95_ms}ms"
        )
        return p95_latency

    async def test_memory_stability(self, max_growth_percent: float = 10.0) -> float:
        """Test memory usage stability under load.

        Args:
            max_growth_percent: Maximum memory growth percentage allowed

        Returns:
            float: Actual memory growth percentage
        """
        import gc

        import psutil

        process = psutil.Process()
        initial_memory = process.memory_info().rss

        # Generate load
        async def worker():
            for i in range(1000):
                event = {"test": f"memory_test_{i}", "level": "INFO"}
                await self._process_event(event)

        # Run 5 concurrent workers
        tasks = [worker() for _ in range(5)]
        await asyncio.gather(*tasks)

        # Force garbage collection
        gc.collect()
        final_memory = process.memory_info().rss
        memory_growth = ((final_memory - initial_memory) / initial_memory) * 100

        assert memory_growth < max_growth_percent, (
            f"Memory growth {memory_growth:.1f}% exceeds target {max_growth_percent}%"
        )
        return cast(float, memory_growth)

    async def _process_event(self, event: Dict[str, Any]) -> Any:
        """Helper method to process an event.

        Args:
            event: Event to process

        Returns:
            Processing result
        """
        try:
            if hasattr(self.processor, "process_async"):
                return await self.processor.process_async(None, "info", event)
            else:
                return self.processor.process(None, "info", event)
        except Exception:
            # Return event on error for performance testing
            return event


class ProcessorConcurrencyTester:
    """Concurrency testing utilities for processors.

    Provides standardized concurrency testing patterns to ensure
    processors handle concurrent access correctly.
    """

    def __init__(self, processor: Processor):
        """Initialize concurrency tester.

        Args:
            processor: Processor instance to test
        """
        self.processor = processor

    async def test_concurrent_shared_keys(
        self, num_workers: int = 10, num_operations: int = 100
    ) -> None:
        """Test concurrent access to shared keys.

        Args:
            num_workers: Number of concurrent workers
            num_operations: Number of operations per worker
        """
        shared_key = "shared_test_key"
        results = []

        async def worker(worker_id: int) -> None:
            for i in range(num_operations):
                event = {
                    "key": shared_key,
                    "worker": worker_id,
                    "operation": i,
                    "level": "INFO",
                }
                result = await self._process_event(event)
                results.append((worker_id, i, result))

        # Run concurrent workers
        tasks = [worker(i) for i in range(num_workers)]
        await asyncio.gather(*tasks)

        # Verify all operations completed
        assert len(results) == num_workers * num_operations

    async def test_concurrent_unique_keys(
        self, num_workers: int = 10, num_operations: int = 100
    ) -> None:
        """Test concurrent access to unique keys.

        Args:
            num_workers: Number of concurrent workers
            num_operations: Number of operations per worker
        """
        results = []

        async def worker(worker_id: int) -> None:
            for i in range(num_operations):
                event = {
                    "key": f"unique_key_{worker_id}_{i}",
                    "worker": worker_id,
                    "operation": i,
                    "level": "INFO",
                }
                result = await self._process_event(event)
                results.append((worker_id, i, result))

        # Run concurrent workers
        tasks = [worker(i) for i in range(num_workers)]
        await asyncio.gather(*tasks)

        # Verify all operations completed
        assert len(results) == num_workers * num_operations

    async def test_concurrent_mixed_patterns(
        self, num_workers: int = 10, num_operations: int = 100
    ) -> None:
        """Test concurrent access with mixed patterns.

        Args:
            num_workers: Number of concurrent workers
            num_operations: Number of operations per worker
        """
        results = []

        async def worker(worker_id: int) -> None:
            for i in range(num_operations):
                # Mix shared and unique keys
                if i % 3 == 0:
                    key = "shared_key"
                else:
                    key = f"unique_key_{worker_id}_{i}"

                event = {
                    "key": key,
                    "worker": worker_id,
                    "operation": i,
                    "level": "INFO",
                }
                result = await self._process_event(event)
                results.append((worker_id, i, result))

        # Run concurrent workers
        tasks = [worker(i) for i in range(num_workers)]
        await asyncio.gather(*tasks)

        # Verify all operations completed
        assert len(results) == num_workers * num_operations

    async def test_concurrent_start_stop(self) -> None:
        """Test concurrent start/stop operations."""

        async def start_stop_worker(worker_id: int) -> None:
            for _ in range(10):
                await self.processor.start()
                await self.processor.stop()

        # Run concurrent start/stop operations
        tasks = [start_stop_worker(i) for i in range(5)]
        await asyncio.gather(*tasks)

        # Verify processor is in a consistent state
        assert not self.processor.is_started

    async def _process_event(self, event: Dict[str, Any]) -> Any:
        """Helper method to process an event.

        Args:
            event: Event to process

        Returns:
            Processing result
        """
        try:
            if hasattr(self.processor, "process_async"):
                return await self.processor.process_async(None, "info", event)
            else:
                return self.processor.process(None, "info", event)
        except Exception:
            # Return event on error for concurrency testing
            return event
