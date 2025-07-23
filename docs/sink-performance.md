# Sink Performance Guide

**Part of the [Advanced Development](advanced-development.md) journey - Optimization techniques for high-throughput**

> 📚 **Previous Steps:** [Sink Development Guide](sink-development.md) → [Sink Best Practices](sink-best-practices.md)

---

## Overview

This guide covers performance optimization techniques for custom sinks handling high-volume logging scenarios. Use these patterns when you need to process thousands of log events per second while maintaining system stability.

**This is Step 3 in the Sink Development Journey:**

1. [Learn the Fundamentals](sink-development.md)
2. [Production-Ready Development](sink-best-practices.md)
3. **Performance Optimization** (You are here)
4. [Debugging & Troubleshooting](sink-troubleshooting.md)

---

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

---

## Next Steps in Your Sink Development Journey

⚡ **Your sink is now optimized for high performance!**

**Complete the journey:**

1. **[Sink Troubleshooting Guide](sink-troubleshooting.md)** - Debug performance issues and other problems

**Or explore related topics:**

- **[Real-World Examples](../examples/sink_examples/)** - See performance patterns in action
- **[Advanced Development Overview](advanced-development.md)** - Explore other advanced topics

**Need help with performance issues?**

- **[Troubleshooting Guide](sink-troubleshooting.md)** - Performance problem diagnosis
- **[Community Performance Tips](https://github.com/chris-haste/fastapi-logger/discussions)** - Share optimization strategies

---

## Resources

- **[Advanced Development Overview](advanced-development.md)** - Complete journey overview
- **[Performance Examples](../examples/index.md#performance--monitoring)** - Real-world performance patterns
- **[Troubleshooting Guide](sink-troubleshooting.md)** - Debug performance issues
- **[Best Practices](sink-best-practices.md)** - Production-ready foundation
