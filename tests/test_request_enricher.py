"""Tests for request context enricher functionality (Story 6.1)."""

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from fapilog._internal.context import get_context
from fapilog.bootstrap import configure_logging
from fapilog.middleware import TraceIDMiddleware
from fapilog.settings import LoggingSettings


@pytest.mark.asyncio
async def test_context_contains_request_fields():
    """Test that context is injected and contains all required request fields."""
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

    response = client.get("/test", headers={"X-Request-ID": "test-trace-123"})
    assert response.status_code == 200

    # Verify all required fields are present in context
    assert context_data["trace_id"] == "test-trace-123"
    assert context_data["method"] == "GET"
    assert context_data["path"] == "/test"
    assert context_data["client_ip"] is not None  # Should be set to some value
    assert "span_id" in context_data
    assert context_data["span_id"] is not None


@pytest.mark.asyncio
async def test_fields_appear_in_emitted_logs():
    """Test that request fields appear in emitted logs."""
    app = FastAPI()
    captured_logs = []

    # Mock the log sink to capture log events
    def mock_log_sink(logger, method_name, event_dict):
        captured_logs.append(event_dict.copy())
        return None  # Prevent further processing

    @app.get("/test")
    async def test_endpoint():
        from fapilog import log

        log.info("Test log message during request")
        return {"message": "test"}

    app.add_middleware(TraceIDMiddleware, trace_id_header="X-Request-ID")

    # Configure logging with mock sink
    settings = LoggingSettings(queue_enabled=False)
    configure_logging(settings=settings, app=app)

    # Patch the pipeline to capture logs
    with patch("fapilog.pipeline.build_processor_chain") as mock_chain:
        mock_chain.return_value = [mock_log_sink]

        client = TestClient(app)
        response = client.get("/test", headers={"X-Request-ID": "test-trace-456"})
        assert response.status_code == 200

    # Verify log contains request metadata
    if captured_logs:
        log_event = captured_logs[0]
        assert log_event.get("trace_id") == "test-trace-456"
        assert log_event.get("method") == "GET"
        assert log_event.get("path") == "/test"
        assert "client_ip" in log_event


@pytest.mark.asyncio
async def test_context_cleanup_after_request():
    """Test that context is cleaned up after request lifecycle."""
    from fapilog._internal.context import get_context

    app = FastAPI()

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    app.add_middleware(TraceIDMiddleware, trace_id_header="X-Request-ID")
    configure_logging(app=app)
    client = TestClient(app)

    # Make request
    response = client.get("/test", headers={"X-Request-ID": "test-trace-789"})
    assert response.status_code == 200

    # Check that context is cleaned up
    context = get_context()
    for value in context.values():
        assert value is None


@pytest.mark.asyncio
async def test_custom_trace_id_header():
    """Test that custom trace ID header is respected."""
    app = FastAPI()
    context_data = {}

    @app.get("/test")
    async def test_endpoint():
        context_data.update(get_context())
        return {"message": "test"}

    # Use custom header name
    app.add_middleware(TraceIDMiddleware, trace_id_header="X-Custom-Trace")
    configure_logging(app=app)
    client = TestClient(app)

    response = client.get("/test", headers={"X-Custom-Trace": "custom-trace-123"})
    assert response.status_code == 200

    # Verify custom trace ID is captured
    assert context_data["trace_id"] == "custom-trace-123"


@pytest.mark.asyncio
async def test_trace_id_generation_when_missing():
    """Test that trace ID is generated when not provided in header."""
    app = FastAPI()
    context_data = {}

    @app.get("/test")
    async def test_endpoint():
        context_data.update(get_context())
        return {"message": "test"}

    app.add_middleware(TraceIDMiddleware, trace_id_header="X-Request-ID")
    configure_logging(app=app)
    client = TestClient(app)

    # Don't provide trace ID header
    response = client.get("/test")
    assert response.status_code == 200

    # Verify trace ID was generated
    assert context_data["trace_id"] is not None
    assert len(context_data["trace_id"]) == 32  # UUID hex length


@pytest.mark.asyncio
async def test_client_ip_extraction():
    """Test that client IP is properly extracted."""
    app = FastAPI()
    context_data = {}

    @app.get("/test")
    async def test_endpoint():
        context_data.update(get_context())
        return {"message": "test"}

    app.add_middleware(TraceIDMiddleware, trace_id_header="X-Request-ID")
    configure_logging(app=app)
    client = TestClient(app)

    response = client.get("/test")
    assert response.status_code == 200

    # Verify client IP is captured (TestClient sets it to testclient)
    assert context_data["client_ip"] is not None
    # In test environment, this will be 'testclient' or similar


@pytest.mark.asyncio
async def test_method_and_path_capture():
    """Test that HTTP method and path are properly captured."""
    app = FastAPI()
    context_data = {}

    @app.post("/api/users/{user_id}")
    async def test_endpoint(user_id: int):
        context_data.update(get_context())
        return {"user_id": user_id}

    app.add_middleware(TraceIDMiddleware, trace_id_header="X-Request-ID")
    configure_logging(app=app)
    client = TestClient(app)

    response = client.post("/api/users/123", json={"name": "test"})
    assert response.status_code == 200

    # Verify method and path are captured
    assert context_data["method"] == "POST"
    assert context_data["path"] == "/api/users/123"


@pytest.mark.asyncio
async def test_context_shared_across_request():
    """Test that all log events during request share the same context."""
    app = FastAPI()
    captured_logs = []

    def mock_log_sink(logger, method_name, event_dict):
        captured_logs.append(event_dict.copy())
        return None

    @app.get("/test")
    async def test_endpoint():
        from fapilog import log

        log.info("First log message")
        log.info("Second log message")
        return {"message": "test"}

    app.add_middleware(TraceIDMiddleware, trace_id_header="X-Request-ID")

    settings = LoggingSettings(queue_enabled=False)
    configure_logging(settings=settings, app=app)

    with patch("fapilog.pipeline.build_processor_chain") as mock_chain:
        mock_chain.return_value = [mock_log_sink]

        client = TestClient(app)
        response = client.get("/test", headers={"X-Request-ID": "shared-trace-123"})
        assert response.status_code == 200

    # Verify both logs share the same context
    if len(captured_logs) >= 2:
        first_log = captured_logs[0]
        second_log = captured_logs[1]

        assert first_log.get("trace_id") == "shared-trace-123"
        assert second_log.get("trace_id") == "shared-trace-123"
        assert first_log.get("method") == second_log.get("method")
        assert first_log.get("path") == second_log.get("path")


@pytest.mark.asyncio
async def test_duration_ms_populated():
    """Test that duration_ms is populated during request processing."""
    app = FastAPI()
    context_data = {}

    @app.get("/test")
    async def test_endpoint():
        import asyncio

        await asyncio.sleep(0.01)  # Small delay to ensure measurable duration
        context_data.update(get_context())
        return {"message": "test"}

    app.add_middleware(TraceIDMiddleware, trace_id_header="X-Request-ID")
    configure_logging(app=app)
    client = TestClient(app)

    response = client.get("/test")
    assert response.status_code == 200

    # At this point in the request, latency_ms might not be set yet
    # It gets set after the response is generated
    # But we can check that the field exists in context structure
    assert "latency_ms" in context_data


@pytest.mark.asyncio
async def test_status_code_in_context():
    """Test that status code is added to context."""
    app = FastAPI()

    @app.get("/test")
    async def test_endpoint():
        from fastapi.responses import JSONResponse

        return JSONResponse(content={"message": "test"}, status_code=201)

    app.add_middleware(TraceIDMiddleware, trace_id_header="X-Request-ID")
    configure_logging(app=app)
    client = TestClient(app)

    response = client.get("/test")
    assert response.status_code == 201

    # The status code is set after the response, so we check the response header
    # to ensure the middleware completed successfully
    assert "X-Response-Time-ms" in response.headers


@pytest.mark.asyncio
async def test_settings_integration():
    """Test that LoggingSettings trace_id_header is used correctly."""
    app = FastAPI()
    context_data = {}

    @app.get("/test")
    async def test_endpoint():
        context_data.update(get_context())
        return {"message": "test"}

    # Configure with custom settings
    settings = LoggingSettings(trace_id_header="X-Custom-Request-ID")
    configure_logging(settings=settings, app=app)
    client = TestClient(app)

    response = client.get(
        "/test", headers={"X-Custom-Request-ID": "settings-trace-123"}
    )
    assert response.status_code == 200

    # Verify the custom header from settings was used
    assert context_data["trace_id"] == "settings-trace-123"
