"""Tests for Loki sink functionality."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fapilog.sinks.loki import (
    LokiSink,
    create_loki_sink_from_uri,
    parse_loki_uri,
)


class TestLokiSink:
    """Test the LokiSink class."""

    def test_init_with_defaults(self) -> None:
        """Test LokiSink initialization with default parameters."""
        sink = LokiSink("http://loki:3100")
        assert sink.url == "http://loki:3100/loki/api/v1/push"
        assert sink.labels == {}
        assert sink.batch_size == 100
        assert sink.batch_interval == 2.0
        assert sink.timeout == 30.0
        assert sink.max_retries == 3
        assert sink.retry_delay == 1.0

    def test_init_with_custom_params(self) -> None:
        """Test LokiSink initialization with custom parameters."""
        labels = {"app": "myapi", "env": "prod"}
        sink = LokiSink(
            url="https://loki.example.com",
            labels=labels,
            batch_size=50,
            batch_interval=1.0,
            timeout=60.0,
            max_retries=5,
            retry_delay=2.0,
        )
        assert sink.url == "https://loki.example.com/loki/api/v1/push"
        assert sink.labels == labels
        assert sink.batch_size == 50
        assert sink.batch_interval == 1.0
        assert sink.timeout == 60.0
        assert sink.max_retries == 5
        assert sink.retry_delay == 2.0

    def test_init_without_httpx(self) -> None:
        """Test that LokiSink raises ImportError when httpx is not available."""
        with patch("fapilog.sinks.loki.httpx", None):
            with pytest.raises(ImportError) as exc_info:
                LokiSink("http://loki:3100")
            assert "httpx is required for LokiSink" in str(exc_info.value)
            assert "pip install fapilog[loki]" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_write_buffers_logs(self) -> None:
        """Test that write() buffers logs without immediately sending."""
        sink = LokiSink("http://loki:3100", batch_size=3)

        # Mock the HTTP client
        mock_client = AsyncMock()
        sink._client = mock_client

        # Write some logs
        event1 = {
            "timestamp": "2024-01-15T10:30:45.123Z",
            "level": "info",
            "event": "test1",
        }
        event2 = {
            "timestamp": "2024-01-15T10:30:46.456Z",
            "level": "info",
            "event": "test2",
        }

        await sink.write(event1)
        await sink.write(event2)

        # Should not have sent anything yet (batch_size=3)
        mock_client.post.assert_not_called()

        # Write one more to trigger batch
        event3 = {
            "timestamp": "2024-01-15T10:30:47.789Z",
            "level": "info",
            "event": "test3",
        }
        await sink.write(event3)

        # Should have sent the batch
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args

        # Calculate expected timestamps
        import datetime

        dt1 = datetime.datetime.fromisoformat("2024-01-15T10:30:45.123+00:00")
        dt2 = datetime.datetime.fromisoformat("2024-01-15T10:30:46.456+00:00")
        dt3 = datetime.datetime.fromisoformat("2024-01-15T10:30:47.789+00:00")

        expected_values = [
            [str(int(dt1.timestamp() * 1_000_000_000)), json.dumps(event1)],
            [str(int(dt2.timestamp() * 1_000_000_000)), json.dumps(event2)],
            [str(int(dt3.timestamp() * 1_000_000_000)), json.dumps(event3)],
        ]

        assert call_args[1]["json"]["streams"][0]["values"] == expected_values

    @pytest.mark.asyncio
    async def test_write_flush_on_interval(self) -> None:
        """Test that logs are flushed when batch_interval is reached."""
        sink = LokiSink("http://loki:3100", batch_size=100, batch_interval=0.1)

        # Mock the HTTP client
        mock_client = AsyncMock()
        sink._client = mock_client

        # Write a log
        event = {
            "timestamp": "2024-01-15T10:30:45.123Z",
            "level": "info",
            "event": "test",
        }
        await sink.write(event)

        # Should not have sent immediately
        mock_client.post.assert_not_called()

        # Wait for interval to trigger flush
        await asyncio.sleep(0.15)

        # Should have sent the batch
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_format_loki_payload(self) -> None:
        """Test that logs are formatted correctly for Loki."""
        labels = {"app": "myapi", "env": "prod"}
        sink = LokiSink("http://loki:3100", labels=labels)

        events = [
            {
                "timestamp": "2024-01-15T10:30:45.123Z",
                "level": "info",
                "event": "test1",
            },
            {
                "timestamp": "2024-01-15T10:30:46.456Z",
                "level": "error",
                "event": "test2",
            },
        ]

        payload = sink._format_loki_payload(events)

        assert payload["streams"][0]["stream"] == labels
        assert len(payload["streams"][0]["values"]) == 2

        # Check first event - use actual timestamp calculation
        timestamp1, logline1 = payload["streams"][0]["values"][0]
        # Calculate expected timestamp
        import datetime

        dt1 = datetime.datetime.fromisoformat("2024-01-15T10:30:45.123+00:00")
        expected_ns1 = int(dt1.timestamp() * 1_000_000_000)
        assert timestamp1 == str(expected_ns1)
        assert json.loads(logline1) == events[0]

        # Check second event
        timestamp2, logline2 = payload["streams"][0]["values"][1]
        dt2 = datetime.datetime.fromisoformat("2024-01-15T10:30:46.456+00:00")
        expected_ns2 = int(dt2.timestamp() * 1_000_000_000)
        assert timestamp2 == str(expected_ns2)
        assert json.loads(logline2) == events[1]

    @pytest.mark.asyncio
    async def test_format_loki_payload_with_unix_timestamp(self) -> None:
        """Test that Unix timestamps are handled correctly."""
        sink = LokiSink("http://loki:3100")

        # Use Unix timestamp
        timestamp = 1705315845.123
        events = [{"timestamp": timestamp, "level": "info", "event": "test"}]

        payload = sink._format_loki_payload(events)

        timestamp_ns, logline = payload["streams"][0]["values"][0]
        expected_ns = int(timestamp * 1_000_000_000)
        assert timestamp_ns == str(expected_ns)
        assert json.loads(logline) == events[0]

    @pytest.mark.asyncio
    async def test_retry_on_failure(self) -> None:
        """Test that failed requests are retried with exponential backoff."""
        sink = LokiSink("http://loki:3100", max_retries=2, retry_delay=0.1)

        # Mock the HTTP client to fail twice, then succeed
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = [
            httpx.HTTPError("Connection failed"),
            httpx.HTTPError("Connection failed"),
            None,  # Success on third attempt
        ]
        mock_client.post.return_value = mock_response
        sink._client = mock_client

        # Write a log to trigger send
        event = {
            "timestamp": "2024-01-15T10:30:45.123Z",
            "level": "info",
            "event": "test",
        }
        await sink.write(event)

        # Explicitly flush to trigger the retry logic
        await sink.flush()

        # Wait for the async retry attempts to complete
        await asyncio.sleep(0.5)

        # Should have been called 3 times (2 failures + 1 success)
        assert mock_client.post.call_count == 3

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self) -> None:
        """Test that errors are logged when max retries are exceeded."""
        sink = LokiSink("http://loki:3100", max_retries=1, retry_delay=0.1)

        # Mock the HTTP client to always fail
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPError(
            "Connection failed"
        )
        mock_client.post.return_value = mock_response
        sink._client = mock_client

        # Write a log to trigger send
        event = {
            "timestamp": "2024-01-15T10:30:45.123Z",
            "level": "info",
            "event": "test",
        }
        await sink.write(event)

        # Explicitly flush to trigger the retry logic
        await sink.flush()

        # Wait for the async retry attempts to complete
        await asyncio.sleep(0.5)

        # Should have been called 2 times (1 failure + 1 retry)
        assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_close_flushes_remaining_logs(self) -> None:
        """Test that close() flushes any remaining logs."""
        sink = LokiSink("http://loki:3100", batch_size=3)

        # Mock the HTTP client
        mock_client = AsyncMock()
        sink._client = mock_client

        # Write some logs (less than batch_size)
        event1 = {
            "timestamp": "2024-01-15T10:30:45.123Z",
            "level": "info",
            "event": "test1",
        }
        event2 = {
            "timestamp": "2024-01-15T10:30:46.456Z",
            "level": "info",
            "event": "test2",
        }

        await sink.write(event1)
        await sink.write(event2)

        # Should not have sent anything yet
        mock_client.post.assert_not_called()

        # Close the sink
        await sink.close()

        # Should have sent the remaining logs
        mock_client.post.assert_called_once()
        mock_client.aclose.assert_called_once()


class TestParseLokiUri:
    """Test the parse_loki_uri function."""

    def test_parse_loki_uri_basic(self) -> None:
        """Test parsing a basic loki:// URI."""
        url, labels, batch_size, batch_interval = parse_loki_uri("loki://loki:3100")

        assert url == "http://loki:3100"
        assert labels == {}
        assert batch_size == 100
        assert batch_interval == 2.0

    def test_parse_loki_uri_with_labels(self) -> None:
        """Test parsing a loki:// URI with labels."""
        url, labels, batch_size, batch_interval = parse_loki_uri(
            "loki://loki:3100?labels=app=myapi,env=prod"
        )

        assert url == "http://loki:3100"
        assert labels == {"app": "myapi", "env": "prod"}
        assert batch_size == 100
        assert batch_interval == 2.0

    def test_parse_loki_uri_with_batch_params(self) -> None:
        """Test parsing a loki:// URI with batch parameters."""
        url, labels, batch_size, batch_interval = parse_loki_uri(
            "loki://loki:3100?batch_size=50&batch_interval=1.5"
        )

        assert url == "http://loki:3100"
        assert labels == {}
        assert batch_size == 50
        assert batch_interval == 1.5

    def test_parse_loki_uri_with_all_params(self) -> None:
        """Test parsing a loki:// URI with all parameters."""
        url, labels, batch_size, batch_interval = parse_loki_uri(
            "loki://loki:3100?labels=app=myapi,env=prod&batch_size=25&batch_interval=0.5"
        )

        assert url == "http://loki:3100"
        assert labels == {"app": "myapi", "env": "prod"}
        assert batch_size == 25
        assert batch_interval == 0.5

    def test_parse_https_uri(self) -> None:
        """Test parsing an https:// URI."""
        url, labels, batch_size, batch_interval = parse_loki_uri(
            "https://loki.example.com?labels=app=myapi"
        )

        assert url == "https://loki.example.com"
        assert labels == {"app": "myapi"}
        assert batch_size == 100
        assert batch_interval == 2.0

    def test_parse_loki_uri_invalid_scheme(self) -> None:
        """Test that invalid schemes raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_loki_uri("http://loki:3100")
        assert "Invalid scheme 'http'" in str(exc_info.value)

    def test_parse_loki_uri_missing_host(self) -> None:
        """Test that missing host raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_loki_uri("loki://")
        assert "Host is required" in str(exc_info.value)

    def test_parse_loki_uri_invalid_batch_size(self) -> None:
        """Test that invalid batch_size raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_loki_uri("loki://loki:3100?batch_size=invalid")
        assert "Invalid batch_size parameter" in str(exc_info.value)

    def test_parse_loki_uri_negative_batch_size(self) -> None:
        """Test that negative batch_size raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_loki_uri("loki://loki:3100?batch_size=-1")
        assert "Invalid batch_size parameter" in str(exc_info.value)

    def test_parse_loki_uri_invalid_batch_interval(self) -> None:
        """Test that invalid batch_interval raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_loki_uri("loki://loki:3100?batch_interval=invalid")
        assert "Invalid batch_interval parameter" in str(exc_info.value)

    def test_parse_loki_uri_negative_batch_interval(self) -> None:
        """Test that negative batch_interval raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_loki_uri("loki://loki:3100?batch_interval=-1")
        assert "Invalid batch_interval parameter" in str(exc_info.value)


class TestCreateLokiSinkFromUri:
    """Test the create_loki_sink_from_uri function."""

    def test_create_loki_sink_from_uri_basic(self) -> None:
        """Test creating a LokiSink from a basic URI."""
        sink = create_loki_sink_from_uri("loki://loki:3100")

        assert sink.url == "http://loki:3100/loki/api/v1/push"
        assert sink.labels == {}
        assert sink.batch_size == 100
        assert sink.batch_interval == 2.0

    def test_create_loki_sink_from_uri_with_params(self) -> None:
        """Test creating a LokiSink from a URI with parameters."""
        sink = create_loki_sink_from_uri(
            "loki://loki:3100?labels=app=myapi,env=prod&batch_size=50&batch_interval=1.0"
        )

        assert sink.url == "http://loki:3100/loki/api/v1/push"
        assert sink.labels == {"app": "myapi", "env": "prod"}
        assert sink.batch_size == 50
        assert sink.batch_interval == 1.0

    def test_create_loki_sink_from_uri_invalid_uri(self) -> None:
        """Test that invalid URIs raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            create_loki_sink_from_uri("invalid-uri")
        assert "Invalid Loki URI" in str(exc_info.value)

    def test_create_loki_sink_from_uri_without_httpx(self) -> None:
        """Test that missing httpx raises ImportError."""
        with patch("fapilog.sinks.loki.httpx", None):
            with pytest.raises(ImportError) as exc_info:
                create_loki_sink_from_uri("loki://loki:3100")
            assert "httpx is required for LokiSink" in str(exc_info.value)
