"""Pure dependency injection container for fapilog logging components.

This module provides a LoggingContainer that implements pure dependency
injection without global state, with complete container isolation and
thread safety through specialized manager classes.
"""

import logging
import threading
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Generator, List, Optional

import structlog

from ._internal.metrics import MetricsCollector
from ._internal.processor_metrics import ProcessorMetrics
from .async_components.concurrency.lock_manager import ProcessorLockManager
from .async_components.queue.worker import QueueWorker
from .config import LoggingSettings
from .core.factories.component_factory import ComponentFactory
from .core.factories.container_logger_factory import ContainerLoggerFactory
from .core.managers.configuration_manager import ConfigurationManager
from .core.managers.lifecycle_manager import LifecycleManager
from .core.managers.metrics_manager import MetricsManager
from .core.managers.middleware_manager import MiddlewareManager
from .core.managers.sink_manager import SinkManager
from .core.registries.component_registry import ComponentRegistry
from .monitoring import PrometheusExporter

if TYPE_CHECKING:
    from .enrichers import (
        AsyncSmartCache,
        EnricherErrorHandler,
        EnricherHealthMonitor,
        RetryCoordinator,
    )

logger = logging.getLogger(__name__)

# Note: Previously cached default settings, but removed to allow environment
# variable overrides to work correctly in tests and dynamic configurations.


class LoggingContainer:
    """Container orchestrating logging dependencies through specialized managers.

    Pure dependency injection with no global state, complete container isolation,
    and thread-safe operations through ConfigurationManager, LifecycleManager,
    SinkManager, MiddlewareManager, and MetricsManager.
    """

    def __init__(self, settings: Optional[LoggingSettings] = None) -> None:
        """Initialize the logging container with manager orchestration."""
        self._lock = threading.RLock()
        # Copy settings to ensure container isolation
        self._settings = (
            settings.model_copy(deep=True)
            if settings is not None
            else LoggingSettings()
        )
        self._configured = False

        # Component management - defer creation until configure()
        self._container_id = f"container_{id(self)}"
        self._configured = False
        self._registry: Optional[ComponentRegistry] = None
        self._factory: Optional[ComponentFactory] = None
        self._lifecycle_manager: Optional[LifecycleManager] = None
        self._middleware_manager: Optional[MiddlewareManager] = None
        self._metrics_manager: Optional[MetricsManager] = None
        self._sink_manager: Optional[SinkManager] = None
        self._queue_worker: Optional[QueueWorker] = None
        self._sinks: List[Any] = []
        self._logger_factory: Optional[ContainerLoggerFactory] = None
        self._console_format: Optional[str] = None
        self._settings_hash: Optional[int] = None

    def _ensure_components_initialized(self) -> None:
        """Initialize all manager components if needed."""
        if self._registry is None:
            self._registry = ComponentRegistry(self._container_id)
        if self._factory is None:
            self._factory = ComponentFactory(self)
        if self._lifecycle_manager is None:
            self._lifecycle_manager = LifecycleManager(self._container_id)
        if self._middleware_manager is None:
            self._middleware_manager = MiddlewareManager(self._container_id)
        if self._metrics_manager is None:
            self._metrics_manager = MetricsManager(self._container_id)
        if self._sink_manager is None:
            self._sink_manager = SinkManager(self._container_id)

    def __enter__(self) -> "LoggingContainer":
        """Context manager entry - configure if needed."""
        if not self._configured:
            self.configure()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - shutdown gracefully."""
        self.shutdown_sync()

    @contextmanager
    def scoped_logger(
        self, name: str = ""
    ) -> Generator[structlog.BoundLogger, None, None]:
        """Create a scoped logger that's automatically cleaned up."""
        try:
            if not self._configured:
                self.configure()
            yield self.get_logger(name)
        finally:
            # Logger cleanup is handled by structlog configuration
            pass

    def configure(
        self,
        settings: Optional[LoggingSettings] = None,
        app: Optional[Any] = None,
    ) -> structlog.BoundLogger:
        """Configure logging with the container (idempotent)."""
        with self._lock:
            # Initialize components on first configure() call for better performance
            self._ensure_components_initialized()

            # Validate settings if changed or first time
            settings_changed = False
            if settings is not None:
                settings_hash = hash(str(settings))
                if self._settings_hash != settings_hash:
                    self._settings = ConfigurationManager.validate_settings(settings)
                    self._settings_hash = settings_hash
                    settings_changed = True
            elif not self._configured:
                self._settings = ConfigurationManager.validate_settings(self._settings)
                self._settings_hash = hash(str(self._settings))
                settings_changed = True

            # Early return if already configured and settings unchanged
            if self._configured and not settings_changed:
                if app is not None:
                    self._middleware_manager.register_middleware(
                        app, self._settings, self.shutdown
                    )
                return self.get_logger()

            # Configure all components through managers
            log_level = self._settings.level
            console_format = ConfigurationManager.determine_console_format(
                self._settings.json_console
            )
            self._console_format = console_format

            self._lifecycle_manager.configure_standard_logging(log_level)

            if self._settings.queue.enabled:
                self._queue_worker = self._sink_manager.setup_queue_worker(
                    self._settings, console_format, self
                )
                self._sinks = self._sink_manager.get_sinks()

            self._metrics_manager.configure_metrics(self._settings)
            self._metrics_manager.setup_prometheus_exporter(
                self._settings, self._registry
            )
            self._configure_structlog(console_format, log_level)
            self._middleware_manager.configure_httpx_trace_propagation(self._settings)

            if app is not None:
                self._middleware_manager.register_middleware(
                    app, self._settings, self.shutdown
                )

            self._configured = True
            self._lifecycle_manager.register_shutdown_handler(self.shutdown_sync)
            return self.get_logger()

    def _configure_structlog(self, console_format: str, log_level: str) -> None:
        """Configure container-specific logging with factory approach."""
        self._console_format = console_format
        self._logger_factory = ContainerLoggerFactory(self)

    async def shutdown(self) -> None:
        """Shutdown the container gracefully (async version)."""
        # Coordinate shutdown through managers
        await self._shutdown_async_managers()

    async def _shutdown_async_managers(self) -> None:
        """Coordinate async shutdown across all managers."""
        await self._lifecycle_manager.shutdown_async(
            registry=self._registry,
            queue_worker=self._queue_worker,
            httpx_propagation=None,
            metrics_collector=self._metrics_manager.get_metrics_collector()
            if self._metrics_manager
            else None,
            sink_manager=self._sink_manager,
        )
        if self._metrics_manager:
            await self._metrics_manager.shutdown_async()
        if self._middleware_manager:
            self._middleware_manager.cleanup_httpx_propagation()
        self._reset_manager_references()

    def shutdown_sync(self) -> None:
        """Shutdown the container gracefully (sync version)."""
        # Coordinate shutdown through managers
        self._shutdown_sync_managers()

    def _shutdown_sync_managers(self) -> None:
        """Coordinate sync shutdown across all managers."""
        self._lifecycle_manager.shutdown_sync(
            registry=self._registry,
            queue_worker=self._queue_worker,
            httpx_propagation=None,
            metrics_collector=self._metrics_manager.get_metrics_collector()
            if self._metrics_manager
            else None,
            sink_manager=self._sink_manager,
        )
        if self._metrics_manager:
            self._metrics_manager.shutdown_sync()
        if self._middleware_manager:
            self._middleware_manager.cleanup_httpx_propagation()
        self._reset_manager_references()

    def _reset_manager_references(self) -> None:
        """Reset manager references after shutdown."""
        self._queue_worker = self._middleware_manager = self._metrics_manager = None

    def reset(self) -> None:
        """Reset the container for testing purposes."""
        with self._lock:
            self.shutdown_sync()
            self._configured = False
            if self._metrics_manager is not None:
                self._metrics_manager.cleanup_resources()
            structlog.reset_defaults()
            root_logger = logging.getLogger()
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)

    @classmethod
    def create_from_settings(cls, settings: LoggingSettings) -> "LoggingContainer":
        """Factory method to create a container from settings."""
        return cls(settings=settings)

    @classmethod
    def create_with_defaults(cls) -> "LoggingContainer":
        """Factory method to create a container with default settings."""
        return cls()

    @property
    def settings(self) -> LoggingSettings:
        """Get the current settings."""
        return self._settings

    @property
    def is_configured(self) -> bool:
        """Check if the container is configured."""
        return self._configured

    @property
    def queue_worker(self) -> Optional[QueueWorker]:
        """Get the queue worker instance."""
        return self._queue_worker

    async def setup(self) -> None:
        """Async setup for container components."""
        with self._lock:
            # Start async metrics components through MetricsManager
            if self._metrics_manager is not None:
                await self._metrics_manager.start_async_components()

    def get_logger(self, name: str = "") -> structlog.BoundLogger:
        """Get container-specific logger using factory approach."""
        if not self._configured:
            self.configure()

        if self._logger_factory is None:
            raise RuntimeError("Container not properly configured")

        return self._logger_factory.create_logger(name)

    def _get_component(self, component_type, factory_method):
        """Helper to get or create components from registry."""
        self._ensure_components_initialized()
        return self._registry.get_or_create_component(component_type, factory_method)  # type: ignore[union-attr]

    def get_lock_manager(self) -> ProcessorLockManager:
        """Get container-scoped ProcessorLockManager instance."""
        return self._get_component(  # type: ignore[no-any-return]
            ProcessorLockManager,
            lambda: self._factory.create_lock_manager(),  # type: ignore[union-attr]
        )

    def get_processor_metrics(self) -> ProcessorMetrics:
        """Get container-scoped ProcessorMetrics instance."""
        return self._get_component(  # type: ignore[no-any-return]
            ProcessorMetrics,
            lambda: self._factory.create_processor_metrics(),  # type: ignore[union-attr]
        )

    def get_metrics_collector(self) -> Optional[MetricsCollector]:
        """Get container-scoped MetricsCollector instance."""
        if not self._settings.metrics.enabled:
            return None
        return self._get_component(  # type: ignore[no-any-return]
            MetricsCollector,
            lambda: self._factory.create_metrics_collector(),  # type: ignore[union-attr]
        )

    def get_prometheus_exporter(self) -> Optional[PrometheusExporter]:
        """Get container-scoped PrometheusExporter instance."""
        if not self._settings.metrics.prometheus_enabled:
            return None
        return self._get_component(  # type: ignore[no-any-return]
            PrometheusExporter,
            lambda: self._factory.create_prometheus_exporter(),  # type: ignore[union-attr]
        )

    def get_async_smart_cache(self) -> "AsyncSmartCache":
        """Get container-scoped AsyncSmartCache instance."""
        from .enrichers import AsyncSmartCache

        return self._get_component(  # type: ignore[no-any-return]
            AsyncSmartCache,
            lambda: self._factory.create_async_smart_cache(),  # type: ignore[union-attr]
        )

    def get_enricher_error_handler(self) -> "EnricherErrorHandler":
        """Get container-scoped EnricherErrorHandler instance."""
        from .enrichers import EnricherErrorHandler

        return self._get_component(  # type: ignore[no-any-return]
            EnricherErrorHandler,
            lambda: self._factory.create_enricher_error_handler(),  # type: ignore[union-attr]
        )

    def get_enricher_health_monitor(self) -> "EnricherHealthMonitor":
        """Get container-scoped EnricherHealthMonitor instance."""
        from .enrichers import EnricherHealthMonitor

        return self._get_component(  # type: ignore[no-any-return]
            EnricherHealthMonitor,
            lambda: self._factory.create_enricher_health_monitor(),  # type: ignore[union-attr]
        )

    def get_retry_coordinator(self) -> "RetryCoordinator":
        """Get container-scoped RetryCoordinator instance."""
        from .enrichers import RetryCoordinator

        return self._get_component(  # type: ignore[no-any-return]
            RetryCoordinator,
            lambda: self._factory.create_retry_coordinator(),  # type: ignore[union-attr]
        )
