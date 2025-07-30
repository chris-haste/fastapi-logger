"""Tests for the base Sink class."""

from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from fapilog.sinks.base import Sink


class TestSink(Sink):
    """Test sink implementation for testing the base Sink class."""

    def __init__(self):
        super().__init__()
        self.write_calls = []

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Test implementation of write method."""
        self.write_calls.append(event_dict)


class FailingSink(Sink):
    """Test sink that fails during write operations."""

    def __init__(self):
        super().__init__()

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Failing implementation for testing error handling."""
        raise RuntimeError("Test write failure")


class TestBaseSink:
    """Test suite for the base Sink class."""

    def test_sink_initialization(self):
        """Test that Sink initializes correctly with proper sink name."""
        sink = TestSink()

        # Test that sink name is set to class name
        assert sink._sink_name == "TestSink"
        assert hasattr(sink, "_sink_name")

    def test_sink_initialization_different_class_names(self):
        """Test that different sink classes get different names."""
        test_sink = TestSink()
        failing_sink = FailingSink()

        assert test_sink._sink_name == "TestSink"
        assert failing_sink._sink_name == "FailingSink"

    def test_base_sink_write_not_implemented(self):
        """Test that base Sink.write raises NotImplementedError."""
        base_sink = Sink()

        with pytest.raises(NotImplementedError):
            # This is a coroutine, so we need to run it
            import asyncio

            asyncio.run(base_sink.write({"test": "event"}))

    @pytest.mark.asyncio
    async def test_write_with_metrics_success(self):
        """Test _write_with_metrics with successful write and metrics collection."""
        sink = TestSink()
        event_dict = {"level": "info", "event": "test_message"}

        # Mock the metrics collector
        mock_metrics = MagicMock()
        mock_get_metrics = MagicMock(return_value=mock_metrics)

        with patch("fapilog.sinks.base.get_metrics_collector", mock_get_metrics):
            with patch("time.time", side_effect=[1000.0, 1000.1]):  # 100ms latency
                await sink._write_with_metrics(event_dict)

        # Verify the write was called
        assert len(sink.write_calls) == 1
        assert sink.write_calls[0] == event_dict

        # Verify metrics were recorded
        mock_get_metrics.assert_called_once()
        mock_metrics.record_sink_write.assert_called_once()
        call_args = mock_metrics.record_sink_write.call_args[1]
        assert call_args["sink_name"] == "TestSink"
        assert (
            abs(call_args["latency_ms"] - 100.0) < 0.1
        )  # Allow floating point precision
        assert call_args["success"] is True
        assert call_args["batch_size"] == 1
        assert call_args["error"] is None

    @pytest.mark.asyncio
    async def test_write_with_metrics_failure(self):
        """Test _write_with_metrics with failed write and metrics collection."""
        sink = FailingSink()
        event_dict = {"level": "error", "event": "test_error"}

        # Mock the metrics collector
        mock_metrics = MagicMock()
        mock_get_metrics = MagicMock(return_value=mock_metrics)

        with patch("fapilog.sinks.base.get_metrics_collector", mock_get_metrics):
            with patch("time.time", side_effect=[2000.0, 2000.05]):  # 50ms latency
                with pytest.raises(RuntimeError, match="Test write failure"):
                    await sink._write_with_metrics(event_dict)

        # Verify metrics were recorded with failure
        mock_get_metrics.assert_called_once()
        mock_metrics.record_sink_write.assert_called_once()
        call_args = mock_metrics.record_sink_write.call_args[1]
        assert call_args["sink_name"] == "FailingSink"
        assert (
            abs(call_args["latency_ms"] - 50.0) < 0.1
        )  # Allow floating point precision
        assert call_args["success"] is False
        assert call_args["batch_size"] == 1
        assert call_args["error"] == "Test write failure"

    @pytest.mark.asyncio
    async def test_write_with_metrics_no_metrics_collector(self):
        """Test _write_with_metrics when no metrics collector is available."""
        sink = TestSink()
        event_dict = {"level": "debug", "event": "no_metrics"}

        # Mock metrics collector to return None
        mock_get_metrics = MagicMock(return_value=None)

        with patch("fapilog.sinks.base.get_metrics_collector", mock_get_metrics):
            await sink._write_with_metrics(event_dict)

        # Verify the write was still called
        assert len(sink.write_calls) == 1
        assert sink.write_calls[0] == event_dict

        # Verify metrics collection was attempted but no recording was done
        mock_get_metrics.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_with_metrics_no_metrics_collector_with_failure(self):
        """Test _write_with_metrics failure when no metrics collector is available."""
        sink = FailingSink()
        event_dict = {"level": "error", "event": "no_metrics_error"}

        # Mock metrics collector to return None
        mock_get_metrics = MagicMock(return_value=None)

        with patch("fapilog.sinks.base.get_metrics_collector", mock_get_metrics):
            with pytest.raises(RuntimeError, match="Test write failure"):
                await sink._write_with_metrics(event_dict)

        # Verify metrics collection was attempted but no recording was done
        mock_get_metrics.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_with_metrics_timing_accuracy(self):
        """Test that _write_with_metrics calculates timing correctly."""
        sink = TestSink()
        event_dict = {"level": "info", "event": "timing_test"}

        mock_metrics = MagicMock()
        mock_get_metrics = MagicMock(return_value=mock_metrics)

        # Test various timing scenarios
        start_time = 1500.0
        end_time = 1500.250  # 250ms latency

        with patch("fapilog.sinks.base.get_metrics_collector", mock_get_metrics):
            with patch("time.time", side_effect=[start_time, end_time]):
                await sink._write_with_metrics(event_dict)

        # Verify precise timing calculation
        expected_latency = (end_time - start_time) * 1000  # 250.0ms
        mock_metrics.record_sink_write.assert_called_once_with(
            sink_name="TestSink",
            latency_ms=expected_latency,
            success=True,
            batch_size=1,
            error=None,
        )

    @pytest.mark.asyncio
    async def test_write_with_metrics_error_message_capture(self):
        """Test that _write_with_metrics captures error messages correctly."""

        class CustomErrorSink(Sink):
            def __init__(self):
                super().__init__()

            async def write(self, event_dict: Dict[str, Any]) -> None:
                raise ValueError("Custom error message with details")

        sink = CustomErrorSink()
        event_dict = {"level": "error", "event": "custom_error"}

        mock_metrics = MagicMock()
        mock_get_metrics = MagicMock(return_value=mock_metrics)

        with patch("fapilog.sinks.base.get_metrics_collector", mock_get_metrics):
            with patch("time.time", return_value=3000.0):
                with pytest.raises(
                    ValueError, match="Custom error message with details"
                ):
                    await sink._write_with_metrics(event_dict)

        # Verify error message was captured
        mock_metrics.record_sink_write.assert_called_once()
        call_args = mock_metrics.record_sink_write.call_args[1]
        assert call_args["success"] is False
        assert call_args["error"] == "Custom error message with details"
        assert call_args["sink_name"] == "CustomErrorSink"

    @pytest.mark.asyncio
    async def test_write_with_metrics_finally_block_execution(self):
        """Test that _write_with_metrics always executes the finally block."""
        sink = FailingSink()
        event_dict = {"level": "error", "event": "finally_test"}

        mock_metrics = MagicMock()
        mock_get_metrics = MagicMock(return_value=mock_metrics)

        # Ensure the finally block runs even when an exception occurs
        with patch("fapilog.sinks.base.get_metrics_collector", mock_get_metrics):
            with patch("time.time", side_effect=[4000.0, 4000.1]):
                try:
                    await sink._write_with_metrics(event_dict)
                except RuntimeError:
                    pass  # Expected exception

        # Verify metrics were recorded despite the exception
        mock_get_metrics.assert_called_once()
        mock_metrics.record_sink_write.assert_called_once()
        call_args = mock_metrics.record_sink_write.call_args[1]
        assert call_args["success"] is False
        assert call_args["sink_name"] == "FailingSink"
