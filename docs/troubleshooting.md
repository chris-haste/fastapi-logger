# Troubleshooting

Find solutions to common issues, performance problems, and integration challenges with Fapilog.

## Quick Diagnosis

### 🔍 **Check Your Configuration**

```python
from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings

# Test basic configuration
try:
    configure_logging()
    log.info("Configuration test successful")
except Exception as e:
    print(f"Configuration error: {e}")
```

### 🔍 **Enable Debug Mode**

```python
import logging
logging.getLogger("fapilog").setLevel(logging.DEBUG)

# Test all components
log.debug("Debug test")
log.info("Info test")
log.warning("Warning test")
log.error("Error test")
```

---

## Common Issues

### 🚨 **Configuration Errors**

#### **Invalid Log Level**

**Error:** `ConfigurationError: Invalid log level 'INVALID'`

**Cause:** Invalid log level specified in configuration

**Solutions:**

```python
# ✅ Correct
settings = LoggingSettings(level="DEBUG")  # or INFO, WARN, ERROR, CRITICAL
configure_logging(settings=settings)

# ✅ Environment variable
export FAPILOG_LEVEL=DEBUG

# ❌ Incorrect
settings = LoggingSettings(level="INVALID")
```

**Valid Log Levels:** `DEBUG`, `INFO`, `WARN`, `ERROR`, `CRITICAL`

#### **Missing Dependencies**

**Error:** `ConfigurationError: httpx is required for LokiSink`

**Cause:** Optional dependencies not installed

**Solutions:**

```bash
# Install optional dependencies
pip install fapilog[loki]  # For Loki sink
pip install fapilog[metrics]  # For metrics
pip install fapilog[all]  # For all features
```

**Required Dependencies by Feature:**

- **Loki Sink**: `httpx`
- **Metrics**: `prometheus-client`, `psutil`
- **File Sink**: Built-in (no extra dependencies)

#### **Invalid Sink Configuration**

**Error:** `ConfigurationError: Invalid sink type 'invalid_sink'`

**Cause:** Unsupported sink type specified

**Solutions:**

```python
# ✅ Correct sink types
settings = LoggingSettings(sinks=["stdout", "file", "loki"])

# ❌ Incorrect
settings = LoggingSettings(sinks=["invalid_sink"])
```

**Valid Sink Types:** `stdout`, `file`, `loki`, `custom`

### 🚨 **Sink Errors**

#### **File Sink Permission Denied**

**Error:** `SinkError: Failed to write to log file`

**Cause:** Insufficient permissions or directory doesn't exist

**Solutions:**

```python
# ✅ Ensure directory exists and is writable
import os
os.makedirs("/var/log", exist_ok=True)

# ✅ Use relative path
settings = LoggingSettings(
    sinks=["file"],
    file_sink_path="./logs/app.log"
)

# ✅ Check permissions
import os
if os.access("/var/log", os.W_OK):
    print("Directory is writable")
```

#### **Loki Sink Connection Failed**

**Error:** `SinkError: HTTP request failed (status_code=500)`

**Cause:** Loki server unavailable or misconfigured

**Solutions:**

```python
# ✅ Check Loki connectivity
import httpx
try:
    response = httpx.get("http://loki:3100/ready")
    print(f"Loki status: {response.status_code}")
except Exception as e:
    print(f"Loki connection failed: {e}")

# ✅ Configure retry settings
settings = LoggingSettings(
    sinks=["loki"],
    loki_sink_url="http://loki:3100",
    loki_sink_timeout=30,
    loki_sink_retry_attempts=3
)
```

#### **Custom Sink Implementation Error**

**Error:** `SinkError: Custom sink write failed`

**Cause:** Custom sink implementation issues

**Solutions:**

```python
# ✅ Proper custom sink implementation
from fapilog.sinks import Sink

class MyCustomSink(Sink):
    async def write(self, event_dict: dict) -> None:
        try:
            # Your sink logic here
            print(f"Custom sink: {event_dict}")
        except Exception as e:
            # Proper error handling
            raise SinkError(f"Custom sink failed: {e}", "custom", {}, "write")
```

### 🚨 **Queue Errors**

#### **Queue Full**

**Error:** `QueueError: Queue is full (queue_size=1000, max_size=1000)`

**Cause:** High log volume exceeding queue capacity

**Solutions:**

```python
# ✅ Increase queue size
settings = LoggingSettings(
    queue_enabled=True,
    queue_maxsize=5000,  # Increase from default 1000
    queue_overflow="drop"  # or "block", "drop_oldest"
)

# ✅ Monitor queue metrics
from fapilog.monitoring import get_metrics_collector
metrics = get_metrics_collector()
print(f"Queue size: {metrics.get_queue_size()}")
```

#### **Queue Worker Shutdown Error**

**Error:** `QueueError: Worker shutdown failed`

**Cause:** Queue worker not properly shutting down

**Solutions:**

```python
# ✅ Proper application shutdown
import asyncio
from fapilog import shutdown_logging

async def main():
    # Your application code
    pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        # Ensure proper shutdown
        shutdown_logging()
```

### 🚨 **Middleware Errors**

#### **Context Binding Error**

**Error:** `MiddlewareError: Failed to bind context`

**Cause:** Invalid context key or value

**Solutions:**

```python
# ✅ Proper context usage
from fapilog import set_user_context, bind_context

# Use string keys
set_user_context(user_id="123", session_id="abc")

# Bind context with valid keys
bind_context(request_id="xyz", endpoint="/api/users")
```

#### **Trace Propagation Error**

**Error:** `MiddlewareError: Trace propagation failed`

**Cause:** Invalid trace headers or middleware configuration

**Solutions:**

```python
# ✅ Proper middleware setup
from fastapi import FastAPI
from fapilog import configure_logging, TraceIDMiddleware

app = FastAPI()
app.add_middleware(TraceIDMiddleware)
configure_logging(app=app)

# ✅ Custom trace headers
app.add_middleware(TraceIDMiddleware, header_name="X-Custom-Trace-ID")
```

### 🚨 **Redaction Errors**

#### **Invalid Regex Pattern**

**Error:** `RedactionError: Invalid regex pattern '[invalid'`

**Cause:** Malformed regex pattern in PII redaction

**Solutions:**

```python
# ✅ Valid regex patterns
settings = LoggingSettings(
    enable_auto_redact_pii=True,
    custom_pii_patterns=[
        r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',  # Credit card
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'  # Email
    ]
)

# ✅ Test patterns
import re
try:
    re.compile(r'your_pattern_here')
    print("Pattern is valid")
except re.error as e:
    print(f"Invalid pattern: {e}")
```

#### **Field Redaction Error**

**Error:** `RedactionError: Failed to redact field 'user.password'`

**Cause:** Invalid field path or nested structure

**Solutions:**

```python
# ✅ Proper field redaction
from fapilog import redact_field

# Simple field
log.info("User data", user_id="123", password="secret")  # Auto-redacted

# Nested field
log.info("Complex data", user={"id": "123", "password": "secret"})  # Auto-redacted

# Manual redaction
redact_field("user.password", {"user": {"password": "secret"}})
```

### 🚨 **Performance Issues**

#### **High Memory Usage**

**Symptoms:** Memory usage growing over time

**Solutions:**

```python
# ✅ Monitor memory usage
from fapilog.monitoring import get_metrics_collector
metrics = get_metrics_collector()

print(f"Memory usage: {metrics.get_memory_bytes()} bytes")
print(f"CPU usage: {metrics.get_cpu_percent()}%")

# ✅ Optimize queue settings
settings = LoggingSettings(
    queue_enabled=True,
    queue_maxsize=1000,  # Reduce if memory is high
    queue_batch_size=10,  # Smaller batches
    queue_overflow="drop"  # Drop logs if queue is full
)
```

#### **Slow Logging Performance**

**Symptoms:** Logging operations taking too long

**Solutions:**

```python
# ✅ Enable async queue
settings = LoggingSettings(
    queue_enabled=True,
    queue_maxsize=2000,
    queue_workers=2  # Multiple workers
)

# ✅ Use appropriate log levels
settings = LoggingSettings(level="INFO")  # Avoid DEBUG in production

# ✅ Optimize sink configuration
settings = LoggingSettings(
    sinks=["stdout"],  # Fastest sink
    # Avoid file sink for high-volume logging
)
```

---

## Debugging Techniques

### 🔍 **Enable Verbose Logging**

```python
import logging

# Enable debug logging for fapilog
logging.getLogger("fapilog").setLevel(logging.DEBUG)

# Enable debug for specific modules
logging.getLogger("fapilog._internal.queue").setLevel(logging.DEBUG)
logging.getLogger("fapilog.sinks.loki").setLevel(logging.DEBUG)
```

### 🔍 **Test Individual Components**

```python
# Test configuration
from fapilog.settings import LoggingSettings
settings = LoggingSettings()
print(f"Settings: {settings}")

# Test sinks individually
from fapilog.sinks.stdout import StdoutSink
sink = StdoutSink()
await sink.write({"test": "message"})

# Test queue
from fapilog._internal.queue import QueueWorker
worker = QueueWorker(sinks=[sink])
await worker._process_event({"test": "event"})
```

### 🔍 **Monitor Metrics**

```python
from fapilog.monitoring import get_metrics_collector

metrics = get_metrics_collector()

# Check queue status
print(f"Queue size: {metrics.get_queue_size()}")
print(f"Events per second: {metrics.get_events_per_second()}")

# Check memory usage
print(f"Memory: {metrics.get_memory_bytes()} bytes")
print(f"CPU: {metrics.get_cpu_percent()}%")
```

### 🔍 **Trace Request Flow**

```python
# Enable trace logging
import logging
logging.getLogger("fapilog.middleware").setLevel(logging.DEBUG)

# Check trace headers
from fapilog import get_trace_id, get_span_id
print(f"Trace ID: {get_trace_id()}")
print(f"Span ID: {get_span_id()}")
```

---

## Production Issues

### 🚨 **Memory Leaks**

**Symptoms:** Memory usage continuously increasing

**Diagnosis:**

```python
# Monitor memory over time
import time
from fapilog.monitoring import get_metrics_collector

metrics = get_metrics_collector()
for i in range(10):
    print(f"Memory: {metrics.get_memory_bytes()} bytes")
    time.sleep(1)
```

**Solutions:**

- Reduce queue size
- Enable queue overflow to "drop"
- Check for circular references in custom sinks
- Ensure proper cleanup in custom enrichers

### 🚨 **High CPU Usage**

**Symptoms:** CPU usage spikes during logging

**Diagnosis:**

```python
# Monitor CPU usage
from fapilog.monitoring import get_metrics_collector
metrics = get_metrics_collector()
print(f"CPU: {metrics.get_cpu_percent()}%")
```

**Solutions:**

- Use async queue with multiple workers
- Optimize custom enrichers
- Reduce log volume or level
- Use faster sinks (stdout vs file)

### 🚨 **Network Issues (Loki)**

**Symptoms:** Logs not reaching Loki

**Diagnosis:**

```python
# Test Loki connectivity
import httpx
try:
    response = httpx.get("http://loki:3100/ready", timeout=5)
    print(f"Loki status: {response.status_code}")
except Exception as e:
    print(f"Loki connection failed: {e}")
```

**Solutions:**

- Check network connectivity
- Verify Loki configuration
- Increase timeout settings
- Enable retry with backoff

### 🚨 **File System Issues**

**Symptoms:** File sink errors or missing logs

**Diagnosis:**

```python
# Check file system
import os
log_path = "/var/log/app.log"
print(f"Directory exists: {os.path.exists(os.path.dirname(log_path))}")
print(f"Directory writable: {os.access(os.path.dirname(log_path), os.W_OK)}")
print(f"File exists: {os.path.exists(log_path)}")
```

**Solutions:**

- Ensure directory exists and is writable
- Check disk space
- Verify file permissions
- Use absolute paths

---

## Integration Issues

### 🚨 **FastAPI Integration Problems**

#### **Middleware Not Working**

**Symptoms:** No trace IDs or request context

**Solutions:**

```python
# ✅ Proper FastAPI setup
from fastapi import FastAPI
from fapilog import configure_logging, TraceIDMiddleware

app = FastAPI()

# Add middleware BEFORE configure_logging
app.add_middleware(TraceIDMiddleware)
configure_logging(app=app)

# ✅ Custom middleware configuration
app.add_middleware(
    TraceIDMiddleware,
    header_name="X-Custom-Trace-ID",
    include_response_headers=True
)
```

#### **Exception Handler Not Logging**

**Symptoms:** Errors not being logged

**Solutions:**

```python
# ✅ Global exception handler
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fapilog import log

app = FastAPI()

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.error(
        "Unhandled exception",
        endpoint=str(request.url.path),
        method=request.method,
        error=str(exc),
        error_type=type(exc).__name__
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
```

### 🚨 **Docker/Container Issues**

#### **Logs Not Appearing in Container**

**Symptoms:** No logs in container stdout

**Solutions:**

```python
# ✅ Ensure stdout sink is enabled
settings = LoggingSettings(sinks=["stdout"])

# ✅ Configure for container environment
settings = LoggingSettings(
    sinks=["stdout"],
    console_format="json",  # Structured logging
    level="INFO"
)
```

#### **File Permissions in Container**

**Symptoms:** File sink permission errors

**Solutions:**

```dockerfile
# ✅ Dockerfile with proper permissions
FROM python:3.11

# Create log directory with proper permissions
RUN mkdir -p /var/log && chmod 755 /var/log

# Set user permissions
USER 1000:1000

# Your application code
COPY . /app
WORKDIR /app
```

### 🚨 **Kubernetes Integration**

#### **Logs Not in Kubernetes Logs**

**Symptoms:** Application logs not visible in `kubectl logs`

**Solutions:**

```python
# ✅ Ensure stdout logging
settings = LoggingSettings(
    sinks=["stdout"],
    console_format="json"
)

# ✅ Add Kubernetes metadata
from fapilog import bind_context
bind_context(
    pod_name=os.getenv("POD_NAME"),
    namespace=os.getenv("NAMESPACE"),
    container_name=os.getenv("CONTAINER_NAME")
)
```

---

## Performance Optimization

### ⚡ **Queue Optimization**

```python
# ✅ Optimal queue settings for high volume
settings = LoggingSettings(
    queue_enabled=True,
    queue_maxsize=5000,  # Large queue for bursts
    queue_workers=4,     # Multiple workers
    queue_batch_size=50, # Larger batches
    queue_overflow="drop"  # Drop on overflow
)
```

### ⚡ **Sink Optimization**

```python
# ✅ Fastest sink configuration
settings = LoggingSettings(
    sinks=["stdout"],  # Fastest sink
    console_format="json",  # Structured output
    level="INFO"  # Avoid DEBUG in production
)

# ✅ File sink optimization
settings = LoggingSettings(
    sinks=["file"],
    file_sink_path="/tmp/app.log",  # Use tmpfs for speed
    file_sink_buffering=0  # Unbuffered for immediate flush
)
```

### ⚡ **Custom Enricher Optimization**

```python
# ✅ Efficient custom enricher
from fapilog.enrichers import register_enricher

def fast_enricher(event_dict: dict) -> dict:
    # Cache expensive operations
    if not hasattr(fast_enricher, '_cached_hostname'):
        fast_enricher._cached_hostname = os.getenv('HOSTNAME', 'unknown')

    event_dict['hostname'] = fast_enricher._cached_hostname
    return event_dict

register_enricher(fast_enricher)
```

---

## Getting Help

### 📚 **Documentation Resources**

- **[API Reference](api-reference.md)** - Complete technical documentation
- **[Examples](examples/index.md)** - Real-world usage patterns
- **[Configuration](config.md)** - Environment and settings guide
- **[User Guide](user-guide.md)** - Step-by-step tutorials

### 🐛 **Debugging Checklist**

- [ ] Enable debug logging
- [ ] Check configuration settings
- [ ] Verify dependencies are installed
- [ ] Test individual components
- [ ] Monitor metrics and performance
- [ ] Check file permissions and network connectivity
- [ ] Review custom implementations

### 📞 **Support Channels**

- **GitHub Issues**: Report bugs and feature requests
- **Documentation**: Check the troubleshooting sections
- **Examples**: Review the `examples/` directory
- **Community**: Join discussions on GitHub

---

## Error Reference

### **Configuration Errors**

| Error                                   | Cause                   | Solution                                 |
| --------------------------------------- | ----------------------- | ---------------------------------------- |
| `ConfigurationError: Invalid log level` | Invalid level specified | Use DEBUG, INFO, WARN, ERROR, CRITICAL   |
| `ConfigurationError: httpx is required` | Missing dependency      | Install with `pip install fapilog[loki]` |
| `ConfigurationError: Invalid sink type` | Unsupported sink        | Use stdout, file, loki, or custom        |

### **Sink Errors**

| Error                                    | Cause                | Solution                                  |
| ---------------------------------------- | -------------------- | ----------------------------------------- |
| `SinkError: Failed to write to log file` | Permission denied    | Check file permissions and directory      |
| `SinkError: HTTP request failed`         | Network issue        | Check Loki connectivity and configuration |
| `SinkError: Custom sink write failed`    | Implementation error | Review custom sink code                   |

### **Queue Errors**

| Error                                | Cause         | Solution                                       |
| ------------------------------------ | ------------- | ---------------------------------------------- |
| `QueueError: Queue is full`          | High volume   | Increase queue size or use overflow strategies |
| `QueueError: Worker shutdown failed` | Cleanup issue | Ensure proper application shutdown             |

### **Middleware Errors**

| Error                                       | Cause           | Solution                         |
| ------------------------------------------- | --------------- | -------------------------------- |
| `MiddlewareError: Failed to bind context`   | Invalid context | Use string keys and valid values |
| `MiddlewareError: Trace propagation failed` | Header issue    | Check middleware configuration   |

### **Redaction Errors**

| Error                                    | Cause              | Solution                               |
| ---------------------------------------- | ------------------ | -------------------------------------- |
| `RedactionError: Invalid regex pattern`  | Malformed regex    | Test and fix regex patterns            |
| `RedactionError: Failed to redact field` | Invalid field path | Check nested structure and field names |
