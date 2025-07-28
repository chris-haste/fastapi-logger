"""Tests for standardized sink error handling patterns."""

import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from fapilog._internal.error_handling import StandardSinkErrorHandling
from fapilog.exceptions import (
    SinkConfigurationError,
    SinkConnectionError,
    SinkError,
    SinkErrorContextBuilder,
    SinkTimeoutError,
    SinkWriteError,
)
from fapilog.sinks import FileSink, StdoutSink


class TestSinkErrorContextBuilder:
    """Test the standardized error context builder."""

    def test_build_write_context_basic(self):
        """Test basic context building."""
        event_dict = {"message": "test log", "level": "info"}

        context = SinkErrorContextBuilder.build_write_context(
            sink_name="TestSink", event_dict=event_dict, operation="write"
        )

        assert context["sink_name"] == "TestSink"
        assert context["operation"] == "write"
        assert context["event_keys"] == ["message", "level"]
        assert context["event_size"] > 0
        assert "timestamp" in context
        assert isinstance(context["timestamp"], (int, float))

    def test_build_write_context_with_additional(self):
        """Test context building with additional context."""
        event_dict = {"message": "test"}
        additional = {"file_path": "/tmp/test.log", "mode": "append"}

        context = SinkErrorContextBuilder.build_write_context(
            sink_name="FileSink",
            event_dict=event_dict,
            operation="file_write",
            additional_context=additional,
        )

        assert context["sink_name"] == "FileSink"
        assert context["operation"] == "file_write"
        assert context["file_path"] == "/tmp/test.log"
        assert context["mode"] == "append"


class TestStandardSinkErrorHandling:
    """Test the standard error handling mixin."""

    class MockSink(StandardSinkErrorHandling):
        """Mock sink for testing error handling."""

        pass

    def test_handle_connection_error(self):
        """Test connection error handling."""
        sink = self.MockSink()
        event_dict = {"message": "test"}
        error = ConnectionError("Connection failed")

        result = sink._handle_sink_error(
            error=error, operation="connect", event_dict=event_dict
        )

        assert isinstance(result, SinkConnectionError)
        assert result.sink_name == "MockSink"
        assert "connect" in result.context["operation"]

    def test_handle_timeout_error(self):
        """Test timeout error handling."""
        sink = self.MockSink()
        event_dict = {"message": "test"}
        error = TimeoutError("Operation timed out")

        result = sink._handle_sink_error(
            error=error, operation="write", event_dict=event_dict
        )

        assert isinstance(result, SinkTimeoutError)
        assert result.sink_name == "MockSink"

    def test_handle_configuration_error(self):
        """Test configuration error handling."""
        sink = self.MockSink()
        event_dict = {"message": "test"}
        error = ValueError("Invalid configuration")

        result = sink._handle_sink_error(
            error=error, operation="configure", event_dict=event_dict
        )

        assert isinstance(result, SinkConfigurationError)

    def test_handle_generic_error(self):
        """Test generic error handling (defaults to SinkWriteError)."""
        sink = self.MockSink()
        event_dict = {"message": "test"}
        error = RuntimeError("Something went wrong")

        result = sink._handle_sink_error(
            error=error, operation="write", event_dict=event_dict
        )

        assert isinstance(result, SinkWriteError)

    @patch("fapilog._internal.error_handling.log_error_with_context")
    def test_log_error_with_context(self, mock_log):
        """Test error logging with context."""
        sink = self.MockSink()
        error = SinkWriteError("Test error", "TestSink", {"test": "context"})

        sink._log_error_with_context(error)

        mock_log.assert_called_once()
        call_args = mock_log.call_args
        # Check that the error and context were passed
        assert error in call_args[0] or error in call_args[1].values()
        assert error.context in call_args[0] or error.context in call_args[1].values()


class TestFileSinkErrorHandling:
    """Test FileSink standardized error handling."""

    @pytest.mark.asyncio
    async def test_file_write_error_handling(self):
        """Test file write error handling with mock."""
        import tempfile
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / "test.log"

            sink = FileSink(str(temp_path))
            event_dict = {"message": "test log", "level": "info"}

            # Mock the _write_and_flush method to raise an error
            with patch.object(sink, "_write_and_flush") as mock_write:
                mock_write.side_effect = OSError("Mocked file error")

                with pytest.raises(SinkError) as exc_info:
                    await sink.write(event_dict)

                error = exc_info.value
                assert error.sink_name == "FileSink"
                assert "write_to_file" in error.context["operation"]
                assert "file_path" in error.context
                assert isinstance(error.context["timestamp"], (int, float))

    @pytest.mark.asyncio
    async def test_file_write_success(self):
        """Test successful file write doesn't raise errors."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            temp_path = f.name

        try:
            sink = FileSink(temp_path)
            event_dict = {"message": "test log", "level": "info"}

            # Should not raise any errors
            await sink.write(event_dict)

        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestStdoutSinkErrorHandling:
    """Test StdoutSink standardized error handling."""

    @pytest.mark.asyncio
    async def test_stdout_write_with_mock_error(self):
        """Test stdout write error handling."""
        sink = StdoutSink(mode="json")
        event_dict = {"message": "test log", "level": "info"}

        # Mock sys.stdout to raise an error
        with patch("sys.stdout") as mock_stdout:
            mock_stdout.write.side_effect = OSError("Stdout error")
            mock_stdout.isatty.return_value = False
            mock_stdout.closed = False

            with pytest.raises(SinkError) as exc_info:
                await sink.write(event_dict)

            error = exc_info.value
            assert error.sink_name == "StdoutSink"
            assert "write_to_stdout" in error.context["operation"]
            assert "mode" in error.context
            assert error.context["mode"] == "json"

    @pytest.mark.asyncio
    async def test_stdout_write_success(self):
        """Test successful stdout write doesn't raise errors."""
        sink = StdoutSink(mode="json")
        event_dict = {"message": "test log", "level": "info"}

        # Should not raise any errors
        await sink.write(event_dict)


@pytest.mark.skipif("httpx" not in sys.modules, reason="httpx not available")
class TestLokiSinkErrorHandling:
    """Test LokiSink standardized error handling."""

    @pytest.mark.asyncio
    async def test_loki_batch_error(self):
        """Test Loki batch error handling."""
        from fapilog.sinks import LokiSink

        sink = LokiSink("http://localhost:3100")
        event_dict = {"message": "test log", "level": "info"}

        # Mock the batch manager to raise an error
        with patch.object(sink._batch_manager, "add_event") as mock_add:
            mock_add.side_effect = RuntimeError("Batch error")

            with pytest.raises(SinkError) as exc_info:
                await sink.write(event_dict)

            error = exc_info.value
            assert error.sink_name == "LokiSink"
            assert "add_to_batch" in error.context["operation"]
            assert "url" in error.context
            assert "batch_size" in error.context


class TestSinkErrorHierarchy:
    """Test the sink error class hierarchy."""

    def test_sink_error_inheritance(self):
        """Test that all sink errors inherit from SinkError."""
        assert issubclass(SinkConnectionError, SinkError)
        assert issubclass(SinkWriteError, SinkError)
        assert issubclass(SinkConfigurationError, SinkError)
        assert issubclass(SinkTimeoutError, SinkError)

    def test_sink_error_context(self):
        """Test SinkError context handling."""
        context = {"key": "value", "timestamp": time.time()}
        error = SinkError("Test message", "TestSink", context)

        assert error.sink_name == "TestSink"
        assert error.context["key"] == "value"
        assert "timestamp" in error.context
        assert error.context["sink_name"] == "TestSink"  # Added by constructor

    def test_sink_error_string_representation(self):
        """Test SinkError string representation includes context."""
        context = {"operation": "write", "file_path": "/tmp/test.log"}
        error = SinkError("Write failed", "FileSink", context)

        error_str = str(error)
        assert "Write failed" in error_str
        assert "operation=write" in error_str
        assert "file_path=/tmp/test.log" in error_str


class TestErrorConsistencyAcrossSinks:
    """Test error handling consistency across all sink implementations."""

    @pytest.mark.asyncio
    async def test_all_sinks_use_standard_error_handling(self):
        """Verify all sinks inherit from StandardSinkErrorHandling."""
        # Check that all sink classes use the mixin
        assert issubclass(FileSink, StandardSinkErrorHandling)
        assert issubclass(StdoutSink, StandardSinkErrorHandling)

        # LokiSink check (only if httpx available)
        if "httpx" in sys.modules:
            from fapilog.sinks import LokiSink

            assert issubclass(LokiSink, StandardSinkErrorHandling)

    def test_error_context_consistency(self):
        """Test that all sinks provide consistent error context."""
        event_dict = {"message": "test", "level": "info"}

        # Test context structure consistency
        for sink_name in ["FileSink", "StdoutSink", "LokiSink"]:
            context = SinkErrorContextBuilder.build_write_context(
                sink_name=sink_name, event_dict=event_dict, operation="write"
            )

            # All contexts should have these standard fields
            required_fields = [
                "sink_name",
                "operation",
                "event_keys",
                "event_size",
                "timestamp",
            ]
            for field in required_fields:
                assert field in context, f"Missing {field} in {sink_name} context"

            assert context["sink_name"] == sink_name
            assert context["operation"] == "write"
            assert isinstance(context["event_keys"], list)
            assert isinstance(context["event_size"], int)
            assert isinstance(context["timestamp"], (int, float))
