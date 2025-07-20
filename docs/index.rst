FastAPI-Logger (``fapilog``)
==============================

.. image:: https://github.com/chris-haste/fastapi-logger/actions/workflows/ci.yml/badge.svg
   :target: https://github.com/chris-haste/fastapi-logger/actions
   :alt: CI

.. image:: https://img.shields.io/badge/License-Apache%202.0-blue.svg
   :target: https://opensource.org/licenses/Apache-2.0
   :alt: License

.. image:: https://img.shields.io/badge/python-3.8+-blue.svg
   :target: https://python.org
   :alt: Python

.. image:: https://img.shields.io/pypi/v/fapilog
   :target: https://pypi.org/project/fapilog/
   :alt: PyPI

**Production-ready structured logging for FastAPI with trace IDs, async queues, and observability integration.**

``fapilog`` delivers enterprise-grade logging with zero friction—JSON logs, distributed tracing, async-safe queues, and observability hooks—so every microservice in your stack emits consistent, query-friendly events from day one.

.. note::
   **Package Info**: This project is published to PyPI as ``fapilog`` and developed in the ``fastapi-logger`` repository.

Why Choose fapilog?
===================

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Feature
     - fapilog Advantage
   * - **Zero-friction setup**
     - One-liner ``configure_logging()``—no YAML gymnastics or copy-pasted boilerplate.
   * - **Production-ready**
     - Built for high-traffic microservices with async queues, distributed tracing, and observability integration.
   * - **Structured by default**
     - JSON logs (Docker & cloud-native friendly) with pretty console rendering for local development.
   * - **Context propagation**
     - Trace ID, span ID, request path, status, user ID flow through ``contextvars`` without polluting your code.
   * - **Async & non-blocking**
     - Background queue + worker ensures log writing never blocks the event loop, even under high RPS.
   * - **Enterprise security**
     - Built-in PII redaction, field-level allow/deny lists, GDPR-friendly opt-outs, and audit trails.
   * - **Observability integration**
     - Native OpenTelemetry spans, Prometheus/OTLP metrics, and correlation IDs across logs, traces, and metrics.
   * - **Container architecture**
     - Clean dependency injection with multiple configurations, thread safety, and excellent testability.
   * - **Extensible architecture**
     - Pluggable sinks (stdout, files, Loki, HTTP) and custom enrichers with just a few lines of code.
   * - **Developer experience**
     - Pytest fixtures, comprehensive examples, and detailed documentation for rapid adoption.

Comparison with Alternatives
============================

.. list-table::
   :header-rows: 1
   :widths: 25 20 20 20 15

   * - Feature
     - fapilog
     - fastapi-logger
     - structlog
     - Basic logging
   * - **Zero-config setup**
     - ✅ One-liner
     - ❌ Manual setup
     - ❌ Manual setup
     - ❌ Manual setup
   * - **Async-safe**
     - ✅ Background queue
     - ❌ Blocking
     - ❌ Blocking
     - ❌ Blocking
   * - **Distributed tracing**
     - ✅ Native support
     - ❌ Manual
     - ❌ Manual
     - ❌ Manual
   * - **PII redaction**
     - ✅ Built-in
     - ❌ Manual
     - ❌ Manual
     - ❌ Manual
   * - **Observability hooks**
     - ✅ OpenTelemetry
     - ❌ None
     - ❌ None
     - ❌ None
   * - **Container architecture**
     - ✅ Dependency injection
     - ❌ Global state
     - ❌ Global state
     - ❌ Global state
   * - **Multiple configs**
     - ✅ Isolated containers
     - ❌ Single config
     - ❌ Single config
     - ❌ Single config
   * - **Production-ready**
     - ✅ Enterprise features
     - ⚠️ Basic
     - ⚠️ Basic
     - ❌ Basic
   * - **FastAPI integration**
     - ✅ Native middleware
     - ✅ Native
     - ❌ Manual
     - ❌ Manual

Quick Start
===========

Installation
------------

.. code-block:: bash

   pip install fapilog

For additional features, install optional dependencies:

.. code-block:: bash

   # With Loki support
   pip install fapilog[loki]

   # With FastAPI integration helpers
   pip install fapilog[fastapi]

   # With system metrics support
   pip install fapilog[metrics]

   # For development
   pip install fapilog[dev]

Version Pinning
~~~~~~~~~~~~~~~

For production deployments, we recommend pinning the version to ensure reproducible builds:

.. code-block:: bash

   # Production (allows patch updates)
   pip install fapilog~=0.1.0

   # Strict reproducibility (exact version)
   pip install fapilog==0.1.0

Python Compatibility
~~~~~~~~~~~~~~~~~~~~~

``fapilog`` requires Python 3.8 or higher and is compatible with Python 3.8, 3.9, 3.10, 3.11, and 3.12.

Basic Usage
-----------

After installation, you can start logging immediately:

.. code-block:: python

   from fapilog import configure_logging, log

   configure_logging()
   log.info("Hello from fapilog!")

FastAPI Integration
-------------------

.. code-block:: python

   # main.py
   from fastapi import FastAPI
   from fapilog import configure_logging, log

   configure_logging()              # instant logging superpowers

   app = FastAPI()

   @app.get("/ping")
   async def ping():
       log.info("ping_hit")         # JSON log with trace_id, path, method, etc.
       return {"pong": True}

Run the service:

.. code-block:: bash

   uvicorn app.main:app --reload

Local console shows colourised logs; in production the same call emits compact JSON suitable for Loki, Cloud Logging, or ELK.

Configuration
-------------

``fapilog`` is designed for zero-configuration setup but offers extensive customization options. All settings can be configured via environment variables or programmatically.

**Quick Configuration Examples:**

.. code-block:: bash

   # Basic configuration
   export FAPILOG_LEVEL=INFO
   export FAPILOG_SINKS=stdout
   export FAPILOG_JSON_CONSOLE=auto

   # Production configuration
   export FAPILOG_LEVEL=INFO
   export FAPILOG_SINKS=stdout,file:///var/log/app.log,loki://loki:3100
   export FAPILOG_JSON_CONSOLE=json
   export FAPILOG_REDACT_PATTERNS=password,token,secret

**Programmatic Configuration:**

.. code-block:: python

   from fapilog.settings import LoggingSettings
   from fapilog import configure_logging

   settings = LoggingSettings(
       level="DEBUG",
       sinks=["stdout", "file:///var/log/app.log"],
       redact_patterns=["password", "token"],
       queue_enabled=True
   )
   logger = configure_logging(settings=settings)

.. note::
   📖 **For complete configuration reference, see** :doc:`config`

Table of Contents
=================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   config
   api-reference
   user-guide

Development Setup
=================

.. code-block:: bash

   git clone https://github.com/chris-haste/fastapi-logger.git
   cd fastapi-logger
   python -m venv .venv && source .venv/bin/activate
   pip install -e ".[dev]"
   hatch run test

.. note::
   **Repository vs Package Name**: This project is developed in the ``fastapi-logger`` repository but published to PyPI as ``fapilog``. The repository name is descriptive of the project's purpose, while the package name is concise and memorable.

.. warning::
   The test suite enforces a minimum coverage threshold of 85% using ``pytest-cov``. If coverage falls below this threshold, the test run will fail locally and in CI. To see a detailed coverage report, use ``hatch run test-cov`` or inspect the HTML report in ``htmlcov/`` after running tests.

Development Commands
--------------------

* ``hatch run lint`` - Run Ruff linter
* ``hatch run typecheck`` - Run MyPy type checker
* ``hatch run test`` - Run pytest test suite
* ``hatch run test-cov`` - Run tests with coverage report
* ``hatch run test-queue-load`` - Run load testing for logging queue

Pre-commit Hooks
----------------

This project uses pre-commit hooks to ensure code quality. The hooks run automatically on staged files and include:

* **Ruff** - Linting and code formatting
* **MyPy** - Type checking
* **Vulture** - Dead code detection

**Setup:**

.. code-block:: bash

   # Install pre-commit (included in dev dependencies)
   pip install -e ".[dev]"

   # Install the git hooks
   pre-commit install

   # Run manually on all files
   pre-commit run --all-files

.. note::
   The pre-commit hooks will run automatically on staged files when you commit. You can also run them manually using the commands above.

Contributing
============

We welcome contributions! Please see our `Contributing Guide <https://github.com/chris-haste/fastapi-logger/blob/main/CONTRIBUTING.md>`_ for detailed information on:

* Setting up your development environment
* Code style and testing guidelines
* Commit message conventions
* Pull request process
* Release procedures

How It Works
============

.. code-block:: text

   Request ─► TraceIDMiddleware ─► structlog pipeline ─► Async Queue ─► Sink(s)
                 ▲                                            │
                 └──────────── contextvars (trace_id, user_id, …)
                                                 stdout, file, Loki…

**Core Components:**

* **middleware.py** — injects trace/context and measures request duration
* **enrichers.py** — attaches hostname, memory usage, SQL timings, etc.
* **_internal/queue.py** — decouples log generation from I/O
* **sinks/** — pluggable writers (stdout, file, Loki, custom)

**Configuration:** All behavior is configurable via environment variables or programmatic settings. See :doc:`config` for complete reference.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search` 