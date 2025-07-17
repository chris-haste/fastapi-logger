"""FastAPI middleware for request correlation and timing."""

import time
import uuid
from typing import Any

try:
    from fastapi import Request, Response, status
    from fastapi.requests import Request as FastAPIRequest
    from fastapi.responses import JSONResponse

    FASTAPI_AVAILABLE = True
except ImportError:  # pragma: no cover
    FASTAPI_AVAILABLE = False
    # Type stubs for when FastAPI is not available
    Request = Any
    Response = Any
    FastAPIRequest = Any
    status = type("status", (), {"HTTP_500_INTERNAL_SERVER_ERROR": 500})()

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ._internal.context import (
    bind_context,
    clear_context,
)


def add_trace_exception_handler(app, trace_id_header: str = "X-Request-ID"):
    """
    Register a custom exception handler that adds trace/span/latency
    headers to 500 responses.

    Args:
        app: FastAPI application instance
        trace_id_header: Header name for trace ID (default: X-Request-ID)
    """

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
            response.headers[trace_id_header] = trace_id
        if span_id:
            response.headers["X-Span-Id"] = span_id
        response.headers["X-Response-Time-ms"] = str(latency)
        return response


class TraceIDMiddleware(BaseHTTPMiddleware):
    """Middleware that injects trace_id and span_id into request context.

    This middleware:
    - Generates or forwards trace_id from configurable header
      (default: X-Request-ID)
    - Generates a fresh span_id for each request
    - Measures request latency and adds X-Response-Time-ms header
    - Captures request/response metadata (body sizes, status code, user-agent)
    - Captures request details (method, path, client_ip) for context
      enrichment
    - Echoes trace_id in X-Trace-Id response header
    - Cleans up context variables after request completion
    """

    def __init__(self, app: ASGIApp, trace_id_header: str = "X-Request-ID") -> None:
        """Initialize the middleware.

        Args:
            app: The ASGI application to wrap
            trace_id_header: The HTTP header name for trace ID
                           (default: X-Request-ID)
        """
        super().__init__(app)
        self.trace_id_header = trace_id_header

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

        # Generate or forward trace_id using configurable header
        trace_id = request.headers.get(self.trace_id_header)
        if not trace_id:
            trace_id = uuid.uuid4().hex

        # Generate fresh span_id
        span_id = uuid.uuid4().hex

        # Extract request details for context enrichment (Story 6.1)
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path

        # Capture request metadata
        req_size = 0
        try:
            req_size = int(request.headers.get("content-length", 0) or 0)
        except (ValueError, TypeError):
            # Handle invalid content-length header gracefully
            req_size = 0
        user_agent = request.headers.get("user-agent", "-")

        # Set context variables with all request metadata
        bind_context(
            trace_id=trace_id,
            span_id=span_id,
            req_bytes=req_size,
            user_agent=user_agent,
            client_ip=client_ip,
            method=method,
            path=path,
        )

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

            # Calculate response body size
            res_size = 0
            if hasattr(response, "body"):
                if response.body:
                    res_size = len(response.body)
                elif (
                    hasattr(response, "media_type")
                    and response.media_type == "application/json"
                ):
                    # For JSONResponse, try to get body size
                    try:
                        import json

                        body_str = json.dumps(response.body) if response.body else ""
                        res_size = len(body_str.encode("utf-8"))
                    except (TypeError, ValueError):  # pragma: no cover
                        # This branch is not testable via FastAPI/Starlette's
                        # public API because setting response.body to
                        # non-serializable types causes framework-level errors
                        # before reaching this middleware logic
                        res_size = 0

            # Set response metadata context variables
            bind_context(
                res_bytes=res_size,
                status_code=response.status_code,
                latency_ms=duration,
            )

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
            response.headers[self.trace_id_header] = trace_id
            response.headers["X-Span-Id"] = span_id
            response.headers["X-Response-Time-ms"] = str(duration)

            return response

        except Exception as e:
            # Calculate latency even on error
            duration = round((time.perf_counter() - start_time) * 1000, 2)

            # Set response metadata for error case (status 500, no body)
            bind_context(res_bytes=0, status_code=500, latency_ms=duration)

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

            # Re-raise the exception so FastAPI can handle it
            # (our handler will add headers)
            raise

        finally:
            # Always clean up context variables
            clear_context()
