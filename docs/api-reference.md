# API Reference

This document provides a complete reference for all public APIs in `fapilog`. The API is designed to be simple for basic usage while remaining fully extensible for advanced scenarios.

---

## Table of Contents

- [Core Functions](#core-functions)
- [Configuration](#configuration)
- [Logging Interface](#logging-interface)
- [Middleware](#middleware)
- [Enrichers](#enrichers)
- [Sinks](#sinks)
- [Context Management](#context-management)
- [Types and Models](#types-and-models)

---

## Core Functions

### `configure_logging()`

The primary function for setting up structured logging in your application.

```python
from fapilog import configure_logging

# Basic usage with defaults
configure_logging()

# With FastAPI app (automatically adds middleware)
from fastapi import FastAPI
app = FastAPI()
configure_logging(app=app)

# With custom settings
from fapilog.settings import LoggingSettings
settings = LoggingSettings(level="DEBUG", queue_enabled=True)
configure_logging(settings=settings)
```

**Parameters:**

- `level` (str, optional): Logging level override. Defaults to `None` (uses settings).
- `sinks` (Dict[str, Any], optional): Sink configurations. **Deprecated** - use `LoggingSettings` instead.
- `json_console` (str, optional): Console output format override. **Deprecated** - use `LoggingSettings` instead.
- `settings` (LoggingSettings, optional): Complete configuration object. If `None`, created from environment variables.
- `app` (Any, optional): FastAPI app instance. If provided, `TraceIDMiddleware` is automatically registered.

**Returns:**

- `structlog.BoundLogger`: Configured logger instance

**Raises:**

- `RuntimeError`: If called from an async context without proper setup

**Notes:**

- This function is idempotent - subsequent calls will not duplicate handlers
- When `app` is provided, middleware is registered and shutdown handlers are configured
- Environment variables with `FAPILOG_` prefix are automatically loaded

### `reset_logging()`

Reset logging configuration for testing purposes.

```python
from fapilog import reset_logging

# Reset all configuration
reset_logging()
```

**Use Cases:**

- Unit testing to ensure clean state between tests
- Development environments where you need to reconfigure logging
- Debugging configuration issues

---

## Configuration

### `LoggingSettings`

Pydantic-based configuration model that maps environment variables to logging behavior.

```python
from fapilog.settings import LoggingSettings

# Create from environment variables (default)
settings = LoggingSettings()

# Create with custom values
settings = LoggingSettings(
    level="DEBUG",
    sinks=["stdout", "loki"],
    json_console="pretty",
    queue_enabled=True,
    queue_maxsize=2000,
    sampling_rate=0.5
)
```

**Fields:**

| Field                     | Type      | Default      | Description                                        |
| ------------------------- | --------- | ------------ | -------------------------------------------------- |
| `level`                   | str       | `"INFO"`     | Logging level (DEBUG, INFO, WARN, ERROR, CRITICAL) |
| `sinks`                   | List[str] | `["stdout"]` | List of sink names for log output                  |
| `json_console`            | str       | `"auto"`     | Console format (auto, json, pretty)                |
| `redact_patterns`         | List[str] | `[]`         | Regex patterns to redact from logs                 |
| `sampling_rate`           | float     | `1.0`        | Log sampling rate (0.0 to 1.0)                     |
| `queue_enabled`           | bool      | `True`       | Enable async queue for non-blocking logging        |
| `queue_maxsize`           | int       | `1000`       | Maximum size of async log queue                    |
| `queue_overflow`          | str       | `"drop"`     | Queue overflow strategy (drop, block, sample)      |
| `queue_batch_size`        | int       | `10`         | Events per batch                                   |
| `queue_batch_timeout`     | float     | `1.0`        | Batch timeout in seconds                           |
| `queue_retry_delay`       | float     | `1.0`        | Retry delay in seconds                             |
| `queue_max_retries`       | int       | `3`          | Maximum retries per event                          |
| `enable_resource_metrics` | bool      | `False`      | Enable memory/CPU metrics in logs                  |

**Environment Variables:**

All fields can be configured via environment variables with the `FAPILOG_` prefix:

```bash
export FAPILOG_LEVEL=DEBUG
export FAPILOG_QUEUE_ENABLED=true
export FAPILOG_QUEUE_MAXSIZE=2000
export FAPILOG_SINKS=stdout,loki
```

---

## Logging Interface

### `log`

The main logger instance that provides structured logging capabilities.

```python
from fapilog import log

# Basic logging
log.info("User logged in")
log.error("Database connection failed")

# Structured logging with key-value pairs
log.info("User action", user_id="123", action="login", ip="192.168.1.1")
log.error("API error", status_code=500, endpoint="/api/users", error="timeout")

# Logging with context
log.warning("High memory usage", memory_mb=1024, threshold=512)
log.debug("Processing request", request_id="abc123", duration_ms=45.2)
```

**Available Methods:**

- `log.debug(message, **kwargs)` - Debug level logging
- `log.info(message, **kwargs)` - Info level logging
- `log.warning(message, **kwargs)` - Warning level logging
- `log.error(message, **kwargs)` - Error level logging
- `log.critical(message, **kwargs)` - Critical level logging

**Features:**

- **Structured Output**: All logs are JSON objects in production
- **Context Enrichment**: Automatically includes trace_id, hostname, PID, etc.
- **Async Safe**: Non-blocking logging via background queue
- **Pretty Console**: Human-readable output in development

**Example Output:**

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "info",
  "event": "User logged in",
  "trace_id": "abc123def456",
  "span_id": "789ghi012jkl",
  "hostname": "server-01",
  "pid": 12345,
  "user_id": "123",
  "action": "login",
  "ip": "192.168.1.1"
}
```

---

## Middleware

### `TraceIDMiddleware`

FastAPI middleware that provides request correlation and timing.

```python
from fapilog.middleware import TraceIDMiddleware
from fastapi import FastAPI

app = FastAPI()

# Add middleware manually
app.add_middleware(TraceIDMiddleware)

# Or automatically via configure_logging
from fapilog import configure_logging
configure_logging(app=app)
```

**Features:**

- **Trace Correlation**: Generates or forwards trace_id from `X-Trace-Id` header
- **Span Generation**: Creates unique span_id for each request
- **Request Timing**: Measures and logs request latency
- **Response Headers**: Adds correlation headers to responses
- **Context Isolation**: Ensures clean context between requests

**Response Headers:**

- `X-Trace-Id`: Request trace identifier
- `X-Span-Id`: Request span identifier
- `X-Response-Time-ms`: Request latency in milliseconds

**Captured Metadata:**

- Request path and method
- HTTP status code
- Request/response body sizes
- User-Agent header
- Request latency
- Error details (if applicable)

### `add_trace_exception_handler()`

Register a custom exception handler that adds trace headers to error responses.

```python
from fapilog.middleware import add_trace_exception_handler
from fastapi import FastAPI

app = FastAPI()
add_trace_exception_handler(app)
```

**Features:**

- Adds trace headers to 500 error responses
- Preserves original error handling
- Includes latency information in error responses

---

## Enrichers

Enrichers add metadata to log events automatically. Built-in enrichers provide system and request information.

### Built-in Enrichers

#### `host_process_enricher()`

Adds hostname and process ID to all log events.

```python
# Automatically applied - no manual configuration needed
```

**Added Fields:**

- `hostname`: System hostname
- `pid`: Process ID

#### `resource_snapshot_enricher()`

Adds memory and CPU usage metrics to log events.

```python
# Enable via settings
settings = LoggingSettings(enable_resource_metrics=True)
configure_logging(settings=settings)
```

**Added Fields:**

- `memory_mb`: Resident memory usage in MB
- `cpu_percent`: Process CPU usage percentage

#### `body_size_enricher()`

Adds request and response body sizes to log events.

```python
# Automatically applied when TraceIDMiddleware is used
```

**Added Fields:**

- `req_bytes`: Request body size in bytes
- `res_bytes`: Response body size in bytes

#### `request_response_enricher()`

Adds comprehensive request/response metadata to log events.

```python
# Automatically applied when TraceIDMiddleware is used
```

**Added Fields:**

- `status_code`: HTTP status code
- `latency_ms`: Request latency in milliseconds
- `req_bytes`: Request body size
- `res_bytes`: Response body size
- `user_agent`: User-Agent header value

### Custom Enrichers

Register custom enrichers to add application-specific metadata.

```python
from fapilog.enrichers import register_enricher

@register_enricher
def user_context_enricher(logger, method_name, event_dict):
    """Add user context from session."""
    # Get user from your session/context
    user = get_current_user()
    if user:
        event_dict["user_id"] = user.id
        event_dict["user_role"] = user.role
    return event_dict

@register_enricher
def application_enricher(logger, method_name, event_dict):
    """Add application-specific metadata."""
    event_dict["app_version"] = "1.2.3"
    event_dict["environment"] = "production"
    return event_dict
```

**Enricher Function Signature:**

```python
def enricher_function(logger, method_name, event_dict):
    """
    Args:
        logger: The logger instance
        method_name: The logging method name (info, error, etc.)
        event_dict: The event dictionary to enrich

    Returns:
        The enriched event dictionary
    """
    # Add your fields to event_dict
    event_dict["custom_field"] = "value"
    return event_dict
```

### Enricher Management

```python
from fapilog.enrichers import register_enricher, clear_enrichers

# Register multiple enrichers
register_enricher(custom_enricher_1)
register_enricher(custom_enricher_2)

# Clear all custom enrichers (for testing)
clear_enrichers()
```

---

## Sinks

Sinks handle writing log events to different destinations. Built-in sinks provide common output targets.

### Built-in Sinks

#### `StdoutSink`

Writes log events to stdout with JSON or pretty formatting.

```python
from fapilog.sinks.stdout import StdoutSink

# JSON output (production)
sink = StdoutSink(pretty=False)

# Pretty output (development)
sink = StdoutSink(pretty=True)
```

**Features:**

- JSON or pretty console output
- Automatic flushing
- Thread-safe writing
- Configurable via `LoggingSettings.json_console`

### Custom Sinks

Create custom sinks for specific output destinations.

```python
from fapilog._internal.queue import Sink
import httpx

class HTTPApiSink(Sink):
    """Send logs to HTTP API endpoint."""

    def __init__(self, url: str, api_key: str):
        self.url = url
        self.api_key = api_key
        self.client = httpx.AsyncClient()

    async def write(self, event_dict):
        """Write log event to HTTP API."""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        await self.client.post(self.url, json=event_dict, headers=headers)

    async def close(self):
        """Clean up resources."""
        await self.client.aclose()

class FileSink(Sink):
    """Write logs to rotating files."""

    def __init__(self, filename: str):
        self.filename = filename

    async def write(self, event_dict):
        """Write log event to file."""
        import json
        with open(self.filename, "a") as f:
            f.write(json.dumps(event_dict) + "\n")

    async def close(self):
        """Clean up resources."""
        pass
```

**Sink Interface:**

```python
from fapilog._internal.queue import Sink

class CustomSink(Sink):
    async def write(self, event_dict):
        """
        Write a log event.

        Args:
            event_dict: The structured log event dictionary
        """
        # Your sink implementation
        pass

    async def close(self):
        """Clean up resources when sink is closed."""
        pass
```

---

## Context Management

Context management allows you to add request-scoped metadata to all log events.

### `bind_context()`

Bind context variables that will be included in all subsequent log events.

```python
from fapilog._internal.context import bind_context

# Bind single variable
bind_context(user_id="123")

# Bind multiple variables
bind_context(
    user_id="123",
    session_id="abc456",
    request_id="req789",
    tenant="acme-corp"
)

# All subsequent logs will include these fields
log.info("User action")  # Includes user_id, session_id, etc.
```

### `get_context()`

Get the current context variables.

```python
from fapilog._internal.context import get_context

context = get_context()
print(context)  # {'user_id': '123', 'session_id': 'abc456', ...}
```

### `clear_context()`

Clear all context variables.

```python
from fapilog._internal.context import clear_context

# Clear context (useful for testing or request cleanup)
clear_context()
```

**Context Variables:**

Common context variables set by middleware:

- `trace_id`: Request trace identifier
- `span_id`: Request span identifier
- `req_bytes`: Request body size
- `res_bytes`: Response body size
- `status_code`: HTTP status code
- `latency_ms`: Request latency
- `user_agent`: User-Agent header

**Best Practices:**

- Use context for request-scoped data
- Clear context between requests in long-running processes
- Avoid storing large objects in context
- Use descriptive variable names

---

## Types and Models

### `Sink`

Base class for all log sinks.

```python
from fapilog._internal.queue import Sink

class MySink(Sink):
    async def write(self, event_dict):
        # Implementation
        pass

    async def close(self):
        # Cleanup
        pass
```

### `QueueWorker`

Manages the async log queue and sink processing.

```python
from fapilog._internal.queue import QueueWorker

# Usually managed internally, but can be customized
worker = QueueWorker(
    sinks=[my_sink],
    queue_size=1000,
    batch_size=10,
    batch_timeout=1.0
)
```

### Environment Variables

All configuration can be set via environment variables:

| Variable                          | Default  | Description                    |
| --------------------------------- | -------- | ------------------------------ |
| `FAPILOG_LEVEL`                   | `INFO`   | Logging level                  |
| `FAPILOG_SINKS`                   | `stdout` | Comma-separated sink list      |
| `FAPILOG_JSON_CONSOLE`            | `auto`   | Console format                 |
| `FAPILOG_QUEUE_ENABLED`           | `true`   | Enable async queue             |
| `FAPILOG_QUEUE_MAXSIZE`           | `1000`   | Queue maximum size             |
| `FAPILOG_QUEUE_OVERFLOW`          | `drop`   | Queue overflow strategy        |
| `FAPILOG_QUEUE_BATCH_SIZE`        | `10`     | Events per batch               |
| `FAPILOG_QUEUE_BATCH_TIMEOUT`     | `1.0`    | Batch timeout (seconds)        |
| `FAPILOG_QUEUE_RETRY_DELAY`       | `1.0`    | Retry delay (seconds)          |
| `FAPILOG_QUEUE_MAX_RETRIES`       | `3`      | Maximum retries                |
| `FAPILOG_SAMPLING_RATE`           | `1.0`    | Log sampling rate              |
| `FAPILOG_ENABLE_RESOURCE_METRICS` | `false`  | Enable resource metrics        |
| `FAPILOG_REDACT_PATTERNS`         | ``       | Comma-separated regex patterns |

---

## Error Handling

### Common Exceptions

**`RuntimeError`**

- Raised when `configure_logging()` is called from async context without proper setup
- Solution: Ensure proper async context or use sync configuration

**`ValueError`**

- Raised for invalid configuration values
- Common causes: Invalid log level, invalid queue settings
- Solution: Check configuration values and environment variables

**`ImportError`**

- Raised when optional dependencies are missing
- Common with `psutil` for resource metrics
- Solution: Install required dependencies or disable features

### Debugging Configuration

```python
import logging

# Enable debug logging for fapilog itself
logging.getLogger("fapilog").setLevel(logging.DEBUG)

# Check configuration
from fapilog.settings import LoggingSettings
settings = LoggingSettings()
print(settings.model_dump())
```

---

## Performance Considerations

### Queue Configuration

For high-throughput applications:

```python
settings = LoggingSettings(
    queue_maxsize=5000,        # Larger queue
    queue_batch_size=50,       # Larger batches
    queue_batch_timeout=0.5,   # Shorter timeout
    queue_overflow="drop"      # Drop logs under load
)
```

### Sampling

For very high-volume logging:

```python
settings = LoggingSettings(
    sampling_rate=0.1,  # Log only 10% of events
    queue_overflow="sample"  # Adaptive sampling under load
)
```

### Resource Metrics

Enable only when needed:

```python
settings = LoggingSettings(
    enable_resource_metrics=False  # Disable for performance
)
```

---

## Migration Guide

### From Standard Logging

```python
# Before
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("User logged in")

# After
from fapilog import configure_logging, log
configure_logging()
log.info("User logged in")
```

### From Structlog

```python
# Before
import structlog
structlog.configure(processors=[...])
logger = structlog.get_logger()
logger.info("User logged in")

# After
from fapilog import configure_logging, log
configure_logging()
log.info("User logged in")
```

### From Custom Middleware

```python
# Before
@app.middleware("http")
async def add_trace_id(request, call_next):
    # Custom trace ID logic
    pass

# After
from fapilog import configure_logging
configure_logging(app=app)  # Automatic trace ID handling
```
