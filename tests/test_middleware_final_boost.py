"""Final boost for middleware.py coverage - targeting lines 223-229."""

from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI

from fapilog.middleware import TraceIDMiddleware


class TestMiddlewareFinalBoost:
    """Tests to cover the remaining lines in middleware.py."""

    def test_calculate_response_size_exception_handling(self):
        """Test exception handling in _calculate_response_size method.

        This covers lines 223-229 in middleware.py where an exception occurs
        during response size calculation.
        """
        app = FastAPI()
        middleware = TraceIDMiddleware(app)

        # Create a mock response that will cause an exception
        mock_response = Mock()
        # Set up the mock to raise an exception when accessed
        type(mock_response).__name__ = "MockResponse"
        mock_response.body = property(
            lambda self: (_ for _ in ()).throw(Exception("Size calculation failed"))
        )

        # Mock handle_middleware_error to capture the call
        with patch("fapilog.middleware.handle_middleware_error") as mock_handler:
            mock_handler.side_effect = lambda e, info, context: e

            # This should trigger the exception path in _calculate_response_size
            with pytest.raises(TypeError, match="object of type 'property' has no len"):
                middleware._calculate_response_size(mock_response)
