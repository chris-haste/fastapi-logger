# Configuration Guide

**Complete guide to core Fapilog configuration settings and environment setup.**

Configure Fapilog through environment variables, programmatic settings, or hybrid approaches. This guide covers essential configuration options, basic queue and monitoring settings, and environment-specific patterns.

**For specialized topics, see:**

- **[Security & Redaction Guide](security.md)** - Data protection, PII redaction, and compliance
- **[FastAPI Integration Guide](fastapi-integration.md)** - Web application configuration and performance
- **[Sinks Guide](sinks.md)** - Output destination configuration and optimization

---

## Quick Navigation

**Jump to what you need:**

- **🚀 [Quick Start](#quick-start)** - Get configured in 30 seconds
- **⚙️ [Environment Variables](#environment-variables)** - Production-ready configuration
- **🔧 [Programmatic Configuration](#programmatic-configuration)** - Python-based setup
- **📊 [Queue Settings](#queue-settings)** - Basic queue configuration
- **📈 [Monitoring Settings](#monitoring-settings)** - Basic metrics setup
- **🌍 [Environment Patterns](#environment-specific-patterns)** - Dev, staging, production
- **🎯 [Real-World Examples](#real-world-examples)** - Configuration examples
- **⚠️ [Troubleshooting](#troubleshooting)** - Common configuration issues

[↑ Back to top](#configuration-guide)

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Configuration Sources](#configuration-sources)
3. [Core Settings Reference](#core-settings-reference)
4. [Environment Variables](#environment-variables)
5. [Programmatic Configuration](#programmatic-configuration)
6. [Queue Settings](#queue-settings)
7. [Monitoring Settings](#monitoring-settings)
8. [Environment-Specific Patterns](#environment-specific-patterns)
9. [Real-World Examples](#real-world-examples)
10. [Configuration Validation](#configuration-validation)
11. [Troubleshooting](#troubleshooting)

[↑ Back to top](#configuration-guide)

---

## Quick Start

### Zero Configuration

**Works out of the box with sensible defaults:**

```python
from fapilog import configure_logging, log

# Zero configuration - uses defaults
configure_logging()
log.info("Hello, Fapilog!", user_id="123")
```

**Output:**

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "info",
  "event": "Hello, Fapilog!",
  "hostname": "server-01",
  "pid": 12345,
  "user_id": "123"
}
```

### Environment Variable Configuration

**Production-ready setup in 3 lines:**

```bash
# Set environment variables
export FAPILOG_LEVEL=INFO
export FAPILOG_SINKS=stdout,file:///var/log/app.log
export FAPILOG_QUEUE_ENABLED=true
```

```python
from fapilog import configure_logging

# Uses environment variables automatically
configure_logging()
```

### Programmatic Configuration

**Full control through Python:**

```python
from fapilog import configure_logging
from fapilog.settings import LoggingSettings

settings = LoggingSettings(
    level="INFO",
    sinks=["stdout", "file:///var/log/app.log"],
    queue_enabled=True,
    queue_maxsize=5000,
    redact_patterns=["password", "token"]
)

configure_logging(settings=settings)
```

[↑ Back to top](#configuration-guide)

---

## Configuration Sources

Fapilog supports multiple configuration sources with clear precedence:

### Precedence Order

1. **Programmatic Settings** (highest priority)
2. **Environment Variables**
3. **Default Values** (lowest priority)

```python
from fapilog.settings import LoggingSettings

# Environment variables provide defaults
# FAPILOG_LEVEL=DEBUG
# FAPILOG_QUEUE_ENABLED=true

settings = LoggingSettings(
    level="INFO",  # Overrides FAPILOG_LEVEL=DEBUG
    # queue_enabled inherited from environment (true)
    queue_maxsize=2000  # Overrides default (1000)
)
```

### Hybrid Configuration

**Best of both worlds:**

```python
# Base configuration from environment
settings = LoggingSettings()

# Override specific settings programmatically
if os.getenv("ENVIRONMENT") == "development":
    settings.level = "DEBUG"
    settings.json_console = "pretty"
elif os.getenv("ENVIRONMENT") == "production":
    settings.sampling_rate = 0.1  # Sample 10% in production
    settings.redact_patterns = ["password", "token", "secret"]

configure_logging(settings=settings)
```

[↑ Back to top](#configuration-guide)

---

## Core Settings Reference

### Essential Settings

| Setting         | Type        | Default      | Description                 |
| --------------- | ----------- | ------------ | --------------------------- |
| `level`         | `str`       | `"INFO"`     | Minimum log level           |
| `sinks`         | `List[str]` | `["stdout"]` | Output destinations         |
| `json_console`  | `str`       | `"auto"`     | Console output format       |
| `queue_enabled` | `bool`      | `True`       | Enable async queue          |
| `sampling_rate` | `float`     | `1.0`        | Log sampling rate (0.0-1.0) |

### Log Levels

**Available levels (case-insensitive):**

- **`DEBUG`** - Detailed development information
- **`INFO`** - General application flow
- **`WARNING`** - Potential issues
- **`ERROR`** - Error conditions
- **`CRITICAL`** - Severe errors

```python
# All equivalent
settings = LoggingSettings(level="INFO")
settings = LoggingSettings(level="info")
settings = LoggingSettings(level="Info")
```

### Output Formats

**Console format options:**

- **`auto`** - JSON in non-TTY, pretty in TTY
- **`json`** - Always structured JSON
- **`pretty`** - Always human-readable

```python
# Development
settings = LoggingSettings(json_console="pretty")

# Production
settings = LoggingSettings(json_console="json")

# Auto-detect (recommended)
settings = LoggingSettings(json_console="auto")
```

### Sink Destinations

**Built-in sink types:**

```python
settings = LoggingSettings(sinks=[
    "stdout",                           # Console output
    "file:///var/log/app.log",         # File output
    "loki://loki-server:3100"          # Loki aggregation
])
```

[↑ Back to top](#configuration-guide)

---

## Environment Variables

### Complete Environment Variables Reference

**All configuration options with environment variable names:**

```bash
# Core Settings
export FAPILOG_LEVEL=INFO                    # Log level
export FAPILOG_SINKS=stdout,file            # Output sinks
export FAPILOG_JSON_CONSOLE=auto            # Console format
export FAPILOG_SAMPLING_RATE=1.0            # Sampling rate

# Queue Settings
export FAPILOG_QUEUE_ENABLED=true           # Enable async queue
export FAPILOG_QUEUE_MAXSIZE=1000           # Queue capacity
export FAPILOG_QUEUE_OVERFLOW=drop          # Overflow strategy
export FAPILOG_QUEUE_BATCH_SIZE=10          # Batch size
export FAPILOG_QUEUE_BATCH_TIMEOUT=1.0      # Batch timeout

# Security Settings
export FAPILOG_REDACT_PATTERNS=password,token    # Patterns to redact
export FAPILOG_REDACT_FIELDS=user.password       # Fields to redact
export FAPILOG_REDACT_LEVEL=INFO                 # Redaction level
export FAPILOG_ENABLE_AUTO_REDACT_PII=true       # Auto PII redaction

# Performance Settings
export FAPILOG_ENABLE_RESOURCE_METRICS=false    # Resource monitoring
export FAPILOG_METRICS_ENABLED=false            # Metrics collection
export FAPILOG_METRICS_PROMETHEUS_ENABLED=false # Prometheus endpoint

# Trace Settings
export FAPILOG_TRACE_ID_HEADER=X-Request-ID     # Trace header name
export FAPILOG_ENABLE_HTTPX_TRACE_PROPAGATION=false # Httpx propagation
```

### Environment Variable Patterns

**Development environment:**

```bash
# .env.development
FAPILOG_LEVEL=DEBUG
FAPILOG_JSON_CONSOLE=pretty
FAPILOG_QUEUE_ENABLED=false
FAPILOG_ENABLE_RESOURCE_METRICS=false
```

**Production environment:**

```bash
# .env.production
FAPILOG_LEVEL=INFO
FAPILOG_JSON_CONSOLE=json
FAPILOG_QUEUE_ENABLED=true
FAPILOG_QUEUE_MAXSIZE=10000
FAPILOG_REDACT_PATTERNS=password,token,secret
FAPILOG_ENABLE_RESOURCE_METRICS=true
```

### Docker Configuration

**Using environment variables in containers:**

```dockerfile
# Dockerfile
ENV FAPILOG_LEVEL=INFO
ENV FAPILOG_SINKS=stdout,file:///var/log/app.log
ENV FAPILOG_QUEUE_ENABLED=true
ENV FAPILOG_REDACT_PATTERNS=password,token
```

```yaml
# docker-compose.yml
version: "3.8"
services:
  api:
    environment:
      - FAPILOG_LEVEL=INFO
      - FAPILOG_SINKS=stdout,loki://loki:3100
      - FAPILOG_QUEUE_MAXSIZE=5000
      - FAPILOG_REDACT_FIELDS=user.password,api_key
```

[↑ Back to top](#configuration-guide)

---

## Programmatic Configuration

### LoggingSettings Class

**Complete programmatic control:**

```python
from fapilog.settings import LoggingSettings
from fapilog import configure_logging

# Full configuration example
settings = LoggingSettings(
    # Core settings
    level="INFO",
    sinks=["stdout", "file:///var/log/app.log"],
    json_console="auto",
    sampling_rate=1.0,

    # Queue settings
    queue_enabled=True,
    queue_maxsize=5000,
    queue_overflow="drop",
    queue_batch_size=50,
    queue_batch_timeout=0.5,

    # Security settings
    redact_patterns=["password", "token", "secret"],
    redact_fields=["user.password", "authorization"],
    redact_level="INFO",
    enable_auto_redact_pii=True,

    # Performance settings
    enable_resource_metrics=True,

    # Trace settings
    trace_id_header="X-Request-ID",
    enable_httpx_trace_propagation=True
)

configure_logging(settings=settings)
```

### Dynamic Configuration

**Adapt configuration based on environment:**

```python
import os
from fapilog.settings import LoggingSettings

def get_logging_settings() -> LoggingSettings:
    """Get environment-appropriate logging settings."""

    env = os.getenv("ENVIRONMENT", "development").lower()

    # Base settings from environment variables
    settings = LoggingSettings()

    if env == "development":
        settings.level = "DEBUG"
        settings.json_console = "pretty"
        settings.queue_enabled = False
        settings.enable_resource_metrics = False

    elif env == "staging":
        settings.level = "INFO"
        settings.json_console = "json"
        settings.queue_maxsize = 2000
        settings.redact_patterns = ["password", "token"]

    elif env == "production":
        settings.level = "INFO"
        settings.queue_maxsize = 10000
        settings.queue_batch_size = 100
        settings.sampling_rate = 0.1  # Sample 10%
        settings.redact_patterns = ["password", "token", "secret", "api_key"]
        settings.enable_resource_metrics = True

    return settings

# Use in application
settings = get_logging_settings()
configure_logging(settings=settings)
```

### Configuration Factory Pattern

**Reusable configuration builders:**

```python
from fapilog.settings import LoggingSettings

class LoggingConfigFactory:
    """Factory for creating logging configurations."""

    @staticmethod
    def development() -> LoggingSettings:
        """Development configuration - verbose and pretty."""
        return LoggingSettings(
            level="DEBUG",
            json_console="pretty",
            queue_enabled=False,
            enable_resource_metrics=False
        )

    @staticmethod
    def production() -> LoggingSettings:
        """Production configuration - optimized and secure."""
        return LoggingSettings(
            level="INFO",
            json_console="json",
            queue_enabled=True,
            queue_maxsize=10000,
            queue_batch_size=100,
            redact_patterns=["password", "token", "secret"],
            enable_resource_metrics=True
        )

    @staticmethod
    def high_volume() -> LoggingSettings:
        """High-volume configuration - maximum throughput."""
        return LoggingSettings(
            level="WARNING",  # Reduce volume
            queue_maxsize=50000,
            queue_batch_size=500,
            queue_overflow="drop",
            sampling_rate=0.01,  # 1% sampling
            enable_resource_metrics=False
        )

# Usage
if os.getenv("HIGH_VOLUME"):
    settings = LoggingConfigFactory.high_volume()
else:
    settings = LoggingConfigFactory.production()

configure_logging(settings=settings)
```

[↑ Back to top](#configuration-guide)

---

## Queue Settings

### Queue Configuration

**Essential queue settings for async performance:**

```python
settings = LoggingSettings(
    queue_enabled=True,           # Enable async processing
    queue_maxsize=1000,          # Queue capacity
    queue_overflow="drop",       # Overflow strategy
    queue_batch_size=10,         # Events per batch
    queue_batch_timeout=1.0,     # Max batch wait time
    queue_retry_delay=1.0,       # Retry delay on failure
    queue_max_retries=3          # Max retry attempts
)
```

### Overflow Strategies

**Handle queue overflow gracefully:**

**Drop Strategy (Default):**

```python
settings = LoggingSettings(queue_overflow="drop")
# Silently discard new logs when queue is full
# Best for: High-performance applications where log loss is acceptable
```

**Block Strategy:**

```python
settings = LoggingSettings(queue_overflow="block")
# Wait for queue space (may block application)
# Best for: Critical logging where no loss is acceptable
```

**Sample Strategy:**

```python
settings = LoggingSettings(
    queue_overflow="sample",
    sampling_rate=0.1  # Keep 10% when overflowing
)
# Probabilistically keep logs when queue is full
# Best for: Balanced approach between performance and data retention
```

### Performance Tuning Patterns

**High-Throughput Configuration:**

```python
# Optimized for 10,000+ events/second
settings = LoggingSettings(
    queue_enabled=True,
    queue_maxsize=50000,         # Large queue for bursts
    queue_batch_size=1000,       # Large batches for efficiency
    queue_batch_timeout=1.0,     # Allow batches to fill
    queue_overflow="drop",       # Don't block under load
    sampling_rate=0.1,           # Sample 10% of logs
    enable_resource_metrics=False # Reduce overhead
)
```

**Low-Latency Configuration:**

```python
# Optimized for minimal delay
settings = LoggingSettings(
    queue_enabled=True,
    queue_maxsize=1000,
    queue_batch_size=1,          # No batching
    queue_batch_timeout=0.01,    # Immediate processing
    queue_overflow="block",      # Ensure delivery
    enable_resource_metrics=True # Monitor performance
)
```

**Memory-Constrained Configuration:**

```python
# Optimized for minimal memory usage
settings = LoggingSettings(
    queue_enabled=True,
    queue_maxsize=100,           # Small queue
    queue_batch_size=5,          # Small batches
    queue_overflow="drop",       # Don't accumulate
    enable_resource_metrics=False,
    sampling_rate=0.5            # Reduce volume
)
```

### Performance Monitoring

**Monitor queue performance:**

```python
from fapilog import get_queue_stats

# Get queue performance metrics
stats = get_queue_stats()
print(f"Queue size: {stats['queue_size']}/{stats['queue_maxsize']}")
print(f"Events processed: {stats['events_processed']}")
print(f"Events dropped: {stats['events_dropped']}")
```

[↑ Back to top](#configuration-guide)

---

## Security & Data Protection

**For comprehensive security and redaction features, see the dedicated [Security & Redaction Guide](security.md).**

Fapilog provides extensive data protection capabilities including:

- **🔒 Field-based redaction** - Redact specific fields by name with dot notation
- **🎯 Pattern-based redaction** - Regex patterns for sensitive data detection
- **🤖 Automatic PII detection** - Built-in detection for emails, credit cards, SSN, phone numbers
- **📊 Level-aware redaction** - Different rules per log level (DEBUG vs production)
- **⚖️ Compliance frameworks** - Pre-configured patterns for GDPR, HIPAA, PCI DSS
- **🎨 Custom security patterns** - Domain-specific protection patterns

### Quick Security Setup

**Basic data protection:**

```python
settings = LoggingSettings(
    # Automatic PII detection
    enable_auto_redact_pii=True,

    # Field-based redaction
    redact_fields=["password", "api_key", "user.ssn"],

    # Pattern-based redaction
    redact_patterns=["secret", "token"],

    # Redaction level
    redact_level="INFO"  # Redact INFO+ levels
)
```

**For complete security configuration, examples, and compliance patterns, see the [Security & Redaction Guide](security.md).**

[↑ Back to top](#configuration-guide)

---

## Monitoring Settings

### Metrics Configuration

**Enable comprehensive monitoring:**

```python
settings = LoggingSettings(
    # Basic metrics
    enable_resource_metrics=True,     # CPU/memory in logs

    # Advanced metrics collection
    metrics_enabled=True,             # Enable metrics system
    metrics_sample_window=100,        # Sample window size

    # Prometheus integration
    metrics_prometheus_enabled=True,  # Enable Prometheus endpoint
    metrics_prometheus_port=8000,     # Metrics HTTP port
    metrics_prometheus_host="0.0.0.0" # Bind address
)
```

### Resource Monitoring

**Monitor logging system performance:**

```python
# Enable resource metrics in log entries
settings = LoggingSettings(enable_resource_metrics=True)

# Logs include resource information
log.info("Processing request", request_id="123")
# Output includes: memory_mb, cpu_percent, process_id
```

### Prometheus Integration

**Export metrics for monitoring systems:**

```python
settings = LoggingSettings(
    metrics_enabled=True,
    metrics_prometheus_enabled=True,
    metrics_prometheus_port=8000
)

configure_logging(settings=settings)

# Metrics available at http://localhost:8000/metrics
# - fapilog_queue_size
# - fapilog_events_total
# - fapilog_sink_writes_total
# - fapilog_memory_bytes
```

### Monitoring Examples

**Production Monitoring Setup:**

```python
# Full monitoring configuration
settings = LoggingSettings(
    # Core logging
    level="INFO",
    queue_enabled=True,
    queue_maxsize=10000,

    # Resource monitoring
    enable_resource_metrics=True,

    # Metrics collection
    metrics_enabled=True,
    metrics_sample_window=1000,  # Larger window for stability

    # Prometheus export
    metrics_prometheus_enabled=True,
    metrics_prometheus_port=8000,
    metrics_prometheus_host="0.0.0.0"
)

configure_logging(settings=settings)

# Use with monitoring stack
# - Prometheus scrapes :8000/metrics
# - Grafana visualizes metrics
# - Alerts on queue size, error rates
```

[↑ Back to top](#configuration-guide)

---

## Environment-Specific Patterns

### Development Environment

**Optimized for development workflow:**

```python
def development_config() -> LoggingSettings:
    """Development configuration - verbose and readable."""
    return LoggingSettings(
        # Verbose logging
        level="DEBUG",
        json_console="pretty",  # Human-readable output

        # Synchronous for debugging
        queue_enabled=False,

        # Minimal overhead
        enable_resource_metrics=False,
        metrics_enabled=False,

        # No redaction for debugging
        enable_auto_redact_pii=False,

        # Simple output
        sinks=["stdout"]
    )
```

### Staging Environment

**Production-like with enhanced debugging:**

```python
def staging_config() -> LoggingSettings:
    """Staging configuration - production-like with debugging."""
    return LoggingSettings(
        # Balanced logging
        level="INFO",
        json_console="json",  # Structured for log aggregation

        # Moderate queue size
        queue_enabled=True,
        queue_maxsize=2000,
        queue_batch_size=20,

        # Basic monitoring
        enable_resource_metrics=True,
        metrics_enabled=True,

        # Security testing
        redact_patterns=["password", "token"],
        enable_auto_redact_pii=True,

        # Multiple outputs for testing
        sinks=["stdout", "file:///var/log/staging.log"]
    )
```

### Production Environment

**Optimized for production workloads:**

```python
def production_config() -> LoggingSettings:
    """Production configuration - optimized and secure."""
    return LoggingSettings(
        # Production logging
        level="INFO",
        json_console="json",

        # High-performance queue
        queue_enabled=True,
        queue_maxsize=10000,
        queue_batch_size=100,
        queue_batch_timeout=0.5,
        queue_overflow="drop",

        # Full monitoring
        enable_resource_metrics=True,
        metrics_enabled=True,
        metrics_prometheus_enabled=True,

        # Security
        redact_patterns=["password", "token", "secret", "api_key"],
        redact_fields=["authorization", "x-api-key"],
        enable_auto_redact_pii=True,

        # Multiple sinks
        sinks=[
            "stdout",
            "file:///var/log/app.log",
            "loki://loki:3100?batch_size=200"
        ],

        # Performance optimization
        sampling_rate=0.1  # Sample 10% for high-volume
    )
```

### Environment Selection

**Dynamic environment-based configuration:**

```python
import os
from fapilog.settings import LoggingSettings

def get_environment_config() -> LoggingSettings:
    """Get configuration based on environment."""

    env = os.getenv("ENVIRONMENT", "development").lower()

    if env == "production":
        return production_config()
    elif env == "staging":
        return staging_config()
    else:
        return development_config()

# Usage
settings = get_environment_config()
configure_logging(settings=settings)
```

[↑ Back to top](#configuration-guide)

---

## Real-World Examples

### Microservices Configuration

**Configuration for microservice architectures:**

```python
def microservice_config(service_name: str) -> LoggingSettings:
    """Configuration for microservice deployment."""

    return LoggingSettings(
        # Service identification
        level="INFO",
        json_console="json",

        # Distributed tracing
        trace_id_header="X-Trace-ID",
        enable_httpx_trace_propagation=True,

        # High-performance queue
        queue_enabled=True,
        queue_maxsize=5000,
        queue_batch_size=50,
        queue_overflow="drop",

        # Service monitoring
        enable_resource_metrics=True,
        metrics_enabled=True,
        metrics_prometheus_enabled=True,
        metrics_prometheus_port=8000,

        # Security
        redact_patterns=["password", "token", "secret"],
        enable_auto_redact_pii=True,

        # Central logging
        sinks=[
            "stdout",
            f"loki://loki:3100?labels=service={service_name},env=prod"
        ]
    )

# Usage per service
user_service_config = microservice_config("user-service")
payment_service_config = microservice_config("payment-service")
```

### High-Volume API Configuration

**Configuration for high-traffic APIs:**

```python
def high_volume_api_config() -> LoggingSettings:
    """Configuration for high-volume API (10K+ RPS)."""

    return LoggingSettings(
        # Reduced log volume
        level="WARNING",  # Only warnings and errors
        json_console="json",

        # Large queue for bursts
        queue_enabled=True,
        queue_maxsize=50000,
        queue_batch_size=1000,  # Large batches
        queue_batch_timeout=2.0,  # Allow batches to fill
        queue_overflow="drop",

        # Aggressive sampling
        sampling_rate=0.01,  # 1% sampling

        # Minimal monitoring to reduce overhead
        enable_resource_metrics=False,
        metrics_enabled=True,  # Still track basics

        # Security
        redact_patterns=["password", "token"],

        # Optimized sinks
        sinks=["stdout"]  # Fastest sink only
    )
```

### Banking/Financial Configuration

**Configuration for regulated financial services:**

```python
def financial_services_config() -> LoggingSettings:
    """Configuration for financial services - maximum security."""

    return LoggingSettings(
        # Audit logging
        level="INFO",
        json_console="json",

        # Reliable delivery
        queue_enabled=True,
        queue_maxsize=10000,
        queue_overflow="block",  # Never drop audit logs
        queue_max_retries=5,     # Retry failures

        # Comprehensive monitoring
        enable_resource_metrics=True,
        metrics_enabled=True,

        # Maximum security
        enable_auto_redact_pii=True,
        redact_level="DEBUG",  # Redact all levels
        redact_patterns=[
            "password", "pin", "token", "secret", "key",
            r"\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}",  # Credit cards
            r"\d{3}[-\s]?\d{2}[-\s]?\d{4}",             # SSN
            r"IBAN[A-Z0-9]{15,34}",                     # IBAN
            r"[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?"        # BIC/SWIFT
        ],
        redact_fields=[
            "account_number", "routing_number", "ssn",
            "credit_card", "cvv", "pin", "password"
        ],

        # Audit trail
        sinks=[
            "stdout",
            "file:///var/log/audit.log",
            "syslog://audit-server:514"
        ]
    )
```

### IoT/Edge Configuration

**Configuration for resource-constrained environments:**

```python
def iot_edge_config() -> LoggingSettings:
    """Configuration for IoT/edge devices."""

    return LoggingSettings(
        # Minimal logging
        level="ERROR",  # Only errors
        json_console="json",

        # Small queue for memory constraints
        queue_enabled=True,
        queue_maxsize=100,
        queue_batch_size=5,
        queue_overflow="drop",

        # No overhead features
        enable_resource_metrics=False,
        metrics_enabled=False,

        # Minimal security
        enable_auto_redact_pii=False,

        # Local logging only
        sinks=["file:///tmp/device.log"]
    )
```

[↑ Back to top](#configuration-guide)

---

## Configuration Validation

### Automatic Validation

**Fapilog validates all configuration automatically:**

```python
from fapilog.settings import LoggingSettings
from fapilog.exceptions import ConfigurationError

try:
    settings = LoggingSettings(
        level="INVALID_LEVEL",  # Invalid
        sampling_rate=2.0       # Invalid (must be 0.0-1.0)
    )
except ConfigurationError as e:
    print(f"Configuration error: {e}")
    # Configuration error: Invalid level 'INVALID_LEVEL'.
    # Must be one of: DEBUG, INFO, WARN, WARNING, ERROR, CRITICAL
```

### Common Validation Rules

**Settings are validated on creation:**

- **Log levels:** Must be DEBUG, INFO, WARN, WARNING, ERROR, CRITICAL
- **Sampling rate:** Must be between 0.0 and 1.0
- **Queue sizes:** Must be positive integers
- **Timeouts:** Must be positive floats
- **Overflow strategy:** Must be drop, block, or sample

### Configuration Testing

**Test your configuration before deployment:**

```python
def test_configuration():
    """Test configuration before deployment."""

    try:
        # Test settings creation
        settings = LoggingSettings(
            level="INFO",
            queue_maxsize=1000,
            sampling_rate=0.1
        )

        # Test configuration
        configure_logging(settings=settings)

        # Test logging
        log.info("Configuration test successful")

        print("✅ Configuration is valid")
        return True

    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

# Run before deployment
if not test_configuration():
    exit(1)
```

### Environment Variable Validation

**Validate environment variables:**

```python
import os
from fapilog.settings import LoggingSettings

def validate_environment():
    """Validate environment variable configuration."""

    # Check required variables
    required_vars = ["FAPILOG_LEVEL", "FAPILOG_SINKS"]
    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        print(f"Missing environment variables: {missing}")
        return False

    # Test settings creation from environment
    try:
        settings = LoggingSettings()
        print("✅ Environment configuration is valid")
        return True
    except Exception as e:
        print(f"❌ Environment configuration error: {e}")
        return False

# Validate on startup
validate_environment()
```

[↑ Back to top](#configuration-guide)

---

## Troubleshooting

### Common Configuration Issues

**No logs appearing:**

```python
# Check configuration
from fapilog.settings import LoggingSettings

settings = LoggingSettings()
print(f"Log level: {settings.level}")
print(f"Sinks: {settings.sinks}")

# Enable debug mode
import logging
logging.getLogger("fapilog").setLevel(logging.DEBUG)
```

**Queue not working:**

```python
# Verify queue configuration
settings = LoggingSettings()
print(f"Queue enabled: {settings.queue_enabled}")
print(f"Queue size: {settings.queue_maxsize}")

# Test queue manually
from fapilog import get_queue_stats
stats = get_queue_stats()
print(f"Queue stats: {stats}")
```

**Environment variables not working:**

```python
import os

# Check environment variables
env_vars = {k: v for k, v in os.environ.items() if k.startswith("FAPILOG_")}
print(f"Fapilog environment variables: {env_vars}")

# Check case sensitivity
print(f"FAPILOG_LEVEL: {os.getenv('FAPILOG_LEVEL')}")
print(f"fapilog_level: {os.getenv('fapilog_level')}")  # Won't work
```

### Performance Issues

**High memory usage:**

```python
# Reduce memory usage
settings = LoggingSettings(
    queue_maxsize=100,          # Smaller queue
    enable_resource_metrics=False,  # Disable metrics
    sampling_rate=0.1           # Sample logs
)
```

**Slow logging performance:**

```python
# Optimize for speed
settings = LoggingSettings(
    queue_enabled=True,         # Enable async
    queue_batch_size=100,       # Larger batches
    queue_overflow="drop",      # Don't block
    enable_resource_metrics=False  # Reduce overhead
)
```

**Queue overflow:**

```python
# Handle overflow
settings = LoggingSettings(
    queue_maxsize=10000,        # Larger queue
    queue_overflow="sample",    # Sample instead of drop
    sampling_rate=0.1           # 10% sampling when full
)
```

### Debug Configuration

**Enable debug logging for troubleshooting:**

```python
import logging

# Enable debug logging for fapilog
logging.getLogger("fapilog").setLevel(logging.DEBUG)
logging.basicConfig(level=logging.DEBUG)

# Configure fapilog
from fapilog import configure_logging
configure_logging()  # Debug output will show configuration details
```

**Inspect current configuration:**

```python
from fapilog.settings import LoggingSettings

# Show current configuration
settings = LoggingSettings()
config_dict = settings.model_dump()

print("Current Configuration:")
for key, value in config_dict.items():
    print(f"  {key}: {value}")
```

### Getting Help

**Check the documentation:**

- **[API Reference](../api-reference.md)** - Complete technical reference
- **[FastAPI Integration Guide](fastapi-integration.md)** - Integration patterns
- **[Sinks Guide](sinks.md)** - Output configuration
- **[Examples](../examples/index.md)** - Real-world usage patterns

**Enable verbose logging:**

```python
# Get detailed error information
import logging
logging.getLogger("fapilog").setLevel(logging.DEBUG)

# Test configuration step by step
from fapilog import configure_logging
configure_logging()  # Watch debug output for issues
```

[↑ Back to top](#configuration-guide)

---

## Next Steps

### 🚀 **Advanced Configuration**

- **[Sinks Guide](sinks.md)** - Configure custom output destinations
- **[FastAPI Integration Guide](fastapi-integration.md)** - Web application patterns
- **[Monitoring & Performance](../monitoring.md)** - Production observability

### 🎯 **Real-World Usage**

- **[Examples](../examples/index.md)** - Copy-paste examples for common scenarios
- **[Production Patterns](../examples/production/index.md)** - Battle-tested configurations
- **[Advanced Patterns](../examples/advanced/index.md)** - Complex use cases

### 📚 **Reference**

- **[API Reference](../api-reference.md)** - Complete technical documentation
- **[Environment Variables](../api-reference.md#environment-variables)** - Full variable reference
- **[Troubleshooting](../troubleshooting.md)** - Common issues and solutions

Ready to configure your specific environment? Check out the [Environment-Specific Patterns](#environment-specific-patterns) section for copy-paste configurations!

[↑ Back to top](#configuration-guide)
