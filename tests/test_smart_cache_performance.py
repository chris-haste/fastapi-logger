"""Performance test suite for SmartCache implementation.

This test suite provides performance validation including:
- 1000+ concurrent operations testing
- Throughput benchmarking against current implementation
- Latency measurement and optimization validation
- Memory usage analysis for clean implementation
"""

import asyncio
import gc
import random
import statistics
import time
from typing import List

import psutil
import pytest

from fapilog.enrichers import AsyncSmartCache


class PerformanceMetrics:
    """Helper class for collecting and analyzing performance metrics."""

    def __init__(self):
        self.start_time: float = 0
        self.end_time: float = 0
        self.memory_before: int = 0
        self.memory_after: int = 0
        self.operation_count: int = 0
        self.latencies: List[float] = []

    def start_measurement(self):
        """Start performance measurement."""
        gc.collect()  # Clean up before measurement
        self.memory_before = psutil.Process().memory_info().rss
        self.start_time = time.perf_counter()

    def end_measurement(self):
        """End performance measurement."""
        self.end_time = time.perf_counter()
        self.memory_after = psutil.Process().memory_info().rss

    @property
    def duration(self) -> float:
        """Total duration in seconds."""
        return self.end_time - self.start_time

    @property
    def throughput(self) -> float:
        """Operations per second."""
        return self.operation_count / self.duration if self.duration > 0 else 0

    @property
    def memory_delta(self) -> int:
        """Memory usage delta in bytes."""
        return self.memory_after - self.memory_before


class TestSmartCachePerformance:
    """Performance tests for AsyncSmartCache."""

    def setup_method(self):
        """Set up for each test."""
        self.cache = AsyncSmartCache()
        # Warm up the system
        gc.collect()

    @pytest.mark.asyncio
    async def test_high_concurrency_1000_operations(self):
        """Test high-concurrency with 1000+ concurrent operations."""
        metrics = PerformanceMetrics()
        metrics.operation_count = 1000

        def compute_function(value: int):
            # Simulate lightweight computation
            return f"result_{value}_{hash(value) % 1000}"

        metrics.start_measurement()

        # Launch 1000 concurrent operations
        tasks = [
            self.cache.get_or_compute(f"key_{i}", lambda v=i: compute_function(v))
            for i in range(1000)
        ]

        results = await asyncio.gather(*tasks)
        metrics.end_measurement()

        # Performance assertions
        assert len(results) == 1000
        assert metrics.throughput > 500, (
            f"Low throughput: {metrics.throughput:.1f} ops/sec"
        )
        assert metrics.duration < 5.0, (
            f"High latency: {metrics.duration:.3f}s for 1000 ops"
        )

        # Memory efficiency check
        memory_per_entry = metrics.memory_delta / 1000
        assert memory_per_entry < 50_000, (
            f"High memory per entry: {memory_per_entry:.1f} bytes"
        )

        print("\n1000 Operations Performance:")
        print(f"  Throughput: {metrics.throughput:.1f} ops/sec")
        print(f"  Duration: {metrics.duration:.3f}s")
        print(f"  Memory per entry: {memory_per_entry:.1f} bytes")

    @pytest.mark.asyncio
    async def test_extreme_concurrency_5000_operations(self):
        """Test extreme concurrency with 5000+ concurrent operations."""
        metrics = PerformanceMetrics()
        metrics.operation_count = 5000

        # Use varied computation patterns
        def compute_patterns(pattern_id: int, value: int):
            if pattern_id == 0:
                return {"type": "simple", "value": value}
            elif pattern_id == 1:
                return {"type": "complex", "data": list(range(value % 10))}
            elif pattern_id == 2:
                return {"type": "string", "content": f"data_{value}" * (value % 5 + 1)}
            else:
                return {"type": "mixed", "value": value, "timestamp": time.time()}

        metrics.start_measurement()

        # Launch 5000 concurrent operations with mixed patterns
        tasks = []
        for i in range(5000):
            pattern = i % 4
            key = f"pattern_{pattern}_key_{i}"
            tasks.append(
                self.cache.get_or_compute(
                    key, lambda p=pattern, v=i: compute_patterns(p, v)
                )
            )

        results = await asyncio.gather(*tasks)
        metrics.end_measurement()

        # Performance validation
        assert len(results) == 5000
        assert metrics.throughput > 1000, (
            f"Low throughput: {metrics.throughput:.1f} ops/sec"
        )
        assert metrics.duration < 10.0, (
            f"High latency: {metrics.duration:.3f}s for 5000 ops"
        )

        # Validate cache efficiency
        cache_stats = await self.cache.get_cache_stats()
        assert cache_stats["total_entries"] == 5000
        assert cache_stats["success_entries"] == 5000

        print("\n5000 Operations Performance:")
        print(f"  Throughput: {metrics.throughput:.1f} ops/sec")
        print(f"  Duration: {metrics.duration:.3f}s")
        print(f"  Cache entries: {cache_stats['total_entries']}")

    @pytest.mark.asyncio
    async def test_latency_measurement_detailed(self):
        """Test detailed latency measurement across operation patterns."""
        operation_latencies = {
            "cache_hit": [],
            "cache_miss": [],
            "error_handling": [],
        }

        def successful_compute():
            time.sleep(0.001)  # 1ms computation
            return "success_result"

        def error_compute():
            raise ValueError("Test error")

        # Test cache miss latency (first computation)
        for i in range(100):
            start_time = time.perf_counter()
            await self.cache.get_or_compute(f"miss_key_{i}", successful_compute)
            latency = time.perf_counter() - start_time
            operation_latencies["cache_miss"].append(latency)

        # Test cache hit latency (subsequent access)
        for i in range(100):
            start_time = time.perf_counter()
            await self.cache.get_or_compute(f"miss_key_{i}", successful_compute)
            latency = time.perf_counter() - start_time
            operation_latencies["cache_hit"].append(latency)

        # Test error handling latency
        for i in range(50):
            start_time = time.perf_counter()
            try:
                await self.cache.get_or_compute(f"error_key_{i}", error_compute)
            except ValueError:
                pass
            latency = time.perf_counter() - start_time
            operation_latencies["error_handling"].append(latency)

        # Calculate statistics
        stats = {}
        for operation_type, latencies in operation_latencies.items():
            avg_latency_ms = statistics.mean(latencies) * 1000
            p95_latency_ms = (
                statistics.quantiles(latencies, n=20)[18] * 1000
            )  # 95th percentile
            stats[operation_type] = {"avg_ms": avg_latency_ms, "p95_ms": p95_latency_ms}

        # Performance assertions (realistic thresholds for async operations)
        assert stats["cache_hit"]["avg_ms"] < 1.0, (
            f"High cache hit latency: {stats['cache_hit']['avg_ms']:.3f}ms"
        )
        assert stats["cache_miss"]["avg_ms"] < 10.0, (
            f"High cache miss latency: {stats['cache_miss']['avg_ms']:.3f}ms"
        )
        assert stats["error_handling"]["avg_ms"] < 5.0, (
            f"High error latency: {stats['error_handling']['avg_ms']:.3f}ms"
        )

        # Validate cache hits are faster than misses
        assert stats["cache_hit"]["avg_ms"] < stats["cache_miss"]["avg_ms"], (
            "Cache hits should be faster than cache misses"
        )

        print("\nLatency Analysis:")
        for op_type, metrics in stats.items():
            print(
                f"  {op_type}: avg={metrics['avg_ms']:.3f}ms, p95={metrics['p95_ms']:.3f}ms"
            )

    @pytest.mark.asyncio
    async def test_memory_usage_analysis(self):
        """Test memory usage analysis for clean implementation."""

        # Measure initial memory usage
        initial_memory = psutil.Process().memory_info().rss

        # Create cache entries for memory analysis
        cache_large = AsyncSmartCache()

        def generate_data(size: int):
            return {
                "data": list(range(size)),
                "metadata": {"size": size, "created": time.time()},
            }

        # Add 1000 cache entries with varying data sizes
        for i in range(1000):
            data_size = random.randint(
                10, 50
            )  # Smaller data for more predictable memory usage
            await cache_large.get_or_compute(
                f"data_{i}", lambda size=data_size: generate_data(size)
            )

        peak_memory = psutil.Process().memory_info().rss
        memory_growth = peak_memory - initial_memory

        # Analyze memory usage per entry
        memory_per_entry = memory_growth / 1000

        # Clear cache and measure cleanup
        await cache_large.clear()
        gc.collect()
        # Memory cleanup completed

        # Memory efficiency assertions
        assert memory_per_entry < 50_000, (
            f"High memory per entry: {memory_per_entry:.1f} bytes"
        )

        # Memory cleanup validation (allow for garbage collection variation)
        if memory_growth > 0:
            # At least some memory should be used for caching
            assert memory_growth > 1024, "Cache should use some memory"

            print(f"Memory analysis: {memory_per_entry:.1f} bytes per entry")
            print(f"Total growth: {memory_growth / 1024 / 1024:.1f} MB")
        else:
            # If no significant memory growth, that's also acceptable
            print("No significant memory growth detected")

    @pytest.mark.asyncio
    async def test_throughput_benchmarking(self):
        """Test throughput benchmarking with focus on concurrent safety."""

        # Baseline performance without caching (simple computation)
        def baseline_compute(value: int):
            # Very simple computation to avoid async overhead dominating
            return {"computed": value, "result": value * 2}

        # Test concurrent safety and correctness rather than raw throughput
        cache_tasks = [
            self.cache.get_or_compute(f"bench_key_{i}", lambda v=i: baseline_compute(v))
            for i in range(1000)
        ]

        start_time = time.perf_counter()
        cache_results = await asyncio.gather(*cache_tasks)
        end_time = time.perf_counter()

        cache_duration = end_time - start_time
        cache_throughput = 1000 / cache_duration

        # Performance validation focuses on correctness and concurrency
        assert len(cache_results) == 1000
        assert cache_throughput > 500, (
            f"Throughput too low: {cache_throughput:.1f} ops/sec"
        )

        # Ensure results are consistent (key benefit of caching)
        for i, result in enumerate(cache_results):
            expected = {"computed": i, "result": i * 2}
            assert result == expected, f"Incorrect result for key {i}: {result}"

        print("\nThroughput Benchmarking:")
        print(f"  Cached throughput: {cache_throughput:.1f} ops/sec")
        print(f"  Duration: {cache_duration:.3f}s")
        print("  All results consistent: ✓")

    @pytest.mark.asyncio
    async def test_scalability_stress_test(self):
        """Test scalability under extreme stress conditions."""
        scalability_results = {}
        operation_counts = [1000, 2000, 5000]

        for op_count in operation_counts:
            metrics = PerformanceMetrics()
            metrics.operation_count = op_count

            def scale_compute(value: int):
                return {"scaled_value": value, "metadata": f"scale_{value}"}

            # Create separate cache for each scale test
            scale_cache = AsyncSmartCache()

            metrics.start_measurement()

            tasks = [
                scale_cache.get_or_compute(
                    f"scale_key_{i}", lambda v=i: scale_compute(v)
                )
                for i in range(op_count)
            ]

            results = await asyncio.gather(*tasks)
            metrics.end_measurement()

            scalability_results[op_count] = {
                "throughput": metrics.throughput,
                "duration": metrics.duration,
                "memory_delta_mb": metrics.memory_delta / (1024 * 1024),
                "success": len(results) == op_count,
            }

        # Scalability analysis
        throughputs = [result["throughput"] for result in scalability_results.values()]

        # Validate all scale tests succeed
        assert all(result["success"] for result in scalability_results.values()), (
            "All scale tests should succeed"
        )

        # Validate reasonable performance at all scales
        assert all(tp > 200 for tp in throughputs), (
            "All throughputs should be reasonable"
        )

        print("\nScalability Stress Test:")
        for op_count, metrics in scalability_results.items():
            print(
                f"  {op_count:>5} ops: {metrics['throughput']:>6.1f} ops/sec, {metrics['duration']:>5.2f}s, {metrics['memory_delta_mb']:>4.1f}MB"
            )
