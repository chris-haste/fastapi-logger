#!/usr/bin/env python3
"""
Example 3: Output Formats

This example demonstrates the different output formats available in fapilog:
- JSON format (production-ready, machine-readable)
- Pretty console format (development-friendly, human-readable)
- Auto-detection based on TTY
"""

import sys

from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings


def demonstrate_json_format():
    """Show JSON output format (production-ready)."""
    print("=== JSON Output Format ===")
    print("Best for: Production, log aggregation, machine processing")
    print("-" * 50)

    settings = LoggingSettings(
        level="INFO",
        json_console="json",  # Force JSON output
        queue_enabled=False,  # Disable queue for simpler example
    )
    configure_logging(settings=settings)

    # Log some structured events
    log.info(
        "User login successful",
        user_id="user_123",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0...",
        login_method="password",
    )

    log.warning(
        "Rate limit approaching",
        endpoint="/api/users",
        current_requests=95,
        limit=100,
        window_seconds=60,
    )

    log.error(
        "Database connection failed",
        database="postgres",
        host="db.example.com",
        port=5432,
        error="connection timeout",
        retry_count=3,
    )

    print("\nJSON format features:")
    print("✅ Machine-readable for log aggregation")
    print("✅ Consistent structure for parsing")
    print("✅ All fields are properly escaped")
    print("✅ Suitable for ELK, Loki, Cloud Logging")


def demonstrate_pretty_format():
    """Show pretty console format (development-friendly)."""
    print("\n\n=== Pretty Console Format ===")
    print("Best for: Development, debugging, human readability")
    print("-" * 50)

    settings = LoggingSettings(
        level="INFO",
        json_console="pretty",  # Force pretty output
        queue_enabled=False,  # Disable queue for simpler example
    )
    configure_logging(settings=settings)

    # Log the same events for comparison
    log.info(
        "User login successful",
        user_id="user_123",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0...",
        login_method="password",
    )

    log.warning(
        "Rate limit approaching",
        endpoint="/api/users",
        current_requests=95,
        limit=100,
        window_seconds=60,
    )

    log.error(
        "Database connection failed",
        database="postgres",
        host="db.example.com",
        port=5432,
        error="connection timeout",
        retry_count=3,
    )

    print("\nPretty format features:")
    print("✅ Color-coded log levels")
    print("✅ Human-readable structure")
    print("✅ Easy to scan and debug")
    print("✅ Great for development and testing")


def demonstrate_auto_detection():
    """Show auto-detection based on TTY."""
    print("\n\n=== Auto-Detection Format ===")
    print("Best for: Automatic dev/prod switching")
    print("-" * 50)

    settings = LoggingSettings(
        level="INFO",
        json_console="auto",  # Auto-detect based on TTY
        queue_enabled=False,  # Disable queue for simpler example
    )
    configure_logging(settings=settings)

    # Log some events
    log.info(
        "Auto-detection example",
        format="auto",
        tty_available=hasattr(sys.stderr, "isatty"),
        detected_format="pretty" if sys.stderr.isatty() else "json",
    )

    log.info(
        "This format is automatically chosen",
        reason="TTY detection",
        development=sys.stderr.isatty(),
    )

    print("\nAuto-detection behavior:")
    print("✅ TTY available → Pretty format")
    print("✅ No TTY (pipes, files) → JSON format")
    print("✅ Perfect for scripts and CI/CD")
    print("✅ No configuration needed")


def demonstrate_complex_structures():
    """Show how complex data structures are handled."""
    print("\n\n=== Complex Data Structures ===")
    print("Demonstrating nested objects, lists, and special values")
    print("-" * 50)

    settings = LoggingSettings(
        level="INFO",
        json_console="pretty",  # Use pretty for readability
        queue_enabled=False,
    )
    configure_logging(settings=settings)

    # Nested dictionary
    user_data = {
        "profile": {
            "name": "John Doe",
            "email": "john@example.com",
            "preferences": {"theme": "dark", "language": "en"},
        },
        "permissions": ["read", "write", "admin"],
    }

    log.info(
        "User data processed",
        user_id="user_456",
        data=user_data,
        processing_time_ms=125.5,
    )

    # List of objects
    api_calls = [
        {"endpoint": "/api/users", "status": 200, "duration_ms": 45},
        {"endpoint": "/api/posts", "status": 200, "duration_ms": 32},
        {"endpoint": "/api/comments", "status": 404, "duration_ms": 12},
    ]

    log.info(
        "API calls summary",
        total_calls=len(api_calls),
        successful_calls=2,
        failed_calls=1,
        calls=api_calls,
    )

    # Special values
    log.info(
        "Special values example",
        null_value=None,
        boolean_true=True,
        boolean_false=False,
        empty_string="",
        zero_number=0,
        negative_number=-42,
    )


def main():
    """Run all output format examples."""

    demonstrate_json_format()
    demonstrate_pretty_format()
    demonstrate_auto_detection()
    demonstrate_complex_structures()

    print("\n" + "=" * 60)
    print("Output Format Summary:")
    print("✅ JSON: Production, aggregation, machine-readable")
    print("✅ Pretty: Development, debugging, human-readable")
    print("✅ Auto: Smart detection based on environment")
    print("✅ Both handle complex data structures")
    print("✅ Both preserve all structured data")


if __name__ == "__main__":
    main()
