"""Container concurrency tests for factory-based architecture.

This test module validates that LoggingContainer instances work correctly
under concurrent load, with thread-safe operations and proper isolation
in multi-threaded environments.
"""

import concurrent.futures
import threading
import time
from typing import List, Tuple

import structlog

from fapilog.config import LoggingSettings
from fapilog.config.sink_settings import SinkSettings
from fapilog.container import LoggingContainer


class TestContainerConcurrency:
    """Test container behavior under concurrent load."""

    def test_concurrent_logger_creation(self):
        """Test creating loggers concurrently from same container."""
        container = LoggingContainer()
        container.configure()

        def create_logger(name: str) -> object:
            """Create a logger with given name."""
            return container.get_logger(f"test_{name}")

        # Create 50 loggers concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_logger, i) for i in range(50)]
            loggers = [future.result() for future in futures]

        # All loggers should be valid and functional
        assert len(loggers) == 50
        for i, logger in enumerate(loggers):
            assert hasattr(logger, "info")
            # Test that logger works
            logger.info(f"test message {i}")

        # Cleanup
        container.shutdown_sync()

    def test_multiple_containers_concurrent_usage(self):
        """Test multiple containers being used concurrently."""
        # Create multiple containers with different settings
        containers = []
        for i in range(5):
            settings = LoggingSettings(
                level=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"][i],
                sinks=SinkSettings(json_console="json" if i % 2 == 0 else "pretty"),
            )
            container = LoggingContainer(settings)
            container.configure()
            containers.append(container)

        def use_container(
            container: LoggingContainer, container_id: int
        ) -> List[structlog.BoundLogger]:
            """Use a container to create loggers and log messages."""
            results = []
            for i in range(10):
                logger = container.get_logger(f"logger_{container_id}_{i}")
                logger.info(f"Message from container {container_id}, logger {i}")
                results.append(logger)
            return results

        # Use all containers concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(use_container, container, i)
                for i, container in enumerate(containers)
            ]
            results = [future.result() for future in futures]

        # Verify all containers worked independently
        assert len(results) == 5
        for result in results:
            assert len(result) == 10
            for logger in result:
                assert hasattr(logger, "info")

        # Cleanup
        for container in containers:
            container.shutdown_sync()

    def test_concurrent_container_configuration(self):
        """Test configuring multiple containers concurrently."""

        def configure_container(container_id: int) -> Tuple[LoggingContainer, object]:
            """Create and configure a container."""
            settings = LoggingSettings(
                level="INFO",
                sinks=SinkSettings(
                    json_console="json" if container_id % 2 == 0 else "pretty"
                ),
            )
            container = LoggingContainer(settings)
            logger = container.configure()
            return container, logger

        # Configure 20 containers concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(configure_container, i) for i in range(20)]
            results = [future.result() for future in futures]

        # Verify all configurations succeeded
        assert len(results) == 20
        containers = [result[0] for result in results]
        loggers = [result[1] for result in results]

        # All containers should be configured and independent
        for i, container in enumerate(containers):
            assert container.is_configured
            assert container._logger_factory is not None
            assert hasattr(loggers[i], "info")

            # Test independence
            for j, other_container in enumerate(containers):
                if i != j:
                    assert container is not other_container
                    assert (
                        container._logger_factory is not other_container._logger_factory
                    )

        # Cleanup
        for container in containers:
            container.shutdown_sync()

    def test_thread_safe_logger_access(self):
        """Test thread-safe access to loggers from single container."""
        container = LoggingContainer()
        container.configure()

        results = {}
        errors = []
        lock = threading.Lock()

        def worker_thread(thread_id: int) -> None:
            """Worker that creates and uses loggers."""
            try:
                # Each thread creates multiple loggers
                thread_loggers = []
                for i in range(5):
                    logger = container.get_logger(f"thread_{thread_id}_logger_{i}")
                    thread_loggers.append(logger)

                # Use the loggers
                for j, logger in enumerate(thread_loggers):
                    logger.info(f"Message from thread {thread_id}, logger {j}")

                # Store results thread-safely
                with lock:
                    results[thread_id] = thread_loggers

            except Exception as e:
                with lock:
                    errors.append(f"Thread {thread_id}: {e}")

        # Create and start threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=worker_thread, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify no errors
        assert not errors, f"Errors occurred: {errors}"

        # Verify results
        assert len(results) == 10
        for _thread_id, thread_loggers in results.items():
            assert len(thread_loggers) == 5
            for logger in thread_loggers:
                assert hasattr(logger, "info")

        # Cleanup
        container.shutdown_sync()

    def test_concurrent_container_reset_and_reconfigure(self):
        """Test concurrent reset and reconfigure operations."""
        containers = []

        # Create multiple containers
        for _i in range(5):
            container = LoggingContainer()
            container.configure()
            containers.append(container)

        def reset_and_reconfigure(
            container: LoggingContainer, container_id: int
        ) -> bool:
            """Reset and reconfigure a container."""
            try:
                # Reset container
                container.reset()
                assert not container.is_configured

                # Small delay to increase chance of race conditions
                time.sleep(0.01)

                # Reconfigure
                logger = container.configure()
                assert container.is_configured
                assert hasattr(logger, "info")

                # Test logger functionality
                logger.info(f"Reconfigured container {container_id}")
                return True

            except Exception:
                return False

        # Reset and reconfigure all containers concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(reset_and_reconfigure, container, i)
                for i, container in enumerate(containers)
            ]
            results = [future.result() for future in futures]

        # All operations should succeed
        assert all(results), "Some reset/reconfigure operations failed"

        # All containers should be functional
        for i, container in enumerate(containers):
            assert container.is_configured
            logger = container.get_logger(f"final_test_{i}")
            logger.info(f"Final test for container {i}")

        # Cleanup
        for container in containers:
            container.shutdown_sync()

    def test_concurrent_logger_creation_stress(self):
        """Stress test with many concurrent logger creation operations."""
        container = LoggingContainer()
        container.configure()

        total_loggers = 200
        max_workers = 20

        def create_batch_loggers(
            batch_id: int, batch_size: int
        ) -> List[structlog.BoundLogger]:
            """Create a batch of loggers."""
            loggers = []
            for i in range(batch_size):
                logger_name = f"batch_{batch_id}_logger_{i}"
                logger = container.get_logger(logger_name)
                logger.info(f"Test message from {logger_name}")
                loggers.append(logger)
            return loggers

        # Calculate batch size
        batch_size = total_loggers // max_workers

        # Create loggers in concurrent batches
        start_time = time.perf_counter()

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(create_batch_loggers, i, batch_size)
                for i in range(max_workers)
            ]
            batch_results = [future.result() for future in futures]

        end_time = time.perf_counter()
        total_time = end_time - start_time

        # Verify results
        total_created = sum(len(batch) for batch in batch_results)
        assert total_created == total_loggers

        # All loggers should be functional
        for batch in batch_results:
            for logger in batch:
                assert hasattr(logger, "info")

        # Performance check - should complete in reasonable time
        assert total_time < 5.0, f"Stress test took too long: {total_time:.2f}s"

        # Cleanup
        container.shutdown_sync()

    def test_concurrent_container_lifecycle_operations(self):
        """Test concurrent lifecycle operations on multiple containers."""
        containers = []

        # Create containers
        for _i in range(8):
            container = LoggingContainer()
            containers.append(container)

        operations_completed = []
        errors = []
        lock = threading.Lock()

        def lifecycle_worker(container: LoggingContainer, worker_id: int) -> None:
            """Perform lifecycle operations on a container."""
            try:
                operations = []

                # Configure
                logger = container.configure()
                operations.append("configure")

                # Use logger
                logger.info(f"Message from worker {worker_id}")
                operations.append("use_logger")

                # Create additional loggers
                for i in range(3):
                    extra_logger = container.get_logger(f"extra_{worker_id}_{i}")
                    extra_logger.info(f"Extra message {i}")
                operations.append("create_extra_loggers")

                # Reset and reconfigure
                container.reset()
                operations.append("reset")

                logger2 = container.configure()
                operations.append("reconfigure")

                logger2.info(f"Reconfigured message from worker {worker_id}")
                operations.append("use_reconfigured_logger")

                with lock:
                    operations_completed.append((worker_id, operations))

            except Exception as e:
                with lock:
                    errors.append(f"Worker {worker_id}: {e}")

        # Run lifecycle operations concurrently
        threads = []
        for i, container in enumerate(containers):
            thread = threading.Thread(target=lifecycle_worker, args=(container, i))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify no errors
        assert not errors, f"Errors occurred: {errors}"

        # Verify all operations completed
        assert len(operations_completed) == 8
        expected_operations = [
            "configure",
            "use_logger",
            "create_extra_loggers",
            "reset",
            "reconfigure",
            "use_reconfigured_logger",
        ]

        for worker_id, operations in operations_completed:
            assert operations == expected_operations, (
                f"Worker {worker_id} had incorrect operations: {operations}"
            )

        # Cleanup
        for container in containers:
            container.shutdown_sync()

    def test_race_condition_prevention(self):
        """Test that race conditions are prevented in concurrent access."""
        container = LoggingContainer()

        configuration_attempts = []
        errors = []
        lock = threading.Lock()

        def configure_worker(worker_id: int) -> None:
            """Worker that attempts to configure container."""
            try:
                # Multiple workers try to configure simultaneously
                logger = container.configure()
                assert container.is_configured
                assert hasattr(logger, "info")

                with lock:
                    configuration_attempts.append(worker_id)

            except Exception as e:
                with lock:
                    errors.append(f"Worker {worker_id}: {e}")

        # Start multiple workers simultaneously
        threads = []
        for i in range(10):
            thread = threading.Thread(target=configure_worker, args=(i,))
            threads.append(thread)

        # Start all threads at once
        for thread in threads:
            thread.start()

        # Wait for all to complete
        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert not errors, f"Race condition errors: {errors}"

        # All workers should have succeeded
        assert len(configuration_attempts) == 10

        # Container should be properly configured
        assert container.is_configured
        logger = container.get_logger("race_test")
        logger.info("Race condition test passed")

        # Cleanup
        container.shutdown_sync()

    def test_performance_under_concurrent_load(self):
        """Test performance characteristics under concurrent load."""
        container = LoggingContainer()
        container.configure()

        num_workers = 15
        loggers_per_worker = 20
        total_expected = num_workers * loggers_per_worker

        def performance_worker(worker_id: int) -> Tuple[int, float]:
            """Worker that creates loggers and measures time."""
            start_time = time.perf_counter()

            loggers_created = 0
            for i in range(loggers_per_worker):
                logger = container.get_logger(f"perf_worker_{worker_id}_logger_{i}")
                logger.info(f"Performance test message {i}")
                loggers_created += 1

            end_time = time.perf_counter()
            return loggers_created, end_time - start_time

        # Run performance test
        overall_start = time.perf_counter()

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(performance_worker, i) for i in range(num_workers)
            ]
            results = [future.result() for future in futures]

        overall_end = time.perf_counter()
        overall_time = overall_end - overall_start

        # Verify results
        total_created = sum(result[0] for result in results)
        assert total_created == total_expected

        # Performance checks
        assert overall_time < 10.0, (
            f"Concurrent load test too slow: {overall_time:.2f}s"
        )

        # Average time per worker should be reasonable
        avg_worker_time = sum(result[1] for result in results) / len(results)
        assert avg_worker_time < 2.0, (
            f"Average worker time too slow: {avg_worker_time:.2f}s"
        )

        # Cleanup
        container.shutdown_sync()
