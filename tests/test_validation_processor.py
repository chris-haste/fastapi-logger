"""Tests for ValidationProcessor."""

import time

import pytest

from fapilog.exceptions import ProcessorConfigurationError
from fapilog.processors.validation import ValidationProcessor


class TestValidationProcessorConfig:
    """Test ValidationProcessor configuration validation."""

    def test_default_config(self):
        """Test processor with default configuration."""
        processor = ValidationProcessor()
        assert processor.required_fields == ["timestamp", "level", "event"]
        assert processor.validation_mode == "strict"
        assert processor.field_types == {}
        assert processor.default_values == {}
        assert processor.schema is None

    def test_custom_required_fields(self):
        """Test processor with custom required fields."""
        required_fields = ["timestamp", "level", "user_id"]
        processor = ValidationProcessor(required_fields=required_fields)
        assert processor.required_fields == required_fields

    def test_validation_mode_config(self):
        """Test different validation modes."""
        for mode in ["strict", "lenient", "fix"]:
            processor = ValidationProcessor(validation_mode=mode)
            assert processor.validation_mode == mode

    def test_invalid_validation_mode(self):
        """Test invalid validation mode raises error."""
        with pytest.raises(ProcessorConfigurationError) as exc_info:
            ValidationProcessor(validation_mode="invalid")
        assert "validation_mode must be 'strict', 'lenient', or 'fix'" in str(
            exc_info.value
        )

    def test_empty_required_fields(self):
        """Test empty required fields raises error."""
        with pytest.raises(ProcessorConfigurationError) as exc_info:
            ValidationProcessor(required_fields=[])
        assert "required_fields cannot be empty" in str(exc_info.value)

    def test_invalid_field_type(self):
        """Test invalid field type raises error."""
        with pytest.raises(ProcessorConfigurationError) as exc_info:
            ValidationProcessor(field_types={"level": "not_a_type"})
        assert "field_types['level'] must be a valid type" in str(exc_info.value)

    def test_field_types_config(self):
        """Test field types configuration."""
        field_types = {"level": str, "duration": float, "count": int}
        processor = ValidationProcessor(field_types=field_types)
        assert processor.field_types == field_types

    def test_default_values_config(self):
        """Test default values configuration."""
        default_values = {"level": "INFO", "user_id": "unknown"}
        processor = ValidationProcessor(default_values=default_values)
        assert processor.default_values == default_values


class TestValidationProcessorValidation:
    """Test ValidationProcessor validation logic."""

    def test_valid_event_passes(self):
        """Test that valid events pass validation."""
        processor = ValidationProcessor(
            required_fields=["timestamp", "level", "event"],
            field_types={"level": str, "timestamp": float},
        )

        event = {
            "timestamp": time.time(),
            "level": "INFO",
            "event": "Test message",
        }

        result = processor.process(None, "info", event)
        assert result == event

        stats = processor.validation_stats
        assert stats["total_events"] == 1
        assert stats["valid_events"] == 1
        assert stats["invalid_events"] == 0

    def test_missing_required_field_strict_mode(self):
        """Test missing required field in strict mode drops event."""
        processor = ValidationProcessor(
            required_fields=["timestamp", "level", "event"],
            validation_mode="strict",
        )

        event = {"timestamp": time.time(), "level": "INFO"}  # Missing 'event'

        result = processor.process(None, "info", event)
        assert result is None

        stats = processor.validation_stats
        assert stats["total_events"] == 1
        assert stats["valid_events"] == 0
        assert stats["invalid_events"] == 1

    def test_missing_required_field_lenient_mode(self):
        """Test missing required field in lenient mode adds error info."""
        processor = ValidationProcessor(
            required_fields=["timestamp", "level", "event"],
            validation_mode="lenient",
        )

        event = {"timestamp": time.time(), "level": "INFO"}  # Missing 'event'

        result = processor.process(None, "info", event)
        assert result is not None
        assert "_validation_errors" in result
        assert "Missing required field: event" in result["_validation_errors"]

        stats = processor.validation_stats
        assert stats["total_events"] == 1
        assert stats["valid_events"] == 0
        assert stats["invalid_events"] == 1

    def test_none_required_field(self):
        """Test required field with None value."""
        processor = ValidationProcessor(
            required_fields=["timestamp", "level", "event"],
            validation_mode="lenient",
        )

        event = {"timestamp": time.time(), "level": None, "event": "test"}

        result = processor.process(None, "info", event)
        assert result is not None
        assert "_validation_errors" in result
        assert "Required field is None: level" in result["_validation_errors"]

    def test_wrong_field_type(self):
        """Test wrong field type validation."""
        processor = ValidationProcessor(
            required_fields=["timestamp", "level"],
            field_types={"timestamp": float, "level": str},
            validation_mode="lenient",
        )

        event = {"timestamp": "not_a_float", "level": "INFO"}

        result = processor.process(None, "info", event)
        assert result is not None
        assert "_validation_errors" in result
        assert any(
            "wrong type: expected float, got str" in error
            for error in result["_validation_errors"]
        )

    def test_fix_mode_adds_missing_fields(self):
        """Test fix mode adds missing required fields with defaults."""
        processor = ValidationProcessor(
            required_fields=["timestamp", "level", "event"],
            validation_mode="fix",
        )

        event = {"level": "INFO"}  # Missing timestamp and event

        result = processor.process(None, "info", event)
        assert result is not None
        assert "timestamp" in result
        assert "event" in result
        assert result["event"] == "Unknown event"
        assert result["level"] == "INFO"

        stats = processor.validation_stats
        assert stats["fixed_events"] == 1

    def test_fix_mode_with_custom_defaults(self):
        """Test fix mode with custom default values."""
        processor = ValidationProcessor(
            required_fields=["timestamp", "level", "event", "user_id"],
            default_values={"user_id": "anonymous", "event": "default_event"},
            validation_mode="fix",
        )

        event = {"level": "INFO"}  # Missing other fields

        result = processor.process(None, "info", event)
        assert result is not None
        assert result["user_id"] == "anonymous"
        assert result["event"] == "default_event"
        assert "timestamp" in result

    def test_fix_mode_type_conversion(self):
        """Test fix mode converts field types."""
        processor = ValidationProcessor(
            required_fields=["timestamp", "level"],
            field_types={"timestamp": float, "duration": int},
            validation_mode="fix",
        )

        event = {"timestamp": "123.45", "level": "INFO", "duration": "67"}

        result = processor.process(None, "info", event)
        assert result is not None
        assert isinstance(result["timestamp"], float)
        assert result["timestamp"] == 123.45
        assert isinstance(result["duration"], int)
        assert result["duration"] == 67

    def test_fix_mode_conversion_failure(self):
        """Test fix mode when type conversion fails."""
        processor = ValidationProcessor(
            required_fields=["timestamp", "level"],
            field_types={"timestamp": float},
            validation_mode="fix",
        )

        event = {"timestamp": "not_convertible", "level": "INFO"}

        result = processor.process(None, "info", event)
        assert result is None  # Can't fix, so drop event

    def test_fix_mode_conversion_with_defaults(self):
        """Test fix mode uses defaults when conversion fails."""
        processor = ValidationProcessor(
            required_fields=["timestamp", "level"],
            field_types={"timestamp": float},
            default_values={"timestamp": 0.0},
            validation_mode="fix",
        )

        event = {"timestamp": "not_convertible", "level": "INFO"}

        result = processor.process(None, "info", event)
        assert result is not None
        assert result["timestamp"] == 0.0

    def test_unfixable_field_drops_event(self):
        """Test fix mode drops event when field can't be fixed."""
        processor = ValidationProcessor(
            required_fields=["custom_field", "level"],
            validation_mode="fix",
        )

        event = {"level": "INFO"}  # Missing custom_field with no default

        result = processor.process(None, "info", event)
        assert result is None


class TestValidationProcessorJsonSchema:
    """Test ValidationProcessor JSON schema validation."""

    def test_json_schema_validation_success(self):
        """Test successful JSON schema validation."""
        schema = {
            "type": "object",
            "properties": {
                "level": {"type": "string"},
                "timestamp": {"type": "number"},
            },
            "required": ["level"],
        }

        processor = ValidationProcessor(
            required_fields=["level"],
            schema=schema,
            validation_mode="lenient",
        )

        event = {"level": "INFO", "timestamp": 123.45}

        result = processor.process(None, "info", event)
        assert result == event
        assert "_validation_errors" not in result

    def test_json_schema_validation_failure(self):
        """Test JSON schema validation failure."""
        schema = {
            "type": "object",
            "properties": {
                "level": {"type": "string"},
                "timestamp": {"type": "number"},
            },
            "required": ["timestamp"],
        }

        processor = ValidationProcessor(
            required_fields=["level"],
            schema=schema,
            validation_mode="lenient",
        )

        event = {"level": "INFO"}  # Missing timestamp required by schema

        result = processor.process(None, "info", event)
        assert result is not None
        assert "_validation_errors" in result
        assert any(
            "Schema validation error" in error for error in result["_validation_errors"]
        )

    def test_missing_jsonschema_library(self):
        """Test handling of missing jsonschema library."""
        processor = ValidationProcessor(
            required_fields=["level"],
            schema={"type": "object"},
            validation_mode="lenient",
        )

        # Mock the import error by patching the validation method
        original_method = processor._validate_json_schema

        def mock_validate_json_schema(event_dict):
            return ["jsonschema library not available for schema validation"]

        processor._validate_json_schema = mock_validate_json_schema

        event = {"level": "INFO"}
        result = processor.process(None, "info", event)

        assert result is not None
        assert "_validation_errors" in result
        assert "jsonschema library not available" in result["_validation_errors"][0]

        # Restore original method
        processor._validate_json_schema = original_method


class TestValidationProcessorErrorHandling:
    """Test ValidationProcessor error handling."""

    def test_validation_exception_strict_mode(self):
        """Test validation exception in strict mode drops event."""
        processor = ValidationProcessor(validation_mode="strict")

        # Mock the validation method to raise exception
        def mock_validate_event(event_dict):
            raise ValueError("Test validation error")

        processor._validate_event = mock_validate_event

        event = {"level": "INFO"}
        result = processor.process(None, "info", event)
        assert result is None

    def test_validation_exception_lenient_mode(self):
        """Test validation exception in lenient mode adds exception info."""
        processor = ValidationProcessor(validation_mode="lenient")

        # Mock the validation method to raise exception
        def mock_validate_event(event_dict):
            raise ValueError("Test validation error")

        processor._validate_event = mock_validate_event

        event = {"level": "INFO"}
        result = processor.process(None, "info", event)
        assert result is not None
        assert "_validation_exception" in result
        assert "Test validation error" in result["_validation_exception"]


class TestValidationProcessorStats:
    """Test ValidationProcessor statistics collection."""

    def test_validation_stats_empty(self):
        """Test validation statistics when no events processed."""
        processor = ValidationProcessor()
        stats = processor.validation_stats

        assert stats["total_events"] == 0
        assert stats["valid_events"] == 0
        assert stats["invalid_events"] == 0
        assert stats["fixed_events"] == 0
        assert stats["valid_percentage"] == 0.0
        assert stats["invalid_percentage"] == 0.0
        assert stats["fixed_percentage"] == 0.0

    def test_validation_stats_mixed_results(self):
        """Test validation statistics with mixed results."""
        processor = ValidationProcessor(
            required_fields=["timestamp", "level", "custom_field"],
            validation_mode="fix",
        )

        # Valid event
        processor.process(
            None, "info", {"timestamp": 123, "level": "INFO", "custom_field": "test"}
        )

        # Invalid event that gets fixed
        processor.process(
            None, "info", {"level": "INFO", "custom_field": "test"}
        )  # Missing timestamp

        # Invalid event that can't be fixed
        processor.process(None, "info", {})  # Missing custom_field with no default

        stats = processor.validation_stats
        assert stats["total_events"] == 3
        assert stats["valid_events"] == 1
        assert stats["fixed_events"] == 1
        assert stats["invalid_events"] == 1
        assert stats["valid_percentage"] == pytest.approx(33.33, rel=1e-2)
        assert stats["fixed_percentage"] == pytest.approx(33.33, rel=1e-2)
        assert stats["invalid_percentage"] == pytest.approx(33.33, rel=1e-2)


class TestValidationProcessorIntegration:
    """Test ValidationProcessor integration scenarios."""

    def test_processor_lifecycle(self):
        """Test processor start/stop lifecycle."""
        processor = ValidationProcessor()

        # Test initial state
        assert not processor.is_started

        # Test startup (should not raise)
        import asyncio

        asyncio.run(processor.start())
        assert processor.is_started

        # Test idempotent startup
        asyncio.run(processor.start())
        assert processor.is_started

        # Test shutdown
        asyncio.run(processor.stop())
        assert not processor.is_started

        # Test idempotent shutdown
        asyncio.run(processor.stop())
        assert not processor.is_started

    def test_processor_config_passthrough(self):
        """Test that configuration is passed through to base class."""
        processor = ValidationProcessor(
            required_fields=["level"],
            validation_mode="lenient",
            custom_config="test_value",
        )

        assert processor.config["required_fields"] == ["level"]
        assert processor.config["validation_mode"] == "lenient"
        assert processor.config["custom_config"] == "test_value"
