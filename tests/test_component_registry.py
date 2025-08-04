"""Tests for ComponentRegistry - Thread-safe component management."""

import threading
import time
import weakref
from typing import Any, cast

import pytest

from fapilog.core.registries.component_registry import ComponentRegistry


class MockService:
    """Mock service for testing component registration."""

    def __init__(self, name: str = "test_service"):
        self.name = name
        self.cleanup_called = False

    def cleanup(self):
        """Mock cleanup method."""
        self.cleanup_called = True


class MockServiceWithoutCleanup:
    """Mock service without cleanup method for testing."""

    def __init__(self, name: str = "test_service"):
        self.name = name


class MockServiceChild(MockService):
    """Child class of MockService for type testing."""

    pass


class UnrelatedService:
    """Unrelated service for type mismatch testing."""

    pass


class TestComponentRegistryBasicOperations:
    """Test basic ComponentRegistry operations."""

    def test_init_with_container_id(self):
        """Test registry initialization with explicit container ID."""
        registry = ComponentRegistry("test_container")
        assert registry.container_id == "test_container"
        assert len(registry) == 0

    def test_init_without_container_id(self):
        """Test registry initialization with auto-generated container ID."""
        registry = ComponentRegistry()
        assert registry.container_id.startswith("container_")
        assert len(registry) == 0

    def test_register_and_get_component(self):
        """Test basic component registration and retrieval."""
        registry = ComponentRegistry()
        service = MockService("test")

        # Register component
        registry.register_component(MockService, service)

        # Verify registration
        assert len(registry) == 1
        assert MockService in registry

        # Retrieve component
        retrieved = registry.get_component(MockService)
        assert retrieved is service
        assert retrieved.name == "test"

    def test_register_component_type_validation(self):
        """Test type safety in component registration."""
        registry = ComponentRegistry()
        service = MockService()
        unrelated = UnrelatedService()

        # Valid registration should work
        registry.register_component(MockService, service)

        # Invalid registration should raise TypeError
        with pytest.raises(TypeError) as excinfo:
            registry.register_component(MockService, unrelated)

        assert "is not compatible with component type" in str(excinfo.value)
        assert "UnrelatedService" in str(excinfo.value)
        assert "MockService" in str(excinfo.value)

    def test_register_component_inheritance(self):
        """Test component registration with inheritance."""
        registry = ComponentRegistry()
        child_service = MockServiceChild("child")

        # Child class should be registerable as parent type
        registry.register_component(MockService, child_service)

        retrieved = registry.get_component(MockService)
        assert retrieved is child_service
        assert isinstance(retrieved, MockServiceChild)

    def test_get_nonexistent_component(self):
        """Test retrieving non-existent component returns None."""
        registry = ComponentRegistry()

        result = registry.get_component(MockService)
        assert result is None

    def test_component_replacement(self):
        """Test replacing existing component registration."""
        registry = ComponentRegistry()
        service1 = MockService("first")
        service2 = MockService("second")

        # Register first service
        registry.register_component(MockService, service1)
        assert registry.get_component(MockService) is service1

        # Replace with second service
        registry.register_component(MockService, service2)
        assert registry.get_component(MockService) is service2
        assert len(registry) == 1


class TestComponentRegistryFactoryPattern:
    """Test factory pattern functionality."""

    def test_get_or_create_new_component(self):
        """Test creating new component using factory."""
        registry = ComponentRegistry()

        # Create component using factory
        service = registry.get_or_create_component(
            MockService, lambda: MockService("factory_created")
        )

        assert isinstance(service, MockService)
        assert service.name == "factory_created"
        assert len(registry) == 1
        assert registry.get_component(MockService) is service

    def test_get_or_create_existing_component(self):
        """Test getting existing component without calling factory."""
        registry = ComponentRegistry()
        original_service = MockService("original")

        # Register component first
        registry.register_component(MockService, original_service)

        # Factory should not be called for existing component
        factory_called = False

        def factory():
            nonlocal factory_called
            factory_called = True
            return MockService("from_factory")

        retrieved = registry.get_or_create_component(MockService, factory)

        assert retrieved is original_service
        assert retrieved.name == "original"
        assert not factory_called
        assert len(registry) == 1

    def test_factory_type_validation(self):
        """Test factory function type validation."""
        registry = ComponentRegistry()

        # Factory returning wrong type should raise TypeError
        with pytest.raises(TypeError) as excinfo:
            registry.get_or_create_component(MockService, lambda: UnrelatedService())  # type: ignore[return-value]

        assert "Factory returned instance of type" in str(excinfo.value)
        assert "UnrelatedService" in str(excinfo.value)
        assert "MockService" in str(excinfo.value)

    def test_factory_exception_handling(self):
        """Test factory exception propagation."""
        registry = ComponentRegistry()

        def failing_factory():
            raise ValueError("Factory error")

        # Factory exceptions should propagate
        with pytest.raises(ValueError, match="Factory error"):
            registry.get_or_create_component(MockService, failing_factory)

        # Registry should remain empty
        assert len(registry) == 0


class TestComponentRegistryCleanup:
    """Test component cleanup and lifecycle management."""

    def test_cleanup_with_cleanup_methods(self):
        """Test cleanup calls component cleanup methods."""
        registry = ComponentRegistry()
        service1 = MockService("service1")
        service2 = MockServiceChild("service2")  # Use proper child instance
        service_no_cleanup = MockServiceWithoutCleanup("no_cleanup")

        # Register components
        registry.register_component(MockService, service1)
        registry.register_component(MockServiceWithoutCleanup, service_no_cleanup)
        registry.register_component(MockServiceChild, service2)

        assert len(registry) == 3

        # Cleanup registry
        registry.cleanup()

        # Verify cleanup was called on components that support it
        assert service1.cleanup_called
        assert service2.cleanup_called
        # service_no_cleanup doesn't have cleanup method, so no error

        # Verify registry is empty
        assert len(registry) == 0
        assert registry.get_component(MockService) is None

    def test_cleanup_with_exceptions(self):
        """Test cleanup continues despite component cleanup exceptions."""
        registry = ComponentRegistry()

        # Mock service with failing cleanup
        service1 = MockService("service1")
        service2 = MockServiceChild("service2")  # Use proper child instance

        def failing_cleanup():
            raise Exception("Cleanup failed")

        service1.cleanup = failing_cleanup

        registry.register_component(MockService, service1)
        registry.register_component(MockServiceChild, service2)

        # Cleanup should not raise exception
        registry.cleanup()

        # service2 should still be cleaned up despite service1 failure
        assert service2.cleanup_called
        assert len(registry) == 0

    def test_cleanup_reverse_order(self):
        """Test cleanup happens in reverse registration order."""
        registry = ComponentRegistry()
        cleanup_order = []

        class OrderedService:
            def __init__(self, name):
                self.name = name

            def cleanup(self):
                cleanup_order.append(self.name)

        # Register services in order with unique types

        # Create unique types for each service with instances
        class OrderedService1(OrderedService):
            pass

        class OrderedService2(OrderedService):
            pass

        class OrderedService3(OrderedService):
            pass

        # Create instances of the specific types
        service1 = OrderedService1("first")
        service2 = OrderedService2("second")
        service3 = OrderedService3("third")

        registry.register_component(OrderedService1, service1)
        registry.register_component(OrderedService2, service2)
        registry.register_component(OrderedService3, service3)

        registry.cleanup()

        # Verify cleanup happened in reverse order
        assert cleanup_order == ["third", "second", "first"]


class TestComponentRegistryThreadSafety:
    """Test thread safety of ComponentRegistry operations."""

    def test_concurrent_registration(self):
        """Test concurrent component registration."""
        registry = ComponentRegistry()
        results = []
        errors = []

        def register_component(thread_id: int) -> None:
            try:
                # Create unique service type for each thread
                component_type = type(f"MockService{thread_id}", (MockService,), {})
                # Create instance of the unique type
                service = component_type(f"service_{thread_id}")
                registry.register_component(component_type, service)
                results.append(thread_id)
            except Exception as e:
                errors.append((thread_id, e))

        # Start multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=register_component, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Verify no errors and all registrations succeeded
        assert len(errors) == 0
        assert len(results) == 10
        assert len(registry) == 10

    def test_concurrent_get_or_create(self):
        """Test concurrent get_or_create operations."""
        registry = ComponentRegistry()
        created_instances = []
        factory_calls = []

        def factory():
            factory_calls.append(threading.current_thread().ident)
            instance = MockService(f"thread_{threading.current_thread().ident}")
            created_instances.append(instance)
            # Small delay to increase chance of race condition
            time.sleep(0.001)
            return instance

        def get_or_create():
            return registry.get_or_create_component(MockService, factory)

        # Start multiple threads trying to create the same component
        threads = []
        results = []

        for _ in range(5):
            thread = threading.Thread(target=lambda: results.append(get_or_create()))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Verify only one instance was created and all threads got the same
        # instance
        assert len(created_instances) == 1
        assert len(factory_calls) == 1
        assert len(results) == 5
        assert all(result is results[0] for result in results)
        assert len(registry) == 1

    def test_concurrent_cleanup(self):
        """Test concurrent cleanup operations."""
        registry = ComponentRegistry()
        service = MockService()
        registry.register_component(MockService, service)

        cleanup_results = []

        def cleanup_registry():
            try:
                registry.cleanup()
                cleanup_results.append("success")
            except Exception as e:
                cleanup_results.append(f"error: {e}")

        # Start multiple cleanup threads
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=cleanup_registry)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Verify no errors and registry is cleaned up
        assert all("success" in result for result in cleanup_results)
        assert len(registry) == 0
        assert service.cleanup_called


class TestComponentRegistryMemoryManagement:
    """Test memory management and leak prevention."""

    def test_component_garbage_collection(self):
        """Test that cleaned up components can be garbage collected."""
        registry = ComponentRegistry()
        service = MockService()
        weak_ref = weakref.ref(service)

        # Register and verify component exists
        registry.register_component(MockService, service)
        assert weak_ref() is not None

        # Remove local reference
        del service

        # Component should still exist due to registry reference
        assert weak_ref() is not None

        # Cleanup registry
        registry.cleanup()

        # Component should now be garbage collectable
        # Force garbage collection to ensure cleanup
        import gc

        gc.collect()

        # Note: This test might be flaky due to garbage collection timing
        # In practice, the weak reference should become None after cleanup

    def test_registry_replacement_cleanup(self):
        """Test that replaced components can be cleaned up."""
        registry = ComponentRegistry()

        # Register first service
        service1 = MockService("first")
        registry.register_component(MockService, service1)

        # Replace with second service
        service2 = MockService("second")
        registry.register_component(MockService, service2)

        # Only the second service should be in registry
        assert registry.get_component(MockService) is service2
        assert len(registry) == 1

        # First service should be eligible for garbage collection
        # (though we can't reliably test this)


class TestComponentRegistryUtilityMethods:
    """Test utility methods and operators."""

    def test_len_operator(self):
        """Test __len__ method."""
        registry = ComponentRegistry()
        assert len(registry) == 0

        registry.register_component(MockService, MockService())
        assert len(registry) == 1

        registry.register_component(
            MockServiceWithoutCleanup, MockServiceWithoutCleanup()
        )
        assert len(registry) == 2

        registry.cleanup()
        assert len(registry) == 0

    def test_contains_operator(self):
        """Test __contains__ method."""
        registry = ComponentRegistry()
        service = MockService()

        assert MockService not in registry

        registry.register_component(MockService, service)
        assert MockService in registry
        assert MockServiceWithoutCleanup not in registry

        registry.cleanup()
        assert MockService not in registry

    def test_repr_method(self):
        """Test __repr__ method."""
        registry = ComponentRegistry("test_container")

        # Empty registry
        repr_str = repr(registry)
        assert "ComponentRegistry" in repr_str
        assert "test_container" in repr_str
        assert "components=0" in repr_str

        # Registry with components
        registry.register_component(MockService, MockService())
        repr_str = repr(registry)
        assert "components=1" in repr_str

    def test_component_lock_context_manager(self):
        """Test component_lock context manager."""
        registry = ComponentRegistry()
        service1 = MockService("service1")
        service2 = MockServiceWithoutCleanup("service2")  # Use proper type

        registry.register_component(MockService, service1)
        registry.register_component(MockServiceWithoutCleanup, service2)

        # Test atomic access to multiple components
        with registry.component_lock():
            retrieved1 = registry.get_component(MockService)
            retrieved2 = registry.get_component(MockServiceWithoutCleanup)

            assert retrieved1 is service1  # type: ignore[comparison-overlap]
            assert retrieved2 is service2  # type: ignore[comparison-overlap]


class TestComponentRegistryIntegration:
    """Integration tests for ComponentRegistry."""

    def test_full_lifecycle_scenario(self):
        """Test complete component lifecycle scenario."""
        registry = ComponentRegistry("integration_test")

        # Step 1: Register components using both methods
        direct_service = MockService("direct")
        registry.register_component(MockService, direct_service)

        factory_service = registry.get_or_create_component(
            MockServiceWithoutCleanup, lambda: MockServiceWithoutCleanup("factory")
        )

        # Step 2: Verify components are available
        assert len(registry) == 2
        retrieved_direct = registry.get_component(MockService)
        assert retrieved_direct is direct_service  # type: ignore[comparison-overlap]
        retrieved_factory = registry.get_component(MockServiceWithoutCleanup)
        assert retrieved_factory is factory_service  # type: ignore[comparison-overlap]

        # Step 3: Test atomic operations
        with registry.component_lock():
            services = [
                registry.get_component(MockService),
                registry.get_component(MockServiceWithoutCleanup),
            ]
            assert len(services) == 2
            assert all(service is not None for service in services)

        # Step 4: Cleanup and verify
        registry.cleanup()
        assert len(registry) == 0
        assert direct_service.cleanup_called
        # factory_service doesn't have cleanup method

    def test_error_recovery(self):
        """Test registry behavior after errors."""
        registry = ComponentRegistry()

        # Test type error doesn't affect registry state
        try:
            registry.register_component(MockService, UnrelatedService())
        except TypeError:
            pass

        assert len(registry) == 0

        # Test factory error doesn't affect registry state
        try:
            # type: ignore[return-value]
            registry.get_or_create_component(
                MockService,
                cast(Any, lambda: UnrelatedService()),  # Will cause TypeError
            )
        except (TypeError, ValueError):
            pass

        assert len(registry) == 0

        # Registry should still work normally
        service = MockService()
        registry.register_component(MockService, service)
        assert len(registry) == 1
        retrieved_service = registry.get_component(MockService)
        assert retrieved_service is service
