#!/usr/bin/env python3
"""
Example: Multiple Sinks Configuration

This example demonstrates how to configure fapilog with multiple sinks
for different output destinations simultaneously.

Key features:
- Multiple sinks configured via environment variables
- Different sink combinations for different environments
- Structured logging across all sinks
- Error handling and sink-specific configurations
- Automatic request context enrichment (method, path, status_code, client_ip,
  duration_ms, trace_id) via TraceIDMiddleware

Note: As of fapilog Story 6.1, request metadata is automatically captured.
This example focuses on business logging across multiple sink destinations.
"""

import asyncio
import os
import tempfile
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings


class OrderRequest(BaseModel):
    customer_id: str
    items: List[Dict[str, Any]]
    total_amount: float
    priority: str = "normal"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Create temporary log file for this example
    log_file_path = tempfile.mktemp(suffix=".log", prefix="fapilog_multi_sink_")

    # Configure multiple sinks via settings
    settings = LoggingSettings(
        level="INFO",
        json_console="pretty",  # Console sink with pretty formatting
        queue_enabled=True,  # Enable queue for better performance
        # File sink configuration
        sinks=[
            f"file:{log_file_path}",  # File sink
            "stdout:pretty",  # Stdout sink with pretty formatting
        ],
    )

    # Configure logging - automatically registers TraceIDMiddleware
    configure_logging(app=app, settings=settings)

    # Log startup across all sinks
    log.info(
        "Multi-sink application starting",
        app_name="fapilog-multi-sink-example",
        version="1.0.0",
        sinks_configured=["file", "stdout"],
        log_file=log_file_path,
        features=["multiple_sinks", "automatic_request_context", "queue_enabled"],
    )

    print("=== Multi-Sink Logging Example ===")
    print(f"📄 File sink: {log_file_path}")
    print("🖥️  Console sink: stdout (pretty format)")
    print("🔄 Queue enabled for performance")
    print("✅ Automatic request context enrichment enabled")
    print()

    try:
        yield
    finally:
        # Log shutdown
        log.info("Multi-sink application shutting down")

        # Clean up temporary log file
        try:
            if os.path.exists(log_file_path):
                os.unlink(log_file_path)
        except OSError:
            pass


app = FastAPI(lifespan=lifespan)


# Note: Custom request middleware is no longer needed as TraceIDMiddleware
# automatically captures all request metadata. This example focuses on
# demonstrating multi-sink logging with business-specific log events.


@app.get("/")
async def root():
    """Root endpoint - automatically logged to all sinks."""
    # Request metadata automatically captured and sent to all sinks
    log.info("Root endpoint accessed", service="multi-sink-example")
    return {
        "message": "Multi-sink logging example",
        "note": "Request metadata automatically logged to all configured sinks",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint with structured logging."""
    log.info(
        "Health check requested",
        operation="health_check",
        status="healthy",
        checks=["database", "cache", "external_api"],
    )

    return {
        "status": "healthy",
        "timestamp": time.time(),
        "checks": {"database": "ok", "cache": "ok", "external_api": "ok"},
    }


@app.post("/orders")
async def create_order(order: OrderRequest):
    """Create order with multi-sink business logging."""
    order_id = f"ord_{int(time.time())}_{hash(order.customer_id) % 1000:03d}"

    # Business logic logging (sent to all sinks)
    log.info(
        "Order processing started",
        operation="order_create",
        order_id=order_id,
        customer_id=order.customer_id,
        item_count=len(order.items),
        total_amount=order.total_amount,
        priority=order.priority,
    )

    # Simulate order validation
    await asyncio.sleep(0.1)

    # Validate total amount
    calculated_total = sum(
        item.get("price", 0) * item.get("quantity", 1) for item in order.items
    )

    if abs(calculated_total - order.total_amount) > 0.01:
        log.error(
            "Order total mismatch",
            operation="order_create",
            order_id=order_id,
            customer_id=order.customer_id,
            provided_total=order.total_amount,
            calculated_total=calculated_total,
            error_type="validation_error",
        )
        raise HTTPException(
            status_code=400, detail="Order total does not match item prices"
        )

    # Simulate order processing
    await asyncio.sleep(0.2)

    # Log successful order creation
    log.info(
        "Order created successfully",
        operation="order_create",
        order_id=order_id,
        customer_id=order.customer_id,
        total_amount=order.total_amount,
        priority=order.priority,
        business_metrics={
            "order_value": order.total_amount,
            "item_count": len(order.items),
            "processing_priority": order.priority,
        },
    )

    return {
        "order_id": order_id,
        "status": "created",
        "customer_id": order.customer_id,
        "total_amount": order.total_amount,
        "items": order.items,
        "created_at": time.time(),
    }


@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    """Get order details with audit logging."""
    log.info(
        "Order lookup requested",
        operation="order_lookup",
        order_id=order_id,
        audit_category="data_access",
    )

    # Simulate database lookup
    await asyncio.sleep(0.05)

    # Mock order not found for demonstration
    if "invalid" in order_id.lower():
        log.warning(
            "Order not found",
            operation="order_lookup",
            order_id=order_id,
            reason="invalid_order_id",
        )
        raise HTTPException(status_code=404, detail="Order not found")

    # Mock order response
    mock_order = {
        "order_id": order_id,
        "customer_id": "customer_123",
        "status": "processing",
        "total_amount": 99.99,
        "created_at": time.time() - 3600,  # 1 hour ago
    }

    log.info(
        "Order retrieved successfully",
        operation="order_lookup",
        order_id=order_id,
        customer_id=mock_order["customer_id"],
        order_status=mock_order["status"],
        audit_category="data_access",
    )

    return mock_order


@app.get("/analytics/summary")
async def get_analytics():
    """Get analytics with business intelligence logging."""
    log.info(
        "Analytics summary requested",
        operation="analytics",
        report_type="business_summary",
    )

    # Simulate analytics calculation
    await asyncio.sleep(0.15)

    # Mock analytics data
    analytics = {
        "total_orders": 1250,
        "total_revenue": 125000.50,
        "avg_order_value": 100.00,
        "top_customer_segments": ["premium", "enterprise"],
        "generated_at": time.time(),
    }

    # Business intelligence logging
    log.info(
        "Analytics summary generated",
        operation="analytics",
        report_type="business_summary",
        metrics=analytics,
        business_category="business_intelligence",
    )

    return analytics


@app.get("/performance/load-test")
async def load_test():
    """Load testing endpoint for multi-sink performance evaluation."""
    log.info(
        "Load test started",
        operation="load_test",
        test_type="multi_sink_performance",
    )

    # Generate multiple log events quickly to test sink performance
    for i in range(10):
        log.info(
            f"Load test event {i + 1}",
            operation="load_test",
            event_number=i + 1,
            batch_size=10,
            test_data={"value": i * 10, "category": f"test_{i % 3}"},
        )
        # Small delay to avoid overwhelming
        await asyncio.sleep(0.01)

    log.info(
        "Load test completed",
        operation="load_test",
        test_type="multi_sink_performance",
        events_generated=10,
    )

    return {
        "message": "Load test completed",
        "events_generated": 10,
        "note": "Check both console and file sinks for all events",
    }


def main():
    """Run the FastAPI application."""

    print("=== FastAPI Multiple Sinks Example (Updated for Story 6.1) ===")
    print("This example demonstrates:")
    print("✅ Multiple sink configuration (file + console)")
    print("✅ Automatic request context enrichment")
    print("✅ Business logging across all sinks")
    print("✅ Queue-based logging for performance")
    print("✅ Structured logging with sink-specific formatting")
    print()
    print("Available endpoints:")
    print("  GET  /                    - Root endpoint")
    print("  GET  /health              - Health check with structured logging")
    print("  POST /orders              - Create order with validation")
    print("  GET  /orders/{id}         - Get order details")
    print("  GET  /analytics/summary   - Business analytics")
    print("  GET  /performance/load-test - Multi-sink performance test")
    print()
    print("Key features:")
    print("✅ Automatic request metadata capture (via TraceIDMiddleware)")
    print("✅ Multiple output destinations")
    print("✅ Queue-based processing")
    print("✅ Business-specific structured logging")
    print("✅ Performance testing capabilities")
    print()
    print(
        "Note: Request metadata (method, path, status_code, client_ip, "
        "duration_ms, trace_id)"
    )
    print("      is automatically logged to ALL configured sinks!")
    print()
    print("Start the server with: uvicorn examples.14_multiple_sinks:app --reload")
    print("Then visit: http://localhost:8000/docs")


if __name__ == "__main__":
    main()
