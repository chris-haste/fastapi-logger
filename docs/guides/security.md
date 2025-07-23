# Security & Redaction Guide

**Complete guide to data protection, PII redaction, and compliance with Fapilog.**

Protect sensitive data with fapilog's comprehensive redaction system. From automatic PII detection to custom compliance patterns, this guide covers everything you need to secure your logs and meet regulatory requirements.

---

## Quick Navigation

**Jump to what you need:**

- **🚀 [Quick Start](#quick-start)** - Basic security setup in 60 seconds
- **🔍 [Field Redaction](#field-based-redaction)** - Redact specific fields by name
- **🎯 [Pattern Redaction](#pattern-based-redaction)** - Regex patterns for sensitive data
- **🤖 [Automatic PII](#automatic-pii-detection)** - Built-in detection for common PII
- **📊 [Level-Aware Redaction](#level-aware-redaction)** - Different rules per log level
- **⚖️ [Compliance Patterns](#compliance-patterns)** - GDPR, HIPAA, PCI DSS frameworks
- **🎨 [Custom Security](#custom-security-patterns)** - Domain-specific protection
- **🌍 [Real-World Examples](#real-world-examples)** - Production security configurations
- **⚠️ [Troubleshooting](#troubleshooting)** - Common security issues

[↑ Back to top](#security--redaction-guide)

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Redaction System Overview](#redaction-system-overview)
3. [Field-Based Redaction](#field-based-redaction)
4. [Pattern-Based Redaction](#pattern-based-redaction)
5. [Automatic PII Detection](#automatic-pii-detection)
6. [Level-Aware Redaction](#level-aware-redaction)
7. [Compliance Patterns](#compliance-patterns)
8. [Custom Security Patterns](#custom-security-patterns)
9. [Real-World Examples](#real-world-examples)
10. [Performance & Testing](#performance--testing)
11. [Troubleshooting](#troubleshooting)

[↑ Back to top](#security--redaction-guide)

---

## Quick Start

### Basic Security Setup

**Enable comprehensive data protection in 3 lines:**

```python
from fapilog import configure_logging
from fapilog.settings import LoggingSettings

# Basic security configuration
settings = LoggingSettings(
    # Automatic PII detection
    enable_auto_redact_pii=True,

    # Field-based redaction
    redact_fields=["password", "token", "api_key"],

    # Pattern-based redaction
    redact_patterns=["secret", "private_key"]
)

configure_logging(settings=settings)
```

### Environment Variable Setup

**Production-ready security via environment variables:**

```bash
# Enable automatic PII redaction
export FAPILOG_ENABLE_AUTO_REDACT_PII=true

# Redact specific fields
export FAPILOG_REDACT_FIELDS=user.password,authorization,x-api-key

# Redact sensitive patterns
export FAPILOG_REDACT_PATTERNS=password,token,secret,api_key

# Set redaction level
export FAPILOG_REDACT_LEVEL=INFO
```

### Before and After Example

**See redaction in action:**

```python
from fapilog import log

# Without redaction
user_data = {
    "username": "john_doe",
    "password": "secret123",
    "email": "john@example.com",
    "credit_card": "4532-1234-5678-9012"
}

log.info("User registration", user_data=user_data)
```

**Output without redaction:**

```json
{
  "event": "User registration",
  "user_data": {
    "username": "john_doe",
    "password": "secret123",
    "email": "john@example.com",
    "credit_card": "4532-1234-5678-9012"
  }
}
```

**Output with redaction:**

```json
{
  "event": "User registration",
  "user_data": {
    "username": "john_doe",
    "password": "REDACTED",
    "email": "REDACTED",
    "credit_card": "REDACTED"
  }
}
```

[↑ Back to top](#security--redaction-guide)

---

## Redaction System Overview

Fapilog provides a **multi-layered redaction system** that works together to protect sensitive data:

### Redaction Layers

1. **Field-Based Redaction** - Redact specific fields by exact name
2. **Pattern-Based Redaction** - Redact values matching regex patterns
3. **Automatic PII Detection** - Built-in detection for common PII types
4. **Level-Aware Redaction** - Apply different rules based on log level

### Processing Order

```
Log Event → Field Redaction → Pattern Redaction → PII Detection → Output
```

**Why this order matters:**

- **Field redaction first** - Fastest, most precise
- **Pattern redaction second** - Catches field names and values
- **PII detection last** - Comprehensive safety net

### Configuration Hierarchy

```python
settings = LoggingSettings(
    # 1. Field-based (most precise)
    redact_fields=["user.password", "api_key"],

    # 2. Pattern-based (flexible)
    redact_patterns=["secret", "token"],

    # 3. Automatic PII (comprehensive)
    enable_auto_redact_pii=True,
    custom_pii_patterns=["employee_id"],

    # 4. Level control (context-aware)
    redact_level="INFO"  # Skip DEBUG logs
)
```

### Common Settings

| Setting                  | Purpose            | Example                      |
| ------------------------ | ------------------ | ---------------------------- |
| `redact_fields`          | Exact field names  | `["password", "user.token"]` |
| `redact_patterns`        | Regex patterns     | `["secret", r"api[_-]?key"]` |
| `enable_auto_redact_pii` | Auto PII detection | `True`                       |
| `redact_replacement`     | Replacement value  | `"***REDACTED***"`           |
| `redact_level`           | Minimum level      | `"INFO"`                     |

[↑ Back to top](#security--redaction-guide)

---

## Field-Based Redaction

**Precise redaction by field name with dot notation support.**

### Basic Field Redaction

**Redact top-level fields:**

```python
settings = LoggingSettings(
    redact_fields=["password", "api_key", "secret_token"]
)

# These fields will be redacted regardless of value
log.info("User data", password="secret123", api_key="key_abc")
# Output: {"password": "REDACTED", "api_key": "REDACTED"}
```

### Nested Field Redaction

**Use dot notation for nested structures:**

```python
settings = LoggingSettings(
    redact_fields=[
        "user.password",           # user.password field
        "auth.token",              # auth.token field
        "config.database.password", # deeply nested
        "request.headers.authorization"
    ]
)

user_data = {
    "user": {
        "username": "john",
        "password": "secret123",    # Will be redacted
        "profile": {
            "email": "john@example.com"  # Not redacted
        }
    },
    "auth": {
        "token": "abc123",          # Will be redacted
        "expires": "2024-12-31"     # Not redacted
    }
}

log.info("User login", data=user_data)
```

**Output:**

```json
{
  "data": {
    "user": {
      "username": "john",
      "password": "REDACTED",
      "profile": {
        "email": "john@example.com"
      }
    },
    "auth": {
      "token": "REDACTED",
      "expires": "2024-12-31"
    }
  }
}
```

### List and Array Support

**Automatic redaction within lists:**

```python
settings = LoggingSettings(
    redact_fields=["users.password", "tokens.value"]
)

data = {
    "users": [
        {"username": "john", "password": "secret1"},
        {"username": "jane", "password": "secret2"}
    ],
    "tokens": [
        {"name": "api", "value": "token123"},
        {"name": "refresh", "value": "refresh456"}
    ]
}

log.info("Bulk operation", data=data)
```

**Output:**

```json
{
  "data": {
    "users": [
      { "username": "john", "password": "REDACTED" },
      { "username": "jane", "password": "REDACTED" }
    ],
    "tokens": [
      { "name": "api", "value": "REDACTED" },
      { "name": "refresh", "value": "REDACTED" }
    ]
  }
}
```

### Environment Variable Configuration

**Configure field redaction via environment:**

```bash
# Single field
export FAPILOG_REDACT_FIELDS=password

# Multiple fields (comma-separated)
export FAPILOG_REDACT_FIELDS=password,api_key,secret_token

# Nested fields
export FAPILOG_REDACT_FIELDS=user.password,auth.token,config.database.url

# Custom replacement
export FAPILOG_REDACT_REPLACEMENT=***SENSITIVE***
```

### Field Redaction Examples

**Common field patterns:**

```python
# Authentication fields
auth_fields = [
    "password", "token", "refresh_token", "api_key",
    "secret", "private_key", "certificate"
]

# User data fields
user_fields = [
    "user.password", "user.ssn", "user.credit_card",
    "profile.phone", "profile.address", "profile.dob"
]

# Request/response fields
request_fields = [
    "request.headers.authorization",
    "request.headers.x-api-key",
    "response.body.access_token",
    "headers.cookie"
]

# Database fields
database_fields = [
    "config.database.password",
    "config.redis.auth",
    "connection.credentials"
]

settings = LoggingSettings(
    redact_fields=auth_fields + user_fields + request_fields + database_fields
)
```

[↑ Back to top](#security--redaction-guide)

---

## Pattern-Based Redaction

**Flexible redaction using regex patterns to catch sensitive data by pattern.**

### Basic Pattern Redaction

**Redact based on field names or values:**

```python
settings = LoggingSettings(
    redact_patterns=[
        "password",     # Matches any field/value containing "password"
        "token",        # Matches any field/value containing "token"
        "secret",       # Matches any field/value containing "secret"
        "api[_-]?key"   # Matches "api_key", "api-key", "apikey"
    ]
)

# Pattern matching works on both field names and values
log.info("Auth data",
         user_password="secret123",      # Field name matches "password"
         access_token="abc123",          # Field name matches "token"
         config={"secret_key": "xyz789"} # Field name matches "secret"
)
```

### Advanced Regex Patterns

**Complex patterns for specific data types:**

```python
settings = LoggingSettings(
    redact_patterns=[
        # Credit card numbers (basic pattern)
        r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",

        # Social Security Numbers
        r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b",

        # Email addresses
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",

        # Phone numbers
        r"\b(?:\+?1[-.\s]?)?(?:\(?[0-9]{3}\)?[-.\s]?)?[0-9]{3}[-.\s]?[0-9]{4}\b",

        # IPv4 addresses
        r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b",

        # API keys (common formats)
        r"\b[A-Za-z0-9]{32,}\b",  # 32+ character alphanumeric strings

        # AWS keys
        r"AKIA[0-9A-Z]{16}",      # AWS Access Key format

        # JWT tokens
        r"eyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]*"
    ]
)
```

### Case-Insensitive Patterns

**Pattern matching is case-insensitive by default:**

```python
settings = LoggingSettings(
    redact_patterns=["password", "token", "secret"]
)

# All of these will be redacted:
log.info("Mixed case",
         Password="secret123",        # Uppercase P
         ACCESS_TOKEN="abc123",       # All uppercase
         Secret_Key="xyz789",         # Mixed case
         user_password="sensitive"    # Lowercase
)
```

### Environment Variable Configuration

**Configure patterns via environment variables:**

```bash
# Basic patterns
export FAPILOG_REDACT_PATTERNS=password,token,secret,api_key

# Complex patterns (escape special characters)
export FAPILOG_REDACT_PATTERNS="password,token,\d{4}-\d{4}-\d{4}-\d{4}"

# Financial patterns
export FAPILOG_REDACT_PATTERNS="ssn,credit_card,\b\d{3}-\d{2}-\d{4}\b"
```

### Pattern Examples by Domain

**Industry-specific pattern collections:**

```python
# Financial Services
financial_patterns = [
    r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",  # Credit cards
    r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b",             # SSN
    r"\b\d{9}\b",                                    # Tax ID
    r"IBAN[A-Z0-9]{15,34}",                         # IBAN
    r"[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?",          # BIC/SWIFT
    "account_number", "routing_number", "cvv"
]

# Healthcare
healthcare_patterns = [
    r"\b\d{3}-\d{2}-\d{4}\b",        # SSN
    r"MRN\d{6,10}",                   # Medical Record Numbers
    r"\b\d{10}\b",                    # Patient ID
    "patient_id", "medical_record", "diagnosis"
]

# Technology
tech_patterns = [
    r"AKIA[0-9A-Z]{16}",              # AWS Access Keys
    r"sk-[a-zA-Z0-9]{48}",            # OpenAI API keys
    r"ghp_[a-zA-Z0-9]{36}",           # GitHub tokens
    r"xoxb-[0-9]{11}-[0-9]{11}-[a-zA-Z0-9]{24}",  # Slack tokens
    "api_key", "secret_key", "private_key"
]

# Choose patterns for your domain
settings = LoggingSettings(redact_patterns=financial_patterns)
```

[↑ Back to top](#security--redaction-guide)

---

## Automatic PII Detection

**Built-in detection and redaction of common personally identifiable information.**

### Enable Automatic PII Detection

**Zero-configuration PII protection:**

```python
settings = LoggingSettings(
    enable_auto_redact_pii=True  # Enable automatic PII detection
)

# Automatically detects and redacts common PII
log.info("User contact",
         email="john@example.com",           # Automatically redacted
         phone="+1-555-123-4567",            # Automatically redacted
         credit_card="4532-1234-5678-9012",  # Automatically redacted
         ip_address="192.168.1.100"          # Automatically redacted
)
```

### Built-in PII Patterns

**Fapilog automatically detects these PII types:**

| PII Type        | Pattern                                                          | Example               |
| --------------- | ---------------------------------------------------------------- | --------------------- |
| **Email**       | `[\w\.-]+@[\w\.-]+\.\w+`                                         | `john@example.com`    |
| **Phone**       | `(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}` | `+1-555-123-4567`     |
| **Credit Card** | `\b\d{4}(?:[ -]?\d{4}){3}\b`                                     | `4532-1234-5678-9012` |
| **SSN**         | `\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b`                                | `123-45-6789`         |
| **IPv4**        | `\b(?:\d{1,3}\.){3}\d{1,3}\b`                                    | `192.168.1.100`       |

### Custom PII Patterns

**Add domain-specific PII patterns:**

```python
settings = LoggingSettings(
    enable_auto_redact_pii=True,
    custom_pii_patterns=[
        # Employee IDs
        r"EMP-\d{6}",

        # Customer numbers
        r"CUST\d{8}",

        # License plates
        r"\b[A-Z]{2,3}[-\s]?\d{3,4}\b",

        # Passport numbers
        r"\b[A-Z]\d{8}\b",

        # Driver's license
        r"\b[A-Z]\d{7,8}\b"
    ]
)
```

### Environment Variable Configuration

**Configure PII detection via environment:**

```bash
# Enable automatic PII detection
export FAPILOG_ENABLE_AUTO_REDACT_PII=true

# Add custom PII patterns
export FAPILOG_CUSTOM_PII_PATTERNS=employee_id,customer_number,license_plate

# Set custom replacement
export FAPILOG_REDACT_REPLACEMENT=[PII_REDACTED]
```

### PII Detection Examples

**Real-world PII detection scenarios:**

```python
# Customer service scenario
customer_data = {
    "name": "John Doe",
    "email": "john.doe@email.com",      # Auto-detected PII
    "phone": "(555) 123-4567",          # Auto-detected PII
    "address": "123 Main St",
    "ssn": "123-45-6789",               # Auto-detected PII
    "account": "ACCT-12345678"
}

# Payment processing scenario
payment_data = {
    "amount": 99.99,
    "currency": "USD",
    "card_number": "4532 1234 5678 9012",  # Auto-detected PII
    "cvv": "123",
    "email": "customer@shop.com"            # Auto-detected PII
}

# System logs scenario
system_logs = {
    "user_ip": "192.168.1.100",         # Auto-detected PII
    "user_agent": "Mozilla/5.0...",
    "session_id": "sess_abc123",
    "email": "admin@company.com"        # Auto-detected PII
}

# All PII automatically redacted
log.info("Customer interaction", customer=customer_data)
log.info("Payment processed", payment=payment_data)
log.info("User session", logs=system_logs)
```

### Disabling PII Detection

**Disable for development or specific use cases:**

```python
# Disable automatic PII detection
settings = LoggingSettings(
    enable_auto_redact_pii=False  # Disable for debugging
)

# Or disable via environment
# export FAPILOG_ENABLE_AUTO_REDACT_PII=false
```

### PII Performance Considerations

**PII detection runs on all string values:**

```python
# For high-volume applications, consider:
settings = LoggingSettings(
    enable_auto_redact_pii=True,
    redact_level="INFO",  # Skip DEBUG logs (performance)

    # Reduce custom patterns for performance
    custom_pii_patterns=["employee_id"]  # Only essential patterns
)
```

[↑ Back to top](#security--redaction-guide)

---

## Level-Aware Redaction

**Apply different redaction rules based on log level for development vs production.**

### Basic Level-Aware Redaction

**Skip redaction in DEBUG for development:**

```python
settings = LoggingSettings(
    redact_level="INFO",  # Only redact INFO and above
    redact_fields=["password", "token"],
    enable_auto_redact_pii=True
)

# DEBUG logs - NOT redacted (full context for debugging)
log.debug("Debug user data", user={"password": "secret123"})
# Output: {"user": {"password": "secret123"}}

# INFO logs - REDACTED (protected in production)
log.info("User login", user={"password": "secret123"})
# Output: {"user": {"password": "REDACTED"}}
```

### Log Level Hierarchy

**Standard Python logging levels:**

| Level        | Numeric | Redacted | Use Case              |
| ------------ | ------- | -------- | --------------------- |
| **DEBUG**    | 10      | ❌ No    | Development debugging |
| **INFO**     | 20      | ✅ Yes   | General information   |
| **WARNING**  | 30      | ✅ Yes   | Warning conditions    |
| **ERROR**    | 40      | ✅ Yes   | Error conditions      |
| **CRITICAL** | 50      | ✅ Yes   | Critical failures     |

### Environment-Specific Configuration

**Different redaction levels per environment:**

```python
import os

# Development environment - no redaction
if os.getenv("ENVIRONMENT") == "development":
    settings = LoggingSettings(
        redact_level="CRITICAL",  # Only redact CRITICAL (basically never)
        enable_auto_redact_pii=False
    )

# Staging environment - redact WARNING+
elif os.getenv("ENVIRONMENT") == "staging":
    settings = LoggingSettings(
        redact_level="WARNING",   # Redact WARNING and above
        enable_auto_redact_pii=True
    )

# Production environment - redact INFO+
else:
    settings = LoggingSettings(
        redact_level="INFO",      # Redact INFO and above
        enable_auto_redact_pii=True,
        redact_patterns=["password", "token", "secret"]
    )
```

### Environment Variable Configuration

**Configure redaction level via environment:**

```bash
# Development
export FAPILOG_REDACT_LEVEL=DEBUG    # Redact all levels
export FAPILOG_REDACT_LEVEL=CRITICAL # Redact only CRITICAL (never)

# Production
export FAPILOG_REDACT_LEVEL=INFO     # Redact INFO and above (default)
export FAPILOG_REDACT_LEVEL=WARNING  # Redact WARNING and above
```

### Level-Aware Examples

**Practical level-aware redaction scenarios:**

```python
# Configure for development debugging
settings = LoggingSettings(
    redact_level="CRITICAL",  # No redaction for debugging
    redact_fields=["password", "api_key"]
)

configure_logging(settings=settings)

# Development debugging - full context preserved
log.debug("Authentication attempt",
          username="john",
          password="secret123",    # NOT redacted in DEBUG
          api_key="key_abc123")    # NOT redacted in DEBUG

# Production logging - sensitive data protected
log.info("User authenticated",
         username="john",
         password="secret123",     # REDACTED in INFO
         api_key="key_abc123")     # REDACTED in INFO

log.error("Authentication failed",
          username="john",
          password="wrong_pass",    # REDACTED in ERROR
          reason="invalid_credentials")
```

### Testing Level-Aware Redaction

**Verify redaction behavior across levels:**

```python
def test_level_aware_redaction():
    """Test redaction at different log levels."""

    settings = LoggingSettings(
        redact_level="INFO",
        redact_fields=["password"]
    )

    configure_logging(settings=settings)

    sensitive_data = {"password": "secret123"}

    # DEBUG - should NOT be redacted
    log.debug("Debug data", data=sensitive_data)

    # INFO - should be redacted
    log.info("Info data", data=sensitive_data)

    # ERROR - should be redacted
    log.error("Error data", data=sensitive_data)
```

[↑ Back to top](#security--redaction-guide)

---

## Compliance Patterns

**Pre-configured patterns for regulatory compliance frameworks.**

### GDPR Compliance

**European privacy regulation compliance:**

```python
def gdpr_compliance_config():
    """GDPR-compliant logging configuration."""
    return LoggingSettings(
        # Comprehensive PII protection
        enable_auto_redact_pii=True,
        redact_level="DEBUG",  # Redact at all levels

        # GDPR-specific fields
        redact_fields=[
            # Personal identifiers
            "user.email", "user.phone", "user.address",
            "customer.name", "customer.dob", "customer.id",

            # Authentication data
            "password", "token", "session_id",

            # Profile data
            "profile.personal_info", "profile.preferences",
            "profile.tracking_data"
        ],

        # GDPR-specific patterns
        redact_patterns=[
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
            r"\b(?:\+\d{1,3}[-.\s]?)?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}\b",  # Phone
            r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",  # Payment cards
            "personal", "private", "confidential"
        ],

        # Strong replacement for audit trails
        redact_replacement="[GDPR_REDACTED]"
    )

# Use GDPR configuration
settings = gdpr_compliance_config()
configure_logging(settings=settings)
```

### HIPAA Compliance

**Healthcare privacy regulation compliance:**

```python
def hipaa_compliance_config():
    """HIPAA-compliant logging configuration."""
    return LoggingSettings(
        # Healthcare PII protection
        enable_auto_redact_pii=True,
        redact_level="DEBUG",

        # HIPAA-specific fields
        redact_fields=[
            # Patient identifiers
            "patient.name", "patient.dob", "patient.ssn",
            "patient.address", "patient.phone", "patient.email",
            "patient.mrn", "patient.id",

            # Medical data
            "diagnosis", "treatment", "medication",
            "medical_record", "insurance",

            # Provider data
            "provider.npi", "provider.dea", "provider.license"
        ],

        # HIPAA-specific patterns
        custom_pii_patterns=[
            r"MRN\d{6,10}",           # Medical Record Numbers
            r"NPI\d{10}",             # National Provider Identifier
            r"DEA[A-Z]{2}\d{7}",      # DEA Registration
            r"\b\d{3}-\d{2}-\d{4}\b", # SSN
            "patient", "medical", "health", "diagnosis"
        ],

        redact_replacement="[PHI_REDACTED]"  # Protected Health Information
    )

settings = hipaa_compliance_config()
configure_logging(settings=settings)
```

### PCI DSS Compliance

**Payment card industry compliance:**

```python
def pci_dss_compliance_config():
    """PCI DSS-compliant logging configuration."""
    return LoggingSettings(
        # Payment data protection
        enable_auto_redact_pii=True,
        redact_level="DEBUG",

        # PCI DSS-specific fields
        redact_fields=[
            # Payment card data
            "card_number", "cvv", "cvv2", "cvc", "expiry",
            "cardholder_name", "cardholder_data",

            # Authentication data
            "pin", "password", "magnetic_stripe",

            # Sensitive authentication data
            "full_track_data", "cav2", "cid", "cvc2"
        ],

        # PCI DSS-specific patterns
        redact_patterns=[
            # Primary Account Number (PAN) patterns
            r"\b4[0-9]{12}(?:[0-9]{3})?\b",      # Visa
            r"\b5[1-5][0-9]{14}\b",              # Mastercard
            r"\b3[47][0-9]{13}\b",               # American Express
            r"\b3[0-9]{13}\b",                   # Diners Club
            r"\b6(?:011|5[0-9]{2})[0-9]{12}\b",  # Discover

            # General card patterns
            r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",

            # Security codes
            r"\b\d{3,4}\b",  # CVV/CVC (be careful - may be too broad)

            # Keywords
            "card", "payment", "cvv", "pin", "magnetic"
        ],

        redact_replacement="[PCI_REDACTED]"
    )

settings = pci_dss_compliance_config()
configure_logging(settings=settings)
```

### SOX Compliance

**Financial reporting compliance:**

```python
def sox_compliance_config():
    """SOX-compliant logging configuration."""
    return LoggingSettings(
        # Financial data protection
        enable_auto_redact_pii=True,

        # SOX-specific fields
        redact_fields=[
            # Financial identifiers
            "account_number", "routing_number", "swift_code",
            "iban", "tax_id", "ein",

            # Trading data
            "portfolio", "trading_account", "investment_data",

            # Audit-sensitive fields
            "financial_statement", "earnings", "revenue"
        ],

        # SOX-specific patterns
        custom_pii_patterns=[
            r"\b\d{9}\b",                    # Tax ID/EIN
            r"IBAN[A-Z0-9]{15,34}",         # IBAN
            r"[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?",  # BIC/SWIFT
            "financial", "audit", "revenue", "earnings"
        ],

        redact_replacement="[SOX_REDACTED]"
    )
```

### Multi-Compliance Configuration

**Support multiple compliance frameworks:**

```python
def multi_compliance_config(frameworks: List[str]):
    """Configure for multiple compliance frameworks."""

    base_config = LoggingSettings(
        enable_auto_redact_pii=True,
        redact_level="INFO",
        redact_replacement="[COMPLIANCE_REDACTED]"
    )

    # Combine patterns from selected frameworks
    all_fields = []
    all_patterns = []

    if "gdpr" in frameworks:
        all_fields.extend(["user.email", "user.phone", "user.address"])
        all_patterns.extend(["personal", "private"])

    if "hipaa" in frameworks:
        all_fields.extend(["patient.name", "medical_record", "diagnosis"])
        all_patterns.extend(["patient", "medical", "health"])

    if "pci_dss" in frameworks:
        all_fields.extend(["card_number", "cvv", "cardholder_data"])
        all_patterns.extend([r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"])

    base_config.redact_fields = all_fields
    base_config.redact_patterns = all_patterns

    return base_config

# Configure for multiple frameworks
settings = multi_compliance_config(["gdpr", "pci_dss"])
configure_logging(settings=settings)
```

### Environment-Based Compliance

**Different compliance per environment:**

```bash
# Development - minimal compliance
export FAPILOG_COMPLIANCE_MODE=development
export FAPILOG_REDACT_LEVEL=CRITICAL

# Staging - moderate compliance
export FAPILOG_COMPLIANCE_MODE=staging
export FAPILOG_REDACT_LEVEL=INFO

# Production - full compliance
export FAPILOG_COMPLIANCE_MODE=gdpr,pci_dss
export FAPILOG_REDACT_LEVEL=DEBUG
export FAPILOG_REDACT_FIELDS=user.email,card_number,patient.name
```

[↑ Back to top](#security--redaction-guide)

---

## Custom Security Patterns

**Build domain-specific security patterns for your organization.**

### Custom Pattern Development

**Create organization-specific redaction patterns:**

```python
class OrganizationSecurity:
    """Custom security patterns for organization."""

    @staticmethod
    def employee_patterns():
        """Employee data protection patterns."""
        return [
            # Employee IDs
            r"EMP-\d{6}",
            r"E\d{6}",

            # Badge numbers
            r"BADGE-[A-Z0-9]{8}",

            # Internal phone extensions
            r"ext\s?\d{3,4}",

            # Department codes
            r"DEPT-[A-Z]{3}",

            # Salary information
            r"\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?",

            # Keywords
            "salary", "compensation", "performance_review"
        ]

    @staticmethod
    def customer_patterns():
        """Customer data protection patterns."""
        return [
            # Customer IDs
            r"CUST\d{8}",
            r"C-\d{6}-[A-Z]{2}",

            # Order numbers
            r"ORD-\d{10}",

            # Support ticket IDs
            r"TICKET-\d{8}",

            # Account numbers
            r"ACCT-[A-Z0-9]{12}",

            # Keywords
            "customer_data", "order_history", "support_case"
        ]

    @staticmethod
    def technical_patterns():
        """Technical security patterns."""
        return [
            # API keys (company-specific format)
            r"CORP-[A-Z0-9]{32}",

            # Service account names
            r"svc-[a-z-]+@company\.com",

            # Internal URLs
            r"https?://[a-z-]+\.internal\.company\.com",

            # Server names
            r"srv-[a-z0-9-]+-[0-9]{2}",

            # Database connection strings
            r"postgresql://[^@]+@[^/]+/\w+",

            # Keywords
            "internal", "confidential", "proprietary"
        ]

# Use custom patterns
settings = LoggingSettings(
    redact_patterns=(
        OrganizationSecurity.employee_patterns() +
        OrganizationSecurity.customer_patterns() +
        OrganizationSecurity.technical_patterns()
    ),
    custom_pii_patterns=["employee_id", "customer_id", "internal_url"]
)
```

### Industry-Specific Patterns

**Patterns for specific industries:**

```python
class IndustrySecurity:

    @staticmethod
    def financial_services():
        """Financial services security patterns."""
        return LoggingSettings(
            redact_patterns=[
                # Account numbers
                r"\b\d{8,17}\b",

                # SWIFT codes
                r"[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?",

                # IBAN codes
                r"IBAN[A-Z0-9]{15,34}",

                # Credit scores
                r"\b[3-8]\d{2}\b",

                # Wire transfer references
                r"WIRE-[A-Z0-9]{10,20}",

                "account", "balance", "transaction", "wire"
            ],
            redact_fields=[
                "account_number", "routing_number", "balance",
                "transaction_history", "credit_score", "wire_details"
            ]
        )

    @staticmethod
    def healthcare():
        """Healthcare security patterns."""
        return LoggingSettings(
            redact_patterns=[
                # Medical Record Numbers
                r"MRN[0-9]{6,10}",

                # National Provider Identifier
                r"NPI[0-9]{10}",

                # Insurance ID
                r"INS-[A-Z0-9]{8,12}",

                # Prescription numbers
                r"RX[0-9]{8,12}",

                "patient", "diagnosis", "treatment", "medication"
            ],
            redact_fields=[
                "patient.mrn", "patient.insurance", "diagnosis",
                "treatment_plan", "medication_list", "lab_results"
            ]
        )

    @staticmethod
    def retail_ecommerce():
        """Retail/e-commerce security patterns."""
        return LoggingSettings(
            redact_patterns=[
                # Order numbers
                r"ORD-[0-9]{8,12}",

                # SKU codes
                r"SKU-[A-Z0-9]{6,10}",

                # Loyalty program numbers
                r"LOYALTY-[0-9]{8,12}",

                # Gift card numbers
                r"GIFT-[0-9]{12,16}",

                "customer", "order", "payment", "shipping"
            ],
            redact_fields=[
                "customer.address", "shipping_address", "payment_method",
                "order_history", "loyalty_points", "gift_card_balance"
            ]
        )

# Use industry-specific patterns
settings = IndustrySecurity.financial_services()
configure_logging(settings=settings)
```

### Dynamic Security Configuration

**Adjust security based on runtime conditions:**

```python
class DynamicSecurity:

    @staticmethod
    def get_security_config(user_role: str, environment: str):
        """Get security configuration based on user role and environment."""

        base_patterns = ["password", "token", "secret"]
        base_fields = ["password", "api_key"]

        # Admin users see more data in development
        if user_role == "admin" and environment == "development":
            return LoggingSettings(
                redact_level="ERROR",  # Minimal redaction
                redact_patterns=base_patterns,
                redact_fields=base_fields
            )

        # Regular users in production get full redaction
        elif environment == "production":
            return LoggingSettings(
                redact_level="DEBUG",  # Full redaction
                enable_auto_redact_pii=True,
                redact_patterns=base_patterns + [
                    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                    r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"
                ],
                redact_fields=base_fields + [
                    "user.email", "user.phone", "user.address"
                ]
            )

        # Default configuration
        else:
            return LoggingSettings(
                redact_level="INFO",
                redact_patterns=base_patterns,
                redact_fields=base_fields
            )

# Use dynamic configuration
import os
user_role = os.getenv("USER_ROLE", "user")
environment = os.getenv("ENVIRONMENT", "development")

settings = DynamicSecurity.get_security_config(user_role, environment)
configure_logging(settings=settings)
```

### Custom Redaction Functions

**Build custom redaction logic:**

```python
from fapilog.redactors import field_redactor

def custom_redactor(replacement: str = "CUSTOM_REDACTED"):
    """Create a custom redaction processor."""

    def redactor_processor(logger, method_name, event_dict):
        """Custom redaction logic."""

        # Custom logic for sensitive data detection
        for key, value in event_dict.items():
            if isinstance(value, str):
                # Custom pattern: detect internal IDs
                if key.endswith("_id") and len(value) > 8:
                    event_dict[key] = replacement

                # Custom pattern: detect configuration URLs
                if "config" in key.lower() and "://" in value:
                    event_dict[key] = replacement

                # Custom pattern: detect large numeric strings (potential IDs)
                if value.isdigit() and len(value) > 6:
                    event_dict[key] = replacement

        return event_dict

    return redactor_processor

# Use custom redactor in processor chain
from fapilog.pipeline import build_processor_chain

def custom_processor_chain(settings):
    """Build processor chain with custom redactor."""
    processors = build_processor_chain(settings)

    # Add custom redactor before standard redaction
    processors.insert(-3, custom_redactor("INTERNAL_REDACTED"))

    return processors
```

[↑ Back to top](#security--redaction-guide)

---

## Real-World Examples

**Production-ready security configurations for common scenarios.**

### Financial Services Platform

**High-security configuration for banking/fintech:**

```python
def financial_platform_security():
    """Security configuration for financial services platform."""

    return LoggingSettings(
        # Maximum security level
        redact_level="DEBUG",  # Redact at all levels
        enable_auto_redact_pii=True,

        # Financial-specific fields
        redact_fields=[
            # Account information
            "account.number", "account.balance", "account.routing",
            "customer.ssn", "customer.tax_id", "customer.dob",

            # Payment data
            "payment.card_number", "payment.cvv", "payment.expiry",
            "payment.bank_account", "payment.wire_details",

            # Trading data
            "trading.account", "trading.positions", "trading.pnl",
            "portfolio.holdings", "portfolio.value",

            # Authentication
            "auth.password", "auth.pin", "auth.token",
            "session.credentials", "api.key"
        ],

        # Financial regex patterns
        redact_patterns=[
            # Account numbers (8-17 digits)
            r"\b\d{8,17}\b",

            # Credit card numbers (all major brands)
            r"\b4[0-9]{12}(?:[0-9]{3})?\b",      # Visa
            r"\b5[1-5][0-9]{14}\b",              # Mastercard
            r"\b3[47][0-9]{13}\b",               # Amex
            r"\b6(?:011|5[0-9]{2})[0-9]{12}\b",  # Discover

            # Banking codes
            r"IBAN[A-Z0-9]{15,34}",             # IBAN
            r"[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?", # SWIFT/BIC

            # SSN patterns
            r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b",

            # Financial keywords
            "balance", "account", "ssn", "routing", "wire",
            "trading", "portfolio", "investment", "financial"
        ],

        # Custom PII for finance
        custom_pii_patterns=[
            r"ACCT-\d{10,15}",     # Internal account format
            r"TXN-[A-Z0-9]{12}",   # Transaction IDs
            r"WIRE-[0-9]{10,15}",  # Wire transfer refs
            r"TRAD-[A-Z0-9]{8}"    # Trading IDs
        ],

        redact_replacement="[FINANCIAL_PII_REDACTED]"
    )

# Production financial configuration
settings = financial_platform_security()
configure_logging(settings=settings)

# Example usage
log.info("Account transaction",
         account_number="1234567890123456",  # Redacted
         amount=1000.00,                     # Not redacted
         transaction_id="TXN-ABC123456789",  # Redacted
         customer_ssn="123-45-6789")         # Redacted
```

### Healthcare Management System

**HIPAA-compliant healthcare platform:**

```python
def healthcare_platform_security():
    """Security configuration for healthcare platform."""

    return LoggingSettings(
        # HIPAA compliance level
        redact_level="DEBUG",
        enable_auto_redact_pii=True,

        # Healthcare-specific fields
        redact_fields=[
            # Patient information (PHI)
            "patient.name", "patient.dob", "patient.ssn",
            "patient.address", "patient.phone", "patient.email",
            "patient.mrn", "patient.insurance_id",

            # Medical data
            "diagnosis.code", "diagnosis.description",
            "treatment.plan", "treatment.notes",
            "medication.list", "medication.dosage",
            "lab.results", "lab.values",

            # Provider information
            "provider.npi", "provider.dea", "provider.license",
            "provider.notes", "provider.observations",

            # Billing information
            "billing.insurance", "billing.copay", "billing.deductible"
        ],

        # HIPAA regex patterns
        redact_patterns=[
            # Medical Record Numbers
            r"MRN[0-9]{6,10}",
            r"MR[0-9]{8,12}",

            # National Provider Identifier
            r"NPI[0-9]{10}",

            # DEA Registration Numbers
            r"DEA[A-Z]{2}[0-9]{7}",

            # Insurance ID patterns
            r"INS-[A-Z0-9]{8,15}",
            r"POLICY-[0-9]{8,12}",

            # Medical keywords
            "patient", "diagnosis", "treatment", "medication",
            "medical", "health", "clinical", "phi"
        ],

        # Healthcare-specific PII
        custom_pii_patterns=[
            r"PATIENT-\d{8}",      # Internal patient ID
            r"VISIT-\d{10}",       # Visit ID
            r"LAB-\d{8}",          # Lab order ID
            r"RX-\d{10}"           # Prescription ID
        ],

        redact_replacement="[PHI_REDACTED]"
    )

# HIPAA-compliant logging
settings = healthcare_platform_security()
configure_logging(settings=settings)

# Example usage
log.info("Patient visit",
         patient_mrn="MRN1234567890",    # Redacted
         provider_npi="NPI1234567890",   # Redacted
         diagnosis="Hypertension",       # Redacted
         visit_id="VISIT-1234567890")    # Redacted
```

### E-commerce Platform

**Customer data protection for retail:**

```python
def ecommerce_platform_security():
    """Security configuration for e-commerce platform."""

    return LoggingSettings(
        # Customer protection level
        redact_level="INFO",
        enable_auto_redact_pii=True,

        # E-commerce specific fields
        redact_fields=[
            # Customer data
            "customer.email", "customer.phone", "customer.address",
            "customer.name", "customer.dob", "customer.preferences",

            # Payment information
            "payment.card_number", "payment.cvv", "payment.expiry",
            "payment.billing_address", "payment.method_details",

            # Order information
            "order.shipping_address", "order.billing_address",
            "order.customer_notes", "order.special_instructions",

            # Account data
            "account.password", "account.security_questions",
            "account.loyalty_points", "account.wish_list"
        ],

        # E-commerce patterns
        redact_patterns=[
            # Order numbers
            r"ORD-[0-9]{8,12}",

            # SKU patterns
            r"SKU-[A-Z0-9]{6,12}",

            # Customer IDs
            r"CUST-\d{8,12}",

            # Loyalty program
            r"LOYALTY-\d{10,15}",

            # Gift cards
            r"GIFT-[0-9]{12,16}",

            # Promo codes
            r"PROMO-[A-Z0-9]{6,10}",

            # Keywords
            "customer", "payment", "shipping", "billing",
            "loyalty", "gift_card", "promo"
        ],

        # Retail-specific PII
        custom_pii_patterns=[
            r"MEMBER-\d{8}",       # Membership ID
            r"REWARD-\d{10}",      # Rewards ID
            r"TRACK-[A-Z0-9]{10}", # Tracking number
            r"RETURN-\d{8}"        # Return ID
        ],

        redact_replacement="[CUSTOMER_PII_REDACTED]"
    )

# E-commerce logging
settings = ecommerce_platform_security()
configure_logging(settings=settings)

# Example usage
log.info("Order processed",
         order_id="ORD-1234567890",         # Redacted
         customer_email="john@example.com", # Redacted
         payment_method="**** 1234",        # Redacted
         shipping_address="123 Main St")    # Redacted
```

### SaaS Application

**Multi-tenant SaaS security configuration:**

```python
def saas_platform_security():
    """Security configuration for SaaS platform."""

    return LoggingSettings(
        # Multi-tenant security
        redact_level="INFO",
        enable_auto_redact_pii=True,

        # SaaS-specific fields
        redact_fields=[
            # Tenant data
            "tenant.name", "tenant.domain", "tenant.config",
            "tenant.billing_info", "tenant.contract_details",

            # User data
            "user.email", "user.phone", "user.profile",
            "user.preferences", "user.activity_log",

            # Authentication
            "auth.password", "auth.api_key", "auth.oauth_token",
            "auth.refresh_token", "auth.session_data",

            # Application data
            "app.user_data", "app.custom_fields", "app.integrations",
            "app.webhook_urls", "app.third_party_keys"
        ],

        # SaaS patterns
        redact_patterns=[
            # Tenant IDs
            r"TENANT-[A-Z0-9]{8,12}",

            # User IDs
            r"USER-\d{6,10}",

            # API keys (various formats)
            r"sk-[a-zA-Z0-9]{48}",        # Stripe-style
            r"pk_[a-zA-Z0-9]{24}",        # Public keys
            r"[A-Za-z0-9]{32,64}",        # Generic long keys

            # OAuth tokens
            r"ya29\.[a-zA-Z0-9_-]+",      # Google
            r"EAA[a-zA-Z0-9]+",           # Facebook

            # Webhook URLs
            r"https://hooks\.[a-z]+\.com/[a-zA-Z0-9/]+",

            # Keywords
            "tenant", "api_key", "webhook", "oauth",
            "integration", "third_party"
        ],

        # SaaS-specific PII
        custom_pii_patterns=[
            r"ORG-\d{6}",          # Organization ID
            r"TEAM-[A-Z0-9]{8}",   # Team ID
            r"PROJ-\d{8}",         # Project ID
            r"INTEG-[A-Z0-9]{10}"  # Integration ID
        ],

        redact_replacement="[SAAS_PII_REDACTED]"
    )

# SaaS logging
settings = saas_platform_security()
configure_logging(settings=settings)

# Example usage
log.info("User action",
         tenant_id="TENANT-ABC123456",     # Redacted
         user_email="admin@company.com",   # Redacted
         api_key="sk-abc123...",           # Redacted
         action="data_export")             # Not redacted
```

### IoT/Edge Device Security

**Resource-constrained security for IoT:**

```python
def iot_device_security():
    """Security configuration for IoT/edge devices."""

    return LoggingSettings(
        # Minimal overhead for resource constraints
        redact_level="WARNING",  # Only redact warnings+
        enable_auto_redact_pii=False,  # Disable for performance

        # Essential IoT fields only
        redact_fields=[
            "device.mac_address", "device.serial", "device.imei",
            "device.sim_id", "device.private_key",
            "network.wifi_password", "network.cellular_apn"
        ],

        # Minimal patterns for performance
        redact_patterns=[
            # MAC addresses
            r"\b[0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}\b",

            # Serial numbers
            r"SN[A-Z0-9]{8,16}",

            # Essential keywords only
            "password", "key", "secret"
        ],

        redact_replacement="[REDACTED]"  # Short replacement
    )

# IoT logging
settings = iot_device_security()
configure_logging(settings=settings)
```

[↑ Back to top](#security--redaction-guide)

---

## Performance & Testing

### Redaction Performance Considerations

**Optimize redaction for high-volume applications:**

```python
# High-performance configuration
settings = LoggingSettings(
    # Optimize redaction level
    redact_level="INFO",  # Skip DEBUG for performance

    # Selective PII detection
    enable_auto_redact_pii=True,
    custom_pii_patterns=[
        # Only essential patterns - fewer is faster
        "employee_id", "customer_id"
    ],

    # Focused field redaction
    redact_fields=[
        # Only most critical fields
        "password", "api_key", "token"
    ],

    # Minimal patterns
    redact_patterns=[
        # Limit to essential patterns
        "password", "token", "secret"
    ]
)
```

### Performance Testing

**Test redaction performance impact:**

```python
import time
from fapilog import configure_logging, log

def test_redaction_performance():
    """Test performance impact of redaction."""

    # Test data
    test_data = {
        "user": {
            "email": "user@example.com",
            "password": "secret123",
            "profile": {
                "phone": "+1-555-123-4567",
                "ssn": "123-45-6789"
            }
        },
        "payment": {
            "card_number": "4532-1234-5678-9012",
            "cvv": "123"
        }
    }

    # Test without redaction
    start_time = time.perf_counter()
    for _ in range(1000):
        log.info("Test without redaction", data=test_data)
    no_redaction_time = time.perf_counter() - start_time

    # Configure with redaction
    settings = LoggingSettings(
        enable_auto_redact_pii=True,
        redact_fields=["user.password", "payment.card_number"],
        redact_patterns=["secret", "password"]
    )
    configure_logging(settings=settings)

    # Test with redaction
    start_time = time.perf_counter()
    for _ in range(1000):
        log.info("Test with redaction", data=test_data)
    with_redaction_time = time.perf_counter() - start_time

    print(f"No redaction: {no_redaction_time:.3f}s")
    print(f"With redaction: {with_redaction_time:.3f}s")
    print(f"Overhead: {(with_redaction_time / no_redaction_time - 1) * 100:.1f}%")

test_redaction_performance()
```

### Testing Redaction Behavior

**Verify redaction works correctly:**

```python
import json
from io import StringIO
import logging

def test_redaction_effectiveness():
    """Test that sensitive data is properly redacted."""

    # Capture log output
    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    logger = logging.getLogger("fapilog")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    # Configure redaction
    settings = LoggingSettings(
        redact_fields=["password", "user.ssn"],
        redact_patterns=["secret"],
        enable_auto_redact_pii=True
    )
    configure_logging(settings=settings)

    # Log sensitive data
    sensitive_data = {
        "password": "secret123",
        "user": {"ssn": "123-45-6789"},
        "email": "user@example.com",
        "secret_key": "my_secret_value"
    }

    log.info("Test data", data=sensitive_data)

    # Check log output
    log_output = log_capture.getvalue()

    # Verify sensitive data is redacted
    assert "secret123" not in log_output, "Password not redacted!"
    assert "123-45-6789" not in log_output, "SSN not redacted!"
    assert "user@example.com" not in log_output, "Email not redacted!"
    assert "my_secret_value" not in log_output, "Secret not redacted!"

    # Verify REDACTED appears
    assert "REDACTED" in log_output, "Redaction marker not found!"

    print("✅ All sensitive data properly redacted")

test_redaction_effectiveness()
```

### Unit Testing Redaction

**Test individual redaction components:**

```python
from fapilog.redactors import field_redactor, _redact_nested_fields
from fapilog._internal.pii_patterns import auto_redact_pii_processor

def test_field_redaction():
    """Test field redaction functionality."""

    # Test data
    event_dict = {
        "level": "INFO",
        "user": {"password": "secret123"},
        "api_key": "key_abc123"
    }

    # Create field redactor
    redactor = field_redactor(["user.password", "api_key"])

    # Apply redaction
    result = redactor(None, "info", event_dict)

    # Verify results
    assert result["user"]["password"] == "REDACTED"
    assert result["api_key"] == "REDACTED"
    assert result["level"] == "INFO"  # Unchanged

    print("✅ Field redaction test passed")

def test_pii_detection():
    """Test automatic PII detection."""

    # Test data with PII
    event_dict = {
        "level": "INFO",
        "email": "user@example.com",
        "phone": "+1-555-123-4567",
        "credit_card": "4532-1234-5678-9012"
    }

    # Create PII processor
    pii_processor = auto_redact_pii_processor()

    # Apply PII detection
    result = pii_processor(None, "info", event_dict)

    # Verify PII is redacted
    assert "user@example.com" not in str(result)
    assert "+1-555-123-4567" not in str(result)
    assert "4532-1234-5678-9012" not in str(result)

    print("✅ PII detection test passed")

# Run tests
test_field_redaction()
test_pii_detection()
```

### Redaction Validation

**Validate redaction configuration:**

```python
def validate_redaction_config(settings: LoggingSettings):
    """Validate redaction configuration for security compliance."""

    issues = []

    # Check essential fields are redacted
    essential_fields = ["password", "token", "api_key", "secret"]
    for field in essential_fields:
        if field not in settings.redact_fields and field not in settings.redact_patterns:
            issues.append(f"Essential field '{field}' not configured for redaction")

    # Check PII protection is enabled for production
    if not settings.enable_auto_redact_pii:
        issues.append("Automatic PII redaction is disabled")

    # Check redaction level is appropriate
    if settings.redact_level not in ["DEBUG", "INFO"]:
        issues.append(f"Redaction level '{settings.redact_level}' may be too permissive")

    # Check for common compliance patterns
    compliance_patterns = [
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
        r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",           # Credit card
        r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b"                       # SSN
    ]

    for pattern in compliance_patterns:
        if pattern not in settings.redact_patterns:
            issues.append(f"Missing compliance pattern: {pattern}")

    # Return validation results
    if issues:
        print("❌ Redaction configuration issues:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("✅ Redaction configuration is compliant")
        return True

# Validate configuration
settings = LoggingSettings(
    redact_fields=["password", "api_key"],
    enable_auto_redact_pii=True,
    redact_level="INFO"
)

validate_redaction_config(settings)
```

[↑ Back to top](#security--redaction-guide)

---

## Troubleshooting

### Common Redaction Issues

**Sensitive data still visible in logs:**

```python
# Problem: Data not being redacted
log.info("User data", password="secret123")  # Still visible

# Solution 1: Check field configuration
settings = LoggingSettings(
    redact_fields=["password"]  # Ensure field is configured
)

# Solution 2: Check pattern configuration
settings = LoggingSettings(
    redact_patterns=["password"]  # Pattern-based approach
)

# Solution 3: Enable automatic PII detection
settings = LoggingSettings(
    enable_auto_redact_pii=True  # Automatic detection
)
```

**Nested fields not being redacted:**

```python
# Problem: Nested data not redacted
user_data = {"user": {"password": "secret123"}}
log.info("User", data=user_data)  # password still visible

# Solution: Use dot notation for nested fields
settings = LoggingSettings(
    redact_fields=["data.user.password"]  # Full path to nested field
)

# Alternative: Pattern-based for nested structures
settings = LoggingSettings(
    redact_patterns=["password"]  # Catches any field named password
)
```

**Redaction not working at DEBUG level:**

```python
# Problem: DEBUG logs not redacted
log.debug("Debug data", password="secret123")  # Not redacted

# Solution: Lower redaction level
settings = LoggingSettings(
    redact_level="DEBUG",  # Redact at DEBUG level too
    redact_fields=["password"]
)

# Check current redaction level
print(f"Current redaction level: {settings.redact_level}")
```

### Performance Issues

**Slow logging with redaction enabled:**

```python
# Problem: Redaction causing performance issues

# Solution 1: Optimize redaction level
settings = LoggingSettings(
    redact_level="INFO",  # Skip DEBUG logs
    enable_auto_redact_pii=True
)

# Solution 2: Reduce custom PII patterns
settings = LoggingSettings(
    custom_pii_patterns=[
        # Only essential patterns
        "employee_id"  # Remove unnecessary patterns
    ]
)

# Solution 3: Use specific fields instead of patterns
settings = LoggingSettings(
    redact_fields=["password", "api_key"],  # Faster than patterns
    redact_patterns=[]  # Disable pattern matching
)
```

**High memory usage with redaction:**

```python
# Problem: Memory usage increases with redaction

# Solution: Optimize data structures
settings = LoggingSettings(
    redact_replacement="[X]",  # Shorter replacement string
    enable_auto_redact_pii=True
)

# Monitor memory usage
import psutil
process = psutil.Process()
print(f"Memory usage: {process.memory_info().rss / 1024 / 1024:.1f} MB")
```

### Configuration Issues

**Environment variables not working:**

```bash
# Problem: Environment variables ignored

# Solution: Check variable names and casing
export FAPILOG_REDACT_FIELDS=password,api_key  # Correct
export fapilog_redact_fields=password,api_key  # Wrong case

# Check if variables are set
env | grep FAPILOG_
```

```python
# Verify environment variable loading
import os
print("Environment variables:")
for key, value in os.environ.items():
    if key.startswith("FAPILOG_"):
        print(f"  {key}={value}")

# Test settings loading
settings = LoggingSettings()
print(f"Loaded redact_fields: {settings.redact_fields}")
```

**Redaction not working in production:**

```python
# Problem: Redaction works in development but not production

# Solution 1: Check environment-specific configuration
import os
environment = os.getenv("ENVIRONMENT", "development")
print(f"Current environment: {environment}")

# Solution 2: Verify production settings
if environment == "production":
    settings = LoggingSettings(
        redact_level="INFO",  # Ensure appropriate level
        enable_auto_redact_pii=True,
        redact_fields=["password", "api_key", "token"]
    )
else:
    settings = LoggingSettings(
        redact_level="CRITICAL"  # Minimal redaction in dev
    )

# Solution 3: Test redaction in production environment
configure_logging(settings=settings)
log.info("Production test", password="test123")  # Should be redacted
```

### Debugging Redaction

**Enable debug logging for redaction:**

```python
import logging

# Enable debug logging for fapilog internals
logging.getLogger("fapilog").setLevel(logging.DEBUG)
logging.basicConfig(level=logging.DEBUG)

# Configure with redaction
settings = LoggingSettings(
    redact_fields=["password"],
    enable_auto_redact_pii=True
)
configure_logging(settings=settings)

# Test redaction - debug output will show processing
log.info("Test redaction", password="secret123")
```

**Test redaction step by step:**

```python
def debug_redaction_pipeline():
    """Debug the redaction pipeline step by step."""

    # Original event
    event_dict = {
        "level": "INFO",
        "password": "secret123",
        "email": "user@example.com"
    }

    print("1. Original event:")
    print(f"   {event_dict}")

    # Test field redaction
    from fapilog.redactors import field_redactor
    field_redactor_func = field_redactor(["password"])
    after_field = field_redactor_func(None, "info", event_dict.copy())

    print("2. After field redaction:")
    print(f"   {after_field}")

    # Test PII redaction
    from fapilog._internal.pii_patterns import auto_redact_pii_processor
    pii_redactor_func = auto_redact_pii_processor()
    after_pii = pii_redactor_func(None, "info", after_field.copy())

    print("3. After PII redaction:")
    print(f"   {after_pii}")

debug_redaction_pipeline()
```

### Getting Help

**Check documentation and examples:**

```python
# Check current configuration
from fapilog.settings import LoggingSettings
settings = LoggingSettings()
print("Current settings:")
print(settings.model_dump_json(indent=2))

# Test redaction configuration
def test_my_redaction():
    """Test current redaction configuration."""
    test_data = {
        "password": "secret123",
        "email": "test@example.com",
        "credit_card": "4532-1234-5678-9012"
    }

    log.info("Redaction test", **test_data)
    print("Check log output above - sensitive data should be REDACTED")

test_my_redaction()
```

**Common solutions checklist:**

- ✅ **Check field names** - Use exact field names in `redact_fields`
- ✅ **Use dot notation** - For nested fields: `user.password`
- ✅ **Verify redaction level** - Set `redact_level="DEBUG"` for all levels
- ✅ **Enable PII detection** - Set `enable_auto_redact_pii=True`
- ✅ **Test incrementally** - Start with simple field redaction
- ✅ **Check environment variables** - Verify `FAPILOG_*` variables are set
- ✅ **Monitor performance** - Use minimal patterns for high volume

[↑ Back to top](#security--redaction-guide)

---

## Next Steps

### 🚀 **Advanced Security**

- **[Configuration Guide](configuration.md)** - Complete configuration reference
- **[FastAPI Integration Guide](fastapi-integration.md)** - Web application security patterns
- **[Performance Guide](../performance.md)** - Optimize redaction performance

### 🎯 **Implementation Guides**

- **[Examples](../examples/index.md)** - Copy-paste security examples
- **[Production Patterns](../examples/production/index.md)** - Real-world configurations
- **[Compliance Examples](../examples/advanced/index.md)** - Regulatory compliance patterns

### 📚 **Reference**

- **[API Reference](../api-reference.md)** - Complete technical documentation
- **[Troubleshooting](../troubleshooting.md)** - Common issues and solutions
- **[Best Practices](../best-practices.md)** - Security best practices

Ready to implement comprehensive data protection? Start with the [Quick Start](#quick-start) section and choose the security patterns that match your compliance requirements!

[↑ Back to top](#security--redaction-guide)
