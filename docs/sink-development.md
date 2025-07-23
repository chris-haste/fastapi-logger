# Sink Development Guide

**Part of the [Advanced Development](advanced-development.md) journey - Build custom sinks for any destination**

> 🚀 **New to Advanced Development?** Start with the [Advanced Development Overview](advanced-development.md) to understand when and why you need custom sinks.

---

## Overview

This guide explains how to create custom sinks for fapilog using the sink registry system. Sinks are responsible for writing log events to various destinations like databases, external services, or message queues.

**This is Step 1 in the Sink Development Journey:**

1. **Learn the Fundamentals** (You are here)
2. [Production-Ready Development](sink-best-practices.md)
3. [Performance Optimization](sink-performance.md)
4. [Debugging & Troubleshooting](sink-troubleshooting.md)

---

## When You Need Custom Sinks

Before building a custom sink, consider if your use case fits these scenarios:

- **✅ Perfect for custom sinks:** MongoDB, Kafka, Custom APIs, Proprietary systems
- **⚠️ Check existing options first:** PostgreSQL, Elasticsearch, Redis (see [real-world examples](../examples/sink_examples/))
- **❌ Avoid custom sinks for:** Basic file output, stdout, syslog (built-in sinks available)

---

## Basic Sink Implementation

```python
from fapilog import register_sink, Sink
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

@register_sink("my_sink")
class MyCustomSink(Sink):
    def __init__(self, host="localhost", port=8080, **kwargs):
        super().__init__()

        # Validate configuration
        if not host:
            raise ValueError("host parameter is required")

        self.host = host
        self.port = port

    async def start(self):
        """Initialize resources (connections, sessions, etc.)"""
        # Optional: setup connections, pools, etc.
        logger.info(f"Custom sink started on {self.host}:{self.port}")

    async def stop(self):
        """Cleanup resources"""
        # Optional: cleanup connections, pools, etc.
        logger.info("Custom sink stopped")

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Write log event - this is the main method you must implement"""
        try:
            # Your sink implementation here
            await self._send_to_service(event_dict)
        except Exception as e:
            # CRITICAL: Never re-raise exceptions from sinks
            logger.error(
                f"Sink {self.__class__.__name__} failed: {e}",
                extra={"sink_error": True, "original_event": event_dict}
            )

    async def _send_to_service(self, event_dict: Dict[str, Any]) -> None:
        """Private method for actual sending logic"""
        # Implementation details here
        pass
```

## URI Configuration

Custom sinks can be configured via URIs:

```python
from fapilog import configure_logging

# Basic configuration
configure_logging(sinks=["my_sink://localhost:8080"])

# With parameters
configure_logging(sinks=["my_sink://user:pass@host:8080/path?ssl=true&timeout=30"])

# Multiple sinks
configure_logging(sinks=[
    "my_sink://localhost:8080",
    "stdout",
    "file:///var/log/app.log"
])
```

## Environment Variable Configuration

```bash
export FAPILOG_SINKS=my_sink://localhost:8080,stdout
export FAPILOG_LEVEL=INFO
```

## Advanced Patterns

### Batching for Performance

```python
import asyncio
from collections import deque

@register_sink("batched_sink")
class BatchedSink(Sink):
    def __init__(self, batch_size=100, batch_timeout=5.0, **kwargs):
        super().__init__()
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.buffer = deque()
        self._send_task = None
        self._buffer_lock = asyncio.Lock()

    async def start(self):
        self._send_task = asyncio.create_task(self._batch_sender())

    async def stop(self):
        if self._send_task:
            self._send_task.cancel()
            # Flush remaining data
            if self.buffer:
                await self._send_batch(list(self.buffer))

    async def write(self, event_dict: Dict[str, Any]) -> None:
        async with self._buffer_lock:
            self.buffer.append(event_dict)
            if len(self.buffer) >= self.batch_size:
                await self._flush_buffer()

    async def _batch_sender(self):
        while True:
            try:
                await asyncio.sleep(self.batch_timeout)
                await self._flush_buffer()
            except asyncio.CancelledError:
                break

    async def _flush_buffer(self):
        if not self.buffer:
            return
        batch = list(self.buffer)
        self.buffer.clear()
        await self._send_batch(batch)
```

## Testing Your Sink

```python
import pytest
from fapilog.testing import SinkTestFramework

@pytest.mark.asyncio
async def test_my_sink():
    sink = MyCustomSink(host="test.local", port=9999)

    # Use testing framework for comprehensive testing
    framework = SinkTestFramework(sink)

    # Test basic functionality
    await framework.test_basic_write()

    # Test error handling
    await framework.test_error_scenarios()

    # Test performance
    await framework.test_throughput(events_count=1000)
```

---

## Next Steps in Your Sink Development Journey

🎉 **Congratulations!** You've learned the fundamentals of sink development.

**Ready for the next step?**

1. **[Sink Best Practices](sink-best-practices.md)** - Make your sink production-ready
2. **[Sink Performance Guide](sink-performance.md)** - Optimize for high-throughput scenarios
3. **[Real-World Examples](../examples/sink_examples/)** - Study production implementations
4. **[Sink Troubleshooting](sink-troubleshooting.md)** - Debug issues when they arise

**Or jump to a specific use case:**

- **Need high performance?** → [Performance Guide](sink-performance.md)
- **Ready for production?** → [Best Practices](sink-best-practices.md)
- **Having issues?** → [Troubleshooting Guide](sink-troubleshooting.md)

---

## Resources

- **[Advanced Development Overview](advanced-development.md)** - Complete journey overview
- **[Real-World Examples](../examples/sink_examples/)** - PostgreSQL, Elasticsearch, Slack, Redis
- **[Integration Patterns](../examples/sink_integrations/)** - FastAPI, Docker, Kubernetes
- **[Community Discussions](https://github.com/chris-haste/fastapi-logger/discussions)** - Share your sink implementations
