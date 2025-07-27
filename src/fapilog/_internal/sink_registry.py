"""Sink registry for custom sinks in fapilog.

This module provides a global registry for custom sinks, allowing developers to
register custom sink implementations and use them via URI configuration.
"""

from typing import Dict, Optional, Type

from ..sinks import Sink


class SinkRegistry:
    """Global registry for custom sinks."""

    _sinks: Dict[str, Type[Sink]] = {}

    @classmethod
    def register(cls, name: str, sink_class: Type[Sink]) -> Type[Sink]:
        """Register a sink class with a name.

        Args:
            name: The name to register the sink under (used in URIs)
            sink_class: The sink class to register

        Returns:
            The registered sink class (for decorator chaining)

        Raises:
            ValueError: If name is empty or sink_class is not a Sink subclass
        """
        if not name or not name.strip():
            raise ValueError("Sink name cannot be empty")

        if not issubclass(sink_class, Sink):
            raise ValueError(f"Sink class {sink_class.__name__} must inherit from Sink")

        cls._sinks[name.strip()] = sink_class
        return sink_class

    @classmethod
    def get(cls, name: str) -> Optional[Type[Sink]]:
        """Get a registered sink class.

        Args:
            name: The name of the registered sink

        Returns:
            The sink class if found, None otherwise
        """
        return cls._sinks.get(name.strip() if name else "")

    @classmethod
    def list(cls) -> Dict[str, Type[Sink]]:
        """List all registered sinks.

        Returns:
            A copy of the registered sinks dictionary
        """
        return cls._sinks.copy()

    @classmethod
    def clear(cls) -> None:
        """Clear all registered sinks (primarily for testing)."""
        cls._sinks.clear()


def register_sink(name: str):
    """Decorator to register a sink class.

    Args:
        name: The name to register the sink under

    Returns:
        Decorator function that registers the sink

    Example:
        @register_sink("postgres")
        class PostgresSink(Sink):
            ...
    """

    def decorator(sink_class: Type[Sink]) -> Type[Sink]:
        return SinkRegistry.register(name, sink_class)

    return decorator
