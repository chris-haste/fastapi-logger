"""FastAPI logging middleware with structured logging and multiple sinks."""

from typing import Any, Optional

import structlog

from ._internal.context import get_trace_id as get_current_trace_id
from .bootstrap import configure_logging
from .container import LoggingContainer
from .settings import LoggingSettings

__version__ = "0.1.0"

__all__ = [
    "configure_logging",
    "create_logging_container",
    "get_logger",
    "get_current_trace_id",
    "__version__",
]


def get_logger(name: str = "") -> structlog.BoundLogger:
    """Get a configured structlog logger.

    Args:
        name: Optional logger name

    Returns:
        A configured structlog.BoundLogger instance
    """
    return structlog.get_logger(name)


def create_logging_container(
    settings: Optional[LoggingSettings] = None,
) -> LoggingContainer:
    """Create a new logging container instance.

    Args:
        settings: Optional LoggingSettings instance. If None, created from env.

    Returns:
        A new LoggingContainer instance
    """
    return LoggingContainer(settings)


# For backward compatibility, expose log as a function
def _get_log() -> structlog.BoundLogger:
    """Get the default logger for backward compatibility."""
    return get_logger()


# Create a property-like access for log
class _LogProxy:
    """Proxy object that provides lazy access to the configured logger."""

    def __getattr__(self, name: str) -> Any:
        """Delegate all attribute access to the configured logger."""
        logger = get_logger()
        return getattr(logger, name)


# Create the proxy instance
log = _LogProxy()
