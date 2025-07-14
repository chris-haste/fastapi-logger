"""FastAPI logging middleware with structured logging and multiple sinks."""

import structlog

from .bootstrap import configure_logging

__all__ = ["configure_logging", "log"]

# Import the logger instance
log = structlog.get_logger()
