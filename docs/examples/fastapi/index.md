# FastAPI Integration Examples

**Integrate Fapilog with FastAPI applications**

This section covers FastAPI-specific patterns for structured logging, including automatic middleware, trace correlation, and error handling.

---

## 📚 What You'll Learn

- **Basic Integration** - Get FastAPI + Fapilog working together
- **Custom Middleware** - Advanced request/response logging
- **Error Handling** - Structured error logging and reporting
- **Advanced Patterns** - User context, structured endpoints

---

## 🚀 Examples

### 05 - FastAPI Basic Integration

**Integrate Fapilog with FastAPI for automatic request logging**

```python
#!/usr/bin/env python3
"""
Example 5: FastAPI Basic Integration

This example demonstrates how to integrate fapilog with a FastAPI application.
It shows basic setup, middleware integration, and structured logging in API endpoints.
"""

import asyncio
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings


def create_app() -> FastAPI:
    """Create a FastAPI application with fapilog integration."""

    # Configure logging with FastAPI integration
    settings = LoggingSettings(
        level="INFO",
        json_console="pretty",  # Pretty output for development
        queue_enabled=False,  # Disable queue for simpler example
    )

    # Configure logging and get the app instance
    configure_logging(settings=settings)

    # Create FastAPI app
    app = FastAPI(
        title="fapilog Example API",
        description="Example FastAPI application with structured logging",
        version="1.0.0",
    )

    # Log application startup
    log.info(
        "FastAPI application starting",
        app_name="fapilog-example",
        version="1.0.0",
        environment="development",
    )

    return app


# Create the FastAPI application
app = create_app()


@app.get("/")
async def root():
    """Root endpoint with basic logging."""
    log.info("Root endpoint accessed")
    return {"message": "Hello from fapilog example API"}


@app.get("/users")
async def get_users():
    """Get users endpoint with structured logging."""
    # Simulate some processing
    await asyncio.sleep(0.1)

    # Log the request with structured data
    log.info("Users endpoint accessed", endpoint="/users", method="GET", user_count=3)

    users = [
        {"id": 1, "name": "Alice", "email": "alice@example.com"},
        {"id": 2, "name": "Bob", "email": "bob@example.com"},
        {"id": 3, "name": "Charlie", "email": "charlie@example.com"},
    ]

    return {"users": users}


@app.get("/users/{user_id}")
async def get_user(user_id: int):
    """Get specific user with error handling and logging."""
    log.info(
        "User detail requested",
        endpoint=f"/users/{user_id}",
        method="GET",
        user_id=user_id,
    )

    # Simulate database lookup
    await asyncio.sleep(0.05)

    if user_id == 1:
        user = {"id": 1, "name": "Alice", "email": "alice@example.com"}
        log.info("User found", user_id=user_id, user_name=user["name"])
        return user
    elif user_id == 2:
        user = {"id": 2, "name": "Bob", "email": "bob@example.com"}
        log.info("User found", user_id=user_id, user_name=user["name"])
        return user
    else:
        log.warning("User not found", user_id=user_id, error="user_not_found")
        raise HTTPException(status_code=404, detail="User not found")


@app.post("/users")
async def create_user(request: Request):
    """Create user endpoint with request body logging."""
    # Get request body
    body = await request.json()

    log.info(
        "User creation requested", endpoint="/users", method="POST", user_data=body
    )

    # Simulate validation
    if "name" not in body or "email" not in body:
        log.error(
            "Invalid user data",
            endpoint="/users",
            method="POST",
            error="missing_required_fields",
            provided_fields=list(body.keys()),
        )
        raise HTTPException(status_code=400, detail="Name and email are required")

    # Simulate database operation
    await asyncio.sleep(0.1)

    new_user = {"id": 4, "name": body["name"], "email": body["email"]}

    log.info(
        "User created successfully",
        endpoint="/users",
        method="POST",
        user_id=new_user["id"],
        user_name=new_user["name"],
    )

    return new_user


@app.get("/health")
async def health_check():
    """Health check endpoint with minimal logging."""
    log.info("Health check requested")
    return {"status": "healthy", "timestamp": time.time()}


@app.get("/slow")
async def slow_endpoint():
    """Slow endpoint to demonstrate timing logs."""
    log.info("Slow endpoint started")

    # Simulate slow operation
    await asyncio.sleep(2)

    log.info("Slow endpoint completed")
    return {"message": "Slow operation completed"}


@app.get("/error")
async def error_endpoint():
    """Endpoint that always raises an error."""
    log.error(
        "Error endpoint accessed - this is expected",
        endpoint="/error",
        method="GET",
        error_type="simulated_error",
    )

    raise HTTPException(status_code=500, detail="This is a simulated error")


# Custom exception handler to log errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with logging."""
    log.error(
        "Unhandled exception occurred",
        endpoint=str(request.url.path),
        method=request.method,
        error=str(exc),
        error_type=type(exc).__name__,
    )

    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


if __name__ == "__main__":
    print("Start the server with: uvicorn example:app --reload")
    print("Then visit: http://localhost:8000/docs")
```

**Automatic Features:**

- ✅ Request correlation with trace IDs
- ✅ Request/response metadata capture
- ✅ Performance timing
- ✅ Response headers with trace info

**Run the Server:**

```bash
uvicorn example:app --reload
# Visit: http://localhost:8000/docs
```

---

### 06 - FastAPI Custom Middleware

**Enhanced FastAPI integration with custom middleware**

```python
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import time

from fapilog import configure_logging, log

app = FastAPI()
configure_logging()

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

**Key Features:**

- ✅ Custom request/response middleware
- ✅ Performance timing
- ✅ Error context capture
- ✅ Global exception handling

---

### 07 - FastAPI Error Handling

**Comprehensive error handling and logging in FastAPI**

```python
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fapilog import configure_logging, log

app = FastAPI()
configure_logging()

class BusinessLogicError(Exception):
    """Custom business logic error."""
    def __init__(self, message: str, error_code: str):
        self.message = message
        self.error_code = error_code
        super().__init__(message)

@app.exception_handler(BusinessLogicError)
async def business_logic_error_handler(request: Request, exc: BusinessLogicError):
    """Handle business logic errors with structured logging."""
    log.warning("Business logic error",
                endpoint=str(request.url.path),
                method=request.method,
                error_code=exc.error_code,
                error_message=exc.message)

    return JSONResponse(
        status_code=400,
        content={"error_code": exc.error_code, "message": exc.message}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with logging."""
    log.warning("HTTP exception",
                endpoint=str(request.url.path),
                method=request.method,
                status_code=exc.status_code,
                detail=exc.detail)

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.get("/api/users/{user_id}")
async def get_user(user_id: int):
    log.info("User lookup requested", user_id=user_id)

    if user_id < 1:
        raise BusinessLogicError("Invalid user ID", "INVALID_USER_ID")

    if user_id > 1000:
        log.error("User ID out of range", user_id=user_id, max_id=1000)
        raise HTTPException(status_code=404, detail="User not found")

    log.info("User found", user_id=user_id)
    return {"id": user_id, "name": f"User {user_id}"}
```

**Key Features:**

- ✅ Custom exception types
- ✅ Structured error responses
- ✅ Error context preservation
- ✅ Client error vs server error handling

---

### 08 - FastAPI Advanced Patterns

**User context, dependency injection, and structured endpoints**

```python
from fastapi import FastAPI, Depends, HTTPException
from fapilog import configure_logging, log
from fapilog._internal.context import bind_context

app = FastAPI()
configure_logging()

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

async def get_current_user(token: str = None):
    """Get current user from token."""
    if token and token in USERS_DB:
        user = USERS_DB[token]
        # Bind user context to all subsequent logs
        bind_context(user_id=user.id, user_role=user.role, user_email=user.email)
        return user
    raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/api/protected")
async def protected_route(current_user = Depends(get_current_user)):
    # User context is automatically added to all logs
    log.info("Protected route accessed")
    log.warning("Permission check", resource="/admin")

    return {"message": "Access granted", "user_id": current_user.id}

@app.post("/api/users/{user_id}/profile")
async def update_profile(user_id: str, profile_data: dict,
                        current_user = Depends(get_current_user)):
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
```

**Key Features:**

- ✅ User context enrichment
- ✅ Dependency injection patterns
- ✅ Background task logging
- ✅ Business logic logging

---

## 🎯 Integration Patterns

### **Basic Integration**

```python
# Automatic middleware and trace correlation
from fapilog import configure_logging
configure_logging()  # Add to your FastAPI app
```

### **Custom Middleware**

```python
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    # Custom request/response logging
    pass
```

### **User Context**

```python
async def get_current_user(token: str = Depends(oauth2_scheme)):
    user = await verify_token(token)
    bind_context(user_id=user.id, user_role=user.role)
    return user
```

---

## 🎯 Next Steps

### 🏭 **Production Deployment**

- **[Production Examples](../production/index.md)** - Queue configuration, performance optimization
- **[Configuration Guide](../../config.md)** - Production settings

### 🔒 **Security & Compliance**

- **[Advanced Patterns](../advanced/index.md)** - Security logging, PII redaction, trace propagation

### 🚀 **Custom Components**

- **[Sink Development](../sinks/index.md)** - Send logs to custom destinations

---

## 💡 FastAPI Best Practices

1. **Use App Integration** - `configure_logging()` for automatic middleware
2. **Bind User Context** - Add user info to all logs in a request
3. **Structure Errors** - Use consistent error logging patterns
4. **Trace Requests** - Leverage automatic trace ID correlation
5. **Monitor Performance** - Log request timing and performance metrics

Ready for production? Check out the [production examples](../production/index.md)!
