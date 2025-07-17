#!/usr/bin/env python3
"""
Example 17: Trace ID Propagation and Correlation

This example demonstrates the trace propagation features introduced in
Story 6.2:
- get_current_trace_id() API function
- Custom trace header configuration
- httpx automatic trace propagation (opt-in)
- Cross-service request correlation

Run this example to see trace IDs automatically propagating between services
and being accessible programmatically.
"""

import asyncio

import uvicorn
from fastapi import FastAPI

# Optional: Install httpx for trace propagation demo
try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    print("⚠️  httpx not installed. Install with: pip install httpx")
    print("   Some trace propagation features will be simulated.")

from fapilog import configure_logging, get_current_trace_id, log
from fapilog.settings import LoggingSettings


def create_app() -> FastAPI:
    """Create a FastAPI application with trace propagation enabled."""

    # Configure logging with trace propagation features
    settings = LoggingSettings(
        level="INFO",
        json_console="pretty",  # Pretty output for development
        queue_enabled=False,  # Disable queue for simpler example
        # Story 6.2 Features:
        trace_id_header="X-Custom-Trace-ID",  # Custom header name
        enable_httpx_trace_propagation=True,  # Enable httpx propagation
    )

    app = FastAPI(
        title="Trace Propagation Example",
        description="Demonstrating trace ID propagation across services",
        version="1.0.0",
    )

    # Configure logging with the app - this registers middleware automatically
    configure_logging(settings=settings, app=app)

    return app


# Create the FastAPI app
app = create_app()


@app.get("/")
async def root():
    """Root endpoint demonstrating basic trace ID access."""

    # Story 6.2: Access current trace ID programmatically
    current_trace = get_current_trace_id()

    log.info(
        "Root endpoint accessed",
        endpoint="/",
        trace_id_from_api=current_trace,
        example_feature="get_current_trace_id",
    )

    return {
        "message": "Trace Propagation Example Service",
        "trace_id": current_trace,
        "features": [
            "get_current_trace_id() API",
            "Custom trace headers",
            "httpx automatic propagation",
            "Cross-service correlation",
        ],
    }


@app.get("/status/{service_name}")
async def service_status(service_name: str):
    """Endpoint that demonstrates accessing trace ID for business logic."""

    # Get current trace ID for correlation
    trace_id = get_current_trace_id()

    log.info(
        "Service status check requested",
        service=service_name,
        trace_id=trace_id,
        business_context="status_check",
    )

    # Simulate some business logic that uses trace ID
    if trace_id:
        # Log with trace ID for debugging/audit purposes
        log.info(
            "Performing health check",
            service=service_name,
            trace_correlation=trace_id,
            check_type="health",
        )

        status = "healthy" if service_name != "broken-service" else "unhealthy"

        log.info(
            "Health check completed",
            service=service_name,
            status=status,
            trace_id=trace_id,
        )

        return {
            "service": service_name,
            "status": status,
            "trace_id": trace_id,
            "message": f"Status check for {service_name} completed",
        }
    else:
        log.warning("No trace ID available in context")
        return {"error": "No trace context available"}


@app.get("/call-external/{target_service}")
async def call_external_service(target_service: str):
    """Demonstrates httpx trace propagation to downstream services."""

    trace_id = get_current_trace_id()

    log.info(
        "Making external service call",
        target=target_service,
        trace_id=trace_id,
        propagation="httpx_automatic",
    )

    if not HTTPX_AVAILABLE:
        # Simulate the call if httpx is not available
        log.info(
            "Simulating external call (httpx not available)",
            target=target_service,
            trace_id=trace_id,
            headers_that_would_be_sent={"X-Custom-Trace-ID": trace_id},
        )

        return {
            "simulated": True,
            "target_service": target_service,
            "trace_id": trace_id,
            "message": "Install httpx to see real propagation",
            "would_send_headers": {"X-Custom-Trace-ID": trace_id},
        }

    try:
        # Make an HTTP request - trace ID will be automatically propagated
        # thanks to enable_httpx_trace_propagation=True
        async with httpx.AsyncClient() as client:
            # This could be a real service URL in production
            # For demo, we'll call a public API
            target_url = "https://httpbin.org/json"

            log.info(
                "Sending HTTP request with automatic trace propagation",
                url=target_url,
                trace_id=trace_id,
                httpx_patch="enabled",
            )

            # The trace ID will automatically be added to headers
            response = await client.get(target_url, timeout=5.0)

            log.info(
                "External service response received",
                status_code=response.status_code,
                target=target_service,
                trace_id=trace_id,
                response_size=len(response.content),
            )

            return {
                "target_service": target_service,
                "status_code": response.status_code,
                "trace_id": trace_id,
                "message": "Request completed with trace propagation",
                "external_response_size": len(response.content),
            }

    except Exception as e:
        log.error(
            "External service call failed",
            target=target_service,
            error=str(e),
            trace_id=trace_id,
            exc_info=True,
        )

        return {
            "error": f"Failed to call {target_service}",
            "trace_id": trace_id,
            "details": str(e),
        }


@app.get("/simulate-service-chain")
async def simulate_service_chain():
    """Simulates a chain of service calls with trace propagation."""

    trace_id = get_current_trace_id()

    log.info("Starting service chain simulation", trace_id=trace_id, chain_length=3)

    # Simulate calling multiple services
    services = ["user-service", "payment-service", "notification-service"]
    results = []

    for i, service in enumerate(services, 1):
        log.info(
            f"Calling service {i} in chain",
            service=service,
            step=i,
            total_steps=len(services),
            trace_id=trace_id,
        )

        # Simulate service call delay
        await asyncio.sleep(0.1)

        # In a real scenario, this would be an HTTP call to another service
        # The trace_id would be automatically propagated via httpx

        log.info(
            f"Service {i} responded",
            service=service,
            step=i,
            response_time_ms=100,
            trace_id=trace_id,
        )

        results.append(
            {"service": service, "step": i, "status": "success", "trace_id": trace_id}
        )

    log.info(
        "Service chain completed",
        total_services=len(services),
        trace_id=trace_id,
        chain_status="success",
    )

    return {
        "chain_completed": True,
        "trace_id": trace_id,
        "services_called": results,
        "message": "All services in chain processed with same trace ID",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""

    trace_id = get_current_trace_id()

    return {
        "status": "healthy",
        "service": "trace-propagation-example",
        "trace_id": trace_id,
        "features": {
            "trace_id_api": True,
            "custom_headers": True,
            "httpx_propagation": HTTPX_AVAILABLE,
            "middleware_integration": True,
        },
    }


def print_example_info():
    """Print information about running the example."""
    print("=" * 70)
    print("🔄 Trace Propagation Example (Story 6.2)")
    print("=" * 70)
    print()
    print("This example demonstrates:")
    print("  ✅ get_current_trace_id() API function")
    print("  ✅ Custom trace header: X-Custom-Trace-ID")
    print("  ✅ httpx automatic trace propagation")
    print("  ✅ Cross-service request correlation")
    print()
    print("Test endpoints:")
    print("  GET /                           - Basic trace ID access")
    print("  GET /status/{service}           - Business logic with trace ID")
    print("  GET /call-external/{service}    - httpx propagation demo")
    print("  GET /simulate-service-chain     - Multi-service trace flow")
    print("  GET /health                     - Health check")
    print()
    print("Try with custom trace headers:")
    print("  curl -H 'X-Custom-Trace-ID: my-trace-123' http://localhost:8000/")
    print()
    print("Example log output will show:")
    print("  📋 trace_id field in all log entries")
    print("  🔗 Same trace_id across related requests")
    print("  📤 Automatic propagation to external services")
    print()
    if not HTTPX_AVAILABLE:
        print("⚠️  Install httpx to see full propagation demo:")
        print("   pip install httpx")
        print()
    print("=" * 70)


if __name__ == "__main__":
    print_example_info()

    # Run the example server
    uvicorn.run(
        "17_trace_propagation:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        access_log=False,  # We handle logging via fapilog
    )
