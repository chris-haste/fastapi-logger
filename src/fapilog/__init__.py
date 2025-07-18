"""FastAPI logging middleware with structured logging and multiple sinks."""

import structlog

from ._internal.context import get_trace_id as get_current_trace_id
from .bootstrap import configure_logging

__version__ = "0.1.0"

__all__ = ["configure_logging", "log", "get_current_trace_id", "__version__"]

# Import the logger instance
log = structlog.get_logger()
