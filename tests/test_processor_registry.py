"""Tests for processor registry functionality."""

import threading
from typing import Any, Dict, Optional, Type

import pytest

from fapilog.core.registries.processor_registry import (
    ProcessorRegistry,
    register_processor,
)
from fapilog.processors.base import Processor


# Test processor implementations
class MockProcessor(Processor):
    """Simple mock processor for registry testing."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.kwargs = kwargs

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Mock process implementation."""
        return event_dict


class CustomValidationProcessor(Processor):
    """Mock validation processor for testing."""

    def __init__(self, strict_mode=False, required_fields=None, **kwargs):
        super().__init__(**kwargs)
        self.strict_mode = strict_mode
        self.required_fields = required_fields or []

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Mock validation process implementation."""
        if self.strict_mode:
            for field in self.required_fields:
                if field not in event_dict:
                    return None  # Drop invalid events
        return event_dict


class TestProcessorRegistry:
    """Test the ProcessorRegistry class."""

    def setup_method(self):
        """Clear registry before each test."""
        ProcessorRegistry.clear()

    def test_register_processor(self):
        """Test basic processor registration."""
        result = ProcessorRegistry.register("test", MockProcessor)
        assert result is MockProcessor
        assert ProcessorRegistry.get("test") is MockProcessor

    def test_register_processor_with_whitespace(self):
        """Test registration handles whitespace in names."""
        ProcessorRegistry.register("  test  ", MockProcessor)
        assert ProcessorRegistry.get("test") is MockProcessor
        assert ProcessorRegistry.get("  test  ") is MockProcessor

    def test_register_invalid_name(self):
        """Test registration with invalid names."""
        with pytest.raises(ValueError, match="Processor name cannot be empty"):
            ProcessorRegistry.register("", MockProcessor)

        with pytest.raises(ValueError, match="Processor name cannot be empty"):
            ProcessorRegistry.register("   ", MockProcessor)

    def test_register_invalid_class(self):
        """Test registration with invalid processor class."""

        class NotAProcessor:
            pass

        with pytest.raises(ValueError, match="must inherit from Processor"):
            ProcessorRegistry.register("test", NotAProcessor)

    def test_register_with_non_class(self):
        """Test registration with non-class objects."""
        with pytest.raises(TypeError):
            ProcessorRegistry.register("test", "not_a_class")

        with pytest.raises(TypeError):
            ProcessorRegistry.register("test", 123)

    def test_get_nonexistent_processor(self):
        """Test getting non-existent processor returns None."""
        assert ProcessorRegistry.get("nonexistent") is None
        assert ProcessorRegistry.get("") is None
        assert ProcessorRegistry.get(None) is None

    def test_list_processors(self):
        """Test listing registered processors."""
        ProcessorRegistry.register("test1", MockProcessor)
        ProcessorRegistry.register("test2", CustomValidationProcessor)

        processors = ProcessorRegistry.list()
        assert len(processors) == 2
        assert processors["test1"] is MockProcessor
        assert processors["test2"] is CustomValidationProcessor

        # Verify it returns a copy
        processors["test3"] = MockProcessor
        assert "test3" not in ProcessorRegistry.list()

    def test_clear_registry(self):
        """Test clearing the registry."""
        ProcessorRegistry.register("test", MockProcessor)
        assert len(ProcessorRegistry.list()) == 1

        ProcessorRegistry.clear()
        assert len(ProcessorRegistry.list()) == 0

    def test_duplicate_registration(self):
        """Test that duplicate registration overwrites."""
        ProcessorRegistry.register("test", MockProcessor)
        ProcessorRegistry.register("test", CustomValidationProcessor)

        assert ProcessorRegistry.get("test") is CustomValidationProcessor
        assert len(ProcessorRegistry.list()) == 1

    def test_case_sensitive_registration(self):
        """Test that registration is case sensitive."""
        ProcessorRegistry.register("test", MockProcessor)
        ProcessorRegistry.register("Test", CustomValidationProcessor)

        assert ProcessorRegistry.get("test") is MockProcessor
        assert ProcessorRegistry.get("Test") is CustomValidationProcessor
        assert len(ProcessorRegistry.list()) == 2


class TestRegisterProcessorDecorator:
    """Test the @register_processor decorator."""

    def setup_method(self):
        """Clear registry before each test."""
        ProcessorRegistry.clear()

    def test_decorator_registration(self):
        """Test decorator registers processor correctly."""

        @register_processor("validation")
        class DecoratedProcessor(Processor):
            def process(
                self, logger: Any, method_name: str, event_dict: Dict[str, Any]
            ) -> Optional[Dict[str, Any]]:
                return event_dict

        assert ProcessorRegistry.get("validation") is DecoratedProcessor

    def test_decorator_returns_class(self):
        """Test decorator returns the original class."""

        @register_processor("test")
        class DecoratedProcessor(Processor):
            def process(
                self, logger: Any, method_name: str, event_dict: Dict[str, Any]
            ) -> Optional[Dict[str, Any]]:
                return event_dict

        # Should be able to instantiate normally
        instance = DecoratedProcessor()
        assert isinstance(instance, Processor)

    def test_decorator_with_invalid_name(self):
        """Test decorator with invalid names."""
        with pytest.raises(ValueError, match="Processor name cannot be empty"):

            @register_processor("")
            class InvalidNameProcessor(Processor):
                def process(
                    self, logger: Any, method_name: str, event_dict: Dict[str, Any]
                ) -> Optional[Dict[str, Any]]:
                    return event_dict

    def test_decorator_with_invalid_class(self):
        """Test decorator with non-processor class."""
        with pytest.raises(ValueError, match="must inherit from Processor"):

            @register_processor("test")
            class NotAProcessor:
                pass


class TestProcessorRegistryThreadSafety:
    """Test thread safety of processor registry operations."""

    def setup_method(self):
        """Clear registry before each test."""
        ProcessorRegistry.clear()

    def test_concurrent_registration(self):
        """Test concurrent processor registration."""
        results = {}
        errors = []

        def register_processor_thread(
            name: str, processor_class: Type[Processor]
        ) -> None:
            try:
                result = ProcessorRegistry.register(name, processor_class)
                results[name] = result
            except Exception as e:
                errors.append(e)

        # Create multiple threads registering different processors
        threads = []
        for i in range(10):
            thread = threading.Thread(
                target=register_processor_thread, args=(f"processor_{i}", MockProcessor)
            )
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify results
        assert len(errors) == 0
        assert len(results) == 10
        assert len(ProcessorRegistry.list()) == 10

        for i in range(10):
            assert ProcessorRegistry.get(f"processor_{i}") is MockProcessor

    def test_concurrent_access_operations(self):
        """Test concurrent get/list operations."""
        # Pre-register some processors
        ProcessorRegistry.register("proc1", MockProcessor)
        ProcessorRegistry.register("proc2", CustomValidationProcessor)

        results = []
        errors = []

        def access_registry():
            try:
                # Mix of different operations
                proc1 = ProcessorRegistry.get("proc1")
                proc_list = ProcessorRegistry.list()
                proc2 = ProcessorRegistry.get("proc2")
                nonexistent = ProcessorRegistry.get("nonexistent")

                results.append(
                    {
                        "proc1": proc1,
                        "list_size": len(proc_list),
                        "proc2": proc2,
                        "nonexistent": nonexistent,
                    }
                )
            except Exception as e:
                errors.append(e)

        # Create multiple threads accessing registry
        threads = []
        for _ in range(20):
            thread = threading.Thread(target=access_registry)
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify results
        assert len(errors) == 0
        assert len(results) == 20

        for result in results:
            assert result["proc1"] is MockProcessor
            assert result["list_size"] == 2
            assert result["proc2"] is CustomValidationProcessor
            assert result["nonexistent"] is None


class TestProcessorRegistryIntegration:
    """Test processor registry integration scenarios."""

    def setup_method(self):
        """Clear registry before each test."""
        ProcessorRegistry.clear()

    def test_processor_instantiation(self):
        """Test that registered processors can be instantiated."""
        ProcessorRegistry.register("mock", MockProcessor)
        ProcessorRegistry.register("validator", CustomValidationProcessor)

        # Get and instantiate processors
        mock_class = ProcessorRegistry.get("mock")
        validator_class = ProcessorRegistry.get("validator")

        mock_instance = mock_class()
        validator_instance = validator_class(
            strict_mode=True, required_fields=["user_id"]
        )

        assert isinstance(mock_instance, MockProcessor)
        assert isinstance(validator_instance, CustomValidationProcessor)
        assert validator_instance.strict_mode is True
        assert validator_instance.required_fields == ["user_id"]

    def test_processor_functionality(self):
        """Test that registered processors work correctly."""
        ProcessorRegistry.register("validator", CustomValidationProcessor)

        validator_class = ProcessorRegistry.get("validator")
        validator = validator_class(strict_mode=True, required_fields=["user_id"])

        # Test valid event
        valid_event = {"user_id": "123", "message": "test"}
        result = validator.process(None, "info", valid_event)
        assert result == valid_event

        # Test invalid event (missing required field)
        invalid_event = {"message": "test"}
        result = validator.process(None, "info", invalid_event)
        assert result is None

    def test_registry_persistence(self):
        """Test that registry persists across operations."""
        # Register processors
        ProcessorRegistry.register("proc1", MockProcessor)
        ProcessorRegistry.register("proc2", CustomValidationProcessor)

        # Perform various operations
        proc1 = ProcessorRegistry.get("proc1")
        proc_list = ProcessorRegistry.list()

        # Registry should still have both processors
        assert len(proc_list) == 2
        assert proc1 is MockProcessor
        assert ProcessorRegistry.get("proc2") is CustomValidationProcessor

    def test_clear_isolation(self):
        """Test that clear() properly isolates test runs."""
        # Register a processor
        ProcessorRegistry.register("test", MockProcessor)
        assert len(ProcessorRegistry.list()) == 1

        # Clear registry
        ProcessorRegistry.clear()
        assert len(ProcessorRegistry.list()) == 0
        assert ProcessorRegistry.get("test") is None

        # Register different processor with same name
        ProcessorRegistry.register("test", CustomValidationProcessor)
        assert ProcessorRegistry.get("test") is CustomValidationProcessor
        assert len(ProcessorRegistry.list()) == 1
