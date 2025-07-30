"""Bootstrap configuration for fapilog structured logging."""

from typing import Any, List, Optional, Union

import structlog

from .container import LoggingContainer
from .settings import LoggingSettings
from .sinks import Sink

# Container registry for lifecycle management
# This is NOT global state - it's a registry for explicit cleanup
_active_containers: List[LoggingContainer] = []


def configure_logging(
    settings: Optional[LoggingSettings] = None,
    app: Optional[Any] = None,
    sinks: Optional[List[Union[str, Sink]]] = None,
) -> structlog.BoundLogger:
    """Configure structured logging for the application.

    This function creates a new isolated container instance each time it's called,
    providing complete isolation while maintaining backward compatibility.

    Args:
        settings: Optional LoggingSettings instance. If None, created from env.
        app: Optional FastAPI app instance. If provided, TraceIDMiddleware
             will be registered once.
        sinks: Optional list of sink URIs or sink instances. If provided,
               overrides the sinks setting in LoggingSettings.

    Returns:
        A configured structlog.BoundLogger instance

    Raises:
        RuntimeError: If called from an async context without proper setup
    """
    # Handle sinks parameter
    if sinks is not None:
        # Override settings.sinks with provided sinks
        if settings is None:
            settings = LoggingSettings()
        else:
            # Create a copy to avoid modifying the original
            settings = LoggingSettings(**settings.model_dump())
        settings.sinks = sinks

    # Create a new isolated container instance using pure dependency injection
    container = (
        LoggingContainer.create_from_settings(settings)
        if settings
        else LoggingContainer.create_with_defaults()
    )

    # Configure the container
    result = container.configure(
        settings=settings,
        app=app,
    )

    # Register container for lifecycle management
    _active_containers.append(container)

    return result


def reset_logging() -> None:
    """Reset all active logging containers for testing purposes.

    This function resets all containers created via configure_logging()
    and clears the active container registry.
    """
    # Reset all active containers
    for container in _active_containers:
        try:
            container.reset()
        except Exception:
            # Ignore errors during reset for robustness
            pass

    # Clear the registry
    _active_containers.clear()


def shutdown_logging() -> None:
    """Shutdown all active logging containers gracefully.

    This function should be called during application shutdown to ensure
    all containers are properly cleaned up.
    """
    # Shutdown all active containers
    for container in _active_containers:
        try:
            container.shutdown_sync()
        except Exception:
            # Ignore errors during shutdown for robustness
            pass

    # Clear the registry
    _active_containers.clear()


def _shutdown_queue_worker() -> None:
    """Shutdown queue workers in all active containers gracefully.

    This function is provided for test compatibility and backward compatibility.
    """
    for container in _active_containers:
        if container.queue_worker is not None:
            try:
                container.shutdown_sync()
            except Exception:
                # Ignore errors during shutdown for robustness
                pass


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


def get_active_containers() -> List[LoggingContainer]:
    """Get list of active containers for advanced use cases.

    This function is provided for advanced users who need access to the
    container instances for lifecycle management or testing.

    Returns:
        List of currently active LoggingContainer instances
    """
    return _active_containers.copy()


def configure_with_container(
    settings: Optional[LoggingSettings] = None,
    app: Optional[Any] = None,
    sinks: Optional[List[Union[str, Sink]]] = None,
) -> tuple[structlog.BoundLogger, LoggingContainer]:
    """Configure logging and return both logger and container.

    This function provides explicit access to the container for advanced
    use cases while maintaining the same configuration logic.

    Args:
        settings: Optional LoggingSettings instance. If None, created from env.
        app: Optional FastAPI app instance.
        sinks: Optional list of sink URIs or sink instances.

    Returns:
        Tuple of (logger, container) for explicit lifecycle management
    """
    # Handle sinks parameter
    if sinks is not None:
        if settings is None:
            settings = LoggingSettings()
        else:
            settings = LoggingSettings(**settings.model_dump())
        settings.sinks = sinks

    # Create isolated container
    container = (
        LoggingContainer.create_from_settings(settings)
        if settings
        else LoggingContainer.create_with_defaults()
    )

    # Configure the container
    logger = container.configure(settings=settings, app=app)

    # Register for lifecycle management
    _active_containers.append(container)

    return logger, container
