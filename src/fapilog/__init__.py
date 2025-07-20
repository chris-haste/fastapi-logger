"""FastAPI logging middleware with structured logging and multiple sinks."""

import importlib.metadata
from pathlib import Path
from typing import Any, Optional

import structlog

from ._internal.context import get_trace_id as get_current_trace_id
from .bootstrap import configure_logging
from .container import LoggingContainer
from .settings import LoggingSettings


def _get_version() -> str:
    """Get version from package metadata or pyproject.toml."""
    # First, try to get version from installed package metadata
    try:
        return importlib.metadata.version("fapilog")
    except (importlib.metadata.PackageNotFoundError, AttributeError, ImportError):
        pass

    # If not found in metadata (development/editable install),
    # try pyproject.toml
    try:
        # Try tomllib first (Python 3.11+)
        import tomllib
    except ImportError:
        # Fallback to tomli for older Python versions
        try:
            import tomli as tomllib
        except ImportError:
            return "0.1.2"  # Fallback version

    # Find pyproject.toml relative to this file
    current_file = Path(__file__)
    pyproject_path = current_file.parent.parent.parent / "pyproject.toml"

    try:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
            return data["project"]["version"]
    except (KeyError, FileNotFoundError, OSError):
        return "0.1.2"  # Fallback version


# Get version from package metadata or pyproject.toml
__version__ = _get_version()

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
