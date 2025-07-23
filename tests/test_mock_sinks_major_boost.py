"""Major coverage boost for mock_sinks.py - targeting untested classes."""

import pytest

from fapilog.testing.mock_sinks import (
    BatchingSink,
    ConditionalFailingSink,
    FailingSink,
    RecordingSink,
    SlowSink,
)


class TestConditionalFailingSink:
    """Tests for ConditionalFailingSink class."""

    @pytest.mark.asyncio
    async def test_conditional_failing_sink_init(self):
        """Test ConditionalFailingSink initialization."""
        sink = ConditionalFailingSink(fail_on_level="error", fail_on_field="password")
        assert sink.fail_on_level == "error"
        assert sink.fail_on_field == "password"
        assert sink._failure_conditions_met == 0

    @pytest.mark.asyncio
    async def test_fail_on_level_condition(self):
        """Test failing based on log level."""
        sink = ConditionalFailingSink(fail_on_level="error")

        # Should fail on error level
        with pytest.raises(Exception, match="Conditional failure: level=error"):
            await sink.write({"level": "error", "message": "error message"})

        assert sink.get_failure_count() == 1

        # Should not fail on other levels
        await sink.write({"level": "info", "message": "info message"})
        assert sink.get_failure_count() == 1  # Still 1

    @pytest.mark.asyncio
    async def test_fail_on_field_condition(self):
        """Test failing based on field presence."""
        sink = ConditionalFailingSink(fail_on_field="password")

        # Should fail when field is present
        with pytest.raises(Exception, match="Conditional failure: field=password"):
            await sink.write({"level": "info", "password": "secret"})

        assert sink.get_failure_count() == 1

        # Should not fail when field is absent
        await sink.write({"level": "info", "user": "john"})
        assert sink.get_failure_count() == 1  # Still 1

    @pytest.mark.asyncio
    async def test_fail_on_both_conditions(self):
        """Test failing when both level and field conditions are met."""
        sink = ConditionalFailingSink(fail_on_level="error", fail_on_field="password")

        # Should fail when both conditions are met
        with pytest.raises(
            Exception, match="Conditional failure: level=error, field=password"
        ):
            await sink.write({"level": "error", "password": "secret"})

        assert sink.get_failure_count() == 1

    @pytest.mark.asyncio
    async def test_fail_on_either_condition(self):
        """Test failing when either condition is met."""
        sink = ConditionalFailingSink(fail_on_level="error", fail_on_field="password")

        # Fail on level only
        with pytest.raises(Exception, match="level=error"):
            await sink.write({"level": "error", "message": "error message"})

        # Fail on field only
        with pytest.raises(Exception, match="field=password"):
            await sink.write({"level": "info", "password": "secret"})

        assert sink.get_failure_count() == 2

    @pytest.mark.asyncio
    async def test_no_failure_conditions(self):
        """Test when no failure conditions are met."""
        sink = ConditionalFailingSink(fail_on_level="error", fail_on_field="password")

        # Should not fail
        await sink.write({"level": "info", "message": "safe message"})
        assert sink.get_failure_count() == 0


class TestBatchingSink:
    """Tests for BatchingSink class."""

    @pytest.mark.asyncio
    async def test_batching_sink_init(self):
        """Test BatchingSink initialization."""
        sink = BatchingSink(batch_size=3, auto_flush=True)
        assert sink.batch_size == 3
        assert sink.auto_flush is True
        assert len(sink._batch) == 0
        assert len(sink._processed_batches) == 0

    @pytest.mark.asyncio
    async def test_auto_flush_on_batch_size(self):
        """Test automatic flushing when batch size is reached."""
        sink = BatchingSink(batch_size=3, auto_flush=True)

        # Add events - should auto-flush on 3rd event
        await sink.write({"event": 1})
        await sink.write({"event": 2})
        assert len(sink.get_current_batch()) == 2
        assert len(sink.get_batches()) == 0

        await sink.write({"event": 3})  # This should trigger flush
        assert len(sink.get_current_batch()) == 0
        assert len(sink.get_batches()) == 1
        assert len(sink.get_batches()[0]) == 3

    @pytest.mark.asyncio
    async def test_no_auto_flush(self):
        """Test batching without auto-flush."""
        sink = BatchingSink(batch_size=2, auto_flush=False)

        # Add events - should not auto-flush
        await sink.write({"event": 1})
        await sink.write({"event": 2})
        await sink.write({"event": 3})

        assert len(sink.get_current_batch()) == 3
        assert len(sink.get_batches()) == 0

    @pytest.mark.asyncio
    async def test_manual_flush(self):
        """Test manual flushing."""
        sink = BatchingSink(batch_size=5, auto_flush=False)

        await sink.write({"event": 1})
        await sink.write({"event": 2})

        # Manual flush
        await sink.flush()

        assert len(sink.get_current_batch()) == 0
        assert len(sink.get_batches()) == 1
        assert len(sink.get_batches()[0]) == 2

    @pytest.mark.asyncio
    async def test_flush_empty_batch(self):
        """Test flushing when batch is empty."""
        sink = BatchingSink(batch_size=3)

        await sink.flush()  # Should not crash
        assert len(sink.get_batches()) == 0

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test batching statistics."""
        sink = BatchingSink(batch_size=3, auto_flush=True)

        # Add events to trigger batches
        for i in range(7):  # Should create 2 full batches + 1 partial
            await sink.write({"event": i})

        stats = sink.get_stats()
        assert stats["processed_batches"] == 2
        assert stats["current_batch_size"] == 1
        assert stats["total_events"] == 7
        assert stats["configured_batch_size"] == 3

    @pytest.mark.asyncio
    async def test_get_batches_copy(self):
        """Test that get_batches returns a copy."""
        sink = BatchingSink(batch_size=2, auto_flush=True)

        await sink.write({"event": 1})
        await sink.write({"event": 2})  # Triggers flush

        batches = sink.get_batches()
        batches.clear()  # Modify returned copy

        # Original should be unchanged
        assert len(sink.get_batches()) == 1

    @pytest.mark.asyncio
    async def test_get_current_batch_copy(self):
        """Test that get_current_batch returns a copy."""
        sink = BatchingSink(batch_size=5, auto_flush=False)

        await sink.write({"event": 1})

        current = sink.get_current_batch()
        current.clear()  # Modify returned copy

        # Original should be unchanged
        assert len(sink.get_current_batch()) == 1


class TestOtherMockSinkMethods:
    """Tests for other untested methods in mock sinks."""

    @pytest.mark.asyncio
    async def test_failing_sink_reset_stats(self):
        """Test FailingSink reset_stats method."""
        sink = FailingSink(failure_rate=1.0)

        # Generate some stats
        try:
            await sink.write({"test": "event"})
        except Exception:  # More specific than bare except
            pass

        stats_before = sink.get_stats()
        assert stats_before["attempts"] > 0

        # Reset stats
        sink.reset_stats()

        stats_after = sink.get_stats()
        assert stats_after["attempts"] == 0
        assert stats_after["failures"] == 0
        assert stats_after["successes"] == 0

    @pytest.mark.asyncio
    async def test_slow_sink_reset_stats(self):
        """Test SlowSink reset_stats method."""
        sink = SlowSink(delay=0.01)

        await sink.write({"test": "event"})

        stats_before = sink.get_performance_stats()
        assert stats_before["total_delay"] > 0
        assert stats_before["write_count"] > 0

        # Reset stats
        sink.reset_stats()

        stats_after = sink.get_performance_stats()
        assert stats_after["total_delay"] == 0.0
        assert stats_after["write_count"] == 0

    @pytest.mark.asyncio
    async def test_slow_sink_with_jitter(self):
        """Test SlowSink with jitter configuration."""
        sink = SlowSink(delay=0.01, jitter=0.005)

        # Write multiple events to test jitter variation
        for i in range(3):
            await sink.write({"event": i})

        stats = sink.get_performance_stats()
        assert stats["write_count"] == 3
        assert stats["total_delay"] > 0

    @pytest.mark.asyncio
    async def test_recording_sink_additional_methods(self):
        """Test additional RecordingSink methods if any exist."""
        sink = RecordingSink()

        # Test with different levels
        await sink.write({"level": "debug", "message": "debug msg"})
        await sink.write({"level": "error", "message": "error msg"})

        # Test that events are properly stored
        events = sink.get_events()
        assert len(events) == 2
        assert events[0]["level"] == "debug"
        assert events[1]["level"] == "error"
