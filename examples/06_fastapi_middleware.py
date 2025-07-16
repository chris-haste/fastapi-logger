#!/usr/bin/env python3
"""
Example 6: FastAPI Middleware Integration

This example demonstrates the TraceIDMiddleware integration and shows how
trace IDs, span IDs, and request metadata are automatically captured and
propagated through the logging system.
"""

import asyncio
import time
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings


def create_app() -> FastAPI:
    """Create a FastAPI application with middleware integration."""

    # Configure logging with middleware support
    settings = LoggingSettings(
        level="INFO",
        json_console="pretty",  # Pretty output for development
        queue_enabled=False,  # Disable queue for simpler example
    )

    # Configure logging - this automatically registers TraceIDMiddleware
    configure_logging(settings=settings)

    # Create FastAPI app
    app = FastAPI(
        title="fapilog Middleware Example",
        description="Example showing trace ID middleware and request correlation",
        version="1.0.0",
    )

    # Log application startup
    log.info(
        "FastAPI application with middleware starting",
        app_name="fapilog-middleware-example",
        version="1.0.0",
        middleware_enabled=True,
    )

    return app


# Create the FastAPI application
app = create_app()


@app.get("/")
async def root():
    """Root endpoint - trace ID will be automatically added to logs."""
    log.info("Root endpoint accessed")
    return {"message": "Hello from fapilog middleware example"}


@app.get("/trace")
async def trace_example():
    """Endpoint to demonstrate trace ID propagation."""
    log.info("Trace example endpoint accessed")

    # Simulate some work
    await asyncio.sleep(0.1)

    log.info("Processing trace example", step="validation")

    await asyncio.sleep(0.05)

    log.info("Trace example completed", step="completion")

    return {
        "message": "Trace example completed",
        "note": "Check the logs to see trace_id and span_id fields",
    }


@app.get("/nested")
async def nested_calls():
    """Endpoint that demonstrates nested function calls with trace propagation."""
    log.info("Nested calls endpoint accessed")

    # Call helper functions that also log
    result1 = await helper_function_1()
    result2 = await helper_function_2()

    log.info("Nested calls completed", result1=result1, result2=result2)

    return {"message": "Nested calls completed", "results": [result1, result2]}


async def helper_function_1() -> str:
    """Helper function that logs with trace context."""
    log.info("Helper function 1 called")
    await asyncio.sleep(0.05)
    log.info("Helper function 1 completed")
    return "helper_1_result"


async def helper_function_2() -> str:
    """Another helper function that logs with trace context."""
    log.info("Helper function 2 called")
    await asyncio.sleep(0.03)
    log.info("Helper function 2 completed")
    return "helper_2_result"


@app.get("/headers")
async def check_headers(request: Request):
    """Endpoint to check request headers and demonstrate header propagation."""
    # Log request headers (some may be redacted for security)
    log.info(
        "Headers endpoint accessed",
        user_agent=request.headers.get("user-agent", "unknown"),
        content_type=request.headers.get("content-type", "none"),
    )

    return {
        "message": "Headers logged",
        "user_agent": request.headers.get("user-agent", "unknown"),
        "content_type": request.headers.get("content-type", "none"),
    }


@app.post("/data")
async def process_data(request: Request):
    """Endpoint that processes request data and logs body size."""
    # Get request body
    body = await request.json()

    log.info(
        "Data processing started",
        data_size=len(str(body)),
        data_keys=list(body.keys()) if isinstance(body, dict) else "not_dict",
    )

    # Simulate processing
    await asyncio.sleep(0.1)

    # Process the data
    processed_data = {"original": body, "processed": True, "timestamp": time.time()}

    log.info(
        "Data processing completed",
        original_size=len(str(body)),
        processed_size=len(str(processed_data)),
    )

    return processed_data


@app.get("/error-with-trace")
async def error_with_trace():
    """Endpoint that raises an error to show trace ID in error logs."""
    log.error(
        "About to raise an error - this is expected",
        error_type="simulated_error",
        step="before_error",
    )

    # This will raise an error, but the trace ID will still be in the logs
    raise HTTPException(status_code=500, detail="Simulated error with trace ID")


@app.get("/slow-with-trace")
async def slow_with_trace():
    """Slow endpoint to demonstrate timing with trace IDs."""
    log.info("Slow operation started")

    # Simulate slow operation
    await asyncio.sleep(2)

    log.info("Slow operation completed")

    return {"message": "Slow operation completed - check logs for timing"}


@app.get("/correlation")
async def correlation_example():
    """Endpoint to demonstrate request correlation across multiple logs."""
    request_id = f"req_{int(time.time())}"

    log.info("Correlation example started", request_id=request_id, step="start")

    # Simulate multiple operations
    for i in range(3):
        await asyncio.sleep(0.1)
        log.info(
            f"Operation {i+1} completed", request_id=request_id, step=f"operation_{i+1}"
        )

    log.info("Correlation example completed", request_id=request_id, step="complete")

    return {
        "message": "Correlation example completed",
        "request_id": request_id,
        "note": "All logs for this request will have the same trace_id",
    }


# Custom middleware to demonstrate additional header handling
@app.middleware("http")
async def custom_header_middleware(request: Request, call_next):
    """Custom middleware to add additional headers."""
    # Add custom header
    request.state.custom_header = "custom_value"

    # Process the request
    response = await call_next(request)

    # Add custom response header
    response.headers["X-Custom-Header"] = "custom_response_value"

    return response


def main():
    """Run the FastAPI application."""
    import uvicorn

    print("=== FastAPI Middleware Integration Example ===")
    print("This example demonstrates:")
    print("✅ Automatic trace ID generation")
    print("✅ Span ID for each request")
    print("✅ Request/response timing")
    print("✅ Header propagation")
    print("✅ Body size tracking")
    print("✅ Error correlation")
    print()
    print("Available endpoints:")
    print("  GET  /              - Basic endpoint")
    print("  GET  /trace         - Trace ID demonstration")
    print("  GET  /nested        - Nested function calls")
    print("  GET  /headers       - Header logging")
    print("  POST /data          - Request body processing")
    print("  GET  /error-with-trace - Error with trace ID")
    print("  GET  /slow-with-trace  - Slow operation timing")
    print("  GET  /correlation   - Request correlation")
    print()
    print("Start the server with: uvicorn examples.06_fastapi_middleware:app --reload")
    print("Then visit: http://localhost:8000/docs")
    print()
    print("Key features to observe in logs:")
    print("✅ trace_id: Unique identifier for each request")
    print("✅ span_id: Unique identifier for each request span")
    print("✅ latency_ms: Request processing time")
    print("✅ req_bytes: Request body size")
    print("✅ res_bytes: Response body size")
    print("✅ status_code: HTTP status code")
    print("✅ user_agent: User agent string")


if __name__ == "__main__":
    main()
