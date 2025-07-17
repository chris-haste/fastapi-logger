#!/usr/bin/env python3
"""
Automatic PII Redaction Example

This example demonstrates the automatic PII (Personally Identifiable Information)
redaction feature in fapilog. It shows how the logger can automatically detect
and redact common sensitive patterns like email addresses, credit card numbers,
phone numbers, and IP addresses without manual configuration.

Key features:
- Automatic detection of common PII patterns
- Recursive scanning of all string values
- Configurable patterns and replacement text
- Opt-out capability for specific use cases
- Built-in patterns for emails, credit cards, phones, and IPs
"""

import os
from typing import Any, Dict

from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings


def create_sample_data_with_pii() -> Dict[str, Any]:
    """Create sample data with various PII patterns for demonstration."""
    return {
        "user": {
            "id": 12345,
            "name": "John Doe",
            "email": "john.doe@example.com",
            "phone": "+1-555-123-4567",
            "profile": {
                "contact": {
                    "work_email": "john.doe@company.com",
                    "personal_email": "john.doe@gmail.com",
                    "mobile": "(555) 987-6543",
                    "home_phone": "555-111-2222",
                },
                "address": "123 Main St, City, State 12345",
                "preferences": {"theme": "dark", "language": "en"},
            },
        },
        "payment": {
            "card_number": "4111-1111-1111-1111",
            "expiry": "12/25",
            "cvv": "123",
            "billing_email": "billing@example.com",
        },
        "network": {
            "client_ip": "192.168.1.100",
            "server_ip": "10.0.0.1",
            "gateway": "172.16.0.1",
            "dns_servers": ["8.8.8.8", "1.1.1.1"],
        },
        "support_ticket": {
            "id": "TICKET-12345",
            "customer_email": "customer@example.com",
            "phone_contact": "+1-800-555-0123",
            "description": "Customer called from 192.168.1.50 about payment issue",
            "payment_info": "Card ending in 1234",
        },
        "api_requests": [
            {
                "endpoint": "/api/users",
                "client_ip": "203.0.113.1",
                "user_email": "api_user@example.com",
                "request_data": {
                    "email": "new_user@example.com",
                    "phone": "555-123-4567",
                },
            },
            {
                "endpoint": "/api/payments",
                "client_ip": "198.51.100.1",
                "payment_data": {
                    "card_number": "5555-5555-5555-4444",
                    "billing_email": "payment@example.com",
                },
            },
        ],
        "logs": [
            "Error occurred for user john.doe@example.com at 192.168.1.100",
            "Payment processed for card 4111-1111-1111-1111",
            "Contact support at support@example.com or call 1-800-555-0123",
        ],
    }


def demonstrate_automatic_pii_redaction():
    """Demonstrate automatic PII redaction functionality."""

    print("=" * 80)
    print("AUTOMATIC PII REDACTION DEMONSTRATION")
    print("=" * 80)

    # Sample data with various PII patterns
    data = create_sample_data_with_pii()

    print("\n1. NO PII REDACTION (Original data)")
    print("-" * 50)
    # Disable automatic PII redaction
    settings = LoggingSettings(enable_auto_redact_pii=False)
    configure_logging(settings=settings)
    log.info("user_data_without_pii_redaction", user_data=data)

    print("\n2. AUTOMATIC PII REDACTION (Default)")
    print("-" * 50)
    # Enable automatic PII redaction with default patterns
    settings = LoggingSettings(enable_auto_redact_pii=True)
    configure_logging(settings=settings)
    log.info("user_data_with_auto_pii_redaction", user_data=data)

    print("\n3. CUSTOM PII REDACTION PATTERNS")
    print("-" * 50)
    # Add custom patterns to the built-in ones
    settings = LoggingSettings(
        enable_auto_redact_pii=True,
        custom_pii_patterns=[
            r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",  # 16-digit card numbers
            r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b",  # IBAN-like patterns
            r"\b\d{3}-\d{2}-\d{4}\b",  # SSN pattern
        ],
    )
    configure_logging(settings=settings)
    log.info("user_data_with_custom_patterns", user_data=data)

    print("\n4. CUSTOM REDACTION REPLACEMENT")
    print("-" * 50)
    # Use custom replacement text
    settings = LoggingSettings(
        enable_auto_redact_pii=True,
        redact_replacement="[PII_REDACTED]",
    )
    configure_logging(settings=settings)
    log.info("user_data_with_custom_replacement", user_data=data)

    print("\n5. ENVIRONMENT-BASED CONFIGURATION")
    print("-" * 50)
    # Configure via environment variables
    os.environ["FAPILOG_ENABLE_AUTO_REDACT_PII"] = "true"
    os.environ["FAPILOG_REDACT_REPLACEMENT"] = "🔒"
    os.environ["FAPILOG_CUSTOM_PII_PATTERNS"] = r"\b\d{3}-\d{2}-\d{4}\b"

    configure_logging()
    log.info("user_data_with_env_config", user_data=data)


def demonstrate_pii_patterns():
    """Demonstrate different PII patterns and their detection."""

    print("\n" + "=" * 80)
    print("PII PATTERN DETECTION DEMONSTRATION")
    print("=" * 80)

    # Test different PII patterns
    test_data = {
        "emails": [
            "simple@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org",
            "test.email@subdomain.example.com",
        ],
        "credit_cards": [
            "4111-1111-1111-1111",
            "5555 5555 5555 4444",
            "378282246310005",
            "6011111111111117",
        ],
        "phone_numbers": [
            "+1-555-123-4567",
            "(555) 123-4567",
            "555.123.4567",
            "555-123-4567",
            "+44 20 7946 0958",
        ],
        "ip_addresses": [
            "192.168.1.1",
            "10.0.0.1",
            "172.16.0.1",
            "203.0.113.1",
            "198.51.100.1",
        ],
        "mixed_content": [
            "Contact john@example.com or call 555-123-4567",
            "Payment card 4111-1111-1111-1111 from 192.168.1.100",
            "Support: support@example.com, Phone: +1-800-555-0123",
        ],
    }

    print("\n1. TESTING BUILT-IN PII PATTERNS")
    print("-" * 50)
    settings = LoggingSettings(enable_auto_redact_pii=True)
    configure_logging(settings=settings)
    log.info("pii_pattern_test", test_data=test_data)


def demonstrate_recursive_redaction():
    """Demonstrate recursive PII redaction in complex nested structures."""

    print("\n" + "=" * 80)
    print("RECURSIVE PII REDACTION DEMONSTRATION")
    print("=" * 80)

    # Complex nested data with PII scattered throughout
    complex_data = {
        "organization": {
            "id": "org_123",
            "name": "Acme Corp",
            "contact": {
                "primary_email": "contact@acme.com",
                "support_email": "support@acme.com",
                "phone": "+1-800-555-0123",
            },
            "departments": [
                {
                    "id": "dept_1",
                    "name": "Engineering",
                    "manager": {
                        "name": "Alice Smith",
                        "email": "alice@acme.com",
                        "phone": "555-123-4567",
                    },
                    "projects": [
                        {
                            "name": "Project Alpha",
                            "lead_email": "alpha@acme.com",
                            "client_contact": "client@example.com",
                        }
                    ],
                },
                {
                    "id": "dept_2",
                    "name": "Sales",
                    "manager": {
                        "name": "Bob Johnson",
                        "email": "bob@acme.com",
                        "phone": "555-987-6543",
                    },
                    "customers": [
                        {
                            "name": "Customer A",
                            "email": "customer.a@example.com",
                            "phone": "555-111-2222",
                            "payment_info": "Card ending in 1234",
                        }
                    ],
                },
            ],
            "network": {
                "servers": [
                    {"name": "web-01", "ip": "192.168.1.10"},
                    {"name": "db-01", "ip": "192.168.1.20"},
                ],
                "vpn_clients": [
                    {"user": "alice@acme.com", "ip": "203.0.113.1"},
                    {"user": "bob@acme.com", "ip": "198.51.100.1"},
                ],
            },
        },
        "logs": [
            "User alice@acme.com accessed from 192.168.1.100",
            "Payment processed for customer@example.com",
            "Support ticket from support@example.com regarding 555-123-4567",
        ],
    }

    print("\n1. COMPLEX NESTED STRUCTURE WITH PII")
    print("-" * 50)
    settings = LoggingSettings(enable_auto_redact_pii=True)
    configure_logging(settings=settings)
    log.info("complex_data_with_pii", org_data=complex_data)


def demonstrate_opt_out_scenarios():
    """Demonstrate scenarios where automatic PII redaction might be disabled."""

    print("\n" + "=" * 80)
    print("OPT-OUT SCENARIOS DEMONSTRATION")
    print("=" * 80)

    # Data that might need to preserve PII for debugging/audit
    audit_data = {
        "debug_info": {
            "user_email": "debug@example.com",
            "client_ip": "192.168.1.100",
            "error_context": "Error occurred for user@example.com",
        },
        "audit_trail": [
            "User admin@example.com performed action at 2024-01-15T10:30:00Z",
            "Payment card 4111-1111-1111-1111 processed successfully",
            "Support contact: support@example.com, Phone: 555-123-4567",
        ],
    }

    print("\n1. AUDIT LOGGING (PII Redaction Disabled)")
    print("-" * 50)
    # Disable PII redaction for audit logging
    settings = LoggingSettings(enable_auto_redact_pii=False)
    configure_logging(settings=settings)
    log.info("audit_log_with_pii", audit_data=audit_data)

    print("\n2. PRODUCTION LOGGING (PII Redaction Enabled)")
    print("-" * 50)
    # Enable PII redaction for production
    settings = LoggingSettings(enable_auto_redact_pii=True)
    configure_logging(settings=settings)
    log.info("production_log_with_redaction", audit_data=audit_data)


if __name__ == "__main__":
    print("Automatic PII Redaction Example")
    print(
        "This example demonstrates automatic detection and redaction of PII patterns."
    )
    print(
        "The logger automatically scans all string values for common sensitive patterns.\n"
    )

    # Demonstrate various PII redaction scenarios
    demonstrate_automatic_pii_redaction()
    demonstrate_pii_patterns()
    demonstrate_recursive_redaction()
    demonstrate_opt_out_scenarios()

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("✓ Automatic detection: Scans all string values for PII patterns")
    print("✓ Built-in patterns: Email, credit card, phone, and IP addresses")
    print("✓ Recursive scanning: Works on nested dictionaries and lists")
    print("✓ Custom patterns: Add your own regex patterns via settings")
    print("✓ Configurable replacement: Customize the redaction placeholder")
    print("✓ Opt-out capability: Disable for specific use cases (audit, debug)")
    print("✓ Environment configuration: Configure via environment variables")
    print("✓ Performance optimized: Minimal impact on logging performance")
    print("✓ Non-destructive: Original data is never modified")
    print(
        "✓ Level-aware: Respects FAPILOG_REDACT_LEVEL setting (DEBUG bypass, INFO+ redacted)"
    )
    print(
        "\nPerfect for GDPR compliance, security auditing, and protecting sensitive data automatically!"
    )
    print(
        "\nFor level-aware redaction examples, see examples/21_level_aware_redaction.py"
    )
