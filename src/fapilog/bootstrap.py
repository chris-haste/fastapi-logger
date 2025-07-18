"""Bootstrap configuration for fapilog structured logging."""

import atexit
import logging
import sys
import warnings
from typing import Any, Dict, Optional

import structlog

from ._internal.error_handling import handle_configuration_error, handle_sink_error
from ._internal.queue import QueueWorker, set_queue_worker
from .httpx_patch import configure_httpx_trace_propagation
from .middleware import TraceIDMiddleware
from .pipeline import build_processor_chain
from .settings import LoggingSettings
from .sinks.file import create_file_sink_from_uri
from .sinks.loki import create_loki_sink_from_uri
from .sinks.stdout import StdoutSink

# Module-level flag to track if logging has been configured
_configured = False
_queue_worker: Optional[QueueWorker] = None


def _validate_and_get_settings(settings: Optional[LoggingSettings]) -> LoggingSettings:
    """Validate and return LoggingSettings instance.

    Args:
        settings: Optional LoggingSettings instance

    Returns:
        Validated LoggingSettings instance

    Raises:
        ConfigurationError: If settings validation fails
    """
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


def _apply_deprecated_overrides(
    level: Optional[str], json_console: Optional[str], sinks: Optional[Dict[str, Any]]
) -> None:
    """Apply deprecated keyword argument overrides with warnings.

    Args:
        level: Logging level override
        json_console: Console output format override
        sinks: Sinks configuration override
    """
    if level is not None or json_console is not None or sinks is not None:
        warnings.warn(
            "Using keyword arguments for configure_logging is deprecated. "
            "Use LoggingSettings instead.",
            DeprecationWarning,
            stacklevel=2,
        )


def _determine_console_format(console_format: str) -> str:
    """Determine the console output format.

    Args:
        console_format: Requested console format

    Returns:
        Final console format to use

    Raises:
        ConfigurationError: If console_format is invalid
    """
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


def _configure_standard_logging(log_level: str) -> None:
    """Configure standard library logging.

    Args:
        log_level: Logging level to configure

    Raises:
        ConfigurationError: If log_level is invalid
    """
    try:
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format="%(message)s",
            datefmt=None,
            force=True,  # Force reconfiguration
        )
    except AttributeError as e:
        raise handle_configuration_error(
            e,
            "log_level",
            log_level,
            "valid logging level (DEBUG/INFO/WARNING/ERROR/CRITICAL)",
        ) from e


def _setup_queue_worker(settings: LoggingSettings, console_format: str) -> QueueWorker:
    """Set up the queue worker with appropriate sinks.

    Args:
        settings: LoggingSettings instance
        console_format: Console output format ('json' or 'pretty')

    Returns:
        Configured QueueWorker instance

    Raises:
        ConfigurationError: If queue configuration is invalid
        SinkError: If sink initialization fails
    """
    # Create sinks based on settings
    sinks = []

    for sink_uri in settings.sinks:
        if sink_uri == "stdout":
            # Map console_format to StdoutSink mode
            if console_format == "pretty":
                mode = "pretty"
            elif console_format == "json":
                mode = "json"
            else:
                mode = "auto"
            sinks.append(StdoutSink(mode=mode))
        elif sink_uri.startswith("file://"):
            try:
                sinks.append(create_file_sink_from_uri(sink_uri))
            except Exception as e:
                raise handle_sink_error(
                    e, "file", {"uri": sink_uri}, "initialize"
                ) from e
        elif sink_uri.startswith(("loki://", "https://")) and "loki" in sink_uri:
            try:
                sinks.append(create_loki_sink_from_uri(sink_uri))
            except ImportError as e:
                raise handle_sink_error(
                    e, "loki", {"uri": sink_uri}, "initialize"
                ) from e
            except Exception as e:
                raise handle_sink_error(
                    e, "loki", {"uri": sink_uri}, "initialize"
                ) from e
        else:
            # Unknown sink type
            raise handle_sink_error(
                ValueError(f"Unknown sink type: {sink_uri}"),
                "unknown",
                {"uri": sink_uri},
                "initialize",
            )

    # Create queue worker with error handling
    try:
        worker = QueueWorker(
            sinks=sinks,
            queue_max_size=settings.queue_maxsize,
            batch_size=settings.queue_batch_size,
            batch_timeout=settings.queue_batch_timeout,
            retry_delay=settings.queue_retry_delay,
            max_retries=settings.queue_max_retries,
            overflow_strategy=settings.queue_overflow,
            sampling_rate=settings.sampling_rate,
        )
    except Exception as e:
        queue_config = {
            "queue_max_size": settings.queue_maxsize,
            "batch_size": settings.queue_batch_size,
            "batch_timeout": settings.queue_batch_timeout,
            "retry_delay": settings.queue_retry_delay,
            "max_retries": settings.queue_max_retries,
            "overflow_strategy": settings.queue_overflow,
            "sampling_rate": settings.sampling_rate,
        }
        raise handle_configuration_error(
            e, "queue_worker", queue_config, "valid queue configuration"
        ) from e

    # Don't start the worker immediately - it will be started when needed
    # This avoids event loop conflicts during shutdown

    # Register shutdown handler
    atexit.register(_shutdown_queue_worker)

    return worker


def _configure_structlog(
    settings: LoggingSettings, console_format: str, log_level: str
) -> None:
    """Configure structlog with processor chain.

    Args:
        settings: LoggingSettings instance
        console_format: Console output format
        log_level: Logging level
    """
    # Build structlog processor chain using the new pipeline
    processors = build_processor_chain(settings, pretty=(console_format == "pretty"))

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _register_middleware_and_handlers(
    app: Optional[Any], settings: LoggingSettings, queue_worker: Optional[QueueWorker]
) -> None:
    """Register middleware and event handlers if app is provided.

    Args:
        app: Optional FastAPI app instance
        settings: LoggingSettings instance
        queue_worker: Optional QueueWorker instance
    """
    if app is not None:
        app.add_middleware(TraceIDMiddleware, trace_id_header=settings.trace_id_header)
        # Register FastAPI shutdown event for graceful log flushing
        if queue_worker is not None:
            app.add_event_handler("shutdown", queue_worker.shutdown)


def configure_logging(
    level: Optional[str] = None,
    sinks: Optional[Dict[str, Any]] = None,
    json_console: Optional[str] = None,
    settings: Optional[LoggingSettings] = None,
    app: Optional[Any] = None,
) -> structlog.BoundLogger:
    """Configure structured logging for the application.

    This function is idempotent - subsequent calls will not duplicate handlers
    or re-initialize sinks.

    Args:
        level: Logging level override (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        sinks: Dictionary of sink configurations (reserved for future use)
        json_console: Override for console output format ('json' or 'pretty')
        settings: Optional LoggingSettings instance. If None, created from env.
        app: Optional FastAPI app instance. If provided, TraceIDMiddleware
             will be registered once.

    Returns:
        A configured structlog.BoundLogger instance

    Raises:
        RuntimeError: If called from an async context without proper setup
    """
    global _configured, _queue_worker

    # Check if already configured
    if _configured:
        # Still register middleware if app is provided
        if app is not None:
            # Get settings if not provided for middleware registration
            if settings is None:
                settings = LoggingSettings()
            app.add_middleware(
                TraceIDMiddleware, trace_id_header=settings.trace_id_header
            )
        return structlog.get_logger()  # type: ignore[no-any-return]

    # Validate and get settings
    settings = _validate_and_get_settings(settings)

    # Apply deprecated overrides with warnings
    _apply_deprecated_overrides(level, json_console, sinks)

    # Determine final configuration values
    log_level = level or settings.level
    console_format = _determine_console_format(json_console or settings.json_console)

    # Configure standard library logging
    _configure_standard_logging(log_level)

    # Initialize queue worker if enabled
    if settings.queue_enabled:
        _queue_worker = _setup_queue_worker(settings, console_format)
        set_queue_worker(_queue_worker)
    else:
        # Ensure no queue worker is set when queue is disabled
        set_queue_worker(None)

    # Configure structlog
    _configure_structlog(settings, console_format, log_level)

    # Mark as configured
    _configured = True

    # Configure httpx trace propagation
    configure_httpx_trace_propagation(settings)

    # Register middleware and handlers if app is provided
    _register_middleware_and_handlers(app, settings, _queue_worker)

    return structlog.get_logger()  # type: ignore[no-any-return]


def _shutdown_queue_worker() -> None:
    """Shutdown the queue worker gracefully."""
    global _queue_worker
    if _queue_worker is not None:
        try:
            _queue_worker.shutdown_sync()
        except Exception:
            # Ignore errors during shutdown
            pass


def reset_logging() -> None:
    """Reset logging configuration for testing purposes."""
    global _configured, _queue_worker
    _configured = False

    # Shutdown queue worker
    if _queue_worker is not None:
        _shutdown_queue_worker()

    # Reset structlog configuration
    structlog.reset_defaults()

    # Remove all handlers from root logger
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
