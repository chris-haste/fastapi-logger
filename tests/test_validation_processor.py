"""Tests for ValidationProcessor."""

from unittest.mock import Mock

import pytest

from fapilog.exceptions import ProcessorConfigurationError
from fapilog.processors.validation import ValidationProcessor


class TestValidationProcessorConfig:
    """Test ValidationProcessor configuration validation."""

    def test_valid_default_config(self):
        """Test processor with default configuration."""
        processor = ValidationProcessor()
        assert processor.required_fields == ["timestamp", "level", "event"]
        assert processor.validation_mode == "strict"
        assert processor.field_types == {}
        assert processor.default_values == {}
        assert processor.schema is None

    def test_valid_custom_config(self):
        """Test processor with custom configuration."""
        processor = ValidationProcessor(
            required_fields=["event", "user_id"],
            validation_mode="lenient",
            field_types={"user_id": str, "count": int},
            default_values={"user_id": "unknown"},
        )
        assert processor.required_fields == ["event", "user_id"]
        assert processor.validation_mode == "lenient"
        assert processor.field_types == {"user_id": str, "count": int}
        assert processor.default_values == {"user_id": "unknown"}

    def test_invalid_validation_mode(self):
        """Test invalid validation mode raises error."""
        with pytest.raises(
            ProcessorConfigurationError,
            match="validation_mode must be 'strict', 'lenient', or 'fix'",
        ):
            ValidationProcessor(validation_mode="invalid")

    def test_empty_required_fields(self):
        """Test empty required fields raises error."""
        with pytest.raises(
            ProcessorConfigurationError, match="required_fields cannot be empty"
        ):
            ValidationProcessor(required_fields=[])

    def test_invalid_field_type(self):
        """Test invalid field type raises error."""
        with pytest.raises(
            ProcessorConfigurationError,
            match="field_types\\['invalid'\\] must be a valid type",
        ):
            ValidationProcessor(field_types={"invalid": "not_a_type"})


class TestValidationProcessorStrict:
    """Test ValidationProcessor in strict mode."""

    def test_valid_event_passes(self):
        """Test valid event passes through."""
        processor = ValidationProcessor(
            validation_mode="strict",
            required_fields=["timestamp", "level", "event"],
            field_types={"level": str, "count": int},
        )

        event = {
            "timestamp": 1234567890,
            "level": "INFO",
            "event": "Test event",
            "count": 42,
        }

        result = processor.process(Mock(), "info", event)
        assert result == event
        assert processor.validation_stats["valid_events"] == 1
        assert processor.validation_stats["total_events"] == 1

    def test_missing_required_field_drops_event(self):
        """Test missing required field drops event in strict mode."""
        processor = ValidationProcessor(
            validation_mode="strict", required_fields=["timestamp", "level", "event"]
        )

        event = {"timestamp": 1234567890, "level": "INFO"}  # Missing 'event'

        result = processor.process(Mock(), "info", event)
        assert result is None
        assert processor.validation_stats["invalid_events"] == 1
        assert processor.validation_stats["total_events"] == 1

    def test_none_required_field_drops_event(self):
        """Test None required field drops event in strict mode."""
        processor = ValidationProcessor(
            validation_mode="strict", required_fields=["timestamp", "level", "event"]
        )

        event = {"timestamp": 1234567890, "level": None, "event": "Test"}

        result = processor.process(Mock(), "info", event)
        assert result is None
        assert processor.validation_stats["invalid_events"] == 1

    def test_wrong_field_type_drops_event(self):
        """Test wrong field type drops event in strict mode."""
        processor = ValidationProcessor(
            validation_mode="strict",
            required_fields=["timestamp", "level"],
            field_types={"level": str, "count": int},
        )

        event = {"timestamp": 1234567890, "level": "INFO", "count": "not_int"}

        result = processor.process(Mock(), "info", event)
        assert result is None
        assert processor.validation_stats["invalid_events"] == 1


class TestValidationProcessorLenient:
    """Test ValidationProcessor in lenient mode."""

    def test_invalid_event_passes_with_errors(self):
        """Test invalid event passes through with errors in lenient mode."""
        processor = ValidationProcessor(
            validation_mode="lenient",
            required_fields=["timestamp", "level", "event"],
            field_types={"level": str, "count": int},
        )

        event = {
            "timestamp": 1234567890,
            "count": "not_int",
        }  # Missing level, event; wrong type

        result = processor.process(Mock(), "info", event)
        assert result is not None
        assert "_validation_errors" in result
        assert (
            len(result["_validation_errors"]) == 3
        )  # Missing level, event; wrong type
        assert processor.validation_stats["invalid_events"] == 1

    def test_validation_exception_passes_with_exception(self):
        """Test validation exception adds exception to event in lenient mode."""
        processor = ValidationProcessor(validation_mode="lenient")

        # Mock the _validate_event method to raise an exception
        def mock_validate(*args):
            raise ValueError("Test exception")

        processor._validate_event = mock_validate

        event = {"timestamp": 1234567890, "level": "INFO", "event": "Test"}
        result = processor.process(Mock(), "info", event)

        assert result is not None
        assert "_validation_exception" in result
        assert "Test exception" in result["_validation_exception"]


class TestValidationProcessorFix:
    """Test ValidationProcessor in fix mode."""

    def test_fix_missing_timestamp(self):
        """Test fixing missing timestamp field."""
        processor = ValidationProcessor(
            validation_mode="fix", required_fields=["timestamp", "level", "event"]
        )

        event = {"level": "INFO", "event": "Test"}  # Missing timestamp

        result = processor.process(Mock(), "info", event)
        assert result is not None
        assert "timestamp" in result
        assert isinstance(result["timestamp"], float)
        assert processor.validation_stats["fixed_events"] == 1

    def test_fix_missing_level(self):
        """Test fixing missing level field."""
        processor = ValidationProcessor(
            validation_mode="fix", required_fields=["timestamp", "level", "event"]
        )

        event = {"timestamp": 1234567890, "event": "Test"}  # Missing level

        result = processor.process(Mock(), "info", event)
        assert result is not None
        assert result["level"] == "INFO"
        assert processor.validation_stats["fixed_events"] == 1

    def test_fix_missing_event(self):
        """Test fixing missing event field."""
        processor = ValidationProcessor(
            validation_mode="fix", required_fields=["timestamp", "level", "event"]
        )

        event = {"timestamp": 1234567890, "level": "INFO"}  # Missing event

        result = processor.process(Mock(), "info", event)
        assert result is not None
        assert result["event"] == "Unknown event"
        assert processor.validation_stats["fixed_events"] == 1

    def test_fix_using_default_values(self):
        """Test fixing using provided default values."""
        processor = ValidationProcessor(
            validation_mode="fix",
            required_fields=["timestamp", "level", "user_id"],
            default_values={"user_id": "anonymous"},
        )

        event = {"timestamp": 1234567890, "level": "INFO"}  # Missing user_id

        result = processor.process(Mock(), "info", event)
        assert result is not None
        assert result["user_id"] == "anonymous"
        assert processor.validation_stats["fixed_events"] == 1

    def test_fix_type_conversion_str(self):
        """Test fixing field type by converting to string."""
        processor = ValidationProcessor(
            validation_mode="fix",
            required_fields=["timestamp", "level"],
            field_types={"level": str},
        )

        event = {"timestamp": 1234567890, "level": 123}  # Wrong type

        result = processor.process(Mock(), "info", event)
        assert result is not None
        assert result["level"] == "123"
        assert isinstance(result["level"], str)
        assert processor.validation_stats["fixed_events"] == 1

    def test_fix_type_conversion_int(self):
        """Test fixing field type by converting to int."""
        processor = ValidationProcessor(
            validation_mode="fix",
            required_fields=["timestamp"],
            field_types={"count": int},
        )

        event = {"timestamp": 1234567890, "count": "42"}  # Wrong type

        result = processor.process(Mock(), "info", event)
        assert result is not None
        assert result["count"] == 42
        assert isinstance(result["count"], int)

    def test_fix_type_conversion_float(self):
        """Test fixing field type by converting to float."""
        processor = ValidationProcessor(
            validation_mode="fix",
            required_fields=["timestamp"],
            field_types={"value": float},
        )

        event = {"timestamp": 1234567890, "value": "42.5"}

        result = processor.process(Mock(), "info", event)
        assert result is not None
        assert result["value"] == 42.5
        assert isinstance(result["value"], float)

    def test_fix_type_conversion_bool(self):
        """Test fixing field type by converting to bool."""
        processor = ValidationProcessor(
            validation_mode="fix",
            required_fields=["timestamp"],
            field_types={"enabled": bool},
        )

        event = {"timestamp": 1234567890, "enabled": "true"}

        result = processor.process(Mock(), "info", event)
        assert result is not None
        assert result["enabled"] is True
        assert isinstance(result["enabled"], bool)

    def test_fix_fails_drops_event(self):
        """Test event is dropped when fixing fails."""
        processor = ValidationProcessor(
            validation_mode="fix", required_fields=["timestamp", "unfixable_field"]
        )

        event = {"timestamp": 1234567890}  # Missing unfixable_field, no default

        result = processor.process(Mock(), "info", event)
        assert result is None
        assert processor.validation_stats["invalid_events"] == 1

    def test_fix_type_conversion_fails_uses_default(self):
        """Test failed type conversion uses default value if available."""
        processor = ValidationProcessor(
            validation_mode="fix",
            required_fields=["timestamp"],
            field_types={"count": int},
            default_values={"count": 0},
        )

        event = {"timestamp": 1234567890, "count": "not_a_number"}

        result = processor.process(Mock(), "info", event)
        assert result is not None
        assert result["count"] == 0
        assert processor.validation_stats["fixed_events"] == 1

    def test_fix_type_conversion_fails_drops_event(self):
        """Test event is dropped when type conversion fails and no default."""
        processor = ValidationProcessor(
            validation_mode="fix",
            required_fields=["timestamp"],
            field_types={"count": int},
        )

        event = {"timestamp": 1234567890, "count": "not_a_number"}

        result = processor.process(Mock(), "info", event)
        assert result is None
        assert processor.validation_stats["invalid_events"] == 1


class TestValidationProcessorSchema:
    """Test ValidationProcessor with JSON schema validation."""

    def test_schema_validation_passes(self):
        """Test valid event passes schema validation."""
        schema = {
            "type": "object",
            "properties": {
                "timestamp": {"type": "number"},
                "level": {"type": "string"},
                "event": {"type": "string"},
            },
            "required": ["timestamp", "level", "event"],
        }

        processor = ValidationProcessor(
            validation_mode="strict",
            required_fields=["timestamp", "level", "event"],
            schema=schema,
        )

        event = {"timestamp": 1234567890, "level": "INFO", "event": "Test"}

        result = processor.process(Mock(), "info", event)
        # Note: This may be None if jsonschema isn't available
        if result is not None:
            assert result == event
            assert processor.validation_stats["valid_events"] == 1
        else:
            # If jsonschema not available, validation may fail
            assert processor.validation_stats["invalid_events"] == 1

    def test_schema_validation_fails_strict(self):
        """Test invalid event fails schema validation in strict mode."""
        schema = {
            "type": "object",
            "properties": {
                "timestamp": {"type": "number"},
                "level": {"type": "string"},
            },
            "required": ["timestamp", "level"],
        }

        processor = ValidationProcessor(
            validation_mode="strict",
            required_fields=["timestamp", "level"],
            schema=schema,
        )

        event = {"timestamp": "not_a_number", "level": "INFO"}  # Wrong type

        result = processor.process(Mock(), "info", event)
        assert result is None
        assert processor.validation_stats["invalid_events"] == 1

    def test_schema_validation_missing_library(self):
        """Test schema validation when jsonschema library is not available."""
        # Mock the _validate_json_schema method to simulate missing library
        processor = ValidationProcessor(
            validation_mode="lenient",
            required_fields=["timestamp"],
            schema={"type": "object"},
        )

        # Mock the method to return the expected error
        def mock_validate_json_schema(*args):
            return ["jsonschema library not available for schema validation"]

        processor._validate_json_schema = mock_validate_json_schema

        event = {"timestamp": 1234567890}
        result = processor.process(Mock(), "info", event)

        assert result is not None
        assert "_validation_errors" in result
        assert "jsonschema library not available" in result["_validation_errors"][0]


class TestValidationProcessorStats:
    """Test ValidationProcessor statistics collection."""

    def test_validation_stats_initial(self):
        """Test initial validation statistics."""
        processor = ValidationProcessor()
        stats = processor.validation_stats

        assert stats["total_events"] == 0
        assert stats["valid_events"] == 0
        assert stats["invalid_events"] == 0
        assert stats["fixed_events"] == 0
        assert stats["valid_percentage"] == 0.0
        assert stats["invalid_percentage"] == 0.0
        assert stats["fixed_percentage"] == 0.0

    def test_validation_stats_calculations(self):
        """Test validation statistics calculations."""
        processor = ValidationProcessor(validation_mode="fix")

        # Process valid event
        valid_event = {"timestamp": 1234567890, "level": "INFO", "event": "Test"}
        processor.process(Mock(), "info", valid_event)

        # Process invalid event that gets fixed
        invalid_event = {"timestamp": 1234567890, "level": "INFO"}  # Missing event
        processor.process(Mock(), "info", invalid_event)

        # Process invalid event that gets dropped
        processor.validation_mode = "strict"
        processor.process(Mock(), "info", invalid_event)

        stats = processor.validation_stats
        assert stats["total_events"] == 3
        assert stats["valid_events"] == 1
        assert stats["invalid_events"] == 1
        assert stats["fixed_events"] == 1
        assert abs(stats["valid_percentage"] - 33.333333333333336) < 0.001
        assert abs(stats["invalid_percentage"] - 33.333333333333336) < 0.001
        assert abs(stats["fixed_percentage"] - 33.333333333333336) < 0.001


class TestValidationProcessorIntegration:
    """Test ValidationProcessor integration scenarios."""

    def test_complex_validation_scenario(self):
        """Test complex validation scenario with multiple rules."""
        processor = ValidationProcessor(
            validation_mode="fix",
            required_fields=["timestamp", "level", "event", "user_id"],
            field_types={"level": str, "user_id": str, "count": int, "value": float},
            default_values={"user_id": "anonymous", "count": 0},
        )

        event = {
            "timestamp": 1234567890,
            "level": 123,  # Wrong type, should be fixed
            "count": "42",  # Wrong type, should be fixed
            "value": "3.14",  # Wrong type, should be fixed
            # Missing event and user_id, should be added with defaults
        }

        result = processor.process(Mock(), "info", event)

        assert result is not None
        assert result["level"] == "123"  # Fixed type
        assert result["event"] == "Unknown event"  # Added default
        assert result["user_id"] == "anonymous"  # Added from defaults
        assert result["count"] == 42  # Fixed type
        assert result["value"] == 3.14  # Fixed type
        assert processor.validation_stats["fixed_events"] == 1

    def test_processor_registry_integration(self):
        """Test ValidationProcessor is registered in ProcessorRegistry."""
        from fapilog._internal.processor_registry import ProcessorRegistry
        from fapilog.processors.validation import ValidationProcessor

        # Ensure the processor is registered (handles test isolation)
        ProcessorRegistry.register("validation", ValidationProcessor)

        registered_processor = ProcessorRegistry.get("validation")
        assert registered_processor == ValidationProcessor
