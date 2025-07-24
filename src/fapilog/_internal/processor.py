"""Processor base class and interface for fapilog structured logging."""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional


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


class FunctionProcessor(Processor):
    """Wrapper for function-based processors to maintain backward compatibility.

    This allows existing function-based processors to work with the new
    class-based processor interface without modification.
    """

    def __init__(self, func: Callable[..., Any], **config: Any) -> None:
        """Initialize function processor wrapper.

        Args:
            func: The processor function to wrap
            **config: Configuration parameters (not used by function processors)
        """
        self.func = func
        super().__init__(**config)

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Execute the wrapped function.

        Args:
            logger: The logger instance
            method_name: The logging method name
            event_dict: The event dictionary to process

        Returns:
            The result of the wrapped function
        """
        return self.func(logger, method_name, event_dict)

    def validate_config(self) -> None:
        """Validate configuration.

        Function processors don't require configuration validation since
        they wrap existing functions that don't use the config system.
        """
        pass
