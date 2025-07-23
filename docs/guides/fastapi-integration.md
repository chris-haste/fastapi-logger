# FastAPI Integration Guide

**Complete guide to integrating fapilog with FastAPI applications - from basic setup to advanced patterns.**

FastAPI integration is where fapilog truly shines. With automatic middleware, trace correlation, request context enrichment, and async-safe logging, you get enterprise-grade observability with minimal setup. This guide covers everything from basic integration to advanced production patterns.

### 🚀 Quick Navigation

**Common Tasks:**

- [Just want basic FastAPI logging?](#basic-integration) → Basic Integration
- [Need automatic request tracing?](#middleware-setup) → Middleware Setup
- [Want user context in logs?](#user-context-enrichment) → User Context
- [Building a production API?](#production-patterns) → Production Patterns
- [Having integration issues?](#common-issues) → Troubleshooting Guide

## Table of Contents

**Getting Started**

- [Quick Start](#quick-start) - One-line FastAPI integration
- [Basic Integration](#basic-integration) - FastAPI app setup with fapilog
  - [Automatic Middleware](#automatic-middleware) - Zero-config middleware setup
  - [Manual Middleware](#manual-middleware) - Custom middleware configuration
  - [App Lifecycle](#app-lifecycle) - Startup and shutdown patterns

**Core Features**

- [Middleware & Tracing](#middleware--tracing) - Request correlation and timing
  - [Trace ID Generation](#trace-id-generation) - Automatic and custom trace IDs
  - [Request/Response Logging](#requestresponse-logging) - Automatic HTTP logging
  - [Performance Tracking](#performance-tracking) - Response times and metrics
- [Context Management](#context-management) - Request-scoped data enrichment
  - [User Context Enrichment](#user-context-enrichment) - User ID and session tracking
  - [Custom Context](#custom-context) - Application-specific context
  - [Context Propagation](#context-propagation) - Across async tasks

**Advanced Patterns**

- [Error Handling](#error-handling) - Exception tracking and correlation
  - [Exception Middleware](#exception-middleware) - Global error handling
  - [Error Context](#error-context) - Rich error information
  - [Error Recovery](#error-recovery) - Graceful degradation
- [Authentication Integration](#authentication-integration) - User tracking patterns
- [Real-World Examples](#real-world-examples) - Production-ready applications
  - [REST API Service](#rest-api-service) - Complete REST API example
  - [Microservice Architecture](#microservice-architecture) - Service-to-service communication
  - [WebSocket Applications](#websocket-applications) - Real-time logging

**Production Deployment**

- [Production Patterns](#production-patterns) - Scalable FastAPI logging
- [Performance Optimization](#performance-optimization) - High-throughput patterns
- [Monitoring Integration](#monitoring-integration) - Health checks and metrics

**Reference**

- [Troubleshooting](#troubleshooting) - Common issues and solutions
- [Best Practices](#best-practices) - Design principles and patterns

---

## Quick Start

**Get FastAPI logging in 30 seconds:**

```python
from fastapi import FastAPI
from fapilog import configure_logging, log

# Create FastAPI app
app = FastAPI()

# One-line logging setup
configure_logging(app=app)

@app.get("/users/{user_id}")
async def get_user(user_id: str):
    log.info("User requested", user_id=user_id)
    return {"user_id": user_id, "name": "John Doe"}
```

**What you get automatically:**

- ✅ **Structured JSON logs** in production
- ✅ **Pretty console logs** in development
- ✅ **Automatic trace IDs** for request correlation
- ✅ **Request/response logging** with timing
- ✅ **Error tracking** with full context

---

## Basic Integration

### Automatic Middleware

**The simplest way to add logging to FastAPI:**

```python
from fastapi import FastAPI
from fapilog import configure_logging, log

app = FastAPI(title="My API", version="1.0.0")

# Automatic middleware registration
configure_logging(app=app)

@app.get("/health")
async def health_check():
    log.info("Health check requested")
    return {"status": "healthy"}

@app.post("/users")
async def create_user(user_data: dict):
    log.info("Creating user", email=user_data.get("email"))
    # Your business logic here
    log.info("User created successfully", user_id="123")
    return {"user_id": "123", "status": "created"}
```

**Automatic features:**

- **TraceIDMiddleware** added to your app
- **Request correlation** via trace IDs
- **Response headers** with trace information
- **Automatic timing** for all requests

### Manual Middleware

**For more control over middleware configuration:**

```python
from fastapi import FastAPI
from fapilog import configure_logging
from fapilog.middleware import TraceIDMiddleware

app = FastAPI()

# Configure logging without automatic middleware
configure_logging()

# Add middleware manually with custom options
app.add_middleware(
    TraceIDMiddleware,
    trace_id_header="X-Custom-Trace-ID",  # Custom header name
    include_request_body=True,            # Log request bodies
    include_response_body=False,          # Skip response bodies
    exclude_paths=["/health", "/metrics"] # Skip certain paths
)
```

### App Lifecycle

**Integrate with FastAPI lifecycle events:**

```python
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fapilog import configure_logging, log

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    log.info("Application starting up", version=app.version)
    configure_logging(app=app)

    # Initialize your services
    await initialize_database()
    await start_background_tasks()

    log.info("Application startup complete")

    yield

    # Shutdown
    log.info("Application shutting down")
    await cleanup_resources()
    log.info("Application shutdown complete")

app = FastAPI(lifespan=lifespan)

async def initialize_database():
    log.info("Initializing database connection")
    # Your database initialization

async def start_background_tasks():
    log.info("Starting background tasks")
    # Your background task setup

async def cleanup_resources():
    log.info("Cleaning up resources")
    # Your cleanup logic
```

[↑ Back to top](#fastapi-integration-guide)

---

## Middleware & Tracing

### Trace ID Generation

**Automatic trace ID generation and propagation:**

```python
from fastapi import FastAPI, Request
from fapilog import configure_logging, log, get_current_trace_id

app = FastAPI()
configure_logging(app=app)

@app.get("/api/orders/{order_id}")
async def get_order(order_id: str, request: Request):
    # Trace ID is automatically generated and available
    trace_id = get_current_trace_id()

    log.info("Order lookup started",
             order_id=order_id,
             trace_id=trace_id,
             user_agent=request.headers.get("user-agent"))

    # Your business logic
    order = await fetch_order_from_db(order_id)

    log.info("Order lookup completed",
             order_id=order_id,
             order_status=order.status,
             processing_time_ms=45.2)

    return order

async def fetch_order_from_db(order_id: str):
    # Trace ID automatically included in logs
    log.debug("Database query started", query="SELECT * FROM orders WHERE id = %s")
    # Database logic here
    log.debug("Database query completed", rows_returned=1)
    return {"id": order_id, "status": "shipped"}
```

**Custom trace ID sources:**

```python
from fapilog.middleware import TraceIDMiddleware

# Use existing header from load balancer
app.add_middleware(
    TraceIDMiddleware,
    trace_id_header="X-Request-ID"  # Use LB trace ID
)

# Or generate custom trace IDs
def custom_trace_generator():
    import uuid
    return f"api-{uuid.uuid4().hex[:8]}"

app.add_middleware(
    TraceIDMiddleware,
    trace_id_generator=custom_trace_generator
)
```

### Request/Response Logging

**Automatic HTTP request and response logging:**

```python
from fastapi import FastAPI, HTTPException
from fapilog import configure_logging, log

app = FastAPI()
configure_logging(app=app)

@app.post("/api/users")
async def create_user(user: dict):
    try:
        # Request automatically logged with:
        # - Method, path, headers
        # - Request body size
        # - Client IP, user agent
        # - Trace ID

        log.info("User creation started", email=user.get("email"))

        # Your business logic
        user_id = await create_user_in_db(user)

        log.info("User created successfully",
                 user_id=user_id,
                 email=user["email"])

        return {"user_id": user_id, "status": "created"}

    except ValueError as e:
        log.error("User creation failed",
                  error=str(e),
                  user_data=user)
        raise HTTPException(status_code=400, detail=str(e))

# Automatic response logging includes:
# - Status code
# - Response body size
# - Processing time
# - Trace ID in response headers
```

**Output example:**

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "info",
  "event": "User creation started",
  "trace_id": "req-abc123-def456",
  "span_id": "span-789ghi-012jkl",
  "method": "POST",
  "path": "/api/users",
  "client_ip": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "req_bytes": 156,
  "email": "user@example.com"
}
```

### Performance Tracking

**Automatic performance monitoring:**

```python
from fastapi import FastAPI
from fapilog import configure_logging, log
import time

app = FastAPI()
configure_logging(app=app)

@app.get("/api/analytics/report")
async def generate_report(query: str):
    start_time = time.time()

    log.info("Report generation started",
             query=query,
             estimated_duration="30s")

    # Simulate complex processing
    await process_large_dataset(query)

    duration = time.time() - start_time
    log.info("Report generation completed",
             query=query,
             duration_seconds=duration,
             performance_tier="normal" if duration < 10 else "slow")

    return {"report": "data", "generated_in": duration}

# Response headers automatically include:
# X-Response-Time-ms: 1234
# X-Trace-Id: req-abc123-def456
```

[↑ Back to top](#fastapi-integration-guide)

---

## Context Management

### User Context Enrichment

**Automatically enrich logs with user information:**

```python
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer
from fapilog import configure_logging, log
from fapilog._internal.context import bind_context

app = FastAPI()
configure_logging(app=app)

security = HTTPBearer()

async def get_current_user(token: str = Depends(security)):
    """Extract user from JWT token."""
    try:
        # Your authentication logic
        user = await verify_jwt_token(token.credentials)

        # Bind user context for all subsequent logs
        bind_context(
            user_id=user["id"],
            user_email=user["email"],
            user_role=user["role"],
            tenant_id=user.get("tenant_id")
        )

        return user
    except Exception as e:
        log.error("Authentication failed", error=str(e))
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/api/profile")
async def get_profile(user = Depends(get_current_user)):
    # All logs automatically include user context
    log.info("Profile requested")  # Includes user_id, user_email, etc.

    # Load user profile
    profile = await load_user_profile(user["id"])

    log.info("Profile loaded",
             profile_completeness=profile.get("completeness", 0))

    return profile

async def verify_jwt_token(token: str):
    # Your JWT verification logic
    return {"id": "user123", "email": "user@example.com", "role": "admin"}

async def load_user_profile(user_id: str):
    # User context automatically included in logs
    log.debug("Loading profile from database")
    return {"name": "John Doe", "completeness": 85}
```

### Custom Context

**Add application-specific context:**

```python
from fastapi import FastAPI, Request, BackgroundTasks
from fapilog import configure_logging, log
from fapilog._internal.context import bind_context

app = FastAPI()
configure_logging(app=app)

@app.middleware("http")
async def add_custom_context(request: Request, call_next):
    # Add request-specific context
    bind_context(
        api_version="v2",
        client_version=request.headers.get("X-Client-Version", "unknown"),
        feature_flags=await get_user_feature_flags(request),
        request_source=determine_request_source(request)
    )

    response = await call_next(request)
    return response

@app.post("/api/orders")
async def create_order(order_data: dict, background_tasks: BackgroundTasks):
    # Context automatically included in all logs
    log.info("Order creation started",
             order_total=order_data.get("total"),
             item_count=len(order_data.get("items", [])))

    # Background task also inherits context
    background_tasks.add_task(send_order_confirmation, order_data)

    return {"order_id": "order123", "status": "processing"}

async def send_order_confirmation(order_data: dict):
    # Context from the original request is preserved
    log.info("Sending order confirmation email")
    # Email sending logic
```

### Context Propagation

**Ensure context flows through async operations:**

```python
from fastapi import FastAPI
from fapilog import configure_logging, log
from fapilog._internal.context import bind_context, get_context
import asyncio

app = FastAPI()
configure_logging(app=app)

@app.post("/api/batch-process")
async def batch_process(items: list):
    # Set processing context
    bind_context(
        batch_id=f"batch-{len(items)}-{int(time.time())}",
        batch_size=len(items),
        processing_mode="parallel"
    )

    log.info("Batch processing started")

    # Process items in parallel while preserving context
    tasks = [process_item_with_context(item, i) for i, item in enumerate(items)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    successful = len([r for r in results if not isinstance(r, Exception)])
    failed = len(results) - successful

    log.info("Batch processing completed",
             successful_items=successful,
             failed_items=failed)

    return {"processed": successful, "failed": failed}

async def process_item_with_context(item: dict, index: int):
    """Process individual item while preserving parent context."""
    # Get current context and add item-specific data
    current_context = get_context()
    bind_context(
        **current_context,  # Preserve parent context
        item_index=index,
        item_id=item.get("id"),
        item_type=item.get("type")
    )

    try:
        log.info("Processing item", item_id=item.get("id"))

        # Simulate processing
        await asyncio.sleep(0.1)

        log.info("Item processed successfully")
        return {"status": "success", "item_id": item.get("id")}

    except Exception as e:
        log.error("Item processing failed", error=str(e))
        return {"status": "failed", "item_id": item.get("id"), "error": str(e)}
```

[↑ Back to top](#fastapi-integration-guide)

---

## Error Handling

### Exception Middleware

**Global error handling with rich context:**

```python
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fapilog import configure_logging, log
import traceback

app = FastAPI()
configure_logging(app=app)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with comprehensive logging."""

    # Log the exception with full context
    log.error("Unhandled exception occurred",
              exception_type=type(exc).__name__,
              exception_message=str(exc),
              request_method=request.method,
              request_url=str(request.url),
              request_headers=dict(request.headers),
              stack_trace=traceback.format_exc())

    # Return appropriate error response
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail, "trace_id": get_current_trace_id()}
        )

    # For unexpected exceptions, return generic error
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "trace_id": get_current_trace_id(),
            "message": "An unexpected error occurred"
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with context."""

    log.warning("HTTP exception",
                status_code=exc.status_code,
                detail=exc.detail,
                request_path=request.url.path)

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "trace_id": get_current_trace_id()
        }
    )
```

### Error Context

**Add rich error context to logs:**

```python
from fastapi import FastAPI, HTTPException
from fapilog import configure_logging, log

app = FastAPI()
configure_logging(app=app)

@app.get("/api/users/{user_id}")
async def get_user(user_id: str):
    try:
        log.info("User lookup started", user_id=user_id)

        # Simulate database operation
        user = await fetch_user_from_database(user_id)

        if not user:
            log.warning("User not found",
                       user_id=user_id,
                       lookup_method="database_query",
                       search_criteria={"id": user_id})

            raise HTTPException(
                status_code=404,
                detail=f"User {user_id} not found"
            )

        log.info("User found successfully",
                 user_id=user_id,
                 user_status=user.get("status"),
                 last_login=user.get("last_login"))

        return user

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        # Log unexpected errors with context
        log.error("User lookup failed",
                  user_id=user_id,
                  error_type=type(e).__name__,
                  error_message=str(e),
                  operation="fetch_user_from_database",
                  recovery_action="manual_investigation_required")

        raise HTTPException(
            status_code=500,
            detail="Internal server error during user lookup"
        )

async def fetch_user_from_database(user_id: str):
    """Simulate database operation with error scenarios."""
    log.debug("Executing database query",
              query_type="user_lookup",
              parameters={"user_id": user_id})

    # Simulate various error conditions
    if user_id == "error_user":
        raise ConnectionError("Database connection failed")
    elif user_id == "timeout_user":
        raise TimeoutError("Database query timeout")
    elif user_id == "missing_user":
        return None

    return {
        "id": user_id,
        "name": "John Doe",
        "status": "active",
        "last_login": "2024-01-15T10:30:45Z"
    }
```

### Error Recovery

**Graceful degradation with fallback mechanisms:**

```python
from fastapi import FastAPI
from fapilog import configure_logging, log
import asyncio

app = FastAPI()
configure_logging(app=app)

@app.get("/api/recommendations/{user_id}")
async def get_recommendations(user_id: str):
    """Get user recommendations with fallback strategies."""

    try:
        # Primary recommendation service
        recommendations = await get_ml_recommendations(user_id)

        log.info("ML recommendations retrieved",
                 user_id=user_id,
                 recommendation_count=len(recommendations),
                 source="ml_service")

        return {"recommendations": recommendations, "source": "ml"}

    except Exception as e:
        log.warning("ML service failed, falling back to rule-based",
                   user_id=user_id,
                   ml_error=str(e),
                   fallback_strategy="rule_based")

        try:
            # Fallback to rule-based recommendations
            recommendations = await get_rule_based_recommendations(user_id)

            log.info("Rule-based recommendations retrieved",
                     user_id=user_id,
                     recommendation_count=len(recommendations),
                     source="rule_based")

            return {"recommendations": recommendations, "source": "fallback"}

        except Exception as fallback_error:
            log.error("All recommendation services failed",
                     user_id=user_id,
                     ml_error=str(e),
                     fallback_error=str(fallback_error),
                     final_strategy="default_recommendations")

            # Last resort: default recommendations
            return {
                "recommendations": get_default_recommendations(),
                "source": "default",
                "message": "Using default recommendations due to service issues"
            }

async def get_ml_recommendations(user_id: str):
    """Simulate ML service call."""
    log.debug("Calling ML recommendation service")
    # Simulate occasional failures
    if user_id == "ml_fail":
        raise Exception("ML service unavailable")

    await asyncio.sleep(0.1)  # Simulate API call
    return ["item1", "item2", "item3"]

async def get_rule_based_recommendations(user_id: str):
    """Fallback rule-based recommendations."""
    log.debug("Using rule-based recommendation engine")
    await asyncio.sleep(0.05)  # Faster than ML
    return ["rule_item1", "rule_item2"]

def get_default_recommendations():
    """Last resort recommendations."""
    return ["popular_item1", "popular_item2"]
```

[↑ Back to top](#fastapi-integration-guide)

---

## Authentication Integration

**Common authentication patterns with automatic user context:**

```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fapilog import configure_logging, log
from fapilog._internal.context import bind_context
import jwt
from typing import Optional

app = FastAPI()
configure_logging(app=app)

security = HTTPBearer()

class AuthService:
    """Authentication service with logging integration."""

    def __init__(self, secret_key: str):
        self.secret_key = secret_key

    async def get_current_user(
        self,
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> dict:
        """Extract and validate user from JWT token."""

        try:
            log.debug("Validating authentication token")

            # Decode JWT token
            payload = jwt.decode(
                credentials.credentials,
                self.secret_key,
                algorithms=["HS256"]
            )

            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: missing user ID"
                )

            # Load user details
            user = await self.load_user(user_id)

            if not user:
                log.warning("Token valid but user not found",
                           user_id=user_id,
                           token_issued_at=payload.get("iat"))

                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )

            # Bind user context for all subsequent logs in this request
            bind_context(
                user_id=user["id"],
                user_email=user["email"],
                user_role=user["role"],
                user_permissions=user.get("permissions", []),
                session_id=payload.get("session_id"),
                token_expires_at=payload.get("exp")
            )

            log.info("User authenticated successfully",
                     user_id=user["id"],
                     user_role=user["role"])

            return user

        except jwt.ExpiredSignatureError:
            log.warning("Authentication failed: token expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            log.warning("Authentication failed: invalid token",
                       token_error=str(e))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        except Exception as e:
            log.error("Authentication service error",
                     error=str(e),
                     error_type=type(e).__name__)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service unavailable"
            )

    async def load_user(self, user_id: str) -> Optional[dict]:
        """Load user details from database."""
        log.debug("Loading user from database", user_id=user_id)

        # Simulate database lookup
        users_db = {
            "user123": {
                "id": "user123",
                "email": "john@example.com",
                "role": "admin",
                "permissions": ["read", "write", "admin"]
            },
            "user456": {
                "id": "user456",
                "email": "jane@example.com",
                "role": "user",
                "permissions": ["read"]
            }
        }

        return users_db.get(user_id)

# Initialize auth service
auth_service = AuthService(secret_key="your-secret-key")

@app.post("/api/admin/users")
async def create_user(
    user_data: dict,
    current_user: dict = Depends(auth_service.get_current_user)
):
    """Admin endpoint with role-based access control."""

    # Check permissions (user context already bound)
    if current_user["role"] != "admin":
        log.warning("Unauthorized access attempt",
                   required_role="admin",
                   user_role=current_user["role"],
                   attempted_action="create_user")

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    log.info("User creation started",
             target_email=user_data.get("email"),
             created_by=current_user["id"])

    # User creation logic
    new_user_id = "new_user_123"

    log.info("User created successfully",
             new_user_id=new_user_id,
             created_by=current_user["id"],
             user_email=user_data.get("email"))

    return {"user_id": new_user_id, "status": "created"}

@app.get("/api/profile")
async def get_profile(current_user: dict = Depends(auth_service.get_current_user)):
    """Get current user profile."""

    # User context automatically included in all logs
    log.info("Profile requested")

    return {
        "user_id": current_user["id"],
        "email": current_user["email"],
        "role": current_user["role"]
    }
```

[↑ Back to top](#fastapi-integration-guide)

---

## Real-World Examples

### REST API Service

**Complete REST API with comprehensive logging:**

```python
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fapilog import configure_logging, log
from fapilog._internal.context import bind_context
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Optional, List
import uuid

# Data models
class UserCreate(BaseModel):
    email: str
    name: str
    role: str = "user"

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    created_at: str

class TaskCreate(BaseModel):
    title: str
    description: str
    priority: str = "medium"

# Application lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle with logging."""

    # Startup
    log.info("API service starting",
             version=app.version,
             environment="production")

    # Initialize services
    await initialize_database()
    await start_background_workers()

    log.info("API service ready")

    yield

    # Shutdown
    log.info("API service shutting down")
    await cleanup_services()
    log.info("API service stopped")

# FastAPI application
app = FastAPI(
    title="Task Management API",
    version="1.0.0",
    lifespan=lifespan
)

# Configure logging with FastAPI integration
configure_logging(app=app)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory database simulation
users_db = {}
tasks_db = {}

@app.post("/api/users", response_model=UserResponse)
async def create_user(user: UserCreate, background_tasks: BackgroundTasks):
    """Create a new user with comprehensive logging."""

    log.info("User creation request",
             email=user.email,
             role=user.role)

    # Validate email uniqueness
    existing_user = next(
        (u for u in users_db.values() if u["email"] == user.email),
        None
    )

    if existing_user:
        log.warning("User creation failed: email exists",
                   email=user.email,
                   existing_user_id=existing_user["id"])

        raise HTTPException(
            status_code=400,
            detail="Email already exists"
        )

    # Create user
    user_id = str(uuid.uuid4())
    new_user = {
        "id": user_id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "created_at": "2024-01-15T10:30:45Z"
    }

    users_db[user_id] = new_user

    # Background task for user onboarding
    background_tasks.add_task(
        send_welcome_email,
        user_id,
        user.email
    )

    log.info("User created successfully",
             user_id=user_id,
             email=user.email,
             role=user.role)

    return UserResponse(**new_user)

@app.get("/api/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """Get user by ID with error handling."""

    log.info("User lookup", user_id=user_id)

    user = users_db.get(user_id)

    if not user:
        log.warning("User not found",
                   user_id=user_id,
                   total_users=len(users_db))

        raise HTTPException(status_code=404, detail="User not found")

    log.info("User found",
             user_id=user_id,
             user_role=user["role"])

    return UserResponse(**user)

@app.get("/api/users", response_model=List[UserResponse])
async def list_users(skip: int = 0, limit: int = 100):
    """List users with pagination logging."""

    log.info("User list request",
             skip=skip,
             limit=limit,
             total_users=len(users_db))

    users_list = list(users_db.values())[skip:skip + limit]

    log.info("User list response",
             returned_users=len(users_list),
             skip=skip,
             limit=limit)

    return [UserResponse(**user) for user in users_list]

@app.post("/api/users/{user_id}/tasks")
async def create_task(user_id: str, task: TaskCreate):
    """Create task for user with context binding."""

    # Verify user exists
    user = users_db.get(user_id)
    if not user:
        log.warning("Task creation failed: user not found", user_id=user_id)
        raise HTTPException(status_code=404, detail="User not found")

    # Bind user context
    bind_context(
        user_id=user_id,
        user_email=user["email"],
        user_role=user["role"]
    )

    log.info("Task creation started",
             task_title=task.title,
             task_priority=task.priority)

    # Create task
    task_id = str(uuid.uuid4())
    new_task = {
        "id": task_id,
        "user_id": user_id,
        "title": task.title,
        "description": task.description,
        "priority": task.priority,
        "status": "pending",
        "created_at": "2024-01-15T10:30:45Z"
    }

    tasks_db[task_id] = new_task

    log.info("Task created successfully",
             task_id=task_id,
             task_title=task.title)

    return {"task_id": task_id, "status": "created"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""

    log.debug("Health check requested")

    health_status = {
        "status": "healthy",
        "users_count": len(users_db),
        "tasks_count": len(tasks_db),
        "timestamp": "2024-01-15T10:30:45Z"
    }

    return health_status

# Background task functions
async def send_welcome_email(user_id: str, email: str):
    """Send welcome email with context preservation."""

    # Context from the original request is preserved
    log.info("Sending welcome email",
             user_id=user_id,
             email=email)

    # Simulate email sending
    await asyncio.sleep(1)

    log.info("Welcome email sent successfully",
             user_id=user_id,
             email=email)

# Service initialization functions
async def initialize_database():
    log.info("Database initialization started")
    # Database setup logic
    log.info("Database initialization completed")

async def start_background_workers():
    log.info("Background workers starting")
    # Worker setup logic
    log.info("Background workers started")

async def cleanup_services():
    log.info("Cleaning up services")
    # Cleanup logic
    log.info("Services cleaned up")
```

### Microservice Architecture

**Service-to-service communication with trace propagation:**

```python
from fastapi import FastAPI, Request
from fapilog import configure_logging, log, get_current_trace_id
import httpx
import asyncio

# Order Service
order_app = FastAPI(title="Order Service")
configure_logging(order_app)

@order_app.post("/orders")
async def create_order(order_data: dict):
    """Create order with service-to-service calls."""

    order_id = f"order-{uuid.uuid4().hex[:8]}"
    trace_id = get_current_trace_id()

    log.info("Order creation started",
             order_id=order_id,
             customer_id=order_data.get("customer_id"),
             total_amount=order_data.get("total"))

    try:
        # Call inventory service
        inventory_result = await call_inventory_service(
            order_data["items"],
            trace_id
        )

        # Call payment service
        payment_result = await call_payment_service(
            order_data["payment_info"],
            order_data["total"],
            trace_id
        )

        # Call notification service
        await call_notification_service(
            order_data["customer_id"],
            order_id,
            trace_id
        )

        log.info("Order created successfully",
                 order_id=order_id,
                 inventory_reserved=inventory_result["reserved"],
                 payment_processed=payment_result["processed"])

        return {
            "order_id": order_id,
            "status": "confirmed",
            "trace_id": trace_id
        }

    except Exception as e:
        log.error("Order creation failed",
                  order_id=order_id,
                  error=str(e))
        raise

async def call_inventory_service(items: list, trace_id: str):
    """Call inventory service with trace propagation."""

    log.info("Calling inventory service",
             service="inventory",
             item_count=len(items))

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://inventory-service/reserve",
            json={"items": items},
            headers={"X-Trace-ID": trace_id}
        )

        result = response.json()

        log.info("Inventory service response",
                 service="inventory",
                 status_code=response.status_code,
                 reserved_items=result.get("reserved", 0))

        return result

async def call_payment_service(payment_info: dict, amount: float, trace_id: str):
    """Call payment service with trace propagation."""

    log.info("Calling payment service",
             service="payment",
             amount=amount)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://payment-service/process",
            json={"payment_info": payment_info, "amount": amount},
            headers={"X-Trace-ID": trace_id}
        )

        result = response.json()

        log.info("Payment service response",
                 service="payment",
                 status_code=response.status_code,
                 transaction_id=result.get("transaction_id"))

        return result

async def call_notification_service(customer_id: str, order_id: str, trace_id: str):
    """Call notification service asynchronously."""

    log.info("Calling notification service",
             service="notification",
             customer_id=customer_id)

    # Fire and forget notification
    asyncio.create_task(
        send_notification_async(customer_id, order_id, trace_id)
    )

async def send_notification_async(customer_id: str, order_id: str, trace_id: str):
    """Send notification with preserved trace context."""

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://notification-service/send",
                json={
                    "customer_id": customer_id,
                    "order_id": order_id,
                    "type": "order_confirmation"
                },
                headers={"X-Trace-ID": trace_id}
            )

            log.info("Notification sent",
                     service="notification",
                     customer_id=customer_id,
                     status_code=response.status_code)

    except Exception as e:
        log.error("Notification failed",
                  service="notification",
                  customer_id=customer_id,
                  error=str(e))
```

### WebSocket Applications

**Real-time applications with connection tracking:**

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fapilog import configure_logging, log
from fapilog._internal.context import bind_context
import asyncio
import json
from typing import Dict, Set

app = FastAPI(title="Chat Service")
configure_logging(app)

# Connection management
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[str, Set[str]] = {}

    async def connect(self, websocket: WebSocket, connection_id: str, user_id: str):
        """Accept WebSocket connection with logging."""

        await websocket.accept()
        self.active_connections[connection_id] = websocket

        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)

        log.info("WebSocket connection established",
                 connection_id=connection_id,
                 user_id=user_id,
                 total_connections=len(self.active_connections))

    def disconnect(self, connection_id: str, user_id: str):
        """Remove WebSocket connection with logging."""

        if connection_id in self.active_connections:
            del self.active_connections[connection_id]

        if user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

        log.info("WebSocket connection closed",
                 connection_id=connection_id,
                 user_id=user_id,
                 total_connections=len(self.active_connections))

    async def send_personal_message(self, message: str, connection_id: str):
        """Send message to specific connection."""

        websocket = self.active_connections.get(connection_id)
        if websocket:
            await websocket.send_text(message)
            log.debug("Personal message sent",
                     connection_id=connection_id,
                     message_length=len(message))

    async def broadcast_to_user(self, message: str, user_id: str):
        """Send message to all user connections."""

        connections = self.user_connections.get(user_id, set())

        for connection_id in connections:
            websocket = self.active_connections.get(connection_id)
            if websocket:
                try:
                    await websocket.send_text(message)
                except Exception as e:
                    log.error("Failed to send message",
                             connection_id=connection_id,
                             user_id=user_id,
                             error=str(e))

manager = ConnectionManager()

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint with comprehensive logging."""

    connection_id = f"conn-{uuid.uuid4().hex[:8]}"

    # Bind connection context
    bind_context(
        connection_id=connection_id,
        user_id=user_id,
        connection_type="websocket"
    )

    try:
        await manager.connect(websocket, connection_id, user_id)

        # Send welcome message
        welcome_msg = json.dumps({
            "type": "welcome",
            "connection_id": connection_id,
            "user_id": user_id
        })
        await websocket.send_text(welcome_msg)

        # Message handling loop
        while True:
            # Receive message
            data = await websocket.receive_text()

            try:
                message = json.loads(data)

                log.info("Message received",
                         message_type=message.get("type"),
                         message_length=len(data))

                # Handle different message types
                if message["type"] == "chat":
                    await handle_chat_message(message, user_id, connection_id)
                elif message["type"] == "typing":
                    await handle_typing_indicator(message, user_id)
                elif message["type"] == "ping":
                    await handle_ping(websocket, connection_id)
                else:
                    log.warning("Unknown message type",
                               message_type=message.get("type"))

            except json.JSONDecodeError:
                log.warning("Invalid JSON message received",
                           raw_message=data)

                error_msg = json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
                await websocket.send_text(error_msg)

            except Exception as e:
                log.error("Message processing error",
                         error=str(e),
                         message_data=data)

    except WebSocketDisconnect:
        log.info("WebSocket disconnected normally")

    except Exception as e:
        log.error("WebSocket error",
                 error=str(e),
                 error_type=type(e).__name__)

    finally:
        manager.disconnect(connection_id, user_id)

async def handle_chat_message(message: dict, user_id: str, connection_id: str):
    """Handle chat message with context."""

    chat_text = message.get("text", "")
    recipient_id = message.get("recipient_id")

    log.info("Chat message processing",
             sender_id=user_id,
             recipient_id=recipient_id,
             message_length=len(chat_text))

    # Store message (simulate database)
    message_id = f"msg-{uuid.uuid4().hex[:8]}"

    # Forward to recipient
    if recipient_id:
        forward_msg = json.dumps({
            "type": "chat",
            "message_id": message_id,
            "sender_id": user_id,
            "text": chat_text,
            "timestamp": "2024-01-15T10:30:45Z"
        })

        await manager.broadcast_to_user(forward_msg, recipient_id)

        log.info("Chat message forwarded",
                 message_id=message_id,
                 sender_id=user_id,
                 recipient_id=recipient_id)

async def handle_typing_indicator(message: dict, user_id: str):
    """Handle typing indicator."""

    recipient_id = message.get("recipient_id")
    is_typing = message.get("is_typing", False)

    log.debug("Typing indicator",
              sender_id=user_id,
              recipient_id=recipient_id,
              is_typing=is_typing)

    if recipient_id:
        typing_msg = json.dumps({
            "type": "typing",
            "sender_id": user_id,
            "is_typing": is_typing
        })

        await manager.broadcast_to_user(typing_msg, recipient_id)

async def handle_ping(websocket: WebSocket, connection_id: str):
    """Handle ping/pong for connection health."""

    log.debug("Ping received, sending pong")

    pong_msg = json.dumps({
        "type": "pong",
        "timestamp": "2024-01-15T10:30:45Z"
    })

    await websocket.send_text(pong_msg)

@app.get("/api/connections")
async def get_connection_stats():
    """Get connection statistics."""

    stats = {
        "total_connections": len(manager.active_connections),
        "unique_users": len(manager.user_connections),
        "connections_per_user": {
            user_id: len(connections)
            for user_id, connections in manager.user_connections.items()
        }
    }

    log.info("Connection stats requested",
             total_connections=stats["total_connections"],
             unique_users=stats["unique_users"])

    return stats
```

[↑ Back to top](#fastapi-integration-guide)

---

## Production Patterns

### High-Performance Configuration

**Optimize for high-throughput production APIs:**

```python
from fastapi import FastAPI
from fapilog import configure_logging
from fapilog.settings import LoggingSettings

# Production-optimized configuration
production_settings = LoggingSettings(
    # Logging configuration
    level="INFO",  # Reduce log volume
    format="json",  # Structured output for log aggregation

    # High-performance async queue
    queue_enabled=True,
    queue_size=10000,  # Large queue for traffic spikes
    batch_size=100,    # Batch processing for efficiency
    batch_timeout=0.5, # Quick batches for low latency
    overflow_strategy="drop",  # Drop logs under extreme load

    # Performance monitoring
    enable_resource_metrics=True,
    metrics_enabled=True,
    metrics_sample_window=1000,

    # Optimized sinks
    sinks=["stdout", "loki://loki-service:3100?batch_size=200"],

    # Security
    redact_patterns=["password", "token", "secret"],
    redact_fields=["authorization", "x-api-key"],

    # Sampling for high-volume endpoints
    sampling_rate=0.1  # Log 10% of events under load
)

app = FastAPI(title="High-Performance API")
configure_logging(settings=production_settings, app=app)

@app.middleware("http")
async def performance_monitoring(request: Request, call_next):
    """Add performance monitoring context."""

    start_time = time.time()

    # Add performance context
    bind_context(
        endpoint=f"{request.method} {request.url.path}",
        request_size=request.headers.get("content-length", 0)
    )

    response = await call_next(request)

    # Log performance metrics for slow requests only
    duration = time.time() - start_time
    if duration > 1.0:  # Only log slow requests
        log.warning("Slow request detected",
                   duration_seconds=duration,
                   endpoint=f"{request.method} {request.url.path}",
                   status_code=response.status_code)

    return response
```

### Container Deployment

**Docker and Kubernetes integration:**

```python
# Production FastAPI app with container-optimized logging
from fastapi import FastAPI
from fapilog import configure_logging
from fapilog.settings import LoggingSettings
import os

# Container-aware configuration
def get_logging_settings():
    """Get logging settings optimized for containers."""

    # Detect container environment
    is_container = os.path.exists("/.dockerenv") or os.getenv("KUBERNETES_SERVICE_HOST")

    if is_container:
        return LoggingSettings(
            # Container-optimized settings
            format="json",  # Structured logs for log aggregation
            sinks=["stdout"],  # Stdout for container log collection

            # Kubernetes-friendly configuration
            level=os.getenv("LOG_LEVEL", "INFO"),

            # Performance tuning for containers
            queue_enabled=True,
            queue_size=int(os.getenv("LOG_QUEUE_SIZE", "5000")),
            batch_size=int(os.getenv("LOG_BATCH_SIZE", "50")),

            # Resource constraints
            enable_resource_metrics=False,  # Reduce overhead

            # Service mesh integration
            trace_id_header=os.getenv("TRACE_HEADER", "X-Request-ID"),
            enable_httpx_trace_propagation=True
        )
    else:
        # Development settings
        return LoggingSettings(
            format="pretty",
            sinks=["stdout"],
            level="DEBUG"
        )

app = FastAPI(
    title=os.getenv("SERVICE_NAME", "FastAPI Service"),
    version=os.getenv("SERVICE_VERSION", "1.0.0")
)

# Configure logging
settings = get_logging_settings()
configure_logging(settings=settings, app=app)

@app.get("/health")
async def health_check():
    """Kubernetes health check endpoint."""

    # Minimal logging for health checks
    return {"status": "healthy", "service": app.title}

@app.get("/ready")
async def readiness_check():
    """Kubernetes readiness check."""

    # Check dependencies
    ready = await check_dependencies()

    if ready:
        return {"status": "ready"}
    else:
        log.error("Service not ready")
        raise HTTPException(status_code=503, detail="Service not ready")

async def check_dependencies():
    """Check service dependencies."""
    # Database, external services, etc.
    return True
```

### Load Balancer Integration

**Handle load balancer headers and routing:**

```python
from fastapi import FastAPI, Request
from fapilog import configure_logging, log
from fapilog._internal.context import bind_context

app = FastAPI()
configure_logging(app=app)

@app.middleware("http")
async def load_balancer_context(request: Request, call_next):
    """Extract load balancer context and routing information."""

    # Extract load balancer headers
    lb_headers = {
        "x_forwarded_for": request.headers.get("x-forwarded-for"),
        "x_real_ip": request.headers.get("x-real-ip"),
        "x_forwarded_proto": request.headers.get("x-forwarded-proto"),
        "x_forwarded_host": request.headers.get("x-forwarded-host"),
        "x_forwarded_port": request.headers.get("x-forwarded-port")
    }

    # Extract routing information
    route_info = {
        "lb_backend": request.headers.get("x-backend-server"),
        "lb_region": request.headers.get("x-region"),
        "lb_zone": request.headers.get("x-zone"),
        "cdn_cache": request.headers.get("x-cache", "MISS")
    }

    # Bind load balancer context
    bind_context(
        client_ip=get_real_client_ip(request),
        lb_backend=route_info["lb_backend"],
        lb_region=route_info["lb_region"],
        cdn_cache_status=route_info["cdn_cache"],
        forwarded_proto=lb_headers["x_forwarded_proto"]
    )

    # Log routing information for debugging
    if route_info["lb_backend"]:
        log.debug("Request routing",
                 backend_server=route_info["lb_backend"],
                 region=route_info["lb_region"],
                 cdn_status=route_info["cdn_cache"])

    response = await call_next(request)
    return response

def get_real_client_ip(request: Request) -> str:
    """Extract real client IP from load balancer headers."""

    # Try X-Forwarded-For first (load balancer)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # Take the first IP (original client)
        return forwarded_for.split(",")[0].strip()

    # Try X-Real-IP (some load balancers)
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip

    # Fall back to direct connection IP
    return request.client.host if request.client else "unknown"
```

[↑ Back to top](#fastapi-integration-guide)

---

## Performance Optimization

### Async Queue Tuning

**Optimize queue performance for your workload:**

```python
from fastapi import FastAPI
from fapilog import configure_logging
from fapilog.settings import LoggingSettings

# Different configurations for different load patterns

# High-frequency, low-latency API
high_frequency_settings = LoggingSettings(
    queue_enabled=True,
    queue_size=20000,      # Large queue for burst traffic
    batch_size=50,         # Smaller batches for lower latency
    batch_timeout=0.1,     # Quick processing
    overflow_strategy="drop"  # Don't block under load
)

# Batch processing API
batch_processing_settings = LoggingSettings(
    queue_enabled=True,
    queue_size=5000,       # Smaller queue for steady load
    batch_size=200,        # Larger batches for efficiency
    batch_timeout=2.0,     # Longer timeout for batching
    overflow_strategy="sample"  # Adaptive sampling
)

# Real-time API
realtime_settings = LoggingSettings(
    queue_enabled=True,
    queue_size=10000,
    batch_size=1,          # Immediate processing
    batch_timeout=0.01,    # Minimal delay
    overflow_strategy="drop"
)

# Select configuration based on environment
import os
load_pattern = os.getenv("LOAD_PATTERN", "high_frequency")

if load_pattern == "high_frequency":
    settings = high_frequency_settings
elif load_pattern == "batch":
    settings = batch_processing_settings
elif load_pattern == "realtime":
    settings = realtime_settings
else:
    settings = LoggingSettings()  # Defaults

app = FastAPI()
configure_logging(settings=settings, app=app)
```

### Selective Logging

**Log only what matters in production:**

```python
from fastapi import FastAPI, Request
from fapilog import configure_logging, log
import re

app = FastAPI()
configure_logging(app=app)

# Define logging rules
SKIP_PATHS = {"/health", "/metrics", "/favicon.ico"}
LOG_ALL_ERRORS = True
LOG_SLOW_REQUESTS_THRESHOLD = 1.0  # seconds
LOG_LARGE_RESPONSES_THRESHOLD = 1024 * 1024  # 1MB

@app.middleware("http")
async def selective_logging_middleware(request: Request, call_next):
    """Only log requests that meet certain criteria."""

    start_time = time.time()

    # Skip logging for certain paths
    if request.url.path in SKIP_PATHS:
        return await call_next(request)

    # Always log API endpoints
    is_api_endpoint = request.url.path.startswith("/api/")

    response = await call_next(request)

    duration = time.time() - start_time
    response_size = response.headers.get("content-length", 0)

    # Determine if we should log this request
    should_log = (
        LOG_ALL_ERRORS and response.status_code >= 400 or
        duration > LOG_SLOW_REQUESTS_THRESHOLD or
        int(response_size) > LOG_LARGE_RESPONSES_THRESHOLD or
        is_api_endpoint
    )

    if should_log:
        log_level = "error" if response.status_code >= 400 else "info"

        getattr(log, log_level)(
            "Request processed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration * 1000,
            response_size=response_size,
            is_slow=duration > LOG_SLOW_REQUESTS_THRESHOLD,
            is_large_response=int(response_size) > LOG_LARGE_RESPONSES_THRESHOLD
        )

    return response

@app.get("/api/data/export")
async def export_large_dataset():
    """Endpoint that generates large responses."""

    log.info("Large dataset export started")

    # Generate large response
    data = {"records": [{"id": i, "value": f"data_{i}"} for i in range(10000)]}

    log.info("Large dataset export completed",
             record_count=len(data["records"]))

    return data
```

### Memory Management

**Optimize memory usage for logging:**

```python
from fastapi import FastAPI
from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings
import gc

# Memory-efficient logging configuration
memory_optimized_settings = LoggingSettings(
    # Smaller queue to reduce memory footprint
    queue_size=2000,
    batch_size=100,
    batch_timeout=1.0,

    # Disable resource metrics to save memory
    enable_resource_metrics=False,

    # Aggressive sampling under load
    sampling_rate=0.5,
    overflow_strategy="drop",

    # Simplified sinks
    sinks=["stdout"]
)

app = FastAPI()
configure_logging(settings=memory_optimized_settings, app=app)

@app.middleware("http")
async def memory_monitoring_middleware(request: Request, call_next):
    """Monitor memory usage and trigger cleanup if needed."""

    import psutil
    import os

    # Get memory usage before request
    process = psutil.Process(os.getpid())
    memory_before = process.memory_info().rss / 1024 / 1024  # MB

    response = await call_next(request)

    # Check memory usage after request
    memory_after = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = memory_after - memory_before

    # Log significant memory increases
    if memory_increase > 10:  # More than 10MB increase
        log.warning("High memory usage detected",
                   memory_before_mb=memory_before,
                   memory_after_mb=memory_after,
                   memory_increase_mb=memory_increase,
                   endpoint=request.url.path)

    # Trigger garbage collection for large memory usage
    if memory_after > 500:  # More than 500MB
        log.info("Triggering garbage collection",
                 memory_usage_mb=memory_after)
        gc.collect()

    return response
```

[↑ Back to top](#fastapi-integration-guide)

---

## Monitoring Integration

### Health Checks

**Integrate logging health into application health checks:**

```python
from fastapi import FastAPI, HTTPException
from fapilog import configure_logging, log
from fapilog.monitoring import get_metrics_dict
import asyncio

app = FastAPI()
configure_logging(app=app)

@app.get("/health")
async def health_check():
    """Basic health check."""
    return {"status": "healthy"}

@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check including logging system."""

    health_status = {
        "status": "healthy",
        "timestamp": "2024-01-15T10:30:45Z",
        "checks": {}
    }

    # Check logging system health
    try:
        logging_metrics = get_metrics_dict()

        # Check queue health
        queue_metrics = logging_metrics.get("queue", {})
        queue_size = queue_metrics.get("size", 0)
        queue_peak = queue_metrics.get("peak_size", 0)

        if queue_size > 8000:  # Queue getting full
            health_status["checks"]["logging_queue"] = {
                "status": "warning",
                "message": f"Queue size high: {queue_size}",
                "current_size": queue_size,
                "peak_size": queue_peak
            }
        else:
            health_status["checks"]["logging_queue"] = {
                "status": "healthy",
                "current_size": queue_size,
                "peak_size": queue_peak
            }

        # Check sink health
        sink_metrics = logging_metrics.get("sinks", {})
        failed_sinks = []

        for sink_name, sink_data in sink_metrics.items():
            error_rate = sink_data.get("error_rate", 0)
            if error_rate > 0.1:  # More than 10% error rate
                failed_sinks.append(sink_name)

        if failed_sinks:
            health_status["checks"]["logging_sinks"] = {
                "status": "error",
                "message": f"Sinks with high error rate: {failed_sinks}",
                "failed_sinks": failed_sinks
            }
            health_status["status"] = "unhealthy"
        else:
            health_status["checks"]["logging_sinks"] = {
                "status": "healthy",
                "active_sinks": list(sink_metrics.keys())
            }

    except Exception as e:
        health_status["checks"]["logging_system"] = {
            "status": "error",
            "message": f"Logging system check failed: {e}"
        }
        health_status["status"] = "unhealthy"

    # Check other application components
    health_status["checks"]["database"] = await check_database_health()
    health_status["checks"]["external_apis"] = await check_external_apis()

    # Log health check results
    log.info("Health check performed",
             overall_status=health_status["status"],
             failed_checks=[
                 name for name, check in health_status["checks"].items()
                 if check["status"] != "healthy"
             ])

    if health_status["status"] != "healthy":
        raise HTTPException(status_code=503, detail=health_status)

    return health_status

async def check_database_health():
    """Check database connectivity."""
    try:
        # Database health check logic
        await asyncio.sleep(0.01)  # Simulate check
        return {"status": "healthy", "response_time_ms": 10}
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def check_external_apis():
    """Check external API dependencies."""
    try:
        # External API health check logic
        await asyncio.sleep(0.02)  # Simulate check
        return {"status": "healthy", "response_time_ms": 20}
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

### Metrics Endpoints

**Expose logging metrics for monitoring:**

```python
from fastapi import FastAPI
from fapilog import configure_logging
from fapilog.monitoring import get_metrics_text, get_metrics_dict, start_metrics_server

app = FastAPI()
configure_logging(app=app)

@app.on_event("startup")
async def start_prometheus_server():
    """Start Prometheus metrics server."""

    # Start metrics server on port 8000
    await start_metrics_server(port=8000)
    log.info("Prometheus metrics server started on port 8000")

@app.get("/metrics")
async def get_prometheus_metrics():
    """Prometheus metrics endpoint."""

    from fastapi.responses import PlainTextResponse

    metrics_text = get_metrics_text()

    return PlainTextResponse(
        content=metrics_text,
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )

@app.get("/api/metrics")
async def get_json_metrics():
    """JSON metrics endpoint for application monitoring."""

    metrics = get_metrics_dict()

    # Add application-specific metrics
    app_metrics = {
        "application": {
            "name": app.title,
            "version": "1.0.0",
            "uptime_seconds": get_application_uptime()
        },
        "logging": metrics
    }

    return app_metrics

def get_application_uptime():
    """Get application uptime in seconds."""
    import time
    # Application start time would be stored at startup
    return time.time() - getattr(app.state, "start_time", time.time())
```

[↑ Back to top](#fastapi-integration-guide)

---

## Troubleshooting

### Common Issues

**1. Middleware not working**

```python
# Problem: Logs don't have trace IDs
from fastapi import FastAPI
from fapilog import configure_logging

app = FastAPI()
configure_logging()  # Missing app parameter!

# Solution: Pass app to configure_logging
configure_logging(app=app)  # This adds middleware automatically
```

**2. Context not propagating to background tasks**

```python
# Problem: Background tasks lose request context
@app.post("/users")
async def create_user(user_data: dict, background_tasks: BackgroundTasks):
    log.info("Creating user")  # Has context
    background_tasks.add_task(send_email, user_data)  # Loses context!

# Solution: Capture context before background task
from fapilog._internal.context import get_context

@app.post("/users")
async def create_user(user_data: dict, background_tasks: BackgroundTasks):
    current_context = get_context()
    background_tasks.add_task(send_email_with_context, user_data, current_context)

async def send_email_with_context(user_data: dict, context: dict):
    bind_context(**context)  # Restore context
    log.info("Sending email")  # Now has context
```

**3. Performance issues with high-volume logging**

```python
# Problem: Logging blocking application
settings = LoggingSettings(
    queue_enabled=False,  # Synchronous logging!
    level="DEBUG"         # Too verbose!
)

# Solution: Enable async queue and appropriate level
settings = LoggingSettings(
    queue_enabled=True,
    queue_size=10000,
    level="INFO",         # Less verbose
    sampling_rate=0.1     # Sample high-volume endpoints
)
```

**4. Memory leaks with long-running processes**

```python
# Problem: Context accumulating over time
@app.middleware("http")
async def context_middleware(request: Request, call_next):
    bind_context(user_id="123")  # Context never cleared!
    response = await call_next(request)
    return response

# Solution: Clear context after request
@app.middleware("http")
async def context_middleware(request: Request, call_next):
    try:
        bind_context(user_id="123")
        response = await call_next(request)
        return response
    finally:
        clear_context()  # Clean up
```

### Debug Mode

**Enable debug logging to troubleshoot issues:**

```python
from fapilog import configure_logging
from fapilog.settings import LoggingSettings
import logging

# Enable debug logging for fapilog itself
logging.getLogger("fapilog").setLevel(logging.DEBUG)

# Debug configuration
debug_settings = LoggingSettings(
    level="DEBUG",
    format="pretty",
    queue_enabled=False,  # Synchronous for debugging
    enable_resource_metrics=True
)

configure_logging(settings=debug_settings)

# Test middleware
@app.get("/debug/test")
async def debug_test():
    log.debug("Debug endpoint called")
    log.info("Info message")
    log.warning("Warning message")
    log.error("Error message")
    return {"debug": "complete"}
```

[↑ Back to top](#fastapi-integration-guide)

---

## Best Practices

### 1. **Middleware Design Principles**

- **Use automatic middleware** via `configure_logging(app=app)` for simplicity
- **Add manual middleware** only when you need custom configuration
- **Order matters** - place logging middleware early in the stack
- **Handle exceptions** gracefully in custom middleware

### 2. **Context Management**

- **Bind context early** in the request lifecycle
- **Keep context lightweight** - avoid large objects
- **Clear context** in long-running processes
- **Preserve context** across async operations when needed

### 3. **Performance Optimization**

- **Enable async queue** for production workloads
- **Tune queue size** based on your traffic patterns
- **Use sampling** for high-volume endpoints
- **Monitor memory usage** with resource metrics

### 4. **Error Handling**

- **Log errors with context** - include request details
- **Use appropriate log levels** - error for exceptions, warning for handled issues
- **Add trace IDs to error responses** for debugging
- **Don't log and re-raise** - let exception handlers manage logging

### 5. **Production Deployment**

- **Use JSON format** for log aggregation
- **Configure appropriate log levels** (INFO or WARNING for production)
- **Set up health checks** that include logging system status
- **Monitor queue health** and sink performance

### 6. **Security Considerations**

- **Redact sensitive data** using built-in redaction patterns
- **Limit log retention** for compliance
- **Secure log transmission** when using remote sinks
- **Avoid logging credentials** or tokens

---

## Summary

This guide covered:

- **Basic Integration** - One-line setup and automatic middleware
- **Advanced Features** - Context management, trace propagation, error handling
- **Real-World Examples** - REST APIs, microservices, WebSocket applications
- **Production Patterns** - Performance optimization, container deployment
- **Monitoring Integration** - Health checks, metrics, observability
- **Troubleshooting** - Common issues and debugging techniques

**Next steps:**

- Try the [Configuration Guide](configuration.md) for advanced settings
- See [Performance Guide](performance.md) for optimization techniques
- Check [API Reference](../api-reference.md) for detailed function documentation

[↑ Back to top](#fastapi-integration-guide)
