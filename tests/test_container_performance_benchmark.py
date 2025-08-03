"""Performance Benchmark Tests for Refactored LoggingContainer Architecture.

This test suite provides performance benchmarks comparing the refactored architecture
with baseline expectations to ensure no regressions in performance.
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from fapilog.container import LoggingContainer
from fapilog.settings import LoggingSettings


class TestContainerPerformanceBenchmark:
    """Performance benchmark tests for the refactored container architecture."""

    def test_container_creation_benchmark(self):
        """Benchmark container creation performance."""
        # Baseline: Should create containers quickly
        start_time = time.time()

        containers = []
        for _ in range(50):
            container = LoggingContainer()
            containers.append(container)

        creation_time = time.time() - start_time

        # Should create 50 containers in under 0.2 seconds (allowing for system variations)
        assert creation_time < 0.2, f"Container creation too slow: {creation_time:.3f}s"

        print(f"Created 50 containers in {creation_time:.3f} seconds")
        print(f"Average per container: {creation_time / 50 * 1000:.2f}ms")

    def test_container_configuration_benchmark(self):
        """Benchmark container configuration performance."""
        containers = [LoggingContainer() for _ in range(20)]

        start_time = time.time()

        for container in containers:
            container.configure()

        config_time = time.time() - start_time

        # Should configure 20 containers in under 2 seconds
        assert config_time < 2.0, f"Configuration too slow: {config_time:.3f}s"

        print(f"Configured 20 containers in {config_time:.3f} seconds")
        print(f"Average per container: {config_time / 20 * 1000:.2f}ms")

        # Cleanup
        for container in containers:
            container.shutdown_sync()

    def test_logger_creation_benchmark(self):
        """Benchmark logger creation performance."""
        container = LoggingContainer()
        container.configure()

        start_time = time.time()

        loggers = []
        for i in range(200):
            logger = container.get_logger(f"benchmark.test.{i}")
            loggers.append(logger)

        logger_time = time.time() - start_time

        # Should create 200 loggers in under 0.5 seconds
        assert logger_time < 0.5, f"Logger creation too slow: {logger_time:.3f}s"

        print(f"Created 200 loggers in {logger_time:.3f} seconds")
        print(f"Average per logger: {logger_time / 200 * 1000:.2f}ms")

        container.shutdown_sync()

    def test_component_access_benchmark(self):
        """Benchmark component access performance."""
        container = LoggingContainer()
        container.configure()

        start_time = time.time()

        # Access components multiple times (should be cached)
        for _ in range(100):
            _ = container.get_lock_manager()
            _ = container.get_processor_metrics()
            _ = container.get_async_smart_cache()
            _ = container.get_enricher_error_handler()
            _ = container.get_enricher_health_monitor()
            _ = container.get_retry_coordinator()

        access_time = time.time() - start_time

        # Should access components very quickly due to caching (under 0.1 seconds)
        assert access_time < 0.1, f"Component access too slow: {access_time:.3f}s"

        print(
            f"Accessed 600 components (6 types x 100 iterations) in {access_time:.3f} seconds"
        )
        print(f"Average per access: {access_time / 600 * 1000000:.2f}μs")

        container.shutdown_sync()

    def test_concurrent_container_benchmark(self):
        """Benchmark concurrent container operations."""

        def create_configure_use_container(container_id: int) -> float:
            start = time.time()

            container = LoggingContainer()
            container.configure()

            # Use the container
            logger = container.get_logger(f"concurrent.test.{container_id}")
            logger.info(f"Benchmark message from container {container_id}")

            # Access some components
            _ = container.get_lock_manager()
            _ = container.get_processor_metrics()

            container.shutdown_sync()

            return time.time() - start

        start_time = time.time()

        # Run 10 containers concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(create_configure_use_container, i) for i in range(10)
            ]

            times = [future.result() for future in as_completed(futures)]

        total_time = time.time() - start_time
        avg_time = sum(times) / len(times)
        max_time = max(times)

        # Should handle concurrent operations efficiently
        assert total_time < 3.0, f"Concurrent operations too slow: {total_time:.3f}s"
        assert avg_time < 1.0, f"Average container time too slow: {avg_time:.3f}s"

        print(f"10 concurrent containers completed in {total_time:.3f} seconds")
        print(f"Average per container: {avg_time:.3f}s, Max: {max_time:.3f}s")

    def test_logger_usage_benchmark(self):
        """Benchmark actual logging performance."""
        container = LoggingContainer()
        container.configure()

        logger = container.get_logger("benchmark.logging")

        start_time = time.time()

        # Log many messages
        for i in range(500):
            logger.info(f"Benchmark log message {i}", extra_data=i, test_field="value")

        logging_time = time.time() - start_time

        # Should log 500 messages in reasonable time (under 1 second)
        assert logging_time < 1.0, f"Logging too slow: {logging_time:.3f}s"

        print(f"Logged 500 messages in {logging_time:.3f} seconds")
        print(f"Average per message: {logging_time / 500 * 1000:.2f}ms")

        container.shutdown_sync()

    def test_settings_validation_benchmark(self):
        """Benchmark settings validation performance."""
        # Create various settings configurations
        settings_configs = []
        for i in range(20):
            settings = LoggingSettings()
            settings.level = "DEBUG" if i % 2 == 0 else "INFO"
            settings.metrics.enabled = i % 3 == 0
            settings.queue.enabled = i % 4 == 0
            settings_configs.append(settings)

        start_time = time.time()

        containers = []
        for settings in settings_configs:
            container = LoggingContainer()
            container.configure(settings=settings)
            containers.append(container)

        validation_time = time.time() - start_time

        # Should validate and configure 20 different settings quickly
        assert validation_time < 1.5, (
            f"Settings validation too slow: {validation_time:.3f}s"
        )

        print(
            f"Validated and configured 20 different settings in {validation_time:.3f} seconds"
        )
        print(f"Average per validation: {validation_time / 20 * 1000:.2f}ms")

        # Cleanup
        for container in containers:
            container.shutdown_sync()

    @pytest.mark.asyncio
    async def test_async_operations_benchmark(self):
        """Benchmark async operations performance."""
        containers = [LoggingContainer() for _ in range(10)]

        # Configure all containers
        for container in containers:
            container.configure()

        start_time = time.time()

        # Run async setup on all containers
        await asyncio.gather(*[container.setup() for container in containers])

        setup_time = time.time() - start_time

        # Should setup all containers quickly
        assert setup_time < 1.0, f"Async setup too slow: {setup_time:.3f}s"

        print(f"Async setup for 10 containers in {setup_time:.3f} seconds")

        # Test async shutdown
        start_time = time.time()

        await asyncio.gather(*[container.shutdown() for container in containers])

        shutdown_time = time.time() - start_time

        assert shutdown_time < 1.0, f"Async shutdown too slow: {shutdown_time:.3f}s"

        print(f"Async shutdown for 10 containers in {shutdown_time:.3f} seconds")

    def test_memory_efficiency_benchmark(self):
        """Benchmark memory efficiency of container architecture."""
        import gc
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        containers = []

        # Create many containers to test memory usage
        for _ in range(50):
            container = LoggingContainer()
            container.configure()
            containers.append(container)

        # Force garbage collection
        gc.collect()

        peak_memory = process.memory_info().rss
        memory_increase = peak_memory - initial_memory
        memory_per_container = memory_increase / 50

        print(
            f"Memory increase for 50 containers: {memory_increase / 1024 / 1024:.2f} MB"
        )
        print(f"Average memory per container: {memory_per_container / 1024:.2f} KB")

        # Cleanup
        for container in containers:
            container.shutdown_sync()

        # Force cleanup
        containers.clear()
        gc.collect()

        final_memory = process.memory_info().rss
        print(
            f"Memory after cleanup: {(final_memory - initial_memory) / 1024 / 1024:.2f} MB increase"
        )

        # Should not use excessive memory per container (less than 500KB per container)
        assert memory_per_container < 500 * 1024, (
            f"Memory usage too high: {memory_per_container / 1024:.2f} KB per container"
        )

    def test_scalability_benchmark(self):
        """Test scalability with increasing load."""
        results = {}

        # Test with different numbers of containers
        for container_count in [1, 5, 10, 20, 50]:
            start_time = time.time()

            containers = []
            for i in range(container_count):
                container = LoggingContainer()
                container.configure()

                # Use the container
                logger = container.get_logger(f"scale.test.{i}")
                logger.info(f"Scalability test message {i}")

                containers.append(container)

            creation_time = time.time() - start_time

            # Cleanup
            cleanup_start = time.time()
            for container in containers:
                container.shutdown_sync()
            cleanup_time = time.time() - cleanup_start

            total_time = creation_time + cleanup_time
            results[container_count] = {
                "creation_time": creation_time,
                "cleanup_time": cleanup_time,
                "total_time": total_time,
                "time_per_container": total_time / container_count,
            }

            print(
                f"{container_count} containers: {total_time:.3f}s total, {total_time / container_count * 1000:.2f}ms per container"
            )

        # Performance should scale reasonably (not exponentially)
        # Time per container should not increase drastically
        time_per_1 = results[1]["time_per_container"]
        time_per_50 = results[50]["time_per_container"]

        # 50 containers should not take more than 10x the time per container as 1 container
        scale_factor = time_per_50 / time_per_1
        assert scale_factor < 10, (
            f"Poor scalability: {scale_factor:.2f}x slowdown at 50 containers"
        )

        print(f"Scalability factor (50 vs 1 container): {scale_factor:.2f}x")


class TestContainerRegressionBenchmark:
    """Regression benchmarks to ensure performance doesn't degrade over time."""

    def test_baseline_performance_targets(self):
        """Test that performance meets baseline targets."""
        container = LoggingContainer()

        # Container creation should be very fast
        start = time.time()
        container.configure()
        config_time = time.time() - start
        assert config_time < 0.1, f"Configuration regression: {config_time:.3f}s > 0.1s"

        # Logger creation should be fast
        start = time.time()
        _ = container.get_logger("regression.test")
        logger_time = time.time() - start
        assert logger_time < 0.01, (
            f"Logger creation regression: {logger_time:.3f}s > 0.01s"
        )

        # Component access should be very fast (cached)
        start = time.time()
        _ = container.get_lock_manager()
        component_time = time.time() - start
        assert component_time < 0.001, (
            f"Component access regression: {component_time:.3f}s > 0.001s"
        )

        print("✅ Performance targets met:")
        print(f"  Configuration: {config_time * 1000:.2f}ms < 100ms")
        print(f"  Logger creation: {logger_time * 1000:.2f}ms < 10ms")
        print(f"  Component access: {component_time * 1000000:.2f}μs < 1000μs")

        container.shutdown_sync()

    def test_no_memory_leaks(self):
        """Test that repeated operations don't cause memory leaks."""
        import gc
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Perform repeated operations
        for cycle in range(10):
            containers = []

            # Create and use containers
            for i in range(10):
                container = LoggingContainer()
                container.configure()

                logger = container.get_logger(f"leak.test.{cycle}.{i}")
                logger.info(f"Memory leak test {cycle}-{i}")

                containers.append(container)

            # Cleanup
            for container in containers:
                container.shutdown_sync()

            # Force garbage collection
            gc.collect()

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        print(
            f"Memory increase after 100 container cycles: {memory_increase / 1024 / 1024:.2f} MB"
        )

        # Should not have significant memory growth (less than 10MB)
        assert memory_increase < 10 * 1024 * 1024, (
            f"Potential memory leak: {memory_increase / 1024 / 1024:.2f} MB increase"
        )

    def test_performance_stability(self):
        """Test that performance is stable across multiple runs."""
        times = []

        # Run same operation multiple times
        for run in range(20):
            start_time = time.time()

            container = LoggingContainer()
            container.configure()

            logger = container.get_logger(f"stability.test.{run}")
            logger.info(f"Performance stability test {run}")

            # Access components
            _ = container.get_lock_manager()
            _ = container.get_processor_metrics()

            container.shutdown_sync()

            times.append(time.time() - start_time)

        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        variance = max_time - min_time

        print("Performance stability over 20 runs:")
        print(f"  Average: {avg_time:.3f}s")
        print(f"  Min: {min_time:.3f}s")
        print(f"  Max: {max_time:.3f}s")
        print(f"  Variance: {variance:.3f}s")

        # Performance should be stable (variance < 100% of average - allowing for system variations)
        assert variance < avg_time * 1.0, (
            f"Performance instability: {variance:.3f}s variance > {avg_time * 1.0:.3f}s threshold"
        )


if __name__ == "__main__":
    # Run benchmarks manually for development
    print("Running Container Performance Benchmarks...")

    benchmark = TestContainerPerformanceBenchmark()

    print("\n=== Container Creation Benchmark ===")
    benchmark.test_container_creation_benchmark()

    print("\n=== Container Configuration Benchmark ===")
    benchmark.test_container_configuration_benchmark()

    print("\n=== Logger Creation Benchmark ===")
    benchmark.test_logger_creation_benchmark()

    print("\n=== Component Access Benchmark ===")
    benchmark.test_component_access_benchmark()

    print("\n=== Concurrent Container Benchmark ===")
    benchmark.test_concurrent_container_benchmark()

    print("\n=== Settings Validation Benchmark ===")
    benchmark.test_settings_validation_benchmark()

    print("\n=== Scalability Benchmark ===")
    benchmark.test_scalability_benchmark()

    print("\n=== Regression Benchmarks ===")
    regression = TestContainerRegressionBenchmark()
    regression.test_baseline_performance_targets()
    regression.test_performance_stability()

    print("\n✅ All benchmarks completed successfully!")
