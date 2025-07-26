"""Processor base class and interface for fapilog structured logging."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class Processor(ABC):
    """Base class for all processors.

    Provides lifecycle management, configuration validation, and a standardized
    interface for processing log events.
    """

    def __init__(self, **config: Any) -> None:
        """Initialize processor with configuration.

        Args:
            **config: Configuration parameters for the processor
        """
        self.config = config
        self._started = False
        self.validate_config()

    async def start(self) -> None:
        """Initialize processor resources.

        This method is idempotent - subsequent calls will not duplicate
        initialization.
        """
        if self._started:
            return
        await self._start_impl()
        self._started = True

    async def stop(self) -> None:
        """Clean up processor resources.

        This method is idempotent - subsequent calls will not duplicate
        cleanup operations.
        """
        if not self._started:
            return
        await self._stop_impl()
        self._started = False

    async def _start_impl(self) -> None:
        """Processor-specific startup logic.

        Override this method to implement custom initialization logic.
        The default implementation does nothing.
        """
        # Default implementation - processors can override if needed
        return

    async def _stop_impl(self) -> None:
        """Processor-specific cleanup logic.

        Override this method to implement custom cleanup logic.
        The default implementation does nothing.
        """
        # Default implementation - processors can override if needed
        return

    @abstractmethod
    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Process a log event.

        Args:
            logger: The logger instance
            method_name: The logging method name (e.g., 'info', 'error')
            event_dict: The event dictionary to process

        Returns:
            The processed event dictionary, or None to drop the event
        """
        pass

    def validate_config(self) -> None:
        """Validate processor configuration.

        Override this method to implement custom configuration validation.
        The default implementation does nothing.

        Raises:
            ValueError: If configuration is invalid
        """
        # Default implementation - processors can override if needed
        return

    @property
    def is_started(self) -> bool:
        """Check if processor is started.

        Returns:
            True if the processor has been started, False otherwise
        """
        return self._started
