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
| `trace_id`    | string  | Request correlation ID      | `"abc123def456"`             |
| `span_id`     | string  | Request span ID             | `"xyz789uvw012"`             |
| `status_code` | integer | HTTP response status        | `200`, `404`, `500`          |
| `latency_ms`  | float   | Request duration in ms      | `45.2`                       |
| `req_bytes`   | integer | Request body size in bytes  | `1024`                       |
| `res_bytes`   | integer | Response body size in bytes | `512`                        |
| `user_agent`  | string  | Client User-Agent header    | `"curl/7.68.0"`              |

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
