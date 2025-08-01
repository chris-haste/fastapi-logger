"""Container stress tests for factory-based architecture.

This test module performs stress testing on LoggingContainer instances
to validate stability, performance, and resource management under
extreme conditions and high load scenarios.
"""

import concurrent.futures
import gc
import threading
import time
from typing import Any, Dict

import pytest

from fapilog.container import LoggingContainer
from fapilog.settings import LoggingSettings


class TestContainerStress:
    """Stress testing for container isolation and performance."""

    def test_thousand_containers_creation(self):
        """Test creating and managing 1000+ containers."""
        num_containers = 1000
        containers = []

        print(f"\nCreating {num_containers} containers...")
        start_time = time.perf_counter()

        try:
            # Create containers in batches to avoid overwhelming the system
            batch_size = 50
            for batch_start in range(0, num_containers, batch_size):
                batch_containers = []
                batch_end = min(batch_start + batch_size, num_containers)

                for i in range(batch_start, batch_end):
                    settings = LoggingSettings(
                        level="INFO" if i % 2 == 0 else "DEBUG",
                        json_console="json" if i % 3 == 0 else "pretty",
                    )
                    container = LoggingContainer(settings)
                    container.configure()
                    batch_containers.append(container)

                containers.extend(batch_containers)

                # Brief pause between batches to prevent system overload
                if batch_end < num_containers:
                    time.sleep(0.01)

            creation_time = time.perf_counter() - start_time

            # Verify all containers are functional
            assert len(containers) == num_containers

            # Test a sample of containers
            sample_indices = [
                0,
                num_containers // 4,
                num_containers // 2,
                num_containers // 2 + num_containers // 4,
                num_containers - 1,
            ]
            for idx in sample_indices:
                container = containers[idx]
                assert container.is_configured
                logger = container.get_logger(f"stress_test_{idx}")
                logger.info(f"Test message from container {idx}")

            print(
                f"Successfully created {num_containers} containers in {creation_time:.2f}s"
            )
            print(
                f"Average creation time: {creation_time / num_containers:.6f}s per container"
            )

            # Performance target: should complete in reasonable time
            assert creation_time < 30.0, (
                f"Container creation too slow: {creation_time:.2f}s"
            )

        finally:
            # Cleanup all containers
            print("Cleaning up containers...")
            cleanup_start = time.perf_counter()

            for container in containers:
                try:
                    container.shutdown_sync()
                except Exception:
                    pass  # Continue cleanup even if some fail

            cleanup_time = time.perf_counter() - cleanup_start
            print(f"Cleanup completed in {cleanup_time:.2f}s")

    def test_rapid_creation_destruction_cycles(self):
        """Test rapid container creation and destruction cycles."""
        cycles = 100
        containers_per_cycle = 10

        print(f"\nTesting {cycles} cycles of {containers_per_cycle} containers each...")

        cycle_times = []
        for cycle in range(cycles):
            cycle_start = time.perf_counter()

            # Create containers
            containers = []
            for i in range(containers_per_cycle):
                container = LoggingContainer()
                container.configure()

                # Use the container briefly
                logger = container.get_logger(f"cycle_{cycle}_container_{i}")
                logger.info(f"Rapid cycle test {cycle}.{i}")

                containers.append(container)

            # Destroy containers immediately
            for container in containers:
                container.shutdown_sync()

            cycle_time = time.perf_counter() - cycle_start
            cycle_times.append(cycle_time)

            # Brief pause to prevent overwhelming the system
            if cycle % 10 == 0:
                time.sleep(0.001)

        avg_cycle_time = sum(cycle_times) / len(cycle_times)
        max_cycle_time = max(cycle_times)
        min_cycle_time = min(cycle_times)

        print(
            f"Cycle times - Avg: {avg_cycle_time:.6f}s, Min: {min_cycle_time:.6f}s, Max: {max_cycle_time:.6f}s"
        )

        # Performance targets
        assert avg_cycle_time < 0.1, f"Cycle time too slow: {avg_cycle_time:.6f}s"
        assert max_cycle_time < 0.5, f"Worst cycle too slow: {max_cycle_time:.6f}s"

    def test_container_usage_under_high_load(self):
        """Test container usage under sustained high load."""
        container = LoggingContainer()
        container.configure()

        num_loggers = 1000
        messages_per_logger = 10
        total_messages = num_loggers * messages_per_logger

        print(f"\nGenerating {total_messages} log messages...")

        start_time = time.perf_counter()

        # Create many loggers and use them intensively
        loggers = []
        for i in range(num_loggers):
            logger = container.get_logger(f"high_load_logger_{i}")
            loggers.append(logger)

        # Generate many log messages
        for i, logger in enumerate(loggers):
            for j in range(messages_per_logger):
                logger.info(f"High load message {i}.{j}")

        end_time = time.perf_counter()
        total_time = end_time - start_time

        messages_per_second = total_messages / total_time

        print(f"Generated {total_messages} messages in {total_time:.2f}s")
        print(f"Rate: {messages_per_second:.0f} messages/second")

        # Performance target: should handle high load efficiently
        assert messages_per_second > 1000, (
            f"Message rate too low: {messages_per_second:.0f}/s"
        )

        container.shutdown_sync()

    def test_memory_cleanup_and_garbage_collection(self):
        """Test memory cleanup and garbage collection under stress."""
        try:
            import os

            import psutil
        except ImportError:
            pytest.skip("psutil not available for memory testing")

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Create many containers in waves
        waves = 5
        containers_per_wave = 50

        print(f"\nTesting memory cleanup across {waves} waves...")

        memory_samples = [initial_memory]

        for wave in range(waves):
            print(f"Wave {wave + 1}/{waves}...")

            # Create containers
            containers = []
            for i in range(containers_per_wave):
                container = LoggingContainer()
                container.configure()

                # Use container to allocate memory
                for j in range(10):
                    logger = container.get_logger(
                        f"wave_{wave}_container_{i}_logger_{j}"
                    )
                    logger.info(f"Memory test message {wave}.{i}.{j}")

                containers.append(container)

            # Sample memory after creation
            after_creation = process.memory_info().rss
            memory_samples.append(after_creation)

            # Cleanup containers
            for container in containers:
                container.shutdown_sync()

            # Force garbage collection
            gc.collect()

            # Sample memory after cleanup
            after_cleanup = process.memory_info().rss
            memory_samples.append(after_cleanup)

            wave_growth = (after_cleanup - initial_memory) / (1024 * 1024)
            print(f"  Memory growth after wave {wave + 1}: {wave_growth:.2f}MB")

        final_memory = process.memory_info().rss
        final_growth = (final_memory - initial_memory) / (1024 * 1024)

        print(f"Final memory growth: {final_growth:.2f}MB")

        # Memory growth should be reasonable after all waves
        max_growth_mb = 100  # Allow some growth but not excessive
        assert final_growth < max_growth_mb, (
            f"Memory growth too high: {final_growth:.2f}MB (max: {max_growth_mb}MB)"
        )

    def test_concurrent_stress_multiple_containers(self):
        """Test concurrent stress on multiple containers simultaneously."""
        num_containers = 20
        operations_per_container = 50

        print(f"\nStress testing {num_containers} containers concurrently...")

        def stress_container(container_id: int) -> Dict[str, Any]:
            """Stress test a single container."""
            results: Dict[str, Any] = {
                "container_id": container_id,
                "loggers_created": 0,
                "messages_sent": 0,
                "errors": [],
                "time_taken": 0,
            }

            start_time = time.perf_counter()

            try:
                # Create container
                container = LoggingContainer()
                container.configure()

                # Create many loggers and use them
                for i in range(operations_per_container):
                    logger = container.get_logger(
                        f"stress_container_{container_id}_logger_{i}"
                    )
                    results["loggers_created"] += 1

                    # Send multiple messages per logger
                    for j in range(5):
                        logger.info(f"Stress message {container_id}.{i}.{j}")
                        results["messages_sent"] += 1

                # Cleanup
                container.shutdown_sync()

            except Exception as e:
                results["errors"].append(str(e))

            results["time_taken"] = time.perf_counter() - start_time
            return results

        # Run stress test on multiple containers concurrently
        start_time = time.perf_counter()

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=num_containers
        ) as executor:
            futures = [
                executor.submit(stress_container, i) for i in range(num_containers)
            ]
            results = [future.result() for future in futures]

        total_time = time.perf_counter() - start_time

        # Analyze results
        total_loggers = sum(r["loggers_created"] for r in results)
        total_messages = sum(r["messages_sent"] for r in results)
        total_errors = sum(len(r["errors"]) for r in results)
        avg_container_time = sum(r["time_taken"] for r in results) / len(results)

        print(f"Concurrent stress test completed in {total_time:.2f}s")
        print(f"Total loggers created: {total_loggers}")
        print(f"Total messages sent: {total_messages}")
        print(f"Total errors: {total_errors}")
        print(f"Average time per container: {avg_container_time:.2f}s")

        # Verify success criteria
        expected_loggers = num_containers * operations_per_container
        expected_messages = expected_loggers * 5

        assert total_loggers == expected_loggers, (
            f"Missing loggers: {expected_loggers - total_loggers}"
        )
        assert total_messages == expected_messages, (
            f"Missing messages: {expected_messages - total_messages}"
        )
        assert total_errors == 0, f"Errors occurred: {total_errors}"

        # Performance criteria
        assert total_time < 30.0, f"Concurrent stress test too slow: {total_time:.2f}s"

    def test_resource_exhaustion_resilience(self):
        """Test resilience under resource exhaustion conditions."""
        containers = []
        successful_containers = 0

        print("\nTesting resource exhaustion resilience...")

        try:
            # Keep creating containers until we hit resource limits or reach a reasonable number
            max_containers = 500  # Reasonable limit to prevent system instability

            for i in range(max_containers):
                try:
                    container = LoggingContainer()
                    container.configure()

                    # Basic functionality test
                    logger = container.get_logger(f"exhaustion_test_{i}")
                    logger.info(f"Resource test message {i}")

                    containers.append(container)
                    successful_containers += 1

                    # Check every 50 containers
                    if i % 50 == 0 and i > 0:
                        print(f"Successfully created {i} containers...")

                except Exception as e:
                    print(f"Hit resource limit at container {i}: {e}")
                    break

            print(
                f"Successfully created {successful_containers} containers before hitting limits"
            )

            # Should be able to create a reasonable number of containers
            assert successful_containers >= 100, (
                f"Too few containers created: {successful_containers}"
            )

            # Test that existing containers still work
            if successful_containers > 10:
                sample_indices = [
                    0,
                    successful_containers // 2,
                    successful_containers - 1,
                ]
                for idx in sample_indices:
                    container = containers[idx]
                    logger = container.get_logger(f"post_exhaustion_test_{idx}")
                    logger.info(f"Post-exhaustion test message {idx}")

        finally:
            # Cleanup
            print("Cleaning up containers...")
            for container in containers:
                try:
                    container.shutdown_sync()
                except Exception:
                    pass  # Continue cleanup

    def test_error_handling_under_stress(self):
        """Test error handling under stress conditions."""
        containers = []
        errors_caught = []
        successful_operations = 0

        print("\nTesting error handling under stress...")

        # Create containers with some intentionally problematic configurations
        for i in range(100):
            try:
                if i % 10 == 0:
                    # Every 10th container: invalid level (should be handled gracefully)
                    settings = LoggingSettings(level="INVALID_LEVEL")
                else:
                    # Normal containers
                    settings = LoggingSettings(level="INFO")

                container = LoggingContainer(settings)

                if i % 10 != 0:  # Skip configuration for problematic containers
                    container.configure()
                    containers.append(container)
                    successful_operations += 1

            except Exception as e:
                errors_caught.append(f"Container {i}: {e}")

        # Test operations on good containers
        for i, container in enumerate(containers):
            try:
                logger = container.get_logger(f"error_stress_test_{i}")
                logger.info(f"Error handling stress test {i}")
                successful_operations += 1
            except Exception as e:
                errors_caught.append(f"Logger operation {i}: {e}")

        print(f"Successful operations: {successful_operations}")
        print(f"Errors caught: {len(errors_caught)}")

        # Should have mostly successful operations
        assert successful_operations >= 180, (
            f"Too few successful operations: {successful_operations}"
        )

        # Should have caught some errors from invalid configurations
        assert len(errors_caught) >= 5, (
            f"Expected some errors from invalid configurations: {len(errors_caught)}"
        )

        # Cleanup
        for container in containers:
            try:
                container.shutdown_sync()
            except Exception:
                pass

    def test_thread_safety_under_extreme_load(self):
        """Test thread safety under extreme concurrent load."""
        container = LoggingContainer()
        container.configure()

        num_threads = 50
        operations_per_thread = 100
        results = {}
        errors = []
        lock = threading.Lock()

        def extreme_load_worker(thread_id: int) -> None:
            """Worker that performs many operations concurrently."""
            local_results = {
                "loggers_created": 0,
                "messages_sent": 0,
                "get_logger_calls": 0,
            }

            try:
                for i in range(operations_per_thread):
                    # Create logger
                    logger = container.get_logger(f"extreme_thread_{thread_id}_op_{i}")
                    local_results["loggers_created"] += 1
                    local_results["get_logger_calls"] += 1

                    # Use logger multiple times
                    for j in range(3):
                        logger.info(f"Extreme load message {thread_id}.{i}.{j}")
                        local_results["messages_sent"] += 1

                    # Also test getting existing loggers
                    if i > 0:
                        existing_logger = container.get_logger(
                            f"extreme_thread_{thread_id}_op_{i - 1}"
                        )
                        existing_logger.info(f"Reused logger message {thread_id}.{i}")
                        local_results["get_logger_calls"] += 1

                with lock:
                    results[thread_id] = local_results

            except Exception as e:
                with lock:
                    errors.append(f"Thread {thread_id}: {e}")

        print(
            f"\nRunning extreme load test: {num_threads} threads, {operations_per_thread} ops each..."
        )

        # Start all threads
        threads = []
        start_time = time.perf_counter()

        for i in range(num_threads):
            thread = threading.Thread(target=extreme_load_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        total_time = time.perf_counter() - start_time

        # Analyze results
        total_loggers = sum(r["loggers_created"] for r in results.values())
        total_messages = sum(r["messages_sent"] for r in results.values())
        total_get_calls = sum(r["get_logger_calls"] for r in results.values())

        print(f"Extreme load test completed in {total_time:.2f}s")
        print(f"Total loggers created: {total_loggers}")
        print(f"Total messages sent: {total_messages}")
        print(f"Total get_logger calls: {total_get_calls}")
        print(f"Errors: {len(errors)}")

        # Verify no errors occurred
        assert len(errors) == 0, f"Thread safety errors: {errors}"

        # Verify expected operations completed
        expected_loggers = num_threads * operations_per_thread
        expected_messages = expected_loggers * 3
        expected_get_calls = expected_loggers + (
            num_threads * (operations_per_thread - 1)
        )

        assert total_loggers == expected_loggers, (
            f"Missing loggers: {expected_loggers - total_loggers}"
        )
        assert total_messages == expected_messages, (
            f"Missing messages: {expected_messages - total_messages}"
        )
        assert total_get_calls == expected_get_calls, (
            f"Missing get_logger calls: {expected_get_calls - total_get_calls}"
        )

        # Performance check
        operations_per_second = total_get_calls / total_time
        print(f"Operations per second: {operations_per_second:.0f}")

        assert operations_per_second > 1000, (
            f"Thread safety performance too low: {operations_per_second:.0f} ops/s"
        )

        container.shutdown_sync()

    def test_memory_stability_long_running(self):
        """Test memory stability in long-running scenarios."""
        try:
            import os

            import psutil
        except ImportError:
            pytest.skip("psutil not available for memory testing")

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        container = LoggingContainer()
        container.configure()

        print("\nTesting long-running memory stability...")

        memory_samples = []
        iterations = 100
        loggers_per_iteration = 20

        for iteration in range(iterations):
            # Create and use loggers
            for i in range(loggers_per_iteration):
                logger = container.get_logger(f"longrun_iter_{iteration}_logger_{i}")
                for j in range(5):
                    logger.info(f"Long-running test {iteration}.{i}.{j}")

            # Sample memory every 10 iterations
            if iteration % 10 == 0:
                current_memory = process.memory_info().rss
                memory_growth = (current_memory - initial_memory) / (1024 * 1024)
                memory_samples.append(memory_growth)
                print(f"Iteration {iteration}: Memory growth {memory_growth:.2f}MB")

        final_memory = process.memory_info().rss
        final_growth = (final_memory - initial_memory) / (1024 * 1024)

        print(f"Final memory growth: {final_growth:.2f}MB")

        # Memory growth should stabilize (not grow indefinitely)
        if len(memory_samples) >= 3:
            early_growth = memory_samples[1]  # After some warmup
            late_growth = memory_samples[-1]
            growth_ratio = late_growth / early_growth if early_growth > 0 else 1

            print(f"Memory growth ratio (late/early): {growth_ratio:.2f}")

            # Memory shouldn't grow excessively over time
            assert growth_ratio < 3.0, (
                f"Memory growth unstable: {growth_ratio:.2f}x increase"
            )

        # Total memory growth should be reasonable
        assert final_growth < 200, f"Total memory growth too high: {final_growth:.2f}MB"

        container.shutdown_sync()
