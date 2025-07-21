# Examples & Recipes

**Real-world examples and recipes for using Fapilog in different scenarios.**

This section provides practical, copy-paste ready examples that demonstrate Fapilog's capabilities across various use cases. Each example includes complete code, explanations, and best practices.

**See also:** [Quickstart Tutorial](quickstart.md), [API Reference](api-reference.md), [User Guide](user-guide.md)

---

## Table of Contents

- [Getting Started](#getting-started)
- [FastAPI Integration](#fastapi-integration)
- [Configuration & Environment](#configuration--environment)
- [Security & Compliance](#security--compliance)
- [Performance & Monitoring](#performance--monitoring)
- [Custom Components](#custom-components)
- [Advanced Patterns](#advanced-patterns)

---

## Getting Started

### Basic Setup

**Minimal setup to get started with structured logging.**

```python
# examples/01_basic_setup.py
from fapilog import configure_logging, log

# Configure logging with defaults
configure_logging()

# Basic logging operations
log.info("Application started", version="1.0.0", environment="development")
log.warning("Deprecated feature used", feature="old_api", replacement="new_api")
log.error("Database connection failed", database="postgres", error="timeout")

# Structured logging with multiple fields
log.info(
    "User action completed",
    user_id="user_123",
    action="login",
    ip_address="192.168.1.100",
    duration_ms=45.2,
)
```

**Key Features Demonstrated:**

- ✅ Structured JSON logging
- ✅ Multiple field support
- ✅ Log levels (INFO, WARNING, ERROR)
- ✅ Automatic timestamp and enrichment
- ✅ Hostname and process ID

**Output:**

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "info",
  "event": "Application started",
  "hostname": "server-01",
  "pid": 12345,
  "version": "1.0.0",
  "environment": "development"
}
```

### Environment Configuration

**Configure logging using environment variables for different deployments.**

```python
# examples/02_environment_config.py
import os
from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings

# Environment-specific configuration
environment = os.getenv("ENVIRONMENT", "development")

if environment == "production":
    settings = LoggingSettings(
        level="INFO",
        format="json",
        sinks=["stdout", "file"],
        file_path="/var/log/app.log",
        queue_enabled=True,
        queue_size=5000,
        redact_patterns=["email", "phone", "credit_card"]
    )
else:
    settings = LoggingSettings(
        level="DEBUG",
        format="pretty",
        sinks=["stdout"],
        queue_enabled=False
    )

configure_logging(settings=settings)

log.info("Application configured", environment=environment)
```

**Environment Variables:**

```bash
# Development
export ENVIRONMENT=development
export FAPILOG_LEVEL=DEBUG
export FAPILOG_FORMAT=pretty

# Production
export ENVIRONMENT=production
export FAPILOG_LEVEL=INFO
export FAPILOG_FORMAT=json
export FAPILOG_SINKS=stdout,file
export FAPILOG_FILE_PATH=/var/log/app.log
export FAPILOG_QUEUE_ENABLED=true
```

---

## FastAPI Integration

### Basic FastAPI Setup

**Integrate Fapilog with FastAPI for automatic request logging and trace correlation.**

```python
# examples/05_fastapi_basic.py
from fastapi import FastAPI, HTTPException
from fapilog import configure_logging, log

# Create FastAPI app
app = FastAPI(title="My API", version="1.0.0")

# Configure logging with FastAPI integration
configure_logging(app=app)

@app.get("/users/{user_id}")
async def get_user(user_id: str):
    log.info("User requested", user_id=user_id, endpoint="/users/{user_id}")

    try:
        user = await get_user_from_db(user_id)
        log.info("User found", user_id=user_id, user_name=user.name)
        return user
    except UserNotFound:
        log.warning("User not found", user_id=user_id)
        raise HTTPException(status_code=404, detail="User not found")

@app.post("/users")
async def create_user(user_data: dict):
    log.info("Creating user", email=user_data.get("email"))

    try:
        user = await create_user_in_db(user_data)
        log.info("User created", user_id=user.id, email=user.email)
        return user
    except DuplicateEmailError:
        log.error("Duplicate email", email=user_data.get("email"))
        raise HTTPException(status_code=400, detail="Email already exists")
```

**Automatic Features:**

- ✅ Request correlation with trace IDs
- ✅ Request/response metadata capture
- ✅ Performance timing
- ✅ Error tracking with context
- ✅ Response headers with trace info

### FastAPI with Middleware

**Enhanced FastAPI integration with custom middleware and error handling.**

```python
# examples/06_fastapi_middleware.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fapilog import configure_logging, log
from fapilog.middleware import TraceIDMiddleware

app = FastAPI()

# Add custom middleware for enhanced logging
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    start_time = time.time()

    # Log request start
    log.info("Request started",
             method=request.method,
             path=request.url.path,
             client_ip=request.client.host)

    try:
        response = await call_next(request)

        # Log successful response
        duration_ms = (time.time() - start_time) * 1000
        log.info("Request completed",
                 method=request.method,
                 path=request.url.path,
                 status_code=response.status_code,
                 duration_ms=duration_ms)

        return response

    except Exception as e:
        # Log error with context
        duration_ms = (time.time() - start_time) * 1000
        log.error("Request failed",
                  method=request.method,
                  path=request.url.path,
                  error=str(e),
                  error_type=type(e).__name__,
                  duration_ms=duration_ms)
        raise

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.error("Unhandled exception",
              method=request.method,
              path=request.url.path,
              error=str(exc),
              error_type=type(exc).__name__)

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
```

### Structured Logging in FastAPI

**Advanced structured logging patterns for API development.**

```python
# examples/08_fastapi_structured_logging.py
from fastapi import FastAPI, Depends, HTTPException
from fapilog import configure_logging, log
from fapilog._internal.context import bind_context

app = FastAPI()
configure_logging(app=app)

# User dependency with context binding
async def get_current_user(token: str = Depends(oauth2_scheme)):
    user = await verify_token(token)
    # Bind user context to all subsequent logs
    bind_context(user_id=user.id, user_role=user.role)
    return user

@app.get("/api/users/{user_id}")
async def get_user(user_id: str, current_user = Depends(get_current_user)):
    # All logs in this request include user context
    log.info("User detail requested", target_user_id=user_id)

    try:
        user = await get_user_by_id(user_id)
        log.info("User retrieved",
                 target_user_id=user_id,
                 user_name=user.name,
                 user_email=user.email)
        return user
    except UserNotFound:
        log.warning("User not found", target_user_id=user_id)
        raise HTTPException(status_code=404, detail="User not found")

@app.post("/api/orders")
async def create_order(order_data: dict, current_user = Depends(get_current_user)):
    log.info("Order creation started",
             order_items=len(order_data.get("items", [])),
             total_amount=order_data.get("total"))

    try:
        order = await create_order_in_db(order_data, current_user.id)
        log.info("Order created successfully",
                 order_id=order.id,
                 order_total=order.total,
                 payment_method=order.payment_method)
        return order
    except PaymentError as e:
        log.error("Payment failed",
                  order_total=order_data.get("total"),
                  payment_method=order_data.get("payment_method"),
                  error=str(e))
        raise HTTPException(status_code=400, detail="Payment failed")
```

---

## Configuration & Environment

### Output Formats

**Configure different output formats for different environments.**

```python
# examples/03_output_formats.py
from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings

# JSON format (production)
json_settings = LoggingSettings(format="json")
configure_logging(settings=json_settings)

log.info("JSON format example", user_id="123", action="login")

# Pretty format (development)
pretty_settings = LoggingSettings(format="pretty")
configure_logging(settings=pretty_settings)

log.info("Pretty format example", user_id="123", action="login")

# Auto format (detects TTY)
auto_settings = LoggingSettings(format="auto")
configure_logging(settings=auto_settings)

log.info("Auto format example", user_id="123", action="login")
```

**Output Comparison:**

**JSON Format:**

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "info",
  "event": "JSON format example",
  "user_id": "123",
  "action": "login"
}
```

**Pretty Format:**

```
2024-01-15 10:30:45.123 | INFO | JSON format example | user_id=123 action=login
```

### Logging Levels

**Configure and use different logging levels effectively.**

```python
# examples/04_logging_levels.py
from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings

# Configure for development (all levels)
dev_settings = LoggingSettings(level="DEBUG")
configure_logging(settings=dev_settings)

# All levels will be logged
log.debug("Debug information", debug_data="some debug info")
log.info("General information", user_count=100)
log.warning("Warning message", deprecated_feature="old_api")
log.error("Error occurred", error_code=500, error_message="timeout")

# Configure for production (INFO and above)
prod_settings = LoggingSettings(level="INFO")
configure_logging(settings=prod_settings)

# Only INFO, WARNING, ERROR, CRITICAL will be logged
log.debug("This won't be logged in production")
log.info("This will be logged")
log.error("This will be logged")
```

### Queue Configuration

**Configure async logging queue for high-performance applications.**

```python
# examples/09_queue_configuration.py
from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings

# High-performance configuration
settings = LoggingSettings(
    queue_enabled=True,
    queue_size=10000,        # Large queue for bursts
    batch_size=100,          # Batch for efficiency
    batch_timeout=0.5,       # Flush every 500ms
    overflow_strategy="drop" # Drop logs if queue full
)

configure_logging(settings=settings)

# These logs will be processed asynchronously
for i in range(1000):
    log.info("High-volume logging", iteration=i, timestamp=time.time())
```

### Overflow Strategies

**Handle queue overflow in different scenarios.**

```python
# examples/10_overflow_strategies.py
from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings

# Drop strategy (high performance, may lose logs)
drop_settings = LoggingSettings(
    queue_enabled=True,
    queue_size=100,
    overflow_strategy="drop"
)

# Block strategy (guaranteed delivery, may block app)
block_settings = LoggingSettings(
    queue_enabled=True,
    queue_size=100,
    overflow_strategy="block"
)

# Sample strategy (keep percentage under load)
sample_settings = LoggingSettings(
    queue_enabled=True,
    queue_size=100,
    overflow_strategy="sample"
)
```

---

## Security & Compliance

### PII Redaction

**Automatically redact sensitive data from logs.**

```python
# examples/20_automatic_pii_redaction.py
from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings

# Configure automatic PII redaction
settings = LoggingSettings(
    redact_patterns=[
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
        r'\b\d{3}-\d{3}-\d{4}\b',  # Phone
        r'\b\d{4}-\d{4}-\d{4}-\d{4}\b',  # Credit card
    ],
    redact_fields=["password", "token", "secret_key"],
    redact_replacement="REDACTED",
    redact_level="INFO"
)

configure_logging(settings=settings)

# Sensitive data will be automatically redacted
log.info("User registration",
         email="user@example.com",           # Will be redacted
         phone="555-123-4567",              # Will be redacted
         password="secret123",               # Will be redacted
         user_id="123",                      # Will not be redacted
         ip_address="192.168.1.100")        # Will not be redacted
```

**Output:**

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "info",
  "event": "User registration",
  "email": "REDACTED",
  "phone": "REDACTED",
  "password": "REDACTED",
  "user_id": "123",
  "ip_address": "192.168.1.100"
}
```

### Security Logging

**Comprehensive security and audit logging patterns.**

```python
# examples/16_security_logging.py
from fastapi import FastAPI, Depends, HTTPException
from fapilog import configure_logging, log
from fapilog._internal.context import bind_context

app = FastAPI()
configure_logging(app=app)

# Security event logging
def log_security_event(event_type: str, user_id: str, details: dict):
    log.warning("Security event",
                event_type=event_type,
                user_id=user_id,
                ip_address=request.client.host,
                user_agent=request.headers.get("user-agent"),
                **details)

@app.post("/auth/login")
async def login(credentials: dict):
    try:
        user = await authenticate_user(credentials)

        # Log successful login
        log.info("User login successful",
                 user_id=user.id,
                 login_method="password",
                 ip_address=request.client.host)

        return {"token": generate_token(user)}

    except AuthenticationError:
        # Log failed login attempt
        log.warning("Login failed",
                    attempted_email=credentials.get("email"),
                    ip_address=request.client.host,
                    reason="invalid_credentials")
        raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/users/{user_id}/sensitive-data")
async def process_sensitive_data(user_id: str, data: dict):
    # Log access to sensitive data
    log.info("Sensitive data accessed",
             target_user_id=user_id,
             data_type=data.get("type"),
             access_reason="business_need")

    # Process data...
    return {"status": "processed"}

@app.delete("/users/{user_id}")
async def delete_user(user_id: str, current_user = Depends(get_current_user)):
    # Log user deletion (critical security event)
    log.critical("User account deleted",
                 target_user_id=user_id,
                 deleted_by=current_user.id,
                 deletion_reason="user_request",
                 data_retention_days=30)

    await delete_user_account(user_id)
    return {"status": "deleted"}
```

### Field-Level Redaction

**Selectively redact specific fields while preserving others.**

```python
# examples/19_field_redaction.py
from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings

# Configure field-specific redaction
settings = LoggingSettings(
    redact_fields=[
        "password",
        "token",
        "secret_key",
        "user.credit_card",  # Nested field redaction
        "user.ssn",
        "payment.card_number"
    ],
    redact_replacement="***REDACTED***",
    redact_level="INFO"
)

configure_logging(settings=settings)

# Log user data with selective redaction
user_data = {
    "user_id": "123",
    "email": "user@example.com",
    "password": "secret123",           # Will be redacted
    "token": "abc123def456",           # Will be redacted
    "user": {
        "name": "John Doe",
        "credit_card": "1234-5678-9012-3456",  # Will be redacted
        "ssn": "123-45-6789"                    # Will be redacted
    },
    "payment": {
        "amount": 99.99,
        "card_number": "9876-5432-1098-7654"   # Will be redacted
    }
}

log.info("User data processed", **user_data)
```

---

## Performance & Monitoring

### Performance Testing

**Test logging performance under load.**

```python
# examples/11_performance_testing.py
import asyncio
import time
from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings

# Configure for performance testing
settings = LoggingSettings(
    queue_enabled=True,
    queue_size=10000,
    batch_size=100,
    batch_timeout=0.1,
    overflow_strategy="drop"
)

configure_logging(settings=settings)

async def performance_test():
    start_time = time.time()
    log_count = 10000

    # Log messages rapidly
    for i in range(log_count):
        log.info("Performance test message",
                 iteration=i,
                 timestamp=time.time())

    # Wait for queue to process
    await asyncio.sleep(2)

    duration = time.time() - start_time
    rate = log_count / duration

    print(f"Logged {log_count} messages in {duration:.2f}s")
    print(f"Rate: {rate:.0f} messages/second")

# Run performance test
asyncio.run(performance_test())
```

### Resource Metrics

**Monitor logging system performance and resource usage.**

```python
# examples/21_metrics_monitoring.py
from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings
from fapilog.monitoring import start_metrics_server, get_metrics_dict

# Enable resource metrics
settings = LoggingSettings(
    enable_resource_metrics=True,
    metrics_enabled=True,
    metrics_prometheus_enabled=True,
    metrics_prometheus_port=8000
)

configure_logging(settings=settings)

# Start metrics server
async def start_monitoring():
    await start_metrics_server(port=8000)
    print("Metrics server started at http://localhost:8000/metrics")

# Get current metrics
def print_metrics():
    metrics = get_metrics_dict()
    print(f"Queue size: {metrics['queue']['size']}")
    print(f"Total events: {metrics['performance']['total_log_events']}")
    print(f"Memory usage: {metrics['performance']['memory_bytes']} bytes")

# Log with resource monitoring
log.info("Application started",
         memory_usage_mb=metrics['performance']['memory_bytes'] / 1024 / 1024,
         cpu_percent=metrics['performance']['cpu_percent'])
```

### Batch Processing

**Optimize logging for batch operations.**

```python
# examples/12_batch_processing.py
import asyncio
from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings

# Configure for batch processing
settings = LoggingSettings(
    queue_enabled=True,
    batch_size=1000,        # Large batches
    batch_timeout=5.0,      # Longer timeout
    queue_size=50000        # Large queue
)

configure_logging(settings=settings)

async def process_batch(items: list):
    batch_id = generate_batch_id()

    log.info("Batch processing started",
             batch_id=batch_id,
             item_count=len(items))

    processed = 0
    errors = 0

    for item in items:
        try:
            await process_item(item)
            processed += 1

            # Log progress every 100 items
            if processed % 100 == 0:
                log.info("Batch progress",
                         batch_id=batch_id,
                         processed=processed,
                         total=len(items),
                         progress_percent=(processed / len(items)) * 100)

        except Exception as e:
            errors += 1
            log.error("Item processing failed",
                      batch_id=batch_id,
                      item_id=item.get("id"),
                      error=str(e))

    # Log batch completion
    log.info("Batch processing completed",
             batch_id=batch_id,
             total_items=len(items),
             processed=processed,
             errors=errors,
             success_rate=(processed / len(items)) * 100)
```

---

## Custom Components

### Custom Enrichers

**Create custom enrichers to add application-specific context.**

```python
# examples/custom_enricher_example.py
from fapilog import configure_logging
from fapilog.enrichers import register_enricher
import os
import psutil

# Custom enricher for environment information
@register_enricher
def environment_enricher(logger, method_name, event_dict):
    """Add environment information to all logs."""
    event_dict["environment"] = os.getenv("ENVIRONMENT", "development")
    event_dict["version"] = os.getenv("APP_VERSION", "1.0.0")
    event_dict["deployment_id"] = os.getenv("DEPLOYMENT_ID")
    return event_dict

# Custom enricher for performance metrics
@register_enricher
def performance_enricher(logger, method_name, event_dict):
    """Add performance metrics to logs."""
    process = psutil.Process()
    event_dict["memory_usage_mb"] = process.memory_info().rss / 1024 / 1024
    event_dict["cpu_percent"] = process.cpu_percent()
    return event_dict

# Custom enricher for tenant context
@register_enricher
def tenant_enricher(logger, method_name, event_dict):
    """Add tenant information from request context."""
    tenant_id = get_current_tenant_id()
    if tenant_id:
        event_dict["tenant_id"] = tenant_id
    return event_dict

# Configure logging with custom enrichers
configure_logging()

# All logs will include custom context
log.info("Application started")
```

**Output:**

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "info",
  "event": "Application started",
  "environment": "production",
  "version": "2.1.0",
  "deployment_id": "deploy-abc123",
  "memory_usage_mb": 256.5,
  "cpu_percent": 12.3,
  "tenant_id": "tenant-xyz789"
}
```

### Custom Sinks

**Create custom sinks for specific output destinations.**

```python
# examples/15_custom_sink.py
import aiohttp
import json
from fapilog import Sink, configure_logging, log

class SlackSink(Sink):
    """Send error logs to Slack."""

    def __init__(self, webhook_url: str, channel: str = "#alerts"):
        self.webhook_url = webhook_url
        self.channel = channel
        self.session = None

    async def start(self):
        """Initialize the sink."""
        self.session = aiohttp.ClientSession()

    async def write(self, event_dict):
        """Send log to Slack if it's an error."""
        if event_dict.get("level") == "error":
            message = {
                "channel": self.channel,
                "text": f"🚨 Error: {event_dict.get('event', 'Unknown error')}",
                "attachments": [{
                    "fields": [
                        {"title": "Trace ID", "value": event_dict.get("trace_id", "N/A")},
                        {"title": "User ID", "value": event_dict.get("user_id", "N/A")},
                        {"title": "Timestamp", "value": event_dict.get("timestamp", "N/A")}
                    ]
                }]
            }

            try:
                await self.session.post(self.webhook_url, json=message)
            except Exception as e:
                print(f"Slack sink error: {e}")

    async def close(self):
        """Clean up resources."""
        if self.session:
            await self.session.close()

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

# Register custom sinks
slack_sink = SlackSink("https://hooks.slack.com/services/YOUR/WEBHOOK/URL")
api_sink = HTTPApiSink("https://api.logs.example.com/ingest", "your-api-key")

configure_logging(sinks=["stdout", slack_sink, api_sink])

# Test custom sinks
log.info("Normal message")  # Goes to stdout only
log.error("Error message")  # Goes to stdout and Slack
```

### Multiple Sinks

**Configure multiple output destinations for different purposes.**

```python
# examples/14_multiple_sinks.py
from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings
from fapilog.sinks.stdout import StdoutSink
from fapilog.sinks.file import FileSink

# Configure multiple sinks
stdout_sink = StdoutSink(pretty=True)  # Pretty output for development
file_sink = FileSink("/var/log/app.log")  # JSON output for production

settings = LoggingSettings(
    level="INFO",
    sinks=[stdout_sink, file_sink]
)

configure_logging(settings=settings)

# Logs will be sent to both stdout and file
log.info("Application started", version="1.0.0")
log.error("Database error", database="postgres", error="connection timeout")

# Different log levels for different sinks
log.debug("Debug info")  # Only goes to stdout in development
log.info("User action", user_id="123", action="login")  # Goes to both
log.error("System error", error_code=500)  # Goes to both
```

---

## Advanced Patterns

### Trace Propagation

**Propagate trace IDs across service boundaries.**

```python
# examples/17_trace_propagation.py
import httpx
from fastapi import FastAPI
from fapilog import configure_logging, log, get_current_trace_id
from fapilog.settings import LoggingSettings

app = FastAPI()

# Enable httpx trace propagation
settings = LoggingSettings(
    enable_httpx_trace_propagation=True,
    trace_id_header="X-Request-ID"
)

configure_logging(settings=settings, app=app)

@app.get("/api/data")
async def get_data():
    trace_id = get_current_trace_id()
    log.info("Fetching external data", trace_id=trace_id)

    # Outgoing request will automatically include trace ID
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.external-service.com/data",
            headers={"X-Request-ID": trace_id}  # Automatically added
        )

    log.info("External data received",
             trace_id=trace_id,
             status_code=response.status_code)

    return response.json()

@app.get("/api/users/{user_id}")
async def get_user(user_id: str):
    trace_id = get_current_trace_id()

    # Make multiple service calls with trace correlation
    async with httpx.AsyncClient() as client:
        # User service call
        user_response = await client.get(
            f"https://user-service.com/users/{user_id}",
            headers={"X-Request-ID": trace_id}
        )

        # Profile service call
        profile_response = await client.get(
            f"https://profile-service.com/profiles/{user_id}",
            headers={"X-Request-ID": trace_id}
        )

    log.info("User data aggregated",
             trace_id=trace_id,
             user_id=user_id,
             services_called=["user-service", "profile-service"])

    return {
        "user": user_response.json(),
        "profile": profile_response.json()
    }
```

### User Context Enrichment

**Automatically enrich logs with user context.**

```python
# examples/18_user_context_enrichment.py
from fastapi import FastAPI, Depends, HTTPException
from fapilog import configure_logging, log
from fapilog.enrichers import create_user_dependency
from fapilog._internal.context import bind_context

app = FastAPI()
configure_logging(app=app)

# User model
class User:
    def __init__(self, id: str, email: str, role: str):
        self.id = id
        self.email = email
        self.role = role

# Mock user database
USERS_DB = {
    "token-123": User("user-123", "alice@example.com", "admin"),
    "token-456": User("user-456", "bob@example.com", "user"),
}

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get current user from token."""
    if token in USERS_DB:
        return USERS_DB[token]
    raise HTTPException(status_code=401, detail="Invalid token")

# Create user dependency with automatic context binding
get_current_user_with_context = create_user_dependency(get_current_user)

@app.get("/api/protected")
async def protected_route(current_user = Depends(get_current_user_with_context)):
    # User context is automatically added to all logs
    log.info("Protected route accessed")
    log.warning("Permission check", resource="/admin")

    return {"message": "Access granted", "user_id": current_user.id}

@app.post("/api/users/{user_id}/profile")
async def update_profile(user_id: str, profile_data: dict,
                        current_user = Depends(get_current_user_with_context)):
    # All logs include user context
    log.info("Profile update started",
             target_user_id=user_id,
             profile_fields=len(profile_data))

    if current_user.role != "admin" and current_user.id != user_id:
        log.warning("Unauthorized profile update attempt",
                    target_user_id=user_id,
                    attempted_by=current_user.id)
        raise HTTPException(status_code=403, detail="Not authorized")

    # Update profile...
    log.info("Profile updated successfully",
             target_user_id=user_id,
             updated_fields=list(profile_data.keys()))

    return {"status": "updated"}

# Manual context binding for background tasks
@app.post("/api/batch/process")
async def process_batch(batch_data: list,
                       current_user = Depends(get_current_user_with_context)):
    # Bind additional context for this operation
    bind_context(
        operation_id=generate_operation_id(),
        batch_size=len(batch_data),
        operation_type="batch_process"
    )

    log.info("Batch processing started")

    # Process items...
    for item in batch_data:
        log.info("Processing item", item_id=item.get("id"))
        # Process item...

    log.info("Batch processing completed")
    return {"status": "completed"}
```

### Container Architecture

**Use multiple isolated logging containers for different components.**

```python
# examples/22_container_architecture.py
from fapilog.container import LoggingContainer
from fapilog.settings import LoggingSettings

# Service A container (high-volume logging)
service_a_settings = LoggingSettings(
    level="INFO",
    sinks=["stdout", "file:///var/log/service-a.log"],
    queue_enabled=True,
    queue_size=10000,
    batch_size=100,
    overflow_strategy="drop"
)

service_a_container = LoggingContainer(service_a_settings)
service_a_logger = service_a_container.configure()

# Service B container (debug logging)
service_b_settings = LoggingSettings(
    level="DEBUG",
    sinks=["stdout", "file:///var/log/service-b.log"],
    queue_enabled=False,  # Synchronous for debugging
    enable_resource_metrics=True
)

service_b_container = LoggingContainer(service_b_settings)
service_b_logger = service_b_container.configure()

# Independent logging
service_a_logger.info("Service A message", component="service-a")
service_b_logger.debug("Service B debug", component="service-b")

# Clean shutdown
service_a_container.shutdown_sync()
service_b_container.shutdown_sync()
```

---

## Recipe Categories

### 🚀 Quick Start Recipes

- **Basic Setup**: Minimal configuration for immediate use
- **FastAPI Integration**: Automatic middleware and trace correlation
- **Environment Configuration**: Different settings for dev/prod

### 🔒 Security Recipes

- **PII Redaction**: Automatic sensitive data masking
- **Security Logging**: Audit trails and compliance
- **Field-Level Redaction**: Selective data protection

### ⚡ Performance Recipes

- **Queue Configuration**: Async logging for high throughput
- **Batch Processing**: Optimized for bulk operations
- **Resource Monitoring**: Track logging system performance

### 🔧 Custom Components

- **Custom Enrichers**: Add application-specific context
- **Custom Sinks**: Integrate with external systems
- **Multiple Sinks**: Different outputs for different purposes

### 🔗 Advanced Patterns

- **Trace Propagation**: Distributed tracing across services
- **User Context**: Automatic user information enrichment
- **Container Architecture**: Isolated logging for microservices

---

## Best Practices

### 1. **Structured Logging**

- Always use key-value pairs for log fields
- Be consistent with field names across your application
- Use descriptive event messages

### 2. **Performance**

- Enable async queue for high-volume applications
- Use appropriate batch sizes for your workload
- Monitor queue performance and adjust settings

### 3. **Security**

- Always redact sensitive data in production
- Use field-level redaction for fine-grained control
- Log security events with appropriate detail

### 4. **Monitoring**

- Enable resource metrics for production systems
- Use Prometheus integration for observability
- Set up alerts for logging system issues

### 5. **Development**

- Use pretty format for local development
- Enable debug logging for troubleshooting
- Test custom components thoroughly

---

## Next Steps

- **Explore the full API**: [API Reference](api-reference.md)
- **Learn core concepts**: [Core Concepts](core-concepts.md)
- **Configure for production**: [Configuration Guide](config.md)
- **Troubleshoot issues**: [Troubleshooting](troubleshooting.md)

Each example includes complete, runnable code that you can copy and adapt for your specific use case. The examples demonstrate real-world patterns and best practices for using Fapilog effectively.
