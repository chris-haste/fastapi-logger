"""Tests for multi-sink functionality."""

import asyncio
from unittest.mock import patch

import pytest

from fapilog._internal.queue_worker import QueueWorker
from fapilog.bootstrap import configure_logging, reset_logging
from fapilog.exceptions import SinkError
from fapilog.settings import LoggingSettings
from fapilog.sinks import Sink


class MockSink(Sink):
    """Mock sink for testing multi-sink functionality."""

    def __init__(self, name: str, should_fail: bool = False) -> None:
        """Initialize the mock sink.

        Args:
            name: Name of the sink for identification
            should_fail: Whether this sink should fail on write
        """
        self.name = name
        self.events = []
        self.write_calls = 0
        self.should_fail = should_fail

    async def write(self, event_dict: dict) -> None:
        """Write a log event to the mock sink."""
        self.write_calls += 1
        if self.should_fail:
            raise Exception(f"Mock sink {self.name} failure")
        self.events.append(event_dict)


class TestMultiSinkConfiguration:
    """Test multi-sink configuration and parsing."""

    def setup_method(self) -> None:
        """Reset logging before each test."""
        reset_logging()

    def teardown_method(self) -> None:
        """Reset logging after each test."""
        reset_logging()

    def test_multiple_sinks_from_environment(self) -> None:
        """Test that multiple sinks can be configured from environment."""
        env_vars = {
            "FAPILOG_SINKS": "stdout,file:///var/log/test.log,loki://loki:3100",
        }

        with patch.dict("os.environ", env_vars):
            settings = LoggingSettings()
            assert settings.sinks == [
                "stdout",
                "file:///var/log/test.log",
                "loki://loki:3100",
            ]

    def test_multiple_sinks_from_list(self) -> None:
        """Test that multiple sinks can be configured from a list."""
        settings = LoggingSettings(sinks=["stdout", "file:///var/log/test.log"])
        assert settings.sinks == ["stdout", "file:///var/log/test.log"]

    def test_sinks_with_whitespace(self) -> None:
        """Test that sinks with whitespace are handled correctly."""
        env_vars = {
            "FAPILOG_SINKS": "stdout , file:///var/log/test.log , loki://loki:3100",
        }

        with patch.dict("os.environ", env_vars):
            settings = LoggingSettings()
            assert settings.sinks == [
                "stdout",
                "file:///var/log/test.log",
                "loki://loki:3100",
            ]

    def test_empty_sinks_are_filtered(self) -> None:
        """Test that empty sink entries are filtered out."""
        env_vars = {
            "FAPILOG_SINKS": "stdout,,file:///var/log/test.log,,loki://loki:3100",
        }

        with patch.dict("os.environ", env_vars):
            settings = LoggingSettings()
            assert settings.sinks == [
                "stdout",
                "file:///var/log/test.log",
                "loki://loki:3100",
            ]


class TestMultiSinkFunctionality:
    """Test multi-sink functionality with mock sinks."""

    def setup_method(self) -> None:
        """Reset logging before each test."""
        reset_logging()

    def teardown_method(self) -> None:
        """Reset logging after each test."""
        reset_logging()

    @pytest.mark.asyncio
    async def test_both_sinks_receive_logs(self) -> None:
        """Test that both sinks receive log events."""
        # Create mock sinks
        sink1 = MockSink("sink1")
        sink2 = MockSink("sink2")

        # Create queue worker with multiple sinks
        worker = QueueWorker(
            sinks=[sink1, sink2],
            queue_max_size=10,
            batch_size=1,
            batch_timeout=0.1,
            retry_delay=0.01,
            max_retries=1,
        )

        # Start the worker
        await worker.start()

        # Enqueue an event
        event = {"level": "info", "event": "test_event", "data": "test_data"}
        await worker.enqueue(event)

        # Wait for processing
        await asyncio.sleep(0.2)

        # Stop the worker
        await worker.stop()

        # Verify both sinks received the event
        assert len(sink1.events) == 1
        assert len(sink2.events) == 1
        assert sink1.events[0] == event
        assert sink2.events[0] == event
        assert sink1.write_calls == 1
        assert sink2.write_calls == 1

    @pytest.mark.asyncio
    async def test_one_sink_fails_others_continue(self) -> None:
        """Test that when one sink fails, others continue to work."""
        # Create mock sinks - one that fails, one that works
        failing_sink = MockSink("failing_sink", should_fail=True)
        working_sink = MockSink("working_sink", should_fail=False)

        # Create queue worker with multiple sinks
        worker = QueueWorker(
            sinks=[failing_sink, working_sink],
            queue_max_size=10,
            batch_size=1,
            batch_timeout=0.1,
            retry_delay=0.01,
            max_retries=1,
        )

        # Start the worker
        await worker.start()

        # Enqueue multiple events
        for i in range(3):
            event = {"level": "info", "event": f"test_event_{i}", "data": f"data_{i}"}
            await worker.enqueue(event)

        # Wait for processing
        await asyncio.sleep(0.5)

        # Stop the worker
        await worker.stop()

        # Verify that the working sink received all events (may be called multiple times due to retries)
        assert (
            len(working_sink.events) >= 3
        )  # At least 3 events, may be more due to retries
        assert (
            working_sink.write_calls >= 3
        )  # Called at least 3 times, may be more due to retries

        # Verify that the failing sink was called but failed
        assert failing_sink.write_calls >= 3  # Called at least 3 times due to retries
        assert len(failing_sink.events) == 0  # No events were successfully written

        # Verify that the worker continued processing despite failures
        # (This is handled by the retry logic in QueueWorker)

    @pytest.mark.asyncio
    async def test_multiple_sinks_with_retries(self) -> None:
        """Test that multiple sinks work correctly with retry logic."""
        # Create mock sinks - one that fails initially then succeeds
        intermittent_sink = MockSink("intermittent_sink")
        working_sink = MockSink("working_sink")

        # Create queue worker with retries
        worker = QueueWorker(
            sinks=[intermittent_sink, working_sink],
            queue_max_size=10,
            batch_size=1,
            batch_timeout=0.1,
            retry_delay=0.01,
            max_retries=2,
        )

        # Start the worker
        await worker.start()

        # Make the intermittent sink fail on first call, succeed on retry
        intermittent_sink.should_fail = True

        # Enqueue an event
        event = {"level": "info", "event": "test_event", "data": "test_data"}
        await worker.enqueue(event)

        # Wait for initial processing and retries
        await asyncio.sleep(0.2)

        # Make the sink work again and enqueue another event
        intermittent_sink.should_fail = False
        event2 = {"level": "info", "event": "test_event_2", "data": "test_data_2"}
        await worker.enqueue(event2)

        # Wait for processing
        await asyncio.sleep(0.3)

        # Stop the worker
        await worker.stop()

        # Verify that the working sink received both events at least once
        assert event in working_sink.events
        assert event2 in working_sink.events

        # The intermittent sink should only have event2 (since event1 always failed)
        assert event2 in intermittent_sink.events

        # Verify that the intermittent sink was called multiple times due to retries
        assert intermittent_sink.write_calls >= 3  # 2 events + retries
        assert working_sink.write_calls >= 2  # 2 events

    def test_invalid_sink_uri_raises_on_config(self) -> None:
        """Test that invalid sink URIs raise errors during configuration."""
        # Test with invalid file URI
        settings = LoggingSettings(sinks=["file://invalid/path/that/does/not/exist"])

        with pytest.raises(SinkError) as exc_info:
            configure_logging(settings=settings)
        assert "Sink initialize failed for file" in str(exc_info.value)

        # Test with invalid Loki URI (without httpx)
        with patch("fapilog.sinks.loki.httpx", None):
            settings = LoggingSettings(sinks=["loki://loki:3100"])
            with pytest.raises(SinkError) as exc_info:
                configure_logging(settings=settings)
            assert "Sink initialize failed for loki" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_multiple_sinks_with_different_types(self) -> None:
        """Test that different sink types work together."""
        # Create mock sinks of different types
        stdout_sink = MockSink("stdout")
        file_sink = MockSink("file")
        loki_sink = MockSink("loki")

        # Create queue worker with multiple sink types
        worker = QueueWorker(
            sinks=[stdout_sink, file_sink, loki_sink],
            queue_max_size=10,
            batch_size=1,
            batch_timeout=0.1,
            retry_delay=0.01,
            max_retries=1,
        )

        # Start the worker
        await worker.start()

        # Enqueue multiple events
        events = []
        for i in range(3):
            event = {
                "level": "info",
                "event": f"test_event_{i}",
                "data": f"data_{i}",
                "timestamp": f"2024-01-01T00:00:0{i}Z",
            }
            events.append(event)
            await worker.enqueue(event)

        # Wait for processing
        await asyncio.sleep(0.3)

        # Stop the worker
        await worker.stop()

        # Verify all sinks received all events
        for sink in [stdout_sink, file_sink, loki_sink]:
            assert len(sink.events) == 3
            assert sink.write_calls == 3
            for i, event in enumerate(events):
                assert sink.events[i] == event

    @pytest.mark.asyncio
    async def test_sink_failure_isolation(self) -> None:
        """Test that sink failures are isolated and don't affect other sinks."""
        # Create three sinks: one that fails, one that works, one that fails
        failing_sink1 = MockSink("failing_sink1", should_fail=True)
        working_sink = MockSink("working_sink", should_fail=False)
        failing_sink2 = MockSink("failing_sink2", should_fail=True)

        # Create queue worker with multiple sinks
        worker = QueueWorker(
            sinks=[failing_sink1, working_sink, failing_sink2],
            queue_max_size=10,
            batch_size=1,
            batch_timeout=0.1,
            retry_delay=0.01,
            max_retries=1,
        )

        # Start the worker
        await worker.start()

        # Enqueue an event
        event = {"level": "info", "event": "test_event", "data": "test_data"}
        await worker.enqueue(event)

        # Wait for processing
        await asyncio.sleep(0.3)

        # Stop the worker
        await worker.stop()

        # Verify that the working sink received the event despite other failures
        assert (
            len(working_sink.events) >= 1
        )  # May be called multiple times due to retries
        assert working_sink.events[0] == event
        assert (
            working_sink.write_calls >= 1
        )  # Called at least once, may be more due to retries

        # Verify that failing sinks were called but didn't receive events
        assert failing_sink1.write_calls >= 1  # Called at least once due to retries
        assert failing_sink2.write_calls >= 1  # Called at least once due to retries
        assert len(failing_sink1.events) == 0
        assert len(failing_sink2.events) == 0
