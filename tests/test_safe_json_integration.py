"""Integration tests for safe JSON serialization with sinks."""

import datetime
import json
import tempfile
import uuid
from io import StringIO
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from fapilog.sinks.file import FileSink
from fapilog.sinks.loki import LokiSink
from fapilog.sinks.stdout import StdoutSink
from fapilog.utils.helpers import safe_json_serialize


class TestSafeJsonIntegration:
    """Test integration of safe JSON serialization with all sinks."""

    def create_problematic_log_event(self):
        """Create a log event with problematic serialization data."""
        # Create circular reference
        circular_dict = {"type": "circular"}
        circular_dict["self"] = circular_dict

        return {
            "timestamp": datetime.datetime.now(),
            "level": "INFO",
            "message": "Test with problematic data",
            "user_id": uuid.uuid4(),
            "circular_data": circular_dict,
            "binary_data": b"\x80\x81\x82",
            "custom_object": Mock(),
            "deep_nesting": self._create_deep_nested_dict(15),
        }

    def _create_deep_nested_dict(self, depth):
        """Create deeply nested dictionary for testing depth limits."""
        if depth <= 0:
            return "leaf"
        return {"level": depth, "child": self._create_deep_nested_dict(depth - 1)}

    @pytest.mark.asyncio
    async def test_file_sink_safe_serialization(self):
        """Test FileSink handles problematic data safely."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as tmp:
            tmp_path = tmp.name

        try:
            sink = FileSink(tmp_path)

            # Test with problematic event
            problematic_event = self.create_problematic_log_event()

            # Should not raise exception
            await sink.write(problematic_event)

            # Verify file was written and contains valid JSON
            with open(tmp_path) as f:
                log_line = f.readline().strip()

            # Should be valid JSON
            parsed = json.loads(log_line)

            # Verify key fields are preserved
            assert parsed["level"] == "INFO"
            assert parsed["message"] == "Test with problematic data"
            assert "timestamp" in parsed
            assert "user_id" in parsed

            # Verify problematic data was handled safely
            assert "circular_reference" in parsed["circular_data"]["self"]
            assert "<bytes:" in parsed["binary_data"]
            assert "function:" in parsed["custom_object"]

            sink.close()

        finally:
            # Clean up
            Path(tmp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_file_sink_large_data_handling(self):
        """Test FileSink handles large data properly."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as tmp:
            tmp_path = tmp.name

        try:
            sink = FileSink(tmp_path)

            # Create large event
            large_event = {
                "message": "Large data test",
                "large_field": "x" * 10000,  # 10KB field
                "data": list(range(1000)),
            }

            # Should not raise exception
            await sink.write(large_event)

            # Verify file was written
            with open(tmp_path) as f:
                log_line = f.readline().strip()

            # Should be valid JSON
            parsed = json.loads(log_line)
            assert parsed["message"] == "Large data test"

            sink.close()

        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_stdout_sink_safe_serialization_json_mode(self):
        """Test StdoutSink JSON mode handles problematic data safely."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            sink = StdoutSink(mode="json")

            problematic_event = self.create_problematic_log_event()

            # Should not raise exception
            await sink.write(problematic_event)

            # Verify output was written
            output = mock_stdout.getvalue().strip()

            # Should be valid JSON
            parsed = json.loads(output)

            # Verify key fields are preserved
            assert parsed["level"] == "INFO"
            assert parsed["message"] == "Test with problematic data"
            assert "circular_reference" in parsed["circular_data"]["self"]

    @pytest.mark.asyncio
    async def test_stdout_sink_safe_serialization_pretty_mode(self):
        """Test StdoutSink pretty mode handles problematic data safely."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            sink = StdoutSink(mode="pretty")

            problematic_event = self.create_problematic_log_event()

            # Should not raise exception
            await sink.write(problematic_event)

            # Verify output was written (pretty mode doesn't use JSON)
            output = mock_stdout.getvalue().strip()
            assert len(output) > 0
            # Pretty mode uses structlog's console renderer

    @pytest.mark.asyncio
    async def test_loki_sink_safe_serialization(self):
        """Test LokiSink handles problematic data safely."""
        sink = LokiSink("http://localhost:3100")

        # Mock the HTTP client component to avoid real network calls
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.raise_for_status = AsyncMock()
        mock_client.post.return_value = mock_response
        sink._http_client._client = mock_client

        problematic_event = self.create_problematic_log_event()

        # Should not raise exception
        await sink.write(problematic_event)

        # Force flush to trigger HTTP request
        await sink.flush()

        # Verify HTTP request was made
        assert mock_client.post.called

        # Get the request payload
        call_args = mock_client.post.call_args
        payload = call_args.kwargs["json"]

        # Verify structure
        assert "streams" in payload
        assert len(payload["streams"]) == 1

        stream = payload["streams"][0]
        assert "values" in stream
        assert len(stream["values"]) == 1

        # Parse the log line from the request
        log_entry = stream["values"][0]
        timestamp_ns, log_line = log_entry

        # Should be valid JSON
        parsed = json.loads(log_line)

        # Verify key fields are preserved
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "Test with problematic data"
        assert "circular_reference" in parsed["circular_data"]["self"]

        await sink.close()

    @pytest.mark.asyncio
    async def test_all_sinks_consistency(self):
        """Test that all sinks produce consistent JSON output."""
        test_event = {
            "timestamp": datetime.datetime(2023, 12, 25, 10, 30, 45),
            "level": "INFO",
            "message": "Consistency test",
            "uuid": uuid.UUID("12345678-1234-5678-1234-567812345678"),
            "nested": {"key": "value", "number": 42},
        }

        # Test File Sink
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as tmp:
            tmp_path = tmp.name

        try:
            file_sink = FileSink(tmp_path)
            await file_sink.write(test_event)
            file_sink.close()

            with open(tmp_path) as f:
                file_output = f.readline().strip()

        finally:
            Path(tmp_path).unlink(missing_ok=True)

        # Test Stdout Sink
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            stdout_sink = StdoutSink(mode="json")
            await stdout_sink.write(test_event)
            stdout_output = mock_stdout.getvalue().strip()

        # Test Loki Sink
        loki_sink = LokiSink("http://localhost:3100")

        # Mock the HTTP client component to avoid real network calls
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.raise_for_status = AsyncMock()
        mock_client.post.return_value = mock_response
        loki_sink._http_client._client = mock_client

        await loki_sink.write(test_event)
        await loki_sink.flush()

        # Extract Loki output
        call_args = mock_client.post.call_args
        payload = call_args.kwargs["json"]
        loki_output = payload["streams"][0]["values"][0][1]

        await loki_sink.close()

        # Parse all outputs
        file_parsed = json.loads(file_output)
        stdout_parsed = json.loads(stdout_output)
        loki_parsed = json.loads(loki_output)

        # All should have the same structure and values
        assert file_parsed["level"] == stdout_parsed["level"] == loki_parsed["level"]
        assert (
            file_parsed["message"] == stdout_parsed["message"] == loki_parsed["message"]
        )
        assert file_parsed["uuid"] == stdout_parsed["uuid"] == loki_parsed["uuid"]
        assert file_parsed["nested"] == stdout_parsed["nested"] == loki_parsed["nested"]

    @pytest.mark.asyncio
    async def test_backward_compatibility(self):
        """Test that normal log events work exactly as before."""
        normal_event = {
            "timestamp": "2023-12-25T10:30:45Z",
            "level": "INFO",
            "message": "Normal log event",
            "user_id": "12345",
            "metadata": {"key": "value", "count": 42},
        }

        # Test File Sink
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as tmp:
            tmp_path = tmp.name

        try:
            sink = FileSink(tmp_path)
            await sink.write(normal_event)
            sink.close()

            with open(tmp_path) as f:
                log_line = f.readline().strip()

            # Should be identical to safe JSON serialization output
            expected = safe_json_serialize(normal_event)
            assert log_line == expected

        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_performance_impact(self):
        """Test that safe serialization doesn't significantly impact performance."""
        import time

        normal_events = [
            {
                "timestamp": f"2023-12-25T10:30:{i:02d}Z",
                "level": "INFO",
                "message": f"Log message {i}",
                "user_id": f"user_{i}",
                "data": {"index": i, "value": f"value_{i}"},
            }
            for i in range(100)
        ]

        # Test with temporary file sink
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as tmp:
            tmp_path = tmp.name

        try:
            sink = FileSink(tmp_path)

            start_time = time.time()
            for event in normal_events:
                await sink.write(event)
            duration = time.time() - start_time

            sink.close()

            # Should complete within reasonable time (less than 1 second for 100 events)
            assert duration < 1.0

            # Verify all events were written correctly
            with open(tmp_path) as f:
                lines = f.readlines()

            assert len(lines) == 100

            # Spot check a few entries
            first_event = json.loads(lines[0].strip())
            assert first_event["message"] == "Log message 0"

            last_event = json.loads(lines[-1].strip())
            assert last_event["message"] == "Log message 99"

        finally:
            Path(tmp_path).unlink(missing_ok=True)
