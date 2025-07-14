"""FastAPI middleware for request correlation and timing."""

import time
import uuid
from typing import Any

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.requests import Request as FastAPIRequest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ._internal.context import (
    reset_trace_context,
    set_trace_context,
)


def add_trace_exception_handler(app):
    """Register a custom exception handler that adds trace/span/latency headers to 500 responses."""

    @app.exception_handler(Exception)
    async def trace_exception_handler(request: FastAPIRequest, exc: Exception):
        # Get trace/span from request.state (set by middleware)
        trace_id = getattr(request.state, "trace_id", "")
        span_id = getattr(request.state, "span_id", "")
        latency = getattr(request.state, "latency_ms", 0.0)
        # Compose error response
        content = {"detail": "Internal Server Error"}
        response = JSONResponse(
            content=content,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
        if trace_id:
            response.headers["X-Trace-Id"] = trace_id
        if span_id:
            response.headers["X-Span-Id"] = span_id
        response.headers["X-Response-Time-ms"] = str(latency)
        return response


class TraceIDMiddleware(BaseHTTPMiddleware):
    """Middleware that injects trace_id and span_id into request context.

    This middleware:
    - Generates or forwards trace_id from X-Trace-Id header
    - Generates a fresh span_id for each request
    - Measures request latency and adds X-Response-Time-ms header
    - Echoes trace_id in X-Trace-Id response header
    - Cleans up context variables after request completion
    """

    def __init__(self, app: ASGIApp) -> None:
        """Initialize the middleware.

        Args:
            app: The ASGI application to wrap
        """
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """Process the request and add correlation IDs and timing.

        Args:
            request: The incoming request
            call_next: The next middleware or application in the chain

        Returns:
            The response with correlation headers added
        """
        # Import log here to avoid circular import
        from . import log

        # Generate or forward trace_id
        trace_id = request.headers.get("X-Trace-Id")
        if not trace_id:
            trace_id = uuid.uuid4().hex

        # Generate fresh span_id
        span_id = uuid.uuid4().hex

        # Set context variables
        token_tid, token_sid = set_trace_context(trace_id, span_id)
        # Also store on request.state for exception handler
        request.state.trace_id = trace_id
        request.state.span_id = span_id

        # Record start time
        start_time = time.perf_counter()

        try:
            # Process the request
            response = await call_next(request)

            # Calculate latency
            duration = round((time.perf_counter() - start_time) * 1000, 2)

            # Store latency in request.state for exception handler
            request.state.latency_ms = duration

            # Log request details with correlation IDs
            log.info(
                "Request processed",
                trace_id=trace_id,
                span_id=span_id,
                path=request.url.path,
                method=request.method,
                status_code=response.status_code,
                latency_ms=duration,
            )

            # Add correlation headers to response
            response.headers["X-Trace-Id"] = trace_id
            response.headers["X-Span-Id"] = span_id
            response.headers["X-Response-Time-ms"] = str(duration)

            return response

        except Exception as e:
            # Calculate latency even on error
            duration = round((time.perf_counter() - start_time) * 1000, 2)

            # Store latency in request.state for exception handler
            request.state.latency_ms = duration

            # Log error with correlation IDs
            log.error(
                "Request failed",
                trace_id=trace_id,
                span_id=span_id,
                path=request.url.path,
                method=request.method,
                latency_ms=duration,
                error=str(e),
                exc_info=True,
            )

            # Re-raise the exception so FastAPI can handle it (our handler will add headers)
            raise

        finally:
            # Always clean up context variables
            reset_trace_context(token_tid, token_sid)
