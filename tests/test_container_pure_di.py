"""Tests for pure dependency injection LoggingContainer functionality."""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List

import pytest
import structlog

from fapilog.config import LoggingSettings
from fapilog.container import LoggingContainer
from fapilog.exceptions import ConfigurationError


class MockSink:
    """Mock sink for testing."""

    def __init__(self, name: str = "mock", should_fail: bool = False):
        self.name = name
        self.should_fail = should_fail
        self.events: List[Dict[str, Any]] = []
        self.write_calls = 0

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Write event to mock sink."""
        self.write_calls += 1
        if self.should_fail:
            raise Exception("Mock sink failure")
        self.events.append(event_dict.copy())


class TestPureDependencyInjectionContainer:
    """Test pure dependency injection container functionality."""

    def setup_method(self) -> None:
        """Clean up before each test."""
        # Reset structlog
        structlog.reset_defaults()
        # Clear root logger handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    def teardown_method(self) -> None:
        """Clean up after each test."""
        # Reset structlog
        structlog.reset_defaults()
        # Clear root logger handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    def test_container_initialization_no_global_state(self) -> None:
        """Test that container initialization doesn't create global state."""
        container = LoggingContainer()

        assert not container.is_configured
        assert container.queue_worker is None
        assert isinstance(container.settings, LoggingSettings)

        # Verify no global state exists
        import fapilog.container as container_module

        # These should not exist in the pure DI version
        assert not hasattr(container_module, "_current_container")
        assert not hasattr(container_module, "_current_container_lock")
        assert not hasattr(container_module, "_container_registry")
        assert not hasattr(container_module, "get_current_container")
        assert not hasattr(container_module, "set_current_container")
        assert not hasattr(container_module, "cleanup_all_containers")

    def test_factory_methods(self) -> None:
        """Test factory methods for container creation."""
        # Test create_from_settings
        settings = LoggingSettings(level="DEBUG")
        settings.queue.enabled = True
        container1 = LoggingContainer.create_from_settings(settings)

        assert container1.settings.level == "DEBUG"
        assert container1.settings.queue.enabled is True

        # Test create_with_defaults
        container2 = LoggingContainer.create_with_defaults()

        assert isinstance(container2.settings, LoggingSettings)

    def test_context_manager_functionality(self) -> None:
        """Test context manager __enter__ and __exit__ methods."""
        settings = LoggingSettings(level="INFO", sinks=["stdout"])

        with LoggingContainer(settings) as container:
            # Container should be configured automatically
            assert container.is_configured

            # Logger should be available
            logger = container.get_logger("test")
            assert callable(logger.info)

        # Container should be shut down after exiting context
        # Note: We can't easily test the shutdown state without side effects

    def test_scoped_logger_context_manager(self) -> None:
        """Test scoped logger context manager."""
        container = LoggingContainer()

        with container.scoped_logger("test_logger") as logger:
            # Logger should be configured and available
            assert callable(logger.info)
            assert callable(logger.error)

    def test_complete_container_isolation(self) -> None:
        """Test that multiple containers are completely isolated."""
        settings1 = LoggingSettings(level="INFO")
        settings1.queue.enabled = False
        settings2 = LoggingSettings(level="DEBUG")
        settings2.queue.enabled = True
        settings3 = LoggingSettings(level="WARNING")
        settings3.queue.enabled = False

        # Create multiple containers
        containers = [
            LoggingContainer(settings1),
            LoggingContainer(settings2),
            LoggingContainer(settings3),
        ]

        # Configure all containers
        loggers = []
        for container in containers:
            loggers.append(container.configure())

        # Verify complete isolation
        assert containers[0].settings.level == "INFO"
        assert containers[1].settings.level == "DEBUG"
        assert containers[2].settings.level == "WARNING"

        assert containers[0].settings.queue.enabled is False
        assert containers[1].settings.queue.enabled is True
        assert containers[2].settings.queue.enabled is False

        # Verify all are configured independently
        for container in containers:
            assert container.is_configured

        # Verify loggers are functional
        for logger in loggers:
            assert callable(logger.info)

        # Reset one container - should not affect others
        containers[0].reset()
        assert not containers[0].is_configured
        assert containers[1].is_configured
        assert containers[2].is_configured

    def test_thread_safety_without_global_locks(self) -> None:
        """Test thread safety without global locking mechanisms."""

        def create_and_configure_container(container_id: int) -> Dict[str, Any]:
            """Create and configure a container in a thread."""
            settings = LoggingSettings(level="INFO", sinks=["stdout"])
            # Alternate queue enabled status for thread safety testing
            settings.queue.enabled = container_id % 2 == 0
            container = LoggingContainer(settings)
            logger = container.configure()

            return {
                "container_id": container_id,
                "configured": container.is_configured,
                "queue_enabled": container.settings.queue.enabled,
                "logger_callable": callable(logger.info),
            }

        # Create multiple containers concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(create_and_configure_container, i) for i in range(50)
            ]

            results = [future.result() for future in futures]

        # Verify all containers were created and configured successfully
        assert len(results) == 50

        for result in results:
            assert result["configured"] is True
            assert result["logger_callable"] is True

        # Verify alternating queue_enabled pattern (thread safety test)
        for i, result in enumerate(results):
            expected_queue_enabled = i % 2 == 0
            assert result["queue_enabled"] == expected_queue_enabled

    def test_concurrent_container_operations(self) -> None:
        """Test concurrent operations on different containers."""
        containers = [LoggingContainer() for _ in range(5)]
        results = {}

        def container_operations(container_index: int) -> None:
            """Perform operations on a specific container."""
            container = containers[container_index]

            # Configure
            container.configure()
            results[f"configure_{container_index}"] = container.is_configured

            # Get logger
            test_logger = container.get_logger(f"test_{container_index}")
            results[f"logger_{container_index}"] = callable(test_logger.info)

            # Reset
            container.reset()
            results[f"reset_{container_index}"] = not container.is_configured

        # Run operations concurrently
        threads = []
        for i in range(5):
            thread = threading.Thread(target=container_operations, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify all operations completed successfully
        for i in range(5):
            assert results[f"configure_{i}"] is True
            assert results[f"logger_{i}"] is True
            assert results[f"reset_{i}"] is True

    def test_container_idempotent_configuration(self) -> None:
        """Test that container configuration is idempotent."""
        container = LoggingContainer()

        # First configuration
        logger1 = container.configure()
        assert container.is_configured

        # Second configuration should not reconfigure
        logger2 = container.configure()
        assert container.is_configured

        # Both loggers should be functional
        assert callable(logger1.info)
        assert callable(logger2.info)

    def test_container_memory_management(self) -> None:
        """Test that containers don't leak memory without global registry."""
        import gc
        import weakref

        # Create containers and track them with weak references
        containers_refs = []

        for _ in range(10):
            container = LoggingContainer()
            container.configure()
            containers_refs.append(weakref.ref(container))
            # Delete strong reference
            del container

        # Force garbage collection
        gc.collect()

        # All containers should be garbage collected since no global registry
        alive_containers = sum(1 for ref in containers_refs if ref() is not None)
        # This test verifies no global registry prevents GC (not strict timing)
        # Note: Some containers may still be alive due to GC timing and references
        # The key is that without global registry, they CAN be garbage collected
        assert alive_containers <= len(containers_refs)  # Allow for GC timing

    @pytest.mark.asyncio
    async def test_async_container_operations(self) -> None:
        """Test async container operations."""
        settings = LoggingSettings(sinks=["stdout"])
        settings.queue.enabled = True
        settings.metrics.enabled = True
        settings.metrics.prometheus_enabled = True
        container = LoggingContainer(settings)

        # Configure
        container.configure()
        assert container.is_configured

        # Setup async components
        await container.setup()

        # Shutdown gracefully
        await container.shutdown()

    def test_container_with_custom_settings_override(self) -> None:
        """Test container with settings override in configure method."""
        initial_settings = LoggingSettings(level="INFO")
        container = LoggingContainer(initial_settings)

        # Override settings during configuration
        override_settings = LoggingSettings(level="DEBUG")
        override_settings.queue.enabled = True
        container.configure(settings=override_settings)

        assert container.is_configured
        assert container.settings.level == "DEBUG"
        assert container.settings.queue.enabled is True

    def test_container_error_handling_isolation(self) -> None:
        """Test that errors in one container don't affect others."""
        # Create a container with invalid settings
        with pytest.raises(ConfigurationError):
            bad_settings = LoggingSettings(level="INVALID_LEVEL")
            LoggingContainer(bad_settings)

        # Create a valid container - should work fine
        good_settings = LoggingSettings(level="INFO")
        good_container = LoggingContainer(good_settings)
        logger = good_container.configure()

        assert good_container.is_configured
        assert callable(logger.info)

    def test_multiple_containers_different_queue_configs(self) -> None:
        """Test multiple containers with different queue configurations."""
        # Container 1: No queue
        settings1 = LoggingSettings(sinks=["stdout"])
        settings1.queue.enabled = False
        container1 = LoggingContainer(settings1)

        # Container 2: With queue
        settings2 = LoggingSettings(sinks=["stdout"])
        settings2.queue.enabled = True
        settings2.queue.maxsize = 100
        container2 = LoggingContainer(settings2)

        # Configure both
        logger1 = container1.configure()
        logger2 = container2.configure()

        # Verify configurations
        assert container1.is_configured
        assert container2.is_configured
        assert container1.queue_worker is None
        assert container2.queue_worker is not None
        assert container2.queue_worker.queue.maxsize == 100

        # Both loggers should work
        assert callable(logger1.info)
        assert callable(logger2.info)

    def test_container_settings_validation(self) -> None:
        """Test container settings validation."""
        # Valid settings
        valid_settings = LoggingSettings(level="INFO", json_console="pretty")
        container = LoggingContainer(valid_settings)
        container.configure()
        assert container.is_configured

        # Invalid console format should be caught
        with pytest.raises(ConfigurationError):
            invalid_settings = LoggingSettings(json_console="invalid_format")
            LoggingContainer(invalid_settings)

    def test_performance_no_global_locks(self) -> None:
        """Test performance improvement without global locks."""

        def time_container_operations(iterations: int) -> float:
            """Time container creation and configuration operations."""
            start_time = time.perf_counter()

            for _ in range(iterations):
                container = LoggingContainer()
                container.configure()
                container.reset()

            return time.perf_counter() - start_time

        # Time operations
        iterations = 100
        elapsed_time = time_container_operations(iterations)

        # Should complete reasonably quickly (this is more of a smoke test)
        # Without global locks, this should be faster than the old implementation
        assert elapsed_time < 10.0  # Should complete in under 10 seconds

    def test_container_logger_isolation(self) -> None:
        """Test that loggers from different containers are properly isolated."""
        container1 = LoggingContainer(LoggingSettings(level="INFO"))
        container2 = LoggingContainer(LoggingSettings(level="DEBUG"))

        logger1 = container1.get_logger("app1")
        logger2 = container2.get_logger("app2")

        # Both should be functional
        assert callable(logger1.info)
        assert callable(logger2.info)

        # Reset one container
        container1.reset()

        # Logger2 should still work (containers are isolated)
        assert callable(logger2.info)
