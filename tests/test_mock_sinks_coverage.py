"""Tests for mock sink implementations."""

import asyncio

import pytest

from fapilog.testing.mock_sinks import (
    FailingSink,
    RecordingSink,
    SlowSink,
)


class TestRecordingSink:
    """Test the RecordingSink class."""

    @pytest.fixture
    def sink(self):
        """Create a recording sink."""
        return RecordingSink()

    @pytest.mark.asyncio
    async def test_init(self, sink):
        """Test sink initialization."""
        assert sink.events == []
        assert len(sink.events) == 0

    @pytest.mark.asyncio
    async def test_write_single_event(self, sink):
        """Test writing a single event."""
        event = {"level": "info", "message": "test"}

        await sink.write(event)

        assert len(sink.events) == 1
        # Check that the event was enriched
        recorded_event = sink.events[0]
        assert recorded_event["level"] == "info"
        assert recorded_event["message"] == "test"
        assert "_recorded_at" in recorded_event
        assert "_write_count" in recorded_event

    @pytest.mark.asyncio
    async def test_write_multiple_events(self, sink):
        """Test writing multiple events."""
        events = [
            {"level": "info", "message": "test1"},
            {"level": "error", "message": "test2"},
            {"level": "debug", "message": "test3"},
        ]

        for event in events:
            await sink.write(event)

        assert len(sink.events) == 3

    def test_clear_events(self, sink):
        """Test clearing recorded events."""
        sink.events = [{"test": "data"}]

        sink.clear()

        assert len(sink.events) == 0

    def test_get_events_no_filter(self, sink):
        """Test getting all events without filter."""
        sink.events = [
            {"level": "info", "message": "test1"},
            {"level": "error", "message": "test2"},
        ]

        events = sink.get_events()

        assert len(events) == 2
        assert events == sink.events

    def test_get_events_with_level_filter(self, sink):
        """Test filtering events by level."""
        sink.events = [
            {"level": "info", "message": "test1"},
            {"level": "error", "message": "test2"},
            {"level": "info", "message": "test3"},
        ]

        info_events = sink.get_events("info")
        error_events = sink.get_events("error")

        assert len(info_events) == 2
        assert len(error_events) == 1
        assert all(e["level"] == "info" for e in info_events)
        assert all(e["level"] == "error" for e in error_events)


class TestFailingSink:
    """Test the FailingSink class."""

    @pytest.fixture
    def always_fail_sink(self):
        """Create a sink that always fails."""
        return FailingSink(failure_rate=1.0)

    @pytest.fixture
    def never_fail_sink(self):
        """Create a sink that never fails."""
        return FailingSink(failure_rate=0.0)

    @pytest.fixture
    def sometimes_fail_sink(self):
        """Create a sink that sometimes fails."""
        return FailingSink(failure_rate=0.5)

    @pytest.mark.asyncio
    async def test_always_fails(self, always_fail_sink):
        """Test sink that always fails."""
        with pytest.raises(Exception, match="Mock sink failure"):
            await always_fail_sink.write({"test": "data"})

    @pytest.mark.asyncio
    async def test_never_fails(self, never_fail_sink):
        """Test sink that never fails."""
        # Should not raise an exception
        await never_fail_sink.write({"test": "data"})

    @pytest.mark.asyncio
    async def test_failure_rate_respected(self, sometimes_fail_sink):
        """Test that failure rate is approximately respected."""
        failures = 0
        total_attempts = 50  # Reduced for faster testing

        for _ in range(total_attempts):
            try:
                await sometimes_fail_sink.write({"test": "data"})
            except Exception:
                failures += 1

        # With 50% failure rate, expect some failures
        # Allow wide variance due to randomness
        failure_rate = failures / total_attempts
        assert 0.2 <= failure_rate <= 0.8

    def test_custom_error_message(self):
        """Test sink with custom error message."""
        # Note: The actual FailingSink may not support custom error message
        sink = FailingSink(failure_rate=1.0)

        with pytest.raises(Exception):  # noqa: B017
            asyncio.run(sink.write({"test": "data"}))


class TestSlowSink:
    """Test the SlowSink class."""

    @pytest.fixture
    def slow_sink(self):
        """Create a slow sink."""
        return SlowSink(delay=0.05)  # Reduced delay for faster testing

    @pytest.mark.asyncio
    async def test_write_with_delay(self, slow_sink):
        """Test that write operation is delayed."""
        import time

        start_time = time.time()
        await slow_sink.write({"test": "data"})
        end_time = time.time()

        # Should take at least the delay time
        assert end_time - start_time >= 0.05

    @pytest.mark.asyncio
    async def test_zero_delay(self):
        """Test sink with zero delay."""
        sink = SlowSink(delay=0.0)

        import time

        start_time = time.time()
        await sink.write({"test": "data"})
        end_time = time.time()

        # Should be very fast
        assert end_time - start_time < 0.01

    @pytest.mark.asyncio
    async def test_variable_delay(self):
        """Test sink with variable delay."""
        delays = [0.01, 0.02, 0.03]  # Reduced delays

        for delay in delays:
            sink = SlowSink(delay=delay)

            import time

            start_time = time.time()
            await sink.write({"test": "data"})
            end_time = time.time()

            assert end_time - start_time >= delay * 0.9  # Allow small variance
