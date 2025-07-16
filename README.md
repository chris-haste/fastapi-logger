# FastAPI-Logger (`fapilog`)

**Structured, context-aware, production-ready logging for FastAPI and other ASGI apps.**

`fapilog` delivers opinionated defaults—JSON logs, trace IDs, async-safe sinks—while remaining fully extensible, so every micro-service in your stack emits consistent, query-friendly events from day one.

---

## ✨ Key Goals

| Goal                          | Practical impact                                                                                                             |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| **Zero-friction setup**       | One-liner `configure_logging()`—no YAML gymnastics or copy-pasted boilerplate.                                               |
| **Structured by default**     | Logs are JSON objects (Docker & cloud-native friendly). A pretty console renderer toggles on automatically during local dev. |
| **Context propagation**       | Trace ID, span ID, request path, status, user ID, and other metadata flow through `contextvars` without polluting your code. |
| **Async & non-blocking**      | A background queue + worker ensures log writing never blocks the event loop, even under high RPS.                            |
| **Pluggable sinks**           | Ship logs to stdout, files, Loki, or any HTTP endpoint. Custom sinks take just a few lines.                                  |
| **Security & compliance**     | Built-in PII redaction, field-level allow/deny lists, GDPR-friendly opt-outs.                                                |
| **Observability integration** | Hooks for OpenTelemetry spans and Prometheus/OTLP metrics so logs, traces, and metrics share the same IDs.                   |
| **Testability**               | Pytest fixtures capture structured logs so you can assert on their content with ease.                                        |

---

## 🚀 Quick Start

```bash
pip install fapilog
```

```python
# main.py
from fastapi import FastAPI
from fapilog import configure_logging, log

configure_logging()              # instant logging superpowers

app = FastAPI()

@app.get("/ping")
async def ping():
    log.info("ping_hit")         # JSON log with trace_id, path, method, etc.
    return {"pong": True}
```

Run the service:

```bash
uvicorn app.main:app --reload
```

Local console shows colourised logs; in production the same call emits compact JSON suitable for Loki, Cloud Logging, or ELK.

---

## 🛠 Development Setup

```bash
git clone <repo>
cd fastapi-logger
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
hatch run test
```

> **Note:** The test suite enforces a minimum coverage threshold of 85% using `pytest-cov`. If coverage falls below this threshold, the test run will fail locally and in CI. To see a detailed coverage report, use `hatch run test-cov` or inspect the HTML report in `htmlcov/` after running tests.

### Development Commands

- `hatch run lint` - Run Ruff linter
- `hatch run typecheck` - Run MyPy type checker
- `hatch run test` - Run pytest test suite
- `hatch run test-cov` - Run tests with coverage report
- `hatch run test-queue-load` - Run load testing for logging queue

---

## 🛠 How It Works

```
Request ─► TraceIDMiddleware ─► structlog pipeline ─► Async Queue ─► Sink(s)
              ▲                                            │
              └──────────── contextvars (trace_id, user_id, …)
                                              stdout, file, Loki…
```

- **`middleware.py`** — injects trace/context and measures request duration
- **`enrichers.py`** — attaches hostname, memory usage, SQL timings, etc.
- **`_internal/queue.py`** — decouples log generation from I/O
- **`sinks/`** — pluggable writers (start with `stdout` and `loki`; add more)

## 🔄 Async Logging Queue

`fapilog` uses a non-blocking, in-process queue to ensure log calls never block the asyncio event loop, even under high concurrency. This is crucial for maintaining performance in production environments.

### How It Works

1. **Non-blocking enqueue**: Log events are immediately enqueued as structured dictionaries
2. **Background processing**: A dedicated `QueueWorker` coroutine processes events in batches
3. **Graceful degradation**: When the queue is full, events are dropped silently (configurable)
4. **Retry logic**: Failed sink writes are retried with exponential backoff
5. **Graceful shutdown**: The queue worker shuts down cleanly on application exit

### Performance Benefits

- **Zero blocking**: Log calls return immediately, never blocking your request handlers
- **Batch processing**: Events are processed in configurable batches for efficiency
- **Memory efficient**: Fixed-size queue prevents unbounded memory growth
- **Fault tolerant**: Sink failures don't affect application performance

### Configuration

```python
from fapilog import configure_logging
from fapilog.settings import LoggingSettings

settings = LoggingSettings(
    queue_enabled=True,           # Enable async queue (default: True)
    queue_size=1000,             # Maximum queue size (default: 1000)
    queue_batch_size=10,         # Events per batch (default: 10)
    queue_batch_timeout=1.0,     # Max wait for batch (default: 1.0s)
    queue_retry_delay=1.0,       # Retry delay (default: 1.0s)
    queue_max_retries=3,         # Max retries per event (default: 3)
)

logger = configure_logging(settings=settings)
```

### Environment Variables

| Variable                      | Default | Description             |
| ----------------------------- | ------- | ----------------------- |
| `FAPILOG_QUEUE_ENABLED`       | `true`  | Enable async queue      |
| `FAPILOG_QUEUE_SIZE`          | `1000`  | Maximum queue size      |
| `FAPILOG_QUEUE_BATCH_SIZE`    | `10`    | Events per batch        |
| `FAPILOG_QUEUE_BATCH_TIMEOUT` | `1.0`   | Batch timeout (seconds) |
| `FAPILOG_QUEUE_RETRY_DELAY`   | `1.0`   | Retry delay (seconds)   |
| `FAPILOG_QUEUE_MAX_RETRIES`   | `3`     | Maximum retries         |

### Controlling Queue Overflow Behavior

When the queue reaches capacity, you can control how `fapilog` handles the overflow using the `queue_overflow` setting. Three strategies are available:

#### Drop Strategy (Default)

Silently discards logs when the queue is full. This ensures your application never blocks on logging:

```python
settings = LoggingSettings(
    queue_overflow="drop",  # Default behavior
    queue_maxsize=1000,
)
```

#### Block Strategy

Waits for queue space to become available before continuing. Use this when you need guaranteed log delivery:

```python
settings = LoggingSettings(
    queue_overflow="block",  # Wait for space
    queue_maxsize=1000,
)
```

#### Sample Strategy

Uses probabilistic sampling when the queue is full. This provides adaptive logging under load:

```python
settings = LoggingSettings(
    queue_overflow="sample",  # Probabilistic sampling
    sampling_rate=0.1,        # Keep 10% of logs when queue is full
    queue_maxsize=1000,
)
```

### Environment Variables

| Variable                      | Default | Description             |
| ----------------------------- | ------- | ----------------------- |
| `FAPILOG_QUEUE_ENABLED`       | `true`  | Enable async queue      |
| `FAPILOG_QUEUE_SIZE`          | `1000`  | Maximum queue size      |
| `FAPILOG_QUEUE_OVERFLOW`      | `drop`  | Overflow strategy       |
| `FAPILOG_QUEUE_BATCH_SIZE`    | `10`    | Events per batch        |
| `FAPILOG_QUEUE_BATCH_TIMEOUT` | `1.0`   | Batch timeout (seconds) |
| `FAPILOG_QUEUE_RETRY_DELAY`   | `1.0`   | Retry delay (seconds)   |
| `FAPILOG_QUEUE_MAX_RETRIES`   | `3`     | Maximum retries         |

### Under High Load

When the queue reaches capacity, new log events are handled according to your overflow strategy. This ensures your application remains responsive even during logging bottlenecks:

```python
# These calls will never block, even if sinks are slow
for i in range(10000):
    logger.info(f"high_frequency_event_{i}")  # Non-blocking
```

The queue worker processes events in the background, so your application continues to handle requests at full speed.

---

## 🚀 Benchmarking Logging Queue

`fapilog` includes a comprehensive load testing script to verify the logging queue performs reliably under high throughput scenarios.

### Running Load Tests

**Basic test with default settings:**

```bash
python scripts/load_test_log_queue.py
```

**High concurrency test:**

```bash
python scripts/load_test_log_queue.py --concurrency 50 --rate 1000 --duration 30
```

**Test different overflow strategies:**

```bash
# Test drop strategy (default)
python scripts/load_test_log_queue.py --overflow drop --queue-size 100

# Test block strategy
python scripts/load_test_log_queue.py --overflow block --queue-size 100

# Test sample strategy
python scripts/load_test_log_queue.py --overflow sample --queue-size 100
```

**Using environment variables:**

```bash
export LOAD_TEST_CONCURRENCY=20
export LOAD_TEST_RATE=500
export LOAD_TEST_DURATION=60
export LOAD_TEST_QUEUE_SIZE=500
export LOAD_TEST_OVERFLOW=drop
python scripts/load_test_log_queue.py
```

**Using hatch:**

```bash
hatch run test-queue-load
```

### Test Parameters

| Parameter         | Default | Description                           |
| ----------------- | ------- | ------------------------------------- |
| `--concurrency`   | 10      | Number of concurrent workers          |
| `--rate`          | 100     | Logs per second per worker            |
| `--duration`      | 30      | Test duration in seconds              |
| `--queue-size`    | 1000    | Maximum queue size                    |
| `--overflow`      | drop    | Overflow strategy (drop/block/sample) |
| `--batch-size`    | 10      | Queue batch size                      |
| `--batch-timeout` | 1.0     | Queue batch timeout in seconds        |

### Performance Targets

The load test script helps verify that your logging configuration meets performance targets:

- **Excellent**: <100 µs average enqueue latency
- **Good**: <500 µs average enqueue latency
- **Poor**: >500 µs average enqueue latency

### Sample Output

```
Starting load test with 10 workers...
Target rate: 100 logs/sec per worker
Duration: 30 seconds
Queue size: 1000
Overflow strategy: drop
Batch size: 10
Batch timeout: 1.0s
------------------------------------------------------------

============================================================
LOAD TEST RESULTS
============================================================
Test Duration:           30.05 seconds
Total Logs Attempted:    30,000
Successfully Enqueued:   29,875
Dropped:                 125
Actual Logs/Second:      998.33
Average Enqueue Latency: 42.15 µs
Min Latency:             12.34 µs
Max Latency:             156.78 µs

Queue Configuration:
  Queue Size:            1000
  Overflow Strategy:      drop
  Batch Size:            10
  Batch Timeout:         1.0s

Performance Assessment:
  ✅ Excellent: <100 µs average latency
  ⚠️  0.42% of logs dropped
============================================================
```

### Interpreting Results

- **Latency**: Measures the time to enqueue a log event (not processing time)
- **Dropped logs**: Occur when the queue is full and overflow strategy is "drop"
- **Throughput**: Actual logs per second achieved vs. target rate
- **Concurrency**: How well the system handles multiple concurrent loggers

The load test helps ensure your logging infrastructure can handle production workloads without impacting application performance.

---

## 🔄 Shutdown Behavior and Log Flushing

`fapilog` ensures that all log events are flushed during application shutdown, preventing data loss when the service exits or is terminated cleanly.

### How Shutdown Works

1. **FastAPI Integration**: When used with FastAPI, the queue worker automatically registers a shutdown handler that flushes remaining logs
2. **CLI/Script Mode**: For standalone applications, `atexit` handlers ensure logs are flushed on exit
3. **Event Loop Safety**: The worker tracks its event loop and uses `run_coroutine_threadsafe` to safely shutdown from sync contexts
4. **Timeout Protection**: Shutdown operations have a 5-second timeout to prevent hanging during cleanup

### Shutdown Scenarios

**FastAPI Application:**

```python
from fastapi import FastAPI
from fapilog import configure_logging

app = FastAPI()
configure_logging(app=app)  # Automatically registers shutdown handler

@app.get("/")
async def root():
    log.info("Request processed")
    return {"message": "Hello World"}
```

**CLI/Script Application:**

```python
from fapilog import configure_logging

configure_logging()  # Registers atexit handler automatically

def main():
    log.info("Application started")
    # ... your application logic ...
    log.info("Application completed")

if __name__ == "__main__":
    main()
    # Logs are automatically flushed on exit
```

### Graceful Degradation

- If the worker's event loop is unavailable during shutdown, the system falls back to `asyncio.run()`
- Shutdown operations are wrapped in try/catch blocks to prevent exceptions from affecting application exit
- The queue worker can be safely shut down multiple times (idempotent shutdown)

### Configuration

All knobs are environment-driven (perfect for 12-factor apps):

| Env var                   | Default   | Description                                                                 |
| ------------------------- | --------- | --------------------------------------------------------------------------- |
| `FAPILOG_LEVEL`           | `INFO`    | Global log level (`DEBUG`, `INFO`, `WARN`, `ERROR`)                         |
| `FAPILOG_SINKS`           | `stdout`  | Comma-separated list: `stdout`, `file://./logs/app.log`, `loki://loki:3100` |
| `FAPILOG_JSON_CONSOLE`    | `auto`    | `auto` (JSON in prod, pretty in dev), `json`, or `pretty`                   |
| `FAPILOG_REDACT_PATTERNS` | _(empty)_ | Regex list for masking PII (`password`, `token`, …)                         |

Programmatic override:

```python
configure_logging(
    level="DEBUG",
    sinks=["stdout", "loki://loki:3100"],
    redact_patterns=[r"(?i)password"],
)
```

### Sink Configuration

`fapilog` supports multiple output destinations (sinks) for log events. The default sink is `stdout`, which writes logs to standard output in either JSON or pretty format.

#### Stdout Sink

The `stdout` sink is the default sink and supports three output modes:

- **`json`**: Force JSON output (compact, one-line-per-event)
- **`pretty`**: Force pretty console output (colorized, multiline)
- **`auto`**: Automatically choose based on TTY detection (default)

##### Configuration

**Environment variables:**

```bash
# Force JSON output
export FAPILOG_JSON_CONSOLE=json

# Force pretty output
export FAPILOG_JSON_CONSOLE=pretty

# Auto-detect (pretty in TTY, JSON otherwise)
export FAPILOG_JSON_CONSOLE=auto
```

**Programmatic configuration:**

```python
from fapilog.settings import LoggingSettings

# Force JSON output
settings = LoggingSettings(json_console="json")
configure_logging(settings=settings)

# Force pretty output
settings = LoggingSettings(json_console="pretty")
configure_logging(settings=settings)

# Auto-detect (default)
settings = LoggingSettings(json_console="auto")
configure_logging(settings=settings)
```

##### Output Formats

**JSON Mode:**

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "info",
  "event": "Request processed",
  "trace_id": "abc123def456",
  "status_code": 200,
  "latency_ms": 45.2
}
```

**Pretty Mode:**

```
2024-01-15 10:30:45.123 | INFO     | Request processed
                          trace_id=abc123def456 status_code=200 latency_ms=45.2
```

##### TTY Detection

When using `auto` mode (the default), the sink automatically detects whether it's running in an interactive terminal:

- **Interactive terminal**: Uses pretty output with ANSI color codes
- **Non-interactive (pipes, files, containers)**: Uses JSON output

This makes it perfect for development (pretty logs in your terminal) and production (JSON logs in Docker/Kubernetes).

##### Development Tips

For consistent pretty output during development, you can force pretty mode:

```bash
# In your development environment
export FAPILOG_JSON_CONSOLE=pretty
```

Or in your development configuration:

```python
# development.py
from fapilog.settings import LoggingSettings

settings = LoggingSettings(
    level="DEBUG",
    json_console="pretty",  # Force pretty output in development
)
```

#### File Sink

The `file` sink writes logs to a file with automatic rotation support. It's perfect for production environments where you need persistent logs with size management.

##### Configuration

**Environment variables:**

```bash
# Basic file logging
export FAPILOG_SINKS="file:///var/log/myapp.log"

# With custom rotation settings
export FAPILOG_SINKS="file:///var/log/myapp.log?maxBytes=10485760&backupCount=3"

# Multiple sinks (stdout + file)
export FAPILOG_SINKS="stdout,file:///var/log/myapp.log"
```

**Programmatic configuration:**

```python
from fapilog.settings import LoggingSettings

# Basic file logging
settings = LoggingSettings(sinks=["file:///var/log/myapp.log"])
configure_logging(settings=settings)

# With custom rotation settings
settings = LoggingSettings(
    sinks=["file:///var/log/myapp.log?maxBytes=10485760&backupCount=3"]
)
configure_logging(settings=settings)
```

##### URI Format

File sinks use a URI-style configuration format:

```
file:///path/to/logfile.log?maxBytes=10485760&backupCount=5
```

**Parameters:**

- **`maxBytes`** (optional): Maximum file size before rotation (default: 10 MB)
- **`backupCount`** (optional): Number of backup files to keep (default: 5)

**Examples:**

```bash
# Default settings (10MB, 5 backups)
export FAPILOG_SINKS="file:///var/log/myapp.log"

# Custom size (5MB, 3 backups)
export FAPILOG_SINKS="file:///var/log/myapp.log?maxBytes=5242880&backupCount=3"

# Large files (100MB, 10 backups)
export FAPILOG_SINKS="file:///var/log/myapp.log?maxBytes=104857600&backupCount=10"
```

##### Features

- **Automatic rotation**: Files are rotated when they exceed the `maxBytes` limit
- **Backup management**: Old log files are automatically cleaned up
- **Thread-safe**: Safe for concurrent logging from multiple threads
- **Immediate flush**: Logs are flushed immediately to prevent data loss
- **Directory creation**: Parent directories are created automatically if they don't exist

##### Output Format

File sinks always write logs in JSON format, one event per line:

```json
{"timestamp": "2024-01-15T10:30:45.123Z", "level": "info", "event": "Request processed", "trace_id": "abc123def456", "status_code": 200, "latency_ms": 45.2}
{"timestamp": "2024-01-15T10:30:46.456Z", "level": "error", "event": "Database connection failed", "trace_id": "def789ghi012", "error": "Connection timeout"}
```

##### File Rotation

When a log file reaches the `maxBytes` limit, it's automatically rotated:

```
/var/log/myapp.log          # Current log file
/var/log/myapp.log.1        # First backup
/var/log/myapp.log.2        # Second backup
/var/log/myapp.log.3        # Third backup
...
```

Old backup files beyond `backupCount` are automatically deleted.

##### Production Usage

For production environments, consider these best practices:

```bash
# Separate logs by environment
export FAPILOG_SINKS="file:///var/log/myapp/production.log?maxBytes=104857600&backupCount=10"

# Multiple sinks for redundancy
export FAPILOG_SINKS="stdout,file:///var/log/myapp/app.log"

# Application-specific paths
export FAPILOG_SINKS="file:///var/log/myapp/api.log?maxBytes=52428800&backupCount=5"
```

### Loki Sink

The Loki sink allows you to push logs directly to a [Grafana Loki](https://grafana.com/oss/loki/) endpoint over HTTP, enabling centralized log aggregation for distributed services.

### Installation

To use the Loki sink, install the optional dependency:

```bash
pip install fapilog[loki]
```

### Configuration

You can configure the Loki sink using a URI in the `FAPILOG_SINKS` environment variable or programmatically via `LoggingSettings`:

```env
FAPILOG_SINKS=loki://loki:3100?labels=app=myapi,env=dev
```

Or in Python:

```python
from fapilog.settings import LoggingSettings
settings = LoggingSettings(sinks=[
    "loki://loki:3100?labels=app=myapi,env=prod&batch_size=50&batch_interval=1.5"
])
```

#### URI Format

```
loki://host:port?labels=key1=val1,key2=val2&batch_size=100&batch_interval=2.0
https://host:port?labels=key1=val1
```

- **labels**: Static labels for all log streams (e.g., `labels=app=myapi,env=prod`)
- **batch_size**: Number of logs to buffer before pushing (default: 100)
- **batch_interval**: Max seconds to wait before pushing a batch (default: 2.0)

#### Features

- **Batching**: Logs are buffered and sent in batches to `/loki/api/v1/push`.
- **Async HTTP**: Uses `httpx.AsyncClient` for non-blocking HTTP push.
- **Retry Logic**: Failures are logged and retried with exponential backoff.
- **Optional Dependency**: Raises `ImportError` with guidance if `httpx` is not installed.
- **Graceful Degradation**: If Loki is unavailable, logs are retried up to the configured limit.

#### Example

```python
from fapilog.settings import LoggingSettings
settings = LoggingSettings(
    sinks=["loki://loki:3100?labels=app=myapi,env=prod&batch_size=50"]
)
logger = configure_logging(settings=settings)
logger.info("user_login", user_id="123", status="success")
```

#### Output Format

Each batch is sent as:

```json
{
  "streams": [
    {
      "stream": {"app": "myapi", "env": "prod"},
      "values": [["<timestamp_ns>", "<logline_json>"], ...]
    }
  ]
}
```

- **Timestamps** are in nanoseconds since epoch (RFC3339 or Unix time supported).
- **Log lines** are JSON-serialized event dicts.

#### Notes

- If you use the Loki sink, ensure your Loki endpoint is reachable from your app.
- Batching reduces HTTP load and aligns with Loki best practices.
- If `httpx` is not installed, you’ll get a clear ImportError with install instructions.

#### Installation Recap

```bash
pip install fapilog[loki]
```

See the [docs/stories/story-5.3.md](docs/stories/story-5.3.md) for full requirements and technical details.

### Resource Metrics

`fapilog` can optionally include memory and CPU usage metrics in log entries to help monitor system health and correlate log spikes with resource load.

#### Enabling Resource Metrics

**Environment variable:**

```bash
export FAPILOG_ENABLE_RESOURCE_METRICS=true
```

**Programmatic configuration:**

```python
from fapilog.settings import LoggingSettings

settings = LoggingSettings(enable_resource_metrics=True)
configure_logging(settings=settings)
```

#### Dependencies

Resource metrics require the `psutil` library. Install it with:

```bash
pip install fapilog[metrics]
```

Or manually:

```bash
pip install psutil>=5.9
```

#### Usage

When enabled, every log entry will include:

- `memory_mb`: Resident memory usage of the current process in megabytes (rounded float)
- `cpu_percent`: Process CPU usage percentage (float, 0.0-100.0)

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "info",
  "event": "Request processed",
  "memory_mb": 45.2,
  "cpu_percent": 12.5,
  "trace_id": "abc123def456",
  "status_code": 200,
  "latency_ms": 45.2
}
```

#### Performance Considerations

- Resource metrics are cached for performance and only updated when logs are generated
- The `psutil` library is imported lazily and only when metrics are enabled
- If `psutil` is not available, the enricher is silently skipped
- Resource metrics are added near the end of the pipeline (after context, before rendering)

### Custom Enrichers

`fapilog` supports custom enrichers that allow you to inject application-specific metadata into log events without modifying the core library. Custom enrichers are called at the end of the processor chain, after all built-in enrichers.

#### Registering Custom Enrichers

Custom enrichers follow the structlog processor signature: `(logger, method_name, event_dict) → event_dict`

```python
from fapilog.enrichers import register_enricher

def tenant_enricher(logger, method_name, event_dict):
    """Add tenant ID to all log events."""
    event_dict["tenant_id"] = "tenant_123"
    return event_dict

def session_enricher(logger, method_name, event_dict):
    """Add session ID to all log events."""
    event_dict["session_id"] = "session_456"
    return event_dict

# Register enrichers (call this during app startup)
register_enricher(tenant_enricher)
register_enricher(session_enricher)
```

#### Enricher Function Requirements

- **Signature**: Must have exactly 3 parameters: `logger`, `method_name`, `event_dict`
- **Return value**: Must return the modified `event_dict`
- **Error handling**: Exceptions are silently caught to prevent breaking the logging chain
- **Order**: Enrichers are called in registration order

#### Example: Multi-tenant Application

```python
from fapilog.enrichers import register_enricher
from fapilog._internal.context import get_context

def tenant_context_enricher(logger, method_name, event_dict):
    """Add tenant context from request headers."""
    context = get_context()
    tenant_id = context.get("tenant_id")
    if tenant_id:
        event_dict["tenant_id"] = tenant_id
    return event_dict

def user_context_enricher(logger, method_name, event_dict):
    """Add user context from request headers."""
    context = get_context()
    user_id = context.get("user_id")
    if user_id:
        event_dict["user_id"] = user_id
    return event_dict

# Register during app startup
register_enricher(tenant_context_enricher)
register_enricher(user_context_enricher)
```

#### Testing Custom Enrichers

```python
from fapilog.enrichers import clear_enrichers, register_enricher

def test_custom_enricher():
    # Clear any existing enrichers for test isolation
    clear_enrichers()

    def test_enricher(logger, method_name, event_dict):
        event_dict["test_field"] = "test_value"
        return event_dict

    register_enricher(test_enricher)

    # Your test logic here...
    # The enricher will be automatically applied to all log events
```

#### Clearing Enrichers

For test isolation or dynamic configuration, you can clear all registered enrichers:

```python
from fapilog.enrichers import clear_enrichers

# Clear all custom enrichers
clear_enrichers()
```

---

## 📦 Project Layout

```
fapilog/
├── __init__.py            # log facade + configurator
├── settings.py            # Pydantic-driven config
├── middleware.py          # TraceID & timing middleware
├── enrichers.py           # Standard field enrichers
├── sinks/                 # stdout.py, loki.py, …
└── _internal/
    ├── queue.py           # Async queue worker
    └── utils.py
tests/
README.md
pyproject.toml

```

---

## 📊 Log Fields

The following fields are automatically added to all log events:

| Field         | Type    | Description                 | Example                      |
| ------------- | ------- | --------------------------- | ---------------------------- |
| `timestamp`   | string  | ISO-8601 UTC timestamp      | `"2024-01-15T10:30:45.123Z"` |
| `level`       | string  | Log level                   | `"info"`, `"error"`          |
| `event`       | string  | Log message                 | `"Request processed"`        |
| `hostname`    | string  | System hostname             | `"web-server-01"`            |
| `pid`         | integer | Process ID                  | `12345`                      |
| `trace_id`    | string  | Request correlation ID      | `"abc123def456"`             |
| `span_id`     | string  | Request span ID             | `"xyz789uvw012"`             |
| `method`      | string  | HTTP request method         | `"GET"`, `"POST"`            |
| `path`        | string  | HTTP request path           | `"/api/users/123"`           |
| `client_ip`   | string  | Client IP address           | `"192.168.1.100"`            |
| `status_code` | integer | HTTP response status        | `200`, `404`, `500`          |
| `latency_ms`  | float   | Request duration in ms      | `45.2`                       |
| `req_bytes`   | integer | Request body size in bytes  | `1024`                       |
| `res_bytes`   | integer | Response body size in bytes | `512`                        |
| `user_agent`  | string  | Client User-Agent header    | `"curl/7.68.0"`              |
| `memory_mb`   | float   | Process memory usage in MB  | `45.2`                       |
| `cpu_percent` | float   | Process CPU usage %         | `12.5`                       |

## 🧪 Testing

```python
def test_trace_id(caplog_json):
    log.info("test_event", extra="value")
    record = caplog_json.find(event="test_event")
    assert "trace_id" in record
    assert record["extra"] == "value"
```

## 🏷️ Request Context Enrichment

`fapilog` automatically enriches all logs with HTTP request metadata through the `TraceIDMiddleware`. This provides complete request traceability without manual log field management.

### Automatic Fields

Every log event during a request automatically includes:

| Field         | Type    | Description            | Example            |
| ------------- | ------- | ---------------------- | ------------------ |
| `trace_id`    | string  | Request correlation ID | `"abc123def456"`   |
| `span_id`     | string  | Request span ID        | `"xyz789uvw012"`   |
| `method`      | string  | HTTP method            | `"POST"`           |
| `path`        | string  | Request path           | `"/api/users/123"` |
| `client_ip`   | string  | Client IP address      | `"192.168.1.100"`  |
| `status_code` | integer | HTTP response status   | `200`              |
| `latency_ms`  | float   | Request duration in ms | `45.2`             |
| `user_agent`  | string  | User-Agent header      | `"curl/7.68.0"`    |

### Configuration

Configure the trace ID header name using environment variables or settings:

```bash
# Environment variable (default: X-Request-ID)
export FAPILOG_TRACE_ID_HEADER=X-Custom-Trace-ID
```

```python
from fapilog.settings import LoggingSettings

settings = LoggingSettings(
    trace_id_header="X-Custom-Trace-ID"  # Default: "X-Request-ID"
)
configure_logging(settings=settings, app=app)
```

### Example Usage

```python
from fastapi import FastAPI
from fapilog import configure_logging, log

app = FastAPI()
configure_logging(app=app)  # Automatically registers TraceIDMiddleware

@app.post("/api/orders")
async def create_order(order_data: dict):
    # All these logs automatically include request context
    log.info("Order creation started", order_value=order_data.get("total"))

    try:
        order_id = await process_order(order_data)
        log.info("Order created successfully", order_id=order_id)
        return {"order_id": order_id, "status": "created"}
    except Exception as e:
        log.error("Order creation failed", error=str(e))
        raise
```

**Generated logs automatically include request context:**

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "info",
  "event": "Order creation started",
  "trace_id": "abc123def456",
  "span_id": "xyz789uvw012",
  "method": "POST",
  "path": "/api/orders",
  "client_ip": "192.168.1.100",
  "order_value": 299.99
}
```

### Trace ID Propagation

The middleware respects incoming trace IDs from headers and generates new ones when missing:

```bash
# Request with existing trace ID
curl -H "X-Request-ID: external-trace-123" http://localhost:8000/api/users

# Request without trace ID (auto-generated)
curl http://localhost:8000/api/users
```

### Manual Middleware Registration

If you prefer manual setup instead of using `configure_logging(app=app)`:

```python
from fapilog.middleware import TraceIDMiddleware
from fapilog.settings import LoggingSettings

app = FastAPI()
settings = LoggingSettings(trace_id_header="X-Custom-Trace")

# Register middleware manually
app.add_middleware(TraceIDMiddleware, trace_id_header=settings.trace_id_header)
configure_logging(settings=settings)
```

## 🔄 Using Context in Background Tasks

The logging context (trace_id, span_id, etc.) automatically propagates to background tasks using `context_copy()`:

```python
import asyncio
from fapilog._internal.context import context_copy, get_context

async def background_task():
    """Background task that inherits the request context."""
    context = get_context()
    log.info("Background task started",
             trace_id=context["trace_id"],
             span_id=context["span_id"])

@app.post("/process")
async def process_data():
    # Launch background task with context propagation
    task = asyncio.create_task(context_copy().run(background_task))

    # Main request continues...
    log.info("Processing started")

    # Wait for background task
    await task
    return {"status": "completed"}
```

The background task will log with the same `trace_id` as the original request, enabling end-to-end tracing across async operations.

---

## 🗺️ Roadmap

- [ ] Refactor to remove dependency on structlog
- [ ] OpenTelemetry span auto-capture
- [ ] SQLAlchemy slow-query detector
- [ ] Redis/RabbitMQ context propagation helpers
- [ ] Live log-level toggle endpoint (`/admin/log-level`)
- [ ] Kinesis / PubSub sinks

Contributions welcome—see **`CONTRIBUTING.md`** for guidelines.

---

## 🤝 License

Apache 2.0 — free for commercial and open-source use.

> _FastAPI-Logger is built for high-throughput async APIs, but the core modules are framework-agnostic—use them in Celery workers, scripts, or any structlog pipeline with minimal tweaks._

## Multiple Sink Support

`fapilog` supports writing log events to multiple destinations (sinks) in parallel. This is useful for redundancy, local debugging, and sending logs to multiple backends (e.g., stdout, file, and Loki) at the same time.

### How It Works

- **Fan-out:** Every log event is sent to all configured sinks.
- **Failure Isolation:** If one sink fails (e.g., network error to Loki), the others continue to receive logs. Failures are logged as warnings, and do not block the rest.
- **Concurrency:** All sinks are written to concurrently using `asyncio.gather(..., return_exceptions=True)` for maximum performance and isolation.

### Configuration

#### Environment Variable

Set the `FAPILOG_SINKS` environment variable to a comma-separated list of sink URIs:

```bash
# Example: stdout and Loki
export FAPILOG_SINKS="stdout,loki://loki:3100"

# Example: stdout and file
export FAPILOG_SINKS="stdout,file:///var/log/myapp.log"

# Example: all three
export FAPILOG_SINKS="stdout,file:///var/log/myapp.log,loki://loki:3100"
```

#### Programmatic Configuration

```python
from fapilog.settings import LoggingSettings

settings = LoggingSettings(
    sinks=[
        "stdout",
        "file:///var/log/myapp.log",
        "loki://loki:3100?labels=app=myapi,env=prod"
    ]
)
logger = configure_logging(settings=settings)
```

### Best Practices

- **Order:** Put `stdout` first for local development and debugging, so you always see logs in your terminal.
- **Redundancy:** Use both file and remote sinks (like Loki) for production reliability.
- **Startup Validation:** Misconfigured sinks (bad URI, missing dependencies) will raise errors at startup, not at runtime.

### Example

```bash
export FAPILOG_SINKS="stdout,file:///tmp/app.log,loki://localhost:3100"
```

Every log event will be written to your terminal, to `/tmp/app.log`, and to your Loki instance.

### Robustness

- All sinks are tested for fan-out and error isolation.
- See `tests/test_multi_sink.py` for comprehensive test coverage.
