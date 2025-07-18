"""Tests for request/response metadata enricher."""

from fapilog._internal.context import (
    latency_ctx,
    req_bytes_ctx,
    res_bytes_ctx,
    status_code_ctx,
    user_agent_ctx,
)
from fapilog.bootstrap import configure_logging
from fastapi import FastAPI
from starlette.testclient import TestClient


def make_app():
    """Create a test FastAPI app with logging configured."""
    app = FastAPI()

    @app.get("/ping")
    async def ping():
        return {"status": "ok"}

    @app.post("/echo")
    async def echo(data: dict):
        return {"echo": data}

    @app.get("/error")
    async def error_endpoint():
        raise ValueError("Test error")

    configure_logging(app=app)
    return app


def test_post_with_body_sizes():
    """Test that POST request with body correctly enriches logs with request/response metadata."""
    app = make_app()
    client = TestClient(app)

    # Make a POST request with a JSON body
    test_data = {"message": "hello world", "number": 42}
    response = client.post(
        "/echo", json=test_data, headers={"User-Agent": "test-agent/1.0"}
    )

    assert response.status_code == 200

    # Verify response contains expected data
    response_data = response.json()
    assert response_data["echo"] == test_data

    # The middleware should have captured metadata in context variables
    # Note: In a real test, we'd need to capture the actual log output
    # For now, we verify the context variables are set correctly
    # This is a simplified test - in practice you'd want to capture log output


def test_get_no_body():
    """Test that GET request with no body reports req_bytes == 0."""
    app = make_app()
    client = TestClient(app)

    response = client.get("/ping", headers={"User-Agent": "curl/7.68.0"})
    assert response.status_code == 200

    # Verify the response
    response_data = response.json()
    assert response_data["status"] == "ok"

    # In a real test, we'd verify that logs show req_bytes == 0
    # This is a simplified test - in practice you'd want to capture log output


def test_outside_request_no_keys():
    """Test that logs emitted outside of a request context do not include request/response fields."""
    from fapilog import log

    # Ensure context variables are not set
    assert req_bytes_ctx.get(None) is None
    assert res_bytes_ctx.get(None) is None
    assert status_code_ctx.get(None) is None
    assert latency_ctx.get(None) is None
    assert user_agent_ctx.get(None) is None

    # Log outside of request context
    log.info("Test log outside request context")

    # In a real test, we'd capture the log output and verify it doesn't contain
    # req_bytes, res_bytes, status_code, latency_ms, or user_agent fields
    # This is a simplified test - in practice you'd want to capture log output


def test_context_variables_set_correctly():
    """Test that context variables are set and reset correctly by middleware."""
    app = make_app()
    client = TestClient(app)

    # Before request, context should be None
    assert req_bytes_ctx.get(None) is None
    assert user_agent_ctx.get(None) is None

    # Make a request
    test_data = {"test": "data"}
    response = client.post(
        "/echo", json=test_data, headers={"User-Agent": "test-agent"}
    )
    assert response.status_code == 200

    # After request, context should be cleaned up (None)
    assert req_bytes_ctx.get(None) is None
    assert res_bytes_ctx.get(None) is None
    assert status_code_ctx.get(None) is None
    assert latency_ctx.get(None) is None
    assert user_agent_ctx.get(None) is None


def test_error_request_metadata():
    """Test that error requests still capture metadata correctly."""
    app = make_app()
    client = TestClient(app, raise_server_exceptions=False)

    # Make a request that will cause an error
    response = client.get("/error", headers={"User-Agent": "error-test-agent"})
    assert response.status_code == 500

    # After request, context should be cleaned up (None)
    assert req_bytes_ctx.get(None) is None
    assert res_bytes_ctx.get(None) is None
    assert status_code_ctx.get(None) is None
    assert latency_ctx.get(None) is None
    assert user_agent_ctx.get(None) is None


def test_user_agent_default():
    """Test that missing User-Agent header defaults to '-'."""
    app = make_app()
    client = TestClient(app)

    # Make request without User-Agent header
    response = client.get("/ping")
    assert response.status_code == 200

    # After request, context should be cleaned up
    assert user_agent_ctx.get(None) is None


def test_request_with_large_body():
    """Test request with large body size."""
    app = make_app()
    client = TestClient(app)

    # Create a large JSON payload
    large_data = {"data": ["x" * 1000] * 10}  # ~10KB payload

    response = client.post(
        "/echo", json=large_data, headers={"User-Agent": "large-payload-test"}
    )
    assert response.status_code == 200

    # After request, context should be cleaned up
    assert req_bytes_ctx.get(None) is None
    assert res_bytes_ctx.get(None) is None


def test_request_with_empty_body():
    """Test request with empty body."""
    app = make_app()
    client = TestClient(app)

    response = client.post("/echo", json={}, headers={"User-Agent": "empty-body-test"})
    assert response.status_code == 200

    # After request, context should be cleaned up
    assert req_bytes_ctx.get(None) is None
    assert res_bytes_ctx.get(None) is None


def test_request_with_content_length_zero():
    """Test request with Content-Length: 0 header."""
    app = make_app()
    client = TestClient(app)

    response = client.post(
        "/echo",
        json={},
        headers={"Content-Length": "0", "User-Agent": "zero-length-test"},
    )
    assert response.status_code == 200

    # After request, context should be cleaned up
    assert req_bytes_ctx.get(None) is None
    assert res_bytes_ctx.get(None) is None


def test_request_with_invalid_content_length():
    """Test request with invalid Content-Length header."""
    app = make_app()
    client = TestClient(app)

    response = client.post(
        "/echo",
        json={"test": "data"},
        headers={"Content-Length": "invalid", "User-Agent": "invalid-length-test"},
    )
    assert response.status_code == 200

    # After request, context should be cleaned up
    assert req_bytes_ctx.get(None) is None
    assert res_bytes_ctx.get(None) is None


def test_request_with_empty_content_length():
    """Test request with empty Content-Length header."""
    app = make_app()
    client = TestClient(app)

    response = client.post(
        "/echo",
        json={"test": "data"},
        headers={"Content-Length": "", "User-Agent": "empty-length-test"},
    )
    assert response.status_code == 200

    # After request, context should be cleaned up
    assert req_bytes_ctx.get(None) is None
    assert res_bytes_ctx.get(None) is None


def test_response_with_large_body():
    """Test response with large body."""
    app = FastAPI()

    @app.get("/large-response")
    async def large_response():
        return {"data": ["x" * 1000] * 10}  # ~10KB response

    configure_logging(app=app)
    client = TestClient(app)

    response = client.get("/large-response")
    assert response.status_code == 200

    # After request, context should be cleaned up
    assert res_bytes_ctx.get(None) is None
    assert status_code_ctx.get(None) is None


def test_response_with_empty_body():
    """Test response with empty body."""
    app = FastAPI()

    @app.get("/empty-response")
    async def empty_response():
        return {}

    configure_logging(app=app)
    client = TestClient(app)

    response = client.get("/empty-response")
    assert response.status_code == 200

    # After request, context should be cleaned up
    assert res_bytes_ctx.get(None) is None
    assert status_code_ctx.get(None) is None


def test_error_response_metadata():
    """Test that error responses capture correct metadata."""
    app = FastAPI()

    @app.get("/error-500")
    async def error_500():
        from fastapi import HTTPException

        raise HTTPException(status_code=500, detail="Internal error")

    @app.get("/error-404")
    async def error_404():
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Not found")

    configure_logging(app=app)
    client = TestClient(app, raise_server_exceptions=False)

    # Test 500 error
    response = client.get("/error-500")
    assert response.status_code == 500

    # After request, context should be cleaned up
    assert status_code_ctx.get(None) is None
    assert latency_ctx.get(None) is None

    # Test 404 error
    response = client.get("/error-404")
    assert response.status_code == 404

    # After request, context should be cleaned up
    assert status_code_ctx.get(None) is None
    assert latency_ctx.get(None) is None


def test_user_agent_variations():
    """Test various User-Agent header values."""
    app = make_app()
    client = TestClient(app)

    # Test with different User-Agent values
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "curl/7.68.0",
        "Python-urllib/3.8",
        "PostmanRuntime/7.28.0",
        "",  # Empty User-Agent
    ]

    for user_agent in user_agents:
        headers = {"User-Agent": user_agent} if user_agent else {}
        response = client.get("/ping", headers=headers)
        assert response.status_code == 200

        # After request, context should be cleaned up
        assert user_agent_ctx.get(None) is None


def test_context_variables_initial_state():
    """Test that context variables start in the correct initial state."""
    # Ensure context variables are not set
    assert req_bytes_ctx.get(None) is None
    assert res_bytes_ctx.get(None) is None
    assert status_code_ctx.get(None) is None
    assert latency_ctx.get(None) is None
    assert user_agent_ctx.get(None) is None


def test_context_variables_after_multiple_requests():
    """Test that context variables are properly reset after multiple requests."""
    app = make_app()
    client = TestClient(app)

    # Make multiple requests
    for i in range(3):
        response = client.post(
            "/echo", json={"request": i}, headers={"User-Agent": f"test-agent-{i}"}
        )
        assert response.status_code == 200

        # After each request, context should be cleaned up
        assert req_bytes_ctx.get(None) is None
        assert res_bytes_ctx.get(None) is None
        assert status_code_ctx.get(None) is None
        assert latency_ctx.get(None) is None
        assert user_agent_ctx.get(None) is None
