"""Bootstrap configuration for fapilog structured logging."""

import logging
import sys
import warnings
from typing import Any, Dict, Optional

import structlog

from .pipeline import build_processor_chain
from .settings import LoggingSettings

# Module-level flag to track if logging has been configured
_configured = False


def configure_logging(
    level: Optional[str] = None,
    sinks: Optional[Dict[str, Any]] = None,
    json_console: Optional[str] = None,
    settings: Optional[LoggingSettings] = None,
) -> structlog.BoundLogger:
    """Configure structured logging for the application.

    This function is idempotent - subsequent calls will not duplicate handlers
    or re-initialize sinks.

    Args:
        level: Logging level override (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        sinks: Dictionary of sink configurations (reserved for future use)
        json_console: Override for console output format ('json' or 'pretty')
        settings: Optional LoggingSettings instance. If None, created from env.

    Returns:
        A configured structlog.BoundLogger instance

    Raises:
        RuntimeError: If called from an async context without proper setup
    """
    global _configured

    # Check if already configured
    if _configured:
        return structlog.get_logger()  # type: ignore[no-any-return]

    # Get settings from environment if not provided
    if settings is None:
        settings = LoggingSettings()
    else:
        # Validate settings
        settings = LoggingSettings.model_validate(settings.model_dump())

    # At this point, settings is guaranteed to be a LoggingSettings instance

    # Apply overrides (with deprecation warning for backward compatibility)
    if level is not None or json_console is not None or sinks is not None:
        warnings.warn(
            "Using keyword arguments for configure_logging is deprecated. "
            "Use LoggingSettings instead.",
            DeprecationWarning,
            stacklevel=2,
        )

    log_level = level or settings.level
    console_format = json_console or settings.json_console

    # Detect interactive TTY for pretty output unless explicitly set
    if console_format == "auto":
        console_format = "pretty" if sys.stderr.isatty() else "json"

    # Configure standard library logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(message)s",
        datefmt=None,
        force=True,  # Force reconfiguration
    )

    # Build structlog processor chain using the new pipeline
    processors = build_processor_chain(settings, pretty=(console_format == "pretty"))

    # Configure structlog
    structlog.configure(
        processors=processors,  # type: ignore[arg-type]
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Mark as configured
    _configured = True

    return structlog.get_logger()  # type: ignore[no-any-return]


def reset_logging() -> None:
    """Reset logging configuration for testing purposes."""
    global _configured
    _configured = False

    # Reset structlog configuration
    structlog.reset_defaults()

    # Remove all handlers from root logger
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
