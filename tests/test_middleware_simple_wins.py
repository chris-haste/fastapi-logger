"""Simple tests for middleware functionality - easy coverage wins."""

from unittest.mock import MagicMock, Mock, patch

import pytest
from starlette.requests import Request
from starlette.responses import JSONResponse

from fapilog.exceptions import MiddlewareError
from fapilog.middleware import TraceIDMiddleware


class TestMiddlewareErrorHandling:
    """Test middleware error handling paths that are easy to trigger."""

    @pytest.fixture
    def middleware(self):
        """Create a middleware instance."""
        return TraceIDMiddleware(app=MagicMock(), trace_id_header="X-Request-ID")

    def test_extract_request_metadata_with_missing_url(self, middleware):
        """Test _extract_request_metadata when request has no url attribute."""
        request = Mock(spec=Request)
        request.method = "POST"
        # Don't set url attribute to trigger the hasattr check
        del request.url

        # This should raise MiddlewareError due to missing url
        with pytest.raises(MiddlewareError):
            middleware._extract_request_metadata(request)

    def test_extract_request_metadata_with_none_url(self, middleware):
        """Test _extract_request_metadata when request.url is None."""
        request = Mock(spec=Request)
        request.method = "DELETE"
        request.url = None

        # This should raise MiddlewareError due to None url
        with pytest.raises(MiddlewareError):
            middleware._extract_request_metadata(request)


class TestResponseSizeCalculation:
    """Test response size calculation scenarios."""

    @pytest.fixture
    def middleware(self):
        """Create a middleware instance."""
        return TraceIDMiddleware(app=MagicMock(), trace_id_header="X-Request-ID")

    def test_json_response_with_body(self, middleware):
        """Test response size calculation for JSON responses with body."""
        response = JSONResponse(content={"message": "test", "data": [1, 2, 3]})

        # Override the body attribute to have serializable data
        response.body = {"message": "test", "data": [1, 2, 3]}
        response.media_type = "application/json"

        size = middleware._calculate_response_size(response)

        # Should calculate size based on JSON serialization
        assert isinstance(size, int)
        assert size > 0

    def test_json_response_without_body(self, middleware):
        """Test response size calculation for JSON responses without body."""
        response = JSONResponse(content=None)
        response.media_type = "application/json"
        response.body = None

        size = middleware._calculate_response_size(response)

        # Should handle None body gracefully
        assert size == 0

    def test_response_with_direct_body(self, middleware):
        """Test response size calculation with direct body content."""
        response = Mock()
        response.body = b"Hello, World!"

        size = middleware._calculate_response_size(response)

        assert size == len("Hello, World!")

    def test_response_without_body(self, middleware):
        """Test response size calculation without body."""
        response = Mock()
        response.body = None

        # Mock hasattr to return False for media_type
        with patch("builtins.hasattr", return_value=False):
            size = middleware._calculate_response_size(response)
            assert size == 0


class TestMiddlewareEdgeCases:
    """Test edge cases that trigger error handling paths."""

    @pytest.fixture
    def middleware(self):
        """Create a middleware instance."""
        return TraceIDMiddleware(app=MagicMock(), trace_id_header="X-Request-ID")

    def test_set_request_context_exception_handling(self, middleware):
        """Test exception handling in _set_request_context method."""
        request = Mock(spec=Request)
        metadata = {"method": "GET", "path": "/test"}
        trace_id = "test-trace-123"
        span_id = "test-span-456"

        # Mock context binding to raise an exception
        with patch(
            "fapilog.middleware.bind_context", side_effect=Exception("Context error")
        ):
            with pytest.raises(MiddlewareError):
                middleware._set_request_context(request, trace_id, span_id, metadata)


if __name__ == "__main__":
    pytest.main([__file__])
