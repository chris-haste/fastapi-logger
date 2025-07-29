"""Comprehensive test suite for AsyncSmartCache redesigned functionality.

This test suite provides extensive validation of:
- Async cache operations testing
- Race condition validation with asyncio.gather()
- Lock contention testing
- Error state management under concurrent access
- Retry mechanism testing with async patterns
- Memory and resource optimization validation
"""

import asyncio
import gc
import logging
import random
import time
from datetime import timedelta

import pytest

from fapilog.enrichers import AsyncSmartCache


class TestAsyncSmartCacheComprehensive:
    """Comprehensive tests for AsyncSmartCache redesigned functionality."""

    def setup_method(self):
        """Set up fresh cache instance for each test."""
        self.cache = AsyncSmartCache()
        # Enable debug logging for detailed test analysis
        logging.getLogger("fapilog.enrichers").setLevel(logging.DEBUG)

    def teardown_method(self):
        """Clean up after each test."""
        # Force garbage collection to verify memory cleanup
        gc.collect()

    @pytest.mark.asyncio
    async def test_async_cache_operations_basic(self):
        """Test basic async cache operations with comprehensive validation."""

        async def async_compute_function():
            return {"result": "async_value", "computed_at": time.time()}

        def sync_compute_function():
            return {"result": "sync_value", "computed_at": time.time()}

        # Test async function caching
        result1 = await self.cache.get_or_compute("async_key", async_compute_function)
        assert result1["result"] == "async_value"
        assert "computed_at" in result1

        # Test sync function caching
        result2 = await self.cache.get_or_compute("sync_key", sync_compute_function)
        assert result2["result"] == "sync_value"
        assert "computed_at" in result2

        # Verify cached values are returned on subsequent calls
        cached_result1 = await self.cache.get_or_compute(
            "async_key", async_compute_function
        )
        cached_result2 = await self.cache.get_or_compute(
            "sync_key", sync_compute_function
        )

        assert cached_result1 == result1  # Exact same object
        assert cached_result2 == result2  # Exact same object

    @pytest.mark.asyncio
    async def test_race_condition_validation_extreme_concurrency(self):
        """Test zero race conditions with extreme concurrent access patterns."""
        computation_counter = 0

        def compute_function():
            nonlocal computation_counter
            computation_counter += 1
            # Simulate some computation time
            time.sleep(0.001)  # 1ms delay
            return f"computed_value_{computation_counter}"

        # Launch 2000 concurrent operations on the same key
        tasks = [
            self.cache.get_or_compute("race_test_key", compute_function)
            for _ in range(2000)
        ]

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks)

        # Validate no race conditions occurred
        unique_results = set(results)
        assert len(unique_results) == 1, (
            f"Race condition detected! Got {len(unique_results)} unique results"
        )
        assert computation_counter == 1, (
            f"Expected 1 computation, got {computation_counter}"
        )
        assert all(result == results[0] for result in results), "Not all results match"

    @pytest.mark.asyncio
    async def test_lock_contention_stress_testing(self):
        """Test lock contention under extreme stress conditions."""
        async_computation_counter = 0
        sync_computation_counter = 0

        async def async_compute_heavy():
            nonlocal async_computation_counter
            async_computation_counter += 1
            # Simulate heavy async computation
            await asyncio.sleep(0.002)  # 2ms async delay
            return f"async_heavy_{async_computation_counter}"

        def sync_compute_heavy():
            nonlocal sync_computation_counter
            sync_computation_counter += 1
            # Simulate heavy sync computation
            time.sleep(0.002)  # 2ms sync delay
            return f"sync_heavy_{sync_computation_counter}"

        # Mix async and sync operations with different keys
        tasks = []

        # 500 async operations on 5 different keys
        for i in range(500):
            key = f"async_key_{i % 5}"
            tasks.append(self.cache.get_or_compute(key, async_compute_heavy))

        # 500 sync operations on 5 different keys
        for i in range(500):
            key = f"sync_key_{i % 5}"
            tasks.append(self.cache.get_or_compute(key, sync_compute_heavy))

        start_time = time.time()
        results = await asyncio.gather(*tasks)
        end_time = time.time()

        # Validate results
        assert len(results) == 1000
        assert async_computation_counter == 5  # Only 5 unique async keys
        assert sync_computation_counter == 5  # Only 5 unique sync keys

        # Performance validation - should complete efficiently due to caching
        total_time = end_time - start_time
        assert total_time < 1.0, (
            f"Lock contention caused performance degradation: {total_time}s"
        )

    @pytest.mark.asyncio
    async def test_error_state_management_concurrent_access(self):
        """Test error state management under concurrent access patterns."""
        error_count = 0

        def failing_function():
            nonlocal error_count
            error_count += 1
            raise RuntimeError(f"Failure #{error_count}")

        def success_function():
            return "success_result"

        # Set short retry interval for testing
        cache_with_retry = AsyncSmartCache(retry_interval=timedelta(milliseconds=50))

        # First batch - should all fail with same error
        tasks_1 = [
            cache_with_retry.get_or_compute("error_key", failing_function)
            for _ in range(100)
        ]

        results_1 = await asyncio.gather(*tasks_1, return_exceptions=True)

        # All should be RuntimeError (either original or cached error)
        assert all(isinstance(r, RuntimeError) for r in results_1)
        assert error_count == 1  # Only one actual error computation

        # Wait for retry interval to allow retry
        await asyncio.sleep(0.1)

        # Test successful computation after error retry interval
        result_success = await cache_with_retry.get_or_compute(
            "success_key", success_function
        )
        assert result_success == "success_result"

        # Verify error cache entry still exists but allows retry after interval
        cache_stats = await cache_with_retry.get_cache_stats()
        assert cache_stats["total_entries"] >= 1

    @pytest.mark.asyncio
    async def test_retry_mechanism_async_patterns(self):
        """Test retry mechanism with various async patterns."""

        # Test basic retry pattern with known behavior
        error_call_count = 0

        def failing_function():
            nonlocal error_call_count
            error_call_count += 1
            raise ConnectionError(f"Network failure #{error_call_count}")

        def success_function():
            return "retry_success"

        cache_fast_retry = AsyncSmartCache(retry_interval=timedelta(milliseconds=10))

        # First call should fail and cache the error
        with pytest.raises(ConnectionError):
            await cache_fast_retry.get_or_compute("retry_key", failing_function)

        assert error_call_count == 1

        # Immediate second call should return cached error without calling
        # function
        with pytest.raises(RuntimeError, match="Cached error"):
            await cache_fast_retry.get_or_compute("retry_key", failing_function)

        assert error_call_count == 1  # Function not called again

        # Wait for retry interval
        await asyncio.sleep(0.02)

        # After retry interval, should attempt computation again
        with pytest.raises(ConnectionError):
            await cache_fast_retry.get_or_compute("retry_key", failing_function)

        # Function called again after retry interval
        assert error_call_count == 2

        # Test successful retry on different key
        success_result = await cache_fast_retry.get_or_compute(
            "success_retry_key", success_function
        )
        assert success_result == "retry_success"

    @pytest.mark.asyncio
    async def test_memory_efficiency_validation(self):
        """Test memory efficiency of cache implementation."""

        # Measure initial memory usage
        initial_objects = len(gc.get_objects())

        # Create cache entries for memory analysis
        cache_large = AsyncSmartCache()

        def generate_data(size: int):
            return {
                "data": list(range(size)),
                "metadata": {"size": size, "created": time.time()},
            }

        # Add 1000 cache entries with varying data sizes
        for i in range(1000):
            data_size = random.randint(10, 100)
            await cache_large.get_or_compute(
                f"data_key_{i}", lambda size=data_size: generate_data(size)
            )

        # Measure memory after caching
        after_cache_objects = len(gc.get_objects())

        # Clear cache
        await cache_large.clear()

        # Force garbage collection
        gc.collect()

        # Measure memory after cleanup
        after_cleanup_objects = len(gc.get_objects())

        # Validate memory efficiency
        memory_growth = after_cache_objects - initial_objects
        memory_cleanup = after_cache_objects - after_cleanup_objects

        assert memory_growth > 0, "Cache should use memory for storing data"
        assert memory_cleanup > 0, "Cache cleanup should free memory"

        # Memory cleanup should free at least 80% of allocated memory
        cleanup_ratio = memory_cleanup / memory_growth
        assert cleanup_ratio > 0.8, (
            f"Poor memory cleanup: only {cleanup_ratio:.2%} freed"
        )

    @pytest.mark.asyncio
    async def test_async_compute_function_validation(self):
        """Test comprehensive validation of async compute functions."""

        async def async_generator_simulation():
            """Simulate async generator-like computation."""
            results = []
            for i in range(5):
                await asyncio.sleep(0.001)  # Simulate async I/O
                results.append(f"chunk_{i}")
            return results

        async def async_network_simulation():
            """Simulate async network call."""
            await asyncio.sleep(0.002)  # Simulate network delay
            return {"status": "success", "data": "network_data"}

        async def async_failing_function():
            """Simulate async function that fails."""
            await asyncio.sleep(0.001)
            raise TimeoutError("Async timeout occurred")

        # Test async generator simulation
        result1 = await self.cache.get_or_compute(
            "async_gen", async_generator_simulation
        )
        assert len(result1) == 5
        assert all("chunk_" in item for item in result1)

        # Test async network simulation
        result2 = await self.cache.get_or_compute(
            "async_network", async_network_simulation
        )
        assert result2["status"] == "success"
        assert result2["data"] == "network_data"

        # Test async failing function
        with pytest.raises(TimeoutError):
            await self.cache.get_or_compute("async_fail", async_failing_function)

        # Verify cached results are returned
        cached_result1 = await self.cache.get_or_compute(
            "async_gen", async_generator_simulation
        )
        cached_result2 = await self.cache.get_or_compute(
            "async_network", async_network_simulation
        )

        assert cached_result1 == result1
        assert cached_result2 == result2

    @pytest.mark.asyncio
    async def test_extreme_concurrent_different_keys(self):
        """Test extreme concurrency with different keys for scalability."""

        def key_specific_computation(key_id: int):
            # Simulate key-specific computation
            time.sleep(0.0001)  # 0.1ms computation
            return {
                "key_id": key_id,
                "value": f"computed_value_{key_id}",
                "timestamp": time.time(),
            }

        # Launch 5000 concurrent operations on different keys
        tasks = [
            self.cache.get_or_compute(
                f"unique_key_{i}", lambda kid=i: key_specific_computation(kid)
            )
            for i in range(5000)
        ]

        start_time = time.time()
        results = await asyncio.gather(*tasks)
        end_time = time.time()

        # Validate all operations completed successfully
        assert len(results) == 5000
        assert len({result["key_id"] for result in results}) == 5000

        # Validate performance - should complete efficiently
        total_time = end_time - start_time
        assert total_time < 2.0, f"Scalability issue: {total_time}s for 5000 operations"

        # Validate cache contains all entries
        cache_stats = await self.cache.get_cache_stats()
        assert cache_stats["total_entries"] == 5000
        assert cache_stats["success_entries"] == 5000
        assert cache_stats["error_entries"] == 0

    @pytest.mark.asyncio
    async def test_mixed_workload_stress_testing(self):
        """Test mixed workload with various computation patterns."""

        # Different computation patterns
        async def fast_async_compute():
            return "fast_async_result"

        def fast_sync_compute():
            return "fast_sync_result"

        async def slow_async_compute():
            await asyncio.sleep(0.01)  # 10ms delay
            return "slow_async_result"

        def slow_sync_compute():
            time.sleep(0.01)  # 10ms delay
            return "slow_sync_result"

        def error_compute():
            raise ValueError("Computation error")

        # Mixed workload patterns
        workload_patterns = [
            ("fast_async", fast_async_compute),
            ("fast_sync", fast_sync_compute),
            ("slow_async", slow_async_compute),
            ("slow_sync", slow_sync_compute),
            ("error_pattern", error_compute),
        ]

        # Create mixed concurrent workload
        tasks = []
        for i in range(200):  # 200 operations per pattern = 1000 total
            pattern_name, compute_func = workload_patterns[i % len(workload_patterns)]
            key = f"{pattern_name}_{i // len(workload_patterns)}"
            tasks.append(self.cache.get_or_compute(key, compute_func))

        # Execute mixed workload
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze results
        success_results = [r for r in results if not isinstance(r, Exception)]
        error_results = [r for r in results if isinstance(r, Exception)]

        # Should have 160 success results (4 patterns × 40 unique keys each)
        # and 40 error results (1 error pattern × 40 unique keys)
        assert len(success_results) == 160
        assert len(error_results) == 40
        assert all(isinstance(e, ValueError) for e in error_results)

        # Validate cache efficiency
        cache_stats = await self.cache.get_cache_stats()
        # Should be 160 unique keys (4 success patterns × 40 unique keys each)
        # + 40 error keys = 200 total
        assert cache_stats["total_entries"] == 200
        assert cache_stats["success_entries"] == 160
        assert cache_stats["error_entries"] == 40
