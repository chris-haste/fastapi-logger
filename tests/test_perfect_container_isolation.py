"""Perfect container isolation tests for factory-based architecture.

This test module validates that multiple LoggingContainer instances achieve
perfect isolation without any shared state or interference, demonstrating
the benefits of the factory-based approach over global configuration.
"""

import concurrent.futures
import threading
import time
from typing import Tuple

import pytest

from fapilog.config import LoggingSettings
from fapilog.container import LoggingContainer


class TestPerfectContainerIsolation:
    """Test that containers achieve perfect isolation."""

    def test_multiple_containers_different_configurations(self):
        """Test containers with different settings don't interfere."""
        # Container 1: DEBUG level, JSON format
        from fapilog.config.sink_settings import SinkSettings

        settings1 = LoggingSettings(
            level="DEBUG", sinks=SinkSettings(json_console="json")
        )
        container1 = LoggingContainer(settings1)

        # Container 2: ERROR level, pretty format
        settings2 = LoggingSettings(
            level="ERROR", sinks=SinkSettings(json_console="pretty")
        )
        container2 = LoggingContainer(settings2)

        # Configure both
        logger1 = container1.configure()
        logger2 = container2.configure()

        # Verify complete isolation
        assert container1 is not container2
        assert container1._logger_factory is not container2._logger_factory
        assert container1._settings.level != container2._settings.level
        assert container1._console_format != container2._console_format
        assert container1._container_id != container2._container_id

        # Verify loggers are independent
        assert logger1 is not logger2
        assert hasattr(logger1, "info") and hasattr(logger1, "debug")
        assert hasattr(logger2, "info") and hasattr(logger2, "error")

        # Cleanup
        container1.shutdown_sync()
        container2.shutdown_sync()

    def test_concurrent_container_creation(self):
        """Test creating containers concurrently doesn't cause interference."""

        def create_container(container_id: int) -> Tuple[LoggingContainer, object]:
            """Create a container with unique settings."""
            from fapilog.config.sink_settings import SinkSettings

            settings = LoggingSettings(
                level="INFO",
                sinks=SinkSettings(
                    json_console="json" if container_id % 2 == 0 else "pretty"
                ),
            )
            container = LoggingContainer(settings)
            logger = container.configure()
            return container, logger

        # Create 10 containers concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_container, i) for i in range(10)]
            results = [future.result() for future in futures]

        # Verify all containers are independent
        containers = [result[0] for result in results]
        loggers = [result[1] for result in results]

        # Test pairwise independence
        for i, container in enumerate(containers):
            for j, other_container in enumerate(containers):
                if i != j:
                    assert container is not other_container
                    assert (
                        container._logger_factory is not other_container._logger_factory
                    )
                    assert container._container_id != other_container._container_id

        # Verify all loggers are functional
        for logger in loggers:
            assert hasattr(logger, "info")
            logger.info("Test message from concurrent creation")

        # Cleanup all containers
        for container in containers:
            container.shutdown_sync()

    def test_factory_independence_verification(self):
        """Test that factories are completely independent between containers."""
        # Create multiple containers
        containers = []
        for i in range(5):
            from fapilog.config.sink_settings import SinkSettings

            settings = LoggingSettings(
                level=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"][i],
                sinks=SinkSettings(json_console="json" if i % 2 == 0 else "pretty"),
            )
            container = LoggingContainer(settings)
            container.configure()
            containers.append(container)

        # Verify factory independence
        for i, container in enumerate(containers):
            # Each container should have its own factory
            assert container._logger_factory is not None

            # Factory uses lazy initialization, so trigger configuration by creating a logger
            _test_logger = container.get_logger(f"trigger_config_{i}")
            assert container._logger_factory.is_configured()

            # Factory should be unique to this container
            for j, other_container in enumerate(containers):
                if i != j:
                    assert (
                        container._logger_factory is not other_container._logger_factory
                    )

        # Test logger creation independence
        for i, container in enumerate(containers):
            logger = container.get_logger(f"test_logger_{i}")
            assert hasattr(logger, "info")
            logger.info(f"Message from container {i}")

        # Cleanup
        for container in containers:
            container.shutdown_sync()

    def test_zero_shared_state_validation(self):
        """Test that containers share absolutely no state."""
        # Create containers with identical settings to test even more isolation
        from fapilog.config.sink_settings import SinkSettings

        settings = LoggingSettings(
            level="INFO", sinks=SinkSettings(json_console="json")
        )

        container1 = LoggingContainer(settings)
        container2 = LoggingContainer(settings)

        # Configure both
        _logger1 = container1.configure()
        logger2 = container2.configure()

        # Even with identical settings, containers should be completely independent
        assert container1 is not container2
        assert container1._logger_factory is not container2._logger_factory
        # Settings should be separate instances (deep copied for isolation)
        assert container1._settings is not container2._settings
        assert container1._container_id != container2._container_id

        # Test that modifying one doesn't affect the other
        # Reset one container
        container1.reset()
        assert not container1.is_configured
        assert container2.is_configured  # Should remain configured

        # Reconfigure first container
        logger1_new = container1.configure()
        assert container1.is_configured
        assert container2.is_configured

        # Both should work independently
        logger1_new.info("Message from container 1")
        logger2.info("Message from container 2")

        # Cleanup
        container1.shutdown_sync()
        container2.shutdown_sync()

    def test_container_settings_isolation(self):
        """Test that container settings don't interfere with each other."""
        # Create containers with different sink configurations
        from fapilog.config.sink_settings import SinkSettings

        settings1 = LoggingSettings(
            level="DEBUG", sinks=SinkSettings(sinks=["stdout"], json_console="json")
        )
        settings1.queue.enabled = False
        settings2 = LoggingSettings(
            level="WARNING", sinks=SinkSettings(sinks=["stdout"], json_console="pretty")
        )
        settings2.queue.enabled = True

        container1 = LoggingContainer(settings1)
        container2 = LoggingContainer(settings2)

        # Configure containers
        _logger1 = container1.configure()
        _logger2 = container2.configure()

        # Verify settings isolation
        assert container1._settings.level != container2._settings.level
        assert (
            container1._settings.sinks.json_console
            != container2._settings.sinks.json_console
        )
        assert container1._settings.queue.enabled != container2._settings.queue.enabled

        # Verify that changing settings on one doesn't affect the other
        original_level = container2._settings.level
        container1._settings = LoggingSettings(level="CRITICAL")

        # Container2 should be unaffected
        assert container2._settings.level == original_level

        # Cleanup
        container1.shutdown_sync()
        container2.shutdown_sync()

    def test_logger_namespace_isolation(self):
        """Test that logger namespaces are isolated between containers."""
        container1 = LoggingContainer()
        container2 = LoggingContainer()

        container1.configure()
        container2.configure()

        # Create loggers with same names in different containers
        logger1_app = container1.get_logger("app")
        logger1_db = container1.get_logger("database")

        logger2_app = container2.get_logger("app")
        logger2_db = container2.get_logger("database")

        # Loggers should be different instances even with same names
        assert logger1_app is not logger2_app
        assert logger1_db is not logger2_db

        # All loggers should be functional
        loggers = [logger1_app, logger1_db, logger2_app, logger2_db]
        for i, logger in enumerate(loggers):
            assert hasattr(logger, "info")
            logger.info(f"Test message from logger {i}")

        # Cleanup
        container1.shutdown_sync()
        container2.shutdown_sync()

    def test_container_lifecycle_independence(self):
        """Test that container lifecycle operations don't affect other containers."""
        containers = []

        # Create multiple containers
        for _i in range(3):
            container = LoggingContainer()
            container.configure()
            containers.append(container)

        # Shutdown one container
        containers[1].shutdown_sync()

        # Other containers should remain functional
        logger0 = containers[0].get_logger("test0")
        logger2 = containers[2].get_logger("test2")

        logger0.info("Container 0 still works")
        logger2.info("Container 2 still works")

        # Reset one container
        containers[0].reset()
        assert not containers[0].is_configured
        assert containers[2].is_configured  # Should remain unaffected

        # Cleanup remaining containers
        containers[0].shutdown_sync()
        containers[2].shutdown_sync()

    def test_threading_container_isolation(self):
        """Test container isolation in multi-threaded environment."""
        results = {}
        errors = []

        def worker_thread(thread_id: int) -> None:
            """Worker function that creates and uses a container."""
            try:
                # Each thread creates its own container
                from fapilog.config.sink_settings import SinkSettings

                settings = LoggingSettings(
                    level="INFO", sinks=SinkSettings(json_console="json")
                )
                container = LoggingContainer(settings)
                logger = container.configure()

                # Store results for verification
                results[thread_id] = {
                    "container": container,
                    "logger": logger,
                    "container_id": container._container_id,
                    "factory": container._logger_factory,
                }

                # Use the logger
                logger.info(f"Message from thread {thread_id}")

                # Keep container alive until test is done
                time.sleep(0.1)

            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")

        # Create multiple threads with containers
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker_thread, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert not errors, f"Errors in threads: {errors}"

        # Verify all containers are independent
        assert len(results) == 5
        container_ids = [result["container_id"] for result in results.values()]
        factories = [result["factory"] for result in results.values()]

        # All container IDs should be unique
        assert len(set(container_ids)) == 5

        # All factories should be unique
        for i, factory1 in enumerate(factories):
            for j, factory2 in enumerate(factories):
                if i != j:
                    assert factory1 is not factory2

        # Cleanup all containers
        for result in results.values():
            container = result["container"]
            if hasattr(container, "shutdown_sync"):
                container.shutdown_sync()

    def test_memory_isolation_multiple_containers(self):
        """Test that containers don't share memory or cause memory leaks."""
        import gc

        # Force garbage collection before test
        gc.collect()

        containers = []
        initial_object_count = len(gc.get_objects())

        # Create and configure multiple containers
        for _i in range(10):
            from fapilog.config.sink_settings import SinkSettings

            settings = LoggingSettings(
                level="INFO", sinks=SinkSettings(json_console="json")
            )
            container = LoggingContainer(settings)
            container.configure()
            containers.append(container)

        # Use containers
        for i, container in enumerate(containers):
            logger = container.get_logger(f"test_{i}")
            logger.info(f"Test message {i}")

        # Cleanup containers
        for container in containers:
            container.shutdown_sync()

        # Clear references
        containers.clear()

        # Force garbage collection
        gc.collect()

        # Object count should not have grown significantly
        final_object_count = len(gc.get_objects())
        object_growth = final_object_count - initial_object_count

        # Allow some growth but not excessive (< 100 objects per container)
        assert object_growth < 1000, f"Too many objects created: {object_growth}"

    def test_container_error_isolation(self):
        """Test that errors in one container don't affect others."""
        container1 = LoggingContainer()
        container2 = LoggingContainer()

        container1.configure()
        container2.configure()

        # Force an error in container1 by corrupting its state
        original_factory = container1._logger_factory
        container1._logger_factory = None

        # Container1 should fail
        with pytest.raises(RuntimeError):
            container1.get_logger("test")

        # Container2 should remain unaffected
        logger2 = container2.get_logger("test")
        assert hasattr(logger2, "info")
        logger2.info("Container 2 works despite container 1 error")

        # Restore container1 for cleanup
        container1._logger_factory = original_factory

        # Cleanup
        container1.shutdown_sync()
        container2.shutdown_sync()
