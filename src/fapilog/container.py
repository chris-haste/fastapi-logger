"""Dependency injection container for fapilog logging components."""

import atexit
import logging
import threading
import weakref
from typing import Any, List, Optional, Set

import structlog

from ._internal.error_handling import (
    handle_configuration_error,
    handle_sink_error,
)
from ._internal.queue import QueueWorker, Sink
from ._internal.sink_factory import (
    SinkConfigurationError,
    create_custom_sink_from_uri,
)
from .httpx_patch import HttpxTracePropagation
from .middleware import TraceIDMiddleware
from .pipeline import build_processor_chain
from .settings import LoggingSettings
from .sinks.file import create_file_sink_from_uri
from .sinks.loki import create_loki_sink_from_uri
from .sinks.stdout import StdoutSink

logger = logging.getLogger(__name__)

# Registry to track all container instances for proper cleanup
_container_registry: Set[weakref.ReferenceType["LoggingContainer"]] = set()
_registry_lock = threading.Lock()

# Current container access without thread-local storage
_current_container: Optional["LoggingContainer"] = None
_current_container_lock = threading.RLock()


def set_current_container(container: Optional["LoggingContainer"]) -> None:
    """Set the current container instance.

    Args:
        container: The LoggingContainer instance to set as current
    """
    global _current_container
    with _current_container_lock:
        _current_container = container


def get_current_container() -> Optional["LoggingContainer"]:
    """Get the current container instance.

    Returns:
        The current LoggingContainer instance or None if not set
    """
    with _current_container_lock:
        return _current_container


class LoggingContainer:
    """Container that manages all logging dependencies and lifecycle.

    This replaces global state with proper dependency injection, allowing
    multiple logging configurations to coexist safely while maintaining
    thread-safety and idempotent behavior.
    """

    def __init__(self, settings: Optional[LoggingSettings] = None) -> None:
        """Initialize the logging container.

        Args:
            settings: Optional LoggingSettings instance. If None, created from env.
        """
        self._lock = threading.RLock()
        self._settings = settings or LoggingSettings()
        self._configured = False
        self._queue_worker: Optional[QueueWorker] = None
        self._sinks: List[Any] = []
        self._httpx_propagation: Optional[HttpxTracePropagation] = None
        self._shutdown_registered = False

        # Metrics components
        self._metrics_collector: Optional[Any] = None
        self._prometheus_exporter: Optional[Any] = None

        # Register this container for cleanup
        with _registry_lock:
            _container_registry.add(weakref.ref(self, self._cleanup_registry_ref))

    @staticmethod
    def _cleanup_registry_ref(
        ref: weakref.ReferenceType["LoggingContainer"],
    ) -> None:
        """Clean up a dead reference from the registry."""
        with _registry_lock:
            _container_registry.discard(ref)

    def configure(
        self,
        settings: Optional[LoggingSettings] = None,
        app: Optional[Any] = None,
    ) -> structlog.BoundLogger:
        """Configure logging with the container.

        This method is idempotent - subsequent calls will not duplicate
        configuration.

        Args:
            settings: Optional LoggingSettings instance to override container
                     settings
            app: Optional FastAPI app instance for middleware registration

        Returns:
            A configured structlog.BoundLogger instance
        """
        with self._lock:
            # Use provided settings or fall back to container settings
            if settings is not None:
                self._settings = self._validate_and_get_settings(settings)
            elif not self._configured:
                self._settings = self._validate_and_get_settings(self._settings)

            # Check if already configured
            if self._configured:
                # Still register middleware if app is provided
                if app is not None:
                    self._register_middleware(app)
                return structlog.get_logger()  # type: ignore[no-any-return]

            # Determine final configuration values from settings
            log_level = self._settings.level
            console_format = self._determine_console_format(self._settings.json_console)

            # Configure standard library logging
            self._configure_standard_logging(log_level)

            # Initialize queue worker if enabled
            if self._settings.queue_enabled:
                self._queue_worker = self._setup_queue_worker(console_format)

            # Initialize metrics if enabled
            self._configure_metrics()

            # Configure structlog
            self._configure_structlog(console_format, log_level)

            # Configure httpx trace propagation
            self._configure_httpx_trace_propagation()

            # Register middleware if app is provided
            if app is not None:
                self._register_middleware(app)

            # Mark as configured
            self._configured = True

            # Register shutdown handler once
            if not self._shutdown_registered:
                atexit.register(self.shutdown_sync)
                self._shutdown_registered = True

            return structlog.get_logger()  # type: ignore[no-any-return]

    def _validate_and_get_settings(
        self, settings: Optional[LoggingSettings]
    ) -> LoggingSettings:
        """Validate and return LoggingSettings instance."""
        try:
            if settings is None:
                return LoggingSettings()
            return LoggingSettings.model_validate(settings.model_dump())
        except Exception as e:
            raise handle_configuration_error(
                e,
                "settings",
                str(settings) if settings else "None",
                "valid LoggingSettings",
            ) from e

    def _determine_console_format(self, console_format: str) -> str:
        """Determine the console output format."""
        import sys

        valid_formats = {"auto", "pretty", "json"}
        if console_format not in valid_formats:
            raise handle_configuration_error(
                ValueError(f"Invalid console_format: {console_format}"),
                "console_format",
                console_format,
                f"one of {', '.join(valid_formats)}",
            )

        if console_format == "auto":
            return "pretty" if sys.stderr.isatty() else "json"
        return console_format

    def _configure_standard_logging(self, log_level: str) -> None:
        """Configure standard library logging."""
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

    def _setup_queue_worker(self, console_format: str) -> QueueWorker:
        """Set up the queue worker with appropriate sinks."""
        # Create sinks based on settings
        self._sinks = []

        for sink_item in self._settings.sinks:
            # Handle direct Sink instances
            if isinstance(sink_item, Sink):
                self._sinks.append(sink_item)
                continue

            # Handle string URIs (existing logic)
            sink_uri = sink_item
            if sink_uri == "stdout":
                # Map console_format to StdoutSink mode
                if console_format == "pretty":
                    mode = "pretty"
                elif console_format == "json":
                    mode = "json"
                else:
                    mode = "auto"
                self._sinks.append(StdoutSink(mode=mode))
            elif sink_uri.startswith("file://"):
                try:
                    self._sinks.append(create_file_sink_from_uri(sink_uri))
                except Exception as e:
                    raise handle_sink_error(
                        e, "file", {"uri": sink_uri}, "initialize"
                    ) from e
            elif sink_uri.startswith(("loki://", "https://")) and "loki" in sink_uri:
                try:
                    self._sinks.append(create_loki_sink_from_uri(sink_uri))
                except ImportError as e:
                    raise handle_sink_error(
                        e, "loki", {"uri": sink_uri}, "initialize"
                    ) from e
                except Exception as e:
                    raise handle_sink_error(
                        e, "loki", {"uri": sink_uri}, "initialize"
                    ) from e
            else:
                # Try custom sink from registry
                try:
                    self._sinks.append(create_custom_sink_from_uri(sink_uri))
                except SinkConfigurationError as e:
                    # If it's a custom sink error, re-raise with sink error handling
                    raise handle_sink_error(
                        e, e.sink_name or "custom", {"uri": sink_uri}, "initialize"
                    ) from e
                except Exception as e:
                    # Unknown sink type or other error
                    raise handle_sink_error(
                        ValueError(f"Unknown sink type: {sink_uri}"),
                        "unknown",
                        {"uri": sink_uri},
                        "initialize",
                    ) from e

        # Create queue worker with error handling
        try:
            worker = QueueWorker(
                sinks=self._sinks,
                queue_max_size=self._settings.queue_maxsize,
                batch_size=self._settings.queue_batch_size,
                batch_timeout=self._settings.queue_batch_timeout,
                retry_delay=self._settings.queue_retry_delay,
                max_retries=self._settings.queue_max_retries,
                overflow_strategy=self._settings.queue_overflow,
                sampling_rate=self._settings.sampling_rate,
            )
        except Exception as e:
            queue_config = {
                "queue_max_size": self._settings.queue_maxsize,
                "batch_size": self._settings.queue_batch_size,
                "batch_timeout": self._settings.queue_batch_timeout,
                "retry_delay": self._settings.queue_retry_delay,
                "max_retries": self._settings.queue_max_retries,
                "overflow_strategy": self._settings.queue_overflow,
                "sampling_rate": self._settings.sampling_rate,
            }
            raise handle_configuration_error(
                e, "queue_worker", queue_config, "valid queue configuration"
            ) from e

        return worker

    def _configure_structlog(self, console_format: str, log_level: str) -> None:
        """Configure structlog with processor chain."""
        # Set this container as the current context for queue operations
        set_current_container(self)

        # Build structlog processor chain using the pipeline
        # The pipeline already handles queue vs non-queue configuration
        processors = build_processor_chain(
            self._settings, pretty=(console_format == "pretty")
        )

        # Configure structlog with appropriate factory based on queue usage
        if self._settings.queue_enabled:
            # When using queues, enrichers still add structured data that
            # PrintLogger can't handle, so use stdlib logger even with queues
            structlog.configure(
                processors=processors,
                wrapper_class=structlog.make_filtering_bound_logger(
                    getattr(logging, log_level.upper())
                ),
                logger_factory=structlog.stdlib.LoggerFactory(),
                cache_logger_on_first_use=True,
            )
        else:
            # When not using queues, we have renderers that convert to strings
            # so we need a logger factory that handles pre-rendered strings
            structlog.configure(
                processors=processors,
                wrapper_class=structlog.make_filtering_bound_logger(
                    getattr(logging, log_level.upper())
                ),
                logger_factory=structlog.stdlib.LoggerFactory(),
                cache_logger_on_first_use=True,
            )

    def _configure_metrics(self) -> None:
        """Configure metrics collection and Prometheus exporter."""
        # Initialize metrics collector if enabled
        if self._settings.metrics_enabled:
            from ._internal.metrics import create_metrics_collector

            self._metrics_collector = create_metrics_collector(
                enabled=True,
                sample_window=self._settings.metrics_sample_window,
            )

        # Initialize Prometheus exporter if enabled
        if self._settings.metrics_prometheus_enabled:
            from .monitoring import create_prometheus_exporter

            self._prometheus_exporter = create_prometheus_exporter(
                host=self._settings.metrics_prometheus_host,
                port=self._settings.metrics_prometheus_port,
                path="/metrics",
                enabled=True,
            )

    def _configure_httpx_trace_propagation(self) -> None:
        """Configure httpx trace propagation."""
        if self._settings.enable_httpx_trace_propagation:
            self._httpx_propagation = HttpxTracePropagation()
            self._httpx_propagation.configure(self._settings)

    def _register_middleware(self, app: Any) -> None:
        """Register middleware with the FastAPI app."""
        app.add_middleware(
            TraceIDMiddleware, trace_id_header=self._settings.trace_id_header
        )
        # Register shutdown event for graceful queue worker shutdown
        if self._queue_worker is not None:
            app.add_event_handler("shutdown", self.shutdown)

    async def shutdown(self) -> None:
        """Shutdown the container gracefully (async version)."""
        with self._lock:
            # Shutdown Prometheus exporter
            if self._prometheus_exporter is not None:
                try:
                    await self._prometheus_exporter.stop()
                except Exception as e:
                    logger.warning(f"Error during Prometheus exporter shutdown: {e}")
                finally:
                    self._prometheus_exporter = None

            if self._queue_worker is not None:
                try:
                    await self._queue_worker.shutdown()
                except Exception as e:
                    logger.warning(f"Error during queue worker shutdown: {e}")
                finally:
                    self._queue_worker = None

            if self._httpx_propagation is not None:
                try:
                    self._httpx_propagation.cleanup()
                except Exception as e:
                    logger.warning(f"Error during httpx propagation cleanup: {e}")
                finally:
                    self._httpx_propagation = None

            # Reset metrics components
            self._metrics_collector = None

            self._sinks.clear()

    def shutdown_sync(self) -> None:
        """Shutdown the container gracefully (sync version)."""
        with self._lock:
            # Reset metrics components (sync version doesn't need to stop Prometheus)
            self._prometheus_exporter = None
            self._metrics_collector = None

            if self._queue_worker is not None:
                try:
                    self._queue_worker.shutdown_sync()
                except Exception as e:
                    logger.warning(f"Error during sync queue worker shutdown: {e}")
                finally:
                    self._queue_worker = None

            if self._httpx_propagation is not None:
                try:
                    self._httpx_propagation.cleanup()
                except Exception as e:
                    logger.warning(f"Error during httpx propagation cleanup: {e}")
                finally:
                    self._httpx_propagation = None

            self._sinks.clear()

    def reset(self) -> None:
        """Reset the container for testing purposes."""
        with self._lock:
            self.shutdown_sync()
            self._configured = False

            # Reset metrics components
            self._metrics_collector = None
            self._prometheus_exporter = None

            # Reset structlog configuration
            structlog.reset_defaults()

            # Remove all handlers from root logger
            root_logger = logging.getLogger()
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)

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
        """Async setup for container components (e.g., start Prometheus exporter).

        This should be called after configure() if using async components.
        """
        with self._lock:
            # Start Prometheus exporter if configured
            if self._prometheus_exporter is not None:
                try:
                    await self._prometheus_exporter.start()
                except Exception as e:
                    logger.warning(f"Failed to start Prometheus exporter: {e}")

    def get_logger(self, name: str = "") -> structlog.BoundLogger:
        """Get a configured logger from this container.

        Args:
            name: Optional logger name

        Returns:
            A configured structlog.BoundLogger instance
        """
        return structlog.get_logger(name)


def cleanup_all_containers() -> None:
    """Clean up all container instances."""
    with _registry_lock:
        containers = [ref() for ref in _container_registry if ref() is not None]

    for container in containers:
        if container is not None:
            try:
                container.shutdown_sync()
            except Exception as e:
                logger.warning(f"Error cleaning up container: {e}")


# Register global cleanup on exit
atexit.register(cleanup_all_containers)
