"""ContextualComponentManager - Context-based component management.

Uses Python's contextvars for complete context isolation.

This module provides a ContextualComponentManager that manages components using
Python's contextvars for complete context isolation, eliminating global state
and providing automatic cleanup per execution context.
"""

import contextvars
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional, Type, TypeVar

T = TypeVar("T")

# Context variable for component storage per execution context
_container_components: contextvars.ContextVar[Optional[Dict[Type[Any], Any]]] = (
    contextvars.ContextVar("container_components", default=None)
)


class ContextualComponentManager:
    """Context-based component manager using Python's contextvars.

    This manager provides component isolation using Python's built-in
    contextvars
    module, ensuring that each execution context (async tasks, threads, etc.)
    maintains its own component registry without global state dependencies.

    All operations are context-scoped and automatically cleaned up when the
    context exits. This approach is particularly beneficial for:
    - FastAPI request contexts
    - Async/await coroutine isolation
    - Background task separation
    - Multi-tenant request handling

    Example:
        # Basic usage within a context
        with ContextualComponentManager.container_context():
            ContextualComponentManager.set_component(
                MyService, service_instance
            )
            service = ContextualComponentManager.get_component(MyService)

        # Async usage
        async def handle_request():
            with ContextualComponentManager.container_context():
                service = ContextualComponentManager.get_component(MyService)
                await service.process()
    """

    @staticmethod
    def get_component(component_type: Type[T]) -> Optional[T]:
        """Get component instance from current context.

        Retrieves a component instance of the specified type from the current
        execution context. Returns None if no component of that type has been
        registered in the current context.

        Args:
            component_type: The type/class of the component to retrieve

        Returns:
            Component instance of the specified type, or None if not found

        Example:
            service = ContextualComponentManager.get_component(MyService)
            if service:
                result = service.process()
        """
        components = _container_components.get()
        if components is None:
            return None
        return components.get(component_type)

    @staticmethod
    def set_component(component_type: Type[T], instance: T) -> None:
        """Set component instance in current context.

        Registers a component instance of the specified type in the current
        execution context. The component will only be available within the
        current context and will not affect other execution contexts.

        Args:
            component_type: The type/class of the component to register
            instance: The component instance to register

        Raises:
            TypeError: If instance is not of the expected component_type

        Example:
            service = MyService()
            ContextualComponentManager.set_component(MyService, service)
        """
        if not isinstance(instance, component_type):
            raise TypeError(
                f"Instance must be of type {component_type.__name__}, "
                f"got {type(instance).__name__}"
            )

        # Get current components dict and create a new copy
        current_components = _container_components.get()
        if current_components is None:
            current_components = {}
        else:
            current_components = current_components.copy()
        current_components[component_type] = instance

        # Set the updated components dict in context
        _container_components.set(current_components)

    @staticmethod
    def has_component(component_type: Type[Any]) -> bool:
        """Check if component type is registered in current context.

        Args:
            component_type: The type/class to check for

        Returns:
            True if component is registered, False otherwise

        Example:
            if ContextualComponentManager.has_component(MyService):
                service = ContextualComponentManager.get_component(MyService)
        """
        components = _container_components.get()
        if components is None:
            return False
        return component_type in components

    @staticmethod
    def remove_component(component_type: Type[Any]) -> bool:
        """Remove component from current context.

        Args:
            component_type: The type/class to remove

        Returns:
            True if component was removed, False if it wasn't registered

        Example:
            removed = ContextualComponentManager.remove_component(MyService)
        """
        current_components = _container_components.get()
        if current_components is None or component_type not in current_components:
            return False

        # Create new dict without the component
        updated_components = {
            k: v for k, v in current_components.items() if k != component_type
        }
        _container_components.set(updated_components)
        return True

    @staticmethod
    def clear_components() -> None:
        """Clear all components from current context.

        Removes all registered components from the current execution context.
        This does not affect components in other contexts.

        Example:
            ContextualComponentManager.clear_components()
        """
        _container_components.set(None)

    @staticmethod
    def get_component_count() -> int:
        """Get number of registered components in current context.

        Returns:
            Number of components registered in current context

        Example:
            count = ContextualComponentManager.get_component_count()
        """
        components = _container_components.get()
        if components is None:
            return 0
        return len(components)

    @staticmethod
    def get_component_types() -> list[Type[Any]]:
        """Get list of registered component types in current context.

        Returns:
            List of component types registered in current context

        Example:
            types = ContextualComponentManager.get_component_types()
            for component_type in types:
                print(f"Registered: {component_type.__name__}")
        """
        components = _container_components.get()
        if components is None:
            return []
        return list(components.keys())

    @staticmethod
    @contextmanager
    def container_context() -> Generator[None, None, None]:
        """Context manager for isolated container contexts.

        Creates an isolated execution context where components can be
        registered
        and retrieved without affecting other contexts. When the context exits,
        all components are automatically cleaned up.

        The context manager ensures proper isolation and cleanup:
        - Components registered within the context are isolated
        - Context changes don't affect other running contexts
        - Automatic cleanup when context manager exits
        - Thread-safe context variable operations

        Yields:
            None

        Example:
            with ContextualComponentManager.container_context():
                # Components registered here are isolated
                ContextualComponentManager.set_component(MyService, service)
                # ... use components ...
            # Automatic cleanup happens here

        Async Example:
            async def process_request():
                with ContextualComponentManager.container_context():
                    service = (
                        ContextualComponentManager.get_component(MyService)
                    )
                    await service.process()
        """
        # Create a fresh context with empty components
        token = _container_components.set({})
        try:
            yield
        finally:
            # Reset context to previous state
            _container_components.reset(token)
