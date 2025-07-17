#!/usr/bin/env python3
"""
Example 18: User Context Enrichment

This example demonstrates the User Context Enrichment feature (Story 6.3)
that automatically adds user information to log contexts in FastAPI applications.

Key features:
- Automatic user context enrichment (user_id, user_roles, auth_scheme)
- Integration with FastAPI authentication dependencies
- Support for different user object types (dict, class-based)
- Graceful handling of unauthenticated requests
- Manual user context binding
- Configuration options

The user context enricher automatically captures authenticated user information
and makes it available in all log events during the request lifecycle.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

from fastapi import FastAPI, HTTPException, Request, Depends, status
from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials,
    OAuth2PasswordBearer,
)
from pydantic import BaseModel

from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings
from fapilog.enrichers import create_user_dependency
from fapilog._internal.context import bind_user_context


# Pydantic models for different user representations
class UserClass(BaseModel):
    """Class-based user model"""

    id: str
    email: str
    roles: List[str]
    permissions: List[str]


class LoginRequest(BaseModel):
    username: str
    password: str


class ApiResponse(BaseModel):
    message: str
    data: Optional[Dict[str, Any]] = None


# Mock user database
USERS_DB = {
    "alice@example.com": {
        "id": "user_123",
        "password": "secret123",
        "email": "alice@example.com",
        "roles": ["admin", "user"],
        "permissions": ["read", "write", "delete"],
    },
    "bob@example.com": {
        "id": "user_456",
        "password": "password456",
        "email": "bob@example.com",
        "roles": ["user"],
        "permissions": ["read"],
    },
}

# Authentication schemes
security_bearer = HTTPBearer()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


# Basic authentication function (returns dict)
async def get_current_user_dict(
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer),
) -> Dict[str, Any]:
    """
    Basic auth function that returns user as dict.
    This simulates JWT token validation or database lookup.
    """
    token = credentials.credentials

    # Simple token validation (in real apps, validate JWT, check DB, etc.)
    if token == "alice_token":
        user_data = USERS_DB["alice@example.com"].copy()
        user_data.pop("password")  # Don't include password in context
        return user_data
    elif token == "bob_token":
        user_data = USERS_DB["bob@example.com"].copy()
        user_data.pop("password")
        return user_data

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


# Advanced authentication function (returns class instance)
async def get_current_user_class(
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer),
) -> UserClass:
    """
    Advanced auth function that returns user as Pydantic model.
    """
    user_dict = await get_current_user_dict(credentials)
    return UserClass(**user_dict)


# Optional authentication (for endpoints that work with/without auth)
async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
) -> Optional[Dict[str, Any]]:
    """
    Optional authentication - returns None if not authenticated.
    """
    if not token:
        return None

    # Validate token
    if token == "alice_token":
        user_data = USERS_DB["alice@example.com"].copy()
        user_data.pop("password")
        return user_data
    elif token == "bob_token":
        user_data = USERS_DB["bob@example.com"].copy()
        user_data.pop("password")
        return user_data

    # Invalid token - return None instead of raising exception
    return None


# Create user context dependencies using the new create_user_dependency function
get_user_with_context = create_user_dependency(get_current_user_dict)
get_user_class_with_context = create_user_dependency(get_current_user_class)
get_user_optional_with_context = create_user_dependency(get_current_user_optional)


# Configure logging with user context enabled
def setup_logging():
    """Configure logging with user context enrichment enabled."""
    settings = LoggingSettings(
        level="INFO",
        json_console=True,
        user_context_enabled=True,  # Enable user context enrichment
        sinks=["stdout://"],
    )

    return configure_logging(settings)


# FastAPI application
async def create_app():
    app = FastAPI(title="User Context Enrichment Example")

    @app.get("/")
    async def root():
        """Public endpoint - no authentication required."""
        log.info("Public endpoint accessed")
        return {"message": "Welcome to the User Context Enrichment example!"}

    @app.post("/auth/login")
    async def login(request: LoginRequest):
        """Login endpoint that returns tokens for testing."""
        if request.username == "alice@example.com" and request.password == "secret123":
            log.info("User login successful", extra={"username": request.username})
            return {"access_token": "alice_token", "token_type": "bearer"}
        elif (
            request.username == "bob@example.com" and request.password == "password456"
        ):
            log.info("User login successful", extra={"username": request.username})
            return {"access_token": "bob_token", "token_type": "bearer"}

        log.warning("Login attempt failed", extra={"username": request.username})
        raise HTTPException(status_code=401, detail="Invalid credentials")

    @app.get("/user/profile")
    async def get_profile(
        current_user: Dict[str, Any] = Depends(get_user_with_context),
    ):
        """
        Protected endpoint using dict-based user auth.
        User context (user_id, user_roles, auth_scheme) is automatically added to logs.
        """
        log.info("User profile accessed")
        return {"message": "Profile retrieved successfully", "user": current_user}

    @app.get("/user/advanced-profile")
    async def get_advanced_profile(
        current_user: UserClass = Depends(get_user_class_with_context),
    ):
        """
        Protected endpoint using class-based user auth.
        Demonstrates user context enrichment with Pydantic models.
        """
        log.info("Advanced user profile accessed")
        return {
            "message": "Advanced profile retrieved",
            "user_id": current_user.id,
            "email": current_user.email,
            "roles": current_user.roles,
        }

    @app.get("/user/dashboard")
    async def dashboard(current_user: Dict[str, Any] = Depends(get_user_with_context)):
        """
        Dashboard endpoint that logs multiple events.
        All logs will include user context automatically.
        """
        log.info("Dashboard access started")

        try:
            # Simulate business logic with multiple log events
            log.info("Loading user preferences")
            await asyncio.sleep(0.1)  # Simulate async operation

            log.info("Loading user data", extra={"data_size": 1024})
            await asyncio.sleep(0.1)

            log.info("Dashboard rendering complete")

            return {
                "message": "Dashboard loaded successfully",
                "user_id": current_user["id"],
                "widgets": ["calendar", "stats", "notifications"],
            }

        except Exception as e:
            log.error("Dashboard loading failed", extra={"error": str(e)})
            raise HTTPException(status_code=500, detail="Dashboard unavailable")

    @app.get("/content/mixed")
    async def mixed_content(
        current_user: Optional[Dict[str, Any]] = Depends(
            get_user_optional_with_context
        ),
    ):
        """
        Mixed endpoint that works with or without authentication.
        Logs will include user context if authenticated, null values if not.
        """
        if current_user:
            log.info("Authenticated user accessing mixed content")
            content_type = "premium"
        else:
            log.info("Anonymous user accessing mixed content")
            content_type = "basic"

        return {
            "message": f"Showing {content_type} content",
            "content": ["item1", "item2", "item3"] if current_user else ["item1"],
        }

    @app.post("/user/action")
    async def user_action(
        action_data: Dict[str, Any],
        current_user: Dict[str, Any] = Depends(get_user_with_context),
    ):
        """
        Action endpoint that demonstrates user context in error scenarios.
        """
        action_type = action_data.get("type")

        log.info("User action initiated", extra={"action_type": action_type})

        if action_type == "dangerous_action":
            if "admin" not in current_user.get("roles", []):
                log.warning(
                    "Unauthorized action attempted", extra={"action_type": action_type}
                )
                raise HTTPException(status_code=403, detail="Insufficient permissions")

        if action_type == "fail_action":
            log.error("Action failed intentionally", extra={"action_type": action_type})
            raise HTTPException(status_code=400, detail="Action failed")

        log.info(
            "User action completed successfully", extra={"action_type": action_type}
        )
        return {"message": f"Action '{action_type}' completed successfully"}

    @app.get("/manual-context")
    async def manual_context():
        """
        Endpoint demonstrating manual user context binding.
        Useful for background tasks or non-HTTP contexts.
        """
        # Manually bind user context (e.g., from background job, queue processor)
        bind_user_context(
            user_id="background_user",
            user_roles=["system", "processor"],
            auth_scheme="internal",
        )

        log.info("Background task processing")

        # Simulate background work
        await asyncio.sleep(0.1)

        log.info("Background task completed")

        return {"message": "Manual context demonstration complete"}

    return app


async def demonstrate_user_context():
    """
    Demonstration function showing different user context scenarios.
    """
    print("\n" + "=" * 60)
    print("FastAPI User Context Enrichment Example")
    print("=" * 60)

    # Setup logging
    logger = setup_logging()

    print("\n🔧 Configuration:")
    print("- User context enrichment: ENABLED")
    print("- JSON console output: ENABLED")
    print("- Log level: INFO")

    print("\n📋 Features demonstrated:")
    print("- Automatic user context in logs (user_id, user_roles, auth_scheme)")
    print("- Dict-based and class-based user objects")
    print("- Optional authentication endpoints")
    print("- Manual user context binding")
    print("- Error scenarios with user context")

    print("\n🚀 FastAPI application created with the following endpoints:")
    print("  GET  /                      - Public endpoint (no auth)")
    print("  POST /auth/login            - Login endpoint")
    print("  GET  /user/profile          - Protected (dict-based user)")
    print("  GET  /user/advanced-profile - Protected (class-based user)")
    print("  GET  /user/dashboard        - Protected (multiple log events)")
    print("  GET  /content/mixed         - Optional auth endpoint")
    print("  POST /user/action           - Protected action endpoint")
    print("  GET  /manual-context        - Manual context binding demo")

    print("\n🔑 Test credentials:")
    print("  Username: alice@example.com, Password: secret123 → Token: alice_token")
    print("  Username: bob@example.com,   Password: password456 → Token: bob_token")

    print("\n📄 Example requests:")
    print("  # Login")
    print('  curl -X POST "http://localhost:8000/auth/login" \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"username": "alice@example.com", "password": "secret123"}\'')
    print()
    print("  # Authenticated request")
    print('  curl -H "Authorization: Bearer alice_token" \\')
    print('    "http://localhost:8000/user/profile"')
    print()
    print("  # Mixed content (with auth)")
    print('  curl -H "Authorization: Bearer alice_token" \\')
    print('    "http://localhost:8000/content/mixed"')
    print()
    print("  # Mixed content (without auth)")
    print('  curl "http://localhost:8000/content/mixed"')

    print("\n📊 Expected log output includes:")
    print("  - user_id: User identifier from authentication")
    print("  - user_roles: Array of user roles/permissions")
    print("  - auth_scheme: Authentication method used")
    print("  - Standard request context (trace_id, method, path, etc.)")

    # Create the app
    app = await create_app()

    print(f"\n✅ Application setup complete!")
    print(
        "💡 Note: User context fields will appear in all log events during authenticated requests"
    )
    print("💡 For unauthenticated requests, user context fields will be null")

    return app


if __name__ == "__main__":
    import uvicorn

    # Run the demonstration
    app = asyncio.run(demonstrate_user_context())

    print(f"\n🌐 Starting server...")
    print("   User context enrichment will be visible in all log outputs")
    print("   Try the endpoints above to see user context in action!")

    # Start the server
    uvicorn.run(app, host="0.0.0.0", port=8000)
