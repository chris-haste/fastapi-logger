"""ComponentFactory - Factory for creating container-scoped component instances.

This module provides a ComponentFactory class that creates container-scoped
components with proper configuration and isolation, eliminating global state
dependencies.
"""

from typing import TYPE_CHECKING, Optional

from fapilog._internal.async_lock_manager import ProcessorLockManager
from fapilog._internal.metrics import MetricsCollector
from fapilog._internal.processor_metrics import ProcessorMetrics
from fapilog.monitoring import PrometheusExporter
from fapilog.settings import LoggingSettings

if TYPE_CHECKING:
    from fapilog.container import LoggingContainer


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
        if not self._settings.metrics_enabled:
            return None

        return MetricsCollector(
            enabled=True, sample_window=self._settings.metrics_sample_window
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
        if not self._settings.metrics_prometheus_enabled:
            return None

        return PrometheusExporter(
            host=self._settings.metrics_prometheus_host,
            port=self._settings.metrics_prometheus_port,
            enabled=True,
        )

    def __repr__(self) -> str:
        """Return string representation of factory."""
        container_id = getattr(self.container, "container_id", id(self.container))
        return f"ComponentFactory(container_id={container_id!r})"
