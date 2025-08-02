"""Bootstrap configuration for fapilog structured logging.

This module provides stateless configuration functions for creating
logging containers without global state management.
"""

from typing import Any, List, Optional, Tuple, Union

import structlog

from .container import LoggingContainer
from .settings import LoggingSettings
from .sinks import Sink


def create_logger(
    settings: Optional[LoggingSettings] = None,
    app: Optional[Any] = None,
    sinks: Optional[List[Union[str, Sink]]] = None,
) -> Tuple[structlog.BoundLogger, LoggingContainer]:
    """Create a configured logger with explicit container management.

    This is the recommended way to configure logging as it returns both
    the logger and container, allowing explicit lifecycle management.

    Args:
        settings: Optional LoggingSettings instance. If None, created from env.
        app: Optional FastAPI app instance. If provided, TraceIDMiddleware
             will be registered once.
        sinks: Optional list of sink URIs or sink instances. If provided,
               overrides the sinks setting in LoggingSettings.

    Returns:
        Tuple of (logger, container) for explicit lifecycle management

    Example:
        ```python
        logger, container = create_logger()
        try:
            logger.info("Application started")
            # ... use logger ...
        finally:
            container.shutdown_sync()  # Explicit cleanup
        ```
    """
    # Handle sinks parameter
    if sinks is not None:
        if settings is None:
            settings = LoggingSettings()
        else:
            # Create a copy to avoid modifying the original
            settings = LoggingSettings(**settings.model_dump())
        settings.sinks = sinks

    # Create isolated container using pure dependency injection
    container = (
        LoggingContainer.create_from_settings(settings)
        if settings
        else LoggingContainer.create_with_defaults()
    )

    # Configure the container
    logger = container.configure(settings=settings, app=app)

    return logger, container


def configure_logging(
    settings: Optional[LoggingSettings] = None,
    app: Optional[Any] = None,
    sinks: Optional[List[Union[str, Sink]]] = None,
) -> structlog.BoundLogger:
    """Configure structured logging and return only the logger.

    NOTE: This function does not provide container lifecycle management.
    For production use, prefer create_logger() which returns both logger
    and container for explicit cleanup.

    Args:
        settings: Optional LoggingSettings instance. If None, created from env.
        app: Optional FastAPI app instance. If provided, TraceIDMiddleware
             will be registered once.
        sinks: Optional list of sink URIs or sink instances. If provided,
               overrides the sinks setting in LoggingSettings.

    Returns:
        A configured structlog.BoundLogger instance

    Example:
        ```python
        # Simple usage (container lifecycle not managed)
        logger = configure_logging()
        logger.info("Application started")
        ```
    """
    logger, _ = create_logger(settings=settings, app=app, sinks=sinks)
    return logger


# Legacy alias for backward compatibility within the codebase
configure_with_container = create_logger
