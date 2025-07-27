"""Unit tests for LokiHttpClient component."""

from unittest.mock import AsyncMock

import pytest

try:
    import httpx
except ImportError:
    httpx = None

from fapilog._internal.loki_http_client import LokiHttpClient
from fapilog.exceptions import SinkError


@pytest.mark.skipif(httpx is None, reason="httpx not installed")
class TestLokiHttpClient:
    """Test cases for LokiHttpClient."""

    @pytest.mark.asyncio
    async def test_send_batch_success(self) -> None:
        """Test successful batch sending."""
        client = LokiHttpClient("http://loki:3100/loki/api/v1/push")

        # Mock successful HTTP response
        mock_http_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.raise_for_status.return_value = None
        mock_http_client.post.return_value = mock_response
        client._client = mock_http_client

        payload = {"streams": [{"stream": {}, "values": [["123", "test"]]}]}

        # Should not raise an exception
        await client.send_batch(payload)

        # Verify HTTP call was made
        mock_http_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_batch_retry_success(self) -> None:
        """Test that failed requests are retried successfully."""
        from unittest.mock import patch

        client = LokiHttpClient("http://loki:3100/loki/api/v1/push")

        # Track call count
        call_count = 0

        async def mock_send_request(payload):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                # Fail first two attempts
                raise httpx.HTTPError("Connection failed")
            # Succeed on third attempt
            return None

        # Mock the _send_request method to control retry behavior
        with patch.object(client, "_send_request", side_effect=mock_send_request):
            payload = {"streams": [{"stream": {}, "values": [["123", "test"]]}]}

            # Should succeed after retries
            await client.send_batch(payload, max_retries=2, retry_delay=0.1)

            # Verify 3 calls were made (2 failures + 1 success)
            assert call_count == 3

    @pytest.mark.asyncio
    async def test_send_batch_max_retries_exceeded(self) -> None:
        """Test that SinkError is raised when max retries are exceeded."""
        from unittest.mock import patch

        client = LokiHttpClient("http://loki:3100/loki/api/v1/push")

        # Track call count
        call_count = 0

        async def mock_send_request(payload):
            nonlocal call_count
            call_count += 1
            # Always fail
            raise httpx.HTTPError("Connection failed")

        # Mock the _send_request method to always fail
        with patch.object(client, "_send_request", side_effect=mock_send_request):
            payload = {"streams": [{"stream": {}, "values": [["123", "test"]]}]}

            # Should raise SinkError after exhausting retries
            with pytest.raises(SinkError) as exc_info:
                await client.send_batch(payload, max_retries=1, retry_delay=0.1)

            # Verify error message contains original error
            assert "Connection failed" in str(exc_info.value)

            # Verify retry attempts were made (1 original + 1 retry = 2 total)
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_close_cleanup(self) -> None:
        """Test that close properly cleans up the HTTP client."""
        client = LokiHttpClient("http://loki:3100/loki/api/v1/push")

        # Initialize client
        mock_http_client = AsyncMock()
        client._client = mock_http_client

        # Close should call aclose
        await client.close()

        mock_http_client.aclose.assert_called_once()
        assert client._client is None

    def test_is_connected_property(self) -> None:
        """Test the is_connected property."""
        client = LokiHttpClient("http://loki:3100/loki/api/v1/push")

        # Initially not connected
        assert not client.is_connected

        # After setting client
        client._client = AsyncMock()
        assert client.is_connected

        # After closing
        client._client = None
        assert not client.is_connected
