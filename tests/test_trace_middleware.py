import re
import uuid
from fastapi import FastAPI
from starlette.testclient import TestClient

from fapilog.bootstrap import configure_logging
from fapilog.middleware import add_trace_exception_handler


def make_app():
    app = FastAPI()

    @app.get("/ping")
    async def ping():
        return {"status": "ok"}

    @app.get("/error")
    async def error_endpoint():
        raise ValueError("Test error")

    configure_logging(app=app)
    add_trace_exception_handler(app)
    return app


def test_forward_trace_header():
    app = make_app()
    client = TestClient(app)
    custom_trace_id = uuid.uuid4().hex
    response = client.get("/ping", headers={"X-Trace-Id": custom_trace_id})
    assert response.status_code == 200
    # Should forward the provided trace ID
    assert response.headers["x-trace-id"] == custom_trace_id
    # Span ID should be a valid UUID hex
    span_id = response.headers["x-span-id"]
    assert re.fullmatch(r"[0-9a-f]{32}", span_id)
    # X-Response-Time-ms should be present and numeric
    assert "x-response-time-ms" in response.headers
    assert float(response.headers["x-response-time-ms"]) >= 0


def test_generate_trace_header():
    app = make_app()
    client = TestClient(app)
    response = client.get("/ping")
    assert response.status_code == 200
    # Should generate a new trace ID
    trace_id = response.headers["x-trace-id"]
    assert re.fullmatch(r"[0-9a-f]{32}", trace_id)
    # Span ID should be a valid UUID hex
    span_id = response.headers["x-span-id"]
    assert re.fullmatch(r"[0-9a-f]{32}", span_id)
    # X-Response-Time-ms should be present and numeric
    assert "x-response-time-ms" in response.headers
    assert float(response.headers["x-response-time-ms"]) >= 0


def test_latency_header_present():
    app = make_app()
    client = TestClient(app)
    response = client.get("/ping")
    assert response.status_code == 200
    # X-Response-Time-ms should be present and numeric
    assert "x-response-time-ms" in response.headers
    latency = response.headers["x-response-time-ms"]
    assert re.fullmatch(r"\d+(\.\d+)?", latency)
    assert float(latency) >= 0


def test_context_cleanup():
    app = make_app()
    client = TestClient(app)
    # Call endpoint to set context
    response = client.get("/ping")
    assert response.status_code == 200
    # After request, contextvars should be None (no leakage)
    from fapilog._internal.context import get_trace_id, get_span_id

    assert get_trace_id() is None
    assert get_span_id() is None


def test_exception_handling():
    """Test that middleware handles exceptions properly and still logs."""
    app = make_app()
    client = TestClient(app, raise_server_exceptions=False)

    # This should return a 500 response due to the exception
    response = client.get("/error")
    assert response.status_code == 500

    # Should still have correlation headers
    assert "x-trace-id" in response.headers
    assert "x-span-id" in response.headers
    assert "x-response-time-ms" in response.headers

    # Verify trace and span IDs are valid UUIDs
    trace_id = response.headers["x-trace-id"]
    span_id = response.headers["x-span-id"]
    assert re.fullmatch(r"[0-9a-f]{32}", trace_id)
    assert re.fullmatch(r"[0-9a-f]{32}", span_id)

    # Verify latency is numeric and positive
    latency = response.headers["x-response-time-ms"]
    assert re.fullmatch(r"\d+(\.\d+)?", latency)
    assert float(latency) >= 0


def test_context_cleanup_after_exception():
    """Test that context is cleaned up even after exceptions."""
    app = make_app()
    client = TestClient(app, raise_server_exceptions=False)

    # This should return a 500 response due to the exception
    response = client.get("/error")
    assert response.status_code == 500

    # After request, contextvars should be None (no leakage)
    from fapilog._internal.context import get_trace_id, get_span_id

    assert get_trace_id() is None
    assert get_span_id() is None


def test_middleware_idempotent_registration():
    """Test that middleware is only registered once."""
    app = FastAPI()

    @app.get("/ping")
    async def ping():
        return {"status": "ok"}

    # First call should register middleware
    configure_logging(app=app)

    # Second call should not duplicate middleware
    configure_logging(app=app)

    client = TestClient(app)
    response = client.get("/ping")
    assert response.status_code == 200
    assert "x-trace-id" in response.headers
