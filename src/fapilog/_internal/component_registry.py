"""ComponentRegistry - Thread-safe component management for container isolation.

This module provides a ComponentRegistry class that manages component lifecycles
per container with thread-safe operations, eliminating global state dependencies.
"""

import threading
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional, Type, TypeVar

T = TypeVar("T")


class ComponentRegistry:
    """Thread-safe component registry for container-scoped component management.

    Each container has its own registry instance to maintain component isolation
    and eliminate global state dependencies. All operations are thread-safe
    using reentrant locking.

    Attributes:
        container_id: Unique identifier for this container's registry

    Example:
        registry = ComponentRegistry("container_123")
        registry.register_component(MyService, my_service_instance)
        service = registry.get_component(MyService)
        registry.cleanup()  # Clean up all components
    """

    def __init__(self, container_id: Optional[str] = None):
        """Initialize ComponentRegistry with unique container ID.

        Args:
            container_id: Optional container identifier. If None, generates
                         unique ID based on object instance.
        """
        self.container_id = container_id or f"container_{id(self)}"
        self._components: Dict[Type[Any], Any] = {}
        self._lock = threading.RLock()

    def register_component(self, component_type: Type[T], instance: T) -> None:
        """Register component instance for this container.

        Args:
            component_type: The type/class of the component to register
            instance: The component instance to register

        Raises:
            TypeError: If instance is not of the expected component_type

        Example:
            registry.register_component(MyService, my_service_instance)
        """
        if not isinstance(instance, component_type):
            raise TypeError(
                f"Instance of type {type(instance).__name__} is not compatible "
                f"with component type {component_type.__name__}"
            )

        with self._lock:
            self._components[component_type] = instance

    def get_component(self, component_type: Type[T]) -> Optional[T]:
        """Retrieve component instance for this container.

        Args:
            component_type: The type/class of the component to retrieve

        Returns:
            Component instance if found, None otherwise

        Example:
            service = registry.get_component(MyService)
            if service:
                service.do_something()
        """
        with self._lock:
            return self._components.get(component_type)

    def get_or_create_component(
        self, component_type: Type[T], factory: Callable[[], T]
    ) -> T:
        """Get existing component or create new using factory.

        This method provides thread-safe lazy initialization. If the component
        already exists, it returns the existing instance. Otherwise, it calls
        the factory function to create a new instance.

        Args:
            component_type: The type/class of the component
            factory: Factory function that creates new component instance

        Returns:
            Component instance (existing or newly created)

        Example:
            service = registry.get_or_create_component(
                MyService,
                lambda: MyService(config)
            )
        """
        with self._lock:
            # Check if component already exists
            existing = self._components.get(component_type)
            if existing is not None:
                return existing

            # Create new component using factory
            new_instance = factory()

            # Validate type safety
            if not isinstance(new_instance, component_type):
                raise TypeError(
                    f"Factory returned instance of type "
                    f"{type(new_instance).__name__} which is not compatible "
                    f"with component type {component_type.__name__}"
                )

            # Register the new component
            self._components[component_type] = new_instance
            return new_instance

    def cleanup(self) -> None:
        """Clean up all components and call component cleanup methods.

        This method performs proper resource management by:
        1. Calling cleanup() method on components that have it
        2. Clearing the component registry

        Components are cleaned up in reverse registration order to handle
        potential dependencies correctly.

        Example:
            registry.cleanup()  # Cleans up all registered components
        """
        with self._lock:
            # Get components in reverse order for dependency cleanup
            components = list(self._components.values())
            components.reverse()

            # Call cleanup on components that support it
            for component in components:
                if hasattr(component, "cleanup") and callable(component.cleanup):
                    try:
                        component.cleanup()
                    except Exception:
                        # Log cleanup errors but continue with other components
                        # In a real implementation, this would use proper logging
                        pass

            # Clear all components
            self._components.clear()

    @contextmanager
    def component_lock(self):
        """Context manager for accessing multiple components atomically.

        Use this when you need to perform multiple component operations
        that should be atomic.

        Example:
            with registry.component_lock():
                service1 = registry.get_component(Service1)
                service2 = registry.get_component(Service2)
                # Both services accessed atomically
        """
        with self._lock:
            yield

    def __len__(self) -> int:
        """Return number of registered components."""
        with self._lock:
            return len(self._components)

    def __contains__(self, component_type: Type[Any]) -> bool:
        """Check if component type is registered."""
        with self._lock:
            return component_type in self._components

    def __repr__(self) -> str:
        """Return string representation of registry."""
        with self._lock:
            component_count = len(self._components)
            return (
                f"ComponentRegistry(container_id={self.container_id!r}, "
                f"components={component_count})"
            )
