"""Comprehensive Integration Tests for Refactored LoggingContainer Architecture.

This test suite validates the complete integration of the refactored LoggingContainer
with all specialized managers, ensuring no regressions from the original implementation
and validating all functionality works correctly with the new manager-based architecture.
"""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock

import pytest

from fapilog.container import LoggingContainer
from fapilog.exceptions import ConfigurationError
from fapilog.settings import LoggingSettings


class TestContainerArchitectureIntegration:
    """Test suite for comprehensive integration validation of refactored architecture."""

    def test_container_initialization_default(self):
        """Test container initialization with default settings."""
        container = LoggingContainer()

        assert container is not None
        assert isinstance(container.settings, LoggingSettings)
        assert not container.is_configured
        assert container.queue_worker is None
        assert container._container_id.startswith("container_")

    def test_container_initialization_custom_settings(self):
        """Test container initialization with custom settings."""
        settings = LoggingSettings()
        settings.level = "DEBUG"
        settings.metrics.enabled = True
        settings.queue.enabled = True

        container = LoggingContainer(settings)

        assert container.settings.level == "DEBUG"
        assert container.settings.metrics.enabled is True
        assert container.settings.queue.enabled is True
        assert not container.is_configured

    def test_container_factory_methods(self):
        """Test container factory methods work correctly."""
        # Test create_with_defaults
        container1 = LoggingContainer.create_with_defaults()
        assert container1 is not None
        assert isinstance(container1.settings, LoggingSettings)

        # Test create_from_settings
        settings = LoggingSettings()
        settings.level = "WARNING"
        container2 = LoggingContainer.create_from_settings(settings)
        assert container2.settings.level == "WARNING"

    def test_container_configure_basic(self):
        """Test basic container configuration functionality."""
        container = LoggingContainer()

        logger = container.configure()

        assert container.is_configured
        assert logger is not None
        # Logger should be a structlog logger (may be subclass like BoundLoggerFilteringAtInfo)
        assert hasattr(logger, "info") and hasattr(logger, "error")

    def test_container_configure_idempotent(self):
        """Test that multiple configure calls are idempotent."""
        container = LoggingContainer()

        logger1 = container.configure()
        logger2 = container.configure()

        assert container.is_configured
        assert logger1 is not None
        assert logger2 is not None

    def test_container_configure_with_custom_settings(self):
        """Test container configuration with custom settings."""
        container = LoggingContainer()
        custom_settings = LoggingSettings()
        custom_settings.level = "DEBUG"
        custom_settings.metrics.enabled = True

        logger = container.configure(settings=custom_settings)

        assert container.is_configured
        assert container.settings.level == "DEBUG"
        assert container.settings.metrics.enabled is True
        assert logger is not None

    def test_container_logger_creation(self):
        """Test logger creation and naming."""
        container = LoggingContainer()
        container.configure()

        # Test default logger
        default_logger = container.get_logger()
        assert default_logger is not None

        # Test named logger
        named_logger = container.get_logger("test.module")
        assert named_logger is not None

        # Loggers should be functional
        default_logger.info("Test message")
        named_logger.info("Test named message")

    def test_container_component_access_methods(self):
        """Test all component access methods work correctly."""
        container = LoggingContainer()
        container.configure()

        # Test core components
        lock_manager = container.get_lock_manager()
        assert lock_manager is not None

        processor_metrics = container.get_processor_metrics()
        assert processor_metrics is not None

        # Test optional components (may be None based on settings)
        _ = container.get_metrics_collector()
        _ = container.get_prometheus_exporter()
        # Note: These may be None based on settings, but we test they can be accessed

        # Test enricher components
        async_cache = container.get_async_smart_cache()
        assert async_cache is not None

        error_handler = container.get_enricher_error_handler()
        assert error_handler is not None

        health_monitor = container.get_enricher_health_monitor()
        assert health_monitor is not None

        retry_coordinator = container.get_retry_coordinator()
        assert retry_coordinator is not None

    def test_container_component_caching(self):
        """Test that components are properly cached/reused."""
        container = LoggingContainer()
        container.configure()

        # Get same component twice
        lock_manager1 = container.get_lock_manager()
        lock_manager2 = container.get_lock_manager()

        # Should be same instance (cached)
        assert lock_manager1 is lock_manager2

        # Test with other components
        cache1 = container.get_async_smart_cache()
        cache2 = container.get_async_smart_cache()
        assert cache1 is cache2

    def test_container_context_manager(self):
        """Test container context manager functionality."""
        container = LoggingContainer()

        with container as ctx:
            assert ctx is container
            logger = ctx.configure()
            assert logger is not None
            assert ctx.is_configured

        # Container should be properly cleaned up after context

    def test_container_scoped_logger(self):
        """Test scoped logger functionality."""
        container = LoggingContainer()

        with container.scoped_logger("test.scoped") as logger:
            assert logger is not None
            logger.info("Scoped logger test")

    @pytest.mark.asyncio
    async def test_container_async_setup(self):
        """Test container async setup functionality."""
        container = LoggingContainer()
        container.configure()

        await container.setup()

        # Container should still be configured after async setup
        assert container.is_configured

    def test_container_reset(self):
        """Test container reset functionality."""
        container = LoggingContainer()
        container.configure()

        assert container.is_configured

        container.reset()

        assert not container.is_configured

    def test_container_shutdown_sync(self):
        """Test synchronous shutdown functionality."""
        container = LoggingContainer()
        container.configure()

        assert container.is_configured

        container.shutdown_sync()

        # Container should still be marked as configured but cleaned up

    @pytest.mark.asyncio
    async def test_container_shutdown_async(self):
        """Test asynchronous shutdown functionality."""
        container = LoggingContainer()
        container.configure()

        assert container.is_configured

        await container.shutdown()

        # Container should be properly shut down


class TestContainerManagerIntegration:
    """Test integration between container and all managers."""

    def test_configuration_manager_integration(self):
        """Test ConfigurationManager integration."""
        container = LoggingContainer()

        # Test settings validation through ConfigurationManager
        # Use completely invalid settings structure to trigger validation error
        with pytest.raises(ConfigurationError):
            container.configure(settings="completely_invalid_settings")

    def test_lifecycle_manager_integration(self):
        """Test LifecycleManager integration."""
        container = LoggingContainer()
        container.configure()

        # LifecycleManager should have configured standard logging
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) > 0

    def test_sink_manager_integration(self):
        """Test SinkManager integration with queue enabled."""
        settings = LoggingSettings()
        settings.queue.enabled = True

        container = LoggingContainer(settings)
        container.configure()

        # Queue worker should be created when queue is enabled
        assert container.queue_worker is not None

    def test_middleware_manager_integration(self):
        """Test MiddlewareManager integration."""
        container = LoggingContainer()

        # Mock FastAPI app
        mock_app = Mock()
        mock_app.add_middleware = Mock()
        mock_app.add_event_handler = Mock()

        container.configure(app=mock_app)

        # Middleware should have been registered
        mock_app.add_middleware.assert_called()

    def test_metrics_manager_integration(self):
        """Test MetricsManager integration."""
        settings = LoggingSettings()
        settings.metrics.enabled = True
        settings.metrics.prometheus_enabled = True

        container = LoggingContainer(settings)
        container.configure()

        # Metrics components should be available
        metrics_collector = container.get_metrics_collector()
        _ = container.get_prometheus_exporter()
        # Note: prometheus_exporter may be None if FastAPI not available

        assert metrics_collector is not None
        # Note: prometheus_exporter may be None if FastAPI not available


class TestContainerPublicAPICompatibility:
    """Test that all public API methods work identically to original."""

    def test_configure_backwards_compatibility(self):
        """Test configure method backwards compatibility."""
        container = LoggingContainer()

        # Should work with no parameters
        logger1 = container.configure()
        assert logger1 is not None

        # Should work with settings parameter
        settings = LoggingSettings()
        settings.level = "DEBUG"
        logger2 = container.configure(settings=settings)
        assert logger2 is not None
        assert container.settings.level == "DEBUG"

    def test_get_logger_backwards_compatibility(self):
        """Test get_logger method backwards compatibility."""
        container = LoggingContainer()
        container.configure()

        # Should work with no name
        logger1 = container.get_logger()
        assert logger1 is not None

        # Should work with name
        logger2 = container.get_logger("test.module")
        assert logger2 is not None

    def test_properties_backwards_compatibility(self):
        """Test all properties work as expected."""
        container = LoggingContainer()

        # Test initial state
        assert isinstance(container.settings, LoggingSettings)
        assert not container.is_configured
        assert container.queue_worker is None

        # Test after configuration
        container.configure()
        assert container.is_configured

    def test_factory_methods_backwards_compatibility(self):
        """Test factory methods work as expected."""
        # Test create_with_defaults
        container1 = LoggingContainer.create_with_defaults()
        logger1 = container1.configure()
        assert logger1 is not None

        # Test create_from_settings
        settings = LoggingSettings()
        container2 = LoggingContainer.create_from_settings(settings)
        logger2 = container2.configure()
        assert logger2 is not None


class TestContainerThreadSafety:
    """Test thread-safety of the refactored container architecture."""

    def test_concurrent_container_operations(self):
        """Test concurrent operations on same container are thread-safe."""
        container = LoggingContainer()
        errors = []
        results = []

        def configure_and_log(thread_id: int) -> None:
            try:
                logger = container.configure()
                logger.info(f"Thread {thread_id} logging")
                results.append(f"thread_{thread_id}_success")
            except Exception as e:
                errors.append(f"thread_{thread_id}: {e}")

        # Run multiple threads concurrently
        threads = []
        for i in range(10):
            thread = threading.Thread(target=configure_and_log, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Should have no errors and all successes
        assert len(errors) == 0
        assert len(results) == 10
        assert container.is_configured

    def test_multiple_containers_different_threads(self):
        """Test multiple containers in different threads don't interfere."""
        results = {}
        errors = []

        def create_and_configure_container(thread_id: int) -> None:
            try:
                container = LoggingContainer()
                settings = LoggingSettings()
                settings.level = "INFO"  # Different settings per thread

                logger = container.configure(settings=settings)
                logger.info(f"Container {thread_id} configured")

                results[thread_id] = {
                    "configured": container.is_configured,
                    "level": container.settings.level,
                }
            except Exception as e:
                errors.append(f"thread_{thread_id}: {e}")

        # Create containers in different threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_and_configure_container, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Verify results
        assert len(errors) == 0
        assert len(results) == 5
        for i in range(5):
            assert results[i]["configured"] is True
            assert results[i]["level"] == "INFO"

    def test_concurrent_component_access(self):
        """Test concurrent access to container components is thread-safe."""
        container = LoggingContainer()
        container.configure()

        components = {}
        errors = []

        def access_components(thread_id: int) -> None:
            try:
                components[f"lock_manager_{thread_id}"] = container.get_lock_manager()
                components[f"processor_metrics_{thread_id}"] = (
                    container.get_processor_metrics()
                )
                components[f"async_cache_{thread_id}"] = (
                    container.get_async_smart_cache()
                )
            except Exception as e:
                errors.append(f"thread_{thread_id}: {e}")

        # Access components concurrently
        threads = []
        for i in range(10):
            thread = threading.Thread(target=access_components, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Should have no errors
        assert len(errors) == 0
        assert len(components) == 30  # 3 components * 10 threads

        # All lock managers should be the same instance (cached)
        lock_managers = [v for k, v in components.items() if "lock_manager" in k]
        assert all(lm is lock_managers[0] for lm in lock_managers)


class TestContainerIsolation:
    """Test container isolation between different container instances."""

    def test_settings_isolation(self):
        """Test that containers have isolated settings."""
        settings1 = LoggingSettings()
        settings1.level = "DEBUG"
        container1 = LoggingContainer(settings1)

        settings2 = LoggingSettings()
        settings2.level = "ERROR"
        container2 = LoggingContainer(settings2)

        container1.configure()
        container2.configure()

        # Settings should be isolated
        assert container1.settings.level == "DEBUG"
        assert container2.settings.level == "ERROR"

        # Containers should have different IDs
        assert container1._container_id != container2._container_id

    def test_component_isolation(self):
        """Test that components are isolated between containers."""
        container1 = LoggingContainer()
        container2 = LoggingContainer()

        container1.configure()
        container2.configure()

        # Components should be different instances
        lock_mgr1 = container1.get_lock_manager()
        lock_mgr2 = container2.get_lock_manager()
        assert lock_mgr1 is not lock_mgr2

        cache1 = container1.get_async_smart_cache()
        cache2 = container2.get_async_smart_cache()
        assert cache1 is not cache2

    def test_logger_isolation(self):
        """Test that loggers are isolated between containers."""
        container1 = LoggingContainer()
        container2 = LoggingContainer()

        logger1 = container1.configure()
        logger2 = container2.configure()

        # Loggers should be functional and independent
        logger1.info("Container 1 message")
        logger2.info("Container 2 message")

        # Should not interfere with each other


class TestContainerErrorHandling:
    """Test error handling and edge cases in container architecture."""

    def test_configuration_error_handling(self):
        """Test error handling during configuration."""
        container = LoggingContainer()

        # Test with invalid settings type
        with pytest.raises((TypeError, AttributeError)):
            container.configure(settings="invalid")

    def test_component_access_before_configuration(self):
        """Test accessing components before configuration."""
        container = LoggingContainer()

        # get_logger should auto-configure
        logger = container.get_logger()
        assert logger is not None
        assert container.is_configured

        # Other components should work after auto-configuration
        lock_manager = container.get_lock_manager()
        assert lock_manager is not None

    def test_repeated_reset_and_configure(self):
        """Test repeated reset and configure cycles."""
        container = LoggingContainer()

        for i in range(3):
            container.configure()
            assert container.is_configured

            logger = container.get_logger(f"test_{i}")
            logger.info(f"Cycle {i} message")

            container.reset()
            assert not container.is_configured

    def test_shutdown_after_shutdown(self):
        """Test multiple shutdown calls don't cause errors."""
        container = LoggingContainer()
        container.configure()

        # Multiple shutdowns should be safe
        container.shutdown_sync()
        container.shutdown_sync()

        # Should still be able to reconfigure
        container.configure()
        assert container.is_configured


class TestContainerPerformance:
    """Basic performance validation tests."""

    def test_configuration_performance(self):
        """Test that configuration performance is reasonable."""
        start_time = time.time()

        containers = []
        for _ in range(10):
            container = LoggingContainer()
            container.configure()
            containers.append(container)

        end_time = time.time()
        total_time = end_time - start_time

        # Should configure 10 containers in reasonable time (< 5 seconds)
        assert total_time < 5.0

        # Clean up
        for container in containers:
            container.shutdown_sync()

    def test_logger_creation_performance(self):
        """Test logger creation performance."""
        container = LoggingContainer()
        container.configure()

        start_time = time.time()

        loggers = []
        for i in range(100):
            logger = container.get_logger(f"test.module.{i}")
            loggers.append(logger)

        end_time = time.time()
        total_time = end_time - start_time

        # Should create 100 loggers quickly (< 1 second)
        assert total_time < 1.0
        assert len(loggers) == 100

    def test_component_access_performance(self):
        """Test component access performance."""
        container = LoggingContainer()
        container.configure()

        start_time = time.time()

        # Access components multiple times
        for _ in range(50):
            _ = container.get_lock_manager()
            _ = container.get_processor_metrics()
            _ = container.get_async_smart_cache()

        end_time = time.time()
        total_time = end_time - start_time

        # Component access should be fast due to caching (< 0.5 seconds)
        assert total_time < 0.5


class TestContainerStressScenarios:
    """Stress tests for high-load scenarios."""

    def test_high_concurrency_stress(self):
        """Test container under high concurrency stress."""
        container = LoggingContainer()
        container.configure()

        errors = []
        success_count = 0

        def stress_worker(worker_id: int) -> None:
            nonlocal success_count
            try:
                for i in range(10):
                    logger = container.get_logger(f"stress.worker.{worker_id}.{i}")
                    logger.info(f"Stress test message {i}")

                    # Access various components
                    _ = container.get_lock_manager()
                    _ = container.get_processor_metrics()
                    _ = container.get_async_smart_cache()

                success_count += 1
            except Exception as e:
                errors.append(f"worker_{worker_id}: {e}")

        # Run high number of concurrent workers
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(stress_worker, i) for i in range(50)]

            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    errors.append(f"Future error: {e}")

        # Should handle high concurrency without errors
        assert len(errors) == 0
        assert success_count == 50

    def test_rapid_container_creation_destruction(self):
        """Test rapid creation and destruction of containers."""
        containers = []
        errors = []

        try:
            for i in range(20):
                container = LoggingContainer()
                container.configure()

                logger = container.get_logger(f"rapid.test.{i}")
                logger.info(f"Rapid container {i}")

                containers.append(container)

        except Exception as e:
            errors.append(f"Creation error: {e}")

        # Clean up all containers
        try:
            for container in containers:
                container.shutdown_sync()
        except Exception as e:
            errors.append(f"Cleanup error: {e}")

        assert len(errors) == 0
        assert len(containers) == 20


@pytest.mark.asyncio
class TestContainerAsyncIntegration:
    """Test async functionality integration."""

    async def test_async_setup_multiple_containers(self):
        """Test async setup with multiple containers."""
        containers = []

        for _ in range(5):
            container = LoggingContainer()
            container.configure()
            await container.setup()
            containers.append(container)

        # All should be configured
        for container in containers:
            assert container.is_configured

        # Clean up
        for container in containers:
            await container.shutdown()

    async def test_async_shutdown_sequence(self):
        """Test proper async shutdown sequence."""
        container = LoggingContainer()
        container.configure()
        await container.setup()

        assert container.is_configured

        await container.shutdown()

        # Should be able to reconfigure after shutdown
        container.configure()
        assert container.is_configured
