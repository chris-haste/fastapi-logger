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
"""

import asyncio
import logging
import time
import tempfile
import os
from typing import Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings


class OrderRequest(BaseModel):
    customer_id: str
    items: List[Dict[str, Any]]
    total_amount: float


class OrderResponse(BaseModel):
    order_id: str
    customer_id: str
    status: str
    total_amount: float
    created_at: str


# Create temporary log file for demonstration
log_file = tempfile.NamedTemporaryFile(delete=False, suffix=".log")
log_file_path = log_file.name
log_file.close()


def demonstrate_development_config():
    """Demonstrate multiple sinks for development environment."""
    print("=== Development Configuration ===")
    print("Environment variables for development:")
    print("  export FAPILOG_SINKS=stdout,file")
    print("  export FAPILOG_LEVEL=DEBUG")
    print("  export FAPILOG_JSON_CONSOLE=pretty")
    print("  export FAPILOG_FILE_PATH=/tmp/app.log")
    print()

    # Configure for development (stdout + file)
    settings = LoggingSettings(
        level="DEBUG",
        sinks=["stdout", "file"],
        json_console="pretty",  # Pretty output for development
        queue_enabled=True,
        queue_maxsize=100,  # Smaller queue for development
        queue_batch_size=5,
    )

    logger = configure_logging(settings=settings)

    logger.info(
        "Development environment configured",
        extra={
            "environment": "development",
            "sinks": ["stdout", "file"],
            "console_format": "pretty",
        },
    )


def demonstrate_production_config():
    """Demonstrate multiple sinks for production environment."""
    print("\n=== Production Configuration ===")
    print("Environment variables for production:")
    print("  export FAPILOG_SINKS=stdout,loki")
    print("  export FAPILOG_LEVEL=INFO")
    print("  export FAPILOG_JSON_CONSOLE=json")
    print("  export LOKI_URL=http://loki:3100")
    print("  export LOKI_LABELS=app=ecommerce,env=prod")
    print()

    # Configure for production (stdout + loki)
    settings = LoggingSettings(
        level="INFO",
        sinks=["stdout", "loki"],
        json_console="json",  # JSON output for production
        queue_enabled=True,
        queue_maxsize=1000,  # Larger queue for production
        queue_batch_size=20,
        queue_overflow="drop",  # Drop logs if overwhelmed
    )

    logger = configure_logging(settings=settings)

    logger.info(
        "Production environment configured",
        extra={
            "environment": "production",
            "sinks": ["stdout", "loki"],
            "console_format": "json",
        },
    )


def demonstrate_monitoring_config():
    """Demonstrate multiple sinks for monitoring/observability."""
    print("\n=== Monitoring Configuration ===")
    print("Environment variables for monitoring:")
    print("  export FAPILOG_SINKS=stdout,loki,file")
    print("  export FAPILOG_LEVEL=WARNING")
    print("  export FAPILOG_ENABLE_RESOURCE_METRICS=true")
    print("  export FAPILOG_FILE_PATH=/var/log/app/errors.log")
    print()

    # Configure for monitoring (stdout + loki + file for errors)
    settings = LoggingSettings(
        level="WARNING",  # Only warnings and errors
        sinks=["stdout", "loki", "file"],
        enable_resource_metrics=True,  # Enable memory/CPU metrics
        queue_enabled=True,
        queue_maxsize=500,
        queue_batch_size=10,
        queue_overflow="sample",  # Sample when overwhelmed
        sampling_rate=0.8,  # Keep 80% of logs
    )

    logger = configure_logging(settings=settings)

    logger.warning(
        "Monitoring environment configured",
        extra={
            "environment": "monitoring",
            "sinks": ["stdout", "loki", "file"],
            "resource_metrics": True,
        },
    )


def demonstrate_environment_variables():
    """Demonstrate configuration via environment variables only."""
    print("\n=== Environment Variables Only ===")
    print("Set these environment variables:")
    print("  export FAPILOG_SINKS=stdout,file,loki")
    print("  export FAPILOG_LEVEL=INFO")
    print("  export FAPILOG_QUEUE_ENABLED=true")
    print("  export FAPILOG_QUEUE_MAXSIZE=1000")
    print("  export FAPILOG_QUEUE_BATCH_SIZE=10")
    print("  export FAPILOG_QUEUE_OVERFLOW=drop")
    print("  export FAPILOG_ENABLE_RESOURCE_METRICS=true")
    print("  export LOKI_URL=http://localhost:3100")
    print("  export FAPILOG_FILE_PATH=/tmp/app.log")
    print()

    # Configure using environment variables only
    logger = configure_logging()

    logger.info(
        "Environment-based configuration active",
        extra={"config_method": "environment_variables", "sinks": "stdout,file,loki"},
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    log.info(
        "Starting e-commerce API with multiple logging sinks",
        extra={"log_file": log_file_path, "sinks": ["stdout", "file", "loki"]},
    )
    yield
    log.info("Shutting down e-commerce API")
    # Clean up log file
    try:
        os.unlink(log_file_path)
    except OSError:
        pass


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware to log all requests."""
    start_time = time.time()

    # Log request details
    log.debug(
        "Incoming request",
        extra={
            "method": request.method,
            "url": str(request.url),
            "client_ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown"),
        },
    )

    try:
        response = await call_next(request)

        # Log response details
        processing_time = time.time() - start_time
        log.info(
            "Request processed",
            extra={
                "method": request.method,
                "url": str(request.url),
                "status_code": response.status_code,
                "processing_time_ms": round(processing_time * 1000, 2),
            },
        )

        return response

    except Exception as e:
        # Log errors
        processing_time = time.time() - start_time
        log.error(
            "Request failed",
            extra={
                "method": request.method,
                "url": str(request.url),
                "error": str(e),
                "processing_time_ms": round(processing_time * 1000, 2),
            },
        )
        raise


@app.get("/")
async def root():
    """Root endpoint."""
    log.info("Root endpoint accessed")
    return {"message": "E-commerce API", "version": "1.0.0"}


@app.post("/orders", response_model=OrderResponse)
async def create_order(request: OrderRequest):
    """Create a new order with comprehensive logging."""
    order_id = f"ORD-{int(time.time())}"

    # Log order creation start
    log.info(
        "Order creation started",
        extra={
            "order_id": order_id,
            "customer_id": request.customer_id,
            "item_count": len(request.items),
            "total_amount": request.total_amount,
        },
    )

    try:
        # Simulate order processing
        await asyncio.sleep(0.2)

        # Validate order
        if request.total_amount <= 0:
            log.warning(
                "Invalid order amount",
                extra={
                    "order_id": order_id,
                    "customer_id": request.customer_id,
                    "total_amount": request.total_amount,
                },
            )
            raise HTTPException(status_code=400, detail="Invalid order amount")

        if len(request.items) == 0:
            log.warning(
                "Empty order",
                extra={"order_id": order_id, "customer_id": request.customer_id},
            )
            raise HTTPException(status_code=400, detail="Order cannot be empty")

        # Log successful order creation
        log.info(
            "Order created successfully",
            extra={
                "order_id": order_id,
                "customer_id": request.customer_id,
                "status": "created",
                "total_amount": request.total_amount,
            },
        )

        return OrderResponse(
            order_id=order_id,
            customer_id=request.customer_id,
            status="created",
            total_amount=request.total_amount,
            created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log unexpected errors
        log.error(
            "Order creation failed",
            extra={
                "order_id": order_id,
                "customer_id": request.customer_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    """Get order details."""
    log.debug("Order lookup requested", extra={"order_id": order_id})

    # Simulate order lookup
    await asyncio.sleep(0.1)

    # Simulate order not found
    if not order_id.startswith("ORD-"):
        log.warning("Invalid order ID format", extra={"order_id": order_id})
        raise HTTPException(status_code=400, detail="Invalid order ID format")

    # Simulate order not found
    if int(order_id.split("-")[1]) < time.time() - 3600:  # Order older than 1 hour
        log.warning("Order not found", extra={"order_id": order_id})
        raise HTTPException(status_code=404, detail="Order not found")

    log.info("Order retrieved successfully", extra={"order_id": order_id})

    return {
        "order_id": order_id,
        "customer_id": "CUST-123",
        "status": "completed",
        "total_amount": 99.99,
        "created_at": "2024-01-15 10:30:00",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    log.debug("Health check requested")
    return {"status": "healthy", "timestamp": time.time()}


@app.get("/logs/file")
async def get_log_file():
    """Get the contents of the log file (for demonstration)."""
    try:
        with open(log_file_path, "r") as f:
            logs = f.read()
        return {"log_file": log_file_path, "contents": logs}
    except FileNotFoundError:
        return {"error": "Log file not found"}


if __name__ == "__main__":
    import uvicorn

    print("=== Multiple Sinks Configuration Examples ===\n")

    # Demonstrate different sink configurations
    demonstrate_development_config()
    demonstrate_production_config()
    demonstrate_monitoring_config()
    demonstrate_environment_variables()

    print("\n=== Starting E-commerce API Server ===")
    print("Configure multiple sinks via environment variables:")
    print("  FAPILOG_SINKS=stdout,file,loki")
    print("  FAPILOG_LEVEL=INFO")
    print("  FAPILOG_QUEUE_ENABLED=true")
    print("  LOKI_URL=http://localhost:3100")
    print("  FAPILOG_FILE_PATH=/tmp/app.log")
    print()

    log.info(
        "Starting e-commerce API server",
        extra={"host": "0.0.0.0", "port": 8000, "log_file": log_file_path},
    )

    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None)
