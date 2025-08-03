"""Metrics management for fapilog logging components.

This module provides a dedicated MetricsManager class that handles
all metrics-related operations extracted from LoggingContainer, following
the single responsibility principle.

Key Features:
- Metrics collector configuration and management
- Prometheus exporter setup and lifecycle
- Metrics-specific settings coordination
- Thread-safe operations
- Clean interface with proper error handling
- Extensible design for future metrics implementations
"""

import logging
import threading
from typing import Any, Optional

from ..._internal.metrics import MetricsCollector
from ...config import LoggingSettings
from ...monitoring import PrometheusExporter

logger = logging.getLogger(__name__)


class MetricsManager:
    """Manages metrics collection and exporter operations.

    This class handles all metrics-related functionality including
    metrics collector configuration, Prometheus exporter setup, and
    metrics lifecycle management.

    Design Principles:
    - Clean separation of metrics concerns
    - Thread-safe operations
    - Extensible design for future metrics systems
    - No dependencies on lifecycle, sink, or middleware logic
    - Proper resource management and cleanup
    """

    def __init__(self, container_id: str) -> None:
        """Initialize the metrics manager.

        Args:
            container_id: Unique identifier for the associated container
        """
        self._container_id = container_id
        self._lock = threading.RLock()
        self._metrics_collector: Optional[MetricsCollector] = None
        self._prometheus_exporter: Optional[PrometheusExporter] = None

    def configure_metrics(
        self, settings: LoggingSettings
    ) -> Optional[MetricsCollector]:
        """Configure metrics collection based on settings.

        Args:
            settings: LoggingSettings containing metrics configuration

        Returns:
            MetricsCollector instance if enabled, None otherwise
        """
        with self._lock:
            if settings.metrics.enabled:
                self._metrics_collector = MetricsCollector(
                    enabled=True,
                    sample_window=settings.metrics.sample_window,
                )
                return self._metrics_collector
            else:
                self._metrics_collector = None
                return None

    def get_metrics_collector(self) -> Optional[MetricsCollector]:
        """Get the current metrics collector instance.

        Returns:
            MetricsCollector instance if configured, None otherwise
        """
        with self._lock:
            return self._metrics_collector

    def setup_prometheus_exporter(
        self, settings: LoggingSettings, component_registry: Any
    ) -> Optional[PrometheusExporter]:
        """Setup Prometheus exporter if enabled in settings.

        Args:
            settings: LoggingSettings containing Prometheus configuration
            component_registry: Component registry for exporter creation

        Returns:
            PrometheusExporter instance if enabled, None otherwise
        """
        with self._lock:
            if settings.metrics.prometheus_enabled:
                # Create Prometheus exporter via component registry
                self._prometheus_exporter = component_registry.get_or_create_component(
                    PrometheusExporter,
                    lambda: self._create_prometheus_exporter(settings),
                )
                return self._prometheus_exporter
            else:
                self._prometheus_exporter = None
                return None

    def _create_prometheus_exporter(
        self, settings: LoggingSettings
    ) -> PrometheusExporter:
        """Create a Prometheus exporter instance.

        Args:
            settings: LoggingSettings containing Prometheus configuration

        Returns:
            Configured PrometheusExporter instance
        """
        return PrometheusExporter(
            host=settings.metrics.prometheus_host,
            port=settings.metrics.prometheus_port,
            path="/metrics",  # Default path
            enabled=True,
        )

    def get_prometheus_exporter(self) -> Optional[PrometheusExporter]:
        """Get the current Prometheus exporter instance.

        Returns:
            PrometheusExporter instance if configured, None otherwise
        """
        with self._lock:
            return self._prometheus_exporter

    async def start_async_components(self) -> None:
        """Start async metrics components (e.g., Prometheus exporter).

        This should be called during container setup if using async components.
        """
        with self._lock:
            if self._prometheus_exporter is not None:
                try:
                    await self._prometheus_exporter.start()
                except Exception as e:
                    logger.warning(f"Failed to start Prometheus exporter: {e}")

    async def shutdown_async(self) -> None:
        """Shutdown metrics components gracefully (async version)."""
        with self._lock:
            # Stop Prometheus exporter
            if self._prometheus_exporter is not None:
                try:
                    await self._prometheus_exporter.stop()
                except Exception as e:
                    logger.warning(f"Error during Prometheus exporter shutdown: {e}")
                finally:
                    self._prometheus_exporter = None

            # Reset metrics collector
            self._metrics_collector = None

    def shutdown_sync(self) -> None:
        """Shutdown metrics components gracefully (sync version)."""
        with self._lock:
            # For sync shutdown, we just reset references
            # The actual async components should be stopped via shutdown_async
            self._prometheus_exporter = None
            self._metrics_collector = None

    def cleanup_resources(self) -> None:
        """Clean up and reset all metrics resources.

        This method should be called during container reset/cleanup.
        """
        with self._lock:
            self._metrics_collector = None
            self._prometheus_exporter = None

    def is_metrics_enabled(self, settings: LoggingSettings) -> bool:
        """Check if metrics collection is enabled.

        Args:
            settings: LoggingSettings to check

        Returns:
            True if metrics are enabled, False otherwise
        """
        return settings.metrics.enabled

    def is_prometheus_enabled(self, settings: LoggingSettings) -> bool:
        """Check if Prometheus metrics are enabled.

        Args:
            settings: LoggingSettings to check

        Returns:
            True if Prometheus is enabled, False otherwise
        """
        return settings.metrics.prometheus_enabled
