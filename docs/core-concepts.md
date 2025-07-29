# Core Concepts

**Understanding the fundamental principles and architecture that make Fapilog powerful and flexible.**

This section provides a deep dive into the core concepts that underpin Fapilog's design. Understanding these concepts will help you make the most of Fapilog's capabilities and design effective logging strategies for your applications.

---

## Architecture Overview

Fapilog uses a **modular pipeline architecture** that processes log events through multiple stages, each adding value while maintaining performance and flexibility.

### Pipeline Flow

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Log Event │───▶│  Enrichment  │───▶│ Processing  │───▶│    Queue    │───▶│    Sinks    │
│             │    │              │    │             │    │             │    │             │
│ log.info()  │    │ Add context  │    │ Redaction   │    │ Async buffer│    │ File/Stdout │
│ log.error() │    │ Trace IDs    │    │ Formatting  │    │ Batching    │    │ Loki/Custom │
└─────────────┘    │ User data    │    │ Validation  │    │ Overflow    │    │             │
                   └──────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### AsyncSmartCache Architecture

The enrichment stage is powered by **AsyncSmartCache v2.0**, a race-condition-free caching system that provides:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Async Enricher  │───▶│ AsyncSmartCache │───▶│ Cached Result   │
│                 │    │                 │    │                 │
│ await enrich()  │    │ Atomic Ops      │    │ Zero Race       │
│ Context Data    │    │ Error Caching   │    │ Conditions      │
│ Performance     │    │ Retry Logic     │    │ 5x Throughput   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

#### Cache Features

- **Atomic Operations**: All cache operations use async locks to prevent race conditions
- **Error Caching**: Failed computations are cached with intelligent retry intervals
- **Async-First Design**: Native async/await support for optimal performance
- **Memory Efficiency**: Automatic cleanup and optimized memory usage
- **Performance Monitoring**: Built-in cache statistics and hit rate tracking

### Key Design Principles

1. **Separation of Concerns** - Each stage has a single responsibility
2. **Extensibility** - Custom enrichers, processors, and sinks
3. **Performance** - Async processing with race-condition-free caching
4. **Reliability** - Fault tolerance, error caching, and intelligent retry
5. **Observability** - Rich context for debugging and monitoring
6. **Concurrency Safety** - Zero race conditions under high-load scenarios

---

## Structured Logging

### What is Structured Logging?

Structured logging is the practice of logging data in a machine-readable format (typically JSON) rather than plain text. Instead of:

```
2024-01-15 10:30:45 INFO User 123 logged in from 192.168.1.100
```

You get:

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "info",
  "event": "User logged in",
  "user_id": "123",
  "ip_address": "192.168.1.100",
  "session_id": "abc123",
  "duration_ms": 45.2,
  "trace_id": "req-abc123-def456"
}
```

### Benefits of Structured Logging

1. **Machine Readable** - Easy to parse and analyze programmatically
2. **Searchable** - Query logs by specific fields and values
3. **Consistent** - Standardized format across all log events
4. **Extensible** - Add new fields without breaking existing tools
5. **Observability** - Rich context for monitoring and alerting

### Example: Before vs After

**Traditional Logging:**

```python
import logging
logging.info(f"Payment processed for user {user_id}, amount: ${amount}")
```

**Structured Logging with Fapilog:**

```python
from fapilog import log
log.info("Payment processed",
         user_id=user_id,
         amount=amount,
         currency="USD",
         payment_method="credit_card",
         transaction_id="txn_12345")
```

### Field Types and Best Practices

**String Fields:**

```python
log.info("User action",
         user_id="123",
         action="login",
         endpoint="/auth/login")
```

**Numeric Fields:**

```python
log.info("Performance metric",
         duration_ms=125.5,
         memory_usage_mb=256.8,
         cpu_percent=12.3)
```

**Boolean Fields:**

```python
log.info("Feature flag",
         feature_enabled=True,
         user_premium=False)
```

**Object Fields:**

```python
log.info("User data",
         user={"id": "123", "name": "John", "email": "john@example.com"},
         session={"id": "sess_abc", "created": "2024-01-15T10:30:00Z"})
```

---

## Configuration Model

Fapilog uses a flexible configuration model that supports multiple configuration sources and environments.

### Configuration Sources

1. **Environment Variables** - Primary configuration method
2. **Programmatic Settings** - Direct Python configuration
3. **Container Settings** - Isolated configurations for different components

### Environment-Based Configuration

```bash
# Basic settings
export FAPILOG_LEVEL=INFO
export FAPILOG_FORMAT=json
export FAPILOG_QUEUE_ENABLED=true

# Output configuration
export FAPILOG_SINKS=stdout,file
export FAPILOG_FILE_PATH=/var/log/app.log

# Performance tuning
export FAPILOG_QUEUE_SIZE=1000
export FAPILOG_BATCH_SIZE=100
```

### Programmatic Configuration

```python
from fapilog.settings import LoggingSettings

settings = LoggingSettings(
    level="INFO",
    format="json",
    sinks=["stdout", "file"],
    file_path="/var/log/app.log",
    queue_enabled=True,
    queue_size=1000
)
```

### Environment-Specific Configurations

**Development:**

```python
dev_settings = LoggingSettings(
    level="DEBUG",
    format="pretty",  # Human-readable
    sinks=["stdout"],
    queue_enabled=False
)
```

**Production:**

```python
prod_settings = LoggingSettings(
    level="INFO",
    format="json",
    sinks=["stdout", "file", "loki"],
    file_path="/var/log/app.log",
    queue_enabled=True,
    queue_size=5000,
    redact_patterns=["email", "phone", "credit_card"]
)
```

---

## Performance Design

Fapilog is designed for high-performance applications with configurable trade-offs between throughput, latency, and resource usage.

### Async Logging Queue

The core performance feature is the asynchronous logging queue:

```python
# High-performance configuration
settings = LoggingSettings(
    queue_enabled=True,
    queue_size=10000,        # Large queue for bursts
    batch_size=100,          # Batch for efficiency
    batch_timeout=0.5,       # Flush every 500ms
    overflow_strategy="drop" # Drop logs if queue full
)
```

### Queue Overflow Strategies

1. **Block** - Wait for space (guaranteed delivery, may block application)
2. **Drop** - Drop new logs (high performance, may lose logs)
3. **Sample** - Keep percentage of logs (balanced approach)

### Performance Tuning

**High Throughput:**

```python
settings = LoggingSettings(
    queue_size=10000,
    batch_size=100,
    batch_timeout=0.1,  # Frequent flushing
    overflow_strategy="drop"
)
```

**Low Latency:**

```python
settings = LoggingSettings(
    queue_size=100,
    batch_size=1,       # No batching
    batch_timeout=0.0,  # Immediate flush
    overflow_strategy="block"
)
```

**Memory Constrained:**

```python
settings = LoggingSettings(
    queue_size=100,
    batch_size=10,
    enable_resource_metrics=False,
    overflow_strategy="drop"
)
```

### Resource Monitoring

Enable resource metrics to monitor logging performance:

```python
settings = LoggingSettings(
    enable_resource_metrics=True,
    level="INFO"
)

# Logs include memory and CPU usage
log.info("Performance check", operation="database_query")
```

---

## Extensibility

Fapilog is designed to be highly extensible through custom enrichers, sinks, and processors.

### Custom Enrichers

Add custom context to all log events:

```python
from fapilog import Enricher
import os

class EnvironmentEnricher(Enricher):
    """Add environment information to all logs."""

    def enrich(self, event):
        event["environment"] = os.getenv("ENVIRONMENT", "development")
        event["version"] = os.getenv("APP_VERSION", "1.0.0")
        event["deployment_id"] = os.getenv("DEPLOYMENT_ID")
        return event

# Register custom enricher
configure_logging(enrichers=[EnvironmentEnricher()])
```

### Custom Sinks

Create custom output destinations:

```python
from fapilog import Sink
import requests

class SlackSink(Sink):
    """Send error logs to Slack."""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def write(self, event):
        if event.get("level") == "error":
            message = {
                "text": f"Error: {event.get('event', 'Unknown error')}",
                "attachments": [{
                    "fields": [
                        {"title": "Trace ID", "value": event.get("trace_id", "N/A")},
                        {"title": "User ID", "value": event.get("user_id", "N/A")}
                    ]
                }]
            }

            try:
                requests.post(self.webhook_url, json=message)
            except Exception as e:
                print(f"Slack sink error: {e}")

# Register custom sink
slack_sink = SlackSink("https://hooks.slack.com/services/YOUR/WEBHOOK/URL")
configure_logging(sinks=["stdout", slack_sink])
```

### Custom Processors

Transform log events before output:

```python
from fapilog import Processor

class TimestampProcessor(Processor):
    """Convert timestamps to ISO format."""

    def process(self, event):
        if "timestamp" in event:
            # Ensure timestamp is in ISO format
            if isinstance(event["timestamp"], (int, float)):
                from datetime import datetime
                event["timestamp"] = datetime.fromtimestamp(event["timestamp"]).isoformat()
        return event

# Register custom processor
configure_logging(processors=[TimestampProcessor()])
```

---

## Key Design Decisions

### 1. JSON as Default Format

**Decision:** Use JSON as the default structured format
**Rationale:**

- Universal compatibility with log aggregation systems
- Rich data types (strings, numbers, booleans, objects, arrays)
- Human-readable while being machine-parseable
- No schema requirements for flexibility

### 2. Async Queue Architecture

**Decision:** Use asynchronous queue for log processing
**Rationale:**

- Non-blocking application performance
- Configurable batching for efficiency
- Overflow strategies for different use cases
- Fault tolerance through error handling

### 3. Environment-Based Configuration

**Decision:** Primary configuration through environment variables
**Rationale:**

- Twelve-factor app compliance
- Easy deployment across environments
- No code changes for configuration
- Security through external configuration

### 4. FastAPI-First Design

**Decision:** Optimize for FastAPI applications
**Rationale:**

- Automatic middleware integration
- Request context enrichment
- Performance characteristics match FastAPI
- Modern Python async patterns

### 5. Container Architecture

**Decision:** Support multiple isolated logging instances
**Rationale:**

- Microservices architecture support
- Test isolation and independence
- Thread safety for concurrent applications
- Resource management and cleanup

---

## Related Topics

- **[User Guide](user-guide.md)** - Step-by-step tutorials and examples
- **[API Reference](api-reference.md)** - Complete technical documentation
- **[Configuration Guide](config.md)** - Environment variables and settings
- **[Examples](examples/index.md)** - Real-world usage patterns
- **[Examples & Recipes](examples/index.md)** - Real-world usage patterns and advanced capabilities
