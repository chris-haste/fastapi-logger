# User Guide

**New to Fapilog? Start with the [Quickstart Tutorial](quickstart.md) for a hands-on, step-by-step introduction!**

This guide provides step-by-step tutorials for using `fapilog` in your applications. It's designed to take you from basic setup to advanced features, with practical examples throughout.

---

## What You'll Learn

By the end of this guide, you'll be able to:

- ✅ **Set up structured logging** in any Python application
- ✅ **Integrate with FastAPI** for automatic request tracking
- ✅ **Configure for different environments** (development, staging, production)
- ✅ **Add custom context** and enrich log data
- ✅ **Optimize performance** for high-volume applications
- ✅ **Deploy to production** with monitoring and security

---

## Learning Path

This guide follows a progressive learning path:

1. **[Quick Start](#quick-start)** - Get logging in 5 minutes
2. **[Basic Usage](#basic-usage)** - Common patterns and configuration
3. **[FastAPI Integration](#fastapi-integration)** - Real-world web application
4. **[Configuration](#configuration)** - Environment and advanced settings
5. **[Advanced Features](#advanced-features)** - Custom enrichers and sinks
6. **[Production Deployment](#production-deployment)** - Production-ready setup

---

## Quick Start

Get up and running with `fapilog` in under 5 minutes.

### Prerequisites

- Python 3.8+
- Basic understanding of Python logging
- FastAPI (optional, but recommended)

### Installation

```bash
pip install fapilog
```

For FastAPI applications:

```bash
pip install fapilog[fastapi]
```

### Basic Setup

The simplest way to get started:

```python
from fapilog import configure_logging, log

# Configure logging with defaults
configure_logging()

# Start logging
log.info("Application started", version="1.0.0")
log.warning("Deprecated feature used", feature="old_api")
log.error("Database connection failed", database="postgres")
```

**What happens:**

- ✅ Structured JSON logging enabled
- ✅ Automatic timestamp and log level
- ✅ Hostname and process ID added
- ✅ Pretty console output in development
- ✅ Async-safe logging with background queue

### Your First Log

```python
from fapilog import configure_logging, log

configure_logging()

# Basic logging
log.info("User logged in", user_id="123", action="login")

# Structured logging with multiple fields
log.info(
    "API request processed",
    endpoint="/api/users",
    method="GET",
    status_code=200,
    duration_ms=45.2,
    user_id="123"
)
```

**Expected Output:**

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "info",
  "event": "User logged in",
  "hostname": "server-01",
  "pid": 12345,
  "user_id": "123",
  "action": "login"
}
```

### What You've Accomplished

✅ **Structured logging** - JSON format with rich context  
✅ **Performance** - Non-blocking async logging  
✅ **Developer experience** - Simple, familiar API  
✅ **Production ready** - Automatic error handling

---

## Basic Usage

Learn the fundamental patterns and configuration options.

### Logging Levels

Use standard logging levels with structured data:

```python
from fapilog import log

# Different levels for different purposes
log.debug("Processing item", item_id=123, step="validation")
log.info("User action", user_id="456", action="login")
log.warning("Deprecated API called", endpoint="/old/api")
log.error("Database error", database="postgres", error_code=500)
log.critical("System failure", component="database", impact="high")
```

### Structured Fields

Add any data you want to track:

```python
# Business data
log.info("Order placed",
         order_id="ORD-12345",
         customer_id="CUST-789",
         total_amount=99.99,
         items_count=3)

# Technical data
log.info("API call",
         endpoint="/api/orders",
         method="POST",
         duration_ms=125.5,
         status_code=201)

# Custom context
log.info("User activity",
         user_id="123",
         session_id="sess-abc123",
         ip_address="192.168.1.100",
         user_agent="Mozilla/5.0...")
```

### Basic Configuration

Configure logging for different environments:

```python
from fapilog import configure_logging
from fapilog.settings import LoggingSettings

# Development (pretty console output)
dev_settings = LoggingSettings(
    level="DEBUG",
    format="pretty",  # Human-readable
    sinks=["stdout"]
)
configure_logging(dev_settings)

# Production (JSON for log aggregation)
prod_settings = LoggingSettings(
    level="INFO",
    format="json",
    sinks=["stdout", "file"],
    file_path="/var/log/app.log"
)
configure_logging(prod_settings)
```

### Environment Variables

Configure via environment variables:

```bash
# Basic settings
export FAPILOG_LEVEL=INFO
export FAPILOG_FORMAT=json
export FAPILOG_SINKS=stdout,file
export FAPILOG_QUEUE_ENABLED=true

# Output configuration
export FAPILOG_SINKS=stdout,file
export FAPILOG_FILE_PATH=/var/log/app.log

# Performance tuning
export FAPILOG_QUEUE_SIZE=1000
export FAPILOG_BATCH_SIZE=100
```

### Common Patterns

**Error handling with context:**

```python
try:
    result = risky_operation()
    log.info("Operation successful", result_type=type(result).__name__)
except Exception as e:
    log.error("Operation failed",
              error=str(e),
              error_type=type(e).__name__,
              operation="risky_operation")
    raise
```

**Performance monitoring:**

```python
import time

def monitored_function():
    start_time = time.time()

    try:
        # Your function logic
        result = complex_calculation()

        duration_ms = (time.time() - start_time) * 1000
        log.info("Function completed",
                 duration_ms=duration_ms,
                 result_size=len(result))
        return result

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        log.error("Function failed",
                  duration_ms=duration_ms,
                  error=str(e))
        raise
```

**User activity tracking:**

```python
def track_user_action(user_id: str, action: str, **kwargs):
    """Track user actions with consistent context."""
    log.info("User action",
             user_id=user_id,
             action=action,
             timestamp=time.time(),
             **kwargs)
```

---

## FastAPI Integration

Learn how to integrate Fapilog with FastAPI for automatic request tracking and context enrichment.

### Automatic Setup

The easiest way to get started:

```python
from fastapi import FastAPI
from fapilog import configure_logging, log

app = FastAPI()

# Configure logging with FastAPI integration
configure_logging(app=app)

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    # All logs automatically include request context
    log.info("Fetching user", user_id=user_id)

    try:
        user = await get_user_from_db(user_id)
        log.info("User found", user_id=user_id, user_name=user.name)
        return user
    except UserNotFound:
        log.warning("User not found", user_id=user_id)
        raise HTTPException(status_code=404, detail="User not found")
```

### What Gets Added Automatically

Every log event during a request includes:

| Field         | Type    | Description                 | Example            |
| ------------- | ------- | --------------------------- | ------------------ |
| `trace_id`    | string  | Request correlation ID      | `"abc123def456"`   |
| `span_id`     | string  | Request span ID             | `"xyz789uvw012"`   |
| `method`      | string  | HTTP method                 | `"POST"`           |
| `path`        | string  | Request path                | `"/api/users/123"` |
| `client_ip`   | string  | Client IP address           | `"192.168.1.100"`  |
| `status_code` | integer | HTTP response status        | `200`              |
| `latency_ms`  | float   | Request duration in ms      | `45.2`             |
| `user_agent`  | string  | User-Agent header           | `"curl/7.68.0"`    |
| `req_bytes`   | integer | Request body size in bytes  | `1024`             |
| `res_bytes`   | integer | Response body size in bytes | `2048`             |

### Response Headers

The middleware automatically adds correlation headers:

```python
# Response headers added automatically
{
    "X-Trace-Id": "abc123def456",
    "X-Span-Id": "xyz789uvw012",
    "X-Response-Time-ms": "45.2"
}
```

### Custom Trace ID Headers

Configure custom header names:

```python
from fapilog.settings import LoggingSettings

# Use custom header name
settings = LoggingSettings(trace_id_header="X-Custom-Trace-ID")
configure_logging(settings=settings, app=app)
```

```bash
# Via environment variable
export FAPILOG_TRACE_ID_HEADER=X-Custom-Trace-ID
```

### Manual Middleware Registration

If you prefer manual setup:

```python
from fapilog.middleware import TraceIDMiddleware
from fapilog.settings import LoggingSettings

app = FastAPI()
settings = LoggingSettings(trace_id_header="X-Request-ID")

# Register middleware manually
app.add_middleware(TraceIDMiddleware, trace_id_header=settings.trace_id_header)
configure_logging(settings=settings)
```

### Real-World Example: E-commerce API

```python
from fastapi import FastAPI, HTTPException, Depends
from fapilog import configure_logging, log

app = FastAPI()
configure_logging(app=app)

@app.post("/orders")
async def create_order(order_data: dict):
    log.info("Order creation started",
             customer_id=order_data.get("customer_id"),
             items_count=len(order_data.get("items", [])))

    try:
        # Validate order
        validated_order = validate_order(order_data)
        log.info("Order validated", order_id=validated_order["id"])

        # Process payment
        payment_result = await process_payment(validated_order)
        log.info("Payment processed",
                 order_id=validated_order["id"],
                 payment_id=payment_result["payment_id"],
                 amount=payment_result["amount"])

        # Save to database
        saved_order = await save_order(validated_order)
        log.info("Order saved",
                 order_id=saved_order["id"],
                 status="confirmed")

        return saved_order

    except ValidationError as e:
        log.warning("Order validation failed",
                    customer_id=order_data.get("customer_id"),
                    errors=e.errors)
        raise HTTPException(status_code=400, detail="Invalid order")

    except PaymentError as e:
        log.error("Payment processing failed",
                  order_id=validated_order["id"],
                  error=str(e),
                  payment_method=order_data.get("payment_method"))
        raise HTTPException(status_code=402, detail="Payment failed")
```

---

## Configuration

Learn how to configure Fapilog for different environments and use cases.

### Environment-Based Configuration

Configure via environment variables for different environments:

**Development:**

```bash
export FAPILOG_LEVEL=DEBUG
export FAPILOG_FORMAT=pretty
export FAPILOG_SINKS=stdout
export FAPILOG_QUEUE_ENABLED=false
```

**Staging:**

```bash
export FAPILOG_LEVEL=INFO
export FAPILOG_FORMAT=json
export FAPILOG_SINKS=stdout,file
export FAPILOG_FILE_PATH=/var/log/app.log
export FAPILOG_QUEUE_ENABLED=true
export FAPILOG_QUEUE_SIZE=1000
```

**Production:**

```bash
export FAPILOG_LEVEL=INFO
export FAPILOG_FORMAT=json
export FAPILOG_SINKS=stdout,file,loki
export FAPILOG_FILE_PATH=/var/log/app.log
export FAPILOG_QUEUE_ENABLED=true
export FAPILOG_QUEUE_SIZE=5000
export FAPILOG_REDACT_PATTERNS=email,phone,credit_card
```

### Programmatic Configuration

```python
from fapilog.settings import LoggingSettings

# Development settings
dev_settings = LoggingSettings(
    level="DEBUG",
    format="pretty",
    sinks=["stdout"],
    queue_enabled=False
)

# Production settings
prod_settings = LoggingSettings(
    level="INFO",
    format="json",
    sinks=["stdout", "file"],
    file_path="/var/log/app.log",
    queue_enabled=True,
    queue_size=5000,
    redact_patterns=["email", "phone", "credit_card"]
)

# Configure based on environment
import os
if os.getenv("ENVIRONMENT") == "production":
    configure_logging(prod_settings)
else:
    configure_logging(dev_settings)
```

### Multiple Environments Example

```python
# config/logging.py
from fapilog.settings import LoggingSettings
import os

def get_logging_settings():
    """Get settings based on environment."""
    env = os.getenv("ENVIRONMENT", "development")

    if env == "development":
        return LoggingSettings(
            level="DEBUG",
            format="pretty",
            sinks=["stdout"],
            queue_enabled=False
        )

    elif env == "staging":
        return LoggingSettings(
            level="INFO",
            format="json",
            sinks=["stdout", "file"],
            file_path="/var/log/app.log",
            queue_enabled=True,
            queue_size=1000
        )

    elif env == "production":
        return LoggingSettings(
            level="INFO",
            format="json",
            sinks=["stdout", "file", "loki"],
            file_path="/var/log/app.log",
            queue_enabled=True,
            queue_size=5000,
            redact_patterns=["email", "phone", "credit_card"],
            batch_size=100
        )

    else:
        raise ValueError(f"Unknown environment: {env}")

# main.py
from fapilog import configure_logging
from config.logging import get_logging_settings

settings = get_logging_settings()
configure_logging(settings)
```

### Configuration Best Practices

**1. Use environment variables for deployment:**

```bash
# .env file
FAPILOG_LEVEL=INFO
FAPILOG_FORMAT=json
FAPILOG_SINKS=stdout,file
FAPILOG_FILE_PATH=/var/log/app.log
```

**2. Validate configuration early:**

```python
from fapilog.settings import LoggingSettings

try:
    settings = LoggingSettings()
    configure_logging(settings)
    log.info("Logging configured successfully")
except Exception as e:
    print(f"Logging configuration failed: {e}")
    # Fall back to basic configuration
    configure_logging()
```

**3. Test configuration in development:**

```python
# Test all log levels
log.debug("Debug message")
log.info("Info message")
log.warning("Warning message")
log.error("Error message")
```

---

## Advanced Features

Learn how to extend Fapilog with custom enrichers, sinks, and advanced configurations.

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

class PerformanceEnricher(Enricher):
    """Add performance metrics to logs."""

    def enrich(self, event):
        import psutil
        event["memory_usage_mb"] = psutil.Process().memory_info().rss / 1024 / 1024
        event["cpu_percent"] = psutil.Process().cpu_percent()
        return event

# Register custom enrichers
from fapilog import configure_logging
configure_logging(enrichers=[EnvironmentEnricher(), PerformanceEnricher()])
```

### Custom Sinks

Create custom output destinations:

```python
from fapilog import Sink
import requests

class SlackSink(Sink):
    """Send error logs to Slack."""

    def __init__(self, webhook_url: str, channel: str = "#alerts"):
        self.webhook_url = webhook_url
        self.channel = channel

    def write(self, event):
        if event.get("level") == "error":
            message = {
                "channel": self.channel,
                "text": f"Error: {event.get('event', 'Unknown error')}",
                "attachments": [{
                    "fields": [
                        {"title": "Trace ID", "value": event.get("trace_id", "N/A")},
                        {"title": "User ID", "value": event.get("user_id", "N/A")},
                        {"title": "Timestamp", "value": event.get("timestamp", "N/A")}
                    ]
                }]
            }

            try:
                requests.post(self.webhook_url, json=message)
            except Exception as e:
                # Don't let sink errors break logging
                print(f"Slack sink error: {e}")

# Register custom sink
slack_sink = SlackSink("https://hooks.slack.com/services/YOUR/WEBHOOK/URL")
configure_logging(sinks=["stdout", slack_sink])
```

### Container Architecture

Use multiple isolated logging instances for complex applications:

```python
from fapilog.container import LoggingContainer
from fapilog.settings import LoggingSettings

# Admin service: verbose logging to file
admin_settings = LoggingSettings(
    level="DEBUG",
    sinks=["stdout", "file:///var/log/admin.log"],
    redact_fields=["password", "token"]
)
admin_container = LoggingContainer(admin_settings)
admin_logger = admin_container.configure()

# API service: JSON logging to Loki
api_settings = LoggingSettings(
    level="INFO",
    sinks=["stdout", "loki://loki:3100"],
    queue_enabled=True
)
api_container = LoggingContainer(api_settings)
api_logger = api_container.configure()

# Background worker: minimal logging
worker_settings = LoggingSettings(
    level="WARNING",
    sinks=["stdout"],
    sampling_rate=0.1  # Only 10% of logs
)
worker_container = LoggingContainer(worker_settings)
worker_logger = worker_container.configure()

# Each logger operates completely independently
admin_logger.debug("Admin debug message")
api_logger.info("API request processed")
worker_logger.warning("Worker task failed")
```

### Performance Tuning

Optimize logging for high-volume applications:

```python
from fapilog.settings import LoggingSettings

# High-performance configuration
settings = LoggingSettings(
    level="INFO",
    queue_enabled=True,
    queue_size=10000,        # Large queue for bursts
    batch_size=100,          # Batch for efficiency
    batch_timeout=0.5,       # Flush every 500ms
    overflow_strategy="drop" # Drop logs if queue full
)

configure_logging(settings)
```

### Sampling for High Volume

Reduce log volume with sampling:

```python
# Log only 10% of debug messages
settings = LoggingSettings(
    level="DEBUG",
    sampling_rate=0.1,  # 10% sampling
    sampling_levels=["debug"]  # Only sample debug level
)
```

---

## Production Deployment

Learn how to deploy Fapilog in production with monitoring, security, and performance optimization.

### Docker Deployment

**Dockerfile:**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application
COPY . .

# Create log directory
RUN mkdir -p /var/log

# Set environment variables
ENV FAPILOG_LEVEL=INFO
ENV FAPILOG_FORMAT=json
ENV FAPILOG_SINKS=stdout,file
ENV FAPILOG_FILE_PATH=/var/log/app.log
ENV FAPILOG_QUEUE_ENABLED=true
ENV FAPILOG_QUEUE_SIZE=5000

# Run application
CMD ["python", "main.py"]
```

**docker-compose.yml:**

```yaml
version: "3.8"
services:
  app:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./logs:/var/log
    environment:
      - FAPILOG_LEVEL=INFO
      - FAPILOG_FORMAT=json
      - FAPILOG_SINKS=stdout,file
      - FAPILOG_FILE_PATH=/var/log/app.log
      - FAPILOG_QUEUE_ENABLED=true
      - FAPILOG_QUEUE_SIZE=5000
      - FAPILOG_REDACT_PATTERNS=email,phone,credit_card
```

### Monitoring Integration

**Prometheus metrics:**

```python
from prometheus_client import Counter, Histogram
from fapilog import log

# Define metrics
log_events_total = Counter('log_events_total', 'Total log events', ['level'])
log_event_duration = Histogram('log_event_duration_seconds', 'Log event duration')

def monitored_logger(level, message, **kwargs):
    """Log with metrics."""
    log_events_total.labels(level=level).inc()

    with log_event_duration.time():
        getattr(log, level)(message, **kwargs)
```

**Health checks:**

```python
from fastapi import HTTPException
from fapilog import log

@app.get("/health/logging")
async def logging_health():
    """Check logging system health."""
    try:
        # Test logging
        log.info("Health check", check_type="logging")

        # Get queue stats
        stats = get_queue_stats()

        return {
            "status": "healthy",
            "queue_size": stats.queue_size,
            "queue_maxsize": stats.queue_maxsize
        }
    except Exception as e:
        log.error("Logging health check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Logging unhealthy")
```

### Security Best Practices

**PII Redaction:**

```python
# Automatic redaction
settings = LoggingSettings(
    redact_patterns=[
        "email",
        "phone",
        "credit_card",
        "ssn",
        "password",
        "api_key"
    ]
)
```

**Manual redaction:**

```python
from fapilog import redact

log.info("Payment processed",
         card_number=redact("4111-1111-1111-1111"),
         amount=100.00)
```

**Access control:**

```python
# Log file permissions
import os
os.chmod("/var/log/app.log", 0o640)  # Owner read/write, group read
```

### Performance Optimization

**Queue configuration for high volume:**

```python
settings = LoggingSettings(
    queue_enabled=True,
    queue_size=10000,        # Large queue
    batch_size=100,          # Efficient batching
    batch_timeout=0.5,       # Frequent flushing
    overflow_strategy="drop" # Don't block on overflow
)
```

**Sampling for high-volume logs:**

```python
settings = LoggingSettings(
    sampling_rate=0.1,       # 10% sampling
    sampling_levels=["debug", "info"]  # Sample these levels
)
```

**Resource monitoring:**

```python
# Monitor queue health
def check_queue_health():
    stats = get_queue_stats()
    if stats.queue_size > stats.queue_maxsize * 0.8:
        log.warning("Queue nearly full",
                   queue_size=stats.queue_size,
                   max_size=stats.queue_maxsize)
```

---

## Troubleshooting

Common issues and their solutions.

### Configuration Issues

**Logs not appearing:**

```python
# Check configuration
from fapilog.settings import LoggingSettings
settings = LoggingSettings()
print(settings.model_dump())

# Enable debug logging
import logging
logging.getLogger("fapilog").setLevel(logging.DEBUG)
```

**Queue not working:**

```python
# Check queue configuration
settings = LoggingSettings(queue_enabled=True)
configure_logging(settings=settings)

# Test queue
log.info("Queue test")
```

### Performance Issues

**High memory usage:**

```python
# Reduce queue size
settings = LoggingSettings(
    queue_maxsize=100,
    queue_batch_size=5,
    enable_resource_metrics=False
)
```

**Slow logging:**

```python
# Enable async queue
settings = LoggingSettings(
    queue_enabled=True,
    queue_overflow="drop",
    queue_batch_size=50
)
```

### Integration Issues

**FastAPI middleware not working:**

```python
# Ensure middleware is registered
from fapilog import configure_logging
app = FastAPI()
configure_logging(app=app)  # This registers middleware
```

**Custom enrichers not working:**

```python
# Clear and re-register enrichers
from fapilog.enrichers import clear_enrichers, register_enricher

clear_enrichers()
register_enricher(my_enricher)
configure_logging()
```

### Common Error Messages

**`ConfigurationError: Invalid log level 'INVALID'`**

- **Cause**: Invalid log level specified in configuration
- **Solution**: Use valid log levels: DEBUG, INFO, WARN, ERROR, CRITICAL
- **Example**: `FAPILOG_LEVEL=DEBUG` (correct) vs `FAPILOG_LEVEL=INVALID` (incorrect)

**`SinkError: Failed to write to log file`**

- **Cause**: File sink cannot write to specified location
- **Solution**: Check file permissions and directory existence
- **Example**: Ensure `/var/log/app.log` is writable

**`QueueError: Queue is full`**

- **Cause**: Log queue has reached maximum capacity
- **Solution**: Increase queue size or use overflow strategies
- **Example**: `FAPILOG_QUEUE_MAXSIZE=5000` or `FAPILOG_QUEUE_OVERFLOW=drop`

### Debug Mode

**Enable debug logging:**

```python
import logging
logging.getLogger("fapilog").setLevel(logging.DEBUG)

# Configure with debug
settings = LoggingSettings(level="DEBUG")
configure_logging(settings=settings)
```

**Test configuration:**

```python
# Test all components
log.debug("Debug test")
log.info("Info test")
log.warning("Warning test")
log.error("Error test")
```

---

## Next Steps

Now that you've learned the basics, explore these advanced topics:

- **API Reference**: [Complete technical documentation](api-reference.md)
- **Examples**: [Real-world usage patterns](examples/index.md)
- **Examples**: [Advanced capabilities and real-world patterns](examples/index.md)
- **Configuration**: [Environment setup](config.md)

### Getting Help

- **Documentation**: [API Reference](api-reference.md)
- **Examples**: Check the `examples/` directory
- **Issues**: Report bugs on GitHub
- **Discussions**: Ask questions in GitHub Discussions

Happy logging!

**See also:** [Primer](primer.md), [Quickstart](quickstart.md), [API Reference](api-reference.md), [Config](config.md), [Style Guide](style-guide.md)
