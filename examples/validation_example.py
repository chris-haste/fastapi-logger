"""Example demonstrating ValidationProcessor usage in fapilog."""

from fapilog import configure_logging, log
from fapilog.processors.validation import ValidationProcessor
from fapilog.settings import LoggingSettings


def main():
    """Demonstrate ValidationProcessor functionality."""
    print("=== ValidationProcessor Example ===\n")

    # Example 1: Lenient mode - invalid events pass through with errors
    print("1. Lenient mode example:")
    settings = LoggingSettings(
        enable_validation=True,
        validation_mode="lenient",
        validation_required_fields=["timestamp", "level", "event", "user_id"],
        validation_field_types={"level": "str", "user_id": "str", "duration": "float"},
        sinks=["stdout"],
        json_console="pretty",
    )

    configure_logging(settings=settings)

    # This will pass through with validation errors
    log.info("User action without user_id")  # Missing user_id

    # This will pass through with type error
    log.info("Request completed", duration="not_a_float")  # Wrong type

    print("\n" + "=" * 50 + "\n")

    # Example 2: Fix mode - invalid events are automatically corrected
    print("2. Fix mode example:")
    settings_fix = LoggingSettings(
        enable_validation=True,
        validation_mode="fix",
        validation_required_fields=["timestamp", "level", "event", "user_id"],
        validation_field_types={"level": "str", "user_id": "str", "duration": "float"},
        sinks=["stdout"],
        json_console="pretty",
    )

    configure_logging(settings=settings_fix)

    # These will be automatically fixed
    log.info("User action")  # Missing user_id will get default value
    log.info(
        "Request completed", duration="123.45"
    )  # String will be converted to float

    print("\n" + "=" * 50 + "\n")

    # Example 3: Direct processor usage with custom configuration
    print("3. Direct processor usage:")

    processor = ValidationProcessor(
        required_fields=["timestamp", "level", "event", "user_id"],
        field_types={"level": str, "user_id": str, "duration": float},
        default_values={"user_id": "anonymous"},
        validation_mode="fix",
    )

    # Mock logger for demonstration
    class MockLogger:
        pass

    # Test various scenarios
    test_events = [
        # Valid event
        {
            "timestamp": 1234567890,
            "level": "INFO",
            "event": "User login",
            "user_id": "user123",
            "duration": 0.5,
        },
        # Missing user_id (will be fixed with default)
        {
            "timestamp": 1234567891,
            "level": "INFO",
            "event": "User action",
            "duration": 1.2,
        },
        # Wrong type for duration (will be fixed)
        {
            "timestamp": 1234567892,
            "level": "INFO",
            "event": "Request completed",
            "user_id": "user456",
            "duration": "2.5",
        },
        # Missing required field that can't be fixed
        {
            "timestamp": 1234567893,
            "level": "INFO",
            # Missing event field with no default
        },
    ]

    print("Processing test events:")
    for i, event in enumerate(test_events, 1):
        print(f"\nEvent {i}: {event}")
        result = processor.process(MockLogger(), "info", event)
        if result:
            print(f"Result: {result}")
        else:
            print("Result: Event dropped (invalid)")

    # Show validation statistics
    print("\nValidation Statistics:")
    stats = processor.validation_stats
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\n" + "=" * 50 + "\n")

    # Example 4: Schema validation (requires jsonschema package)
    print("4. Schema validation example:")

    try:
        import jsonschema  # noqa: F401

        schema = {
            "type": "object",
            "properties": {
                "timestamp": {"type": "number"},
                "level": {
                    "type": "string",
                    "enum": ["DEBUG", "INFO", "WARNING", "ERROR"],
                },
                "event": {"type": "string"},
                "user_id": {"type": "string"},
                "metadata": {
                    "type": "object",
                    "properties": {
                        "ip": {"type": "string"},
                        "user_agent": {"type": "string"},
                    },
                },
            },
            "required": ["timestamp", "level", "event"],
        }

        schema_processor = ValidationProcessor(
            required_fields=["timestamp", "level", "event"],
            schema=schema,
            validation_mode="lenient",
        )

        schema_events = [
            # Valid event
            {
                "timestamp": 1234567890,
                "level": "INFO",
                "event": "User action",
                "user_id": "user123",
                "metadata": {"ip": "192.168.1.1", "user_agent": "Mozilla/5.0"},
            },
            # Invalid level enum
            {
                "timestamp": 1234567891,
                "level": "INVALID_LEVEL",
                "event": "User action",
            },
            # Invalid timestamp type
            {
                "timestamp": "not_a_number",
                "level": "INFO",
                "event": "User action",
            },
        ]

        print("Processing events with JSON schema validation:")
        for i, event in enumerate(schema_events, 1):
            print(f"\nSchema Event {i}: {event}")
            result = schema_processor.process(MockLogger(), "info", event)
            if result:
                if "_validation_errors" in result:
                    print(
                        f"Result: Event passed with errors: {result['_validation_errors']}"
                    )
                else:
                    print("Result: Valid event")
            else:
                print("Result: Event dropped (invalid)")

    except ImportError:
        print("jsonschema package not available - skipping schema validation example")

    print("\n=== Example completed ===")


if __name__ == "__main__":
    main()
