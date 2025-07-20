"""Bootstrap configuration for fapilog structured logging."""

from typing import Any, Dict, Optional

import structlog

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
    container = _get_default_container()
    result = container.configure(
        level=level,
        sinks=sinks,
        json_console=json_console,
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
