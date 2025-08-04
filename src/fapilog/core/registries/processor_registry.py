"""Processor registry for custom processors in fapilog.

This module provides a global registry for custom processors, allowing developers to
register custom processor implementations for use in the logging pipeline.
"""

from typing import Callable, Dict, Optional, Type

from ...processors.base import Processor


class ProcessorRegistry:
    """Global registry for custom processors."""

    _processors: Dict[str, Type[Processor]] = {}

    @classmethod
    def register(cls, name: str, processor_class: Type[Processor]) -> Type[Processor]:
        """Register a processor class with a name.

        Args:
            name: The name to register the processor under
            processor_class: The processor class to register

        Returns:
            The registered processor class (for decorator chaining)

        Raises:
            ValueError: If name is empty or processor_class is not a Processor subclass
        """
        if not name or not name.strip():
            raise ValueError("Processor name cannot be empty")

        if not issubclass(processor_class, Processor):
            raise ValueError(
                f"Processor class {processor_class.__name__} must inherit from Processor"
            )

        cls._processors[name.strip()] = processor_class
        return processor_class

    @classmethod
    def get(cls, name: str) -> Optional[Type[Processor]]:
        """Get a registered processor class.

        Args:
            name: The name of the registered processor

        Returns:
            The processor class if found, None otherwise
        """
        return cls._processors.get(name.strip() if name else "")

    @classmethod
    def list(cls) -> Dict[str, Type[Processor]]:
        """List all registered processors.

        Returns:
            A copy of the registered processors dictionary
        """
        return cls._processors.copy()

    @classmethod
    def clear(cls) -> None:
        """Clear all registered processors (primarily for testing)."""
        cls._processors.clear()


def register_processor(name: str) -> Callable[[Type[Processor]], Type[Processor]]:
    """Decorator to register a processor class.

    Args:
        name: The name to register the processor under

    Returns:
        Decorator function that registers the processor

    Example:
        @register_processor("custom_redaction")
        class CustomRedactionProcessor(Processor):

            ...
    """

    def decorator(processor_class: Type[Processor]) -> Type[Processor]:
        return ProcessorRegistry.register(name, processor_class)

    return decorator
