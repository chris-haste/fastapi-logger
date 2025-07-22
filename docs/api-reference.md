# API Reference

**Complete technical documentation for Fapilog's public APIs.**

This reference provides comprehensive documentation for all public functions, classes, and configuration options in Fapilog. Each section includes practical examples, default values, and allowable options.

**Current Version:** {{ version }} | [Changelog](https://github.com/chris-haste/fastapi-logger/blob/main/CHANGELOG.md)

**See also:** [User Guide](user-guide.md), [Quickstart](quickstart.md), [Configuration Guide](config.md)

---

## Table of Contents

- [Core Functions](#core-functions)
- [Configuration](#configuration)
- [Logging Interface](#logging-interface)
- [Middleware](#middleware)
- [Context Management](#context-management)
- [Enrichers](#enrichers)
- [Sinks](#sinks)
- [Monitoring](#monitoring)
- [Error Handling](#error-handling)
- [Types and Models](#types-and-models)

---

## Core Functions

### `configure_logging()`

**Primary function for setting up structured logging in your application.**

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

| Parameter  | Type              | Default | Description                                                                         |
| ---------- | ----------------- | ------- | ----------------------------------------------------------------------------------- |
| `settings` | `LoggingSettings` | `None`  | Complete configuration object. If `None`, created from environment variables.       |
| `app`      | `Any`             | `None`  | FastAPI app instance. If provided, `TraceIDMiddleware` is automatically registered. |

**Returns:**

- `structlog.BoundLogger`: Configured logger instance

**Raises:**

- `ConfigurationError`: If settings are invalid
- `RuntimeError`: If called from an async context without proper setup

**Environment Variables:**

All configuration can be set via environment variables with the `FAPILOG_` prefix:

```bash
export FAPILOG_LEVEL=INFO
export FAPILOG_SINKS=stdout,file
export FAPILOG_QUEUE_ENABLED=true
```

**Examples:**

**Basic Setup:**

```python
from fapilog import configure_logging, log

configure_logging()
log.info("Application started", version="1.0.0")
```

**FastAPI Integration:**

```python
from fastapi import FastAPI
from fapilog import configure_logging, log

app = FastAPI()
configure_logging(app=app)

@app.get("/users/{user_id}")
async def get_user(user_id: str):
    log.info("User requested", user_id=user_id)
    return {"user_id": user_id}
```

**Custom Configuration:**

```python
from fapilog.settings import LoggingSettings
from fapilog import configure_logging

settings = LoggingSettings(
    level="DEBUG",
    sinks=["stdout", "file"],
    file_path="/var/log/app.log",
    queue_enabled=True,
    queue_size=1000
)
configure_logging(settings=settings)
```

### `get_current_trace_id()`

**Access the current trace ID from within a request context.**

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

**Reset logging configuration for testing purposes.**

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

**Pydantic-based configuration model that maps environment variables to logging behavior.**

```python
from fapilog.settings import LoggingSettings

# Create from environment variables (default)
settings = LoggingSettings()

# Create with custom values
settings = LoggingSettings(
    level="DEBUG",
    sinks=["stdout", "loki"],
    format="json",
    queue_enabled=True,
    queue_size=2000,
    sampling_rate=0.5
)
```

**Core Settings:**

| Field    | Type        | Default      | Environment Variable | Description               |
| -------- | ----------- | ------------ | -------------------- | ------------------------- |
| `level`  | `str`       | `"INFO"`     | `FAPILOG_LEVEL`      | Logging level             |
| `format` | `str`       | `"auto"`     | `FAPILOG_FORMAT`     | Output format             |
| `sinks`  | `List[str]` | `["stdout"]` | `FAPILOG_SINKS`      | List of sink destinations |

**Queue Settings:**

| Field               | Type    | Default  | Environment Variable        | Description             |
| ------------------- | ------- | -------- | --------------------------- | ----------------------- |
| `queue_enabled`     | `bool`  | `True`   | `FAPILOG_QUEUE_ENABLED`     | Enable async queue      |
| `queue_size`        | `int`   | `1000`   | `FAPILOG_QUEUE_SIZE`        | Maximum queue size      |
| `batch_size`        | `int`   | `100`    | `FAPILOG_BATCH_SIZE`        | Events per batch        |
| `batch_timeout`     | `float` | `0.5`    | `FAPILOG_BATCH_TIMEOUT`     | Batch timeout (seconds) |
| `overflow_strategy` | `str`   | `"drop"` | `FAPILOG_OVERFLOW_STRATEGY` | Queue overflow behavior |

**Security Settings:**

| Field                | Type        | Default      | Environment Variable         | Description                 |
| -------------------- | ----------- | ------------ | ---------------------------- | --------------------------- |
| `redact_patterns`    | `List[str]` | `[]`         | `FAPILOG_REDACT_PATTERNS`    | Regex patterns to redact    |
| `redact_fields`      | `List[str]` | `[]`         | `FAPILOG_REDACT_FIELDS`      | Field names to redact       |
| `redact_replacement` | `str`       | `"REDACTED"` | `FAPILOG_REDACT_REPLACEMENT` | Replacement value           |
| `redact_level`       | `str`       | `"INFO"`     | `FAPILOG_REDACT_LEVEL`       | Minimum level for redaction |

**Performance Settings:**

| Field                     | Type        | Default | Environment Variable              | Description                 |
| ------------------------- | ----------- | ------- | --------------------------------- | --------------------------- |
| `sampling_rate`           | `float`     | `1.0`   | `FAPILOG_SAMPLING_RATE`           | Log sampling rate (0.0-1.0) |
| `sampling_levels`         | `List[str]` | `[]`    | `FAPILOG_SAMPLING_LEVELS`         | Levels to sample            |
| `enable_resource_metrics` | `bool`      | `False` | `FAPILOG_ENABLE_RESOURCE_METRICS` | Enable resource metrics     |

**Trace Settings:**

| Field                            | Type   | Default          | Environment Variable                     | Description              |
| -------------------------------- | ------ | ---------------- | ---------------------------------------- | ------------------------ |
| `trace_id_header`                | `str`  | `"X-Request-ID"` | `FAPILOG_TRACE_ID_HEADER`                | HTTP header for trace ID |
| `enable_httpx_trace_propagation` | `bool` | `False`          | `FAPILOG_ENABLE_HTTPX_TRACE_PROPAGATION` | Enable httpx propagation |

**Allowable Values:**

**Log Levels:**

- `"DEBUG"` - Detailed debug information
- `"INFO"` - General information messages
- `"WARNING"` - Warning messages
- `"ERROR"` - Error messages
- `"CRITICAL"` - Critical error messages

**Formats:**

- `"auto"` - Automatically choose based on environment
- `"json"` - Structured JSON output
- `"pretty"` - Human-readable console output

**Overflow Strategies:**

- `"drop"` - Drop new logs when queue is full
- `"block"` - Wait for space (may block application)
- `"sample"` - Keep percentage of logs under load

**Examples:**

**Development Configuration:**

```python
settings = LoggingSettings(
    level="DEBUG",
    format="pretty",
    sinks=["stdout"],
    queue_enabled=False,
    enable_resource_metrics=False
)
```

**Production Configuration:**

```python
settings = LoggingSettings(
    level="INFO",
    format="json",
    sinks=["stdout", "file", "loki"],
    file_path="/var/log/app.log",
    queue_enabled=True,
    queue_size=5000,
    redact_patterns=["email", "phone", "credit_card"],
    sampling_rate=0.1
)
```

**High-Performance Configuration:**

```python
settings = LoggingSettings(
    level="INFO",
    format="json",
    queue_enabled=True,
    queue_size=10000,
    batch_size=100,
    batch_timeout=0.1,
    overflow_strategy="drop",
    sampling_rate=0.5
)
```

---

## Logging Interface

### `log`

**The main logger instance that provides structured logging capabilities.**

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

| Method                            | Level    | Use Case                   |
| --------------------------------- | -------- | -------------------------- |
| `log.debug(message, **kwargs)`    | DEBUG    | Detailed debug information |
| `log.info(message, **kwargs)`     | INFO     | General information        |
| `log.warning(message, **kwargs)`  | WARNING  | Warning messages           |
| `log.error(message, **kwargs)`    | ERROR    | Error messages             |
| `log.critical(message, **kwargs)` | CRITICAL | Critical errors            |

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

**Common Patterns:**

**Error Handling:**

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

**Performance Monitoring:**

```python
import time

def monitored_function():
    start_time = time.time()

    try:
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

**User Activity Tracking:**

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

## Middleware

### `TraceIDMiddleware`

**FastAPI middleware that provides request correlation and timing.**

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

**Constructor Parameters:**

| Parameter         | Type  | Default          | Description                            |
| ----------------- | ----- | ---------------- | -------------------------------------- |
| `trace_id_header` | `str` | `"X-Request-ID"` | HTTP header name for incoming trace ID |

**Response Headers:**

| Header               | Description                            |
| -------------------- | -------------------------------------- |
| `X-Trace-Id`         | Request trace identifier (echoed back) |
| `X-Span-Id`          | Request span identifier                |
| `X-Response-Time-ms` | Request latency in milliseconds        |

**Captured Metadata (automatically added to log context):**

| Field         | Type    | Description                      |
| ------------- | ------- | -------------------------------- |
| `trace_id`    | `str`   | Request correlation identifier   |
| `span_id`     | `str`   | Request span identifier          |
| `method`      | `str`   | HTTP method (GET, POST, etc.)    |
| `path`        | `str`   | Request path                     |
| `client_ip`   | `str`   | Client IP address                |
| `status_code` | `int`   | HTTP response status code        |
| `latency_ms`  | `float` | Request duration in milliseconds |
| `req_bytes`   | `int`   | Request body size in bytes       |
| `res_bytes`   | `int`   | Response body size in bytes      |
| `user_agent`  | `str`   | User-Agent header value          |

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

**Example Usage:**

```python
from fastapi import FastAPI, HTTPException
from fapilog import configure_logging, log

app = FastAPI()
configure_logging(app=app)

@app.get("/users/{user_id}")
async def get_user(user_id: str):
    log.info("User requested", user_id=user_id)

    try:
        user = await get_user_from_db(user_id)
        log.info("User found", user_id=user_id, user_name=user.name)
        return user
    except UserNotFound:
        log.warning("User not found", user_id=user_id)
        raise HTTPException(status_code=404, detail="User not found")
```

**Expected Log Output:**

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "info",
  "event": "User requested",
  "trace_id": "abc123def456",
  "span_id": "789ghi012jkl",
  "method": "GET",
  "path": "/users/123",
  "client_ip": "192.168.1.100",
  "user_id": "123"
}
```

---

## Context Management

**Context management allows you to add request-scoped metadata to all log events.**

### `bind_context()`

**Bind context variables that will be included in all subsequent log events.**

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

**Get the current context variables.**

```python
from fapilog._internal.context import get_context

context = get_context()
print(context)  # {'user_id': '123', 'session_id': 'abc456', ...}
```

### `clear_context()`

**Clear all context variables.**

```python
from fapilog._internal.context import clear_context

# Clear context (useful for testing or request cleanup)
clear_context()
```

**Context Variables:**

Common context variables set by middleware:

| Variable      | Type    | Description              |
| ------------- | ------- | ------------------------ |
| `trace_id`    | `str`   | Request trace identifier |
| `span_id`     | `str`   | Request span identifier  |
| `req_bytes`   | `int`   | Request body size        |
| `res_bytes`   | `int`   | Response body size       |
| `status_code` | `int`   | HTTP status code         |
| `latency_ms`  | `float` | Request latency          |
| `user_agent`  | `str`   | User-Agent header        |

**Best Practices:**

- Use context for request-scoped data
- Clear context between requests in long-running processes
- Avoid storing large objects in context
- Use descriptive variable names

**Example with FastAPI:**

```python
from fastapi import FastAPI, Depends
from fapilog import configure_logging, log
from fapilog._internal.context import bind_context

app = FastAPI()
configure_logging(app=app)

async def get_current_user():
    # Your authentication logic
    return {"id": "user123", "roles": ["admin"]}

@app.get("/protected")
async def protected_route(user=Depends(get_current_user)):
    # Bind user context
    bind_context(user_id=user["id"], user_roles=user["roles"])

    # All logs in this request include user context
    log.info("Protected route accessed")
    log.warning("Permission check", resource="/admin")

    return {"message": "Access granted"}
```

---

## Enrichers

**Enrichers add metadata to log events automatically. Built-in enrichers provide system and request information.**

### Built-in Enrichers

#### `host_process_enricher()`

**Adds hostname and process ID to all log events.**

```python
# Automatically applied - no manual configuration needed
```

**Added Fields:**

| Field      | Type  | Description     |
| ---------- | ----- | --------------- |
| `hostname` | `str` | System hostname |
| `pid`      | `int` | Process ID      |

#### `resource_snapshot_enricher()`

**Adds memory and CPU usage metrics to log events.**

```python
# Enable via settings
settings = LoggingSettings(enable_resource_metrics=True)
configure_logging(settings=settings)
```

**Added Fields:**

| Field         | Type    | Description                  |
| ------------- | ------- | ---------------------------- |
| `memory_mb`   | `float` | Resident memory usage in MB  |
| `cpu_percent` | `float` | Process CPU usage percentage |

#### `body_size_enricher()`

**Adds request and response body sizes to log events.**

```python
# Automatically applied when TraceIDMiddleware is used
```

**Added Fields:**

| Field       | Type  | Description                 |
| ----------- | ----- | --------------------------- |
| `req_bytes` | `int` | Request body size in bytes  |
| `res_bytes` | `int` | Response body size in bytes |

### Custom Enrichers

**Register custom enrichers to add application-specific metadata.**

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

**Example Custom Enricher:**

```python
import os
from fapilog.enrichers import register_enricher

@register_enricher
def environment_enricher(logger, method_name, event_dict):
    """Add environment information to all logs."""
    event_dict["environment"] = os.getenv("ENVIRONMENT", "development")
    event_dict["version"] = os.getenv("APP_VERSION", "1.0.0")
    event_dict["deployment_id"] = os.getenv("DEPLOYMENT_ID")
    return event_dict

@register_enricher
def performance_enricher(logger, method_name, event_dict):
    """Add performance metrics to logs."""
    import psutil
    event_dict["memory_usage_mb"] = psutil.Process().memory_info().rss / 1024 / 1024
    event_dict["cpu_percent"] = psutil.Process().cpu_percent()
    return event_dict
```

---

## Sinks

**Sinks handle writing log events to different destinations. Built-in sinks provide common output targets.**

### Built-in Sinks

#### Stdout Sink

**Writes log events to stdout with JSON or pretty formatting.**

```python
# JSON output (production)
sink = StdoutSink(pretty=False)

# Pretty output (development)
sink = StdoutSink(pretty=True)
```

**Features:**

- JSON or pretty console output
- Automatic flushing
- Thread-safe writing
- Configurable via `LoggingSettings.format`

#### File Sink

**Writes log events to files with rotation support.**

```python
# Basic file sink
sink = FileSink("/var/log/app.log")

# With rotation
sink = FileSink("/var/log/app.log", max_size="10MB", backup_count=5)
```

**Parameters:**

| Parameter      | Type  | Default  | Description                      |
| -------------- | ----- | -------- | -------------------------------- |
| `filename`     | `str` | Required | Path to log file                 |
| `max_size`     | `str` | `None`   | Maximum file size (e.g., "10MB") |
| `backup_count` | `int` | `0`      | Number of backup files to keep   |

#### Loki Sink

**Sends log events to Grafana Loki for aggregation.**

```python
# Basic Loki sink
sink = LokiSink("http://localhost:3100")

# With custom labels
sink = LokiSink("http://localhost:3100", labels={"app": "myapp", "env": "prod"})
```

**Parameters:**

| Parameter       | Type    | Default  | Description              |
| --------------- | ------- | -------- | ------------------------ |
| `url`           | `str`   | Required | Loki API endpoint        |
| `labels`        | `dict`  | `{}`     | Static labels to add     |
| `batch_size`    | `int`   | `100`    | Events per batch         |
| `batch_timeout` | `float` | `1.0`    | Batch timeout in seconds |

### Custom Sinks

**Create custom sinks for specialized output destinations and requirements.**

#### Sink Interface

**Complete interface documentation for the Sink base class:**

```python
from fapilog._internal.queue import Sink
from typing import Dict, Any, Optional
import asyncio

class CustomSink(Sink):
    """Base class for all custom sinks."""

    def __init__(self):
        """Initialize the sink. Called once during setup."""
        super().__init__()
        self._sink_name = self.__class__.__name__

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """
        Write a log event to the sink.

        This is the ONLY required method that must be implemented.

        Args:
            event_dict: The structured log event dictionary containing:
                - level: Log level (str)
                - event: Log message (str)
                - timestamp: Event timestamp (float)
                - trace_id: Request trace ID (str, optional)
                - user_id: User identifier (str, optional)
                - Additional custom fields from enrichers

        Raises:
            Exception: Any exception will be caught and logged by the framework
        """
        raise NotImplementedError

    async def start(self) -> None:
        """
        Initialize the sink. Called once before processing begins.

        Use this for:
        - Creating HTTP sessions
        - Opening database connections
        - Starting background tasks
        - Validating configuration
        """
        pass

    async def stop(self) -> None:
        """
        Clean up the sink. Called once during shutdown.

        Use this for:
        - Closing HTTP sessions
        - Closing database connections
        - Cancelling background tasks
        - Flushing remaining data
        """
        pass

    async def flush(self) -> None:
        """
        Flush any buffered data immediately.

        Called during graceful shutdown or when immediate
        data persistence is required.
        """
        pass
```

#### Required vs Optional Methods

| Method       | Required        | Purpose                       | When to Implement            |
| ------------ | --------------- | ----------------------------- | ---------------------------- |
| `write()`    | ✅ **Required** | Process individual log events | Always implement             |
| `__init__()` | ✅ **Required** | Initialize sink state         | Always implement             |
| `start()`    | Optional        | Setup connections/resources   | When using external services |
| `stop()`     | Optional        | Cleanup resources             | When using external services |
| `flush()`    | Optional        | Force data persistence        | When buffering data          |

#### Error Handling Best Practices

**1. Never Let Sink Errors Break Logging:**

```python
class RobustSink(Sink):
    async def write(self, event_dict: Dict[str, Any]) -> None:
        try:
            # Your sink logic here
            await self._send_to_external_service(event_dict)
        except Exception as e:
            # Log the error but don't re-raise
            # This prevents sink failures from breaking the application
            import logging
            logging.getLogger(__name__).error(
                f"Sink {self._sink_name} failed: {e}",
                extra={"sink_error": True, "original_event": event_dict}
            )
```

**2. Implement Retry Logic for Transient Failures:**

```python
import asyncio
from typing import Optional

class RetryableSink(Sink):
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        super().__init__()
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    async def write(self, event_dict: Dict[str, Any]) -> None:
        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries):
            try:
                await self._send_to_service(event_dict)
                return  # Success
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff

        # All retries failed
        raise last_error
```

**3. Handle Different Error Types Appropriately:**

```python
class SmartSink(Sink):
    async def write(self, event_dict: Dict[str, Any]) -> None:
        try:
            await self._send_to_service(event_dict)
        except ConnectionError as e:
            # Network issues - retry later
            await self._queue_for_retry(event_dict)
        except ValueError as e:
            # Invalid data - log and skip
            import logging
            logging.getLogger(__name__).warning(
                f"Invalid event data: {e}",
                extra={"event": event_dict}
            )
        except Exception as e:
            # Unexpected error - log and continue
            import logging
            logging.getLogger(__name__).error(
                f"Unexpected sink error: {e}",
                extra={"event": event_dict}
            )
```

#### Performance Considerations

**1. Batching for High-Throughput Sinks:**

```python
import asyncio
from typing import List
import time

class BatchedSink(Sink):
    def __init__(self, batch_size: int = 100, batch_timeout: float = 5.0):
        super().__init__()
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.buffer: List[Dict[str, Any]] = []
        self.last_send_time = time.time()
        self._send_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start background batch sender."""
        self._send_task = asyncio.create_task(self._batch_sender())

    async def stop(self):
        """Flush remaining data and stop."""
        if self._send_task:
            self._send_task.cancel()
            try:
                await self._send_task
            except asyncio.CancelledError:
                pass

        # Send any remaining buffered data
        if self.buffer:
            await self._send_batch(self.buffer)
            self.buffer.clear()

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Add event to buffer."""
        self.buffer.append(event_dict)

        # Send immediately if buffer is full
        if len(self.buffer) >= self.batch_size:
            await self._send_buffered_data()

    async def _batch_sender(self):
        """Background task that sends batches periodically."""
        while True:
            try:
                await asyncio.sleep(self.batch_timeout)
                await self._send_buffered_data()
            except asyncio.CancelledError:
                break

    async def _send_buffered_data(self):
        """Send all buffered data."""
        if self.buffer:
            await self._send_batch(self.buffer)
            self.buffer.clear()
            self.last_send_time = time.time()

    async def _send_batch(self, batch: List[Dict[str, Any]]) -> None:
        """Send a batch of events to the external service."""
        # Your batch sending logic here
        pass
```

**2. Async Patterns for Non-Blocking Operations:**

```python
import aiohttp
import asyncio
from typing import Optional

class AsyncHTTPSink(Sink):
    def __init__(self, url: str, timeout: float = 10.0):
        super().__init__()
        self.url = url
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None

    async def start(self):
        """Create HTTP session."""
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self.session = aiohttp.ClientSession(timeout=timeout)

    async def stop(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Send event via HTTP POST."""
        if not self.session:
            raise RuntimeError("Sink not started")

        try:
            async with self.session.post(self.url, json=event_dict) as response:
                response.raise_for_status()
        except Exception as e:
            raise Exception(f"HTTP sink failed: {e}")
```

**3. Memory Management for Large Events:**

```python
class MemoryEfficientSink(Sink):
    def __init__(self, max_event_size: int = 1024 * 1024):  # 1MB
        super().__init__()
        self.max_event_size = max_event_size

    async def write(self, event_dict: Dict[str, Any]) -> None:
        # Check event size before processing
        event_size = len(str(event_dict).encode('utf-8'))
        if event_size > self.max_event_size:
            # Truncate large events to prevent memory issues
            truncated_event = self._truncate_event(event_dict)
            await self._send_event(truncated_event)
        else:
            await self._send_event(event_dict)

    def _truncate_event(self, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Truncate large events to prevent memory issues."""
        truncated = event_dict.copy()
        if 'event' in truncated and len(truncated['event']) > 1000:
            truncated['event'] = truncated['event'][:1000] + "... [truncated]"
        return truncated
```

#### Integration Patterns with FastAPI Lifecycle Events

**1. Sink Lifecycle Management:**

```python
from fastapi import FastAPI
from contextlib import asynccontextmanager

class ManagedSink(Sink):
    def __init__(self):
        super().__init__()
        self._started = False

    async def start(self):
        """Initialize sink resources."""
        if self._started:
            return
        # Your initialization logic
        self._started = True

    async def stop(self):
        """Clean up sink resources."""
        if not self._started:
            return
        # Your cleanup logic
        self._started = False

# FastAPI integration
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    custom_sink = ManagedSink()
    await custom_sink.start()

    # Make sink available to the application
    app.state.custom_sink = custom_sink

    yield

    # Shutdown
    await custom_sink.stop()

app = FastAPI(lifespan=lifespan)
```

**2. Sink Registration with FastAPI:**

```python
from fapilog import configure_logging
from fapilog.settings import LoggingSettings

class FastAPISink(Sink):
    def __init__(self, app: FastAPI):
        super().__init__()
        self.app = app

    async def write(self, event_dict: Dict[str, Any]) -> None:
        # Add FastAPI context to logs
        event_dict['app_name'] = self.app.title
        event_dict['app_version'] = getattr(self.app, 'version', 'unknown')

        # Your sink logic here
        await self._send_to_service(event_dict)

# Register custom sink with FastAPI
app = FastAPI()
custom_sink = FastAPISink(app)

settings = LoggingSettings(sinks=["stdout", custom_sink])
configure_logging(settings=settings)
```

**3. Health Checks and Monitoring:**

```python
class MonitoredSink(Sink):
    def __init__(self):
        super().__init__()
        self.write_count = 0
        self.error_count = 0
        self.last_write_time = None

    async def write(self, event_dict: Dict[str, Any]) -> None:
        try:
            await self._send_to_service(event_dict)
            self.write_count += 1
            self.last_write_time = time.time()
        except Exception as e:
            self.error_count += 1
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Return sink health status for monitoring."""
        return {
            "sink_name": self._sink_name,
            "status": "healthy" if self.error_count == 0 else "degraded",
            "write_count": self.write_count,
            "error_count": self.error_count,
            "last_write_time": self.last_write_time,
            "uptime": time.time() - (self.last_write_time or time.time())
        }
```

#### Complete Custom Sink Example

```python
import asyncio
import aiohttp
import json
import time
from typing import Dict, Any, List, Optional

class SlackAlertSink(Sink):
    """
    Custom sink that sends error logs to Slack.

    Demonstrates:
    - Required vs optional methods
    - Error handling best practices
    - Performance considerations (batching)
    - FastAPI lifecycle integration
    """

    def __init__(
        self,
        webhook_url: str,
        channel: str = "#alerts",
        batch_size: int = 5,
        batch_timeout: float = 30.0,
        max_retries: int = 3
    ):
        super().__init__()
        self.webhook_url = webhook_url
        self.channel = channel
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.max_retries = max_retries

        # State management
        self.session: Optional[aiohttp.ClientSession] = None
        self.buffer: List[Dict[str, Any]] = []
        self._send_task: Optional[asyncio.Task] = None
        self._started = False

    async def start(self):
        """Initialize HTTP session and start background sender."""
        if self._started:
            return

        self.session = aiohttp.ClientSession()
        self._send_task = asyncio.create_task(self._batch_sender())
        self._started = True

    async def stop(self):
        """Clean up resources and send remaining data."""
        if not self._started:
            return

        # Cancel background task
        if self._send_task:
            self._send_task.cancel()
            try:
                await self._send_task
            except asyncio.CancelledError:
                pass

        # Send any remaining buffered alerts
        if self.buffer:
            await self._send_alerts(self.buffer)
            self.buffer.clear()

        # Close HTTP session
        if self.session:
            await self.session.close()

        self._started = False

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Process log event - only send errors to Slack."""
        # Only process error-level logs
        if event_dict.get("level") != "error":
            return

        # Add to buffer for batching
        self.buffer.append(event_dict)

        # Send immediately if buffer is full
        if len(self.buffer) >= self.batch_size:
            await self._send_buffered_alerts()

    async def _batch_sender(self):
        """Background task that sends alerts periodically."""
        while True:
            try:
                await asyncio.sleep(self.batch_timeout)
                await self._send_buffered_alerts()
            except asyncio.CancelledError:
                break

    async def _send_buffered_alerts(self):
        """Send all buffered alerts."""
        if self.buffer:
            await self._send_alerts(self.buffer)
            self.buffer.clear()

    async def _send_alerts(self, alerts: List[Dict[str, Any]]) -> None:
        """Send alerts to Slack with retry logic."""
        if not alerts:
            return

        # Prepare Slack message
        message = self._prepare_slack_message(alerts)

        # Send with retry logic
        for attempt in range(self.max_retries):
            try:
                if not self.session:
                    raise RuntimeError("Session not initialized")

                async with self.session.post(
                    self.webhook_url,
                    json=message,
                    timeout=aiohttp.ClientTimeout(total=10.0)
                ) as response:
                    response.raise_for_status()
                    return  # Success

            except Exception as e:
                if attempt == self.max_retries - 1:
                    # Final attempt failed - log but don't raise
                    import logging
                    logging.getLogger(__name__).error(
                        f"Slack sink failed after {self.max_retries} attempts: {e}",
                        extra={"alerts": alerts}
                    )
                else:
                    # Wait before retry
                    await asyncio.sleep(1.0 * (2 ** attempt))  # Exponential backoff

    def _prepare_slack_message(self, alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare Slack message from alerts."""
        # Group alerts by error type
        error_groups = {}
        for alert in alerts:
            error_type = alert.get("event", "Unknown Error")
            if error_type not in error_groups:
                error_groups[error_type] = []
            error_groups[error_type].append(alert)

        # Create Slack message
        fields = []
        for error_type, group_alerts in error_groups.items():
            fields.append({
                "title": f"Error: {error_type}",
                "value": f"Count: {len(group_alerts)}",
                "short": True
            })

        # Add trace information
        trace_ids = list(set(
            alert.get("trace_id", "N/A")
            for alert in alerts
            if alert.get("trace_id")
        ))
        if trace_ids:
            fields.append({
                "title": "Trace IDs",
                "value": ", ".join(trace_ids[:5]),  # Limit to first 5
                "short": True
            })

        return {
            "channel": self.channel,
            "text": f"🚨 {len(alerts)} error(s) detected",
            "attachments": [{
                "color": "danger",
                "fields": fields,
                "footer": f"fapilog Slack Sink | {time.strftime('%Y-%m-%d %H:%M:%S')}"
            }]
        }

# Usage with FastAPI
from fastapi import FastAPI
from fapilog import configure_logging

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create and start custom sink
    slack_sink = SlackAlertSink(
        webhook_url="https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
        channel="#alerts"
    )
    await slack_sink.start()

    # Configure logging with custom sink
    configure_logging(sinks=["stdout", slack_sink])

    yield

    # Stop custom sink
    await slack_sink.stop()

app = FastAPI(lifespan=lifespan)
```

---

## Monitoring

**The monitoring system provides comprehensive performance tracking for queue operations, sink performance, and overall logging health.**

### `start_metrics_server()`

**Start a Prometheus metrics HTTP server for scraping.**

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

| Parameter | Type  | Default      | Description                    |
| --------- | ----- | ------------ | ------------------------------ |
| `host`    | `str` | `"0.0.0.0"`  | Host to bind to                |
| `port`    | `int` | `8000`       | Port to bind to                |
| `path`    | `str` | `"/metrics"` | HTTP path for metrics endpoint |

**Returns:**

- `PrometheusExporter`: The metrics exporter instance, or `None` if failed

### `get_metrics_text()`

**Get current metrics in Prometheus text format.**

```python
from fapilog.monitoring import get_metrics_text

# Get Prometheus-formatted metrics
metrics_text = get_metrics_text()
print(metrics_text)
```

**Returns:**

- `str`: Metrics in Prometheus format

### `get_metrics_dict()`

**Get current metrics as a structured dictionary.**

```python
from fapilog.monitoring import get_metrics_dict

# Get metrics as dictionary
metrics = get_metrics_dict()
print(f"Queue size: {metrics['queue']['size']}")
print(f"Total events: {metrics['performance']['total_log_events']}")
```

**Returns:**

- `dict`: Structured metrics data with queue, sinks, and performance sections

### Available Metrics

**Queue Metrics:**

| Metric                             | Type    | Description             |
| ---------------------------------- | ------- | ----------------------- |
| `fapilog_queue_size`               | Gauge   | Current queue size      |
| `fapilog_queue_peak_size`          | Gauge   | Peak queue size         |
| `fapilog_queue_enqueued_total`     | Counter | Total events enqueued   |
| `fapilog_queue_dequeued_total`     | Counter | Total events dequeued   |
| `fapilog_queue_dropped_total`      | Counter | Total events dropped    |
| `fapilog_queue_enqueue_latency_ms` | Gauge   | Average enqueue latency |
| `fapilog_queue_memory_bytes`       | Gauge   | Queue memory usage      |

**Sink Metrics:**

Per-sink metrics with `sink` label:

| Metric                                     | Type    | Description             |
| ------------------------------------------ | ------- | ----------------------- |
| `fapilog_sink_writes_total{sink="..."}`    | Counter | Total writes per sink   |
| `fapilog_sink_successes_total{sink="..."}` | Counter | Total successful writes |
| `fapilog_sink_failures_total{sink="..."}`  | Counter | Total failed writes     |
| `fapilog_sink_success_rate{sink="..."}`    | Gauge   | Success rate ratio      |
| `fapilog_sink_latency_ms{sink="..."}`      | Gauge   | Average write latency   |

**Performance Metrics:**

| Metric                      | Type    | Description                |
| --------------------------- | ------- | -------------------------- |
| `fapilog_events_total`      | Counter | Total log events processed |
| `fapilog_events_per_second` | Gauge   | Current throughput         |
| `fapilog_memory_bytes`      | Gauge   | Process memory usage       |
| `fapilog_cpu_percent`       | Gauge   | Process CPU usage          |

### Configuration

**Enable metrics through settings:**

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

**Or via environment variables:**

```bash
export FAPILOG_METRICS_ENABLED=true
export FAPILOG_METRICS_PROMETHEUS_ENABLED=true
export FAPILOG_METRICS_PROMETHEUS_PORT=8000
```

**Example Prometheus Configuration:**

```yaml
# prometheus.yml
scrape_configs:
  - job_name: "fapilog"
    static_configs:
      - targets: ["localhost:8000"]
    metrics_path: "/metrics"
```

---

## Error Handling

**Fapilog provides a comprehensive set of custom exceptions for different error scenarios.**

### Custom Exception Classes

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

**All exceptions include rich context information:**

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

**The library implements graceful degradation for non-critical errors:**

- **Sink failures** don't break the entire logging system
- **Queue errors** fall back to synchronous logging
- **Middleware errors** continue without context enrichment
- **Redaction errors** log the original data without redaction

### Retry Mechanisms

**Automatic retry with exponential backoff for transient failures:**

```python
# Loki sink automatically retries failed HTTP requests
# Queue worker retries failed sink operations
# Configuration errors are logged but don't break startup
```

### Legacy Exceptions

**For backward compatibility, some operations may still raise standard exceptions:**

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

## Types and Models

### `Sink`

**Base class for all log sinks.**

```python
from fapilog import Sink

class MySink(Sink):
    async def write(self, event_dict):
        # Implementation
        pass

    async def close(self):
        # Cleanup
        pass
```

### `QueueWorker`

**Manages the async log queue and sink processing.**

```python
from fapilog import QueueWorker

# Usually managed internally, but can be customized
worker = QueueWorker(
    sinks=[my_sink],
    queue_size=1000,
    batch_size=10,
    batch_timeout=1.0
)
```

### Environment Variables

**All configuration can be set via environment variables:**

| Variable                                 | Default        | Description                           |
| ---------------------------------------- | -------------- | ------------------------------------- |
| `FAPILOG_LEVEL`                          | `INFO`         | Logging level                         |
| `FAPILOG_SINKS`                          | `stdout`       | Comma-separated sink list             |
| `FAPILOG_FORMAT`                         | `auto`         | Console format                        |
| `FAPILOG_QUEUE_ENABLED`                  | `true`         | Enable async queue                    |
| `FAPILOG_QUEUE_SIZE`                     | `1000`         | Queue maximum size                    |
| `FAPILOG_OVERFLOW_STRATEGY`              | `drop`         | Queue overflow strategy               |
| `FAPILOG_BATCH_SIZE`                     | `100`          | Events per batch                      |
| `FAPILOG_BATCH_TIMEOUT`                  | `0.5`          | Batch timeout (seconds)               |
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

## Performance Considerations

### Queue Configuration

**For high-throughput applications:**

```python
settings = LoggingSettings(
    queue_size=10000,        # Larger queue
    batch_size=100,          # Larger batches
    batch_timeout=0.1,       # Shorter timeout
    overflow_strategy="drop" # Drop logs under load
)
```

### Sampling

**For very high-volume logging:**

```python
settings = LoggingSettings(
    sampling_rate=0.1,  # Log only 10% of events
    overflow_strategy="sample"  # Adaptive sampling under load
)
```

### Resource Metrics

**Enable only when needed:**

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
