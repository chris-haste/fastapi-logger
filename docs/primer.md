# What is Fapilog?

**Fapilog** is a modern, structured logging library designed specifically for FastAPI applications and Python services. It provides JSON-structured logging with automatic context enrichment, trace correlation, and production-ready features out of the box.

---

## Core Purpose

Fapilog transforms your application logs from simple text messages into rich, structured data that's perfect for:

- **Observability** - Easy integration with monitoring systems
- **Debugging** - Automatic request correlation and context
- **Compliance** - Built-in PII redaction and audit trails
- **Performance** - Async logging with configurable queues
- **Scalability** - Multiple output sinks and container support

---

## Key Features

### Structured JSON Logging

```python
from fapilog import configure_logging, log

configure_logging()

# Automatic structured output
log.info("User action", user_id="123", action="login", duration_ms=45.2)
```

**Output:**

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "info",
  "event": "User action",
  "hostname": "server-01",
  "pid": 12345,
  "user_id": "123",
  "action": "login",
  "duration_ms": 45.2
}
```

### FastAPI Integration

```python
from fastapi import FastAPI
from fapilog import configure_logging

app = FastAPI()
configure_logging(app=app)  # Automatic middleware and context
```

### Automatic Context Enrichment

- **Request correlation** - Trace IDs across services
- **User context** - Automatic user ID and session tracking
- **Performance metrics** - Response times and resource usage
- **Environment info** - Hostname, process ID, version

### Production Ready

- **Async logging queue** - Non-blocking performance
- **Multiple sinks** - File, stdout, Loki, custom destinations
- **PII redaction** - Automatic sensitive data protection
- **Error handling** - Robust fault tolerance
- **Container support** - Multi-instance logging

---

## Quick Start

**Installation:**

```bash
pip install fapilog
```

**Basic Usage:**

```python
from fapilog import configure_logging, log

configure_logging()
log.info("Application started", version="1.0.0")
```

**FastAPI Integration:**

```python
from fastapi import FastAPI
from fapilog import configure_logging

app = FastAPI()
configure_logging(app=app)
```

For detailed tutorials, see the [User Guide](user-guide.md) and [API Reference](api-reference.md).

---

## Configuration

Fapilog is highly configurable through environment variables:

```bash
# Basic configuration
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

For complete configuration options, see the [Configuration Guide](config.md).

---

## Use Cases

### Microservices

- **Distributed tracing** across service boundaries
- **Request correlation** for debugging
- **Performance monitoring** with automatic metrics

### Web Applications

- **User session tracking** and audit trails
- **API request logging** with response times
- **Error tracking** with full context

### Data Processing

- **Batch job logging** with progress tracking
- **Resource monitoring** and performance metrics
- **Data pipeline observability**

### Compliance & Security

- **PII redaction** for privacy compliance
- **Audit logging** for security requirements
- **Structured data** for automated analysis
