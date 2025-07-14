"""Internal utilities for fapilog."""

from typing import Optional

import structlog


def get_logger(name: Optional[str] = None) -> structlog.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Optional logger name

    Returns:
        A structured logger instance
    """
    return structlog.get_logger(name)  # type: ignore[no-any-return]
