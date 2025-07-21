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
            return "unknown"  # No TOML parser available

    # Try to find pyproject.toml in multiple locations
    current_file = Path(__file__)
    possible_paths = [
        current_file.parent.parent.parent
        / "pyproject.toml",  # src/fapilog/__init__.py -> pyproject.toml
        current_file.parent.parent
        / "pyproject.toml",  # src/__init__.py -> pyproject.toml
        current_file.parent / "pyproject.toml",  # __init__.py -> pyproject.toml
        Path("pyproject.toml"),  # Current working directory
    ]

    for pyproject_path in possible_paths:
        try:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
                return data["project"]["version"]
        except (KeyError, FileNotFoundError, OSError):
            continue

    # If all attempts fail, return unknown
    return "unknown"


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
