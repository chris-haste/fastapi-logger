User Guide
==========

This guide provides step-by-step tutorials for using ``fapilog`` in your applications. It's designed to take you from basic setup to advanced features, with practical examples throughout.

Table of Contents
-----------------

* `Quick Start`_
* `Basic Configuration`_
* `FastAPI Integration`_
* `User Context Enrichment`_
* `Advanced Configuration`_
* `Custom Enrichers`_
* `Container Architecture`_
* `Custom Sinks`_
* `Performance Tuning`_
* `Production Deployment`_
* `Troubleshooting`_

Quick Start
===========

Get up and running with ``fapilog`` in under 5 minutes.

Installation
------------

.. code-block:: bash

   pip install fapilog

Basic Setup
-----------

The simplest way to get started:

.. code-block:: python

   from fapilog import configure_logging, log

   # Configure logging with defaults
   configure_logging()

   # Start logging
   log.info("Application started", version="1.0.0")
   log.warning("Deprecated feature used", feature="old_api")
   log.error("Database connection failed", database="postgres")

**What happens:**

- Structured JSON logs are written to stdout
- Pretty-printed logs in development (TTY detection)
- Automatic trace ID generation
- Context variables for request correlation

Basic Configuration
===================

Environment Variables
--------------------

The easiest way to configure ``fapilog`` is through environment variables:

.. code-block:: bash

   # Basic configuration
   export FAPILOG_LEVEL=INFO
   export FAPILOG_SINKS=stdout
   export FAPILOG_JSON_CONSOLE=auto
   
   # Production configuration
   export FAPILOG_LEVEL=INFO
   export FAPILOG_SINKS=stdout,file:///var/log/app.log
   export FAPILOG_JSON_CONSOLE=json
   export FAPILOG_REDACT_PATTERNS=password,token,secret

Programmatic Configuration
-------------------------

For more control, configure programmatically:

.. code-block:: python

   from fapilog.settings import LoggingSettings
   from fapilog import configure_logging

   settings = LoggingSettings(
       level="DEBUG",
       sinks=["stdout", "file:///var/log/app.log"],
       queue_enabled=True,
       redact_patterns=["password", "token", "secret"]
   )
   
   configure_logging(settings=settings)

FastAPI Integration
==================

Zero-Config Setup
----------------

The simplest FastAPI integration:

.. code-block:: python

   from fastapi import FastAPI
   from fapilog import configure_logging, log

   app = FastAPI()
   
   # This automatically adds TraceIDMiddleware
   configure_logging(app=app)

   @app.get("/")
   async def root():
       log.info("Root endpoint accessed")
       return {"message": "Hello World"}

**Features provided:**

- Automatic request/response logging
- Trace ID generation and propagation
- Request timing and status codes
- Context enrichment with request details

Manual Middleware Setup
----------------------

For more control over middleware configuration:

.. code-block:: python

   from fastapi import FastAPI
   from fapilog import configure_logging
   from fapilog.middleware import TraceIDMiddleware

   app = FastAPI()
   
   # Configure logging first
   configure_logging()
   
   # Add middleware manually with options
   app.add_middleware(
       TraceIDMiddleware,
       trace_header="X-Trace-ID",
       generate_trace_id=True
   )

User Context Enrichment
=======================

Adding User Information
----------------------

Enrich logs with user context for better debugging:

.. code-block:: python

   from fapilog import log, set_user_context
   from fastapi import Depends

   async def get_current_user():
       # Your user authentication logic
       return {"user_id": "123", "username": "alice"}

   @app.get("/profile")
   async def get_profile(user=Depends(get_current_user)):
       # Set user context for all subsequent logs
       set_user_context(
           user_id=user["user_id"],
           username=user["username"]
       )
       
       log.info("Profile accessed")  # Automatically includes user context
       return {"profile": "data"}

Background Tasks
---------------

User context is preserved in background tasks:

.. code-block:: python

   from fastapi import BackgroundTasks

   def send_email(email: str):
       # User context from the request is still available
       log.info("Sending email", recipient=email)
       # Email sending logic here

   @app.post("/send-notification")
   async def send_notification(
       background_tasks: BackgroundTasks,
       user=Depends(get_current_user)
   ):
       set_user_context(user_id=user["user_id"])
       background_tasks.add_task(send_email, user["email"])
       return {"status": "queued"}

Advanced Configuration
=====================

Multiple Sinks
--------------

Send logs to multiple destinations:

.. code-block:: python

   settings = LoggingSettings(
       sinks=[
           "stdout",  # Console output
           "file:///var/log/app.log",  # File with rotation
           "loki://loki:3100"  # Grafana Loki
       ]
   )

PII Redaction
------------

Automatically redact sensitive information:

.. code-block:: python

   settings = LoggingSettings(
       redact_patterns=["password", "token", "ssn"],
       redact_fields=["user.email", "request.headers.authorization"],
       enable_auto_redact_pii=True
   )

Custom Enrichers
===============

Creating Custom Enrichers
-------------------------

Add custom context to all log messages:

.. code-block:: python

   from fapilog.enrichers import BaseEnricher

   class DatabaseEnricher(BaseEnricher):
       def enrich(self, event_dict):
           event_dict["db_pool_size"] = get_pool_size()
           event_dict["db_active_connections"] = get_active_connections()
           return event_dict

   # Register the enricher
   settings = LoggingSettings(
       custom_enrichers=[DatabaseEnricher()]
   )

Container Architecture
=====================

For applications with multiple logging configurations:

.. code-block:: python

   from fapilog.container import LoggingContainer

   # Create isolated logging containers
   api_container = LoggingContainer("api")
   worker_container = LoggingContainer("worker")
   
   # Configure each independently
   api_logger = api_container.configure(
       level="INFO",
       sinks=["stdout", "loki://loki:3100"]
   )
   
   worker_logger = worker_container.configure(
       level="DEBUG", 
       sinks=["file:///var/log/worker.log"]
   )

Custom Sinks
============

Creating a custom sink for external services:

.. code-block:: python

   from fapilog.sinks import BaseSink

   class SlackSink(BaseSink):
       def __init__(self, webhook_url: str):
           self.webhook_url = webhook_url
           
       async def emit(self, record):
           if record["level"] == "error":
               await self.send_to_slack(record)
               
       async def send_to_slack(self, record):
           # Implementation for Slack webhook
           pass

Performance Tuning
==================

Queue Configuration
------------------

Optimize for high-throughput scenarios:

.. code-block:: python

   settings = LoggingSettings(
       queue_enabled=True,
       queue_maxsize=5000,
       queue_batch_size=100,
       queue_batch_timeout=1.0,
       queue_overflow="drop"  # Drop oldest when full
   )

Sampling
--------

Reduce log volume in production:

.. code-block:: python

   settings = LoggingSettings(
       sampling_rate=0.1,  # Log only 10% of messages
       level="WARNING"     # Only warnings and above
   )

Production Deployment
====================

Docker Configuration
-------------------

.. code-block:: bash

   # Environment variables in docker-compose.yml
   environment:
     - FAPILOG_LEVEL=INFO
     - FAPILOG_SINKS=stdout,loki://loki:3100
     - FAPILOG_JSON_CONSOLE=json
     - FAPILOG_REDACT_PATTERNS=password,token,secret

Kubernetes ConfigMap
-------------------

.. code-block:: yaml

   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: app-logging-config
   data:
     FAPILOG_LEVEL: "INFO"
     FAPILOG_SINKS: "stdout,loki://loki.monitoring.svc.cluster.local:3100"
     FAPILOG_JSON_CONSOLE: "json"
     FAPILOG_REDACT_PATTERNS: "password,token,secret"

Troubleshooting
===============

Common Issues
------------

**Issue: Logs not appearing**

- Check log level configuration
- Verify sink configuration
- Check queue status if enabled

.. code-block:: python

   from fapilog.monitoring import get_queue_metrics
   
   metrics = get_queue_metrics()
   print(f"Queue size: {metrics.current_size}")
   print(f"Dropped messages: {metrics.dropped_messages}")

**Issue: Performance problems**

- Enable async queue
- Adjust batch sizes
- Consider sampling for high-volume scenarios

**Issue: Missing trace IDs**

- Ensure TraceIDMiddleware is properly configured
- Check that you're within a request context
- Verify middleware order

Debug Mode
----------

Enable debug mode for troubleshooting:

.. code-block:: python

   settings = LoggingSettings(
       level="DEBUG",
       enable_debug_logging=True
   )

.. note::
   For complete tutorials and examples, see the full user guide in the source markdown file: ``docs/user-guide.md`` 