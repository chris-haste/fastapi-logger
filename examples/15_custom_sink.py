#!/usr/bin/env python3
"""
Example: Custom Sink Implementation

This example demonstrates how to create a custom sink for specialized
logging requirements, such as sending logs to a custom API or database.

Key features:
- Custom sink implementation following fapilog sink interface
- Integration with fapilog's async queue system
- Error handling and retry logic
- Structured data formatting
- Multiple ways to register and use custom sinks
"""

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import aiohttp
from fastapi import FastAPI
from pydantic import BaseModel

from fapilog import configure_logging, log
from fapilog._internal.queue import Sink
from fapilog.settings import LoggingSettings


class UserAction(BaseModel):
    user_id: str
    action: str
    resource: str
    details: Dict[str, Any]


class CustomAPISink(Sink):
    """
    Custom sink that sends logs to a custom API endpoint.

    This sink demonstrates how to create a custom sink for specialized
    logging requirements, such as sending logs to a custom monitoring
    service or database.
    """

    def __init__(
        self,
        api_url: str,
        api_key: Optional[str] = None,
        batch_size: int = 10,
        batch_timeout: float = 5.0,
        retry_attempts: int = 3,
        retry_delay: float = 1.0,
        timeout: float = 10.0,
    ):
        self.api_url = api_url
        self.api_key = api_key
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
        self.log_buffer: List[Dict[str, Any]] = []
        self.last_send_time = time.time()
        self._send_task: Optional[asyncio.Task] = None

    async def start(self):
        """Initialize the custom sink."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        self._send_task = asyncio.create_task(self._batch_sender())
        logging.getLogger(__name__).info(f"Custom API sink started: {self.api_url}")

    async def stop(self):
        """Clean up the custom sink."""
        if self._send_task:
            self._send_task.cancel()
            try:
                await self._send_task
            except asyncio.CancelledError:
                pass

        # Send any remaining logs
        if self.log_buffer:
            await self._send_logs(self.log_buffer)
            self.log_buffer.clear()

        if self.session:
            await self.session.close()

        logging.getLogger(__name__).info("Custom API sink stopped")

    async def write(self, record: Dict[str, Any]):
        """Write a log record to the custom API."""
        # Add timestamp if not present
        if "timestamp" not in record:
            record["timestamp"] = time.time()

        # Add sink metadata
        record["sink"] = "custom_api"
        record["api_url"] = self.api_url

        self.log_buffer.append(record)

        # Send immediately if buffer is full
        if len(self.log_buffer) >= self.batch_size:
            await self._send_logs(self.log_buffer)
            self.log_buffer.clear()
            self.last_send_time = time.time()

    async def _batch_sender(self):
        """Background task to send logs in batches."""
        while True:
            try:
                await asyncio.sleep(self.batch_timeout)

                # Check if we should send logs
                if (
                    self.log_buffer
                    and time.time() - self.last_send_time >= self.batch_timeout
                ):
                    await self._send_logs(self.log_buffer)
                    self.log_buffer.clear()
                    self.last_send_time = time.time()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.getLogger(__name__).error(f"Batch sender error: {e}")

    async def _send_logs(self, logs: List[Dict[str, Any]]):
        """Send logs to the custom API with retry logic."""
        if not logs:
            return

        for attempt in range(self.retry_attempts):
            try:
                headers = {"Content-Type": "application/json"}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"

                payload = {
                    "logs": logs,
                    "batch_size": len(logs),
                    "timestamp": time.time(),
                }

                async with self.session.post(
                    self.api_url, json=payload, headers=headers
                ) as response:
                    if response.status == 200:
                        logging.getLogger(__name__).debug(
                            f"Successfully sent {len(logs)} logs to custom API"
                        )
                        return
                    else:
                        error_text = await response.text()
                        raise Exception(f"API returned {response.status}: {error_text}")

            except Exception as e:
                if attempt == self.retry_attempts - 1:
                    logging.getLogger(__name__).error(
                        f"Failed to send logs to custom API after {self.retry_attempts} attempts: {e}"
                    )
                else:
                    logging.getLogger(__name__).warning(
                        f"Failed to send logs to custom API (attempt {attempt + 1}): {e}"
                    )
                    await asyncio.sleep(self.retry_delay * (attempt + 1))


class AuditLogSink(Sink):
    """
    Custom sink for audit logging to a separate storage.

    This sink demonstrates how to create a specialized sink for
    audit logging with different formatting and storage requirements.
    """

    def __init__(self, audit_file_path: str):
        self.audit_file_path = audit_file_path
        self.audit_buffer: List[Dict[str, Any]] = []
        self._audit_task: Optional[asyncio.Task] = None

    async def start(self):
        """Initialize the audit sink."""
        self._audit_task = asyncio.create_task(self._audit_writer())
        logging.getLogger(__name__).info(f"Audit sink started: {self.audit_file_path}")

    async def stop(self):
        """Clean up the audit sink."""
        if self._audit_task:
            self._audit_task.cancel()
            try:
                await self._audit_task
            except asyncio.CancelledError:
                pass

        # Write any remaining audit logs
        if self.audit_buffer:
            await self._write_audit_logs(self.audit_buffer)
            self.audit_buffer.clear()

        logging.getLogger(__name__).info("Audit sink stopped")

    async def write(self, record: Dict[str, Any]):
        """Write an audit log record."""
        # Only process audit-related logs
        if record.get("log_type") != "audit":
            return

        # Add audit-specific metadata
        record["audit_timestamp"] = time.time()
        record["audit_id"] = f"AUDIT-{int(time.time())}"

        self.audit_buffer.append(record)

        # Write immediately for audit logs (no batching for security)
        if self.audit_buffer:
            await self._write_audit_logs(self.audit_buffer)
            self.audit_buffer.clear()

    async def _audit_writer(self):
        """Background task to write audit logs."""
        while True:
            try:
                await asyncio.sleep(1.0)  # Check every second

                if self.audit_buffer:
                    await self._write_audit_logs(self.audit_buffer)
                    self.audit_buffer.clear()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.getLogger(__name__).error(f"Audit writer error: {e}")

    async def _write_audit_logs(self, logs: List[Dict[str, Any]]):
        """Write audit logs to file."""
        try:
            # Use asyncio to write to file
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._write_logs_sync, logs)
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to write audit logs: {e}")

    def _write_logs_sync(self, logs: List[Dict[str, Any]]):
        """Synchronous file writing."""
        try:
            with open(self.audit_file_path, "a") as f:
                for log in logs:
                    f.write(json.dumps(log) + "\n")
        except Exception as e:
            logging.getLogger(__name__).error(f"Sync audit log write failed: {e}")


def demonstrate_custom_sink_usage():
    """Demonstrate how to use custom sinks with fapilog."""
    print("=== Custom Sink Usage ===")
    print("This example shows how to create and use custom sinks.")
    print(
        "Custom sinks should implement the Sink interface from fapilog._internal.queue"
    )
    print()

    # Note: In a real application, you would register custom sinks
    # with fapilog's sink registry or configure them through
    # environment variables or settings.

    print("Custom sink features:")
    print("✅ Implement async write() method")
    print("✅ Handle batching and retries")
    print("✅ Proper error handling and logging")
    print("✅ Graceful shutdown")
    print("✅ Integration with fapilog's queue system")
    print()


def demonstrate_audit_logging():
    """Demonstrate audit logging patterns."""
    print("\n=== Audit Logging Pattern ===")

    # Configure logging with standard sinks
    settings = LoggingSettings(
        level="INFO",
        sinks=["stdout"],
        queue_enabled=True,  # Standard sinks
    )

    logger = configure_logging(settings=settings)

    # Log regular application events
    logger.info(
        "User action received",
        extra={"user_id": "user-123", "action": "login", "resource": "auth"},
    )

    # Log audit events (these would be handled by custom audit sink)
    logger.info(
        "User action audit",
        extra={
            "log_type": "audit",  # Special marker for audit sink
            "user_id": "user-123",
            "action": "login",
            "resource": "auth",
            "details": {"ip": "192.168.1.100", "session_id": "session-123"},
            "ip_address": "192.168.1.100",
            "session_id": "session-123",
        },
    )

    print("Audit logging features:")
    print("✅ Separate storage for audit logs")
    print("✅ Immediate writing (no batching)")
    print("✅ Enhanced metadata and security")
    print("✅ Compliance-friendly formatting")
    print()


def demonstrate_custom_api_integration():
    """Demonstrate custom API integration."""
    print("\n=== Custom API Integration ===")

    # Configure logging
    settings = LoggingSettings(
        level="INFO",
        sinks=["stdout"],
        queue_enabled=True,
        queue_batch_size=5,  # Smaller batches for API calls
    )

    logger = configure_logging(settings=settings)

    # Log events that would be sent to custom API
    logger.info(
        "Application event",
        extra={
            "event_type": "user_action",
            "user_id": "user-456",
            "action": "profile_update",
            "api_destination": "monitoring-service",
        },
    )

    print("Custom API integration features:")
    print("✅ Batch sending for efficiency")
    print("✅ Retry logic with exponential backoff")
    print("✅ Authentication and headers")
    print("✅ Error handling and monitoring")
    print("✅ Structured payload formatting")
    print()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    log.info("Starting application with custom sinks")
    yield
    log.info("Shutting down application")


app = FastAPI(lifespan=lifespan)


@app.post("/users/{user_id}/action")
async def user_action(user_id: str, action: UserAction):
    """User action endpoint with custom logging."""

    # Regular application log
    log.info(
        "User action received",
        extra={
            "user_id": user_id,
            "action": action.action,
            "resource": action.resource,
        },
    )

    # Audit log for security (would be handled by custom audit sink)
    log.info(
        "User action audit",
        extra={
            "log_type": "audit",
            "user_id": user_id,
            "action": action.action,
            "resource": action.resource,
            "details": action.details,
            "ip_address": "192.168.1.100",  # Mock IP
            "session_id": "session-123",
        },
    )

    # Simulate processing
    await asyncio.sleep(0.1)

    # Log success
    log.info(
        "User action completed",
        extra={"user_id": user_id, "action": action.action, "status": "success"},
    )

    return {
        "user_id": user_id,
        "action": action.action,
        "status": "completed",
        "timestamp": time.time(),
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    log.info("Health check requested")
    return {"status": "healthy"}


@app.get("/audit/logs")
async def get_audit_logs():
    """Get audit logs (for demonstration)."""
    try:
        with open("/tmp/audit.log") as f:
            logs = f.readlines()
        return {"audit_logs": [json.loads(log.strip()) for log in logs]}
    except FileNotFoundError:
        return {"audit_logs": []}


if __name__ == "__main__":
    import uvicorn

    print("=== Custom Sink Implementation Examples ===\n")

    # Demonstrate different custom sink patterns
    demonstrate_custom_sink_usage()
    demonstrate_audit_logging()
    demonstrate_custom_api_integration()

    print("\n=== Starting Application Server ===")
    print("Custom sinks would be configured via:")
    print("  - Environment variables")
    print("  - Sink registry")
    print("  - Programmatic configuration")
    print()

    log.info(
        "Starting application with custom sinks",
        extra={
            "custom_api_url": "http://localhost:8080/api/logs",
            "audit_file": "/tmp/audit.log",
        },
    )

    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None)
