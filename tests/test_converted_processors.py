"""Tests for converted processors and processor registry."""

import re

import pytest

from fapilog._internal.processor_registry import ProcessorRegistry, register_processor
from fapilog._internal.processors import (
    FilterNoneProcessor,
    RedactionProcessor,
    SamplingProcessor,
)


class TestConvertedProcessors:
    """Test that converted processors produce identical output to old function processors."""

    def test_redaction_processor_identical_behavior(self):
        """Test RedactionProcessor produces identical output to old _redact_processor."""
        # Test data
        patterns = ["password", "secret"]
        redact_level = "INFO"
        event_dict = {
            "level": "INFO",
            "user": "john",
            "password": "secret123",
            "token": "abc123",
            "message": "contains secret info",
        }

        # Create processor and manually compile patterns for testing
        processor = RedactionProcessor(patterns=patterns, redact_level=redact_level)
        processor.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in patterns
        ]

        result = processor.process(None, "info", event_dict)

        # Verify behavior matches expected output
        assert result["user"] == "john"  # Should not be redacted
        assert result["password"] == "[REDACTED]"  # Should be redacted
        assert result["token"] == "abc123"  # No pattern match
        assert result["message"] == "[REDACTED]"  # Contains "secret"
        assert result["level"] == "INFO"  # Level preserved

    def test_redaction_processor_level_filtering(self):
        """Test redaction processor respects log level filtering."""
        processor = RedactionProcessor(patterns=["secret"], redact_level="ERROR")
        processor.compiled_patterns = [re.compile("secret", re.IGNORECASE)]

        # INFO level should not be redacted (below ERROR threshold)
        event_dict = {"level": "INFO", "secret_key": "value"}
        result = processor.process(None, "info", event_dict)
        assert result["secret_key"] == "value"  # Should not be redacted

        # ERROR level should be redacted
        event_dict = {"level": "ERROR", "secret_key": "value"}
        result = processor.process(None, "error", event_dict)
        assert result["secret_key"] == "[REDACTED]"

    def test_sampling_processor_identical_behavior(self):
        """Test SamplingProcessor produces identical output to old _sampling_processor."""
        # Test full rate (1.0) - should pass everything through
        processor = SamplingProcessor(rate=1.0)
        event_dict = {"level": "INFO", "message": "test"}

        result = processor.process(None, "info", event_dict)
        assert result == event_dict  # Should be unchanged

        # Test zero rate (0.0) - should drop everything
        processor = SamplingProcessor(rate=0.0)
        result = processor.process(None, "info", event_dict)
        assert result is None  # Should be dropped

        # Test partial rate - statistically verify (with deterministic seed for testing)
        import random

        random.seed(42)  # Make test deterministic

        processor = SamplingProcessor(rate=0.5)
        passed_count = 0
        total_count = 100

        for _ in range(total_count):
            result = processor.process(None, "info", event_dict)
            if result is not None:
                passed_count += 1

        # Should be approximately 50% (allowing for statistical variance)
        assert 35 <= passed_count <= 65  # 35-65% range for variance

    def test_filter_none_processor_identical_behavior(self):
        """Test FilterNoneProcessor produces identical output to old _filter_none_processor."""
        processor = FilterNoneProcessor()

        # Test with None - should be filtered out
        result = processor.process(None, "info", None)
        assert result is None

        # Test with valid dict - should pass through unchanged
        event_dict = {"level": "INFO", "message": "test"}
        result = processor.process(None, "info", event_dict)
        assert result == event_dict

        # Test with empty dict - should pass through
        result = processor.process(None, "info", {})
        assert result == {}

    def test_processor_configuration_validation(self):
        """Test that all processors validate their configuration correctly."""
        # RedactionProcessor validation
        RedactionProcessor(patterns=["test"], redact_level="INFO")  # Should work

        with pytest.raises(ValueError, match="patterns must be a list"):
            RedactionProcessor(patterns="not_a_list")

        with pytest.raises(ValueError, match="All patterns must be strings"):
            RedactionProcessor(patterns=["valid", 123])

        with pytest.raises(ValueError, match="Invalid regex pattern"):
            RedactionProcessor(patterns=["[invalid"])

        with pytest.raises(ValueError, match="redact_level must be a string"):
            RedactionProcessor(patterns=[], redact_level=123)

        # SamplingProcessor validation
        SamplingProcessor(rate=0.5)  # Should work

        with pytest.raises(ValueError, match="rate must be a number"):
            SamplingProcessor(rate="not_a_number")

        with pytest.raises(ValueError, match="rate must be between 0.0 and 1.0"):
            SamplingProcessor(rate=-0.1)

        with pytest.raises(ValueError, match="rate must be between 0.0 and 1.0"):
            SamplingProcessor(rate=1.5)

        # FilterNoneProcessor - no validation, should always work
        FilterNoneProcessor()


class TestProcessorRegistry:
    """Test the ProcessorRegistry system."""

    def setup_method(self, method):
        """Clear registry before each test except for built-in processor test."""
        # Don't clear for the built-in processors test since we need them registered
        if method.__name__ != "test_built_in_processors_registered":
            ProcessorRegistry.clear()

    def teardown_method(self):
        """Clear registry after each test."""
        ProcessorRegistry.clear()

    def test_processor_registration(self):
        """Test basic processor registration and retrieval."""
        # Register a processor
        ProcessorRegistry.register("test_redaction", RedactionProcessor)

        # Retrieve it
        retrieved_class = ProcessorRegistry.get("test_redaction")
        assert retrieved_class is RedactionProcessor

        # Test non-existent processor
        assert ProcessorRegistry.get("non_existent") is None

    def test_processor_registry_decorator(self):
        """Test @register_processor decorator."""

        @register_processor("custom_filter")
        class CustomFilterProcessor(FilterNoneProcessor):
            """Custom processor for testing."""

            pass

        # Verify it was registered
        retrieved_class = ProcessorRegistry.get("custom_filter")
        assert retrieved_class is CustomFilterProcessor

    def test_processor_registry_listing(self):
        """Test listing all registered processors."""
        # Should be empty initially (after clear in setup)
        assert ProcessorRegistry.list() == {}

        # Register some processors
        ProcessorRegistry.register("redaction", RedactionProcessor)
        ProcessorRegistry.register("sampling", SamplingProcessor)

        # Get the list
        processors = ProcessorRegistry.list()
        assert len(processors) == 2
        assert processors["redaction"] is RedactionProcessor
        assert processors["sampling"] is SamplingProcessor

    def test_processor_registry_clear(self):
        """Test clearing the processor registry."""
        # Register some processors
        ProcessorRegistry.register("redaction", RedactionProcessor)
        ProcessorRegistry.register("sampling", SamplingProcessor)

        # Verify they're there
        assert len(ProcessorRegistry.list()) == 2

        # Clear the registry
        ProcessorRegistry.clear()

        # Verify it's empty
        assert ProcessorRegistry.list() == {}

    def test_processor_registry_validation(self):
        """Test processor registry validation."""
        # Empty name should fail
        with pytest.raises(ValueError, match="Processor name cannot be empty"):
            ProcessorRegistry.register("", RedactionProcessor)

        with pytest.raises(ValueError, match="Processor name cannot be empty"):
            ProcessorRegistry.register("   ", RedactionProcessor)

        # Non-Processor class should fail
        class NotAProcessor:
            pass

        with pytest.raises(ValueError, match="must inherit from Processor"):
            ProcessorRegistry.register("bad_processor", NotAProcessor)

    def test_built_in_processors_registered(self):
        """Test that built-in processors are automatically registered."""
        # Re-import to ensure registration
        import importlib

        from fapilog._internal import processors

        importlib.reload(processors)

        # Use class name comparison since reload creates new class objects
        redaction_class = ProcessorRegistry.get("redaction")
        sampling_class = ProcessorRegistry.get("sampling")
        filter_class = ProcessorRegistry.get("filter_none")

        assert redaction_class is not None
        assert redaction_class.__name__ == "RedactionProcessor"
        assert sampling_class is not None
        assert sampling_class.__name__ == "SamplingProcessor"
        assert filter_class is not None
        assert filter_class.__name__ == "FilterNoneProcessor"

    def test_processor_registry_name_trimming(self):
        """Test that processor names are trimmed of whitespace."""
        ProcessorRegistry.register("  test_processor  ", RedactionProcessor)

        # Should be retrievable with trimmed name
        assert ProcessorRegistry.get("test_processor") is RedactionProcessor
        assert ProcessorRegistry.get("  test_processor  ") is RedactionProcessor

        # Verify it's stored with trimmed name
        processors = ProcessorRegistry.list()
        assert "test_processor" in processors
        assert "  test_processor  " not in processors


class TestProcessorIntegration:
    """Test processor integration with the pipeline."""

    def test_processors_work_in_pipeline_context(self):
        """Test that converted processors work correctly in pipeline context."""
        # This is a simplified test to ensure processors work when called
        # as they would be in the actual pipeline

        # Create test processors
        redaction_processor = RedactionProcessor(patterns=["password"])
        sampling_processor = SamplingProcessor(rate=1.0)
        filter_processor = FilterNoneProcessor()

        # Simulate pipeline processing
        event_dict = {"level": "INFO", "password": "secret123", "user": "john"}

        # Process through redaction
        result = redaction_processor.process(None, "info", event_dict)
        redaction_processor.compiled_patterns = [re.compile("password", re.IGNORECASE)]
        result = redaction_processor.process(None, "info", event_dict)
        assert result["password"] == "[REDACTED]"
        assert result["user"] == "john"

        # Process through sampling (should pass through at rate 1.0)
        result = sampling_processor.process(None, "info", result)
        assert result is not None
        assert result["password"] == "[REDACTED]"

        # Process through filter (should pass through non-None)
        result = filter_processor.process(None, "info", result)
        assert result is not None
        assert result["password"] == "[REDACTED]"

        # Test filter with None input
        result = filter_processor.process(None, "info", None)
        assert result is None
