#!/usr/bin/env python3
"""
Example 5: FastAPI Basic Integration

This example demonstrates how to integrate fapilog with a FastAPI application.
It shows basic setup, middleware integration, and structured logging in API endpoints.
"""

import asyncio
import time
from typing import Dict, List

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


def main():
    """Run the FastAPI application."""
    import uvicorn

    print("=== FastAPI Basic Integration Example ===")
    print("Starting FastAPI application with fapilog...")
    print("Available endpoints:")
    print("  GET  /         - Root endpoint")
    print("  GET  /users    - List users")
    print("  GET  /users/{id} - Get specific user")
    print("  POST /users    - Create user")
    print("  GET  /health   - Health check")
    print("  GET  /slow     - Slow endpoint")
    print("  GET  /error    - Error endpoint")
    print()
    print("Start the server with: uvicorn examples.05_fastapi_basic:app --reload")
    print("Then visit: http://localhost:8000/docs")
    print()
    print("Key features demonstrated:")
    print("✅ FastAPI integration with middleware")
    print("✅ Structured logging in endpoints")
    print("✅ Error handling and logging")
    print("✅ Request/response correlation")
    print("✅ Automatic trace ID generation")


if __name__ == "__main__":
    main()
