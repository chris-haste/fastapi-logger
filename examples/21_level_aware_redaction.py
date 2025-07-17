#!/usr/bin/env python3
"""
Level-Aware Redaction Example

This example demonstrates the level-aware redaction functionality in fapilog.
It shows how redaction can be configured to respect log levels, allowing full
context in DEBUG logs for development while protecting sensitive data in INFO+
logs for production.

Key features:
- Redaction respects log level thresholds
- DEBUG logs bypass redaction (full context preserved)
- INFO and higher logs apply redaction (sensitive data protected)
- Works with all redaction types: pattern, field, and PII auto-detection
- Perfect for development vs production workflows
"""

import os
from typing import Any, Dict

from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings


def create_sensitive_data() -> Dict[str, Any]:
    """Create sample data with sensitive information for demonstration."""
    return {
        "user": {
            "id": 12345,
            "username": "john_doe",
            "email": "john.doe@example.com",
            "password": "super_secret_pass_123",
            "api_key": "sk-live-abc123def456ghi789",
            "profile": {
                "phone": "+1-555-123-4567",
                "credit_card": "4111-1111-1111-1111",
                "ssn": "123-45-6789",
            },
        },
        "auth": {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "refresh_token": "rt_abc123def456",
            "session_id": "sess_789xyz012",
        },
        "config": {
            "database_url": "postgresql://user:password@localhost:5432/db",
            "api_secret": "secret_api_key_456",
            "encryption_key": "enc_key_789xyz",
        },
        "request_id": "req_abc123",
        "timestamp": "2024-01-15T10:30:45Z",
    }


def demonstrate_level_aware_redaction():
    """Demonstrate level-aware redaction with different log levels."""
    print("=" * 80)
    print("LEVEL-AWARE REDACTION DEMONSTRATION")
    print("=" * 80)
    print("This example shows how redaction behavior changes based on log levels:")
    print("• DEBUG: No redaction (full context for debugging)")
    print("• INFO+: Redaction applied (sensitive data protected)")
    print("=" * 80)

    data = create_sensitive_data()

    # Configure comprehensive redaction at INFO level
    settings = LoggingSettings(
        level="DEBUG",  # Allow DEBUG logs to be shown
        redact_level="INFO",  # Only redact at INFO level and above
        redact_patterns=[r"(?i)password", r"(?i)secret", r"(?i)token"],
        redact_fields=[
            "user.api_key",
            "auth.access_token",
            "config.database_url",
        ],
        enable_auto_redact_pii=True,  # Enable automatic PII detection
        redact_replacement="[REDACTED]",
        json_console="pretty",
        queue_enabled=False,  # Disable queue for immediate output
    )
    configure_logging(settings=settings)

    print("\n1. DEBUG LEVEL (should NOT be redacted)")
    print("-" * 50)
    print("Full context preserved for debugging - sensitive data visible:")
    log.debug("User authentication attempt", user_data=data)

    print("\n2. INFO LEVEL (should BE redacted)")
    print("-" * 50)
    print("Sensitive data protected for production logs:")
    log.info("User authentication successful", user_data=data)

    print("\n3. WARNING LEVEL (should BE redacted)")
    print("-" * 50)
    print("Sensitive data protected:")
    log.warning("Authentication rate limit warning", user_data=data)

    print("\n4. ERROR LEVEL (should BE redacted)")
    print("-" * 50)
    print("Sensitive data protected even in error logs:")
    log.error("Authentication failed", user_data=data)


def demonstrate_different_redact_levels():
    """Demonstrate different redact level configurations."""
    print("\n" + "=" * 80)
    print("DIFFERENT REDACT LEVEL CONFIGURATIONS")
    print("=" * 80)

    # Test different redact levels
    redact_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]

    for redact_level in redact_levels:
        print(f"\n--- REDACT_LEVEL: {redact_level} ---")
        print(f"Redaction applied at {redact_level} level and above")

        settings = LoggingSettings(
            level="DEBUG",
            redact_level=redact_level,
            redact_fields=["user.password", "user.api_key"],
            redact_replacement=f"[HIDDEN_AT_{redact_level}]",
            json_console="pretty",
            queue_enabled=False,
        )
        configure_logging(settings=settings)

        print(f"DEBUG log (level=10, redact_level={redact_level}):")
        log.debug("Debug message", sensitive_data={"user": {"password": "secret123"}})

        print(f"INFO log (level=20, redact_level={redact_level}):")
        log.info("Info message", sensitive_data={"user": {"password": "secret123"}})

        print(f"ERROR log (level=40, redact_level={redact_level}):")
        log.error("Error message", sensitive_data={"user": {"password": "secret123"}})


def demonstrate_environment_configuration():
    """Demonstrate environment-based level-aware redaction configuration."""
    print("\n" + "=" * 80)
    print("ENVIRONMENT-BASED CONFIGURATION")
    print("=" * 80)

    data = {"user": {"password": "env_secret_123", "api_key": "env_key_456"}}

    # Development environment configuration
    print("\nDEVELOPMENT ENVIRONMENT (DEBUG level redaction):")
    print("-" * 50)
    os.environ["FAPILOG_REDACT_LEVEL"] = "DEBUG"
    os.environ["FAPILOG_REDACT_FIELDS"] = "user.password,user.api_key"
    configure_logging()

    log.debug("Dev: Debug log", user_data=data)
    log.info("Dev: Info log", user_data=data)

    # Production environment configuration
    print("\nPRODUCTION ENVIRONMENT (INFO level redaction):")
    print("-" * 50)
    os.environ["FAPILOG_REDACT_LEVEL"] = "INFO"
    configure_logging()

    log.debug("Prod: Debug log", user_data=data)
    log.info("Prod: Info log", user_data=data)

    # Clean up environment variables
    del os.environ["FAPILOG_REDACT_LEVEL"]
    del os.environ["FAPILOG_REDACT_FIELDS"]


def demonstrate_all_redaction_types():
    """Demonstrate level-aware behavior with all redaction types."""
    print("\n" + "=" * 80)
    print("ALL REDACTION TYPES WITH LEVEL AWARENESS")
    print("=" * 80)

    data = {
        "user": {
            "email": "user@example.com",  # Will be caught by PII detection
            "password": "secret_password",  # Will be caught by pattern
            "api_key": "sk_live_123456",  # Will be caught by field redaction
        },
        "credit_card": "4111-1111-1111-1111",  # Will be caught by PII detection
    }

    settings = LoggingSettings(
        level="DEBUG",
        redact_level="INFO",
        # Pattern-based redaction
        redact_patterns=[r"(?i)password"],
        # Field-based redaction
        redact_fields=["user.api_key"],
        # PII auto-detection (enabled by default)
        enable_auto_redact_pii=True,
        redact_replacement="[PROTECTED]",
        json_console="pretty",
        queue_enabled=False,
    )
    configure_logging(settings=settings)

    print("\nDEBUG: All redaction types bypass level check (sensitive data visible):")
    log.debug("Authentication data", auth_data=data)

    print("\nINFO: All redaction types active (sensitive data protected):")
    log.info("Authentication data", auth_data=data)


def demonstrate_use_cases():
    """Demonstrate real-world use cases for level-aware redaction."""
    print("\n" + "=" * 80)
    print("REAL-WORLD USE CASES")
    print("=" * 80)

    # Simulate different deployment environments
    use_cases = [
        {
            "name": "Development",
            "description": "Full debugging context needed",
            "redact_level": "CRITICAL",  # Only redact critical logs
            "log_level": "DEBUG",
        },
        {
            "name": "Staging",
            "description": "Realistic production testing",
            "redact_level": "WARNING",  # Redact warnings and above
            "log_level": "INFO",
        },
        {
            "name": "Production",
            "description": "Maximum security compliance",
            "redact_level": "INFO",  # Redact info and above
            "log_level": "INFO",
        },
    ]

    data = {"user": {"password": "test_password", "email": "test@example.com"}}

    for use_case in use_cases:
        print(f"\n--- {use_case['name'].upper()} ENVIRONMENT ---")
        print(f"Description: {use_case['description']}")
        print(
            f"Log Level: {use_case['log_level']}, Redact Level: {use_case['redact_level']}"
        )

        settings = LoggingSettings(
            level=use_case["log_level"],
            redact_level=use_case["redact_level"],
            redact_fields=["user.password"],
            enable_auto_redact_pii=True,
            json_console="pretty",
            queue_enabled=False,
        )
        configure_logging(settings=settings)

        log.debug(f"{use_case['name']}: Debug trace", user_data=data)
        log.info(f"{use_case['name']}: User action", user_data=data)
        log.warning(f"{use_case['name']}: Rate limit", user_data=data)


if __name__ == "__main__":
    try:
        demonstrate_level_aware_redaction()
        demonstrate_different_redact_levels()
        demonstrate_environment_configuration()
        demonstrate_all_redaction_types()
        demonstrate_use_cases()

        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print("✓ Level-aware redaction provides flexible security controls")
        print("✓ DEBUG logs preserve full context for development debugging")
        print("✓ INFO+ logs protect sensitive data for production compliance")
        print("✓ Works seamlessly with all redaction types (pattern, field, PII)")
        print("✓ Environment-configurable for different deployment stages")
        print("✓ Zero performance impact with efficient level checking")
        print("\nPerfect for maintaining security in production while enabling")
        print("effective debugging in development environments!")

    except Exception as e:
        print(f"Error running example: {e}")
        import traceback

        traceback.print_exc()
