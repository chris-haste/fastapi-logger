# API Reference

This document provides a complete reference for all public APIs in `fapilog`. The API is designed to be simple for basic usage while remaining fully extensible for advanced scenarios.

---

## Table of Contents

- [Core Functions](#core-functions)
- [Configuration](#configuration)
- [Logging Interface](#logging-interface)
- [Middleware](#middleware)
- [Trace Propagation](#trace-propagation)
- [Enrichers](#enrichers)
- [Sinks](#sinks)
- [Metrics and Monitoring](#metrics-and-monitoring)
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

### `get_current_trace_id()`

Access the current trace ID from within a request context (Story 6.2).

```python
from fapilog import get_current_trace_id

@app.get("/api/status")
async def get_status():
    trace_id = get_current_trace_id()

    if trace_id:
        log.info("Status check requested", trace_id=trace_id)
        return {"status": "ok", "trace_id": trace_id}
    else:
        log.info("Status check outside request context")
        return {"status": "ok", "trace_id": None}
```

**Returns:**

- `str | None`: Current trace ID if within a request context, `None` otherwise

**Use Cases:**

- Business logic that needs to include trace ID in responses
- Custom error handling with trace correlation
- Integration with external services requiring trace headers
- Audit logging with request correlation

**Notes:**

- Only available within request context (when using `TraceIDMiddleware`)
- Returns `None` when called outside of a request (e.g., startup, background tasks)
- The trace ID is either extracted from incoming headers or auto-generated
- Thread-safe and async-safe via `contextvars`

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

| Field                            | Type      | Default          | Description                                                             |
| -------------------------------- | --------- | ---------------- | ----------------------------------------------------------------------- |
| `level`                          | str       | `"INFO"`         | Logging level (DEBUG, INFO, WARN, ERROR, CRITICAL)                      |
| `sinks`                          | List[str] | `["stdout"]`     | List of sink names for log output                                       |
| `json_console`                   | str       | `"auto"`         | Console format (auto, json, pretty)                                     |
| `redact_patterns`                | List[str] | `[]`             | Regex patterns to redact from logs                                      |
| `redact_fields`                  | List[str] | `[]`             | Field names to redact (supports dot notation for nested fields)         |
| `redact_replacement`             | str       | `"REDACTED"`     | Replacement value for redacted fields                                   |
| `redact_level`                   | str       | `"INFO"`         | Minimum log level for redaction (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `sampling_rate`                  | float     | `1.0`            | Log sampling rate (0.0 to 1.0)                                          |
| `queue_enabled`                  | bool      | `True`           | Enable async queue for non-blocking logging                             |
| `queue_maxsize`                  | int       | `1000`           | Maximum size of async log queue                                         |
| `queue_overflow`                 | str       | `"drop"`         | Queue overflow strategy (drop, block, sample)                           |
| `queue_batch_size`               | int       | `10`             | Events per batch                                                        |
| `queue_batch_timeout`            | float     | `1.0`            | Batch timeout in seconds                                                |
| `queue_retry_delay`              | float     | `1.0`            | Retry delay in seconds                                                  |
| `queue_max_retries`              | int       | `3`              | Maximum retries per event                                               |
| `enable_resource_metrics`        | bool      | `False`          | Enable memory/CPU metrics in logs                                       |
| `metrics_enabled`                | bool      | `False`          | Enable comprehensive metrics collection                                 |
| `metrics_sample_window`          | int       | `100`            | Number of samples for averaging metrics                                 |
| `metrics_prometheus_enabled`     | bool      | `False`          | Enable Prometheus HTTP endpoint                                         |
| `metrics_prometheus_port`        | int       | `8000`           | Port for Prometheus metrics endpoint                                    |
| `metrics_prometheus_host`        | str       | `"0.0.0.0"`      | Host for Prometheus metrics endpoint                                    |
| `trace_id_header`                | str       | `"X-Request-ID"` | HTTP header name for incoming trace ID                                  |
| `enable_httpx_trace_propagation` | bool      | `False`          | Enable automatic trace ID propagation in httpx                          |
| `user_context_enabled`           | bool      | `True`           | Enable user context enrichment (user_id, roles, auth_scheme)            |

**Environment Variables:**

All fields can be configured via environment variables with the `FAPILOG_` prefix:

```bash
export FAPILOG_LEVEL=DEBUG
export FAPILOG_QUEUE_ENABLED=true
export FAPILOG_QUEUE_MAXSIZE=2000
export FAPILOG_SINKS=stdout,loki
export FAPILOG_REDACT_LEVEL=INFO
export FAPILOG_TRACE_ID_HEADER=X-Custom-Trace-ID
export FAPILOG_ENABLE_HTTPX_TRACE_PROPAGATION=true
export FAPILOG_USER_CONTEXT_ENABLED=true
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

- **Trace Correlation**: Generates or forwards trace_id from configurable header (default: `X-Request-ID`)
- **Span Generation**: Creates unique span_id for each request
- **Request Timing**: Measures and logs request latency
- **Request Context Enrichment**: Captures comprehensive request metadata (method, path, client_ip, status_code, etc.)
- **Response Headers**: Adds correlation headers to responses
- **Context Isolation**: Ensures clean context between requests

**Constructor Parameters:**

- `trace_id_header` (str, optional): HTTP header name for incoming trace ID. Defaults to `"X-Request-ID"`.

**Response Headers:**

- `X-Trace-Id`: Request trace identifier (echoed back)
- `X-Span-Id`: Request span identifier
- `X-Response-Time-ms`: Request latency in milliseconds

**Captured Metadata (automatically added to log context):**

- `trace_id`: Request correlation identifier
- `span_id`: Request span identifier
- `method`: HTTP method (GET, POST, etc.)
- `path`: Request path
- `client_ip`: Client IP address
- `status_code`: HTTP response status code
- `latency_ms`: Request duration in milliseconds
- `req_bytes`: Request body size in bytes
- `res_bytes`: Response body size in bytes
- `user_agent`: User-Agent header value

**Configuration via Settings:**

```python
from fapilog.settings import LoggingSettings

# Configure custom trace header
settings = LoggingSettings(trace_id_header="X-Custom-Trace-ID")
configure_logging(settings=settings, app=app)
```

**Environment Variable:**

```bash
export FAPILOG_TRACE_ID_HEADER=X-Custom-Trace-ID
```

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

## Trace Propagation

### HTTP Request Trace Propagation (Story 6.2)

Automatic trace ID propagation for outgoing HTTP requests made with `httpx.AsyncClient`.

```python
from fapilog.settings import LoggingSettings
from fapilog import configure_logging
import httpx

# Enable httpx trace propagation
settings = LoggingSettings(
    enable_httpx_trace_propagation=True,
    trace_id_header="X-Request-ID"  # Header used for propagation
)
configure_logging(settings=settings, app=app)

# Now all httpx requests automatically include trace ID
async with httpx.AsyncClient() as client:
    # This request will automatically include the X-Request-ID header
    # with the current trace ID value
    response = await client.get("https://api.example.com/data")
```

**Features:**

- **Automatic Headers**: Outgoing requests include current trace ID in configured header
- **Opt-in**: Must be explicitly enabled via settings to avoid side effects
- **Thread-safe**: Works correctly with concurrent requests
- **Graceful Fallback**: No errors if httpx is not installed

**Configuration:**

```python
# Via LoggingSettings
settings = LoggingSettings(
    enable_httpx_trace_propagation=True,  # Enable the feature
    trace_id_header="X-Custom-Trace"      # Custom header name
)

# Via environment variables
export FAPILOG_ENABLE_HTTPX_TRACE_PROPAGATION=true
export FAPILOG_TRACE_ID_HEADER=X-Custom-Trace
```

**Requirements:**

- `httpx` must be installed: `pip install httpx`
- Feature must be enabled in settings
- Must be within a request context (trace ID available)

**Use Cases:**

- **Distributed Tracing**: Correlate requests across microservices
- **API Gateway Integration**: Maintain trace continuity through service mesh
- **External Service Calls**: Include correlation IDs in third-party API calls
- **Debugging**: Follow request flow through multiple services

**Notes:**

- Only applied when `get_current_trace_id()` returns a valid trace ID
- Header is only added if not already present in the request
- Works with both sync and async httpx clients
- Minimal performance overhead

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

## Metrics and Monitoring

The metrics and monitoring system provides comprehensive performance tracking for queue operations, sink performance, and overall logging health.

### `fapilog.monitoring`

Main module for Prometheus metrics export and monitoring functionality.

#### `start_metrics_server()`

Start a Prometheus metrics HTTP server for scraping.

```python
from fapilog.monitoring import start_metrics_server

# Start metrics server on default port 8000
exporter = await start_metrics_server()

# Start on custom host/port
exporter = await start_metrics_server(
    host="127.0.0.1",
    port=9090,
    path="/custom-metrics"
)
```

**Parameters:**

- `host` (str, optional): Host to bind to. Default: `"0.0.0.0"`
- `port` (int, optional): Port to bind to. Default: `8000`
- `path` (str, optional): HTTP path for metrics endpoint. Default: `"/metrics"`

**Returns:**

- `PrometheusExporter`: The metrics exporter instance, or `None` if failed

#### `get_metrics_text()`

Get current metrics in Prometheus text format.

```python
from fapilog.monitoring import get_metrics_text

# Get Prometheus-formatted metrics
metrics_text = get_metrics_text()
print(metrics_text)
```

**Returns:**

- `str`: Metrics in Prometheus format

#### `get_metrics_dict()`

Get current metrics as a structured dictionary.

```python
from fapilog.monitoring import get_metrics_dict

# Get metrics as dictionary
metrics = get_metrics_dict()
print(f"Queue size: {metrics['queue']['size']}")
print(f"Total events: {metrics['performance']['total_log_events']}")
```

**Returns:**

- `dict`: Structured metrics data with queue, sinks, and performance sections

### `fapilog._internal.metrics`

Internal metrics collection system (advanced usage).

#### `create_metrics_collector()`

Create and configure a global metrics collector.

```python
from fapilog._internal.metrics import create_metrics_collector

# Create with defaults
collector = create_metrics_collector(enabled=True)

# Create with custom sample window
collector = create_metrics_collector(
    enabled=True,
    sample_window=200
)
```

**Parameters:**

- `enabled` (bool): Whether to enable metrics collection
- `sample_window` (int): Number of samples for moving averages

**Returns:**

- `MetricsCollector`: The metrics collector instance

### Available Metrics

The metrics system provides comprehensive tracking across multiple categories:

#### Queue Metrics

- `fapilog_queue_size`: Current queue size (gauge)
- `fapilog_queue_peak_size`: Peak queue size (gauge)
- `fapilog_queue_enqueued_total`: Total events enqueued (counter)
- `fapilog_queue_dequeued_total`: Total events dequeued (counter)
- `fapilog_queue_dropped_total`: Total events dropped (counter)
- `fapilog_queue_enqueue_latency_ms`: Average enqueue latency (gauge)
- `fapilog_queue_memory_bytes`: Queue memory usage (gauge)

#### Sink Metrics

Per-sink metrics with `sink` label:

- `fapilog_sink_writes_total{sink="..."}`: Total writes per sink (counter)
- `fapilog_sink_successes_total{sink="..."}`: Total successful writes (counter)
- `fapilog_sink_failures_total{sink="..."}`: Total failed writes (counter)
- `fapilog_sink_success_rate{sink="..."}`: Success rate ratio (gauge)
- `fapilog_sink_latency_ms{sink="..."}`: Average write latency (gauge)

#### Performance Metrics

- `fapilog_events_total`: Total log events processed (counter)
- `fapilog_events_per_second`: Current throughput (gauge)
- `fapilog_memory_bytes`: Process memory usage (gauge)
- `fapilog_cpu_percent`: Process CPU usage (gauge)

### Configuration

Enable metrics through settings:

```python
from fapilog.settings import LoggingSettings

settings = LoggingSettings(
    # Enable metrics collection
    metrics_enabled=True,

    # Enable Prometheus HTTP endpoint
    metrics_prometheus_enabled=True,
    metrics_prometheus_port=8000,
    metrics_prometheus_host="0.0.0.0",

    # Configure sampling window
    metrics_sample_window=100
)
```

Or via environment variables:

```bash
export FAPILOG_METRICS_ENABLED=true
export FAPILOG_METRICS_PROMETHEUS_ENABLED=true
export FAPILOG_METRICS_PROMETHEUS_PORT=8000
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

| Variable                                 | Default        | Description                           |
| ---------------------------------------- | -------------- | ------------------------------------- |
| `FAPILOG_LEVEL`                          | `INFO`         | Logging level                         |
| `FAPILOG_SINKS`                          | `stdout`       | Comma-separated sink list             |
| `FAPILOG_JSON_CONSOLE`                   | `auto`         | Console format                        |
| `FAPILOG_QUEUE_ENABLED`                  | `true`         | Enable async queue                    |
| `FAPILOG_QUEUE_MAXSIZE`                  | `1000`         | Queue maximum size                    |
| `FAPILOG_QUEUE_OVERFLOW`                 | `drop`         | Queue overflow strategy               |
| `FAPILOG_QUEUE_BATCH_SIZE`               | `10`           | Events per batch                      |
| `FAPILOG_QUEUE_BATCH_TIMEOUT`            | `1.0`          | Batch timeout (seconds)               |
| `FAPILOG_QUEUE_RETRY_DELAY`              | `1.0`          | Retry delay (seconds)                 |
| `FAPILOG_QUEUE_MAX_RETRIES`              | `3`            | Maximum retries                       |
| `FAPILOG_SAMPLING_RATE`                  | `1.0`          | Log sampling rate                     |
| `FAPILOG_ENABLE_RESOURCE_METRICS`        | `false`        | Enable resource metrics               |
| `FAPILOG_METRICS_ENABLED`                | `false`        | Enable comprehensive metrics          |
| `FAPILOG_METRICS_SAMPLE_WINDOW`          | `100`          | Metrics sample window size            |
| `FAPILOG_METRICS_PROMETHEUS_ENABLED`     | `false`        | Enable Prometheus endpoint            |
| `FAPILOG_METRICS_PROMETHEUS_PORT`        | `8000`         | Prometheus endpoint port              |
| `FAPILOG_METRICS_PROMETHEUS_HOST`        | `0.0.0.0`      | Prometheus endpoint host              |
| `FAPILOG_TRACE_ID_HEADER`                | `X-Request-ID` | HTTP header for trace ID              |
| `FAPILOG_ENABLE_HTTPX_TRACE_PROPAGATION` | `false`        | Enable httpx propagation              |
| `FAPILOG_REDACT_PATTERNS`                | ``             | Comma-separated regex patterns        |
| `FAPILOG_REDACT_FIELDS`                  | ``             | Comma-separated field names to redact |
| `FAPILOG_REDACT_REPLACEMENT`             | `REDACTED`     | Replacement value for redacted fields |
| `FAPILOG_REDACT_LEVEL`                   | `INFO`         | Minimum log level for redaction       |

---

## Error Handling

### Custom Exception Classes

`fapilog` provides a comprehensive set of custom exceptions for different error scenarios:

**`FapilogError`** - Base exception class for all fapilog errors

**`ConfigurationError`** - Configuration and settings errors

```python
from fapilog.exceptions import ConfigurationError

# Invalid log level
ConfigurationError("Invalid log level 'INVALID'", expected_type="str", actual_value="INVALID")

# Missing required dependency
ConfigurationError("httpx is required for LokiSink", missing_dependency="httpx")
```

**`SinkError`** - Sink-related errors (file, stdout, loki, custom sinks)

```python
from fapilog.exceptions import SinkError

# File sink error
SinkError("Failed to write to log file", sink_type="file", operation="write", error="Permission denied")

# Loki sink error
SinkError("HTTP request failed", sink_type="loki", operation="send", status_code=500)
```

**`QueueError`** - Queue and worker-related errors

```python
from fapilog.exceptions import QueueError

# Queue full
QueueError("Queue is full", queue_size=1000, max_size=1000, operation="enqueue")

# Worker shutdown error
QueueError("Worker shutdown failed", operation="shutdown", error="Timeout")
```

**`MiddlewareError`** - Middleware and context errors

```python
from fapilog.exceptions import MiddlewareError

# Context binding error
MiddlewareError("Failed to bind context", operation="bind_context", error="Invalid key")

# Trace propagation error
MiddlewareError("Trace propagation failed", operation="propagate_trace", error="Invalid header")
```

**`RedactionError`** - Data redaction errors

```python
from fapilog.exceptions import RedactionError

# Pattern compilation error
RedactionError("Invalid regex pattern", pattern="[invalid", operation="compile_pattern")

# Field redaction error
RedactionError("Failed to redact field", field="user.password", operation="redact_field")
```

**`ContextError`** - Context management errors

```python
from fapilog.exceptions import ContextError

# Context variable error
ContextError("Invalid context variable", variable="invalid_key", operation="get_context")

# Context cleanup error
ContextError("Failed to clear context", operation="clear_context", error="Timeout")
```

### Error Context and Recovery

All exceptions include rich context information:

```python
try:
    configure_logging(settings=invalid_settings)
except ConfigurationError as e:
    print(f"Error: {e}")
    print(f"Operation: {e.operation}")
    print(f"Context: {e.context}")
    print(f"User-friendly message: {e.user_friendly_message}")
```

### Graceful Degradation

The library implements graceful degradation for non-critical errors:

- **Sink failures** don't break the entire logging system
- **Queue errors** fall back to synchronous logging
- **Middleware errors** continue without context enrichment
- **Redaction errors** log the original data without redaction

### Retry Mechanisms

Automatic retry with exponential backoff for transient failures:

```python
# Loki sink automatically retries failed HTTP requests
# Queue worker retries failed sink operations
# Configuration errors are logged but don't break startup
```

### Legacy Exceptions

For backward compatibility, some operations may still raise standard exceptions:

**`RuntimeError`** - Async context issues
**`ValueError`** - Invalid parameter values  
**`ImportError`** - Missing optional dependencies

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

## Container Architecture

### LoggingContainer

The `LoggingContainer` class provides advanced dependency injection and multiple configuration support.

```python
class LoggingContainer:
    def __init__(self, settings: Optional[LoggingSettings] = None) -> None
    def configure(
        self,
        level: Optional[str] = None,
        json_console: Optional[str] = None,
        sinks: Optional[Dict[str, Any]] = None,
        settings: Optional[LoggingSettings] = None,
        app: Optional[Any] = None,
    ) -> structlog.BoundLogger
    async def shutdown(self) -> None
    def shutdown_sync(self) -> None
    def reset(self) -> None

    @property
    def settings(self) -> LoggingSettings
    @property
    def is_configured(self) -> bool
    @property
    def queue_worker(self) -> Optional[QueueWorker]
```

**Key Methods:**

#### **init**(settings)

Initialize a new logging container.

**Parameters:**

- `settings`: Optional LoggingSettings instance

#### configure(...)

Configure the container. Parameters same as `configure_logging()`.

**Returns:** Configured structlog.BoundLogger

#### shutdown() / shutdown_sync()

Gracefully shutdown the container and clean up resources.

#### reset()

Reset the container configuration for testing.

**Example:**

```python
from fapilog.container import LoggingContainer
from fapilog.settings import LoggingSettings

# Create container with custom settings
settings = LoggingSettings(
    level="INFO",
    sinks=["stdout", "file:///var/log/app.log"],
    queue_enabled=True
)
container = LoggingContainer(settings)
logger = container.configure()

# Use logger
logger.info("Application started")

# Clean shutdown
container.shutdown_sync()
```

### Container Management Functions

#### cleanup_all_containers()

```python
def cleanup_all_containers() -> None
```

Clean up all container instances. Automatically called on process exit.

**Example:**

```python
from fapilog.container import cleanup_all_containers

# Manual cleanup (usually not needed)
cleanup_all_containers()
```

## Settings

### LoggingSettings

Comprehensive configuration class using Pydantic v2.

```python
class LoggingSettings(BaseSettings):
    # Basic Configuration
    level: str = "INFO"
    json_console: str = "auto"

    # Queue Configuration
    queue_enabled: bool = False
    queue_maxsize: int = 1000
    queue_batch_size: int = 10
    queue_batch_timeout: float = 1.0
    queue_overflow: Literal["drop", "block", "sample"] = "drop"
    queue_retry_delay: float = 1.0
    queue_max_retries: int = 3

    # Sink Configuration
    sinks: List[str] = ["stdout"]

    # Security Configuration
    redact_fields: List[str] = []
    redact_patterns: List[str] = []
    redact_level: str = "INFO"
    enable_auto_pii_redaction: bool = False

    # Trace Configuration
    enable_httpx_trace_propagation: bool = False
    trace_id_header: str = "X-Request-ID"

    # Performance Configuration
    sampling_rate: float = 1.0
    enable_resource_metrics: bool = False
```

**Environment Variables:**
All settings can be configured via environment variables with `FAPILOG_` prefix:

```bash
export FAPILOG_LEVEL=DEBUG
export FAPILOG_SINKS="stdout,file:///var/log/app.log"
export FAPILOG_QUEUE_ENABLED=true
```

## Context Utilities

### get_context()

```python
def get_context() -> Dict[str, Any]
```

Get current request context variables.

**Returns:** Dictionary containing trace_id, span_id, user_id, etc.

### bind_context()

```python
def bind_context(
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None,
    user_id: Optional[str] = None,
    **kwargs
) -> None
```

Bind values to the current request context.

### clear_context()

```python
def clear_context() -> None
```

Clear all context variables.

### context_copy()

```python
def context_copy() -> contextvars.Context
```

Create a copy of current context for background tasks.

**Example:**

```python
import asyncio
from fapilog import get_context, context_copy

async def background_task():
    # Context is preserved from parent task
    context = get_context()
    print(f"Background task trace_id: {context['trace_id']}")

# In request handler
context = context_copy()
asyncio.create_task(context.run(background_task))
```

## Enrichers

### register_enricher()

```python
def register_enricher(enricher_func: Callable) -> None
```

Register a custom enricher function.

**Parameters:**

- `enricher_func`: Function with signature `(logger, method_name, event_dict) -> event_dict`

### clear_enrichers()

```python
def clear_enrichers() -> None
```

Clear all registered enrichers.

**Example:**

```python
from fapilog.enrichers import register_enricher

def tenant_enricher(logger, method_name, event_dict):
    event_dict["tenant_id"] = get_current_tenant_id()
    return event_dict

register_enricher(tenant_enricher)
```

## User Context

### create_user_dependency()

```python
def create_user_dependency(get_user_func: Callable) -> Callable
```

Create a FastAPI dependency for user context enrichment.

**Example:**

```python
from fastapi import Depends
from fapilog.enrichers import create_user_dependency

async def get_current_user():
    return {"id": "user123", "roles": ["admin"]}

UserDep = create_user_dependency(get_current_user)

@app.get("/protected")
async def protected_route(user=Depends(UserDep)):
    # User context automatically added to logs
    logger.info("Protected route accessed")
```

## Trace Propagation

### get_current_trace_id()

```python
def get_current_trace_id() -> Optional[str]
```

Get the current trace ID from context.

**Returns:** Current trace ID or None if not in request context

## Exception Classes

### FapilogError

Base exception class for all fapilog errors.

### ConfigurationError

Raised when configuration is invalid.

### SinkError

Raised when sink operations fail.

### QueueError

Raised when queue operations fail.

### MiddlewareError

Raised when middleware operations fail.

**Example:**

```python
from fapilog.exceptions import ConfigurationError
from fapilog.settings import LoggingSettings

try:
    settings = LoggingSettings(level="INVALID")
except ConfigurationError as e:
    print(f"Configuration error: {e}")
```

## Sinks

### Built-in Sinks

#### Stdout Sink

```
stdout
```

#### File Sink

```
file:///path/to/logfile.log
file:///path/to/logfile.log?rotation=1MB&retention=7
```

#### Loki Sink

```
loki://localhost:3100/loki/api/v1/push
loki://localhost:3100/loki/api/v1/push?labels=app:myapp,env:prod
```

### Custom Sinks

Implement the sink interface:

```python
class CustomSink:
    async def write(self, event_dict: Dict[str, Any]) -> None:
        # Process the log event
        pass
```

## Advanced Usage

### Multiple Containers

```python
from fapilog.container import LoggingContainer
from fapilog.settings import LoggingSettings

# Service A container
service_a_settings = LoggingSettings(
    level="DEBUG",
    sinks=["stdout", "file:///var/log/service-a.log"]
)
service_a_container = LoggingContainer(service_a_settings)
service_a_logger = service_a_container.configure()

# Service B container
service_b_settings = LoggingSettings(
    level="INFO",
    sinks=["stdout", "loki://localhost:3100"]
)
service_b_container = LoggingContainer(service_b_settings)
service_b_logger = service_b_container.configure()

# Independent logging
service_a_logger.debug("Service A debug message")
service_b_logger.info("Service B info message")
```

### Testing with Containers

```python
import pytest
from fapilog.container import LoggingContainer

@pytest.fixture
def isolated_logging():
    container = LoggingContainer()
    logger = container.configure()
    yield container, logger
    container.reset()

def test_my_feature(isolated_logging):
    container, logger = isolated_logging
    # Test with isolated logging instance
    logger.info("Test message")
    assert container.is_configured
```

## Migration from Global State

For more detailed migration examples, see [Container Architecture Documentation](container-architecture.md).

### Before (Deprecated)

```python
from fapilog.bootstrap import _configure_standard_logging
_configure_standard_logging("INFO")  # Deprecated
```

### After (Recommended)

```python
from fapilog.container import LoggingContainer
from fapilog.settings import LoggingSettings

settings = LoggingSettings(level="INFO")
container = LoggingContainer(settings)
container.configure()
```
