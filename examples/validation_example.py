"""Example demonstrating ValidationProcessor functionality."""

import time

from fapilog import configure_logging, log
from fapilog.processors.validation import ValidationProcessor
from fapilog.settings import LoggingSettings


def example_basic_validation():
    """Example: Basic validation with default settings."""
    print("\n=== Basic Validation Example ===")

    # Configure logging with validation enabled
    settings = LoggingSettings(
        enable_validation=True,
        validation_mode="lenient",  # Show validation errors but don't drop events
        validation_required_fields=["timestamp", "level", "event", "user_id"],
        sinks=["stdout"],
        json_console="pretty",
    )

    configure_logging(settings=settings)

    print("Logging valid events...")
    log.info("User logged in", user_id="user123", duration=1.5)
    log.error("Authentication failed", user_id="user456", error_code=401)

    print("\nLogging invalid events (missing user_id)...")
    log.info("User action")  # Missing user_id - will show validation error
    log.warning("System warning")  # Missing user_id - will show validation error


def example_strict_validation():
    """Example: Strict validation mode that drops invalid events."""
    print("\n=== Strict Validation Example ===")

    # Create a validation processor directly
    processor = ValidationProcessor(
        required_fields=["timestamp", "level", "event", "user_id"],
        validation_mode="strict",
    )

    print("Processing events in strict mode:")

    # Valid event - should pass through
    valid_event = {
        "timestamp": time.time(),
        "level": "INFO",
        "event": "User login successful",
        "user_id": "user123",
    }

    result = processor.process(None, "info", valid_event)
    print(f"Valid event result: {result is not None}")

    # Invalid event - should be dropped
    invalid_event = {
        "timestamp": time.time(),
        "level": "INFO",
        "event": "User action",
        # Missing user_id
    }

    result = processor.process(None, "info", invalid_event)
    print(f"Invalid event result: {result is not None}")

    # Show validation statistics
    stats = processor.validation_stats
    print(f"Validation stats: {stats}")


def example_fix_mode():
    """Example: Fix mode that attempts to repair invalid events."""
    print("\n=== Fix Mode Example ===")

    processor = ValidationProcessor(
        required_fields=["timestamp", "level", "event", "user_id"],
        field_types={"level": str, "duration": float, "user_id": str},
        default_values={"user_id": "anonymous", "event": "Unknown event"},
        validation_mode="fix",
    )

    print("Processing events in fix mode:")

    # Event missing required fields - should be fixed with defaults
    incomplete_event = {
        "level": "INFO",
        # Missing timestamp, event, user_id
    }

    result = processor.process(None, "info", incomplete_event)
    print(f"Fixed incomplete event: {result}")

    # Event with wrong types - should be converted
    wrong_types_event = {
        "timestamp": time.time(),
        "level": "INFO",
        "event": "Request completed",
        "user_id": "user123",
        "duration": "2.5",  # String instead of float
    }

    result = processor.process(None, "info", wrong_types_event)
    print(
        f"Fixed type conversion: duration = {result['duration']} (type: {type(result['duration']).__name__})"
    )

    # Event that can't be fixed - should be dropped
    unfixable_event = {
        "level": "INFO",
        "custom_required_field": None,  # No default available
    }

    # Add custom required field with no default
    processor.required_fields.append("custom_required_field")
    result = processor.process(None, "info", unfixable_event)
    print(f"Unfixable event result: {result is not None}")

    # Show validation statistics
    stats = processor.validation_stats
    print(f"Fix mode stats: {stats}")


def example_json_schema_validation():
    """Example: JSON schema validation."""
    print("\n=== JSON Schema Validation Example ===")

    # Define a JSON schema for log events
    log_schema = {
        "type": "object",
        "properties": {
            "timestamp": {"type": "number"},
            "level": {
                "type": "string",
                "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            },
            "event": {"type": "string", "minLength": 1},
            "user_id": {"type": "string", "pattern": "^user\\d+$"},
            "metadata": {
                "type": "object",
                "properties": {
                    "request_id": {"type": "string"},
                    "duration": {"type": "number", "minimum": 0},
                },
            },
        },
        "required": ["timestamp", "level", "event"],
        "additionalProperties": True,
    }

    processor = ValidationProcessor(
        required_fields=["timestamp", "level", "event"],
        schema=log_schema,
        validation_mode="lenient",
    )

    print("Processing events with JSON schema validation:")

    # Valid event that matches schema
    valid_event = {
        "timestamp": time.time(),
        "level": "INFO",
        "event": "User authentication successful",
        "user_id": "user123",
        "metadata": {"request_id": "req-456", "duration": 0.15},
    }

    result = processor.process(None, "info", valid_event)
    print(f"Schema-valid event passed: {'_validation_errors' not in result}")

    # Invalid event that violates schema
    invalid_event = {
        "timestamp": time.time(),
        "level": "INVALID_LEVEL",  # Not in enum
        "event": "",  # Empty string violates minLength
        "user_id": "invalid-format",  # Doesn't match pattern
        "metadata": {
            "duration": -1  # Negative number violates minimum
        },
    }

    result = processor.process(None, "info", invalid_event)
    if "_validation_errors" in result:
        print("Schema validation errors found:")
        for error in result["_validation_errors"]:
            print(f"  - {error}")


def example_performance_and_statistics():
    """Example: Performance testing and statistics collection."""
    print("\n=== Performance and Statistics Example ===")

    processor = ValidationProcessor(
        required_fields=["timestamp", "level", "event"],
        field_types={"timestamp": float, "level": str},
        validation_mode="fix",
    )

    print("Processing multiple events for statistics...")

    # Process various types of events
    events = [
        # Valid events
        {"timestamp": time.time(), "level": "INFO", "event": "Valid event 1"},
        {"timestamp": time.time(), "level": "DEBUG", "event": "Valid event 2"},
        # Events needing fixes
        {"level": "INFO", "event": "Missing timestamp"},
        {"timestamp": "123.45", "level": "ERROR", "event": "Wrong timestamp type"},
        # Invalid events that can't be fixed
        {"level": "INFO"},  # Missing event field with no default
        {},  # Missing all required fields
    ]

    # Process all events
    processed_count = 0
    for i, event in enumerate(events, 1):
        result = processor.process(None, "info", event.copy())
        if result is not None:
            processed_count += 1
        print(f"Event {i}: {'Processed' if result else 'Dropped'}")

    # Show final statistics
    stats = processor.validation_stats
    print("\nFinal Statistics:")
    print(f"  Total events: {stats['total_events']}")
    print(f"  Valid events: {stats['valid_events']} ({stats['valid_percentage']:.1f}%)")
    print(f"  Fixed events: {stats['fixed_events']} ({stats['fixed_percentage']:.1f}%)")
    print(
        f"  Invalid events: {stats['invalid_events']} ({stats['invalid_percentage']:.1f}%)"
    )
    print(f"  Successfully processed: {processed_count}/{len(events)}")


def example_environment_based_configuration():
    """Example: Environment-based validation configuration."""
    print("\n=== Environment-Based Configuration Example ===")

    # This demonstrates how validation settings can be configured via environment
    # In practice, you would set these environment variables:
    # export FAPILOG_ENABLE_VALIDATION=true
    # export FAPILOG_VALIDATION_MODE=fix
    # export FAPILOG_VALIDATION_REQUIRED_FIELDS=timestamp,level,event,user_id
    # export FAPILOG_VALIDATION_FIELD_TYPES=level:str,duration:float

    settings = LoggingSettings(
        enable_validation=True,
        validation_mode="fix",
        validation_required_fields="timestamp,level,event,user_id",
        validation_field_types={"level": "str", "duration": "float"},
        sinks=["stdout"],
        json_console="json",
    )

    print(f"Validation enabled: {settings.enable_validation}")
    print(f"Validation mode: {settings.validation_mode}")
    print(f"Required fields: {settings.validation_required_fields}")
    print(f"Field types: {settings.validation_field_types}")

    # Configure logging with these settings
    configure_logging(settings=settings)

    print("\nLogging with environment-based validation:")
    log.info(
        "System startup", user_id="system", duration="1.5"
    )  # Will fix duration type
    log.error("Configuration error")  # Missing user_id - will be fixed with default


if __name__ == "__main__":
    """Run all validation examples."""
    print("ValidationProcessor Examples")
    print("=" * 50)

    try:
        example_basic_validation()
        example_strict_validation()
        example_fix_mode()
        example_json_schema_validation()
        example_performance_and_statistics()
        example_environment_based_configuration()

        print("\n" + "=" * 50)
        print("All examples completed successfully!")

    except Exception as e:
        print(f"\nExample failed with error: {e}")
        import traceback

        traceback.print_exc()
