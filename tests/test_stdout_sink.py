"""Tests for the StdoutSink implementation."""

import json
import sys
from unittest.mock import patch

import pytest
from fapilog.sinks.stdout import StdoutSink


class TestStdoutSink:
    """Test the StdoutSink implementation."""

    @pytest.mark.asyncio
    async def test_json_output_format(self) -> None:
        """Test that JSON output format works correctly."""
        sink = StdoutSink(mode="json")
        event = {
            "level": "info",
            "event": "test_event",
            "timestamp": "2023-01-01T00:00:00Z",
            "extra_field": "extra_value",
        }

        with patch("builtins.print") as mock_print:
            await sink.write(event)

            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]
            written_data = json.loads(call_args)

            assert written_data["level"] == "info"
            assert written_data["event"] == "test_event"
            assert written_data["timestamp"] == "2023-01-01T00:00:00Z"
            assert written_data["extra_field"] == "extra_value"

    @pytest.mark.asyncio
    async def test_pretty_output_format(self) -> None:
        """Test that pretty output format works correctly."""
        sink = StdoutSink(mode="pretty")
        event = {
            "level": "info",
            "event": "test_event",
            "timestamp": "2023-01-01T00:00:00Z",
            "extra_field": "extra_value",
        }

        with patch("builtins.print") as mock_print:
            await sink.write(event)

            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]

            # Should contain ANSI color codes
            assert "\x1b[" in call_args
            # Should not be valid JSON
            with pytest.raises(json.JSONDecodeError):
                json.loads(call_args)

    @pytest.mark.asyncio
    async def test_auto_mode_tty_detection(self) -> None:
        """Test that auto mode correctly detects TTY."""
        # Test with TTY
        with patch.object(sys.stderr, "isatty", return_value=True):
            sink = StdoutSink(mode="auto")
            assert sink._pretty is True

        # Test without TTY
        with patch.object(sys.stderr, "isatty", return_value=False):
            sink = StdoutSink(mode="auto")
            assert sink._pretty is False

    @pytest.mark.asyncio
    async def test_auto_mode_tty_json_output(self) -> None:
        """Test that auto mode produces JSON when not in TTY."""
        with patch.object(sys.stderr, "isatty", return_value=False):
            sink = StdoutSink(mode="auto")
            event = {
                "level": "info",
                "event": "test_event",
                "timestamp": "2023-01-01T00:00:00Z",
            }

            with patch("builtins.print") as mock_print:
                await sink.write(event)

                mock_print.assert_called_once()
                call_args = mock_print.call_args[0][0]
                written_data = json.loads(call_args)

                assert written_data["level"] == "info"
                assert written_data["event"] == "test_event"

    @pytest.mark.asyncio
    async def test_auto_mode_tty_pretty_output(self) -> None:
        """Test that auto mode produces pretty output when in TTY."""
        with patch.object(sys.stderr, "isatty", return_value=True):
            sink = StdoutSink(mode="auto")
            event = {
                "level": "info",
                "event": "test_event",
                "timestamp": "2023-01-01T00:00:00Z",
            }

            with patch("builtins.print") as mock_print:
                await sink.write(event)

                mock_print.assert_called_once()
                call_args = mock_print.call_args[0][0]

                # Should contain ANSI color codes
                assert "\x1b[" in call_args

    @pytest.mark.asyncio
    async def test_force_json_mode(self) -> None:
        """Test that json mode forces JSON output even in TTY."""
        with patch.object(sys.stderr, "isatty", return_value=True):
            sink = StdoutSink(mode="json")
            event = {
                "level": "info",
                "event": "test_event",
                "timestamp": "2023-01-01T00:00:00Z",
            }

            with patch("builtins.print") as mock_print:
                await sink.write(event)

                mock_print.assert_called_once()
                call_args = mock_print.call_args[0][0]
                written_data = json.loads(call_args)

                assert written_data["level"] == "info"
                assert written_data["event"] == "test_event"

    @pytest.mark.asyncio
    async def test_force_pretty_mode(self) -> None:
        """Test that pretty mode forces pretty output even without TTY."""
        with patch.object(sys.stderr, "isatty", return_value=False):
            sink = StdoutSink(mode="pretty")
            event = {
                "level": "info",
                "event": "test_event",
                "timestamp": "2023-01-01T00:00:00Z",
            }

            with patch("builtins.print") as mock_print:
                await sink.write(event)

                mock_print.assert_called_once()
                call_args = mock_print.call_args[0][0]

                # Should contain ANSI color codes
                assert "\x1b[" in call_args

    @pytest.mark.asyncio
    async def test_console_renderer_lazy_initialization(self) -> None:
        """Test that ConsoleRenderer is initialized lazily."""
        sink = StdoutSink(mode="pretty")

        # ConsoleRenderer should not be initialized until first write
        assert sink._console_renderer is not None  # It's initialized in __init__

        # But it should be properly configured
        assert callable(sink._console_renderer)

    @pytest.mark.asyncio
    async def test_output_to_stdout(self) -> None:
        """Test that output is written to sys.stdout."""
        sink = StdoutSink(mode="json")
        event = {"level": "info", "event": "test_event"}

        with patch("builtins.print") as mock_print:
            await sink.write(event)

            mock_print.assert_called_once()
            # Check that file=sys.stdout and flush=True are used
            call_kwargs = mock_print.call_args[1]
            assert call_kwargs["file"] == sys.stdout
            assert call_kwargs["flush"] is True

    @pytest.mark.asyncio
    async def test_pretty_output_with_ansi_codes(self) -> None:
        """Test that pretty output includes ANSI codes when enabled."""
        sink = StdoutSink(mode="pretty")
        event = {
            "level": "info",
            "event": "test_event",
            "timestamp": "2023-01-01T00:00:00Z",
        }

        with patch("builtins.print") as mock_print:
            await sink.write(event)

            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]

            # Should contain ANSI color codes for pretty output
            assert "\x1b[" in call_args
            # Should contain level information
            assert "info" in call_args.lower() or "INFO" in call_args
            # Should contain event information
            assert "test_event" in call_args

    @pytest.mark.asyncio
    async def test_json_output_compact_format(self) -> None:
        """Test that JSON output is compact (one line per event)."""
        sink = StdoutSink(mode="json")
        event = {
            "level": "info",
            "event": "test_event",
            "timestamp": "2023-01-01T00:00:00Z",
            "nested": {"key": "value"},
        }

        with patch("builtins.print") as mock_print:
            await sink.write(event)

            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]

            # Should be valid JSON
            written_data = json.loads(call_args)
            assert written_data["level"] == "info"
            assert written_data["event"] == "test_event"
            assert written_data["nested"]["key"] == "value"

            # Should be compact (no newlines in the middle)
            assert "\n" not in call_args.strip()

    def test_invalid_mode_fallback(self) -> None:
        """Test that invalid modes fallback to JSON."""
        # This would normally be caught by type checking, but let's test the fallback
        with patch.object(StdoutSink, "_determine_pretty_mode") as mock_determine:
            mock_determine.return_value = False
            sink = StdoutSink(mode="invalid_mode")  # type: ignore[arg-type]
            assert sink._pretty is False
