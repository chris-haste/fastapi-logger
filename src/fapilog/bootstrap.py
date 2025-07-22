"""Bootstrap configuration for fapilog structured logging."""

from typing import Any, List, Optional, Union

import structlog

from ._internal.queue import Sink
from .container import LoggingContainer
from .settings import LoggingSettings

# Default container instance for backward compatibility
_default_container: Optional[LoggingContainer] = None


def _get_default_container() -> LoggingContainer:
    """Get or create the default container instance."""
    global _default_container
    if _default_container is None:
        _default_container = LoggingContainer()
    return _default_container


def configure_logging(
    settings: Optional[LoggingSettings] = None,
    app: Optional[Any] = None,
    sinks: Optional[List[Union[str, Sink]]] = None,
) -> structlog.BoundLogger:
    """Configure structured logging for the application.

    This function is idempotent - subsequent calls will not duplicate handlers
    or re-initialize sinks.

    Args:
        settings: Optional LoggingSettings instance. If None, created from env.
        app: Optional FastAPI app instance. If provided, TraceIDMiddleware
             will be registered once.
        sinks: Optional list of sink URIs or sink instances. If provided,
               overrides the sinks setting in LoggingSettings.

    Returns:
        A configured structlog.BoundLogger instance

    Raises:
        RuntimeError: If called from an async context without proper setup
    """
    # Handle sinks parameter
    if sinks is not None:
        # Override settings.sinks with provided sinks
        if settings is None:
            settings = LoggingSettings()
        else:
            # Create a copy to avoid modifying the original
            settings = LoggingSettings(**settings.model_dump())
        settings.sinks = sinks

    container = _get_default_container()
    result = container.configure(
        settings=settings,
        app=app,
    )

    # Update global queue worker for backward compatibility
    from ._internal.queue import set_queue_worker

    set_queue_worker(container.queue_worker)

    return result


def reset_logging() -> None:
    """Reset logging configuration for testing purposes."""
    global _default_container
    if _default_container is not None:
        _default_container.reset()
        _default_container = None


def _shutdown_queue_worker() -> None:
    """Shutdown the queue worker gracefully.

    This function is provided for test compatibility.
    """
    global _default_container
    if _default_container is not None:
        _default_container.shutdown_sync()


def _determine_console_format(console_format: str) -> str:
    """Determine the console output format.

    This function is provided for test compatibility.
    """
    import sys

    valid_formats = {"auto", "pretty", "json"}
    if console_format not in valid_formats:
        from ._internal.error_handling import handle_configuration_error

        raise handle_configuration_error(
            ValueError(f"Invalid console_format: {console_format}"),
            "console_format",
            console_format,
            f"one of {', '.join(valid_formats)}",
        )

    if console_format == "auto":
        return "pretty" if sys.stderr.isatty() else "json"
    return console_format
