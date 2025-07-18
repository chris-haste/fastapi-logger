#!/usr/bin/env python3
"""
Example: Security and Compliance Logging

This example demonstrates security-focused logging patterns including
audit trails, sensitive data handling, and compliance logging.

Key features:
- Audit trail logging for security events
- Sensitive data masking and filtering
- Compliance logging (GDPR, SOX, etc.)
- Security event correlation
- Access control logging

Note: As of fapilog Story 6.1, basic request metadata (method, path,
status_code, client_ip, duration_ms, trace_id) is automatically captured
by TraceIDMiddleware. This example shows additional custom security middleware
for enhanced audit logging beyond the automatic features.
"""

import asyncio
import hashlib
import json
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from fapilog import configure_logging
from fapilog.enrichers import create_user_dependency
from fapilog.settings import LoggingSettings
from fapilog.sinks.stdout import StdoutSink


class User(BaseModel):
    user_id: str
    email: str
    role: str
    permissions: List[str]


class LoginRequest(BaseModel):
    username: str
    password: str = Field(..., min_length=8)


class SensitiveData(BaseModel):
    content: str
    classification: str = "confidential"


class SecurityEvent(BaseModel):
    event_type: str
    user_id: Optional[str] = None
    ip_address: str
    user_agent: str
    details: Dict[str, Any] = {}


# Configure security-focused logger
sink = StdoutSink(mode="json")
logger = configure_logging(
    settings=LoggingSettings(level="INFO", enable_resource_metrics=True), sinks=[sink]
)

security = HTTPBearer()


# Mock user database for demonstration
USERS_DB = {
    "valid-token": {
        "user_id": "user-123",
        "email": "user@example.com",
        "role": "admin",
        "permissions": ["read", "write", "delete", "audit"],
    }
}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """Verify bearer token and return user information."""
    token = credentials.credentials

    if token in USERS_DB:
        user_data = USERS_DB[token]
        return User(**user_data)

    raise HTTPException(status_code=401, detail="Invalid authentication credentials")


# Create user context dependency that automatically binds user info to logs
get_current_user_with_context = create_user_dependency(get_current_user)


def hash_sensitive_data(data: str) -> str:
    """Hash sensitive data for logging."""
    return hashlib.sha256(data.encode()).hexdigest()[:16]


def mask_email(email: str) -> str:
    """Mask email for compliance logging."""
    if "@" in email:
        local, domain = email.split("@", 1)
        masked_local = local[:2] + "*" * (len(local) - 2)
        return f"{masked_local}@{domain}"
    return email


def mask_sensitive_data(data: str, mask_char: str = "*") -> str:
    """Mask sensitive data for logging."""
    if len(data) <= 4:
        return mask_char * len(data)
    return data[:2] + mask_char * (len(data) - 4) + data[-2:]


def sanitize_log_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize log data by masking sensitive fields."""
    sensitive_fields = {
        "password",
        "credit_card",
        "ssn",
        "token",
        "secret",
        "api_key",
        "private_key",
        "session_id",
    }

    sanitized = data.copy()
    for key, value in sanitized.items():
        if key.lower() in sensitive_fields and isinstance(value, str):
            sanitized[key] = mask_sensitive_data(value)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_log_data(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_log_data(item) if isinstance(item, dict) else item
                for item in value
            ]

    return sanitized


def log_security_event(event: SecurityEvent, request_id: str):
    """Log security events with proper audit formatting."""
    logger.info(
        f"Security event: {event.event_type}",
        extra={
            "log_type": "security_audit",
            "event_type": event.event_type,
            "request_id": request_id,
            "user_id": event.user_id,
            "client_ip": event.ip_address,
            "user_agent": event.user_agent,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": event.details,
            "compliance": {
                "retention_period": "7_years",
                "classification": "security_audit",
                "regulations": ["SOX", "GDPR", "PCI_DSS"],
            },
        },
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info(
        "Starting secure application",
        extra={
            "app_name": "security-logging-example",
            "security_features": [
                "audit_logging",
                "data_masking",
                "compliance_logging",
                "automatic_request_context",  # Added in Story 6.1
            ],
        },
    )
    yield
    logger.info("Shutting down secure application")


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """Custom security middleware for enhanced audit logging.

    Note: This provides additional security-specific logging beyond the
    automatic request context enrichment provided by fapilog's TraceIDMiddleware.
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())

    # Extract security-relevant information
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    # Log incoming request (additional to automatic logging)
    logger.info(
        "Incoming request",
        extra={
            "log_type": "security",
            "event_type": "request_start",
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "client_ip": client_ip,
            "user_agent": user_agent,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    try:
        response = await call_next(request)

        # Log successful request
        processing_time = time.time() - start_time
        logger.info(
            "Request completed",
            extra={
                "log_type": "security",
                "event_type": "request_success",
                "request_id": request_id,
                "status_code": response.status_code,
                "processing_time_ms": round(processing_time * 1000, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        return response

    except Exception as e:
        # Log failed request
        processing_time = time.time() - start_time
        logger.error(
            "Request failed",
            extra={
                "log_type": "security",
                "event_type": "request_error",
                "request_id": request_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "processing_time_ms": round(processing_time * 1000, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        raise


@app.post("/auth/login")
async def login(request: LoginRequest):
    """Login endpoint with security logging."""
    # Log login attempt
    logger.info(
        "Login attempt",
        extra={
            "log_type": "security",
            "event_type": "login_attempt",
            "email": mask_email(request.username),
            "ip_address": "192.168.1.100",  # Mock IP
            "user_agent": "Mozilla/5.0...",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    # Simulate authentication
    await asyncio.sleep(0.1)

    if request.username == "user@example.com" and request.password == "password123":
        # Log successful login
        session_id = str(uuid.uuid4())
        logger.info(
            "Login successful",
            extra={
                "log_type": "security",
                "event_type": "login_success",
                "user_id": "user-123",
                "email": mask_email(request.username),
                "session_id": session_id,
                "ip_address": "192.168.1.100",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        return {
            "access_token": "valid-token",
            "session_id": session_id,
            "expires_in": 3600,
        }
    else:
        # Log failed login
        logger.warning(
            "Login failed",
            extra={
                "log_type": "security",
                "event_type": "login_failed",
                "email": mask_email(request.username),
                "ip_address": "192.168.1.100",
                "reason": "invalid_credentials",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        raise HTTPException(status_code=401, detail="Invalid credentials")


@app.post("/auth/logout")
async def logout(current_user: User = Depends(get_current_user_with_context)):
    """Logout endpoint with security logging."""
    logger.info(
        "Logout",
        extra={
            "log_type": "security",
            "event_type": "logout",
            "user_id": current_user.user_id,
            "email": mask_email(current_user.email),
            "ip_address": "192.168.1.100",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    return {"message": "Logged out successfully"}


@app.post("/users/{user_id}/sensitive-data")
async def process_sensitive_data(
    user_id: str, data: SensitiveData, current_user: User = Depends(get_current_user)
):
    """Process sensitive data with secure logging."""

    # Log data processing attempt
    logger.info(
        "Sensitive data processing",
        extra={
            "log_type": "security",
            "event_type": "sensitive_data_access",
            "user_id": current_user.user_id,
            "target_user_id": user_id,
            "data_type": "personal_information",
            "ip_address": "192.168.1.100",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    # Check permissions
    if "write" not in current_user.permissions:
        logger.warning(
            "Permission denied",
            extra={
                "log_type": "security",
                "event_type": "permission_denied",
                "user_id": current_user.user_id,
                "target_user_id": user_id,
                "required_permission": "write",
                "user_permissions": current_user.permissions,
                "ip_address": "192.168.1.100",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        raise HTTPException(status_code=403, detail="Permission denied")

    # Process data (simulated)
    await asyncio.sleep(0.1)

    # Log successful processing with sanitized data
    sanitized_data = sanitize_log_data(data.dict())
    logger.info(
        "Sensitive data processed",
        extra={
            "log_type": "security",
            "event_type": "sensitive_data_processed",
            "user_id": current_user.user_id,
            "target_user_id": user_id,
            "data_hash": hash_sensitive_data(json.dumps(data.dict())),
            "sanitized_data": sanitized_data,
            "ip_address": "192.168.1.100",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    return {
        "user_id": user_id,
        "status": "processed",
        "data_hash": hash_sensitive_data(json.dumps(data.dict())),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/users/{user_id}/profile")
async def get_user_profile(
    user_id: str, current_user: User = Depends(get_current_user)
):
    """Get user profile with access logging."""

    # Log access attempt
    logger.info(
        "Profile access",
        extra={
            "log_type": "security",
            "event_type": "profile_access",
            "user_id": current_user.user_id,
            "target_user_id": user_id,
            "ip_address": "192.168.1.100",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    # Check if user can access this profile
    if current_user.user_id != user_id and "admin" not in current_user.role:
        logger.warning(
            "Unauthorized profile access",
            extra={
                "log_type": "security",
                "event_type": "unauthorized_access",
                "user_id": current_user.user_id,
                "target_user_id": user_id,
                "ip_address": "192.168.1.100",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        raise HTTPException(status_code=403, detail="Access denied")

    # Return profile data
    return {
        "user_id": user_id,
        "email": mask_email("user@example.com"),
        "role": "user",
        "created_at": "2024-01-01T00:00:00Z",
    }


@app.post("/security/events")
async def report_security_event(event: SecurityEvent):
    """Report security events for correlation."""

    logger.warning(
        "Security event reported",
        extra={
            "log_type": "security",
            "event_type": event.event_type,
            "user_id": event.user_id,
            "ip_address": event.ip_address,
            "user_agent": event.user_agent,
            "details": sanitize_log_data(event.details),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    return {"status": "event_logged", "event_id": str(uuid.uuid4())}


@app.get("/audit/logs")
async def get_audit_logs(
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    event_type: Optional[str] = None,
    user_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """Get audit logs (admin only)."""

    if "admin" not in current_user.role:
        logger.warning(
            "Unauthorized audit log access",
            extra={
                "log_type": "security",
                "event_type": "unauthorized_audit_access",
                "user_id": current_user.user_id,
                "ip_address": "192.168.1.100",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        raise HTTPException(status_code=403, detail="Admin access required")

    # Log audit log access
    logger.info(
        "Audit logs accessed",
        extra={
            "log_type": "security",
            "event_type": "audit_log_access",
            "user_id": current_user.user_id,
            "filters": {
                "start_time": start_time,
                "end_time": end_time,
                "event_type": event_type,
                "user_id": user_id,
            },
            "ip_address": "192.168.1.100",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    # Return mock audit logs
    return {
        "audit_logs": [
            {
                "event_type": "login_success",
                "user_id": "user-123",
                "timestamp": "2024-01-15T10:30:00Z",
                "ip_address": "192.168.1.100",
            },
            {
                "event_type": "sensitive_data_access",
                "user_id": "user-123",
                "timestamp": "2024-01-15T10:35:00Z",
                "ip_address": "192.168.1.100",
            },
        ],
        "total_count": 2,
        "filters_applied": {
            "start_time": start_time,
            "end_time": end_time,
            "event_type": event_type,
            "user_id": user_id,
        },
    }


if __name__ == "__main__":
    import uvicorn

    logger.info(
        "Starting secure application",
        extra={
            "security_features": [
                "audit_logging",
                "sensitive_data_masking",
                "access_control",
                "compliance_logging",
            ],
            "compliance_standards": ["GDPR", "SOX", "PCI-DSS"],
        },
    )

    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None)
