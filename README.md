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

Shutdown behavior is automatically configured and doesn't require additional setup. The system handles both async and sync shutdown contexts transparently.

---

## 🔧 Configuration

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
