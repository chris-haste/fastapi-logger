API Reference
=============

This document provides a complete reference for all public APIs in ``fapilog``. The API is designed to be simple for basic usage while remaining fully extensible for advanced scenarios.

Table of Contents
-----------------

* `Core Functions`_
* `Configuration`_
* `Logging Interface`_
* `Middleware`_
* `Trace Propagation`_
* `Enrichers`_
* `Sinks`_
* `Metrics and Monitoring`_
* `Context Management`_
* `Types and Models`_

Core Functions
==============

configure_logging()
-------------------

The primary function for setting up structured logging in your application.

.. code-block:: python

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

**Parameters:**

- ``settings`` (LoggingSettings, optional): Complete configuration object. If ``None``, created from environment variables.
- ``app`` (Any, optional): FastAPI app instance. If provided, ``TraceIDMiddleware`` is automatically registered.

**Returns:**

- ``structlog.BoundLogger``: Configured logger instance

**Raises:**

- ``RuntimeError``: If called from an async context without proper setup

.. note::
   This function is idempotent - subsequent calls will not duplicate handlers. When ``app`` is provided, middleware is registered and shutdown handlers are configured. Environment variables with ``FAPILOG_`` prefix are automatically loaded.

get_current_trace_id()
----------------------

Access the current trace ID from within a request context.

.. code-block:: python

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

**Returns:**

- ``str | None``: Current trace ID if within a request context, ``None`` otherwise

**Use Cases:**

- Business logic that needs to include trace ID in responses
- Custom error handling with trace correlation
- Integration with external services requiring trace headers
- Audit logging with request correlation

.. note::
   Only available within request context (when using ``TraceIDMiddleware``). Returns ``None`` when called outside of a request (e.g., startup, background tasks). The trace ID is either extracted from incoming headers or auto-generated. Thread-safe and async-safe via ``contextvars``.

Configuration
=============

LoggingSettings
---------------

Configuration class for all logging settings. Can be configured via environment variables or programmatically.

.. code-block:: python

   from fapilog.settings import LoggingSettings

   settings = LoggingSettings(
       level="INFO",
       sinks=["stdout", "file:///var/log/app.log"],
       queue_enabled=True,
       redact_patterns=["password", "token"]
   )

**Key Configuration Options:**

- ``level``: Log level (DEBUG, INFO, WARN, ERROR, CRITICAL)
- ``sinks``: List of output destinations
- ``queue_enabled``: Enable async logging queue
- ``redact_patterns``: Patterns to redact from logs
- ``json_console``: Console output format (auto, json, pretty)

For complete configuration reference, see :doc:`config`.

Logging Interface
=================

The main logging interface provided by ``fapilog``.

.. code-block:: python

   from fapilog import log

   # Basic logging
   log.info("User logged in", user_id=123)
   log.error("Database error", error=str(e), table="users")
   
   # With structured data
   log.info("Request processed", 
            method="GET", 
            path="/api/users", 
            status_code=200,
            duration_ms=45)

**Log Levels:**

- ``log.debug()``: Detailed information for debugging
- ``log.info()``: General information messages
- ``log.warning()`` / ``log.warn()``: Warning messages
- ``log.error()``: Error messages
- ``log.critical()``: Critical error messages

Middleware
==========

TraceIDMiddleware
-----------------

FastAPI middleware for automatic trace ID injection and request context enrichment.

.. code-block:: python

   from fastapi import FastAPI
   from fapilog.middleware import TraceIDMiddleware

   app = FastAPI()
   
   # Manual registration
   app.add_middleware(TraceIDMiddleware)
   
   # Or use configure_logging() with app parameter
   from fapilog import configure_logging
   configure_logging(app=app)  # Automatically adds middleware

**Features:**

- Automatic trace ID generation and propagation
- Request timing and status code logging
- Context variable management
- Request/response logging

Trace Propagation
=================

Functions for working with distributed tracing.

.. code-block:: python

   from fapilog import get_current_trace_id, get_trace_headers

   # Get current trace ID
   trace_id = get_current_trace_id()
   
   # Get headers for downstream requests
   headers = get_trace_headers()
   response = httpx.get("https://api.example.com", headers=headers)

Enrichers
=========

Custom enrichers for adding contextual information to logs.

.. code-block:: python

   from fapilog.enrichers import RequestEnricher, ResourceEnricher
   
   # Built-in enrichers are automatically configured
   # Custom enrichers can be added via settings

Sinks
=====

Output destinations for log messages.

**Built-in Sinks:**

- ``stdout``: Console output
- ``file://path/to/file.log``: File output with rotation
- ``loki://host:port``: Grafana Loki integration

.. code-block:: python

   # Configure multiple sinks
   settings = LoggingSettings(
       sinks=[
           "stdout",
           "file:///var/log/app.log",
           "loki://loki:3100"
       ]
   )

Metrics and Monitoring
======================

Performance and health metrics integration.

.. code-block:: python

   from fapilog.monitoring import get_queue_metrics
   
   # Get current queue status
   metrics = get_queue_metrics()
   print(f"Queue size: {metrics.current_size}")
   print(f"Total processed: {metrics.total_processed}")

Context Management
==================

Functions for managing request and user context.

.. code-block:: python

   from fapilog import set_user_context, get_user_context
   
   # Set user context
   set_user_context(user_id="123", username="alice")
   
   # Context is automatically included in logs
   log.info("Action performed")  # Includes user_id and username

Types and Models
================

Core data types and Pydantic models used by ``fapilog``.

**Key Types:**

- ``LogLevel``: Enumeration of log levels
- ``SinkConfig``: Configuration for output sinks
- ``QueueConfig``: Async queue configuration
- ``RedactionConfig``: PII redaction settings

.. note::
   For complete API documentation with all functions, classes, and parameters, see the full API reference in the source markdown file: ``docs/api-reference.md`` 