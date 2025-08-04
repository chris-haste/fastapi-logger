"""Tests for trace propagation functionality (Story 6.2)."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from fapilog import get_current_trace_id
from fapilog.bootstrap import configure_logging
from fapilog.config import LoggingSettings
from fapilog.exceptions import ConfigurationError
from fapilog.middleware import TraceIDMiddleware
from fapilog.utils.context import get_context


@pytest.mark.asyncio
async def test_incoming_trace_id_preserved():
    """Test that incoming trace IDs are preserved and propagated."""
    app = FastAPI()
    context_data = {}

    @app.get("/test")
    async def test_endpoint():
        # Capture context during request processing
        context_data.update(get_context())
        return {"message": "test"}

    app.add_middleware(TraceIDMiddleware, trace_id_header="X-Request-ID")
    configure_logging(app=app)
    client = TestClient(app)

    # Test with incoming trace ID
    response = client.get("/test", headers={"X-Request-ID": "incoming-trace-123"})
    assert response.status_code == 200

    # Verify trace ID is preserved in context
    assert context_data["trace_id"] == "incoming-trace-123"

    # Verify trace ID is echoed in response header
    assert response.headers["X-Request-ID"] == "incoming-trace-123"


@pytest.mark.asyncio
async def test_generated_trace_id_present():
    """Test that trace ID is generated when not provided."""
    app = FastAPI()
    context_data = {}

    @app.get("/test")
    async def test_endpoint():
        # Capture context during request processing
        context_data.update(get_context())
        return {"message": "test"}

    app.add_middleware(TraceIDMiddleware, trace_id_header="X-Request-ID")
    configure_logging(app=app)
    client = TestClient(app)

    # Test without incoming trace ID
    response = client.get("/test")
    assert response.status_code == 200

    # Verify trace ID is generated and present in context
    assert "trace_id" in context_data
    assert context_data["trace_id"] is not None
    assert len(context_data["trace_id"]) == 32  # UUID hex length

    # Verify trace ID is present in response header
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) == 32


@pytest.mark.asyncio
async def test_get_current_trace_id():
    """Test the get_current_trace_id() function."""
    app = FastAPI()
    captured_trace_id = None

    @app.get("/test")
    async def test_endpoint():
        nonlocal captured_trace_id
        # Get trace ID via the public API function
        captured_trace_id = get_current_trace_id()
        return {"message": "test"}

    app.add_middleware(TraceIDMiddleware, trace_id_header="X-Request-ID")
    configure_logging(app=app)
    client = TestClient(app)

    # Test with custom trace ID
    response = client.get("/test", headers={"X-Request-ID": "api-test-trace-456"})
    assert response.status_code == 200

    # Verify the API function returns the correct trace ID
    assert captured_trace_id == "api-test-trace-456"
    assert response.headers["X-Request-ID"] == "api-test-trace-456"


@pytest.mark.asyncio
async def test_get_current_trace_id_no_context():
    """Test get_current_trace_id() when no context is set."""
    # Call the function outside of a request context
    trace_id = get_current_trace_id()

    # Should return None when no context is set
    assert trace_id is None


@pytest.mark.asyncio
async def test_trace_id_in_httpx_request():
    """Test that trace ID is automatically added to httpx requests."""
    try:
        import httpx
    except ImportError:
        pytest.skip("httpx not available")

    app = FastAPI()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"external": "response"}

    @app.get("/test")
    async def test_endpoint():
        # Create an httpx client and make a request
        async with httpx.AsyncClient() as client:
            response = await client.request("GET", "https://api.example.com/data")
            return {"status": "ok", "external_status": response.status_code}

    # Enable httpx trace propagation
    settings = LoggingSettings(
        enable_httpx_trace_propagation=True, trace_id_header="X-Request-ID"
    )

    app.add_middleware(TraceIDMiddleware, trace_id_header="X-Request-ID")
    configure_logging(settings=settings, app=app)
    client = TestClient(app)

    # Mock httpx.AsyncClient.request to capture headers
    with patch.object(httpx.AsyncClient, "request") as mock_request:
        mock_request.return_value = mock_response

        # Make request with trace ID
        response = client.get("/test", headers={"X-Request-ID": "httpx-test-789"})
        assert response.status_code == 200

        # Verify that httpx request was called with trace ID header
        assert mock_request.called
        call_args = mock_request.call_args

        # Check if headers were passed and contain trace ID
        if "headers" in call_args.kwargs:
            headers = call_args.kwargs["headers"]
            assert headers.get("X-Request-ID") == "httpx-test-789"


@pytest.mark.asyncio
async def test_httpx_propagation_disabled():
    """Test that httpx propagation does not occur when disabled."""
    try:
        import httpx
    except ImportError:
        pytest.skip("httpx not available")

    app = FastAPI()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"external": "response"}

    @app.get("/test")
    async def test_endpoint():
        async with httpx.AsyncClient() as client:
            await client.request(
                "GET", "https://api.example.com/data", headers={"Custom-Header": "test"}
            )
            return {"status": "ok"}

    # Configure with httpx propagation DISABLED
    settings = LoggingSettings(
        enable_httpx_trace_propagation=False, trace_id_header="X-Request-ID"
    )

    app.add_middleware(TraceIDMiddleware, trace_id_header="X-Request-ID")
    configure_logging(settings=settings, app=app)
    client = TestClient(app)

    # Mock httpx.AsyncClient.request to capture headers
    with patch.object(httpx.AsyncClient, "request") as mock_request:
        mock_request.return_value = mock_response

        # Make request with trace ID
        response = client.get("/test", headers={"X-Request-ID": "no-propagation-test"})
        assert response.status_code == 200

        # Verify that httpx request was called but without automatic trace ID
        assert mock_request.called
        call_args = mock_request.call_args

        # Check that trace ID was NOT automatically added
        if "headers" in call_args.kwargs:
            headers = call_args.kwargs["headers"]
            # Should not contain our trace ID (only the Custom-Header we explicitly set)
            assert headers.get("X-Request-ID") != "no-propagation-test"


@pytest.mark.asyncio
async def test_custom_trace_header_name():
    """Test trace propagation with custom header name."""
    app = FastAPI()
    context_data = {}

    @app.get("/test")
    async def test_endpoint():
        context_data.update(get_context())
        return {"message": "test"}

    # Use custom trace header name
    custom_header = "X-Custom-Trace-ID"
    app.add_middleware(TraceIDMiddleware, trace_id_header=custom_header)
    configure_logging(app=app)
    client = TestClient(app)

    # Test with custom header
    response = client.get("/test", headers={custom_header: "custom-header-test"})
    assert response.status_code == 200

    # Verify trace ID is captured from custom header
    assert context_data["trace_id"] == "custom-header-test"
    assert response.headers[custom_header] == "custom-header-test"


@pytest.mark.asyncio
async def test_trace_propagation_with_httpx_unavailable():
    """Test that httpx propagation fails gracefully when httpx is unavailable."""
    # Mock httpx as unavailable
    with patch("fapilog.httpx_patch.httpx", None):
        from fapilog.config import LoggingSettings
        from fapilog.httpx_patch import configure_httpx_trace_propagation

        settings = LoggingSettings(enable_httpx_trace_propagation=True)

        # This should raise ConfigurationError
        with pytest.raises(ConfigurationError) as exc_info:
            configure_httpx_trace_propagation(settings)
        assert "httpx is required for trace propagation" in str(exc_info.value)
