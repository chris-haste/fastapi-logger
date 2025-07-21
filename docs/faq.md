# FAQ

Frequently Asked Questions about Fapilog.

Find quick answers to common questions about configuration, performance, integration, and production use.

---

## General Questions

### **Q: What is Fapilog?**

**A:** Fapilog is a modern, structured logging library designed specifically for FastAPI applications and Python services. It provides JSON-structured logging with automatic context enrichment, trace correlation, and production-ready features out of the box.

**Key Benefits:**

- ✅ **Zero Configuration** - Works out of the box with sensible defaults
- ✅ **Structured JSON Logging** - Machine-readable logs for observability
- ✅ **FastAPI Integration** - Automatic middleware and request correlation
- ✅ **Production Ready** - Async queue, multiple sinks, PII redaction
- ✅ **Developer Friendly** - Simple API that feels natural to Python developers

### **Q: How does Fapilog compare to standard Python logging?**

**A:** Fapilog is built on top of Python's standard logging but provides significant enhancements:

| Feature                 | Standard Logging      | Fapilog                        |
| ----------------------- | --------------------- | ------------------------------ |
| **Output Format**       | Text messages         | Structured JSON                |
| **Context**             | Manual enrichment     | Automatic request/user context |
| **Performance**         | Synchronous           | Async queue (non-blocking)     |
| **FastAPI Integration** | Manual setup          | Automatic middleware           |
| **Trace Correlation**   | Manual implementation | Built-in trace IDs             |
| **PII Protection**      | Manual implementation | Automatic redaction            |
| **Multiple Outputs**    | Complex setup         | Simple sink configuration      |

### **Q: Is Fapilog production-ready?**

**A:** Yes! Fapilog is designed for production use with:

- ✅ **Comprehensive Error Handling** - 7 custom exception classes with graceful degradation
- ✅ **Performance Optimized** - Async queue prevents blocking, handles 10K+ events/sec
- ✅ **Security Features** - Automatic PII redaction, configurable patterns
- ✅ **Monitoring Ready** - Built-in metrics and Prometheus integration
- ✅ **Container Support** - Multi-instance logging with proper isolation
- ✅ **Fault Tolerant** - Sink failures don't break the application

---

## Installation & Setup

### **Q: How do I install Fapilog?**

**A:** Basic installation:

```bash
pip install fapilog
```

For FastAPI applications with all features:

```bash
pip install fapilog[fastapi]
```

For specific features:

```bash
pip install fapilog[loki]      # Loki sink support
pip install fapilog[metrics]    # Metrics and monitoring
pip install fapilog[all]        # All optional features
```

### **Q: What are the minimum requirements?**

**A:**

- **Python:** 3.8+
- **Dependencies:** structlog, pydantic (included)
- **Optional:** httpx (for Loki), prometheus-client (for metrics), psutil (for resource metrics)

### **Q: How do I get started quickly?**

**A:** Minimal setup in 3 lines:

```python
from fapilog import configure_logging, log

configure_logging()  # Uses sensible defaults
log.info("Hello, Fapilog!", user_id="123", action="login")
```

**Output:**

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "info",
  "event": "Hello, Fapilog!",
  "hostname": "server-01",
  "pid": 12345,
  "user_id": "123",
  "action": "login"
}
```

---

## Configuration

### **Q: How do I configure Fapilog?**

**A:** Three ways to configure:

**1. Environment Variables (Recommended):**

```bash
export FAPILOG_LEVEL=INFO
export FAPILOG_FORMAT=json
export FAPILOG_SINKS=stdout,file
export FAPILOG_FILE_PATH=/var/log/app.log
```

**2. Programmatic Configuration:**

```python
from fapilog.settings import LoggingSettings

settings = LoggingSettings(
    level="INFO",
    format="json",
    sinks=["stdout", "file"],
    file_path="/var/log/app.log"
)
configure_logging(settings=settings)
```

**3. Mixed Approach:**

```python
# Environment variables as defaults, override programmatically
settings = LoggingSettings(
    level="DEBUG",  # Override FAPILOG_LEVEL
    queue_enabled=True  # Override FAPILOG_QUEUE_ENABLED
)
```

### **Q: What are the default settings?**

**A:** Sensible defaults for most applications:

```python
LoggingSettings(
    level="INFO",                    # Log level
    format="json",                   # Output format
    sinks=["stdout"],                # Output destinations
    queue_enabled=True,              # Async queue
    queue_size=1000,                 # Queue capacity
    enable_auto_redact_pii=True,     # PII protection
    enable_resource_metrics=False,    # Performance metrics
)
```

### **Q: How do I configure for different environments?**

**A:** Environment-specific configurations:

**Development:**

```python
dev_settings = LoggingSettings(
    level="DEBUG",
    format="pretty",  # Human-readable
    sinks=["stdout"],
    queue_enabled=False  # Synchronous for debugging
)
```

**Production:**

```python
prod_settings = LoggingSettings(
    level="INFO",
    format="json",
    sinks=["stdout", "file", "loki"],
    queue_enabled=True,
    queue_size=5000,
    enable_auto_redact_pii=True
)
```

**Testing:**

```python
test_settings = LoggingSettings(
    level="WARNING",
    sinks=["stdout"],
    queue_enabled=False,
    enable_auto_redact_pii=False
)
```

---

## FastAPI Integration

### **Q: How do I integrate Fapilog with FastAPI?**

**A:** Automatic integration with one line:

```python
from fastapi import FastAPI
from fapilog import configure_logging

app = FastAPI()
configure_logging(app=app)  # Automatic middleware and context
```

**What this provides:**

- ✅ Automatic trace ID generation
- ✅ Request timing and status codes
- ✅ User context enrichment
- ✅ Error correlation
- ✅ Response headers with trace IDs

### **Q: How do I add custom middleware?**

**A:** Fapilog's middleware works alongside custom middleware:

```python
from fastapi import FastAPI
from fapilog import configure_logging, TraceIDMiddleware

app = FastAPI()

# Add Fapilog middleware first
app.add_middleware(TraceIDMiddleware)

# Add your custom middleware
app.add_middleware(YourCustomMiddleware)

configure_logging(app=app)
```

### **Q: How do I get trace IDs in my logs?**

**A:** Trace IDs are automatically included in all logs:

```python
from fapilog import log, get_trace_id

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    log.info("User requested", user_id=user_id)

    # Trace ID is automatically included
    # {"trace_id": "req-abc123-def456", "user_id": 123}

    # Or access it directly
    trace_id = get_trace_id()
    return {"user_id": user_id, "trace_id": trace_id}
```

---

## Performance & Scalability

### **Q: Does Fapilog impact application performance?**

**A:** Fapilog is designed for high performance:

- ✅ **Non-blocking** - Async queue prevents blocking request handlers
- ✅ **Minimal overhead** - <1ms per log call
- ✅ **High throughput** - Handles 10K+ events/second
- ✅ **Configurable** - Tune for your specific needs

### **Q: How do I optimize for high-volume logging?**

**A:** Performance tuning strategies:

```python
# High-throughput configuration
settings = LoggingSettings(
    queue_enabled=True,
    queue_size=10000,        # Large queue for bursts
    queue_batch_size=100,    # Efficient batching
    queue_batch_timeout=0.1, # Frequent flushing
    queue_overflow="drop"    # Drop logs if queue full
)
```

**Environment variables:**

```bash
export FAPILOG_QUEUE_SIZE=10000
export FAPILOG_QUEUE_BATCH_SIZE=100
export FAPILOG_QUEUE_OVERFLOW=drop
```

### **Q: What happens when the queue is full?**

**A:** Configurable overflow strategies:

**Drop (Default):**

```python
settings = LoggingSettings(queue_overflow="drop")
# New logs are silently dropped when queue is full
```

**Block:**

```python
settings = LoggingSettings(queue_overflow="block")
# Application waits for queue space (guaranteed delivery)
```

**Sample:**

```python
settings = LoggingSettings(
    queue_overflow="sample",
    sampling_rate=0.1  # Keep 10% of logs
)
```

### **Q: How do I monitor logging performance?**

**A:** Built-in metrics and monitoring:

```python
from fapilog.monitoring import get_metrics_collector

metrics = get_metrics_collector()

# Queue metrics
print(f"Queue size: {metrics.get_queue_size()}")
print(f"Events per second: {metrics.get_events_per_second()}")

# Resource metrics
print(f"Memory usage: {metrics.get_memory_bytes()} bytes")
print(f"CPU usage: {metrics.get_cpu_percent()}%")
```

**Prometheus integration:**

```python
settings = LoggingSettings(
    metrics_enabled=True,
    metrics_prometheus_enabled=True,
    metrics_prometheus_port=8000
)
```

---

## Output & Sinks

### **Q: What output formats are supported?**

**A:** Multiple output formats:

**JSON (Production):**

```python
settings = LoggingSettings(format="json")
# {"timestamp": "...", "level": "info", "event": "..."}
```

**Pretty (Development):**

```python
settings = LoggingSettings(format="pretty")
# 2024-01-15 10:30:45 INFO Application started user_id=123
```

**Custom Format:**

```python
settings = LoggingSettings(format="custom")
# Define your own format
```

### **Q: What sinks are available?**

**A:** Multiple output destinations:

**Stdout (Default):**

```python
settings = LoggingSettings(sinks=["stdout"])
```

**File:**

```python
settings = LoggingSettings(
    sinks=["file"],
    file_path="/var/log/app.log"
)
```

**Loki:**

```python
settings = LoggingSettings(
    sinks=["loki"],
    loki_url="http://loki:3100"
)
```

**Multiple Sinks:**

```python
settings = LoggingSettings(
    sinks=["stdout", "file", "loki"]
)
```

### **Q: How do I create a custom sink?**

**A:** Implement the Sink interface:

```python
from fapilog.sinks import Sink

class MyCustomSink(Sink):
    async def write(self, event_dict: dict) -> None:
        # Your custom logic here
        print(f"Custom sink: {event_dict}")

# Register custom sink
settings = LoggingSettings(
    sinks=["stdout", "custom"],
    custom_sinks={"custom": MyCustomSink()}
)
```

---

## Security & Compliance

### **Q: How does PII redaction work?**

**A:** Automatic PII protection:

```python
# Automatic redaction enabled by default
log.info("User data",
         email="user@example.com",
         phone="+1-555-123-4567",
         card="1234-5678-9012-3456")

# Output: email="REDACTED", phone="REDACTED", card="REDACTED"
```

**Custom patterns:**

```python
settings = LoggingSettings(
    enable_auto_redact_pii=True,
    custom_pii_patterns=[
        r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',  # Credit cards
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'  # Emails
    ]
)
```

### **Q: How do I disable PII redaction?**

**A:** Disable for development or testing:

```python
settings = LoggingSettings(enable_auto_redact_pii=False)
```

**Or via environment:**

```bash
export FAPILOG_ENABLE_AUTO_REDACT_PII=false
```

### **Q: What sensitive data is automatically redacted?**

**A:** Built-in patterns include:

- **Email addresses** - `user@example.com`
- **Phone numbers** - `+1-555-123-4567`
- **Credit cards** - `1234-5678-9012-3456`
- **Social Security Numbers** - `123-45-6789`
- **IP addresses** - `192.168.1.100`
- **Passwords** - Fields named `password`, `passwd`, `secret`

---

## Error Handling

### **Q: What happens when logging fails?**

**A:** Graceful degradation and error handling:

**Sink Failures:**

- ✅ Other sinks continue to operate
- ✅ Errors are logged with context
- ✅ Application continues normally

**Queue Failures:**

- ✅ Falls back to synchronous logging
- ✅ Errors are logged with context
- ✅ Application continues normally

**Configuration Errors:**

- ✅ Clear error messages with suggestions
- ✅ Sensible defaults when possible
- ✅ Detailed context for debugging

### **Q: How do I handle logging errors?**

**A:** Custom exception classes for different scenarios:

```python
from fapilog.exceptions import (
    ConfigurationError, SinkError, QueueError,
    MiddlewareError, RedactionError
)

try:
    configure_logging(settings=invalid_settings)
except ConfigurationError as e:
    print(f"Configuration error: {e}")
    # Handle configuration issues
except SinkError as e:
    print(f"Sink error: {e}")
    # Handle sink failures
```

### **Q: How do I debug logging issues?**

**A:** Enable debug logging:

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

## Production Deployment

### **Q: How do I deploy to production?**

**A:** Production-ready configuration:

```python
# Production settings
settings = LoggingSettings(
    level="INFO",
    format="json",
    sinks=["stdout", "file", "loki"],
    file_path="/var/log/app.log",
    queue_enabled=True,
    queue_size=5000,
    enable_auto_redact_pii=True,
    enable_resource_metrics=True
)
```

**Environment variables:**

```bash
export FAPILOG_LEVEL=INFO
export FAPILOG_FORMAT=json
export FAPILOG_SINKS=stdout,file,loki
export FAPILOG_FILE_PATH=/var/log/app.log
export FAPILOG_QUEUE_ENABLED=true
export FAPILOG_QUEUE_SIZE=5000
export FAPILOG_ENABLE_AUTO_REDACT_PII=true
```

### **Q: How do I configure for containers?**

**A:** Container-optimized setup:

```python
# Container settings
settings = LoggingSettings(
    sinks=["stdout"],  # Log to stdout for container logs
    format="json",     # Structured for log aggregation
    level="INFO",
    queue_enabled=True,
    queue_size=1000
)
```

**Dockerfile example:**

```dockerfile
FROM python:3.11

# Create log directory
RUN mkdir -p /var/log && chmod 755 /var/log

# Set environment variables
ENV FAPILOG_LEVEL=INFO
ENV FAPILOG_FORMAT=json
ENV FAPILOG_SINKS=stdout

# Your application code
COPY . /app
WORKDIR /app
```

### **Q: How do I integrate with monitoring systems?**

**A:** Multiple monitoring integrations:

**Prometheus Metrics:**

```python
settings = LoggingSettings(
    metrics_enabled=True,
    metrics_prometheus_enabled=True,
    metrics_prometheus_port=8000
)
```

**Loki Integration:**

```python
settings = LoggingSettings(
    sinks=["loki"],
    loki_url="http://loki:3100",
    loki_batch_size=100,
    loki_timeout=30
)
```

**Custom Monitoring:**

```python
from fapilog.monitoring import get_metrics_collector

metrics = get_metrics_collector()

# Send metrics to your monitoring system
def send_metrics():
    queue_size = metrics.get_queue_size()
    events_per_sec = metrics.get_events_per_second()
    # Send to your monitoring system
```

---

## Troubleshooting

### **Q: Logs not appearing in console?**

**A:** Check configuration:

```python
# Verify sinks include stdout
settings = LoggingSettings(sinks=["stdout"])

# Check log level
settings = LoggingSettings(level="INFO")  # Not DEBUG

# Test configuration
log.info("Test message")
```

### **Q: Performance issues with high log volume?**

**A:** Optimize queue settings:

```python
# High-performance configuration
settings = LoggingSettings(
    queue_enabled=True,
    queue_size=10000,
    queue_batch_size=100,
    queue_batch_timeout=0.1,
    queue_overflow="drop"
)
```

### **Q: FastAPI middleware not working?**

**A:** Ensure proper setup:

```python
from fastapi import FastAPI
from fapilog import configure_logging

app = FastAPI()
configure_logging(app=app)  # This registers middleware

# Or manually add middleware
from fapilog import TraceIDMiddleware
app.add_middleware(TraceIDMiddleware)
```

### **Q: Custom enrichers not working?**

**A:** Register before configuration:

```python
from fapilog.enrichers import register_enricher

def my_enricher(event_dict):
    event_dict["custom_field"] = "value"
    return event_dict

register_enricher(my_enricher)
configure_logging()  # Register after enrichers
```

---

## Migration & Compatibility

### **Q: How do I migrate from standard logging?**

**A:** Gradual migration path:

**Step 1: Install Fapilog**

```bash
pip install fapilog
```

**Step 2: Replace logging calls**

```python
# Before
import logging
logger = logging.getLogger(__name__)
logger.info("User logged in", extra={"user_id": "123"})

# After
from fapilog import log
log.info("User logged in", user_id="123")
```

**Step 3: Configure for your environment**

```python
from fapilog import configure_logging
configure_logging()  # Uses sensible defaults
```

### **Q: Is Fapilog compatible with existing logging?**

**A:** Yes, Fapilog can coexist with standard logging:

```python
import logging
from fapilog import configure_logging, log

# Configure both
configure_logging()
logging.basicConfig(level=logging.INFO)

# Use either
log.info("Fapilog message", user_id="123")
logging.getLogger(__name__).info("Standard logging message")
```

### **Q: Can I use Fapilog with other logging libraries?**

**A:** Fapilog is designed to work alongside other libraries:

- ✅ **structlog** - Fapilog is built on structlog
- ✅ **loguru** - Can coexist in the same application
- ✅ **Custom logging** - No conflicts with existing logging

---

## Advanced Features

### **Q: How do I add custom context?**

**A:** Multiple ways to add context:

**User Context:**

```python
from fapilog import set_user_context

set_user_context(user_id="123", session_id="abc")
log.info("User action")  # Includes user context
```

**Request Context:**

```python
from fapilog import bind_context

bind_context(request_id="xyz", endpoint="/api/users")
log.info("Request processed")  # Includes request context
```

**Custom Enrichers:**

```python
from fapilog.enrichers import register_enricher

def add_environment(event_dict):
    event_dict["environment"] = os.getenv("ENVIRONMENT", "development")
    return event_dict

register_enricher(add_environment)
```

### **Q: How do I implement log sampling?**

**A:** Built-in sampling support:

```python
settings = LoggingSettings(
    sampling_rate=0.1,  # Sample 10% of logs
    sampling_levels=["debug", "info"]  # Only sample these levels
)
```

**Custom sampling:**

```python
from fapilog import should_sample

if should_sample(0.1):  # 10% sampling
    log.info("Sampled log message")
```

### **Q: How do I implement log filtering?**

**A:** Custom processors for filtering:

```python
from fapilog import register_processor

def filter_sensitive_logs(event_dict):
    if "password" in event_dict:
        return None  # Drop this log
    return event_dict

register_processor(filter_sensitive_logs)
```

---

## Support & Community

### **Q: Where can I get help?**

**A:** Multiple support channels:

- 📚 **Documentation**: [User Guide](user-guide.md), [API Reference](api-reference.md)
- 🐛 **Issues**: [GitHub Issues](https://github.com/chris-haste/fastapi-logger/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/chris-haste/fastapi-logger/discussions)
- 📖 **Examples**: [Examples & Recipes](examples/index.md)
- 🔧 **Troubleshooting**: [Troubleshooting Guide](troubleshooting.md)

### **Q: How do I contribute?**

**A:** Welcome contributions:

- 🐛 **Report bugs** - Use GitHub Issues
- 💡 **Suggest features** - Use GitHub Discussions
- 📝 **Improve docs** - Submit pull requests
- 🔧 **Fix issues** - Submit pull requests
- ⭐ **Star the repo** - Show your support

### **Q: Is Fapilog actively maintained?**

**A:** Yes, Fapilog is actively developed with:

- ✅ **Regular releases** - New features and bug fixes
- ✅ **Comprehensive testing** - 90%+ test coverage
- ✅ **Documentation updates** - Kept current with features
- ✅ **Community feedback** - Issues and discussions addressed
- ✅ **Performance monitoring** - Continuous optimization

---

## Performance Benchmarks

### **Q: What performance can I expect?**

**A:** Typical performance characteristics:

**Throughput:**

- ✅ **10,000+ events/second** - Async queue processing
- ✅ **<1ms overhead** - Per log call
- ✅ **Non-blocking** - Never blocks request handlers

**Memory Usage:**

- ✅ **<10MB additional** - For typical applications
- ✅ **Configurable queue** - Prevent unbounded growth
- ✅ **Efficient batching** - Reduce memory overhead

**CPU Usage:**

- ✅ **<5% additional** - For typical applications
- ✅ **Async processing** - Minimal CPU impact
- ✅ **Optimized serialization** - Fast JSON encoding

### **Q: How do I benchmark my setup?**

**A:** Use the built-in performance testing:

```python
# examples/11_performance_testing.py
import time
from fapilog import configure_logging, log

configure_logging()

# Benchmark logging performance
start = time.perf_counter()
for i in range(10000):
    log.info("Performance test", event_number=i)
duration = time.perf_counter() - start

print(f"Throughput: {10000 / duration:.1f} events/sec")
```

---

## Security Considerations

### **Q: Is Fapilog secure for production?**

**A:** Yes, with built-in security features:

- ✅ **PII Redaction** - Automatic sensitive data protection
- ✅ **Configurable Patterns** - Custom redaction rules
- ✅ **No Sensitive Data** - Passwords, tokens filtered from logs
- ✅ **Container Support** - Proper isolation in containers
- ✅ **Audit Trails** - Comprehensive logging for compliance

### **Q: How do I handle sensitive data?**

**A:** Multiple protection layers:

**Automatic Redaction:**

```python
# Sensitive data automatically redacted
log.info("User data",
         password="secret123",  # → "REDACTED"
         token="abc123",        # → "REDACTED"
         email="user@example.com")  # → "REDACTED"
```

**Custom Patterns:**

```python
settings = LoggingSettings(
    custom_pii_patterns=[
        r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',  # Credit cards
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'  # Emails
    ]
)
```

**Manual Filtering:**

```python
# Filter sensitive data before logging
def log_user_data(user_data):
    safe_data = {k: v for k, v in user_data.items()
                 if k not in ["password", "token"]}
    log.info("User data", **safe_data)
```

---

## Integration Examples

### **Q: How do I integrate with Datadog?**

**A:** Use stdout sink with Datadog agent:

```python
settings = LoggingSettings(
    sinks=["stdout"],
    format="json"
)

# Datadog agent will collect logs from stdout
# Configure in datadog.yml:
# logs:
#   - type: file
#     path: /var/log/app.log
#     service: my-app
```

### **Q: How do I integrate with ELK Stack?**

**A:** Use file sink with Logstash:

```python
settings = LoggingSettings(
    sinks=["file"],
    file_path="/var/log/app.json"
)

# Logstash configuration:
# input {
#   file {
#     path => "/var/log/app.json"
#     codec => json
#   }
# }
```

### **Q: How do I integrate with Grafana Loki?**

**A:** Direct Loki integration:

```python
settings = LoggingSettings(
    sinks=["loki"],
    loki_url="http://loki:3100",
    loki_batch_size=100,
    loki_timeout=30
)
```

---

## Best Practices

### **Q: What are the best practices for logging?**

**A:** Recommended practices:

**Structured Logging:**

```python
# ✅ Good - Structured data
log.info("User logged in", user_id="123", ip="192.168.1.100")

# ❌ Avoid - String concatenation
log.info(f"User {user_id} logged in from {ip}")
```

**Appropriate Log Levels:**

```python
log.debug("Detailed debug info")    # Development only
log.info("Normal application flow")  # Production monitoring
log.warning("Unexpected but handled") # Requires attention
log.error("Error that needs fixing")  # Requires action
log.critical("Application failure")    # Immediate action required
```

**Context Enrichment:**

```python
# Add relevant context to all logs
log.info("Database query",
         table="users",
         operation="select",
         duration_ms=45.2,
         rows_returned=10)
```

**Error Handling:**

```python
try:
    result = risky_operation()
    log.info("Operation successful", result_type=type(result).__name__)
except Exception as e:
    log.error("Operation failed",
              error=str(e),
              error_type=type(e).__name__,
              operation="risky_operation")
    raise
```

### **Q: How do I optimize for different environments?**

**A:** Environment-specific configurations:

**Development:**

```python
settings = LoggingSettings(
    level="DEBUG",
    format="pretty",  # Human-readable
    sinks=["stdout"],
    queue_enabled=False  # Synchronous for debugging
)
```

**Staging:**

```python
settings = LoggingSettings(
    level="INFO",
    format="json",
    sinks=["stdout", "file"],
    queue_enabled=True,
    enable_auto_redact_pii=True
)
```

**Production:**

```python
settings = LoggingSettings(
    level="INFO",
    format="json",
    sinks=["stdout", "file", "loki"],
    queue_enabled=True,
    queue_size=5000,
    enable_auto_redact_pii=True,
    enable_resource_metrics=True
)
```

---

## Still Have Questions?

If you couldn't find the answer here:

- 📚 **Check the [User Guide](user-guide.md)** for detailed tutorials
- 🔧 **Review the [Troubleshooting Guide](troubleshooting.md)** for common issues
- 📖 **Explore [Examples & Recipes](examples/index.md)** for real-world patterns
- 🐛 **Report issues** on [GitHub Issues](https://github.com/chris-haste/fastapi-logger/issues)
- 💬 **Ask the community** on [GitHub Discussions](https://github.com/chris-haste/fastapi-logger/discussions)
