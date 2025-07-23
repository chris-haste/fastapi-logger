"""Final coverage boost for mock sinks module."""

import pytest

from fapilog.testing.mock_sinks import FailingSink, RecordingSink, SlowSink


class TestMockSinksBoost:
    """Simple tests to boost mock sinks coverage."""

    @pytest.mark.asyncio
    async def test_recording_sink_get_events_by_level(self):
        """Test RecordingSink get_events with level filtering."""
        sink = RecordingSink()

        await sink.write({"level": "info", "message": "info message"})
        await sink.write({"level": "error", "message": "error message"})
        await sink.write({"level": "info", "message": "another info"})

        # Test getting events by level
        info_events = sink.get_events(level="info")
        assert len(info_events) == 2

        error_events = sink.get_events(level="error")
        assert len(error_events) == 1

        # Test getting all events
        all_events = sink.get_events()
        assert len(all_events) == 3

    @pytest.mark.asyncio
    async def test_failing_sink_different_failure_rates(self):
        """Test FailingSink with different failure rates."""
        # Always fail
        sink = FailingSink(failure_rate=1.0)
        with pytest.raises(Exception):  # noqa: B017
            await sink.write({"test": "data"})

        # Never fail
        sink = FailingSink(failure_rate=0.0)
        await sink.write({"test": "data"})  # Should not raise

    @pytest.mark.asyncio
    async def test_slow_sink_timing(self):
        """Test SlowSink actually delays."""
        import time

        sink = SlowSink(delay=0.01)  # Short delay for testing

        start_time = time.time()
        await sink.write({"test": "data"})
        duration = time.time() - start_time

        # Should have taken at least the delay time
        assert duration >= 0.01

    def test_recording_sink_clear(self):
        """Test RecordingSink clear functionality."""
        sink = RecordingSink()

        # Add some events
        sink.events = [{"test": "event1"}, {"test": "event2"}]
        sink._write_count = 2

        # Clear should reset everything
        sink.clear()
        assert len(sink.events) == 0
        assert sink._write_count == 0

    @pytest.mark.asyncio
    async def test_recording_sink_enrichment(self):
        """Test RecordingSink enriches events with metadata."""
        sink = RecordingSink()

        original_event = {"level": "info", "message": "test"}
        await sink.write(original_event)

        recorded_events = sink.get_events()
        assert len(recorded_events) == 1

        recorded_event = recorded_events[0]

        # Should have original data
        assert recorded_event["level"] == "info"
        assert recorded_event["message"] == "test"

        # Should have enriched metadata
        assert "_recorded_at" in recorded_event
        assert "_write_count" in recorded_event
        assert recorded_event["_write_count"] == 0

    @pytest.mark.asyncio
    async def test_recording_sink_write_count(self):
        """Test RecordingSink tracks write count correctly."""
        sink = RecordingSink()

        # Write multiple events
        for i in range(3):
            await sink.write({"event": i})

        events = sink.get_events()

        # Should have correct write counts
        assert events[0]["_write_count"] == 0
        assert events[1]["_write_count"] == 1
        assert events[2]["_write_count"] == 2

    def test_failing_sink_random_behavior(self):
        """Test FailingSink uses random behavior correctly."""
        # Test with partial failure rate
        sink = FailingSink(failure_rate=0.5)

        # Should have failure_rate attribute
        assert sink.failure_rate == 0.5

        # Test random behavior is set up
        assert hasattr(sink, "failure_rate")

    @pytest.mark.asyncio
    async def test_slow_sink_properties(self):
        """Test SlowSink delay property and behavior."""
        # Test with custom delay
        sink = SlowSink(delay=0.05)
        assert sink.delay == 0.05

        # Test with default delay
        default_sink = SlowSink()
        assert hasattr(default_sink, "delay")

        # Ensure write method exists and works
        await default_sink.write({"test": "data"})

    @pytest.mark.asyncio
    async def test_recording_sink_level_filtering_edge_cases(self):
        """Test edge cases for level filtering."""
        sink = RecordingSink()

        # Add events with missing or None levels
        await sink.write({"message": "no level"})
        await sink.write({"level": None, "message": "none level"})
        await sink.write({"level": "debug", "message": "debug level"})

        # Filter by non-existent level
        missing_events = sink.get_events(level="warning")
        assert len(missing_events) == 0

        # Filter by existing level
        debug_events = sink.get_events(level="debug")
        assert len(debug_events) == 1

        # Get all events
        all_events = sink.get_events()
        assert len(all_events) == 3
