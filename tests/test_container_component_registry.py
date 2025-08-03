"""Tests for LoggingContainer ComponentRegistry integration.

This module tests the enhanced LoggingContainer with ComponentRegistry
support for container-scoped component management.
"""

import threading
import time
from unittest.mock import patch

import pytest

from fapilog._internal.component_registry import ComponentRegistry
from fapilog._internal.metrics import MetricsCollector
from fapilog._internal.processor_metrics import ProcessorMetrics
from fapilog.async_components.concurrency.lock_manager import ProcessorLockManager
from fapilog.container import LoggingContainer
from fapilog.core.factories.component_factory import ComponentFactory
from fapilog.monitoring import PrometheusExporter
from fapilog.settings import LoggingSettings


class TestLoggingContainerComponentRegistry:
    """Test LoggingContainer ComponentRegistry integration."""

    def setup_method(self):
        """Set up test environment before each test."""
        self.settings = LoggingSettings(
            level="INFO",
            sinks=["stdout"],
        )
        self.settings.metrics.enabled = True
        self.settings.metrics.prometheus_enabled = True

    def test_container_has_registry_and_factory(self):
        """Test that container initializes with registry and factory."""
        container = LoggingContainer(self.settings)

        # Check registry and factory are created
        assert hasattr(container, "_registry")
        assert hasattr(container, "_factory")
        assert hasattr(container, "_container_id")

        # Check types (components are deferred until first use)
        # Call a method to initialize components
        container.get_lock_manager()
        assert isinstance(container._registry, ComponentRegistry)
        assert isinstance(container._factory, ComponentFactory)
        assert isinstance(container._container_id, str)

        # Check container ID format
        assert container._container_id.startswith("container_")

    def test_container_id_is_unique(self):
        """Test that each container gets a unique ID."""
        container1 = LoggingContainer(self.settings)
        container2 = LoggingContainer(self.settings)

        assert container1._container_id != container2._container_id

    def test_get_lock_manager(self):
        """Test container-scoped ProcessorLockManager access."""
        container = LoggingContainer(self.settings)

        # First access - should create new instance
        lock_manager1 = container.get_lock_manager()
        assert isinstance(lock_manager1, ProcessorLockManager)

        # Second access - should return same instance (cached)
        lock_manager2 = container.get_lock_manager()
        assert lock_manager1 is lock_manager2

    def test_get_processor_metrics(self):
        """Test container-scoped ProcessorMetrics access."""
        container = LoggingContainer(self.settings)

        # First access - should create new instance
        metrics1 = container.get_processor_metrics()
        assert isinstance(metrics1, ProcessorMetrics)

        # Second access - should return same instance (cached)
        metrics2 = container.get_processor_metrics()
        assert metrics1 is metrics2

    def test_get_metrics_collector_enabled(self):
        """Test MetricsCollector access when enabled."""
        container = LoggingContainer(self.settings)

        # Should return MetricsCollector when enabled
        collector = container.get_metrics_collector()
        assert isinstance(collector, MetricsCollector)

        # Should return same instance on subsequent calls
        collector2 = container.get_metrics_collector()
        assert collector is collector2

    def test_get_metrics_collector_disabled(self):
        """Test MetricsCollector access when disabled."""
        settings = LoggingSettings(
            level="INFO",
            sinks=["stdout"],
        )
        settings.metrics.enabled = False
        container = LoggingContainer(settings)

        # Should return None when disabled
        collector = container.get_metrics_collector()
        assert collector is None

    def test_get_prometheus_exporter_enabled(self):
        """Test PrometheusExporter access when enabled."""
        container = LoggingContainer(self.settings)

        # Should return PrometheusExporter when enabled
        exporter = container.get_prometheus_exporter()
        assert isinstance(exporter, PrometheusExporter)

        # Should return same instance on subsequent calls
        exporter2 = container.get_prometheus_exporter()
        assert exporter is exporter2

    def test_get_prometheus_exporter_disabled(self):
        """Test PrometheusExporter access when disabled."""
        settings = LoggingSettings(
            level="INFO",
            sinks=["stdout"],
        )
        settings.metrics.prometheus_enabled = False
        container = LoggingContainer(settings)

        # Should return None when disabled
        exporter = container.get_prometheus_exporter()
        assert exporter is None

    def test_component_isolation_between_containers(self):
        """Test that components are isolated between different containers."""
        container1 = LoggingContainer(self.settings)
        container2 = LoggingContainer(self.settings)

        # Get components from both containers
        lock_manager1 = container1.get_lock_manager()
        lock_manager2 = container2.get_lock_manager()

        processor_metrics1 = container1.get_processor_metrics()
        processor_metrics2 = container2.get_processor_metrics()

        metrics_collector1 = container1.get_metrics_collector()
        metrics_collector2 = container2.get_metrics_collector()

        # Components should be different instances
        assert lock_manager1 is not lock_manager2
        assert processor_metrics1 is not processor_metrics2
        assert metrics_collector1 is not metrics_collector2

    def test_component_caching_within_container(self):
        """Test that components are cached within the same container."""
        container = LoggingContainer(self.settings)

        # Get same component multiple times
        instances = []
        for _ in range(5):
            instances.append(container.get_lock_manager())

        # All instances should be the same object
        for instance in instances:
            assert instance is instances[0]

    def test_thread_safe_component_access(self):
        """Test thread-safe component access within container."""
        container = LoggingContainer(self.settings)
        components = []
        errors = []

        def get_component():
            try:
                lock_manager = container.get_lock_manager()
                components.append(lock_manager)
            except Exception as e:
                errors.append(e)

        # Create multiple threads accessing the same component
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=get_component)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(components) == 10

        # All components should be the same instance
        for component in components:
            assert component is components[0]

    def test_container_lifecycle_cleanup(self):
        """Test component cleanup when container is destroyed."""
        container = LoggingContainer(self.settings)

        # Access components to create them
        _lock_manager = container.get_lock_manager()
        _processor_metrics = container.get_processor_metrics()
        _metrics_collector = container.get_metrics_collector()

        # Verify components exist in registry
        assert container._registry is not None
        assert ProcessorLockManager in container._registry
        assert ProcessorMetrics in container._registry
        assert MetricsCollector in container._registry

        # Mock the registry cleanup method to verify it's called
        assert container._registry is not None
        with patch.object(container._registry, "cleanup") as mock_cleanup:
            container.shutdown_sync()
            mock_cleanup.assert_called_once()

    def test_backward_compatibility(self):
        """Test that existing container functionality is preserved."""
        container = LoggingContainer(self.settings)

        # Test existing properties and methods still work
        # Settings should be equivalent but not the same object (deep copied for isolation)
        assert container.settings == self.settings
        assert container.settings is not self.settings  # Ensure isolation
        assert not container.is_configured  # Not configured yet

        # Test logger access works
        logger = container.get_logger("test")
        assert logger is not None

        # Test context manager support
        with container as ctx:
            assert ctx is container
            assert container.is_configured

    def test_component_configuration_with_settings(self):
        """Test that components are configured with container settings."""
        # Create container with specific settings
        settings = LoggingSettings(
            level="DEBUG",
            sinks=["stdout"],
        )
        settings.metrics.enabled = True
        settings.metrics.sample_window = 200
        settings.metrics.prometheus_enabled = True
        settings.metrics.prometheus_port = 9000
        settings.metrics.prometheus_host = "127.0.0.1"
        container = LoggingContainer(settings)

        # Get components
        metrics_collector = container.get_metrics_collector()
        prometheus_exporter = container.get_prometheus_exporter()

        # Verify components are configured with container settings
        assert metrics_collector is not None
        assert prometheus_exporter is not None

        # Check that factory was called with equivalent settings (deep copied for isolation)
        assert container._factory._settings == settings
        assert container._factory._settings is not settings  # Ensure isolation

    def test_factory_integration(self):
        """Test integration with ComponentFactory."""
        container = LoggingContainer(self.settings)

        # Initialize components first
        container.get_lock_manager()

        # Verify factory is properly initialized with container
        assert container._factory is not None
        assert container._factory.container is container
        # Settings should be equivalent but not the same object (deep copied for isolation)
        assert container._factory._settings == self.settings
        assert container._factory._settings is not self.settings  # Ensure isolation

    def test_registry_integration(self):
        """Test integration with ComponentRegistry."""
        container = LoggingContainer(self.settings)

        # Initialize components first
        lock_manager = container.get_lock_manager()

        # Verify registry is properly initialized
        assert container._registry is not None
        assert container._registry.container_id == container._container_id

        # Test registry component tracking
        assert container._registry is not None
        assert ProcessorLockManager in container._registry
        assert container._registry.get_component(ProcessorLockManager) is lock_manager


class TestContainerAsyncSupport:
    """Test async support for container lifecycle."""

    def setup_method(self):
        """Set up test environment before each test."""
        self.settings = LoggingSettings(
            level="INFO",
            sinks=["stdout"],
        )
        self.settings.metrics.prometheus_enabled = True

    @pytest.mark.asyncio
    async def test_async_shutdown_with_registry_cleanup(self):
        """Test async shutdown includes registry cleanup."""
        container = LoggingContainer(self.settings)

        # Access components to create them
        container.get_lock_manager()
        container.get_prometheus_exporter()

        # Mock the registry cleanup method to verify it's called
        assert container._registry is not None
        with patch.object(container._registry, "cleanup") as mock_cleanup:
            await container.shutdown()
            mock_cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_setup_preserves_components(self):
        """Test async setup doesn't interfere with component access."""
        container = LoggingContainer(self.settings)
        container.configure()

        # Get components before setup
        lock_manager_before = container.get_lock_manager()
        prometheus_before = container.get_prometheus_exporter()

        # Run async setup
        await container.setup()

        # Get components after setup - should be same instances
        lock_manager_after = container.get_lock_manager()
        prometheus_after = container.get_prometheus_exporter()

        assert lock_manager_before is lock_manager_after
        assert prometheus_before is prometheus_after


class TestContainerErrorHandling:
    """Test error handling in container component access."""

    def setup_method(self):
        """Set up test environment before each test."""
        self.settings = LoggingSettings(level="INFO", sinks=["stdout"])

    def test_registry_cleanup_error_handling(self):
        """Test error handling during registry cleanup."""
        container = LoggingContainer(self.settings)

        # Mock registry to raise exception during cleanup
        # Initialize components first
        container.get_lock_manager()
        assert container._registry is not None
        with patch.object(
            container._registry, "cleanup", side_effect=Exception("Cleanup error")
        ):
            # Should not raise exception, should handle gracefully
            container.shutdown_sync()

    def test_factory_error_handling(self):
        """Test error handling when factory raises exception."""
        container = LoggingContainer(self.settings)

        # Initialize components first
        container.get_processor_metrics()  # Initialize but don't use the one we'll mock

        # Mock factory method to raise exception
        assert container._factory is not None
        with patch.object(
            container._factory,
            "create_lock_manager",
            side_effect=Exception("Factory error"),
        ):
            # Should raise the factory exception
            with pytest.raises(Exception, match="Factory error"):
                container.get_lock_manager()

    def test_component_access_with_invalid_settings(self):
        """Test component access with invalid or missing settings."""
        # Test with None settings (should use defaults)
        container = LoggingContainer(None)

        # Should still work with default settings
        lock_manager = container.get_lock_manager()
        assert isinstance(lock_manager, ProcessorLockManager)

        # Metrics should be disabled by default
        metrics_collector = container.get_metrics_collector()
        assert metrics_collector is None


class TestContainerPerformanceCharacteristics:
    """Test performance characteristics of container component access."""

    def setup_method(self):
        """Set up test environment before each test."""
        self.settings = LoggingSettings(
            level="INFO",
            sinks=["stdout"],
        )
        self.settings.metrics.enabled = True

    def test_component_creation_performance(self):
        """Test that component creation is reasonably fast."""
        container = LoggingContainer(self.settings)

        # Measure first access (creation)
        start_time = time.time()
        for _ in range(100):
            _ = container.get_lock_manager()
        creation_time = time.time() - start_time

        # Should be very fast for cached access
        assert creation_time < 1.0, f"Component access too slow: {creation_time}s"

    def test_concurrent_component_access_performance(self):
        """Test performance under concurrent access."""
        container = LoggingContainer(self.settings)
        results = []

        def measure_access():
            start = time.time()
            for _ in range(10):
                container.get_lock_manager()
            results.append(time.time() - start)

        # Run concurrent access
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=measure_access)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All access should be fast
        for duration in results:
            assert duration < 1.0, f"Concurrent access too slow: {duration}s"

    def test_memory_efficiency(self):
        """Test that component caching doesn't cause memory bloat."""
        container = LoggingContainer(self.settings)

        # Access all components multiple times
        for _ in range(100):
            container.get_lock_manager()
            container.get_processor_metrics()
            container.get_metrics_collector()

        # Should only have one instance of each component type
        assert container._registry is not None
        assert len(container._registry) <= 3
