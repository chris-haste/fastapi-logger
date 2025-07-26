"""Tests for processor base class and implementations."""

from typing import Any, Dict

import pytest

from fapilog._internal.processor import Processor
from fapilog._internal.processors import (
    FilterNoneProcessor,
    RedactionProcessor,
    SamplingProcessor,
)


class ConcreteProcessor(Processor):
    """Concrete processor implementation for testing."""

    def __init__(self, test_value: str = "test", **config: Any) -> None:
        self.test_value = test_value
        self.start_called = False
        self.stop_called = False
        super().__init__(test_value=test_value, **config)

    async def _start_impl(self) -> None:
        self.start_called = True

    async def _stop_impl(self) -> None:
        self.stop_called = True

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        event_dict["processed_by"] = self.test_value
        return event_dict

    def validate_config(self) -> None:
        if not isinstance(self.test_value, str):
            raise ValueError("test_value must be a string")


class FailingProcessor(Processor):
    """Processor that fails validation for testing."""

    def __init__(self, **config: Any) -> None:
        super().__init__(**config)

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        return event_dict

    def validate_config(self) -> None:
        raise ValueError("This processor always fails validation")


class TestProcessorBase:
    """Test the Processor base class."""

    @pytest.mark.asyncio
    async def test_processor_lifecycle(self):
        """Test processor start/stop lifecycle."""
        processor = ConcreteProcessor("lifecycle_test")

        # Initially not started
        assert not processor.is_started
        assert not processor.start_called
        assert not processor.stop_called

        # Start processor
        await processor.start()
        assert processor.is_started
        assert processor.start_called
        assert not processor.stop_called

        # Starting again should be idempotent
        processor.start_called = False
        await processor.start()
        assert processor.is_started
        assert not processor.start_called  # Should not be called again

        # Stop processor
        await processor.stop()
        assert not processor.is_started
        assert processor.stop_called

        # Stopping again should be idempotent
        processor.stop_called = False
        await processor.stop()
        assert not processor.is_started
        assert not processor.stop_called  # Should not be called again

    def test_processor_config_validation(self):
        """Test processor configuration validation."""
        # Valid config should work
        processor = ConcreteProcessor("valid")
        assert processor.test_value == "valid"

        # Invalid config should raise error
        with pytest.raises(ValueError, match="test_value must be a string"):
            ConcreteProcessor(test_value=123)

    def test_processor_validation_failure(self):
        """Test processor validation failure."""
        with pytest.raises(ValueError, match="This processor always fails validation"):
            FailingProcessor()

    def test_processor_config_storage(self):
        """Test that processor config is stored correctly."""
        processor = ConcreteProcessor(test_value="config_test", extra_param="extra")
        assert processor.config["test_value"] == "config_test"
        assert processor.config["extra_param"] == "extra"

    def test_processor_abstract_methods(self):
        """Test that abstract methods must be implemented."""
        with pytest.raises(TypeError):
            # Should fail because process method is not implemented
            Processor()  # type: ignore

    def test_processor_process_method(self):
        """Test processor process method."""
        processor = ConcreteProcessor("process_test")
        event_dict = {"level": "INFO", "message": "test"}

        result = processor.process(None, "info", event_dict)
        assert result["level"] == "INFO"
        assert result["message"] == "test"
        assert result["processed_by"] == "process_test"


class TestRedactionProcessor:
    """Test the RedactionProcessor implementation."""

    def test_redaction_processor_initialization(self):
        """Test redaction processor initialization."""
        processor = RedactionProcessor(
            patterns=["password", "secret"], redact_level="DEBUG"
        )
        assert processor.patterns == ["password", "secret"]
        assert processor.redact_level == "DEBUG"

    def test_redaction_processor_validation(self):
        """Test redaction processor configuration validation."""
        # Valid configuration
        processor = RedactionProcessor(patterns=["test"], redact_level="INFO")
        assert processor.patterns == ["test"]

        # Invalid patterns type
        with pytest.raises(ValueError, match="patterns must be a list of strings"):
            RedactionProcessor(patterns="not_a_list")

        # Invalid pattern in list
        with pytest.raises(ValueError, match="All patterns must be strings"):
            RedactionProcessor(patterns=["valid", 123])

        # Invalid regex pattern
        with pytest.raises(ValueError, match="Invalid regex pattern"):
            RedactionProcessor(patterns=["[invalid"])

        # Invalid redact_level type
        with pytest.raises(ValueError, match="redact_level must be a string"):
            RedactionProcessor(patterns=[], redact_level=123)

    @pytest.mark.asyncio
    async def test_redaction_processor_pattern_compilation(self):
        """Test that patterns are compiled on start."""
        processor = RedactionProcessor(patterns=["test", "password"])
        assert processor.compiled_patterns == []

        await processor.start()
        assert len(processor.compiled_patterns) == 2
        assert all(hasattr(p, "pattern") for p in processor.compiled_patterns)

    def test_redaction_processor_simple_redaction(self):
        """Test basic redaction functionality."""
        processor = RedactionProcessor(patterns=["password"])
        processor.compiled_patterns = [processor.patterns[0]]  # Mock compilation

        # Redact matching value
        event_dict = {"level": "INFO", "user_password": "secret123"}
        # Mock the compiled pattern for testing
        import re

        processor.compiled_patterns = [re.compile("password", re.IGNORECASE)]

        result = processor.process(None, "info", event_dict)
        assert result["user_password"] == "[REDACTED]"
        assert result["level"] == "INFO"

    def test_redaction_processor_no_patterns(self):
        """Test redaction processor with no patterns."""
        processor = RedactionProcessor(patterns=[])
        event_dict = {"level": "INFO", "password": "secret"}

        result = processor.process(None, "info", event_dict)
        assert result == event_dict  # Should be unchanged

    def test_redaction_processor_level_filtering(self):
        """Test that redaction respects log level filtering."""
        processor = RedactionProcessor(patterns=["secret"], redact_level="ERROR")
        import re

        processor.compiled_patterns = [re.compile("secret", re.IGNORECASE)]

        # INFO level should not be redacted (below ERROR threshold)
        event_dict = {"level": "INFO", "secret_key": "value"}
        result = processor.process(None, "info", event_dict)
        assert result["secret_key"] == "value"  # Should not be redacted

        # ERROR level should be redacted
        event_dict = {"level": "ERROR", "secret_key": "value"}
        result = processor.process(None, "error", event_dict)
        assert result["secret_key"] == "[REDACTED]"

    def test_redaction_processor_nested_structures(self):
        """Test redaction of nested dictionary structures."""
        processor = RedactionProcessor(patterns=["password"])
        import re

        processor.compiled_patterns = [re.compile("password", re.IGNORECASE)]

        event_dict = {
            "level": "INFO",
            "user": {"password": "secret", "name": "john"},
            "data": {"nested": {"password_field": "hidden"}},
        }

        result = processor.process(None, "info", event_dict)
        assert result["user"]["password"] == "[REDACTED]"
        assert result["user"]["name"] == "john"
        assert result["data"]["nested"]["password_field"] == "[REDACTED]"


class TestSamplingProcessor:
    """Test the SamplingProcessor implementation."""

    def test_sampling_processor_initialization(self):
        """Test sampling processor initialization."""
        processor = SamplingProcessor(rate=0.5)
        assert processor.rate == 0.5

    def test_sampling_processor_validation(self):
        """Test sampling processor configuration validation."""
        # Valid rates
        SamplingProcessor(rate=0.0)
        SamplingProcessor(rate=0.5)
        SamplingProcessor(rate=1.0)

        # Invalid rate type
        with pytest.raises(ValueError, match="rate must be a number"):
            SamplingProcessor(rate="invalid")

        # Invalid rate range
        with pytest.raises(ValueError, match="rate must be between 0.0 and 1.0"):
            SamplingProcessor(rate=-0.1)

        with pytest.raises(ValueError, match="rate must be between 0.0 and 1.0"):
            SamplingProcessor(rate=1.1)

    def test_sampling_processor_full_rate(self):
        """Test sampling with rate 1.0 (no dropping)."""
        processor = SamplingProcessor(rate=1.0)
        event_dict = {"level": "INFO", "message": "test"}

        # Should never drop events with rate 1.0
        for _ in range(10):
            result = processor.process(None, "info", event_dict)
            assert result == event_dict

    def test_sampling_processor_zero_rate(self):
        """Test sampling with rate 0.0 (drop all)."""
        processor = SamplingProcessor(rate=0.0)
        event_dict = {"level": "INFO", "message": "test"}

        # Should always drop events with rate 0.0
        for _ in range(10):
            result = processor.process(None, "info", event_dict)
            assert result is None

    def test_sampling_processor_partial_rate(self):
        """Test sampling with partial rate."""
        # Use a fixed seed for deterministic testing
        import random

        random.seed(42)

        processor = SamplingProcessor(rate=0.5)
        event_dict = {"level": "INFO", "message": "test"}

        # Test multiple events and check that some are dropped
        results = []
        for _ in range(100):
            result = processor.process(None, "info", event_dict)
            results.append(result)

        # With rate 0.5, we should have some None and some non-None results
        none_count = sum(1 for r in results if r is None)
        non_none_count = sum(1 for r in results if r is not None)

        assert none_count > 0, "Should drop some events"
        assert non_none_count > 0, "Should keep some events"


class TestFilterNoneProcessor:
    """Test the FilterNoneProcessor implementation."""

    def test_filter_none_processor_initialization(self):
        """Test filter none processor initialization."""
        processor = FilterNoneProcessor()
        assert processor.config == {}

    def test_filter_none_processor_none_event(self):
        """Test filtering None events."""
        processor = FilterNoneProcessor()

        result = processor.process(None, "info", None)
        assert result is None

    def test_filter_none_processor_valid_event(self):
        """Test passing through valid events."""
        processor = FilterNoneProcessor()
        event_dict = {"level": "INFO", "message": "test"}

        result = processor.process(None, "info", event_dict)
        assert result == event_dict

    def test_filter_none_processor_empty_dict(self):
        """Test that empty dict is not filtered."""
        processor = FilterNoneProcessor()
        event_dict = {}

        result = processor.process(None, "info", event_dict)
        assert result == event_dict


class TestProcessorIntegration:
    """Test processor integration scenarios."""

    @pytest.mark.asyncio
    async def test_processor_chain_lifecycle(self):
        """Test lifecycle management for a chain of processors."""
        processors = [
            ConcreteProcessor("proc1"),
            ConcreteProcessor("proc2"),
            ConcreteProcessor("proc3"),
        ]

        # Start all processors
        for processor in processors:
            await processor.start()

        assert all(p.is_started for p in processors)
        assert all(p.start_called for p in processors)

        # Stop all processors
        for processor in processors:
            await processor.stop()

        assert all(not p.is_started for p in processors)
        assert all(p.stop_called for p in processors)

    def test_processor_chain_processing(self):
        """Test processing through a chain of processors."""
        processors = [
            ConcreteProcessor("step1"),
            ConcreteProcessor("step2"),
            ConcreteProcessor("step3"),
        ]

        event_dict = {"level": "INFO", "message": "original"}

        # Process through chain
        result = event_dict
        for processor in processors:
            result = processor.process(None, "info", result)

        # Each processor should have added its mark
        assert result["processed_by"] == "step3"  # Last processor wins
        assert result["level"] == "INFO"
        assert result["message"] == "original"
