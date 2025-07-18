#!/usr/bin/env python3
"""
Example 7: FastAPI Error Handling and Logging

This example demonstrates comprehensive error handling and logging in FastAPI
applications, including custom exceptions, validation errors, and proper
error correlation with trace IDs.
"""

import asyncio
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings


# Custom exception classes
class BusinessLogicError(Exception):
    """Custom exception for business logic errors."""

    def __init__(self, message: str, error_code: str, details: Optional[Dict] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


class DatabaseError(Exception):
    """Custom exception for database errors."""

    def __init__(self, message: str, operation: str, table: str):
        self.message = message
        self.operation = operation
        self.table = table
        super().__init__(message)


# Pydantic models for validation
class UserCreate(BaseModel):
    name: str
    email: str
    age: Optional[int] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    age: Optional[int] = None


def create_app() -> FastAPI:
    """Create a FastAPI application with comprehensive error handling."""

    # Configure logging
    settings = LoggingSettings(
        level="INFO",
        json_console="pretty",
        queue_enabled=False,
    )

    configure_logging(settings=settings)

    # Create FastAPI app
    app = FastAPI(
        title="fapilog Error Handling Example",
        description="Example showing comprehensive error handling and logging",
        version="1.0.0",
    )

    log.info(
        "FastAPI application with error handling starting",
        app_name="fapilog-error-handling-example",
        version="1.0.0",
    )

    return app


# Create the FastAPI application
app = create_app()


@app.get("/")
async def root():
    """Root endpoint."""
    log.info("Root endpoint accessed")
    return {"message": "Error handling example API"}


@app.post("/users")
async def create_user(user_data: UserCreate):
    """Create user with validation and error handling."""
    log.info(
        "User creation requested", user_name=user_data.name, user_email=user_data.email
    )

    try:
        # Simulate validation
        if user_data.age and user_data.age < 0:
            log.warning(
                "Invalid age provided", user_name=user_data.name, age=user_data.age
            )
            raise HTTPException(status_code=400, detail="Age must be positive")

        # Simulate database operation
        await asyncio.sleep(0.1)

        # Simulate duplicate email check
        if user_data.email == "existing@example.com":
            log.error(
                "Duplicate email attempted",
                email=user_data.email,
                error_code="DUPLICATE_EMAIL",
            )
            raise BusinessLogicError(
                message="Email already exists",
                error_code="DUPLICATE_EMAIL",
                details={"email": user_data.email},
            )

        # Simulate database error
        if user_data.name == "error":
            log.error(
                "Database error simulated", operation="create_user", table="users"
            )
            raise DatabaseError(
                message="Database connection failed",
                operation="create_user",
                table="users",
            )

        new_user = {
            "id": 1,
            "name": user_data.name,
            "email": user_data.email,
            "age": user_data.age,
        }

        log.info(
            "User created successfully",
            user_id=new_user["id"],
            user_name=new_user["name"],
        )

        return new_user

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except BusinessLogicError as e:
        log.error(
            "Business logic error",
            error_code=e.error_code,
            message=e.message,
            details=e.details,
        )
        raise HTTPException(
            status_code=400,
            detail={
                "error": e.message,
                "error_code": e.error_code,
                "details": e.details,
            },
        )
    except DatabaseError as e:
        log.error(
            "Database error", operation=e.operation, table=e.table, message=e.message
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Database operation failed",
                "operation": e.operation,
                "table": e.table,
            },
        )
    except Exception as e:
        log.error(
            "Unexpected error during user creation",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/users/{user_id}")
async def get_user(user_id: int):
    """Get user with error handling."""
    log.info("User retrieval requested", user_id=user_id)

    try:
        # Simulate database lookup
        await asyncio.sleep(0.05)

        if user_id == 1:
            user = {"id": 1, "name": "Alice", "email": "alice@example.com"}
            log.info("User found", user_id=user_id, user_name=user["name"])
            return user
        elif user_id == 999:
            # Simulate database error
            log.error(
                "Database error for user lookup",
                user_id=user_id,
                operation="get_user",
                table="users",
            )
            raise DatabaseError(
                message="Database connection timeout",
                operation="get_user",
                table="users",
            )
        else:
            log.warning("User not found", user_id=user_id)
            raise HTTPException(status_code=404, detail="User not found")

    except HTTPException:
        raise
    except DatabaseError as e:
        log.error(
            "Database error during user retrieval",
            user_id=user_id,
            operation=e.operation,
            table=e.table,
            message=e.message,
        )
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        log.error(
            "Unexpected error during user retrieval",
            user_id=user_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@app.put("/users/{user_id}")
async def update_user(user_id: int, user_data: UserUpdate):
    """Update user with validation and error handling."""
    log.info(
        "User update requested",
        user_id=user_id,
        update_fields=list(user_data.dict(exclude_unset=True).keys()),
    )

    try:
        # Simulate validation
        if user_data.age is not None and user_data.age < 0:
            log.warning("Invalid age in update", user_id=user_id, age=user_data.age)
            raise HTTPException(status_code=400, detail="Age must be positive")

        # Simulate database operation
        await asyncio.sleep(0.1)

        if user_id == 999:
            raise DatabaseError(
                message="Database connection failed",
                operation="update_user",
                table="users",
            )

        updated_user = {
            "id": user_id,
            "name": user_data.name or "Updated User",
            "email": user_data.email or "updated@example.com",
            "age": user_data.age,
        }

        log.info("User updated successfully", user_id=user_id)

        return updated_user

    except HTTPException:
        raise
    except DatabaseError as e:
        log.error(
            "Database error during user update",
            user_id=user_id,
            operation=e.operation,
            table=e.table,
            message=e.message,
        )
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        log.error(
            "Unexpected error during user update",
            user_id=user_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/users/{user_id}")
async def delete_user(user_id: int):
    """Delete user with error handling."""
    log.info("User deletion requested", user_id=user_id)

    try:
        # Simulate database operation
        await asyncio.sleep(0.1)

        if user_id == 1:
            log.info("User deleted successfully", user_id=user_id)
            return {"message": "User deleted successfully"}
        elif user_id == 999:
            raise DatabaseError(
                message="Database connection failed",
                operation="delete_user",
                table="users",
            )
        else:
            log.warning("User not found for deletion", user_id=user_id)
            raise HTTPException(status_code=404, detail="User not found")

    except HTTPException:
        raise
    except DatabaseError as e:
        log.error(
            "Database error during user deletion",
            user_id=user_id,
            operation=e.operation,
            table=e.table,
            message=e.message,
        )
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        log.error(
            "Unexpected error during user deletion",
            user_id=user_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/error-simulation")
async def error_simulation():
    """Endpoint to simulate different types of errors."""
    log.info("Error simulation endpoint accessed")

    # Simulate different error types
    error_type = "validation"  # Change this to test different errors

    if error_type == "validation":
        log.error("Validation error simulated")
        raise HTTPException(status_code=422, detail="Validation error")
    elif error_type == "business":
        log.error("Business logic error simulated")
        raise BusinessLogicError(
            message="Business rule violation",
            error_code="BUSINESS_RULE_VIOLATION",
            details={"rule": "example_rule"},
        )
    elif error_type == "database":
        log.error("Database error simulated")
        raise DatabaseError(
            message="Database connection failed",
            operation="simulate_error",
            table="test",
        )
    else:
        log.error("Generic error simulated")
        raise Exception("Generic error for testing")


# Custom exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    log.error(
        "Request validation error",
        endpoint=str(request.url.path),
        method=request.method,
        errors=exc.errors(),
    )

    return JSONResponse(
        status_code=422, content={"detail": "Validation error", "errors": exc.errors()}
    )


@app.exception_handler(BusinessLogicError)
async def business_logic_exception_handler(request: Request, exc: BusinessLogicError):
    """Handle business logic errors."""
    log.error(
        "Business logic error",
        endpoint=str(request.url.path),
        method=request.method,
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
    )

    return JSONResponse(
        status_code=400,
        content={
            "detail": exc.message,
            "error_code": exc.error_code,
            "details": exc.details,
        },
    )


@app.exception_handler(DatabaseError)
async def database_exception_handler(request: Request, exc: DatabaseError):
    """Handle database errors."""
    log.error(
        "Database error",
        endpoint=str(request.url.path),
        method=request.method,
        operation=exc.operation,
        table=exc.table,
        message=exc.message,
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Database operation failed",
            "operation": exc.operation,
            "table": exc.table,
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions."""
    log.error(
        "Unhandled exception",
        endpoint=str(request.url.path),
        method=request.method,
        error=str(exc),
        error_type=type(exc).__name__,
    )

    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


def main():
    """Run the FastAPI application."""

    print("=== FastAPI Error Handling Example ===")
    print("This example demonstrates:")
    print("✅ Custom exception classes")
    print("✅ Comprehensive error handling")
    print("✅ Error logging with context")
    print("✅ Validation error handling")
    print("✅ Business logic error handling")
    print("✅ Database error handling")
    print("✅ Trace ID correlation in errors")
    print()
    print("Available endpoints:")
    print("  POST /users              - Create user (with validation)")
    print("  GET  /users/{id}         - Get user (with error handling)")
    print("  PUT  /users/{id}         - Update user (with validation)")
    print("  DELETE /users/{id}       - Delete user (with error handling)")
    print("  GET  /error-simulation   - Simulate different errors")
    print()
    print("Test scenarios:")
    print("✅ Valid user creation: POST /users with valid data")
    print("✅ Invalid age: POST /users with age < 0")
    print("✅ Duplicate email: POST /users with email 'existing@example.com'")
    print("✅ Database error: POST /users with name 'error'")
    print("✅ User not found: GET /users/999")
    print("✅ Database error: GET /users/999")
    print()
    print(
        "Start the server with: uvicorn examples.07_fastapi_error_handling:app --reload"
    )
    print("Then visit: http://localhost:8000/docs")


if __name__ == "__main__":
    main()
