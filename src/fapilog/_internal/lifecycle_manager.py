"""Lifecycle management for fapilog logging components.

This module provides a dedicated LifecycleManager class that handles
all lifecycle-related operations extracted from LoggingContainer, following
the single responsibility principle.

Key Features:
- Standard logging configuration
- Shutdown handler registration for process cleanup
- Graceful shutdown and cleanup operations
- Async/await pattern support
- Thread-safe operations
- Clean interface with no external dependencies beyond required types

Note: Middleware registration is now handled by MiddlewareManager for
better separation of concerns.
"""

import atexit
import logging
import threading
from typing import Any, Callable, Optional

from ..monitoring import PrometheusExporter
from .error_handling import handle_configuration_error

# Note: FastAPI lifespan RuntimeWarnings in test environments are expected and harmless.
# They occur during test cleanup when FastAPI shutdown handlers aren't properly awaited.
# This doesn't affect application functionality or test reliability.

logger = logging.getLogger(__name__)


class LifecycleManager:
    """Manages lifecycle operations for logging components.

    This class handles application lifecycle events including startup
    configuration, shutdown handlers, and graceful cleanup operations.
    Middleware registration is handled separately by MiddlewareManager.

    Design Principles:
    - Clean separation of lifecycle concerns
    - Thread-safe operations
    - Async/await pattern support for shutdown handlers
    - Proper resource cleanup and graceful shutdown
    - No direct dependencies on sinks or middleware logic
    """

    def __init__(self, container_id: str) -> None:
        """Initialize the lifecycle manager.

        Args:
            container_id: Unique identifier for the associated container
        """
        self._container_id = container_id
        self._lock = threading.RLock()
        self._shutdown_registered = False

    def configure_standard_logging(self, log_level: str) -> None:
        """Configure standard library logging.

        Sets up a StreamHandler that outputs to stdout with the specified
        log level, removing any existing handlers to avoid duplicates.

        Args:
            log_level: Log level string (DEBUG/INFO/WARNING/ERROR/CRITICAL)

        Raises:
            ConfigurationError: If log_level is invalid
        """
        import sys

        try:
            # Create a handler that outputs to stdout (like PrintLoggerFactory did)
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(getattr(logging, log_level.upper()))
            handler.setFormatter(logging.Formatter("%(message)s"))

            # Configure root logger
            root_logger = logging.getLogger()
            root_logger.setLevel(getattr(logging, log_level.upper()))

            # Remove existing handlers to avoid duplicates
            for existing_handler in root_logger.handlers[:]:
                root_logger.removeHandler(existing_handler)

            # Add our stdout handler
            root_logger.addHandler(handler)

        except AttributeError as e:
            raise handle_configuration_error(
                e,
                "log_level",
                log_level,
                "valid logging level (DEBUG/INFO/WARNING/ERROR/CRITICAL)",
            ) from e

    def register_shutdown_handler(self, cleanup_func: Callable[[], None]) -> None:
        """Register atexit shutdown handler to ensure cleanup on process exit.

        Args:
            cleanup_func: Function to call for cleanup on process exit
        """
        with self._lock:
            if not self._shutdown_registered:
                atexit.register(cleanup_func)
                self._shutdown_registered = True

    async def shutdown_async(
        self,
        registry: Any,
        queue_worker: Optional[Any] = None,
        httpx_propagation: Optional[Any] = None,
        metrics_collector: Optional[Any] = None,
        sink_manager: Optional[Any] = None,
    ) -> None:
        """Perform graceful async shutdown of logging components.

        Args:
            registry: ComponentRegistry instance for cleanup
            queue_worker: Optional QueueWorker to shutdown
            httpx_propagation: Optional HttpxTracePropagation to cleanup
            metrics_collector: Optional MetricsCollector to reset
            sink_manager: Optional SinkManager for proper sink cleanup
        """
        with self._lock:
            # Cleanup sinks first (as they may depend on other components)
            if sink_manager is not None:
                try:
                    await sink_manager.cleanup_sinks_async()
                except Exception as e:
                    logger.warning(f"Error during sink cleanup: {e}")

            # Cleanup component registry
            try:
                registry.cleanup()
            except Exception as e:
                logger.warning(f"Error during component registry cleanup: {e}")

            # Shutdown Prometheus exporter if it exists in component registry
            prometheus_exporter = registry.get_component(PrometheusExporter)
            if prometheus_exporter is not None:
                try:
                    await prometheus_exporter.stop()
                except Exception as e:
                    logger.warning(f"Error during Prometheus exporter shutdown: {e}")

            # Shutdown queue worker
            if queue_worker is not None:
                try:
                    await queue_worker.shutdown()
                except Exception as e:
                    logger.warning(f"Error during queue worker shutdown: {e}")

            # Cleanup httpx propagation
            if httpx_propagation is not None:
                try:
                    httpx_propagation.cleanup()
                except Exception as e:
                    logger.warning(f"Error during httpx propagation cleanup: {e}")

    def shutdown_sync(
        self,
        registry: Any,
        queue_worker: Optional[Any] = None,
        httpx_propagation: Optional[Any] = None,
        metrics_collector: Optional[Any] = None,
        sink_manager: Optional[Any] = None,
    ) -> None:
        """Perform graceful sync shutdown of logging components.

        Args:
            registry: ComponentRegistry instance for cleanup
            queue_worker: Optional QueueWorker to shutdown
            httpx_propagation: Optional HttpxTracePropagation to cleanup
            metrics_collector: Optional MetricsCollector to reset
            sink_manager: Optional SinkManager for proper sink cleanup
        """
        with self._lock:
            # Cleanup sinks first (as they may depend on other components)
            if sink_manager is not None:
                try:
                    sink_manager.cleanup_sinks()
                except Exception as e:
                    logger.warning(f"Error during sink cleanup: {e}")

            # Cleanup component registry
            try:
                registry.cleanup()
            except Exception as e:
                logger.warning(f"Error during component registry cleanup: {e}")

            # Shutdown queue worker (sync version)
            if queue_worker is not None:
                try:
                    queue_worker.shutdown_sync()
                except Exception as e:
                    logger.warning(f"Error during sync queue worker shutdown: {e}")

            # Cleanup httpx propagation
            if httpx_propagation is not None:
                try:
                    httpx_propagation.cleanup()
                except Exception as e:
                    logger.warning(f"Error during httpx propagation cleanup: {e}")

    def cleanup_resources(self, **resources: Any) -> None:
        """Clean up and reset all provided resources to None.

        This is a utility method for resetting object references during shutdown.

        Args:
            **resources: Named resources to set to None in the calling context
        """
        # Note: This method signature allows callers to pass in resources
        # they want to reset, but the actual resetting must be done by the caller
        # since we can't modify their object references from here.
        # This method serves as documentation of the cleanup interface.
        pass
