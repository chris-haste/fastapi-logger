# Sink Best Practices

**Part of the [Advanced Development](advanced-development.md) journey - Production-ready patterns and error handling**

> 📚 **Previous Step:** [Sink Development Guide](sink-development.md) - Learn the fundamentals first

---

## Overview

This guide covers essential best practices for building production-ready custom sinks. After learning the basics in the [Sink Development Guide](sink-development.md), these patterns ensure your sinks are reliable, secure, and maintainable.

**This is Step 2 in the Sink Development Journey:**

1. [Learn the Fundamentals](sink-development.md)
2. **Production-Ready Development** (You are here)
3. [Performance Optimization](sink-performance.md)
4. [Debugging & Troubleshooting](sink-troubleshooting.md)

---

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

---

## Next Steps in Your Sink Development Journey

🎯 **Your sink is now production-ready!**

**What's next?**

1. **[Sink Performance Guide](sink-performance.md)** - Optimize for high-throughput scenarios
2. **[Sink Troubleshooting Guide](sink-troubleshooting.md)** - Debug issues when they arise
3. **[Real-World Examples](../examples/sink_examples/)** - Study advanced implementations

**Or go back to:**

- **[Advanced Development Overview](advanced-development.md)** - Explore other advanced topics
- **[Sink Development Guide](sink-development.md)** - Review the fundamentals

---

## Resources

- **[Advanced Development Overview](advanced-development.md)** - Complete journey overview
- **[Real-World Examples](../examples/sink_examples/)** - See these practices in action
- **[Performance Guide](sink-performance.md)** - Next step for optimization
- **[Community Best Practices](https://github.com/chris-haste/fastapi-logger/discussions)** - Share your patterns
