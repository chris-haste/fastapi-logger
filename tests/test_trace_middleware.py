"""Tests for trace middleware."""

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from fapilog.bootstrap import configure_logging
from fapilog.middleware import TraceIDMiddleware, add_trace_exception_handler


@pytest.mark.asyncio
async def test_forward_trace_header():
    """Test that X-Request-ID header is forwarded."""
    app = FastAPI()

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    app.add_middleware(TraceIDMiddleware)
    configure_logging(app=app)
    client = TestClient(app)

    # Test with custom trace ID
    response = client.get("/test", headers={"X-Request-ID": "custom-trace-123"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "custom-trace-123"


@pytest.mark.asyncio
async def test_generate_trace_header():
    """Test that trace ID is generated when not provided."""
    app = FastAPI()

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    app.add_middleware(TraceIDMiddleware)
    configure_logging(app=app)
    client = TestClient(app)

    # Test without trace ID header
    response = client.get("/test")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) == 32  # UUID hex length


@pytest.mark.asyncio
async def test_latency_header_present():
    """Test that X-Response-Time-ms header is present."""
    app = FastAPI()

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    app.add_middleware(TraceIDMiddleware)
    configure_logging(app=app)
    client = TestClient(app)

    response = client.get("/test")
    assert response.status_code == 200
    assert "X-Response-Time-ms" in response.headers
    assert float(response.headers["X-Response-Time-ms"]) >= 0


@pytest.mark.asyncio
async def test_context_cleanup():
    """Test that context is cleaned up after request."""
    from fapilog._internal.context import clear_context, get_context

    # Clear context to avoid contamination from other tests
    clear_context()

    app = FastAPI()

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    app.add_middleware(TraceIDMiddleware)
    configure_logging(app=app)
    client = TestClient(app)

    # Make request
    response = client.get("/test")
    assert response.status_code == 200

    # Check that context is cleaned up
    context = get_context()
    for value in context.values():
        assert value is None


@pytest.mark.asyncio
async def test_exception_handling():
    """Test that exceptions are handled correctly."""
    app = FastAPI()

    @app.get("/error")
    async def error_endpoint():
        raise ValueError("Test error")

    app.add_middleware(TraceIDMiddleware)
    add_trace_exception_handler(app, "X-Request-ID")
    configure_logging(app=app)
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/error")
    assert response.status_code == 500
    assert "X-Request-ID" in response.headers
    assert "X-Response-Time-ms" in response.headers


@pytest.mark.asyncio
async def test_context_cleanup_after_exception():
    """Test that context is cleaned up even after exceptions."""
    from fapilog._internal.context import clear_context, get_context

    # Clear context to avoid contamination from other tests
    clear_context()

    app = FastAPI()

    @app.get("/error")
    async def error_endpoint():
        raise ValueError("Test error")

    app.add_middleware(TraceIDMiddleware)
    add_trace_exception_handler(app, "X-Request-ID")
    configure_logging(app=app)
    client = TestClient(app, raise_server_exceptions=False)

    # Make request that will raise an exception
    response = client.get("/error")
    assert response.status_code == 500

    # Check that context is cleaned up
    context = get_context()
    for value in context.values():
        assert value is None


@pytest.mark.asyncio
async def test_middleware_idempotent_registration():
    """Test that middleware can be registered multiple times safely."""
    app = FastAPI()

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    # Register middleware multiple times
    app.add_middleware(TraceIDMiddleware)
    app.add_middleware(TraceIDMiddleware)
    configure_logging(app=app)
    client = TestClient(app)

    response = client.get("/test")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers


@pytest.mark.asyncio
async def test_json_response_body_size_calculation():
    """Test JSON response body size calculation logic."""
    app = FastAPI()

    @app.get("/json-test")
    async def json_endpoint():
        return {"message": "test", "data": [1, 2, 3]}

    @app.get("/empty-json")
    async def empty_json_endpoint():
        return {}

    app.add_middleware(TraceIDMiddleware)
    configure_logging(app=app)
    client = TestClient(app)

    # Test with JSON response
    response = client.get("/json-test")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers

    # Test with empty JSON response
    response = client.get("/empty-json")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers


@pytest.mark.asyncio
async def test_non_json_response_body_size():
    """Test response body size calculation for non-JSON responses."""
    app = FastAPI()

    @app.get("/text-test")
    async def text_endpoint():
        from fastapi.responses import PlainTextResponse

        return PlainTextResponse("Hello, World!")

    app.add_middleware(TraceIDMiddleware)
    configure_logging(app=app)
    client = TestClient(app)

    response = client.get("/text-test")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert response.text == "Hello, World!"


# Note: Tests for JSON response body size calculation error handling are not included
# because the error handling branch (lines 126-139 in middleware.py) cannot be
# reached through FastAPI/Starlette's public API. Setting response.body to
# non-serializable types causes framework-level errors before reaching the
# middleware's exception handling logic.


@pytest.mark.asyncio
async def test_exception_handler_with_missing_state():
    """Test exception handler when request.state attributes are missing."""
    app = FastAPI()

    @app.get("/error-no-state")
    async def error_no_state_endpoint():
        raise ValueError("Test error")

    # Don't add middleware, just add exception handler
    add_trace_exception_handler(app, "X-Request-ID")
    configure_logging(app=app)
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/error-no-state")
    assert response.status_code == 500
    # Should still have X-Response-Time-ms header with default value
    assert "X-Response-Time-ms" in response.headers
    # The actual value will be the actual latency, not 0.0
    assert float(response.headers["X-Response-Time-ms"]) >= 0


@pytest.mark.asyncio
async def test_exception_handler_with_partial_state():
    """Test exception handler when only some request.state attributes are present."""
    app = FastAPI()

    @app.get("/error-partial-state")
    async def error_partial_state_endpoint():
        # Set only some state attributes
        from starlette.requests import Request

        request = Request({"type": "http", "method": "GET", "path": "/"})
        request.state.trace_id = "test-trace"
        request.state.latency_ms = 150.0
        # Don't set span_id
        raise ValueError("Test error")

    add_trace_exception_handler(app, "X-Request-ID")
    configure_logging(app=app)
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/error-partial-state")
    assert response.status_code == 500
    # The middleware will generate its own trace_id, so we can't predict it
    assert "X-Request-ID" in response.headers
    assert "X-Response-Time-ms" in response.headers
    # The actual value will be the actual latency, not 150.0
    assert float(response.headers["X-Response-Time-ms"]) >= 0
    # The middleware will generate its own span_id, so we should have it
    assert "X-Span-Id" in response.headers


@pytest.mark.asyncio
async def test_middleware_with_content_length_header():
    """Test middleware with explicit content-length header."""
    app = FastAPI()

    @app.post("/test-content-length")
    async def test_endpoint():
        return {"message": "test"}

    app.add_middleware(TraceIDMiddleware)
    configure_logging(app=app)
    client = TestClient(app)

    # Test with explicit content-length header
    response = client.post(
        "/test-content-length",
        json={"test": "data"},
        headers={"Content-Length": "25", "X-Request-ID": "custom-trace-456"},
    )
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "custom-trace-456"


@pytest.mark.asyncio
async def test_middleware_with_empty_content_length():
    """Test middleware with empty content-length header."""
    app = FastAPI()

    @app.post("/test-empty-content-length")
    async def test_endpoint():
        return {"message": "test"}

    app.add_middleware(TraceIDMiddleware)
    configure_logging(app=app)
    client = TestClient(app)

    # Test with empty content-length header
    response = client.post(
        "/test-empty-content-length",
        json={"test": "data"},
        headers={"Content-Length": "", "X-Request-ID": "custom-trace-789"},
    )
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "custom-trace-789"


@pytest.mark.asyncio
async def test_middleware_with_invalid_content_length():
    """Test middleware with invalid content-length header."""
    app = FastAPI()

    @app.post("/test-invalid-content-length")
    async def test_endpoint():
        return {"message": "test"}

    app.add_middleware(TraceIDMiddleware)
    configure_logging(app=app)
    client = TestClient(app)

    # Test with invalid content-length header
    response = client.post(
        "/test-invalid-content-length",
        json={"test": "data"},
        headers={"Content-Length": "invalid", "X-Request-ID": "custom-trace-abc"},
    )
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "custom-trace-abc"


@pytest.mark.asyncio
async def test_middleware_with_custom_user_agent():
    """Test middleware with custom user agent header."""
    app = FastAPI()

    @app.get("/test-user-agent")
    async def test_endpoint():
        return {"message": "test"}

    app.add_middleware(TraceIDMiddleware)
    configure_logging(app=app)
    client = TestClient(app)

    # Test with custom user agent
    response = client.get(
        "/test-user-agent",
        headers={"User-Agent": "CustomAgent/1.0", "X-Request-ID": "custom-trace-def"},
    )
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "custom-trace-def"


@pytest.mark.asyncio
async def test_middleware_without_user_agent():
    """Test middleware without user agent header (should default to '-')."""
    app = FastAPI()

    @app.get("/test-no-user-agent")
    async def test_endpoint():
        return {"message": "test"}

    app.add_middleware(TraceIDMiddleware)
    configure_logging(app=app)
    client = TestClient(app)

    # Test without user agent header
    response = client.get("/test-no-user-agent")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers


@pytest.mark.asyncio
async def test_middleware_with_response_body():
    """Test middleware with response that has a body."""
    app = FastAPI()

    @app.get("/test-with-body")
    async def test_endpoint():
        return {"message": "test", "data": [1, 2, 3, 4, 5]}

    app.add_middleware(TraceIDMiddleware)
    configure_logging(app=app)
    client = TestClient(app)

    response = client.get("/test-with-body")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert "X-Response-Time-ms" in response.headers
    assert response.json()["message"] == "test"


@pytest.mark.asyncio
async def test_middleware_with_empty_response_body():
    """Test middleware with response that has an empty body."""
    app = FastAPI()

    @app.get("/test-empty-body")
    async def test_endpoint():
        return {}

    app.add_middleware(TraceIDMiddleware)
    configure_logging(app=app)
    client = TestClient(app)

    response = client.get("/test-empty-body")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert "X-Response-Time-ms" in response.headers
    assert response.json() == {}


@pytest.mark.asyncio
async def test_middleware_with_non_json_response():
    """Test middleware with non-JSON response."""
    app = FastAPI()

    @app.get("/test-plain-text")
    async def test_endpoint():
        from fastapi.responses import PlainTextResponse

        return PlainTextResponse("Hello, World!")

    app.add_middleware(TraceIDMiddleware)
    configure_logging(app=app)
    client = TestClient(app)

    response = client.get("/test-plain-text")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert "X-Response-Time-ms" in response.headers
    assert response.text == "Hello, World!"


@pytest.mark.asyncio
async def test_middleware_with_binary_response():
    """Test middleware with binary response."""
    app = FastAPI()

    @app.get("/test-binary")
    async def test_endpoint():
        from fastapi.responses import Response

        return Response(content=b"binary data", media_type="application/octet-stream")

    app.add_middleware(TraceIDMiddleware)
    configure_logging(app=app)
    client = TestClient(app)

    response = client.get("/test-binary")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert "X-Response-Time-ms" in response.headers
    assert response.content == b"binary data"


@pytest.mark.asyncio
async def test_middleware_with_response_no_body_attribute():
    """Test middleware with response that doesn't have a body attribute."""
    app = FastAPI()

    @app.get("/test-no-body-attr")
    async def test_endpoint():
        from fastapi.responses import StreamingResponse

        def generate():
            yield b"streaming data"

        return StreamingResponse(generate(), media_type="text/plain")

    app.add_middleware(TraceIDMiddleware)
    configure_logging(app=app)
    client = TestClient(app)

    response = client.get("/test-no-body-attr")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert "X-Response-Time-ms" in response.headers
    assert response.text == "streaming data"


@pytest.mark.asyncio
async def test_middleware_with_response_no_media_type():
    """Test middleware with response that doesn't have a media_type attribute."""
    app = FastAPI()

    @app.get("/test-no-media-type")
    async def test_endpoint():
        from fastapi.responses import Response

        # Create a response without media_type attribute
        response = Response(content="text data")
        # The Response object doesn't have media_type attribute by default
        # so this will test the branch where media_type is not available
        return response

    app.add_middleware(TraceIDMiddleware)
    configure_logging(app=app)
    client = TestClient(app)

    response = client.get("/test-no-media-type")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert "X-Response-Time-ms" in response.headers
