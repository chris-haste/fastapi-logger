"""Tests for context utilities."""

import asyncio

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from fapilog._internal.context import (
    bind_context,
    clear_context,
    context_copy,
    get_context,
    get_span_id,
    get_trace_id,
)
from fapilog.bootstrap import configure_logging
from fapilog.exceptions import ContextError


def test_get_context_returns_expected_keys():
    """Test that get_context() returns expected keys during a request."""
    app = FastAPI()

    @app.get("/test")
    async def test_endpoint():
        context = get_context()
        return {
            "has_trace_id": "trace_id" in context,
            "has_span_id": "span_id" in context,
            "has_latency_ms": "latency_ms" in context,
            "has_status_code": "status_code" in context,
            "has_req_bytes": "req_bytes" in context,
            "has_res_bytes": "res_bytes" in context,
            "has_user_agent": "user_agent" in context,
            "has_client_ip": "client_ip" in context,
            "has_method": "method" in context,
            "has_path": "path" in context,
            "has_user_id": "user_id" in context,
            "has_user_roles": "user_roles" in context,
            "has_auth_scheme": "auth_scheme" in context,
            "context_keys": list(context.keys()),
        }

    configure_logging(app=app)
    client = TestClient(app)
    response = client.get("/test")

    assert response.status_code == 200
    data = response.json()

    # All expected keys should be present
    assert data["has_trace_id"]
    assert data["has_span_id"]
    assert data["has_latency_ms"]
    assert data["has_status_code"]
    assert data["has_req_bytes"]
    assert data["has_res_bytes"]
    assert data["has_user_agent"]
    assert data["has_client_ip"]
    assert data["has_method"]
    assert data["has_path"]
    assert data["has_user_id"]
    assert data["has_user_roles"]
    assert data["has_auth_scheme"]

    # Should have exactly 13 keys (10 original + 3 user context vars)
    assert len(data["context_keys"]) == 13
    assert set(data["context_keys"]) == {
        "trace_id",
        "span_id",
        "latency_ms",
        "status_code",
        "req_bytes",
        "res_bytes",
        "user_agent",
        "client_ip",
        "method",
        "path",
        "user_id",
        "user_roles",
        "auth_scheme",
    }


def test_clear_context_wipes_values():
    """Test that clear_context() wipes values and subsequent get_context() shows None."""
    # Set some context values
    bind_context(
        trace_id="test-trace",
        span_id="test-span",
        latency_ms=100.0,
        status_code=200,
        req_bytes=1024,
        res_bytes=2048,
        user_agent="test-agent",
    )

    # Verify values are set
    context_before = get_context()
    assert context_before["trace_id"] == "test-trace"
    assert context_before["span_id"] == "test-span"
    assert context_before["latency_ms"] == 100.0
    assert context_before["status_code"] == 200
    assert context_before["req_bytes"] == 1024
    assert context_before["res_bytes"] == 2048
    assert context_before["user_agent"] == "test-agent"

    # Clear context
    clear_context()

    # Verify all values are None
    context_after = get_context()
    for value in context_after.values():
        assert value is None


def test_bind_context_sets_values():
    """Test that bind_context() correctly sets context values."""
    # Clear any existing context
    clear_context()

    # Set values using bind_context
    bind_context(
        trace_id="new-trace",
        span_id="new-span",
        latency_ms=150.0,
        status_code=201,
        req_bytes=512,
        res_bytes=1024,
        user_agent="new-agent",
    )

    # Verify values are set correctly
    context = get_context()
    assert context["trace_id"] == "new-trace"
    assert context["span_id"] == "new-span"
    assert context["latency_ms"] == 150.0
    assert context["status_code"] == 201
    assert context["req_bytes"] == 512
    assert context["res_bytes"] == 1024
    assert context["user_agent"] == "new-agent"


def test_bind_context_partial_update():
    """Test that bind_context() can update individual values."""
    # Clear any existing context first
    clear_context()

    # Set initial values
    bind_context(trace_id="initial-trace", span_id="initial-span")

    # Update only trace_id
    bind_context(trace_id="updated-trace")

    # Verify only trace_id was updated
    context = get_context()
    assert context["trace_id"] == "updated-trace"
    assert context["span_id"] == "initial-span"
    assert context["latency_ms"] is None
    assert context["status_code"] is None
    assert context["req_bytes"] is None
    assert context["res_bytes"] is None
    assert context["user_agent"] is None


def test_bind_context_invalid_key():
    """Test that bind_context() raises ContextError for invalid keys."""
    with pytest.raises(ContextError, match="Invalid context key: invalid_key"):
        bind_context(invalid_key="value")


def test_context_copy_propagates_to_background_task():
    """Test that context_copy() propagates context to background tasks."""
    app = FastAPI()
    background_results = []

    async def background_task():
        """Background task that should inherit context."""
        context = get_context()
        background_results.append(
            {
                "trace_id": context["trace_id"],
                "span_id": context["span_id"],
                "latency_ms": context["latency_ms"],
            }
        )

    @app.get("/test-background")
    async def test_endpoint():
        # Create background task with context copy
        task = asyncio.create_task(context_copy().run(background_task))
        await task

        # Return the current context for comparison
        context = get_context()
        return {
            "trace_id": context["trace_id"],
            "span_id": context["span_id"],
            "latency_ms": context["latency_ms"],
        }

    configure_logging(app=app)
    client = TestClient(app)
    response = client.get("/test-background")

    assert response.status_code == 200
    data = response.json()

    # Background task should have inherited the same context
    assert len(background_results) == 1
    background_context = background_results[0]

    assert background_context["trace_id"] == data["trace_id"]
    assert background_context["span_id"] == data["span_id"]
    assert background_context["latency_ms"] == data["latency_ms"]


def test_no_context_leakage_between_requests():
    """Test that separate requests receive different trace_ids (no leakage)."""
    app = FastAPI()

    @app.get("/get-context")
    async def get_context_endpoint():
        return get_context()

    configure_logging(app=app)
    client = TestClient(app)

    # Make first request
    response1 = client.get("/get-context")
    assert response1.status_code == 200
    context1 = response1.json()

    # Make second request
    response2 = client.get("/get-context")
    assert response2.status_code == 200
    context2 = response2.json()

    # Trace IDs should be different (no leakage)
    assert context1["trace_id"] != context2["trace_id"]
    assert context1["span_id"] != context2["span_id"]

    # Both should have valid UUID format
    import re

    uuid_pattern = r"[0-9a-f]{32}"
    assert re.fullmatch(uuid_pattern, context1["trace_id"])
    assert re.fullmatch(uuid_pattern, context2["trace_id"])
    assert re.fullmatch(uuid_pattern, context1["span_id"])
    assert re.fullmatch(uuid_pattern, context2["span_id"])


def test_context_cleanup_after_request():
    """Test that context is cleaned up after request completion."""
    # Clear any existing context first
    clear_context()

    app = FastAPI()

    @app.get("/test")
    async def test_endpoint():
        # Set some custom context during request
        bind_context(latency_ms=999.0, status_code=418)
        return {"status": "ok"}

    configure_logging(app=app)
    client = TestClient(app)

    # Make request
    response = client.get("/test")
    assert response.status_code == 200

    # After request, context should be cleared
    context_after = get_context()
    for value in context_after.values():
        assert value is None


def test_context_copy_with_multiple_tasks():
    """Test context propagation with multiple background tasks."""
    app = FastAPI()
    task_results = []

    async def background_task(task_id: int):
        """Background task that logs its context."""
        context = get_context()
        task_results.append(
            {
                "task_id": task_id,
                "trace_id": context["trace_id"],
                "span_id": context["span_id"],
            }
        )

    @app.get("/test-multiple-tasks")
    async def test_endpoint():
        # Create multiple background tasks
        tasks = []
        for i in range(3):
            task = asyncio.create_task(context_copy().run(background_task, i))
            tasks.append(task)

        # Wait for all tasks to complete
        await asyncio.gather(*tasks)

        # Return the main request context
        context = get_context()
        return {
            "trace_id": context["trace_id"],
            "span_id": context["span_id"],
        }

    configure_logging(app=app)
    client = TestClient(app)
    response = client.get("/test-multiple-tasks")

    assert response.status_code == 200
    data = response.json()

    # All tasks should have the same context as the main request
    assert len(task_results) == 3
    for task_result in task_results:
        assert task_result["trace_id"] == data["trace_id"]
        assert task_result["span_id"] == data["span_id"]

    # Task IDs should be different
    task_ids = [r["task_id"] for r in task_results]
    assert len(set(task_ids)) == 3


@pytest.fixture(autouse=True)
def cleanup_context():
    """Automatically clean up context before and after each test."""
    clear_context()
    yield
    clear_context()


def test_legacy_functions_for_coverage():
    """Test legacy functions to improve coverage."""
    from fapilog._internal.context import (
        reset_request_metadata,
        reset_response_metadata,
        reset_trace_context,
        set_request_metadata,
        set_response_metadata,
        set_trace_context,
    )

    # Test set_trace_context and reset_trace_context
    token_tid, token_sid = set_trace_context("legacy-trace", "legacy-span")
    assert get_trace_id() == "legacy-trace"
    assert get_span_id() == "legacy-span"

    reset_trace_context(token_tid, token_sid)
    assert get_trace_id() is None
    assert get_span_id() is None

    # Test set_request_metadata and reset_request_metadata
    token_req, token_ua = set_request_metadata(1024, "legacy-agent")
    context = get_context()
    assert context["req_bytes"] == 1024
    assert context["user_agent"] == "legacy-agent"

    reset_request_metadata(token_req, token_ua)
    context = get_context()
    assert context["req_bytes"] is None
    assert context["user_agent"] is None

    # Test set_response_metadata and reset_response_metadata
    token_res, token_status, token_latency = set_response_metadata(2048, 200, 150.0)
    context = get_context()
    assert context["res_bytes"] == 2048
    assert context["status_code"] == 200
    assert context["latency_ms"] == 150.0

    reset_response_metadata(token_res, token_status, token_latency)
    context = get_context()
    assert context["res_bytes"] is None
    assert context["status_code"] is None
    assert context["latency_ms"] is None


def test_context_copy_with_none_values():
    """Test context_copy() with None values in context."""
    # Clear any existing context first
    clear_context()

    # Set some values to None explicitly
    bind_context(
        trace_id=None,
        span_id=None,
        latency_ms=None,
        status_code=None,
        req_bytes=None,
        res_bytes=None,
        user_agent=None,
    )

    # Create a copy
    copied_context = context_copy()

    # Verify the copy has the same None values by running a function in the copied context
    async def check_context():
        context = get_context()
        return context

    # Run the function in the copied context
    import asyncio

    result = asyncio.run(copied_context.run(check_context))

    # Verify all values are None
    for value in result.values():
        assert value is None


def test_context_copy_with_mixed_values():
    """Test context_copy() with mixed None and non-None values."""
    # Clear any existing context first
    clear_context()

    # Set mixed values
    bind_context(
        trace_id="mixed-trace",
        span_id=None,
        latency_ms=150.0,
        status_code=None,
        req_bytes=1024,
        res_bytes=None,
        user_agent="mixed-agent",
    )

    # Create a copy
    copied_context = context_copy()

    # Verify the copy has the same mixed values by running a function in the copied context
    async def check_context():
        context = get_context()
        return context

    # Run the function in the copied context
    import asyncio

    result = asyncio.run(copied_context.run(check_context))

    assert result["trace_id"] == "mixed-trace"
    assert result["span_id"] is None
    assert result["latency_ms"] == 150.0
    assert result["status_code"] is None
    assert result["req_bytes"] == 1024
    assert result["res_bytes"] is None
    assert result["user_agent"] == "mixed-agent"


def test_context_copy_run_with_exception():
    """Test context_copy().run() with an exception in the background task."""
    app = FastAPI()
    background_results = []

    async def background_task_with_exception():
        """Background task that raises an exception."""
        context = get_context()
        background_results.append(
            {
                "trace_id": context["trace_id"],
                "span_id": context["span_id"],
            }
        )
        raise ValueError("Background task error")

    @app.get("/test-background-exception")
    async def test_endpoint():
        # Create background task with context copy
        try:
            task = asyncio.create_task(
                context_copy().run(background_task_with_exception)
            )
            await task
        except ValueError:
            # Expected exception
            pass

        # Return the current context for comparison
        context = get_context()
        return {
            "trace_id": context["trace_id"],
            "span_id": context["span_id"],
        }

    configure_logging(app=app)
    client = TestClient(app)
    response = client.get("/test-background-exception")

    assert response.status_code == 200
    data = response.json()

    # Background task should have inherited the same context before the exception
    assert len(background_results) == 1
    background_context = background_results[0]

    assert background_context["trace_id"] == data["trace_id"]
    assert background_context["span_id"] == data["span_id"]


def test_bind_context_with_all_none_values():
    """Test bind_context() with all None values."""
    # Clear any existing context first
    clear_context()

    # Set all values to None
    bind_context(
        trace_id=None,
        span_id=None,
        latency_ms=None,
        status_code=None,
        req_bytes=None,
        res_bytes=None,
        user_agent=None,
    )

    # Verify all values are None
    context = get_context()
    for value in context.values():
        assert value is None


def test_bind_context_with_zero_values():
    """Test bind_context() with zero values."""
    # Clear any existing context first
    clear_context()

    # Set zero values
    bind_context(
        trace_id="zero-trace",
        span_id="zero-span",
        latency_ms=0.0,
        status_code=0,
        req_bytes=0,
        res_bytes=0,
        user_agent="zero-agent",
    )

    # Verify zero values are set correctly
    context = get_context()
    assert context["trace_id"] == "zero-trace"
    assert context["span_id"] == "zero-span"
    assert context["latency_ms"] == 0.0
    assert context["status_code"] == 0
    assert context["req_bytes"] == 0
    assert context["res_bytes"] == 0
    assert context["user_agent"] == "zero-agent"


def test_get_context_outside_request():
    """Test get_context() outside of a request context."""
    # Clear any existing context first
    clear_context()

    # Get context outside of request
    context = get_context()

    # All values should be None
    for value in context.values():
        assert value is None


def test_context_isolation_between_tests():
    """Test that context is properly isolated between different test runs."""
    # Clear any existing context first
    clear_context()

    # Set some values
    bind_context(trace_id="test-isolation", span_id="test-span")

    # Verify values are set
    context = get_context()
    assert context["trace_id"] == "test-isolation"
    assert context["span_id"] == "test-span"

    # Clear context
    clear_context()

    # Verify context is cleared
    context_after = get_context()
    for value in context_after.values():
        assert value is None


def test_context_copy_basic_functionality():
    """Test basic context_copy() functionality."""
    # Clear any existing context first
    clear_context()

    # Set some values
    bind_context(trace_id="test-trace", span_id="test-span", latency_ms=100.0)

    # Create a copy
    copied_context = context_copy()

    # Verify the copy works by running a function in the copied context
    async def check_copied_context():
        context = get_context()
        return context

    # Run the function in the copied context
    import asyncio

    copied_values = asyncio.run(copied_context.run(check_copied_context))

    # Verify the copied context has the expected values
    assert copied_values["trace_id"] == "test-trace"
    assert copied_values["span_id"] == "test-span"
    assert copied_values["latency_ms"] == 100.0
