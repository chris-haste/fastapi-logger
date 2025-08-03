"""ComponentFactory - Factory for creating container-scoped components.

This module provides a ComponentFactory class that creates container-scoped
components with proper configuration and isolation, eliminating global state
dependencies.
"""

from typing import TYPE_CHECKING, NamedTuple, Optional

from ..._internal.metrics import MetricsCollector
from ..._internal.processor_metrics import ProcessorMetrics
from ...async_components.concurrency.lock_manager import ProcessorLockManager
from ...enrichers import (
    AsyncSmartCache,
    EnricherErrorHandler,
    EnricherHealthMonitor,
    RetryCoordinator,
)
from ...monitoring import PrometheusExporter
from ...settings import LoggingSettings
from ..managers.configuration_manager import ConfigurationManager
from ..managers.lifecycle_manager import LifecycleManager
from ..managers.middleware_manager import MiddlewareManager
from ..managers.sink_manager import SinkManager

if TYPE_CHECKING:
    from ...container import LoggingContainer


class ManagerSet(NamedTuple):
    """Complete set of managers for LoggingContainer integration.

    This structure provides all managers needed for container operation
    with proper dependency resolution and initialization order.
    """

    configuration: ConfigurationManager
    lifecycle: LifecycleManager
    sink: SinkManager
    middleware: MiddlewareManager


class ComponentFactory:
    """Factory for creating container-scoped component instances.

    This factory provides clean dependency creation for container-scoped
    components, replacing global component creation with explicit,
    container-aware component instantiation.

    All components are created with container-specific configuration
    from LoggingSettings, ensuring proper isolation between containers.

    Example:
        factory = ComponentFactory(container)
        lock_manager = factory.create_lock_manager()
        metrics = factory.create_processor_metrics()
        collector = factory.create_metrics_collector()
        exporter = factory.create_prometheus_exporter()
    """

    def __init__(self, container: "LoggingContainer"):
        """Initialize ComponentFactory with container reference.

        Args:
            container: LoggingContainer instance for configuration access
        """
        self.container = container
        self._settings: LoggingSettings = container._settings

    def create_lock_manager(self) -> ProcessorLockManager:
        """Create ProcessorLockManager for container.

        Creates a new ProcessorLockManager instance for this container,
        providing thread-safe async lock management for processors.

        Returns:
            ProcessorLockManager: New lock manager instance

        Example:
            lock_manager = factory.create_lock_manager()
            async with lock_manager.get_async_lock("processor_id"):
                # Thread-safe processor operations
                pass
        """
        return ProcessorLockManager()

    def create_processor_metrics(self) -> ProcessorMetrics:
        """Create ProcessorMetrics for container.

        Creates a new ProcessorMetrics instance for tracking processor
        performance and health metrics within this container.

        Returns:
            ProcessorMetrics: New processor metrics instance

        Example:
            metrics = factory.create_processor_metrics()
            metrics.record_processor_execution(
                "my_processor", latency_ms=10.5, success=True
            )
        """
        return ProcessorMetrics()

    def create_metrics_collector(self) -> Optional[MetricsCollector]:
        """Create MetricsCollector if enabled in settings.

        Creates a MetricsCollector instance if metrics collection is enabled
        in the container's LoggingSettings. Uses settings for configuration
        of sample window size.

        Returns:
            Optional[MetricsCollector]: MetricsCollector if enabled, None otherwise

        Example:
            collector = factory.create_metrics_collector()
            if collector:
                collector.record_enqueue(latency_ms=10.0)
        """
        if not self._settings.metrics.enabled:
            return None

        return MetricsCollector(
            enabled=True, sample_window=self._settings.metrics.sample_window
        )

    def create_prometheus_exporter(self) -> Optional[PrometheusExporter]:
        """Create PrometheusExporter if enabled in settings.

        Creates a PrometheusExporter instance if Prometheus metrics export
        is enabled in the container's LoggingSettings. Uses settings for
        host and port configuration.

        Returns:
            Optional[PrometheusExporter]: PrometheusExporter if enabled, None otherwise

        Example:
            exporter = factory.create_prometheus_exporter()
            if exporter:
                await exporter.start()
                # Prometheus metrics available at configured endpoint
        """
        if not self._settings.metrics.prometheus_enabled:
            return None

        return PrometheusExporter(
            host=self._settings.metrics.prometheus_host,
            port=self._settings.metrics.prometheus_port,
            enabled=True,
        )

    def create_async_smart_cache(self) -> AsyncSmartCache:
        """Create AsyncSmartCache for container.

        Creates a new AsyncSmartCache instance for this container,
        providing async-safe caching with proper locking for enrichers.

        Returns:
            AsyncSmartCache: New async smart cache instance

        Example:
            cache = factory.create_async_smart_cache()
            result = await cache.get_or_compute("key", lambda: "value")
        """
        return AsyncSmartCache()

    def create_enricher_error_handler(self) -> EnricherErrorHandler:
        """Create EnricherErrorHandler for container.

        Creates a new EnricherErrorHandler instance for this container,
        providing enricher error handling and strategy management.

        Returns:
            EnricherErrorHandler: New enricher error handler instance

        Example:
            handler = factory.create_enricher_error_handler()
            continue_processing = handler.handle_enricher_error(enricher, error, result)
        """
        return EnricherErrorHandler()

    def create_enricher_health_monitor(self) -> EnricherHealthMonitor:
        """Create EnricherHealthMonitor for container.

        Creates a new EnricherHealthMonitor instance for this container,
        providing enricher health tracking and statistics.

        Returns:
            EnricherHealthMonitor: New enricher health monitor instance

        Example:
            monitor = factory.create_enricher_health_monitor()
            monitor.record_enricher_execution("my_enricher", True, 10.5)
        """
        return EnricherHealthMonitor()

    def create_retry_coordinator(self) -> RetryCoordinator:
        """Create RetryCoordinator for container.

        Creates a new RetryCoordinator instance for this container,
        providing retry coordination and locking for enricher operations.

        Returns:
            RetryCoordinator: New retry coordinator instance

        Example:
            coordinator = factory.create_retry_coordinator()
            result = await coordinator.coordinate_retry("key", retry_func)
        """
        return RetryCoordinator()

    def create_configuration_manager(self) -> ConfigurationManager:
        """Create ConfigurationManager for container.

        Creates a new ConfigurationManager instance for configuration
        validation and format determination. This manager is stateless
        and provides static methods for configuration operations.

        Returns:
            ConfigurationManager: New configuration manager instance

        Example:
            config_mgr = factory.create_configuration_manager()
            settings = config_mgr.validate_settings(raw_settings)
            format = config_mgr.determine_console_format("auto")
        """
        return ConfigurationManager()

    def create_lifecycle_manager(self) -> LifecycleManager:
        """Create LifecycleManager for container.

        Creates a new LifecycleManager instance for handling application
        lifecycle events including startup configuration, shutdown handlers,
        and graceful cleanup operations.

        Returns:
            LifecycleManager: New lifecycle manager instance

        Example:
            lifecycle_mgr = factory.create_lifecycle_manager()
            lifecycle_mgr.configure_standard_logging("INFO")
            lifecycle_mgr.register_shutdown_handler(cleanup_func)
        """
        container_id = getattr(self.container, "_container_id", str(id(self.container)))
        return LifecycleManager(container_id)

    def create_sink_manager(self) -> SinkManager:
        """Create SinkManager for container.

        Creates a new SinkManager instance for managing sink creation,
        configuration, and lifecycle operations including queue worker
        setup and sink lifecycle management.

        Returns:
            SinkManager: New sink manager instance

        Example:
            sink_mgr = factory.create_sink_manager()
            worker = sink_mgr.setup_queue_worker(settings, format, container)
            sink_mgr.create_sinks_from_settings(settings)
        """
        container_id = getattr(self.container, "_container_id", str(id(self.container)))
        return SinkManager(container_id)

    def create_middleware_manager(self) -> MiddlewareManager:
        """Create MiddlewareManager for container.

        Creates a new MiddlewareManager instance for handling all
        middleware-related functionality including FastAPI middleware
        registration and httpx trace propagation.

        Returns:
            MiddlewareManager: New middleware manager instance

        Example:
            middleware_mgr = factory.create_middleware_manager()
            middleware_mgr.register_middleware(app, settings, shutdown_callback)
            middleware_mgr.setup_httpx_propagation(settings)
        """
        container_id = getattr(self.container, "_container_id", str(id(self.container)))
        return MiddlewareManager(container_id)

    def create_managers_for_container(self, settings: LoggingSettings) -> ManagerSet:
        """Create complete manager set for LoggingContainer integration.

        Creates all specialized managers with proper dependency injection
        and initialization order. This method provides a single interface
        for LoggingContainer to acquire all required managers.

        Args:
            settings: LoggingSettings for manager configuration

        Returns:
            ManagerSet: Complete set of initialized managers

        Example:
            managers = factory.create_managers_for_container(settings)
            # Use managers.configuration, managers.lifecycle, etc.
            validated_settings = managers.configuration.validate_settings(settings)
        """
        # Create managers in dependency order
        # ConfigurationManager is stateless - no dependencies
        configuration_manager = self.create_configuration_manager()

        # Other managers depend on container_id but not each other
        lifecycle_manager = self.create_lifecycle_manager()
        sink_manager = self.create_sink_manager()
        middleware_manager = self.create_middleware_manager()

        return ManagerSet(
            configuration=configuration_manager,
            lifecycle=lifecycle_manager,
            sink=sink_manager,
            middleware=middleware_manager,
        )

    def __repr__(self) -> str:
        """Return string representation of factory."""
        container_id = getattr(self.container, "_container_id", str(id(self.container)))
        return f"ComponentFactory(container_id={container_id!r})"
