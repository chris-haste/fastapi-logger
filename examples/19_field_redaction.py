#!/usr/bin/env python3
"""
Field Redaction Example

This example demonstrates the manual field redaction functionality in fapilog.
It shows how to redact sensitive fields from log output using both
pattern-based and field-based redaction approaches.

Note: This example covers MANUAL redaction (specifying exact fields/patterns).
For AUTOMATIC PII detection and redaction, see examples/20_automatic_pii_redaction.py
which demonstrates automatic detection of common PII patterns like emails,
credit cards, phone numbers, and IP addresses.
"""

import os
from typing import Any, Dict

from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings


def create_sample_data() -> Dict[str, Any]:
    """Create sample data with sensitive information for demonstration."""
    return {
        "user": {
            "id": 12345,
            "name": "john_doe",
            "email": "john@example.com",
            "password": "secret_password_123",
            "profile": {
                "phone": "+1-555-123-4567",
                "address": "123 Main St, City, State",
                "api_key": "sk-abc123def456ghi789",
                "preferences": {"theme": "dark", "language": "en"},
            },
        },
        "auth": {
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "refresh_token": "rt_abc123def456",
            "expires_at": "2024-12-31T23:59:59Z",
        },
        "users": [
            {
                "id": 1,
                "name": "alice",
                "password": "alice_secret_456",
                "email": "alice@example.com",
            },
            {
                "id": 2,
                "name": "bob",
                "password": "bob_secret_789",
                "email": "bob@example.com",
            },
        ],
        "config": {
            "debug": True,
            "secret_key": "super_secret_key_123",
            "database": {"url": "postgresql://user:pass@localhost/db", "pool_size": 10},
        },
        "public_info": {
            "version": "1.0.0",
            "status": "healthy",
            "timestamp": "2024-01-15T10:30:00Z",
        },
    }


def demonstrate_redaction():
    """Demonstrate different redaction approaches."""

    print("=" * 80)
    print("FIELD REDACTION DEMONSTRATION")
    print("=" * 80)

    # Sample data with sensitive information
    data = create_sample_data()

    print("\n1. NO REDACTION (Original data)")
    print("-" * 50)
    log.info("user_login", user_data=data)

    print("\n2. PATTERN-BASED REDACTION")
    print("-" * 50)
    # Configure pattern-based redaction
    settings = LoggingSettings(
        redact_patterns=[r"(?i)password", r"(?i)token", r"(?i)secret"]
    )
    configure_logging(settings=settings)
    log.info("user_login_with_pattern_redaction", user_data=data)

    print("\n3. FIELD-BASED REDACTION")
    print("-" * 50)
    # Configure field-based redaction
    settings = LoggingSettings(
        redact_fields=[
            "user.password",
            "user.profile.api_key",
            "auth.token",
            "auth.refresh_token",
            "users.password",
            "config.secret_key",
            "config.database.url",
        ],
        redact_replacement="***REDACTED***",
    )
    configure_logging(settings=settings)
    log.info("user_login_with_field_redaction", user_data=data)

    print("\n4. COMBINED REDACTION (Pattern + Field)")
    print("-" * 50)
    # Configure both approaches
    settings = LoggingSettings(
        redact_patterns=[r"(?i)password", r"(?i)token", r"(?i)secret"],
        redact_fields=[
            "user.profile.api_key",
            "auth.refresh_token",
            "config.database.url",
        ],
        redact_replacement="[SENSITIVE]",
    )
    configure_logging(settings=settings)
    log.info("user_login_with_combined_redaction", user_data=data)

    print("\n5. ENVIRONMENT-BASED REDACTION")
    print("-" * 50)
    # Set environment variables for redaction
    os.environ["FAPILOG_REDACT_FIELDS"] = "user.password,auth.token,config.secret_key"
    os.environ["FAPILOG_REDACT_REPLACEMENT"] = "🔒"

    configure_logging()
    log.info("user_login_with_env_redaction", user_data=data)


def demonstrate_nested_redaction():
    """Demonstrate redaction of deeply nested fields."""

    print("\n" + "=" * 80)
    print("NESTED FIELD REDACTION DEMONSTRATION")
    print("=" * 80)

    # Complex nested data structure
    nested_data = {
        "organization": {
            "id": "org_123",
            "name": "Acme Corp",
            "settings": {
                "security": {
                    "api_keys": {
                        "stripe": "sk_live_abc123def456",
                        "aws": "AKIAIOSFODNN7EXAMPLE",
                        "gcp": "AIzaSyC1on0YzJjXjXjXjXjXjXjXjXjXjXjXjXj",
                    },
                    "passwords": {
                        "admin": "admin_secret_123",
                        "service": "service_secret_456",
                    },
                },
                "features": {"enabled": True, "beta_features": False},
            },
            "departments": [
                {
                    "id": "dept_1",
                    "name": "Engineering",
                    "manager": {
                        "id": 101,
                        "name": "Alice Smith",
                        "email": "alice@acme.com",
                        "password": "alice_password_123",
                    },
                },
                {
                    "id": "dept_2",
                    "name": "Sales",
                    "manager": {
                        "id": 102,
                        "name": "Bob Johnson",
                        "email": "bob@acme.com",
                        "password": "bob_password_456",
                    },
                },
            ],
        }
    }

    print("\n1. REDACTING DEEP NESTED FIELDS")
    print("-" * 50)
    settings = LoggingSettings(
        redact_fields=[
            "organization.settings.security.api_keys.stripe",
            "organization.settings.security.api_keys.aws",
            "organization.settings.security.passwords.admin",
            "organization.departments.manager.password",
        ],
        redact_replacement="🔐",
    )
    configure_logging(settings=settings)
    log.info("organization_data", org_data=nested_data)


def demonstrate_list_redaction():
    """Demonstrate redaction within lists of dictionaries."""

    print("\n" + "=" * 80)
    print("LIST REDACTION DEMONSTRATION")
    print("=" * 80)

    # Data with lists containing sensitive information
    list_data = {
        "api_keys": [
            {"name": "stripe", "key": "sk_live_abc123def456", "active": True},
            {"name": "aws", "key": "AKIAIOSFODNN7EXAMPLE", "active": True},
            {
                "name": "gcp",
                "key": "AIzaSyC1on0YzJjXjXjXjXjXjXjXjXjXjXjXjXj",
                "active": False,
            },
        ],
        "users": [
            {
                "id": 1,
                "name": "alice",
                "password": "alice_secret",
                "email": "alice@example.com",
            },
            {
                "id": 2,
                "name": "bob",
                "password": "bob_secret",
                "email": "bob@example.com",
            },
            {
                "id": 3,
                "name": "charlie",
                "password": "charlie_secret",
                "email": "charlie@example.com",
            },
        ],
        "config": {"debug": True, "secret_key": "super_secret_123"},
    }

    print("\n1. REDACTING FIELDS IN LISTS")
    print("-" * 50)
    settings = LoggingSettings(
        redact_fields=["api_keys.key", "users.password", "config.secret_key"],
        redact_replacement="***",
    )
    configure_logging(settings=settings)
    log.info("list_data_with_redaction", data=list_data)


def demonstrate_level_aware_field_redaction():
    """Demonstrate level-aware field redaction functionality."""
    print("\n" + "=" * 80)
    print("LEVEL-AWARE FIELD REDACTION")
    print("=" * 80)
    print("Redaction can be configured to respect log levels:")
    print("• DEBUG logs: No redaction (full context for debugging)")
    print("• INFO+ logs: Redaction applied (sensitive data protected)")
    print("=" * 80)

    # Sample data for level-aware demonstration
    test_data = {
        "user": {
            "name": "test_user",
            "password": "secret_password_123",
            "api_key": "sk_test_abc123def456",
        }
    }

    # Configure field redaction with level awareness
    settings = LoggingSettings(
        level="DEBUG",  # Show DEBUG logs
        redact_level="INFO",  # Only redact at INFO level and above
        redact_fields=["user.password", "user.api_key"],
        redact_replacement="[HIDDEN]",
        json_console="pretty",
        queue_enabled=False,
    )
    configure_logging(settings=settings)

    print("\n1. DEBUG Level (NO redaction - full context preserved):")
    print("-" * 50)
    log.debug("User authentication debug", user_data=test_data)

    print("\n2. INFO Level (WITH redaction - sensitive data protected):")
    print("-" * 50)
    log.info("User authentication info", user_data=test_data)

    print("\n3. ERROR Level (WITH redaction - sensitive data protected):")
    print("-" * 50)
    log.error("User authentication error", user_data=test_data)

    print("\n" + "✓" * 60)
    print("✓ Level-aware redaction provides flexible security controls")
    print("✓ DEBUG logs preserve full context for development debugging")
    print("✓ INFO+ logs protect sensitive data for production compliance")
    print("✓ Perfect for different environments (dev vs staging vs prod)")
    print("\nFor comprehensive level-aware redaction examples, see:")
    print("examples/21_level_aware_redaction.py")


if __name__ == "__main__":
    print("Field Redaction Example")
    print("This example demonstrates how to redact sensitive fields from log output.")
    print("Each section shows different redaction approaches and their effects.\n")

    # Demonstrate various redaction scenarios
    demonstrate_redaction()
    demonstrate_nested_redaction()
    demonstrate_list_redaction()
    demonstrate_level_aware_field_redaction()

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("✓ Pattern-based redaction: Use regex patterns to catch sensitive data")
    print("✓ Field-based redaction: Use exact field names with dot notation")
    print(
        "✓ Nested field support: Redact fields at any depth (e.g., user.profile.api_key)"
    )
    print("✓ List support: Automatically redact fields within lists of dictionaries")
    print("✓ Custom replacement: Configure the replacement value (default: 'REDACTED')")
    print(
        "✓ Environment variables: Configure via FAPILOG_REDACT_FIELDS and FAPILOG_REDACT_REPLACEMENT"
    )
    print(
        "✓ Non-destructive: Original data is never modified, only log output is redacted"
    )
    print("✓ Performance: Zero impact on application performance")
    print(
        "\nPerfect for GDPR compliance, security auditing, and protecting sensitive user data!"
    )
    print(
        "\nFor automatic PII detection and redaction, see examples/20_automatic_pii_redaction.py"
    )
