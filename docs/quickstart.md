# Quickstart Tutorial

**Get up and running with Fapilog in under 5 minutes!**

This tutorial will guide you through installing, configuring, and using Fapilog in a FastAPI application. By the end, you'll have structured logging working with automatic context enrichment.

**See also:** [User Guide](user-guide.md), [API Reference](api-reference.md), [Configuration Guide](config.md)

---

## Prerequisites

- Python 3.8+
- FastAPI (optional, but recommended)
- Basic understanding of Python logging

---

## Step 1: Installation

Install Fapilog using pip:

```bash
pip install fapilog
```

For development with FastAPI:

```bash
pip install fapilog[fastapi]
```

---

## Step 2: Basic Setup

Create a simple Python script to test Fapilog:

```python
# basic_setup.py
from fapilog import configure_logging, log

# Configure logging with defaults
configure_logging()

# Start logging
log.info("Application started", version="1.0.0")
log.warning("Deprecated feature used", feature="old_api")
log.error("Database connection failed", database="postgres")
```

Run the script:

```bash
python basic_setup.py
```

**Expected Output:**

```json
{"timestamp": "2024-01-15T10:30:45.123Z", "level": "info", "event": "Application started", "hostname": "your-host", "pid": 12345, "version": "1.0.0"}
{"timestamp": "2024-01-15T10:30:45.124Z", "level": "warning", "event": "Deprecated feature used", "hostname": "your-host", "pid": 12345, "feature": "old_api"}
{"timestamp": "2024-01-15T10:30:45.125Z", "level": "error", "event": "Database connection failed", "hostname": "your-host", "pid": 12345, "database": "postgres"}
```

**What happened:**

- ✅ Structured JSON logging enabled
- ✅ Automatic timestamp and log level
- ✅ Hostname and process ID added
- ✅ Pretty console output in development
- ✅ Async-safe logging with background queue

---

## Step 3: FastAPI Integration

Create a FastAPI application with Fapilog:

```python
# fastapi_app.py
from fastapi import FastAPI, HTTPException
from fapilog import configure_logging, log

# Create FastAPI app
app = FastAPI(title="My API", version="1.0.0")

# Configure logging with FastAPI integration
configure_logging(app=app)

@app.get("/")
async def root():
    log.info("Root endpoint accessed")
    return {"message": "Hello World"}

@app.get("/users/{user_id}")
async def get_user(user_id: str):
    log.info("User requested", user_id=user_id, endpoint="/users/{user_id}")

    if user_id == "admin":
        log.warning("Admin user accessed", user_id=user_id)
        return {"user_id": user_id, "role": "admin"}

    return {"user_id": user_id, "role": "user"}

@app.get("/error")
async def trigger_error():
    log.error("Error endpoint accessed", error_type="test")
    raise HTTPException(status_code=500, detail="Test error")
```

Run the FastAPI app:

```bash
uvicorn fastapi_app:app --reload
```

Visit `http://localhost:8000/` and check the logs. You'll see:

- **Automatic request correlation** - Each request gets a unique trace ID
- **Structured logging** - All log fields are JSON-structured
- **Context enrichment** - Request path, method, and user info added
- **Error tracking** - Exceptions are automatically logged

---

## Step 4: Environment Configuration

Create a `.env` file for configuration:

```bash
# .env
FAPILOG_LEVEL=INFO
FAPILOG_FORMAT=json
FAPILOG_QUEUE_ENABLED=true
FAPILOG_SINKS=stdout,file
FAPILOG_FILE_PATH=app.log
```

Update your application to use environment variables:

```python
# config_app.py
import os
from fastapi import FastAPI
from fapilog import configure_logging, log

app = FastAPI()

# Configure with environment variables
configure_logging()

@app.get("/")
async def root():
    log.info("Application accessed",
             environment=os.getenv("ENVIRONMENT", "development"),
             version="1.0.0")
    return {"status": "ok"}
```

---

## Step 5: Advanced Features

### Custom Context Enrichment

```python
from fapilog import configure_logging, log, set_user_context

configure_logging()

# Set user context for the current request
set_user_context(user_id="123", session_id="abc123")

log.info("User action", action="login", duration_ms=45.2)
```

### Structured Logging with Multiple Fields

```python
log.info(
    "API request processed",
    endpoint="/api/users",
    method="GET",
    status_code=200,
    duration_ms=45.2,
    user_id="123",
    request_size_bytes=1024,
    response_size_bytes=2048
)
```

### Error Handling with Context

```python
try:
    # Your application logic
    result = some_operation()
    log.info("Operation successful", result_type=type(result).__name__)
except Exception as e:
    log.error("Operation failed",
              error=str(e),
              error_type=type(e).__name__,
              operation="some_operation")
    raise
```

---

## What's Next?

### Learn More

- **User Guide**: [Complete tutorials and advanced features](user-guide.md)
- **API Reference**: [Complete API documentation](api-reference.md)
- **Configuration**: [Environment variables and settings](config.md)

### Explore Examples

- **Basic Setup**: [examples/01_basic_setup.py](../examples/01_basic_setup.py)
- **FastAPI Integration**: [examples/05_fastapi_basic.py](../examples/05_fastapi_basic.py)
- **Advanced Configuration**: [examples/09_queue_configuration.py](../examples/09_queue_configuration.py)

### Production Deployment

- **Environment Configuration**: [User Guide - Production](user-guide.md#production-deployment)
- **Performance Tuning**: [User Guide - Performance](user-guide.md#performance-tuning)
- **Monitoring Integration**: [User Guide - Monitoring](user-guide.md#monitoring-integration)

---

## Troubleshooting

### Common Issues

**Q: Logs not appearing in console?**
A: Check that `FAPILOG_SINKS` includes `stdout` and `FAPILOG_LEVEL` is set appropriately.

**Q: Performance issues with high log volume?**
A: Enable the async queue with `FAPILOG_QUEUE_ENABLED=true` and adjust `FAPILOG_QUEUE_SIZE`.

**Q: Missing trace IDs in logs?**
A: Ensure you're using `configure_logging(app=app)` for FastAPI applications.

For more troubleshooting help, see the [Troubleshooting Guide](troubleshooting.md).

---

## Quick Reference

### Basic Usage

```python
from fapilog import configure_logging, log

configure_logging()
log.info("Message", field1="value1", field2="value2")
```

### FastAPI Integration

```python
from fastapi import FastAPI
from fapilog import configure_logging

app = FastAPI()
configure_logging(app=app)
```

### Environment Variables

```bash
FAPILOG_LEVEL=INFO
FAPILOG_FORMAT=json
FAPILOG_QUEUE_ENABLED=true
FAPILOG_SINKS=stdout,file
```

For complete configuration options, see the [Configuration Guide](config.md).
