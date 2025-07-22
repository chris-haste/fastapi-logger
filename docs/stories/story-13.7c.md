# Story 13.7c – Implement Sink Registry Documentation and Examples

**Epic:** 13 – Architecture Improvements  
Sprint Target: Sprint #⟪next⟫  
Story Points: 3

**As a developer**  
I want comprehensive documentation and examples for custom sink development  
So that I can easily learn how to create and use custom sinks with the registry system.

───────────────────────────────────  
Acceptance Criteria

- Comprehensive documentation for sink registry system
- Step-by-step guides for creating custom sinks
- Real-world examples for common sink types
- Troubleshooting guide for common issues
- Best practices for sink development
- Integration examples with popular services
- Performance optimization guides

───────────────────────────────────  
Tasks / Technical Checklist

1. **Create Sink Development Guide in `docs/sink-development.md`**:

   ````markdown
   # Custom Sink Development Guide

   ## Overview

   This guide explains how to create custom sinks for fapilog using the sink registry system.

   ## Basic Sink Implementation

   ```python
   from fapilog import register_sink, Sink
   from typing import Dict, Any

   @register_sink("my_sink")
   class MyCustomSink(Sink):
       def __init__(self, host="localhost", port=8080, **kwargs):
           super().__init__()
           self.host = host
           self.port = port

       async def write(self, event_dict: Dict[str, Any]) -> None:
           # Your sink implementation here
           pass
   ```
   ````

   ## URI Configuration

   Custom sinks can be configured via URIs:

   ```python
   # Basic configuration
   configure_logging(sinks=["my_sink://localhost:8080"])

   # With parameters
   configure_logging(sinks=["my_sink://user:pass@host:8080/path?ssl=true"])
   ```

   ## Environment Variable Configuration

   ```bash
   export FAPILOG_SINKS=my_sink://localhost:8080,stdout
   ```

   ```

   ```

2. **Create Real-World Sink Examples in `examples/sink_examples/`**:

   **PostgreSQL Sink Example (`examples/sink_examples/postgres_sink.py`)**:

   ```python
   import asyncpg
   from fapilog import register_sink, Sink
   from typing import Dict, Any

   @register_sink("postgres")
   class PostgresSink(Sink):
       def __init__(self, host="localhost", port=5432, database="logs",
                    user=None, password=None, **kwargs):
           super().__init__()
           self.host = host
           self.port = port
           self.database = database
           self.user = user
           self.password = password
           self.pool = None

       async def start(self):
           """Initialize database connection pool."""
           self.pool = await asyncpg.create_pool(
               host=self.host,
               port=self.port,
               database=self.database,
               user=self.user,
               password=self.password
           )

       async def stop(self):
           """Close database connection pool."""
           if self.pool:
               await self.pool.close()

       async def write(self, event_dict: Dict[str, Any]) -> None:
           """Write log event to PostgreSQL."""
           if not self.pool:
               raise RuntimeError("Sink not started")

           async with self.pool.acquire() as conn:
               await conn.execute("""
                   INSERT INTO logs (timestamp, level, event, data)
                   VALUES ($1, $2, $3, $4)
               """, event_dict.get("timestamp"), event_dict.get("level"),
                    event_dict.get("event"), event_dict)
   ```

   **Elasticsearch Sink Example (`examples/sink_examples/elasticsearch_sink.py`)**:

   ```python
   from elasticsearch import AsyncElasticsearch
   from fapilog import register_sink, Sink
   from typing import Dict, Any

   @register_sink("elasticsearch")
   class ElasticsearchSink(Sink):
       def __init__(self, host="localhost", port=9200, index="logs", **kwargs):
           super().__init__()
           self.host = host
           self.port = port
           self.index = index
           self.client = None

       async def start(self):
           """Initialize Elasticsearch client."""
           self.client = AsyncElasticsearch([f"{self.host}:{self.port}"])

       async def stop(self):
           """Close Elasticsearch client."""
           if self.client:
               await self.client.close()

       async def write(self, event_dict: Dict[str, Any]) -> None:
           """Write log event to Elasticsearch."""
           if not self.client:
               raise RuntimeError("Sink not started")

           await self.client.index(
               index=self.index,
               body=event_dict
           )
   ```

   **Slack Sink Example (`examples/sink_examples/slack_sink.py`)**:

   ```python
   import aiohttp
   from fapilog import register_sink, Sink
   from typing import Dict, Any

   @register_sink("slack")
   class SlackSink(Sink):
       def __init__(self, webhook_url, channel="#alerts", **kwargs):
           super().__init__()
           self.webhook_url = webhook_url
           self.channel = channel
           self.session = None

       async def start(self):
           """Initialize HTTP session."""
           self.session = aiohttp.ClientSession()

       async def stop(self):
           """Close HTTP session."""
           if self.session:
               await self.session.close()

       async def write(self, event_dict: Dict[str, Any]) -> None:
           """Send error logs to Slack."""
           if event_dict.get("level") != "error":
               return

           if not self.session:
               raise RuntimeError("Sink not started")

           message = {
               "channel": self.channel,
               "text": f"🚨 Error: {event_dict.get('event', 'Unknown error')}",
               "attachments": [{
                   "fields": [
                       {"title": "Trace ID", "value": event_dict.get("trace_id", "N/A")},
                       {"title": "User ID", "value": event_dict.get("user_id", "N/A")}
                   ]
               }]
           }

           await self.session.post(self.webhook_url, json=message)
   ```

3. **Create Performance Optimization Guide in `docs/sink-performance.md`**:

   ````markdown
   # Sink Performance Optimization Guide

   ## Batching for High Throughput

   ```python
   class BatchedSink(Sink):
       def __init__(self, batch_size=100, batch_timeout=5.0):
           super().__init__()
           self.batch_size = batch_size
           self.batch_timeout = batch_timeout
           self.buffer = []
           self._send_task = None

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

           if self.buffer:
               await self._send_batch(self.buffer)

       async def write(self, event_dict: Dict[str, Any]) -> None:
           """Add event to buffer."""
           self.buffer.append(event_dict)

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
   ```
   ````

   ## Connection Pooling

   ```python
   class PooledSink(Sink):
       def __init__(self, pool_size=10):
           super().__init__()
           self.pool_size = pool_size
           self.pool = None

       async def start(self):
           """Initialize connection pool."""
           self.pool = await create_connection_pool(
               size=self.pool_size
           )

       async def stop(self):
           """Close connection pool."""
           if self.pool:
               await self.pool.close()
   ```

   ```

   ```

4. **Create Troubleshooting Guide in `docs/sink-troubleshooting.md`**:

   ```markdown
   # Sink Troubleshooting Guide

   ## Common Issues and Solutions

   ### Sink Registration Fails

   **Error:** `SinkRegistrationError: Failed to register sink 'my_sink'`

   **Solutions:**

   - Ensure sink class inherits from `Sink`
   - Check that `write` method is async
   - Verify sink name is unique

   ### URI Parsing Errors

   **Error:** `SinkConfigurationError: Invalid URI format`

   **Solutions:**

   - Use standard URI format: `scheme://[user:pass@]host[:port]/path[?param=value]`
   - URL-encode special characters in parameters
   - Check parameter names match sink constructor

   ### Performance Issues

   **Symptoms:** High latency, memory leaks, connection timeouts

   **Solutions:**

   - Implement batching for high throughput
   - Use connection pooling for external services
   - Add proper error handling and retries
   - Monitor sink performance with testing utilities
   ```

5. **Create Integration Examples in `examples/sink_integrations/`**:

   **FastAPI Integration (`examples/sink_integrations/fastapi_integration.py`)**:

   ```python
   from fastapi import FastAPI
   from fapilog import configure_logging, register_sink, Sink
   from contextlib import asynccontextmanager

   @register_sink("custom")
   class CustomSink(Sink):
       def __init__(self, **kwargs):
           super().__init__()
           self.kwargs = kwargs

       async def write(self, event_dict: Dict[str, Any]) -> None:
           # Implementation
           pass

   @asynccontextmanager
   async def lifespan(app: FastAPI):
       # Configure logging with custom sink
       configure_logging(
           app=app,
           sinks=["custom://localhost:8080", "stdout"]
       )
       yield

   app = FastAPI(lifespan=lifespan)
   ```

   **Docker Integration (`examples/sink_integrations/docker_integration.py`)**:

   ```python
   # Dockerfile
   FROM python:3.11-slim

   # Install fapilog and custom sinks
   RUN pip install fapilog fapilog-postgres fapilog-elasticsearch

   # Set environment variables
   ENV FAPILOG_SINKS=postgres://postgres:5432/logs,elasticsearch://elasticsearch:9200/logs
   ENV FAPILOG_LEVEL=INFO

   # Your application code
   COPY . /app
   WORKDIR /app

   CMD ["python", "app.py"]
   ```

6. **Update API Reference Documentation**:

   - Add sink registry section to `docs/api-reference.md`
   - Document `@register_sink` decorator
   - Add URI configuration examples
   - Include error handling documentation

7. **Create Best Practices Guide in `docs/sink-best-practices.md`**:

   ````markdown
   # Sink Development Best Practices

   ## Design Principles

   1. **Fail Gracefully**: Never let sink errors break the application
   2. **Be Async**: Always implement async methods for non-blocking operation
   3. **Handle Resources**: Properly manage connections, sessions, and pools
   4. **Validate Input**: Check configuration parameters and log events
   5. **Monitor Performance**: Use testing utilities to measure performance

   ## Error Handling Patterns

   ```python
   async def write(self, event_dict: Dict[str, Any]) -> None:
       try:
           # Your sink logic here
           await self._send_to_service(event_dict)
       except Exception as e:
           # Log error but don't re-raise
           import logging
           logging.getLogger(__name__).error(
               f"Sink {self._sink_name} failed: {e}",
               extra={"sink_error": True, "original_event": event_dict}
           )
   ```
   ````

   ## Configuration Validation

   ```python
   def __init__(self, host="localhost", port=8080, **kwargs):
       super().__init__()

       # Validate required parameters
       if not host:
           raise ValueError("host is required")

       self.host = host
       self.port = port
   ```

   ```

   ```

8. **Create Video Tutorials and Screencasts**:

   - Step-by-step sink development tutorial
   - Performance optimization walkthrough
   - Troubleshooting common issues
   - Integration with popular services

───────────────────────────────────  
Dependencies / Notes

- Depends on Story 13.7a and 13.7b for sink registry and testing
- Should provide clear, actionable guidance
- Examples should be production-ready and well-tested
- Documentation should be comprehensive but not overwhelming
- Should include both basic and advanced patterns

───────────────────────────────────  
Definition of Done  
✓ Comprehensive sink development guide created  
✓ Real-world sink examples implemented (PostgreSQL, Elasticsearch, Slack)  
✓ Performance optimization guide written  
✓ Troubleshooting guide created with common issues  
✓ Integration examples provided (FastAPI, Docker)  
✓ API reference documentation updated  
✓ Best practices guide created  
✓ Video tutorials and screencasts produced  
✓ Documentation is clear, comprehensive, and actionable  
✓ PR merged to **main** with reviewer approval and green CI  
✓ `CHANGELOG.md` updated under _Unreleased → Added_

───────────────────────────────────  
**CURRENT STATUS: NOT STARTED**

**Remaining Tasks:**

- ❌ Create comprehensive sink development guide
- ❌ Implement real-world sink examples (PostgreSQL, Elasticsearch, Slack)
- ❌ Write performance optimization guide
- ❌ Create troubleshooting guide with common issues
- ❌ Provide integration examples (FastAPI, Docker)
- ❌ Update API reference documentation
- ❌ Create best practices guide
- ❌ Produce video tutorials and screencasts

───────────────────────────────────  
**Example Documentation Structure After Implementation**

```
docs/
├── sink-development.md          # Main development guide
├── sink-performance.md          # Performance optimization
├── sink-troubleshooting.md     # Troubleshooting guide
├── sink-best-practices.md      # Best practices
└── api-reference.md            # Updated with registry docs

examples/sink_examples/
├── postgres_sink.py           # PostgreSQL example
├── elasticsearch_sink.py      # Elasticsearch example
├── slack_sink.py             # Slack example
└── redis_sink.py             # Redis example

examples/sink_integrations/
├── fastapi_integration.py    # FastAPI integration
├── docker_integration.py     # Docker integration
└── kubernetes_integration.py # Kubernetes integration
```
