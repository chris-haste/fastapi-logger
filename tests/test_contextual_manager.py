"""Tests for ContextualComponentManager - Context-based component management."""

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict

import pytest

from fapilog.core.managers.contextual_manager import ContextualComponentManager


# Test components for testing
class MockService:
    """Mock service for testing component management."""

    def __init__(self, name: str = "test_service"):
        self.name = name
        self.processed_count = 0

    def process(self) -> str:
        """Process method for testing."""
        self.processed_count += 1
        return f"Processed by {self.name} (count: {self.processed_count})"


class AnotherService:
    """Another service for multi-component testing."""

    def __init__(self, value: int = 42):
        self.value = value

    def calculate(self) -> int:
        """Calculate method for testing."""
        return self.value * 2


class UnrelatedService:
    """Unrelated service for type validation testing."""

    def __init__(self, data: str = "unrelated"):
        self.data = data


class TestContextualComponentManagerBasicOperations:
    """Test basic ContextualComponentManager operations."""

    def test_set_and_get_component(self):
        """Test basic component setting and retrieval."""
        with ContextualComponentManager.container_context():
            service = MockService("test")

            # Set component
            ContextualComponentManager.set_component(MockService, service)

            # Get component
            retrieved = ContextualComponentManager.get_component(MockService)
            assert retrieved is service
            assert retrieved.name == "test"

    def test_get_nonexistent_component(self):
        """Test getting component that doesn't exist returns None."""
        with ContextualComponentManager.container_context():
            result = ContextualComponentManager.get_component(MockService)
            assert result is None

    def test_get_component_outside_context(self):
        """Test getting component outside of context returns None."""
        # Outside of any context, should return None
        result = ContextualComponentManager.get_component(MockService)
        assert result is None

    def test_set_component_type_validation(self):
        """Test type validation when setting components."""
        with ContextualComponentManager.container_context():
            service = MockService()
            unrelated = UnrelatedService()

            # Valid registration should work
            ContextualComponentManager.set_component(MockService, service)

            # Invalid registration should raise TypeError
            with pytest.raises(TypeError) as excinfo:
                ContextualComponentManager.set_component(MockService, unrelated)

            assert "Instance must be of type MockService" in str(excinfo.value)
            assert "got UnrelatedService" in str(excinfo.value)

    def test_has_component(self):
        """Test checking if component exists."""
        with ContextualComponentManager.container_context():
            # Initially no components
            assert not ContextualComponentManager.has_component(MockService)

            # Add component
            service = MockService()
            ContextualComponentManager.set_component(MockService, service)

            # Now component exists
            assert ContextualComponentManager.has_component(MockService)
            assert not ContextualComponentManager.has_component(AnotherService)

    def test_has_component_outside_context(self):
        """Test checking component existence outside context."""
        # Outside context should return False
        assert not ContextualComponentManager.has_component(MockService)

    def test_remove_component(self):
        """Test removing components."""
        with ContextualComponentManager.container_context():
            service = MockService()
            another = AnotherService()

            # Add components
            ContextualComponentManager.set_component(MockService, service)
            ContextualComponentManager.set_component(AnotherService, another)

            # Verify both exist
            assert ContextualComponentManager.has_component(MockService)
            assert ContextualComponentManager.has_component(AnotherService)

            # Remove one component
            removed = ContextualComponentManager.remove_component(MockService)
            assert removed is True

            # Verify only one remains
            assert not ContextualComponentManager.has_component(MockService)
            assert ContextualComponentManager.has_component(AnotherService)

            # Try removing non-existent component
            removed = ContextualComponentManager.remove_component(MockService)
            assert removed is False

    def test_remove_component_outside_context(self):
        """Test removing component outside context."""
        # Outside context should return False
        removed = ContextualComponentManager.remove_component(MockService)
        assert removed is False

    def test_clear_components(self):
        """Test clearing all components."""
        with ContextualComponentManager.container_context():
            service = MockService()
            another = AnotherService()

            # Add components
            ContextualComponentManager.set_component(MockService, service)
            ContextualComponentManager.set_component(AnotherService, another)

            # Verify components exist
            assert ContextualComponentManager.get_component_count() == 2

            # Clear all components
            ContextualComponentManager.clear_components()

            # Verify all cleared
            assert ContextualComponentManager.get_component_count() == 0
            assert not ContextualComponentManager.has_component(MockService)
            assert not ContextualComponentManager.has_component(AnotherService)

    def test_get_component_count(self):
        """Test getting component count."""
        with ContextualComponentManager.container_context():
            # Initially no components
            assert ContextualComponentManager.get_component_count() == 0

            # Add components one by one
            ContextualComponentManager.set_component(MockService, MockService())
            assert ContextualComponentManager.get_component_count() == 1

            ContextualComponentManager.set_component(AnotherService, AnotherService())
            assert ContextualComponentManager.get_component_count() == 2

    def test_get_component_count_outside_context(self):
        """Test getting component count outside context."""
        # Outside context should return 0
        assert ContextualComponentManager.get_component_count() == 0

    def test_get_component_types(self):
        """Test getting list of component types."""
        with ContextualComponentManager.container_context():
            # Initially no types
            types = ContextualComponentManager.get_component_types()
            assert types == []

            # Add components
            ContextualComponentManager.set_component(MockService, MockService())
            ContextualComponentManager.set_component(AnotherService, AnotherService())

            # Get types
            types = ContextualComponentManager.get_component_types()
            assert len(types) == 2
            assert MockService in types
            assert AnotherService in types

    def test_get_component_types_outside_context(self):
        """Test getting component types outside context."""
        # Outside context should return empty list
        types = ContextualComponentManager.get_component_types()
        assert types == []


class TestContextualComponentManagerContextIsolation:
    """Test context isolation functionality."""

    def test_basic_context_isolation(self):
        """Test that different contexts are isolated."""
        service1 = MockService("service1")
        service2 = MockService("service2")

        # Context 1
        with ContextualComponentManager.container_context():
            ContextualComponentManager.set_component(MockService, service1)
            retrieved1 = ContextualComponentManager.get_component(MockService)
            assert retrieved1 is service1
            assert retrieved1.name == "service1"

            # Context 2 (nested)
            with ContextualComponentManager.container_context():
                ContextualComponentManager.set_component(MockService, service2)
                retrieved2 = ContextualComponentManager.get_component(MockService)
                assert retrieved2 is service2
                assert retrieved2.name == "service2"

                # Verify isolation - different from context 1
                assert retrieved2 is not retrieved1

            # Back to context 1 - should still have original
            retrieved1_again = ContextualComponentManager.get_component(MockService)
            assert retrieved1_again is service1
            assert retrieved1_again.name == "service1"

        # Outside all contexts - should be None
        retrieved_outside = ContextualComponentManager.get_component(MockService)
        assert retrieved_outside is None

    def test_sequential_context_isolation(self):
        """Test isolation between sequential contexts."""
        service1 = MockService("service1")
        service2 = MockService("service2")

        # First context
        with ContextualComponentManager.container_context():
            ContextualComponentManager.set_component(MockService, service1)
            assert ContextualComponentManager.get_component(MockService) is service1

        # Second context (sequential, not nested)
        with ContextualComponentManager.container_context():
            # Should be empty in new context
            assert ContextualComponentManager.get_component(MockService) is None

            # Add different service
            ContextualComponentManager.set_component(MockService, service2)
            assert ContextualComponentManager.get_component(MockService) is service2

        # Outside both contexts
        assert ContextualComponentManager.get_component(MockService) is None

    def test_context_cleanup(self):
        """Test automatic cleanup when exiting context."""
        service = MockService()

        # Verify no components outside context
        assert ContextualComponentManager.get_component_count() == 0

        with ContextualComponentManager.container_context():
            ContextualComponentManager.set_component(MockService, service)
            assert ContextualComponentManager.get_component_count() == 1

        # After exiting context, should be cleaned up
        assert ContextualComponentManager.get_component_count() == 0
        assert ContextualComponentManager.get_component(MockService) is None

    def test_exception_during_context(self):
        """Test cleanup happens even when exception occurs."""
        service = MockService()

        try:
            with ContextualComponentManager.container_context():
                ContextualComponentManager.set_component(MockService, service)
                assert ContextualComponentManager.get_component_count() == 1
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Should still be cleaned up after exception
        assert ContextualComponentManager.get_component_count() == 0
        assert ContextualComponentManager.get_component(MockService) is None


class TestContextualComponentManagerThreadSafety:
    """Test thread safety of ContextualComponentManager."""

    def test_thread_context_isolation(self):
        """Test that different threads have isolated contexts."""
        results = {}
        barrier = threading.Barrier(2)

        def thread_worker(thread_id: int) -> None:
            """Worker function for thread testing."""
            with ContextualComponentManager.container_context():
                service = MockService(f"service_{thread_id}")
                ContextualComponentManager.set_component(MockService, service)

                # Wait for both threads to set their components
                barrier.wait()

                # Verify each thread sees only its own component
                retrieved = ContextualComponentManager.get_component(MockService)
                results[thread_id] = retrieved.name if retrieved else None

        # Start threads
        thread1 = threading.Thread(target=thread_worker, args=(1,))
        thread2 = threading.Thread(target=thread_worker, args=(2,))

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        # Verify each thread saw its own component
        assert results[1] == "service_1"
        assert results[2] == "service_2"

    def test_concurrent_access_different_contexts(self):
        """Test concurrent access with different contexts."""
        num_threads = 10
        results = {}

        def worker(thread_id: int) -> None:
            """Worker that creates isolated context."""
            with ContextualComponentManager.container_context():
                service = MockService(f"service_{thread_id}")
                ContextualComponentManager.set_component(MockService, service)

                # Small delay to increase chance of concurrent access
                time.sleep(0.01)

                retrieved = ContextualComponentManager.get_component(MockService)
                results[thread_id] = retrieved.name if retrieved else None

        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Each thread should have seen its own service
        for i in range(num_threads):
            assert results[i] == f"service_{i}"

    def test_thread_pool_isolation(self):
        """Test context isolation with thread pool."""

        def isolated_work(thread_id: int) -> str:
            """Work function with isolated context."""
            with ContextualComponentManager.container_context():
                service = MockService(f"pooled_{thread_id}")
                ContextualComponentManager.set_component(MockService, service)

                retrieved = ContextualComponentManager.get_component(MockService)
                return retrieved.name if retrieved else "None"

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(isolated_work, i) for i in range(10)]
            results = [future.result() for future in futures]

        # Each task should have seen its own service
        expected = [f"pooled_{i}" for i in range(10)]
        assert results == expected


class TestContextualComponentManagerAsyncSupport:
    """Test async/await support for ContextualComponentManager."""

    @pytest.mark.asyncio
    async def test_async_context_preservation(self):
        """Test that context is preserved across await boundaries."""
        service = MockService("async_service")

        with ContextualComponentManager.container_context():
            ContextualComponentManager.set_component(MockService, service)

            # Verify component before await
            retrieved1 = ContextualComponentManager.get_component(MockService)
            assert retrieved1 is service

            # Await some async operation
            await asyncio.sleep(0.01)

            # Verify component still available after await
            retrieved2 = ContextualComponentManager.get_component(MockService)
            assert retrieved2 is service
            assert retrieved2 is retrieved1

    @pytest.mark.asyncio
    async def test_async_task_isolation(self):
        """Test that different async tasks have isolated contexts."""
        results = {}

        async def async_worker(task_id: int) -> None:
            """Async worker with isolated context."""
            with ContextualComponentManager.container_context():
                service = MockService(f"async_service_{task_id}")
                ContextualComponentManager.set_component(MockService, service)

                # Await to allow other tasks to run
                await asyncio.sleep(0.01)

                retrieved = ContextualComponentManager.get_component(MockService)
                results[task_id] = retrieved.name if retrieved else None

        # Run multiple async tasks concurrently
        tasks = [async_worker(i) for i in range(5)]
        await asyncio.gather(*tasks)

        # Each task should have seen its own service
        for i in range(5):
            assert results[i] == f"async_service_{i}"

    @pytest.mark.asyncio
    async def test_nested_async_contexts(self):
        """Test nested contexts in async environment."""
        service1 = MockService("outer_async")
        service2 = MockService("inner_async")

        with ContextualComponentManager.container_context():
            ContextualComponentManager.set_component(MockService, service1)

            retrieved1 = ContextualComponentManager.get_component(MockService)
            assert retrieved1.name == "outer_async"

            with ContextualComponentManager.container_context():
                ContextualComponentManager.set_component(MockService, service2)

                await asyncio.sleep(0.01)

                retrieved2 = ContextualComponentManager.get_component(MockService)
                assert retrieved2.name == "inner_async"

            # Back to outer context
            retrieved3 = ContextualComponentManager.get_component(MockService)
            assert retrieved3.name == "outer_async"


class TestContextualComponentManagerEdgeCases:
    """Test edge cases and error conditions."""

    def test_component_replacement(self):
        """Test replacing an existing component."""
        with ContextualComponentManager.container_context():
            service1 = MockService("first")
            service2 = MockService("second")

            # Set initial component
            ContextualComponentManager.set_component(MockService, service1)
            assert ContextualComponentManager.get_component(MockService).name == "first"

            # Replace with new component
            ContextualComponentManager.set_component(MockService, service2)
            assert (
                ContextualComponentManager.get_component(MockService).name == "second"
            )

            # Should still only have one component
            assert ContextualComponentManager.get_component_count() == 1

    def test_multiple_component_types(self):
        """Test managing multiple different component types."""
        with ContextualComponentManager.container_context():
            service1 = MockService("service")
            service2 = AnotherService(100)

            # Set different component types
            ContextualComponentManager.set_component(MockService, service1)
            ContextualComponentManager.set_component(AnotherService, service2)

            # Verify both exist and are correct
            retrieved1 = ContextualComponentManager.get_component(MockService)
            retrieved2 = ContextualComponentManager.get_component(AnotherService)

            assert retrieved1.name == "service"
            assert retrieved2.value == 100
            assert ContextualComponentManager.get_component_count() == 2

    def test_none_values_handling(self):
        """Test edge cases with None values."""
        # Test getting None component type
        with ContextualComponentManager.container_context():
            # This should not crash but might not be meaningful
            result = ContextualComponentManager.has_component(None)
            assert isinstance(result, bool)  # Should return a boolean

    def test_component_context_reentry(self):
        """Test re-entering the same context multiple times."""
        service1 = MockService("first")
        service2 = MockService("second")

        with ContextualComponentManager.container_context():
            ContextualComponentManager.set_component(MockService, service1)

            with ContextualComponentManager.container_context():
                ContextualComponentManager.set_component(MockService, service2)
                assert (
                    ContextualComponentManager.get_component(MockService).name
                    == "second"
                )

            # Should revert to outer context
            assert ContextualComponentManager.get_component(MockService).name == "first"


class TestContextualComponentManagerIntegration:
    """Integration tests demonstrating real-world usage patterns."""

    def test_fastapi_request_simulation(self):
        """Simulate FastAPI request processing with component isolation."""

        def simulate_request_handler(request_id: str) -> Dict[str, Any]:
            """Simulate FastAPI request handler."""
            with ContextualComponentManager.container_context():
                # Set up request-specific services
                service = MockService(f"request_{request_id}")
                calculator = AnotherService(int(request_id) * 10)

                ContextualComponentManager.set_component(MockService, service)
                ContextualComponentManager.set_component(AnotherService, calculator)

                # Process request using components
                result = service.process()
                calculation = calculator.calculate()

                return {
                    "service_result": result,
                    "calculation": calculation,
                    "request_id": request_id,
                }

        # Simulate multiple concurrent requests
        results = []
        for i in range(3):
            result = simulate_request_handler(str(i + 1))
            results.append(result)

        # Verify each request was processed independently
        assert len(results) == 3
        assert results[0]["service_result"] == "Processed by request_1 (count: 1)"
        assert results[1]["service_result"] == "Processed by request_2 (count: 1)"
        assert results[2]["service_result"] == "Processed by request_3 (count: 1)"

        assert results[0]["calculation"] == 20  # (1 * 10) * 2
        assert results[1]["calculation"] == 40  # (2 * 10) * 2
        assert results[2]["calculation"] == 60  # (3 * 10) * 2

    @pytest.mark.asyncio
    async def test_async_request_processing(self):
        """Test async request processing with component isolation."""

        async def async_request_handler(request_id: str) -> Any:
            """Async request handler."""
            with ContextualComponentManager.container_context():
                service = MockService(f"async_req_{request_id}")
                ContextualComponentManager.set_component(MockService, service)

                # Simulate async processing
                await asyncio.sleep(0.01)

                retrieved = ContextualComponentManager.get_component(MockService)
                return retrieved.process()

        # Process multiple async requests concurrently
        tasks = [async_request_handler(str(i)) for i in range(3)]
        results = await asyncio.gather(*tasks)

        # Each should be processed independently
        expected = [
            "Processed by async_req_0 (count: 1)",
            "Processed by async_req_1 (count: 1)",
            "Processed by async_req_2 (count: 1)",
        ]
        assert results == expected

    def test_cleanup_verification(self):
        """Verify complete cleanup after context exit."""
        initial_count = ContextualComponentManager.get_component_count()

        with ContextualComponentManager.container_context():
            # Add multiple components
            ContextualComponentManager.set_component(
                MockService, MockService("cleanup_test")
            )
            ContextualComponentManager.set_component(
                AnotherService, AnotherService(999)
            )

            assert ContextualComponentManager.get_component_count() == 2

        # Verify complete cleanup
        final_count = ContextualComponentManager.get_component_count()
        assert final_count == initial_count
        assert ContextualComponentManager.get_component(MockService) is None
        assert ContextualComponentManager.get_component(AnotherService) is None
