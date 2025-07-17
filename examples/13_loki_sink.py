#!/usr/bin/env python3
"""
Example: Loki Sink Configuration

This example demonstrates how to configure fapilog to send logs to Grafana Loki
for centralized log aggregation and querying.

Key features:
- Environment variable configuration for sinks
- Programmatic configuration via LoggingSettings
- Multiple sink configuration patterns
- Structured logging with metadata
"""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings


class UserRequest(BaseModel):
    user_id: str
    action: str
    data: Dict[str, Any]


# Method 1: Environment Variable Configuration (Recommended)
# Set these environment variables before running:
# export FAPILOG_SINKS=stdout,loki
# export FAPILOG_LEVEL=INFO
# export FAPILOG_QUEUE_ENABLED=true


def demonstrate_environment_config():
    """Demonstrate configuration via environment variables."""
    print("=== Environment Variable Configuration ===")
    print("Set these environment variables:")
    print("  export FAPILOG_SINKS=stdout,loki")
    print("  export FAPILOG_LEVEL=INFO")
    print("  export FAPILOG_QUEUE_ENABLED=true")
    print("  export LOKI_URL=http://localhost:3100")
    print()

    # Configure logging using environment variables
    logger = configure_logging()

    logger.info("Application started with environment configuration")
    logger.info(
        "User action processed",
        extra={"user_id": "user-123", "action": "login", "sinks": "stdout,loki"},
    )


# Method 2: Programmatic Configuration
def demonstrate_programmatic_config():
    """Demonstrate configuration via LoggingSettings."""
    print("\n=== Programmatic Configuration ===")

    # Configure via settings object
    settings = LoggingSettings(
        level="INFO",
        sinks=["stdout", "loki"],  # List of sink names
        queue_enabled=True,
        queue_maxsize=1000,
        queue_batch_size=10,
        queue_overflow="drop",
    )

    logger = configure_logging(settings=settings)

    logger.info("Application started with programmatic configuration")
    logger.info(
        "User action processed",
        extra={
            "user_id": "user-456",
            "action": "logout",
            "config_method": "programmatic",
        },
    )


# Method 3: Mixed Configuration (Environment + Overrides)
def demonstrate_mixed_config():
    """Demonstrate mixing environment variables with programmatic overrides."""
    print("\n=== Mixed Configuration ===")

    # Start with environment settings, override specific values
    settings = LoggingSettings(
        level="DEBUG",  # Override environment level
        sinks=["stdout"],  # Override to just stdout for development
        queue_enabled=True,
    )

    logger = configure_logging(settings=settings)

    logger.debug("Debug message with mixed configuration")
    logger.info(
        "User action processed",
        extra={
            "user_id": "user-789",
            "action": "profile_update",
            "config_method": "mixed",
        },
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    log.info("Starting FastAPI application with Loki logging")
    yield
    log.info("Shutting down FastAPI application")


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    """Root endpoint with structured logging."""
    log.info(
        "Root endpoint accessed",
        extra={"endpoint": "/", "method": "GET", "user_agent": "example-client"},
    )
    return {"message": "Hello World"}


@app.post("/users/{user_id}/action")
async def user_action(user_id: str, request: UserRequest):
    """User action endpoint with detailed logging."""
    start_time = time.time()

    # Log the incoming request
    log.info(
        "User action requested",
        extra={
            "user_id": user_id,
            "action": request.action,
            "data_size": len(str(request.data)),
            "endpoint": f"/users/{user_id}/action",
            "method": "POST",
        },
    )

    try:
        # Simulate some processing
        await asyncio.sleep(0.1)

        # Log successful processing
        processing_time = time.time() - start_time
        log.info(
            "User action processed successfully",
            extra={
                "user_id": user_id,
                "action": request.action,
                "processing_time_ms": round(processing_time * 1000, 2),
                "status": "success",
            },
        )

        return {
            "user_id": user_id,
            "action": request.action,
            "status": "success",
            "processing_time_ms": round(processing_time * 1000, 2),
        }

    except Exception as e:
        # Log error with context
        log.error(
            "User action failed",
            extra={
                "user_id": user_id,
                "action": request.action,
                "error": str(e),
                "error_type": type(e).__name__,
                "status": "error",
            },
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    log.info(
        "Health check requested",
        extra={"endpoint": "/health", "method": "GET", "timestamp": time.time()},
    )
    return {"status": "healthy"}


@app.get("/metrics")
async def get_metrics():
    """Metrics endpoint with performance logging."""
    log.info(
        "Metrics requested",
        extra={"endpoint": "/metrics", "method": "GET", "metrics_type": "application"},
    )
    return {"active_connections": 10, "memory_usage": "45MB", "uptime": "2h 30m"}


if __name__ == "__main__":
    import uvicorn

    print("=== Loki Sink Configuration Examples ===\n")

    # Demonstrate different configuration methods
    demonstrate_environment_config()
    demonstrate_programmatic_config()
    demonstrate_mixed_config()

    print("\n=== Starting FastAPI Server ===")
    print("Configure sinks via environment variables:")
    print("  FAPILOG_SINKS=stdout,loki")
    print("  LOKI_URL=http://localhost:3100")
    print()

    # For the server, use environment-based configuration
    log.info(
        "Starting FastAPI server with Loki integration",
        extra={"host": "0.0.0.0", "port": 8000, "loki_url": "http://localhost:3100"},
    )

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_config=None,  # Disable uvicorn's default logging
    )
