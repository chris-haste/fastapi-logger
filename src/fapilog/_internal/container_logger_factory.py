"""Container-specific logger factory for true container isolation.

This module provides ContainerLoggerFactory which creates structlog loggers
without relying on global structlog.configure() calls, enabling true container
isolation and eliminating global state dependencies.
"""

import logging
from typing import TYPE_CHECKING, Any, List, Optional, cast

import structlog

from ..pipeline import build_processor_chain

if TYPE_CHECKING:
    from ..container import LoggingContainer


class ContainerLoggerFactory:
    """Factory for creating loggers with container-specific configuration.

    This factory creates structlog loggers without global state dependencies,
    enabling true container isolation. Each factory is tied to a specific
    container and builds its configuration lazily on first use.

    Key Features:
    - Lazy initialization for optimal performance
    - Container-specific processor chains
    - No global structlog configuration dependencies
    - Thread-safe configuration building
    - Memory efficient (configuration built once per factory)
    """

    def __init__(self, container: "LoggingContainer") -> None:
        """Initialize factory with container-specific configuration.

        Args:
            container: LoggingContainer instance providing settings and context
        """
        self.container = container
        self._processors: Optional[List[Any]] = None
        self._wrapper_class: Optional[Any] = None
        self._configured = False

    def _build_configuration(self) -> None:
        """Build container-specific configuration once (lazy initialization).

        This method builds the processor chain and wrapper class based on the
        container's settings. It's called automatically on first logger creation
        and ensures optimal performance by building configuration only once.

        Raises:
            AttributeError: If container is missing required attributes
            ValueError: If container settings are invalid
        """
        if self._configured:
            return

        try:
            # Use cached console format from container (performance optimization)
            console_format = getattr(self.container, "_console_format", None)
            if console_format is None:
                # Fallback: use ConfigurationManager for consistency
                from .configuration_manager import ConfigurationManager

                console_format = ConfigurationManager.determine_console_format(
                    self.container._settings.json_console
                )

            # Build processor chain using existing pipeline function
            self._processors = build_processor_chain(
                self.container._settings,
                pretty=(console_format == "pretty"),
                container=self.container,
            )

            # Create wrapper class with container's log level
            log_level = getattr(logging, self.container._settings.level.upper())
            self._wrapper_class = structlog.make_filtering_bound_logger(log_level)

            self._configured = True

        except AttributeError as e:
            raise ValueError(f"Container missing required configuration: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to build container configuration: {e}") from e

    def create_logger(self, name: str = "") -> structlog.BoundLogger:
        """Create logger without global structlog configuration.

        Creates a structlog BoundLogger instance using container-specific
        configuration without relying on global structlog state. This enables
        true container isolation and thread-safe logger creation.

        Args:
            name: Optional logger name for stdlib logger identification

        Returns:
            A configured structlog.BoundLogger instance with container-specific
            processor chain and filtering

        Raises:
            ValueError: If container configuration is invalid
        """
        # Ensure configuration is built
        self._build_configuration()

        # Get stdlib logger - this doesn't rely on global structlog config
        stdlib_logger = logging.getLogger(name)

        # Create bound logger with container-specific processors
        # This bypasses structlog.get_logger() which uses global config
        return cast(
            structlog.BoundLogger,
            self._wrapper_class(
                stdlib_logger,
                processors=self._processors,
                context={},
            ),
        )

    def is_configured(self) -> bool:
        """Check if factory has been configured.

        Returns:
            True if factory configuration has been built, False otherwise
        """
        return self._configured

    def reset(self) -> None:
        """Reset factory configuration for testing.

        Clears the cached configuration, forcing it to be rebuilt on next
        logger creation. This is primarily useful for testing scenarios
        where container settings may change.
        """
        self._processors = None
        self._wrapper_class = None
        self._configured = False
