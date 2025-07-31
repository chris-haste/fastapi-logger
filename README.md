# FastAPI-Logger (`fapilog`)

![CI](https://github.com/chris-haste/fastapi-logger/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![PyPI](https://img.shields.io/pypi/v/fapilog)
![PyPI](https://img.shields.io/pypi/status/fapilog)
![Codecov](https://codecov.io/gh/chris-haste/fastapi-logger/graph/badge.svg)

**Production-ready structured logging for FastAPI with trace IDs, async queues, and observability integration.**

`fapilog` delivers enterprise-grade logging with zero friction—JSON logs, distributed tracing, async-safe queues, and observability hooks—so every microservice in your stack emits consistent, query-friendly events from day one.

> **Package Info**: This project is published to PyPI as `fapilog` and developed in the `fastapi-logger` repository.

---

## ✨ Why Choose fapilog?

| Feature                       | fapilog Advantage                                                                                           |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------- |
| **Zero-friction setup**       | One-liner `configure_logging()`—no YAML gymnastics or copy-pasted boilerplate.                              |
| **Production-ready**          | Built for high-traffic microservices with async queues, distributed tracing, and observability integration. |
| **Structured by default**     | JSON logs (Docker & cloud-native friendly) with pretty console rendering for local development.             |
| **Context propagation**       | Trace ID, span ID, request path, status, user ID flow through `contextvars` without polluting your code.    |
| **Async & non-blocking**      | Background queue + worker ensures log writing never blocks the event loop, even under high RPS.             |
| **Enterprise security**       | Built-in PII redaction, field-level allow/deny lists, GDPR-friendly opt-outs, and audit trails.             |
| **Observability integration** | Native OpenTelemetry spans, Prometheus/OTLP metrics, and correlation IDs across logs, traces, and metrics.  |
| **Container architecture**    | Clean dependency injection with multiple configurations, thread safety, and excellent testability.          |
| **Extensible architecture**   | Pluggable sinks (stdout, files, Loki, HTTP) and custom enrichers with just a few lines of code.             |
| **Developer experience**      | Pytest fixtures, comprehensive examples, and detailed documentation for rapid adoption.                     |

---

## 📊 Comparison with Alternatives

| Feature                    | fapilog                 | fastapi-logger   | structlog        | Basic logging    |
| -------------------------- | ----------------------- | ---------------- | ---------------- | ---------------- |
| **Zero-config setup**      | ✅ One-liner            | ❌ Manual setup  | ❌ Manual setup  | ❌ Manual setup  |
| **Async-safe**             | ✅ Background queue     | ❌ Blocking      | ❌ Blocking      | ❌ Blocking      |
| **Distributed tracing**    | ✅ Native support       | ❌ Manual        | ❌ Manual        | ❌ Manual        |
| **PII redaction**          | ✅ Built-in             | ❌ Manual        | ❌ Manual        | ❌ Manual        |
| **Observability hooks**    | ✅ OpenTelemetry        | ❌ None          | ❌ None          | ❌ None          |
| **Container architecture** | ✅ Dependency injection | ❌ Global state  | ❌ Global state  | ❌ Global state  |
| **Multiple configs**       | ✅ Isolated containers  | ❌ Single config | ❌ Single config | ❌ Single config |
| **Production-ready**       | ✅ Enterprise features  | ⚠️ Basic         | ⚠️ Basic         | ❌ Basic         |
| **FastAPI integration**    | ✅ Native middleware    | ✅ Native        | ❌ Manual        | ❌ Manual        |

---

## 🚀 Quick Start

### Installation

```bash
pip install fapilog
```

For additional features, install optional dependencies:

```bash
# With Loki support
pip install fapilog[loki]

# With FastAPI integration helpers
pip install fapilog[fastapi]

# With system metrics support
pip install fapilog[metrics]

# For development
pip install fapilog[dev]
```

#### Version Pinning

For production deployments, we recommend pinning the version to ensure reproducible builds:

```bash
# Production (allows patch updates)
pip install fapilog~=0.1.0

# Strict reproducibility (exact version)
pip install fapilog==0.1.0
```

#### Python Compatibility

`fapilog` requires Python 3.8 or higher and is compatible with Python 3.8, 3.9, 3.10, 3.11, and 3.12.

### Basic Usage

After installation, you can start logging immediately:

```python
from fapilog import configure_logging, log

configure_logging()
log.info("Hello from fapilog!")
```

### FastAPI Integration

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

### Quick Configuration

**Environment variables for common setups:**

```bash
# Development
export FAPILOG_LEVEL=DEBUG
export FAPILOG_JSON_CONSOLE=pretty

# Production
export FAPILOG_LEVEL=INFO
export FAPILOG_SINKS=stdout,file:///var/log/app.log,loki://loki:3100
export FAPILOG_JSON_CONSOLE=json
export FAPILOG_REDACT_PATTERNS=password,token,secret
```

**Programmatic configuration:**

```python
from fapilog.settings import LoggingSettings
from fapilog import configure_logging

settings = LoggingSettings(
    level="INFO",
    sinks=["stdout", "file:///var/log/app.log"],
    redact_patterns=["password", "token"],
    queue_enabled=True
)
logger = configure_logging(settings=settings)
```

📖 **For complete configuration reference, see [Configuration Guide](https://fapilog.readthedocs.io/en/latest/config.html) or [docs/config.md](docs/config.md)**

---

## 📖 Documentation

### 📚 Complete Documentation

- **[📚 ReadTheDocs](https://fapilog.readthedocs.io/)** - Complete documentation with search
- **[Configuration Guide](docs/config.md)** - All 22 configuration settings with examples
- **[API Reference](docs/api-reference.md)** - Complete technical reference
- **[User Guide](docs/user-guide.md)** - Step-by-step tutorials and best practices
- **[Examples](examples/)** - Real-world usage patterns and recipes
- **[Troubleshooting](docs/troubleshooting.md)** - Common issues and solutions
- **[FAQ](docs/faq.md)** - Frequently asked questions

### Quick Navigation

**For New Users:**

- [Introduction](docs/introduction.md) → [Primer](docs/primer.md) → [Quickstart](docs/quickstart.md)

**For Developers:**

- [Configuration Guide](docs/config.md) → [API Reference](docs/api-reference.md) → [Examples](examples/)

**For Production:**

- [User Guide - Production Deployment](docs/user-guide.md#production-deployment) → [Troubleshooting](docs/troubleshooting.md)

---

## 🛠 Development Setup

```bash
git clone https://github.com/chris-haste/fastapi-logger.git
cd fastapi-logger
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
hatch run test
```

> **Repository vs Package Name**: This project is developed in the `fastapi-logger` repository but published to PyPI as `fapilog`. The repository name is descriptive of the project's purpose, while the package name is concise and memorable.

> **Note:** The test suite enforces a minimum coverage threshold of 85% using `pytest-cov`. If coverage falls below this threshold, the test run will fail locally and in CI. To see a detailed coverage report, use `hatch run test-cov` or inspect the HTML report in `htmlcov/` after running tests.

### Development Commands

- `hatch run lint` - Run Ruff linter
- `hatch run typecheck` - Run MyPy type checker
- `hatch run test` - Run pytest test suite
- `hatch run test-cov` - Run tests with coverage report
- `hatch run test-queue-load` - Run load testing for logging queue

### Pre-commit Hooks

This project uses pre-commit hooks to ensure code quality. The hooks run automatically on staged files and include:

- **Ruff** - Linting and code formatting
- **MyPy** - Type checking
- **Vulture** - Dead code detection

**Setup:**

```bash
# Install pre-commit (included in dev dependencies)
pip install -e ".[dev]"

# Install the git hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

**Note:** The pre-commit hooks will run automatically on staged files when you commit. You can also run them manually using the commands above.

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for detailed information on:

- Setting up your development environment
- Code style and testing guidelines
- Commit message conventions
- Pull request process
- Release procedures

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

## 📋 Changelog

See [CHANGELOG.md](CHANGELOG.md) for a complete history of changes and releases.

---

## 📊 Key Features

### Core Capabilities

- **Structured JSON logging** with automatic field enrichment
- **Distributed tracing** with trace ID propagation across services
- **Async-safe logging queue** that never blocks your application
- **Multiple sink support** (stdout, file, Loki, custom)
- **Automatic PII redaction** with configurable patterns
- **Container architecture** for isolated configurations and testing
- **FastAPI middleware** for automatic request context enrichment
- **Resource metrics** (memory, CPU) with optional psutil integration
- **Custom enrichers** for application-specific metadata
- **Comprehensive error handling** with graceful degradation

### Production Features

- **High-performance async queue** with configurable overflow strategies
- **Automatic log flushing** on application shutdown
- **Load testing tools** for queue performance validation
- **Prometheus metrics** for monitoring logging health
- **Thread-safe containers** for concurrent access
- **Graceful error handling** with detailed exception types
- **Environment-driven configuration** (12-factor app compliant)

### Developer Experience

- **Zero-configuration setup** with sensible defaults
- **Comprehensive documentation** with examples and tutorials
- **Type hints** throughout the codebase
- **Extensive test coverage** (85% minimum threshold)
- **Pre-commit hooks** for code quality
- **Load testing tools** for performance validation
- **Multiple configuration patterns** for different environments

📖 **For detailed feature documentation, see [User Guide](docs/user-guide.md) and [API Reference](docs/api-reference.md)**
