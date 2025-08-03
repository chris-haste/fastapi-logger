"""Tests for ComponentFactory - Factory for creating container-scoped components."""

from unittest.mock import Mock

import pytest

from fapilog._internal.async_lock_manager import ProcessorLockManager
from fapilog._internal.component_factory import ComponentFactory, ManagerSet
from fapilog._internal.metrics import MetricsCollector
from fapilog._internal.processor_metrics import ProcessorMetrics
from fapilog.container import LoggingContainer
from fapilog.core.managers.configuration_manager import ConfigurationManager
from fapilog.core.managers.lifecycle_manager import LifecycleManager
from fapilog.core.managers.middleware_manager import MiddlewareManager
from fapilog.core.managers.sink_manager import SinkManager
from fapilog.monitoring import PrometheusExporter
from fapilog.settings import LoggingSettings


class TestComponentFactoryBasicOperations:
    """Test basic ComponentFactory operations."""

    def test_factory_initialization(self):
        """Test ComponentFactory initialization with container."""
        settings = LoggingSettings()
        container = LoggingContainer(settings)
        factory = ComponentFactory(container)

        assert factory.container is container
        # Settings should be equivalent but not the same object (deep copied for isolation)
        assert factory._settings == settings
        assert factory._settings is not settings  # Ensure isolation

    def test_factory_repr(self):
        """Test ComponentFactory string representation."""
        container = LoggingContainer()
        factory = ComponentFactory(container)

        repr_str = repr(factory)
        assert "ComponentFactory" in repr_str
        assert "container_id" in repr_str

    def test_factory_with_custom_settings(self):
        """Test ComponentFactory with custom LoggingSettings."""
        # Test that backward compatibility properties work
        custom_settings = LoggingSettings()
        # Use properties to set values
        custom_settings.metrics.enabled = True
        custom_settings.metrics.sample_window = 200
        custom_settings.metrics.prometheus_enabled = True
        custom_settings.metrics.prometheus_host = "localhost"
        custom_settings.metrics.prometheus_port = 9090

        container = LoggingContainer(custom_settings)
        factory = ComponentFactory(container)

        # Settings should be equivalent but not the same object (deep copied for isolation)
        assert factory._settings == custom_settings
        assert factory._settings is not custom_settings  # Ensure isolation
        assert factory._settings.metrics.enabled is True
        assert factory._settings.metrics.sample_window == 200


class TestComponentFactoryLockManager:
    """Test ComponentFactory lock manager creation."""

    def test_create_lock_manager_basic(self):
        """Test basic lock manager creation."""
        container = LoggingContainer()
        factory = ComponentFactory(container)

        lock_manager = factory.create_lock_manager()

        assert isinstance(lock_manager, ProcessorLockManager)
        assert hasattr(lock_manager, "get_async_lock")
        assert hasattr(lock_manager, "get_sync_lock")

    def test_create_lock_manager_multiple_instances(self):
        """Test multiple lock manager instances are independent."""
        container = LoggingContainer()
        factory = ComponentFactory(container)

        manager1 = factory.create_lock_manager()
        manager2 = factory.create_lock_manager()

        assert isinstance(manager1, ProcessorLockManager)
        assert isinstance(manager2, ProcessorLockManager)
        assert manager1 is not manager2  # Should be different instances

    def test_create_lock_manager_with_different_containers(self):
        """Test lock manager creation with different containers."""
        container1 = LoggingContainer()
        container2 = LoggingContainer()
        factory1 = ComponentFactory(container1)
        factory2 = ComponentFactory(container2)

        manager1 = factory1.create_lock_manager()
        manager2 = factory2.create_lock_manager()

        assert manager1 is not manager2
        assert isinstance(manager1, ProcessorLockManager)
        assert isinstance(manager2, ProcessorLockManager)


class TestComponentFactoryProcessorMetrics:
    """Test ComponentFactory processor metrics creation."""

    def test_create_processor_metrics_basic(self):
        """Test basic processor metrics creation."""
        container = LoggingContainer()
        factory = ComponentFactory(container)

        metrics = factory.create_processor_metrics()

        assert isinstance(metrics, ProcessorMetrics)
        assert hasattr(metrics, "record_processor_execution")
        assert hasattr(metrics, "get_processor_stats")

    def test_create_processor_metrics_multiple_instances(self):
        """Test multiple processor metrics instances are independent."""
        container = LoggingContainer()
        factory = ComponentFactory(container)

        metrics1 = factory.create_processor_metrics()
        metrics2 = factory.create_processor_metrics()

        assert isinstance(metrics1, ProcessorMetrics)
        assert isinstance(metrics2, ProcessorMetrics)
        assert metrics1 is not metrics2  # Should be different instances

    def test_processor_metrics_functionality(self):
        """Test processor metrics basic functionality."""
        container = LoggingContainer()
        factory = ComponentFactory(container)

        metrics = factory.create_processor_metrics()

        # Test recording an execution
        metrics.record_processor_execution(
            "test_processor", latency_ms=10.5, success=True
        )

        # Should not raise exceptions
        processor_metrics = metrics.get_processor_stats("test_processor")
        assert processor_metrics is not None


class TestComponentFactoryMetricsCollector:
    """Test ComponentFactory metrics collector creation."""

    def test_create_metrics_collector_enabled(self):
        """Test metrics collector creation when enabled."""
        settings = LoggingSettings()
        settings.metrics.enabled = True
        settings.metrics.sample_window = 150
        container = LoggingContainer(settings)
        factory = ComponentFactory(container)

        collector = factory.create_metrics_collector()

        assert isinstance(collector, MetricsCollector)
        assert collector.enabled is True
        assert collector.sample_window == 150

    def test_create_metrics_collector_disabled(self):
        """Test metrics collector creation when disabled."""
        settings = LoggingSettings()
        settings.metrics.enabled = False
        container = LoggingContainer(settings)
        factory = ComponentFactory(container)

        collector = factory.create_metrics_collector()

        assert collector is None

    def test_create_metrics_collector_default_settings(self):
        """Test metrics collector with default settings."""
        # Default LoggingSettings should have metrics enabled
        container = LoggingContainer()
        factory = ComponentFactory(container)

        collector = factory.create_metrics_collector()

        if container._settings.metrics.enabled:
            assert isinstance(collector, MetricsCollector)
            assert collector.enabled is True
        else:
            assert collector is None

    def test_metrics_collector_functionality(self):
        """Test metrics collector basic functionality."""
        settings = LoggingSettings()
        settings.metrics.enabled = True
        container = LoggingContainer(settings)
        factory = ComponentFactory(container)

        collector = factory.create_metrics_collector()

        assert collector is not None
        assert hasattr(collector, "record_enqueue")
        assert hasattr(collector, "is_enabled")
        assert collector.is_enabled() is True


class TestComponentFactoryPrometheusExporter:
    """Test ComponentFactory Prometheus exporter creation."""

    def test_create_prometheus_exporter_enabled(self):
        """Test Prometheus exporter creation when enabled."""
        settings = LoggingSettings()
        settings.metrics.prometheus_enabled = True
        settings.metrics.prometheus_host = "custom.host"
        settings.metrics.prometheus_port = 8080
        container = LoggingContainer(settings)
        factory = ComponentFactory(container)

        exporter = factory.create_prometheus_exporter()

        assert isinstance(exporter, PrometheusExporter)
        assert exporter.host == "custom.host"
        assert exporter.port == 8080
        assert exporter.enabled is True

    def test_create_prometheus_exporter_disabled(self):
        """Test Prometheus exporter creation when disabled."""
        settings = LoggingSettings()
        settings.metrics.prometheus_enabled = False
        container = LoggingContainer(settings)
        factory = ComponentFactory(container)

        exporter = factory.create_prometheus_exporter()

        assert exporter is None

    def test_create_prometheus_exporter_default_config(self):
        """Test Prometheus exporter with default configuration."""
        settings = LoggingSettings(
            # Use default host and port
        )
        settings.metrics.prometheus_enabled = (
            True  # Enable Prometheus to create exporter
        )
        container = LoggingContainer(settings)
        factory = ComponentFactory(container)

        exporter = factory.create_prometheus_exporter()

        assert isinstance(exporter, PrometheusExporter)
        assert exporter.host == settings.metrics.prometheus_host
        assert exporter.port == settings.metrics.prometheus_port
        assert exporter.enabled is True

    def test_prometheus_exporter_functionality(self):
        """Test Prometheus exporter basic functionality."""
        settings = LoggingSettings()
        settings.metrics.prometheus_enabled = True
        container = LoggingContainer(settings)
        factory = ComponentFactory(container)

        exporter = factory.create_prometheus_exporter()

        if exporter:  # May be None if FastAPI not available
            assert hasattr(exporter, "start")
            assert hasattr(exporter, "stop")


class TestComponentFactorySettingsIntegration:
    """Test ComponentFactory integration with various LoggingSettings configurations."""

    def test_all_components_enabled(self):
        """Test factory with all components enabled."""
        settings = LoggingSettings()
        settings.metrics.enabled = True
        settings.metrics.sample_window = 100
        settings.metrics.prometheus_enabled = True
        settings.metrics.prometheus_host = "0.0.0.0"
        settings.metrics.prometheus_port = 8000
        container = LoggingContainer(settings)
        factory = ComponentFactory(container)

        # Create all components
        lock_manager = factory.create_lock_manager()
        processor_metrics = factory.create_processor_metrics()
        metrics_collector = factory.create_metrics_collector()
        prometheus_exporter = factory.create_prometheus_exporter()

        # All should be created successfully
        assert isinstance(lock_manager, ProcessorLockManager)
        assert isinstance(processor_metrics, ProcessorMetrics)
        assert isinstance(metrics_collector, MetricsCollector)
        assert isinstance(prometheus_exporter, PrometheusExporter)

    def test_all_optional_components_disabled(self):
        """Test factory with optional components disabled."""
        settings = LoggingSettings()
        settings.metrics.enabled = False
        settings.metrics.prometheus_enabled = False
        container = LoggingContainer(settings)
        factory = ComponentFactory(container)

        # Create components
        lock_manager = factory.create_lock_manager()
        processor_metrics = factory.create_processor_metrics()
        metrics_collector = factory.create_metrics_collector()
        prometheus_exporter = factory.create_prometheus_exporter()

        # Required components should still be created
        assert isinstance(lock_manager, ProcessorLockManager)
        assert isinstance(processor_metrics, ProcessorMetrics)

        # Optional components should be None
        assert metrics_collector is None
        assert prometheus_exporter is None

    def test_partial_component_enablement(self):
        """Test factory with partial component enablement."""
        settings = LoggingSettings()
        settings.metrics.enabled = True
        settings.metrics.prometheus_enabled = False  # Only metrics, no Prometheus
        container = LoggingContainer(settings)
        factory = ComponentFactory(container)

        metrics_collector = factory.create_metrics_collector()
        prometheus_exporter = factory.create_prometheus_exporter()

        assert isinstance(metrics_collector, MetricsCollector)
        assert prometheus_exporter is None


class TestComponentFactoryContainerIntegration:
    """Test ComponentFactory integration with LoggingContainer instances."""

    def test_factory_with_configured_container(self):
        """Test factory with fully configured container."""
        settings = LoggingSettings()
        container = LoggingContainer(settings)

        # Configure the container
        container.configure()

        factory = ComponentFactory(container)

        # Should work normally with configured container
        lock_manager = factory.create_lock_manager()
        assert isinstance(lock_manager, ProcessorLockManager)

    def test_factory_with_unconfigured_container(self):
        """Test factory with unconfigured container."""
        container = LoggingContainer()
        factory = ComponentFactory(container)

        # Should work even with unconfigured container
        lock_manager = factory.create_lock_manager()
        metrics = factory.create_processor_metrics()

        assert isinstance(lock_manager, ProcessorLockManager)
        assert isinstance(metrics, ProcessorMetrics)

    def test_factory_isolation_between_containers(self):
        """Test that factories are properly isolated between containers."""
        settings1 = LoggingSettings()
        settings1.metrics.enabled = True
        settings1.metrics.sample_window = 100
        settings2 = LoggingSettings()
        settings2.metrics.enabled = True
        settings2.metrics.sample_window = 200

        container1 = LoggingContainer(settings1)
        container2 = LoggingContainer(settings2)

        factory1 = ComponentFactory(container1)
        factory2 = ComponentFactory(container2)

        collector1 = factory1.create_metrics_collector()
        collector2 = factory2.create_metrics_collector()

        assert collector1 is not None
        assert collector2 is not None
        assert collector1 is not collector2
        assert collector1.sample_window == 100
        assert collector2.sample_window == 200


class TestComponentFactoryErrorHandling:
    """Test ComponentFactory error handling and edge cases."""

    def test_factory_with_none_container(self):
        """Test factory behavior with problematic container."""
        with pytest.raises((TypeError, AttributeError)):
            ComponentFactory(None)

    def test_factory_with_mock_container(self):
        """Test factory with mock container."""
        mock_container = Mock()
        mock_settings = Mock()
        mock_settings.metrics = Mock()
        mock_settings.metrics.enabled = True
        mock_settings.metrics.sample_window = 100
        mock_settings.metrics.prometheus_enabled = False
        mock_container._settings = mock_settings

        factory = ComponentFactory(mock_container)

        # Basic components should still work
        lock_manager = factory.create_lock_manager()
        metrics = factory.create_processor_metrics()

        assert isinstance(lock_manager, ProcessorLockManager)
        assert isinstance(metrics, ProcessorMetrics)

    def test_factory_settings_access(self):
        """Test factory handles settings access correctly."""
        container = LoggingContainer()
        factory = ComponentFactory(container)

        # Should not raise exception accessing settings
        assert factory._settings is not None

        # Should handle settings-based decisions
        collector = factory.create_metrics_collector()
        exporter = factory.create_prometheus_exporter()

        # Results depend on default settings, but should not crash
        assert collector is None or isinstance(collector, MetricsCollector)
        assert exporter is None or isinstance(exporter, PrometheusExporter)


class TestComponentFactoryTypeHints:
    """Test ComponentFactory type hints and return types."""

    def test_return_types(self):
        """Test all factory methods return correct types."""
        container = LoggingContainer()
        factory = ComponentFactory(container)

        # Test required components
        lock_manager = factory.create_lock_manager()
        processor_metrics = factory.create_processor_metrics()

        assert isinstance(lock_manager, ProcessorLockManager)
        assert isinstance(processor_metrics, ProcessorMetrics)

        # Test optional components
        metrics_collector = factory.create_metrics_collector()
        prometheus_exporter = factory.create_prometheus_exporter()

        assert metrics_collector is None or isinstance(
            metrics_collector, MetricsCollector
        )
        assert prometheus_exporter is None or isinstance(
            prometheus_exporter, PrometheusExporter
        )

    def test_optional_type_consistency(self):
        """Test optional components return consistent types based on settings."""
        # Test with enabled settings
        enabled_settings = LoggingSettings()
        enabled_settings.metrics.enabled = True
        enabled_settings.metrics.prometheus_enabled = True
        container_enabled = LoggingContainer(enabled_settings)
        factory_enabled = ComponentFactory(container_enabled)

        collector_enabled = factory_enabled.create_metrics_collector()
        exporter_enabled = factory_enabled.create_prometheus_exporter()

        assert isinstance(collector_enabled, MetricsCollector)
        assert isinstance(exporter_enabled, PrometheusExporter)

        # Test with disabled settings
        disabled_settings = LoggingSettings()
        disabled_settings.metrics.enabled = False
        disabled_settings.metrics.prometheus_enabled = False
        container_disabled = LoggingContainer(disabled_settings)
        factory_disabled = ComponentFactory(container_disabled)

        collector_disabled = factory_disabled.create_metrics_collector()
        exporter_disabled = factory_disabled.create_prometheus_exporter()

        assert collector_disabled is None
        assert exporter_disabled is None


class TestComponentFactoryManagerCreation:
    """Test ComponentFactory specialized manager creation methods."""

    def test_create_configuration_manager(self):
        """Test ConfigurationManager creation."""
        container = LoggingContainer()
        factory = ComponentFactory(container)

        config_mgr = factory.create_configuration_manager()

        assert isinstance(config_mgr, ConfigurationManager)
        # ConfigurationManager is stateless, so test static methods exist
        assert hasattr(config_mgr, "validate_settings")
        assert hasattr(config_mgr, "determine_console_format")

    def test_create_lifecycle_manager(self):
        """Test LifecycleManager creation."""
        container = LoggingContainer()
        factory = ComponentFactory(container)

        lifecycle_mgr = factory.create_lifecycle_manager()

        assert isinstance(lifecycle_mgr, LifecycleManager)
        assert hasattr(lifecycle_mgr, "configure_standard_logging")
        assert hasattr(lifecycle_mgr, "register_shutdown_handler")

    def test_create_sink_manager(self):
        """Test SinkManager creation."""
        container = LoggingContainer()
        factory = ComponentFactory(container)

        sink_mgr = factory.create_sink_manager()

        assert isinstance(sink_mgr, SinkManager)
        assert hasattr(sink_mgr, "setup_queue_worker")
        assert hasattr(sink_mgr, "create_sinks_from_settings")

    def test_create_middleware_manager(self):
        """Test MiddlewareManager creation."""
        container = LoggingContainer()
        factory = ComponentFactory(container)

        middleware_mgr = factory.create_middleware_manager()

        assert isinstance(middleware_mgr, MiddlewareManager)
        assert hasattr(middleware_mgr, "register_middleware")
        assert hasattr(middleware_mgr, "configure_httpx_trace_propagation")

    def test_manager_instances_are_independent(self):
        """Test that multiple manager instances are independent."""
        container = LoggingContainer()
        factory = ComponentFactory(container)

        # Create multiple instances of each manager
        config1 = factory.create_configuration_manager()
        config2 = factory.create_configuration_manager()
        lifecycle1 = factory.create_lifecycle_manager()
        lifecycle2 = factory.create_lifecycle_manager()
        sink1 = factory.create_sink_manager()
        sink2 = factory.create_sink_manager()
        middleware1 = factory.create_middleware_manager()
        middleware2 = factory.create_middleware_manager()

        # All instances should be different objects
        assert config1 is not config2
        assert lifecycle1 is not lifecycle2
        assert sink1 is not sink2
        assert middleware1 is not middleware2

    def test_managers_with_container_id(self):
        """Test managers receive proper container_id from container."""
        container = LoggingContainer()
        # Set a specific container_id for testing
        container._container_id = "test-container-123"
        factory = ComponentFactory(container)

        lifecycle_mgr = factory.create_lifecycle_manager()
        sink_mgr = factory.create_sink_manager()
        middleware_mgr = factory.create_middleware_manager()

        # Managers should have received the container_id
        assert lifecycle_mgr._container_id == "test-container-123"
        assert sink_mgr._container_id == "test-container-123"
        assert middleware_mgr._container_id == "test-container-123"

    def test_managers_with_fallback_container_id(self):
        """Test managers use fallback when container has no container_id attribute."""
        container = LoggingContainer()
        # Remove container_id attribute if it exists
        if hasattr(container, "container_id"):
            delattr(container, "container_id")
        factory = ComponentFactory(container)

        lifecycle_mgr = factory.create_lifecycle_manager()
        sink_mgr = factory.create_sink_manager()
        middleware_mgr = factory.create_middleware_manager()

        # Managers should have received a fallback ID (string representation of container id)
        assert isinstance(lifecycle_mgr._container_id, str)
        assert isinstance(sink_mgr._container_id, str)
        assert isinstance(middleware_mgr._container_id, str)
        # All should have the same fallback ID from the same container
        assert lifecycle_mgr._container_id == sink_mgr._container_id
        assert sink_mgr._container_id == middleware_mgr._container_id


class TestComponentFactoryManagerSet:
    """Test ComponentFactory ManagerSet creation functionality."""

    def test_create_managers_for_container_basic(self):
        """Test basic ManagerSet creation."""
        settings = LoggingSettings()
        container = LoggingContainer(settings)
        factory = ComponentFactory(container)

        managers = factory.create_managers_for_container(settings)

        assert isinstance(managers, ManagerSet)
        assert isinstance(managers.configuration, ConfigurationManager)
        assert isinstance(managers.lifecycle, LifecycleManager)
        assert isinstance(managers.sink, SinkManager)
        assert isinstance(managers.middleware, MiddlewareManager)

    def test_manager_set_named_tuple_access(self):
        """Test ManagerSet named tuple field access."""
        settings = LoggingSettings()
        container = LoggingContainer(settings)
        factory = ComponentFactory(container)

        managers = factory.create_managers_for_container(settings)

        # Test attribute access
        assert hasattr(managers, "configuration")
        assert hasattr(managers, "lifecycle")
        assert hasattr(managers, "sink")
        assert hasattr(managers, "middleware")

        # Test indexed access
        assert managers[0] is managers.configuration
        assert managers[1] is managers.lifecycle
        assert managers[2] is managers.sink
        assert managers[3] is managers.middleware

    def test_manager_set_with_custom_settings(self):
        """Test ManagerSet creation with custom settings."""
        settings = LoggingSettings()
        settings.metrics.enabled = True
        settings.metrics.sample_window = 500
        container = LoggingContainer(settings)
        factory = ComponentFactory(container)

        managers = factory.create_managers_for_container(settings)

        # All managers should be created successfully regardless of settings
        assert isinstance(managers.configuration, ConfigurationManager)
        assert isinstance(managers.lifecycle, LifecycleManager)
        assert isinstance(managers.sink, SinkManager)
        assert isinstance(managers.middleware, MiddlewareManager)

    def test_manager_set_independence_between_calls(self):
        """Test that multiple ManagerSet calls create independent instances."""
        settings = LoggingSettings()
        container = LoggingContainer(settings)
        factory = ComponentFactory(container)

        managers1 = factory.create_managers_for_container(settings)
        managers2 = factory.create_managers_for_container(settings)

        # ManagerSet instances should be different
        assert managers1 is not managers2

        # Each manager instance should be different
        assert managers1.configuration is not managers2.configuration
        assert managers1.lifecycle is not managers2.lifecycle
        assert managers1.sink is not managers2.sink
        assert managers1.middleware is not managers2.middleware

    def test_manager_set_container_id_consistency(self):
        """Test that all managers in a set have consistent container_id."""
        container = LoggingContainer()
        container._container_id = "test-set-123"
        factory = ComponentFactory(container)
        settings = LoggingSettings()

        managers = factory.create_managers_for_container(settings)

        # All non-stateless managers should have the same container_id
        expected_id = "test-set-123"
        assert managers.lifecycle._container_id == expected_id
        assert managers.sink._container_id == expected_id
        assert managers.middleware._container_id == expected_id

    def test_manager_set_creation_order(self):
        """Test that managers are created in proper dependency order."""
        settings = LoggingSettings()
        container = LoggingContainer(settings)
        factory = ComponentFactory(container)

        # This should not raise any exceptions due to dependency issues
        managers = factory.create_managers_for_container(settings)

        # Configuration manager should be stateless (no dependencies)
        assert isinstance(managers.configuration, ConfigurationManager)

        # Other managers should be properly initialized
        assert isinstance(managers.lifecycle, LifecycleManager)
        assert isinstance(managers.sink, SinkManager)
        assert isinstance(managers.middleware, MiddlewareManager)


class TestComponentFactoryManagerIntegration:
    """Test ComponentFactory manager integration scenarios."""

    def test_all_manager_types_created(self):
        """Test that factory can create all manager types simultaneously."""
        container = LoggingContainer()
        factory = ComponentFactory(container)

        # Create all manager types individually
        config_mgr = factory.create_configuration_manager()
        lifecycle_mgr = factory.create_lifecycle_manager()
        sink_mgr = factory.create_sink_manager()
        middleware_mgr = factory.create_middleware_manager()

        # Create manager set
        settings = LoggingSettings()
        managers = factory.create_managers_for_container(settings)

        # All should be proper instances
        assert isinstance(config_mgr, ConfigurationManager)
        assert isinstance(lifecycle_mgr, LifecycleManager)
        assert isinstance(sink_mgr, SinkManager)
        assert isinstance(middleware_mgr, MiddlewareManager)
        assert isinstance(managers, ManagerSet)

    def test_factory_isolation_between_containers(self):
        """Test factory isolation between different containers."""
        settings1 = LoggingSettings()
        settings2 = LoggingSettings()
        container1 = LoggingContainer(settings1)
        container2 = LoggingContainer(settings2)
        container1._container_id = "container-1"
        container2._container_id = "container-2"

        factory1 = ComponentFactory(container1)
        factory2 = ComponentFactory(container2)

        managers1 = factory1.create_managers_for_container(settings1)
        managers2 = factory2.create_managers_for_container(settings2)

        # Manager sets should be completely independent
        assert managers1 is not managers2
        assert managers1.lifecycle._container_id == "container-1"
        assert managers2.lifecycle._container_id == "container-2"

    def test_manager_functionality_after_creation(self):
        """Test that created managers are functional."""
        settings = LoggingSettings()
        container = LoggingContainer(settings)
        factory = ComponentFactory(container)

        managers = factory.create_managers_for_container(settings)

        # Test ConfigurationManager functionality
        validated_settings = managers.configuration.validate_settings(settings)
        assert isinstance(validated_settings, LoggingSettings)

        console_format = managers.configuration.determine_console_format("auto")
        assert console_format in ["pretty", "json"]

        # Test that other managers have expected interface
        assert hasattr(managers.lifecycle, "configure_standard_logging")
        assert hasattr(managers.sink, "setup_queue_worker")
        assert hasattr(managers.middleware, "register_middleware")
        assert hasattr(managers.middleware, "configure_httpx_trace_propagation")
