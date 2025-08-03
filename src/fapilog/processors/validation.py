"""ValidationProcessor for fapilog structured logging."""

import time
from typing import Any, Dict, List, Optional

from ..exceptions import ProcessorConfigurationError
from .base import Processor


class ValidationProcessor(Processor):
    """Validate log event structure and content."""

    def __init__(
        self,
        required_fields: Optional[List[str]] = None,
        schema: Optional[Dict[str, Any]] = None,
        field_types: Optional[Dict[str, type]] = None,
        default_values: Optional[Dict[str, Any]] = None,
        validation_mode: str = "strict",
        **config: Any,
    ) -> None:
        """Initialize validation processor.

        Args:
            required_fields: List of field names that must be present in events
            schema: JSON schema for validation (requires jsonschema library)
            field_types: Dictionary mapping field names to expected types
            default_values: Default values for missing fields in fix mode
            validation_mode: Validation behavior - 'strict', 'lenient', or 'fix'
            **config: Additional configuration parameters
        """
        self.required_fields = (
            required_fields
            if required_fields is not None
            else ["timestamp", "level", "event"]
        )
        self.schema = schema
        self.field_types = field_types or {}
        self.default_values = default_values or {}
        self.validation_mode = validation_mode
        self._validation_stats = {
            "total_events": 0,
            "valid_events": 0,
            "invalid_events": 0,
            "fixed_events": 0,
        }
        super().__init__(
            required_fields=self.required_fields,
            schema=schema,
            field_types=field_types,
            default_values=default_values,
            validation_mode=validation_mode,
            **config,
        )

    def validate_config(self) -> None:
        """Validate processor configuration."""
        if self.validation_mode not in ["strict", "lenient", "fix"]:
            raise ProcessorConfigurationError(
                "validation_mode must be 'strict', 'lenient', or 'fix'"
            )
        if not self.required_fields:
            raise ProcessorConfigurationError("required_fields cannot be empty")

        # Validate field_types if provided
        for field, field_type in self.field_types.items():
            if not isinstance(field_type, type):
                raise ProcessorConfigurationError(
                    f"field_types['{field}'] must be a valid type"
                )

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Validate and optionally fix event structure."""
        self._validation_stats["total_events"] += 1

        try:
            validation_result = self._validate_event(event_dict)

            if validation_result["is_valid"]:
                self._validation_stats["valid_events"] += 1
                return event_dict

            # Handle invalid events based on mode
            if self.validation_mode == "strict":
                self._validation_stats["invalid_events"] += 1
                return None  # Drop invalid events

            elif self.validation_mode == "lenient":
                self._validation_stats["invalid_events"] += 1
                # Add validation errors to event but pass through
                event_dict["_validation_errors"] = validation_result["errors"]
                return event_dict

            elif self.validation_mode == "fix":
                fixed_event = self._fix_event(event_dict, validation_result["errors"])
                if fixed_event:
                    self._validation_stats["fixed_events"] += 1
                    return fixed_event
                else:
                    self._validation_stats["invalid_events"] += 1
                    return None

        except Exception as e:
            # Validation itself failed - log error and pass through in lenient mode
            if self.validation_mode == "strict":
                return None
            else:
                event_dict["_validation_exception"] = str(e)
                return event_dict

    def _validate_event(self, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Validate event against rules and return validation result."""
        errors = []

        # Check required fields
        for field in self.required_fields:
            if field not in event_dict:
                errors.append(f"Missing required field: {field}")
            elif event_dict[field] is None:
                errors.append(f"Required field is None: {field}")

        # Check field types
        for field, expected_type in self.field_types.items():
            if field in event_dict and event_dict[field] is not None:
                if not isinstance(event_dict[field], expected_type):
                    actual_type = type(event_dict[field]).__name__
                    expected_type_name = expected_type.__name__
                    errors.append(
                        f"Field '{field}' has wrong type: expected "
                        f"{expected_type_name}, got {actual_type}"
                    )

        # Validate against JSON schema if provided
        if self.schema:
            schema_errors = self._validate_json_schema(event_dict)
            errors.extend(schema_errors)

        return {"is_valid": len(errors) == 0, "errors": errors}

    def _validate_json_schema(self, event_dict: Dict[str, Any]) -> List[str]:
        """Validate event against JSON schema."""
        try:
            import jsonschema

            jsonschema.validate(event_dict, self.schema)
            return []
        except ImportError:
            return ["jsonschema library not available for schema validation"]
        except jsonschema.ValidationError as e:
            return [f"Schema validation error: {e.message}"]
        except Exception as e:
            return [f"Schema validation failed: {str(e)}"]

    def _fix_event(
        self, event_dict: Dict[str, Any], errors: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Attempt to fix validation errors in event."""
        fixed_event = event_dict.copy()

        # Add missing required fields with default values
        for field in self.required_fields:
            if field not in fixed_event:
                if field in self.default_values:
                    fixed_event[field] = self.default_values[field]
                elif field == "timestamp":
                    fixed_event[field] = time.time()
                elif field == "level":
                    fixed_event[field] = "INFO"
                elif field == "event":
                    fixed_event[field] = "Unknown event"
                else:
                    # Can't fix this field - return None to drop event
                    return None

        # Fix field types where possible
        for field, expected_type in self.field_types.items():
            if field in fixed_event and fixed_event[field] is not None:
                if not isinstance(fixed_event[field], expected_type):
                    try:
                        # Attempt type conversion
                        if expected_type is str:
                            fixed_event[field] = str(fixed_event[field])
                        elif expected_type is int:
                            fixed_event[field] = int(float(fixed_event[field]))
                        elif expected_type is float:
                            fixed_event[field] = float(fixed_event[field])
                        elif expected_type is bool:
                            fixed_event[field] = bool(fixed_event[field])
                    except (ValueError, TypeError):
                        # Can't convert - use default if available
                        if field in self.default_values:
                            fixed_event[field] = self.default_values[field]
                        else:
                            return None

        return fixed_event

    @property
    def validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        stats = self._validation_stats.copy()
        if stats["total_events"] > 0:
            stats["valid_percentage"] = (
                stats["valid_events"] / stats["total_events"]
            ) * 100
            stats["invalid_percentage"] = (
                stats["invalid_events"] / stats["total_events"]
            ) * 100
            stats["fixed_percentage"] = (
                stats["fixed_events"] / stats["total_events"]
            ) * 100
        else:
            stats["valid_percentage"] = 0.0
            stats["invalid_percentage"] = 0.0
            stats["fixed_percentage"] = 0.0
        return stats
