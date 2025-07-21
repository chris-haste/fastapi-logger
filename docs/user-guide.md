# User Guide

**New to Fapilog? Start with the [Quickstart Tutorial](quickstart.md) for a hands-on, step-by-step introduction!**

This guide provides step-by-step tutorials for using `fapilog` in your applications. It's designed to take you from basic setup to advanced features, with practical examples throughout.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Basic Configuration](#basic-configuration)
- [FastAPI Integration](#fastapi-integration)
- [User Context Enrichment](#user-context-enrichment)
- [Advanced Configuration](#advanced-configuration)
- [Custom Enrichers](#custom-enrichers)
- [Container Architecture](#container-architecture)
- [Custom Sinks](#custom-sinks)
- [Performance Tuning](#performance-tuning)
- [Production Deployment](#production-deployment)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

Get up and running with `fapilog` in under 5 minutes.

### Installation

```bash
pip install fapilog
```

### Basic Setup

The simplest way to get started:

```python
from fapilog import configure_logging, log

# Configure logging with defaults
configure_logging()

# Start logging
log.info("Application started", version="1.0.0")
log.warning("Deprecated feature used", feature="old_api")
log.error("Database connection failed", database="postgres")
```

**What happens:**

- ✅ Structured JSON logging enabled
- ✅ Automatic timestamp and log level
- ✅ Hostname and process ID added
- ✅ Pretty console output in development
- ✅ Async-safe logging with background queue

### Your First Log

```python
from fapilog import configure_logging, log

configure_logging()

# Basic logging
log.info("User logged in", user_id="123", action="login")

# Structured logging with multiple fields
log.info(
    "API request processed",
    endpoint="/api/users",
    method="GET",
    status_code=200,
    duration_ms=45.2,
    user_id="123"
)
```

**Output:**

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "info",
  "event": "User logged in",
  "hostname": "server-01",
  "pid": 12345,
  "user_id": "123",
  "action": "login"
}
```

---

## Basic Configuration

Learn how to configure `fapilog` for different environments and use cases.

### Environment-Based Configuration

`fapilog` uses environment variables for easy configuration:

```bash
# Development
export FAPILOG_LEVEL=DEBUG
export FAPILOG_JSON_CONSOLE=pretty
export FAPILOG_QUEUE_ENABLED=false

# Production
export FAPILOG_LEVEL=INFO
export FAPILOG_JSON_CONSOLE=json
export FAPILOG_QUEUE_ENABLED=true
export FAPILOG_ENABLE_RESOURCE_METRICS=true
```

### Programmatic Configuration

Use `LoggingSettings` for programmatic control:

```python
from fapilog import configure_logging
from fapilog.settings import LoggingSettings

# Development settings
dev_settings = LoggingSettings(
    level="DEBUG",
    json_console="pretty",
    queue_enabled=False,
    enable_resource_metrics=False
)

# Production settings
prod_settings = LoggingSettings(
    level="INFO",
    json_console="json",
    queue_enabled=True,
    queue_maxsize=1000,
    enable_resource_metrics=True
)

configure_logging(settings=dev_settings)
```

### Configuration Options

| Setting          | Environment Variable              | Default | Description                        |
| ---------------- | --------------------------------- | ------- | ---------------------------------- |
| Log Level        | `FAPILOG_LEVEL`                   | `INFO`  | DEBUG, INFO, WARN, ERROR, CRITICAL |
| Console Format   | `FAPILOG_JSON_CONSOLE`            | `auto`  | auto, json, pretty                 |
| Queue Enabled    | `FAPILOG_QUEUE_ENABLED`           | `true`  | Enable async queue                 |
| Queue Size       | `FAPILOG_QUEUE_MAXSIZE`           | `1000`  | Maximum queue size                 |
| Resource Metrics | `FAPILOG_ENABLE_RESOURCE_METRICS` | `false` | Memory/CPU metrics                 |
| Sampling Rate    | `FAPILOG_SAMPLING_RATE`           | `1.0`   | Log sampling (0.0-1.0)             |

### Development vs Production

**Development Configuration:**

```python
settings = LoggingSettings(
    level="DEBUG",
    json_console="pretty",  # Human-readable output
    queue_enabled=False,    # Simpler setup
    enable_resource_metrics=False  # Better performance
)
```

**Production Configuration:**

```python
settings = LoggingSettings(
    level="INFO",
    json_console="json",    # Structured for log aggregation
    queue_enabled=True,     # Non-blocking logging
    queue_maxsize=2000,     # Larger queue for high load
    enable_resource_metrics=True,  # Monitor resources
    sampling_rate=1.0       # Log everything
)
```

---

## FastAPI Integration

`fapilog` provides seamless integration with FastAPI through automatic middleware registration and request context enrichment.

### Automatic Setup

The simplest way to add structured logging to FastAPI:

```python
from fastapi import FastAPI
from fapilog import configure_logging, log

app = FastAPI()

# This automatically registers TraceIDMiddleware and enables request context enrichment
configure_logging(app=app)

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    # All logs automatically include request context: trace_id, method, path, client_ip, etc.
    log.info("Fetching user", user_id=user_id)

    try:
        user = await get_user_from_db(user_id)
        log.info("User found", user_id=user_id, user_name=user.name)
        return user
    except UserNotFound:
        log.warning("User not found", user_id=user_id)
        raise HTTPException(status_code=404, detail="User not found")
```

### Request Context Enrichment

Every log event during a request automatically includes:

| Field         | Type    | Description                 | Example            |
| ------------- | ------- | --------------------------- | ------------------ |
| `trace_id`    | string  | Request correlation ID      | `"abc123def456"`   |
| `span_id`     | string  | Request span ID             | `"xyz789uvw012"`   |
| `method`      | string  | HTTP method                 | `"POST"`           |
| `path`        | string  | Request path                | `"/api/users/123"` |
| `client_ip`   | string  | Client IP address           | `"192.168.1.100"`  |
| `status_code` | integer | HTTP response status        | `200`              |
| `latency_ms`  | float   | Request duration in ms      | `45.2`             |
| `user_agent`  | string  | User-Agent header           | `"curl/7.68.0"`    |
| `req_bytes`   | integer | Request body size in bytes  | `1024`             |
| `res_bytes`   | integer | Response body size in bytes | `2048`             |

### Trace ID Configuration

Configure the trace ID header name:

```python
from fapilog.settings import LoggingSettings

# Use custom header name
settings = LoggingSettings(trace_id_header="X-Custom-Trace-ID")
configure_logging(settings=settings, app=app)
```

```bash
# Via environment variable
export FAPILOG_TRACE_ID_HEADER=X-Custom-Trace-ID
```

### Response Headers

The middleware automatically adds correlation headers to responses:

- `X-Trace-Id`: Request trace identifier (for client correlation)
- `X-Span-Id`: Request span identifier
- `X-Response-Time-ms`: Request latency in milliseconds

### Manual Middleware Registration

If you prefer manual setup:

```python
from fapilog.middleware import TraceIDMiddleware
from fapilog.settings import LoggingSettings

app = FastAPI()
settings = LoggingSettings(trace_id_header="X-Request-ID")

# Register middleware manually
app.add_middleware(TraceIDMiddleware, trace_id_header=settings.trace_id_header)
configure_logging(settings=settings)
```

---

## User Context Enrichment

Automatically include authenticated user information in all log events with zero code changes to your logging calls.

### Automatic User Context with FastAPI

Wrap your existing authentication dependencies to automatically bind user context:

```python
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer
from fapilog import configure_logging, log
from fapilog.enrichers import create_user_dependency

app = FastAPI()
configure_logging(app=app)

security = HTTPBearer()

# Your existing authentication function
async def get_current_user_base(token: str = Depends(security)):
    """Your existing auth logic - no changes needed."""
    if not validate_token(token):
        raise HTTPException(401, "Invalid token")

    return {
        "user_id": "user123",
        "roles": ["admin", "user"],
        "auth_scheme": "Bearer"
    }

# Create the context-aware dependency
get_current_user = create_user_dependency(get_current_user_base)

@app.get("/api/profile")
async def get_profile(user = Depends(get_current_user)):
    # All logs automatically include user_id, user_roles, auth_scheme
    log.info("Profile accessed", section="personal_info")
    log.info("Data retrieved", record_count=15)
    return {"user": user}
```

### What Gets Added Automatically

The user context enricher adds these fields to every log event:

- **`user_id`**: Authenticated user identifier
- **`user_roles`**: Array of user roles/permissions
- **`auth_scheme`**: Authentication method (Bearer, Basic, JWT, etc.)

### Compatible User Objects

Works with any user object format:

**Dict-based users:**

```python
def get_user():
    return {
        "user_id": "123",           # or "id"
        "user_roles": ["admin"],    # or "roles"
        "auth_scheme": "Bearer"     # or "scheme"
    }
```

**Class-based users:**

```python
class User:
    def __init__(self):
        self.id = "123"             # or user_id
        self.roles = ["admin"]      # or user_roles
        self.scheme = "Bearer"      # or auth_scheme

def get_user():
    return User()
```

### Optional Authentication

For endpoints that work with or without authentication:

```python
from fastapi.security import OAuth2PasswordBearer

oauth2_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

async def get_user_optional(token: str = Depends(oauth2_optional)):
    if not token:
        return None  # No user authenticated
    return validate_and_get_user(token)

# Create optional context dependency
get_user_context_optional = create_user_dependency(get_user_optional)

@app.get("/content")
async def get_content(user = Depends(get_user_context_optional)):
    if user:
        log.info("Authenticated content access")  # Includes user context
    else:
        log.info("Anonymous content access")      # No user context fields

    return {"content": "public or premium based on user"}
```

### Configuration

User context enrichment is enabled by default. To disable:

```python
from fapilog.settings import LoggingSettings

settings = LoggingSettings(
    user_context_enabled=False  # Disable user context
)
configure_logging(settings=settings)
```

**Environment variable:**

```bash
export FAPILOG_USER_CONTEXT_ENABLED=false
```

### Example Log Output

**Authenticated request:**

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "info",
  "event": "Profile accessed",
  "trace_id": "abc123def456",
  "user_id": "user123",
  "user_roles": ["admin", "user"],
  "auth_scheme": "Bearer",
  "section": "personal_info"
}
```

**Unauthenticated request:**

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "info",
  "event": "Anonymous content access",
  "trace_id": "abc123def456"
}
```

---

## Advanced Configuration

Configure `fapilog` for high-performance and production environments.

### Queue Configuration

**High-Throughput Applications:**

```python
settings = LoggingSettings(
    queue_maxsize=5000,        # Larger queue
    queue_batch_size=50,       # Larger batches
    queue_batch_timeout=0.5,   # Shorter timeout
    queue_overflow="drop"      # Drop logs under load
)
```

**Guaranteed Log Delivery:**

```python
settings = LoggingSettings(
    queue_overflow="block",    # Wait for space
    queue_maxsize=1000,
    queue_retry_delay=2.0,    # Longer retry delay
    queue_max_retries=5       # More retries
)
```

**Adaptive Sampling:**

```python
settings = LoggingSettings(
    queue_overflow="sample",   # Probabilistic sampling
    sampling_rate=0.1,        # Keep 10% of logs
    queue_maxsize=1000
)
```

### Performance Tuning

**Memory Optimization:**

```python
settings = LoggingSettings(
    enable_resource_metrics=False,  # Disable for performance
    queue_batch_size=100,          # Larger batches
    queue_batch_timeout=2.0        # Longer timeouts
)
```

**CPU Optimization:**

```python
settings = LoggingSettings(
    queue_enabled=True,           # Async processing
    queue_overflow="drop",        # Don't block
    sampling_rate=0.5            # Sample under load
)
```

### Security Configuration

**Data Redaction:**

`fapilog` provides two complementary approaches to redact sensitive information from logs:

#### Pattern-Based Redaction

Use regex patterns to redact values that match specific patterns in field names or values:

```python
settings = LoggingSettings(
    redact_patterns=[
        r"password=\w+",
        r"token=\w+",
        r"ssn=\d{3}-\d{2}-\d{4}"
    ]
)
```

**Environment Variables:**

```bash
export FAPILOG_REDACT_PATTERNS="password,token,secret"
```

#### Field-Based Redaction

Use exact field names to redact specific fields, including nested fields using dot notation:

```python
settings = LoggingSettings(
    redact_fields=[
        "user.password",
        "auth.token",
        "api_key",
        "config.secret_key"
    ],
    redact_replacement="***"
)
```

**Environment Variables:**

```bash
export FAPILOG_REDACT_FIELDS="user.password,auth.token,api_key"
export FAPILOG_REDACT_REPLACEMENT="***"
```

**Features:**

- **Nested field support**: Use dot notation to redact nested fields (e.g., `user.profile.email`)
- **List support**: Automatically redacts fields within lists of dictionaries
- **Custom replacement**: Configure the replacement value (default: `"REDACTED"`)
- **Non-destructive**: Original data is never modified, only the log output is redacted

**Examples:**

```python
# Redact top-level fields
redact_fields=["password", "api_key"]

# Redact nested fields
redact_fields=["user.password", "auth.token", "config.secret_key"]

# Redact fields in lists
redact_fields=["users.password", "items.secret_data"]

# Custom replacement value
redact_replacement="[REDACTED]"
```

**Before redaction:**

```json
{
  "user": {
    "name": "john",
    "password": "secret123"
  },
  "auth": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  },
  "users": [
    { "name": "alice", "password": "alice_secret" },
    { "name": "bob", "password": "bob_secret" }
  ]
}
```

**After redaction:**

```json
{
  "user": {
    "name": "john",
    "password": "REDACTED"
  },
  "auth": {
    "token": "REDACTED"
  },
  "users": [
    { "name": "alice", "password": "REDACTED" },
    { "name": "bob", "password": "REDACTED" }
  ]
}
```

**Combined Redaction:**

You can use both pattern-based and field-based redaction together for comprehensive coverage:

```python
settings = LoggingSettings(
    redact_patterns=[r"(?i)password", r"(?i)token"],  # Catch any password/token fields
    redact_fields=["user.password", "auth.token"],      # Explicit field redaction
    redact_replacement="***"
)
```

#### Level-Aware Redaction

Control redaction behavior based on log levels to preserve debugging context in development while ensuring security in production:

```python
settings = LoggingSettings(
    redact_level="INFO",  # Only redact at INFO level and above
    redact_patterns=[r"(?i)password"],
    redact_fields=["user.password", "auth.token"]
)
```

**Environment Variable:**

```bash
export FAPILOG_REDACT_LEVEL="INFO"
```

**How it works:**

- **DEBUG** logs bypass redaction (full context preserved for debugging)
- **INFO** and higher logs apply redaction (sensitive data protected)
- Log level hierarchy: `DEBUG < INFO < WARNING < ERROR < CRITICAL`

**Example behavior:**

```python
# DEBUG level - no redaction (full context for debugging)
log.debug("Authentication attempt", user={"password": "secret123"})
# Output: {"level": "DEBUG", "user": {"password": "secret123"}}

# INFO level - redacted (production safe)
log.info("Authentication successful", user={"password": "secret123"})
# Output: {"level": "INFO", "user": {"password": "REDACTED"}}
```

**Use cases:**

- **Development**: Set `FAPILOG_REDACT_LEVEL=DEBUG` to see all data
- **Staging**: Set `FAPILOG_REDACT_LEVEL=INFO` for realistic testing
- **Production**: Set `FAPILOG_REDACT_LEVEL=INFO` for security compliance

**Field Filtering (Legacy):**

```python
# In your enrichers
def security_enricher(logger, method_name, event_dict):
    # Remove sensitive fields
    event_dict.pop("password", None)
    event_dict.pop("api_key", None)
    return event_dict
```

---

## Custom Enrichers

Add application-specific metadata to all log events automatically.

### Basic Custom Enricher

```python
from fapilog.enrichers import register_enricher
from fapilog import configure_logging, log

def app_metadata_enricher(logger, method_name, event_dict):
    """Add application metadata to logs."""
    import os
    event_dict["app_version"] = "1.0.0"
    event_dict["deployment_id"] = os.getenv("DEPLOYMENT_ID", "local")
    return event_dict

def environment_enricher(logger, method_name, event_dict):
    """Add environment information."""
    import os
    event_dict["environment"] = os.getenv("ENVIRONMENT", "development")
    event_dict["service_name"] = "my-fastapi-app"
    return event_dict

# Register enrichers
register_enricher(app_metadata_enricher)
register_enricher(environment_enricher)

# Configure logging
configure_logging()

# All logs now include app metadata and environment info
log.info("API request processed", endpoint="/api/users")
```

### Advanced Enrichers

**Request-Scoped Enricher:**

```python
from fapilog._internal.context import get_context

def request_enricher(logger, method_name, event_dict):
    """Add request-scoped data."""
    context = get_context()

    # Add request metadata
    if "trace_id" in context:
        event_dict["trace_id"] = context["trace_id"]

    # Add business context
    if "tenant_id" in context:
        event_dict["tenant_id"] = context["tenant_id"]

    return event_dict

register_enricher(request_enricher)
```

**Performance Enricher:**

```python
import time
import psutil

def performance_enricher(logger, method_name, event_dict):
    """Add performance metrics."""
    process = psutil.Process()

    # Memory usage
    memory_info = process.memory_info()
    event_dict["memory_mb"] = round(memory_info.rss / (1024 * 1024), 2)

    # CPU usage
    event_dict["cpu_percent"] = round(process.cpu_percent(), 2)

    return event_dict

register_enricher(performance_enricher)
```

**Business Metrics Enricher:**

```python
def business_metrics_enricher(logger, method_name, event_dict):
    """Add business-specific metrics."""
    # Add business context
    event_dict["business_unit"] = "e-commerce"
    event_dict["feature_flag"] = get_feature_flag("new_ui")

    # Add timing if available
    if "duration_ms" in event_dict:
        if event_dict["duration_ms"] > 1000:
            event_dict["performance_category"] = "slow"
        elif event_dict["duration_ms"] > 100:
            event_dict["performance_category"] = "medium"
        else:
            event_dict["performance_category"] = "fast"

    return event_dict

register_enricher(business_metrics_enricher)
```

### Enricher Management

**Register Multiple Enrichers:**

```python
from fapilog.enrichers import register_enricher, clear_enrichers

# Clear existing enrichers
clear_enrichers()

# Register new enrichers
register_enricher(user_enricher)
register_enricher(performance_enricher)
register_enricher(business_enricher)
```

**Conditional Enrichers:**

```python
def conditional_enricher(logger, method_name, event_dict):
    """Only add fields in certain conditions."""
    if method_name == "error":
        event_dict["error_timestamp"] = time.time()
        event_dict["error_count"] = get_error_count()

    return event_dict
```

---

## Container Architecture

`fapilog` uses a modern container-based dependency injection architecture that provides excellent testability, thread safety, and supports multiple logging configurations within the same process.

### When to Use Containers

**Simple Applications (Default Approach):**

```python
from fapilog import configure_logging

# This works great for most applications
logger = configure_logging()
logger.info("Application started")
```

**Advanced Applications (Container Approach):**

```python
from fapilog.container import LoggingContainer
from fapilog.settings import LoggingSettings

# Use containers when you need:
# - Multiple logging configurations
# - Better test isolation
# - Thread-safe concurrent logging
# - Explicit resource management
```

### Multiple Configuration Example

Create isolated logging configurations for different parts of your application:

```python
from fapilog.container import LoggingContainer
from fapilog.settings import LoggingSettings

# Admin service: verbose logging to file
admin_settings = LoggingSettings(
    level="DEBUG",
    sinks=["stdout", "file:///var/log/admin.log"],
    redact_fields=["password", "token"]
)
admin_container = LoggingContainer(admin_settings)
admin_logger = admin_container.configure()

# API service: JSON logging to Loki
api_settings = LoggingSettings(
    level="INFO",
    sinks=["stdout", "loki://loki:3100"],
    json_console="json",
    queue_enabled=True
)
api_container = LoggingContainer(api_settings)
api_logger = api_container.configure()

# Background worker: minimal logging
worker_settings = LoggingSettings(
    level="WARNING",
    sinks=["stdout"],
    sampling_rate=0.1  # Only 10% of logs
)
worker_container = LoggingContainer(worker_settings)
worker_logger = worker_container.configure()

# Each logger operates completely independently
admin_logger.debug("Admin debug message")
api_logger.info("API request processed")
worker_logger.warning("Worker task failed")
```

### Testing with Container Isolation

Containers prevent test interference and provide clean test isolation:

```python
import pytest
from fapilog.container import LoggingContainer
from fapilog.settings import LoggingSettings

class TestMyService:
    @pytest.fixture
    def logging_container(self):
        """Create isolated logging for tests."""
        settings = LoggingSettings(
            level="DEBUG",
            sinks=["stdout"],
            queue_enabled=False,  # Synchronous for testing
            json_console="json"   # Consistent output format
        )
        container = LoggingContainer(settings)
        logger = container.configure()

        yield container, logger

        # Automatic cleanup after test
        container.reset()

    def test_user_creation(self, logging_container):
        container, logger = logging_container

        # Test your service with isolated logging
        logger.info("Creating user", user_id="123")

        # Verify container state
        assert container.is_configured
        assert container.settings.level == "DEBUG"

    def test_error_handling(self, logging_container):
        container, logger = logging_container

        # Each test gets a fresh container
        logger.error("Service error", error_code="E001")

        # No interference from other tests
        assert container.queue_worker is None  # Queue disabled
```

### Thread-Safe Concurrent Logging

Containers are fully thread-safe for concurrent applications:

```python
import threading
import time
from fapilog.container import LoggingContainer

def service_worker(service_name: str, message_count: int):
    """Worker function that creates its own logging container."""
    # Each thread gets its own container
    container = LoggingContainer()
    logger = container.configure()

    for i in range(message_count):
        logger.info(
            f"{service_name} processing",
            message_id=i,
            service=service_name,
            thread_id=threading.current_thread().ident
        )
        time.sleep(0.01)  # Simulate work

    # Clean shutdown
    container.shutdown_sync()
    logger.info(f"{service_name} completed", total_messages=message_count)

# Start multiple concurrent services
threads = []
for service_id in range(5):
    thread = threading.Thread(
        target=service_worker,
        args=(f"service-{service_id}", 100)
    )
    threads.append(thread)
    thread.start()

# Wait for all services to complete
for thread in threads:
    thread.join()

print("All services completed successfully")
```

### Container Lifecycle Management

Containers provide explicit resource management:

```python
from fapilog.container import LoggingContainer, cleanup_all_containers

# Manual lifecycle management
container = LoggingContainer()
try:
    logger = container.configure()

    # Application logic
    logger.info("Application running")

finally:
    # Explicit cleanup (recommended for long-running processes)
    container.shutdown_sync()

# Global cleanup (automatic on process exit)
cleanup_all_containers()
```

### FastAPI Integration with Containers

Containers integrate seamlessly with FastAPI for dependency injection:

```python
from fastapi import FastAPI, Depends
from fapilog.container import LoggingContainer
from fapilog.settings import LoggingSettings

app = FastAPI()

# Create application-level container
app_container = LoggingContainer(
    LoggingSettings(
        level="INFO",
        sinks=["stdout", "file:///var/log/api.log"],
        trace_id_header="X-Request-ID"
    )
)

# Configure with automatic middleware registration
app_logger = app_container.configure(app=app)

def get_logger():
    """Dependency to inject logger into routes."""
    return app_logger

@app.get("/users/{user_id}")
async def get_user(user_id: str, logger=Depends(get_logger)):
    logger.info("Fetching user", user_id=user_id)
    return {"user_id": user_id, "name": "John Doe"}

@app.on_event("shutdown")
async def shutdown_event():
    """Clean shutdown of logging resources."""
    await app_container.shutdown()
```

### Container Best Practices

1. **Use Default API for Simple Cases**: `configure_logging()` is perfect for most applications
2. **Use Containers for Complex Scenarios**: Multiple configs, testing, or thread safety requirements
3. **Always Clean Up**: Call `shutdown_sync()` or `shutdown()` in long-running applications
4. **Test Isolation**: Use separate containers in tests to prevent interference
5. **Thread Safety**: Create thread-local containers when needed
6. **Resource Monitoring**: Monitor container memory usage in production

### Container Properties and Debugging

Containers provide introspection capabilities for debugging:

```python
container = LoggingContainer()
logger = container.configure()

# Check container state
print(f"Configured: {container.is_configured}")
print(f"Settings: {container.settings}")
print(f"Queue Worker: {container.queue_worker}")

# Access queue statistics (if queue enabled)
if container.queue_worker:
    queue = container.queue_worker.queue
    print(f"Queue size: {queue.qsize()}")
    print(f"Queue maxsize: {queue.maxsize}")
    print(f"Worker running: {container.queue_worker._running}")
```

📖 **For complete container documentation, see [Container Architecture Guide](docs/container-architecture.md)**

---

## Custom Sinks

Create custom sinks for specialized logging requirements.

### Basic Custom Sink

```python
from fapilog._internal.queue import Sink
import json

class FileSink(Sink):
    """Write logs to a file."""

    def __init__(self, filename: str):
        self.filename = filename

    async def write(self, event_dict):
        """Write log event to file."""
        with open(self.filename, "a") as f:
            f.write(json.dumps(event_dict) + "\n")

    async def close(self):
        """Clean up resources."""
        pass
```

### HTTP API Sink

```python
import aiohttp
from fapilog._internal.queue import Sink

class HTTPApiSink(Sink):
    """Send logs to HTTP API endpoint."""

    def __init__(self, url: str, api_key: str):
        self.url = url
        self.api_key = api_key
        self.session = None

    async def start(self):
        """Initialize the sink."""
        self.session = aiohttp.ClientSession()

    async def write(self, event_dict):
        """Send log to HTTP API."""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        await self.session.post(self.url, json=event_dict, headers=headers)

    async def close(self):
        """Clean up resources."""
        if self.session:
            await self.session.close()
```

### Audit Log Sink

```python
import json
import time
from fapilog._internal.queue import Sink

class AuditLogSink(Sink):
    """Specialized sink for audit logging."""

    def __init__(self, audit_file: str):
        self.audit_file = audit_file

    async def write(self, event_dict):
        """Write audit log with special formatting."""
        audit_entry = {
            "timestamp": time.time(),
            "audit_type": "user_action",
            "user_id": event_dict.get("user_id"),
            "action": event_dict.get("action"),
            "resource": event_dict.get("resource"),
            "ip_address": event_dict.get("ip_address"),
            "user_agent": event_dict.get("user_agent")
        }

        with open(self.audit_file, "a") as f:
            f.write(json.dumps(audit_entry) + "\n")
```

### Using Custom Sinks

**Register with Queue Worker:**

```python
from fapilog._internal.queue import QueueWorker

# Create custom sinks
file_sink = FileSink("app.log")
api_sink = HTTPApiSink("https://logs.example.com/api", "api-key")

# Create queue worker with custom sinks
worker = QueueWorker(
    sinks=[file_sink, api_sink],
    queue_size=1000,
    batch_size=10
)
```

**Integration with FastAPI:**

```python
from fastapi import FastAPI
from fapilog import configure_logging

app = FastAPI()

# Configure with custom sinks
settings = LoggingSettings(
    queue_enabled=True,
    queue_maxsize=1000
)

configure_logging(settings=settings)

# Your custom sinks will be used automatically
```

---

## Performance Tuning

Optimize `fapilog` for your specific performance requirements.

### High-Throughput Scenarios

**API with 10K+ requests/second:**

```python
settings = LoggingSettings(
    queue_maxsize=10000,       # Large queue
    queue_batch_size=100,      # Large batches
    queue_batch_timeout=0.1,   # Short timeout
    queue_overflow="drop",     # Drop under load
    sampling_rate=0.1          # Sample 10% of logs
)
```

**Memory-Constrained Environments:**

```python
settings = LoggingSettings(
    queue_maxsize=100,         # Small queue
    queue_batch_size=5,        # Small batches
    enable_resource_metrics=False,  # Disable metrics
    queue_overflow="block"     # Wait for space
)
```

### Load Testing

**Test Queue Performance:**

```python
import asyncio
from fapilog import configure_logging, log

# Configure for load testing
settings = LoggingSettings(
    queue_maxsize=1000,
    queue_batch_size=50,
    queue_overflow="drop"
)

configure_logging(settings=settings)

async def load_test():
    """Generate high-volume logs."""
    for i in range(10000):
        log.info(f"load_test_message_{i}", iteration=i)
        await asyncio.sleep(0.001)  # 1ms between logs

# Run load test
asyncio.run(load_test())
```

### Monitoring Performance

**Enable Resource Metrics:**

```python
settings = LoggingSettings(
    enable_resource_metrics=True,
    level="INFO"
)

configure_logging(settings=settings)

# Log events will include memory and CPU usage
log.info("Performance check", operation="database_query")
```

**Monitor Queue Health:**

```python
from fapilog._internal.queue import get_queue_stats

# Get queue statistics
stats = get_queue_stats()
log.info(
    "Queue health check",
    queue_size=stats.queue_size,
    queue_maxsize=stats.queue_maxsize,
    dropped_events=stats.dropped_events
)
```

---

## Production Deployment

Deploy `fapilog` in production environments with proper configuration and monitoring.

### Docker Deployment

**Dockerfile:**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application
COPY . .

# Set production environment
ENV FAPILOG_LEVEL=INFO
ENV FAPILOG_JSON_CONSOLE=json
ENV FAPILOG_QUEUE_ENABLED=true
ENV FAPILOG_ENABLE_RESOURCE_METRICS=true

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**docker-compose.yml:**

```yaml
version: "3.8"
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - FAPILOG_LEVEL=INFO
      - FAPILOG_QUEUE_ENABLED=true
      - FAPILOG_QUEUE_MAXSIZE=2000
    volumes:
      - ./logs:/app/logs
```

### Kubernetes Deployment

**ConfigMap:**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fapilog-config
data:
  FAPILOG_LEVEL: "INFO"
  FAPILOG_JSON_CONSOLE: "json"
  FAPILOG_QUEUE_ENABLED: "true"
  FAPILOG_QUEUE_MAXSIZE: "2000"
  FAPILOG_ENABLE_RESOURCE_METRICS: "true"
```

**Deployment:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-api
  template:
    metadata:
      labels:
        app: my-api
    spec:
      containers:
        - name: api
          image: my-api:latest
          envFrom:
            - configMapRef:
                name: fapilog-config
          ports:
            - containerPort: 8000
```

### Environment Configuration

**Development:**

```bash
export FAPILOG_LEVEL=DEBUG
export FAPILOG_JSON_CONSOLE=pretty
export FAPILOG_QUEUE_ENABLED=false
export FAPILOG_ENABLE_RESOURCE_METRICS=false
```

**Staging:**

```bash
export FAPILOG_LEVEL=INFO
export FAPILOG_JSON_CONSOLE=json
export FAPILOG_QUEUE_ENABLED=true
export FAPILOG_QUEUE_MAXSIZE=1000
export FAPILOG_ENABLE_RESOURCE_METRICS=true
```

**Production:**

```bash
export FAPILOG_LEVEL=WARN
export FAPILOG_JSON_CONSOLE=json
export FAPILOG_QUEUE_ENABLED=true
export FAPILOG_QUEUE_MAXSIZE=5000
export FAPILOG_QUEUE_OVERFLOW=drop
export FAPILOG_SAMPLING_RATE=0.1
export FAPILOG_ENABLE_RESOURCE_METRICS=true
```

### Monitoring Integration

**Prometheus Metrics:**

```python
from prometheus_client import Counter, Histogram
from fapilog import log

# Define metrics
log_events_total = Counter('log_events_total', 'Total log events', ['level'])
log_event_duration = Histogram('log_event_duration_seconds', 'Log event duration')

def monitored_logger(level, message, **kwargs):
    """Log with metrics."""
    log_events_total.labels(level=level).inc()

    with log_event_duration.time():
        getattr(log, level)(message, **kwargs)
```

**Health Checks:**

```python
@app.get("/health/logging")
async def logging_health():
    """Check logging system health."""
    try:
        # Test logging
        log.info("Health check", check_type="logging")

        # Get queue stats
        stats = get_queue_stats()

        return {
            "status": "healthy",
            "queue_size": stats.queue_size,
            "queue_maxsize": stats.queue_maxsize
        }
    except Exception as e:
        log.error("Logging health check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Logging unhealthy")
```

---

## Troubleshooting

Common issues and their solutions.

### Configuration Issues

**Logs not appearing:**

```python
# Check configuration
from fapilog.settings import LoggingSettings
settings = LoggingSettings()
print(settings.model_dump())

# Enable debug logging
import logging
logging.getLogger("fapilog").setLevel(logging.DEBUG)
```

**Queue not working:**

```python
# Check queue configuration
settings = LoggingSettings(queue_enabled=True)
configure_logging(settings=settings)

# Test queue
log.info("Queue test")
```

### Performance Issues

**High memory usage:**

```python
# Reduce queue size
settings = LoggingSettings(
    queue_maxsize=100,
    queue_batch_size=5,
    enable_resource_metrics=False
)
```

**Slow logging:**

```python
# Enable async queue
settings = LoggingSettings(
    queue_enabled=True,
    queue_overflow="drop",
    queue_batch_size=50
)
```

### Integration Issues

**FastAPI middleware not working:**

```python
# Ensure middleware is registered
from fapilog import configure_logging
app = FastAPI()
configure_logging(app=app)  # This registers middleware
```

**Custom enrichers not working:**

```python
# Clear and re-register enrichers
from fapilog.enrichers import clear_enrichers, register_enricher

clear_enrichers()
register_enricher(my_enricher)
configure_logging()
```

### Debug Mode

**Enable debug logging:**

```python
import logging
logging.getLogger("fapilog").setLevel(logging.DEBUG)

# Configure with debug
settings = LoggingSettings(level="DEBUG")
configure_logging(settings=settings)
```

**Test configuration:**

```python
# Test all components
log.debug("Debug test")
log.info("Info test")
log.warning("Warning test")
log.error("Error test")
```

### Error Handling Best Practices

**Graceful Error Handling:**

```python
from fapilog.exceptions import ConfigurationError, SinkError, QueueError

try:
    configure_logging(settings=settings)
except ConfigurationError as e:
    # Log the error with context
    log.error("Configuration failed",
              error=str(e),
              operation=e.operation,
              context=e.context)
    # Fall back to basic configuration
    configure_logging()
```

**Sink Error Recovery:**

```python
from fapilog.exceptions import SinkError

try:
    log.info("Important message")
except SinkError as e:
    # Log to fallback sink
    print(f"Logging failed: {e.user_friendly_message}")
    # Continue application execution
```

**Queue Error Handling:**

```python
from fapilog.exceptions import QueueError

try:
    # High-volume logging
    for i in range(10000):
        log.info(f"Processing item {i}")
except QueueError as e:
    # Queue is full, use synchronous logging
    log.warning("Queue full, falling back to sync logging",
                queue_size=e.queue_size,
                max_size=e.max_size)
```

**Context Error Recovery:**

```python
from fapilog.exceptions import ContextError
from fapilog._internal.context import get_context

try:
    context = get_context()
    log.info("Request processed", **context)
except ContextError as e:
    # Log without context
    log.info("Request processed (no context available)")
```

**Redaction Error Handling:**

```python
from fapilog.exceptions import RedactionError

try:
    log.info("User data", user_email="user@example.com")
except RedactionError as e:
    # Log without redaction
    log.warning("Redaction failed, logging original data",
                error=str(e),
                pattern=e.pattern)
```

### Common Error Messages

**`ConfigurationError: Invalid log level 'INVALID'`**

- **Cause**: Invalid log level specified in configuration
- **Solution**: Use valid log levels: DEBUG, INFO, WARN, ERROR, CRITICAL
- **Example**: `FAPILOG_LEVEL=DEBUG` (correct) vs `FAPILOG_LEVEL=INVALID` (incorrect)

**`SinkError: Failed to write to log file`**

- **Cause**: File sink cannot write to specified location
- **Solution**: Check file permissions and directory existence
- **Example**: Ensure `/var/log/app.log` is writable

**`QueueError: Queue is full`**

- **Cause**: Log queue has reached maximum capacity
- **Solution**: Increase queue size or use overflow strategies
- **Example**: `FAPILOG_QUEUE_MAXSIZE=5000` or `FAPILOG_QUEUE_OVERFLOW=drop`

**`MiddlewareError: Failed to bind context`**

- **Cause**: Context variable binding failed
- **Solution**: Check context variable names and async context
- **Example**: Ensure context operations happen in proper async context

**`RedactionError: Invalid regex pattern`**

- **Cause**: Invalid regex pattern in redaction configuration
- **Solution**: Fix regex syntax or use simpler patterns
- **Example**: `FAPILOG_REDACT_PATTERNS=email,phone` (correct) vs `FAPILOG_REDACT_PATTERNS=[invalid` (incorrect)

**`ContextError: Invalid context variable`**

- **Cause**: Attempting to access non-existent context variable
- **Solution**: Use valid context variable names
- **Example**: Use `trace_id`, `user_id`, `method` instead of custom names

**Legacy Exceptions (for backward compatibility):**

**"RuntimeError: Cannot configure logging from async context"**

- Solution: Configure logging before entering async context

**"ValueError: Invalid level 'INVALID'"**

- Solution: Use valid log levels: DEBUG, INFO, WARN, ERROR, CRITICAL

**"ImportError: No module named 'psutil'"**

- Solution: Install psutil or disable resource metrics

---

## Next Steps

Now that you've learned the basics, explore these advanced topics:

1. **API Reference** - Complete technical documentation
2. **Custom Sinks** - Create specialized log destinations
3. **Performance Tuning** - Optimize for your use case
4. **Production Deployment** - Deploy with confidence
5. **Contributing** - Help improve `fapilog`

### Examples to Try

- [Basic Setup](examples/01_basic_setup.py) - Minimal configuration
- [Environment Config](examples/02_environment_config.py) - Environment-based setup
- [FastAPI Basic](examples/05_fastapi_basic.py) - FastAPI integration
- [Structured Logging](examples/08_fastapi_structured_logging.py) - Advanced patterns
- [Trace Propagation](examples/17_trace_propagation.py) - Story 6.2 features
- [Custom Enrichers](examples/custom_enricher_example.py) - Custom metadata
- [Custom Sinks](examples/15_custom_sink.py) - Specialized logging
- [Field Redaction](examples/19_field_redaction.py) - Manual field redaction
- [Automatic PII Redaction](examples/20_automatic_pii_redaction.py) - Automatic PII detection

### Getting Help

- **Documentation**: [API Reference](api-reference.md)
- **Examples**: Check the `examples/` directory
- **Issues**: Report bugs on GitHub
- **Discussions**: Ask questions in GitHub Discussions

Happy logging! 🚀

**See also:** [Primer](primer.md), [Quickstart](quickstart.md), [API Reference](api-reference.md), [Config](config.md), [Style Guide](style-guide.md)
