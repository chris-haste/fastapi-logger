"""Bootstrap configuration for fapilog structured logging."""

import atexit
import logging
import sys
import warnings
from typing import Any, Dict, Optional

import structlog

from ._internal.queue import QueueWorker, set_queue_worker
from .middleware import TraceIDMiddleware
from .pipeline import build_processor_chain
from .settings import LoggingSettings
from .sinks.stdout import StdoutSink
from .sinks.file import create_file_sink_from_uri  # <-- add this import

# Module-level flag to track if logging has been configured
_configured = False
_queue_worker: Optional[QueueWorker] = None


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
            app.add_middleware(TraceIDMiddleware)
        return structlog.get_logger()  # type: ignore[no-any-return]

    # Get settings from environment if not provided
    if settings is None:
        settings = LoggingSettings()
    else:
        # Validate settings
        settings = LoggingSettings.model_validate(settings.model_dump())

    # At this point, settings is guaranteed to be a LoggingSettings instance

    # Apply overrides (with deprecation warning for backward compatibility)
    if level is not None or json_console is not None or sinks is not None:
        warnings.warn(
            "Using keyword arguments for configure_logging is deprecated. "
            "Use LoggingSettings instead.",
            DeprecationWarning,
            stacklevel=2,
        )

    log_level = level or settings.level
    console_format = json_console or settings.json_console

    # Detect interactive TTY for pretty output unless explicitly set
    if console_format == "auto":
        console_format = "pretty" if sys.stderr.isatty() else "json"

    # Configure standard library logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(message)s",
        datefmt=None,
        force=True,  # Force reconfiguration
    )

    # Initialize queue worker if enabled
    if settings.queue_enabled:
        _queue_worker = _setup_queue_worker(settings, console_format)
        set_queue_worker(_queue_worker)
    else:
        # Ensure no queue worker is set when queue is disabled
        set_queue_worker(None)

    # Build structlog processor chain using the new pipeline
    processors = build_processor_chain(settings, pretty=(console_format == "pretty"))

    # Configure structlog
    structlog.configure(
        processors=processors,  # type: ignore[arg-type]
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Mark as configured
    _configured = True

    # Register middleware if app is provided
    if app is not None:
        app.add_middleware(TraceIDMiddleware)
        # Register FastAPI shutdown event for graceful log flushing
        if _queue_worker is not None:
            app.add_event_handler("shutdown", _queue_worker.shutdown)

    return structlog.get_logger()  # type: ignore[no-any-return]


def _setup_queue_worker(settings: LoggingSettings, console_format: str) -> QueueWorker:
    """Set up the queue worker with appropriate sinks.

    Args:
        settings: LoggingSettings instance
        console_format: Console output format ('json' or 'pretty')

    Returns:
        Configured QueueWorker instance
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
                raise RuntimeError(f"Failed to initialize file sink: {e}")
        # Future: elif sink_uri.startswith("loki://"): ...

    # Create queue worker
    worker = QueueWorker(
        sinks=sinks,
        queue_size=settings.queue_maxsize,
        batch_size=settings.queue_batch_size,
        batch_timeout=settings.queue_batch_timeout,
        retry_delay=settings.queue_retry_delay,
        max_retries=settings.queue_max_retries,
        overflow_strategy=settings.queue_overflow,
        sampling_rate=settings.sampling_rate,
    )

    # Don't start the worker immediately - it will be started when needed
    # This avoids event loop conflicts during shutdown

    # Register shutdown handler
    atexit.register(_shutdown_queue_worker)

    return worker


def _shutdown_queue_worker() -> None:
    """Shutdown the queue worker gracefully."""
    global _queue_worker
    if _queue_worker is not None:
        try:
            _queue_worker.shutdown_sync()
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(f"Error stopping queue worker: {e}")
        finally:
            _queue_worker = None


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
