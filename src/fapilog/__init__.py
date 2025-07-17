"""FastAPI logging middleware with structured logging and multiple sinks."""

import structlog

from .bootstrap import configure_logging
from ._internal.context import get_trace_id as get_current_trace_id

__all__ = ["configure_logging", "log", "get_current_trace_id"]

# Import the logger instance
log = structlog.get_logger()
