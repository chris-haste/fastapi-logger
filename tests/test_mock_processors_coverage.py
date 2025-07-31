"""Comprehensive tests for mock processors to increase coverage."""

import time
from typing import Any, Dict
from unittest.mock import Mock

import pytest

from fapilog.exceptions import ProcessorExecutionError
from fapilog.testing.mock_processors import (
    BatchingProcessor,
    ConditionalFailingProcessor,
    FailingProcessor,
    FilteringProcessor,
    RecordingProcessor,
    SlowProcessor,
    TransformProcessor,
)


class TestRecordingProcessor:
    """Test RecordingProcessor functionality."""

    def test_initialization(self):
        """Test processor initialization."""
        processor = RecordingProcessor()
        assert processor.recorded_events == []
        assert processor._process_count == 0

    def test_process_single_event(self):
        """Test processing a single event."""
        processor = RecordingProcessor()
        logger = Mock()
        event_dict = {"level": "INFO", "message": "test"}

        result = processor.process(logger, "info", event_dict)

        # Original event returned unchanged
        assert result == event_dict

        # Event recorded with metadata
        assert len(processor.recorded_events) == 1
        recorded = processor.recorded_events[0]
        assert recorded["level"] == "INFO"
        assert recorded["message"] == "test"
        assert "_recorded_at" in recorded
        assert recorded["_process_count"] == 0
        assert recorded["_method_name"] == "info"

    def test_process_multiple_events(self):
        """Test processing multiple events."""
        processor = RecordingProcessor()
        logger = Mock()

        events = [
            {"level": "INFO", "message": "event1"},
            {"level": "ERROR", "message": "event2"},
            {"level": "DEBUG", "message": "event3"},
        ]

        for event in events:
            result = processor.process(logger, "log", event)
            assert result == event

        assert len(processor.recorded_events) == 3
        for i, recorded in enumerate(processor.recorded_events):
            assert recorded["_process_count"] == i
            assert recorded["message"] == f"event{i + 1}"

    def test_clear(self):
        """Test clearing recorded events."""
        processor = RecordingProcessor()
        logger = Mock()

        # Add some events
        processor.process(logger, "info", {"level": "INFO", "message": "test1"})
        processor.process(logger, "info", {"level": "INFO", "message": "test2"})

        assert len(processor.recorded_events) == 2
        assert processor._process_count == 2

        # Clear
        processor.clear()

        assert processor.recorded_events == []
        assert processor._process_count == 0

    def test_get_events_all(self):
        """Test getting all events."""
        processor = RecordingProcessor()
        logger = Mock()

        events = [
            {"level": "INFO", "message": "info_event"},
            {"level": "ERROR", "message": "error_event"},
            {"level": "INFO", "message": "info_event2"},
        ]

        for event in events:
            processor.process(logger, "log", event)

        all_events = processor.get_events()
        assert len(all_events) == 3

    def test_get_events_filtered_by_level(self):
        """Test getting events filtered by level."""
        processor = RecordingProcessor()
        logger = Mock()

        events = [
            {"level": "INFO", "message": "info_event"},
            {"level": "ERROR", "message": "error_event"},
            {"level": "INFO", "message": "info_event2"},
        ]

        for event in events:
            processor.process(logger, "log", event)

        info_events = processor.get_events(level="INFO")
        assert len(info_events) == 2
        for event in info_events:
            assert event["level"] == "INFO"

        error_events = processor.get_events(level="ERROR")
        assert len(error_events) == 1
        assert error_events[0]["level"] == "ERROR"

        # Non-existent level
        debug_events = processor.get_events(level="DEBUG")
        assert len(debug_events) == 0

    def test_get_last_event(self):
        """Test getting the last event."""
        processor = RecordingProcessor()
        logger = Mock()

        # No events
        assert processor.get_last_event() == {}

        # Add events
        event1 = {"level": "INFO", "message": "first"}
        event2 = {"level": "ERROR", "message": "second"}

        processor.process(logger, "log", event1)
        last = processor.get_last_event()
        assert last["message"] == "first"

        processor.process(logger, "log", event2)
        last = processor.get_last_event()
        assert last["message"] == "second"

    def test_get_stats(self):
        """Test getting processing statistics."""
        processor = RecordingProcessor()
        logger = Mock()

        # Empty stats
        stats = processor.get_stats()
        assert stats["total_events"] == 0
        assert stats["process_count"] == 0
        assert stats["level_counts"] == {}

        # Add events
        events = [
            {"level": "INFO", "message": "info1"},
            {"level": "INFO", "message": "info2"},
            {"level": "ERROR", "message": "error1"},
            {"level": "DEBUG", "message": "debug1"},
        ]

        for event in events:
            processor.process(logger, "log", event)

        stats = processor.get_stats()
        assert stats["total_events"] == 4
        assert stats["process_count"] == 4
        assert stats["level_counts"]["INFO"] == 2  # type: ignore[index]
        assert stats["level_counts"]["ERROR"] == 1  # type: ignore[index]
        assert stats["level_counts"]["DEBUG"] == 1  # type: ignore[index]

    def test_get_stats_unknown_level(self):
        """Test stats with events without level."""
        processor = RecordingProcessor()
        logger = Mock()

        # Event without level
        processor.process(logger, "log", {"message": "no_level"})

        stats = processor.get_stats()
        assert stats["level_counts"]["unknown"] == 1  # type: ignore[index]


class TestFailingProcessor:
    """Test FailingProcessor functionality."""

    def test_initialization_defaults(self):
        """Test processor initialization with defaults."""
        processor = FailingProcessor()
        assert processor.failure_rate == 1.0
        assert processor.failure_message == "Mock processor failure"
        assert processor.fail_on_start is False
        assert processor.fail_on_stop is False
        assert processor._attempt_count == 0
        assert processor._failure_count == 0

    def test_initialization_custom(self):
        """Test processor initialization with custom values."""
        processor = FailingProcessor(
            failure_rate=0.5,
            failure_message="Custom failure",
            fail_on_start=True,
            fail_on_stop=True,
        )
        assert processor.failure_rate == 0.5
        assert processor.failure_message == "Custom failure"
        assert processor.fail_on_start is True
        assert processor.fail_on_stop is True

    @pytest.mark.asyncio
    async def test_start_failure(self):
        """Test start failure."""
        processor = FailingProcessor(fail_on_start=True)

        with pytest.raises(ProcessorExecutionError, match="Processor start failure"):
            await processor._start_impl()

    @pytest.mark.asyncio
    async def test_start_success(self):
        """Test successful start."""
        processor = FailingProcessor(fail_on_start=False)
        # Should not raise
        await processor._start_impl()

    @pytest.mark.asyncio
    async def test_stop_failure(self):
        """Test stop failure."""
        processor = FailingProcessor(fail_on_stop=True)

        with pytest.raises(ProcessorExecutionError, match="Processor stop failure"):
            await processor._stop_impl()

    @pytest.mark.asyncio
    async def test_stop_success(self):
        """Test successful stop."""
        processor = FailingProcessor(fail_on_stop=False)
        # Should not raise
        await processor._stop_impl()

    def test_process_always_fails(self):
        """Test processing with 100% failure rate."""
        processor = FailingProcessor(failure_rate=1.0)
        logger = Mock()
        event_dict = {"level": "INFO", "message": "test"}

        with pytest.raises(ProcessorExecutionError, match="Mock processor failure"):
            processor.process(logger, "info", event_dict)

        assert processor._attempt_count == 1
        assert processor._failure_count == 1

    def test_process_never_fails(self):
        """Test processing with 0% failure rate."""
        processor = FailingProcessor(failure_rate=0.0)
        logger = Mock()
        event_dict = {"level": "INFO", "message": "test"}

        # Should not fail
        result = processor.process(logger, "info", event_dict)
        assert result == event_dict

        assert processor._attempt_count == 1
        assert processor._failure_count == 0

    def test_get_stats(self):
        """Test getting failure statistics."""
        processor = FailingProcessor(failure_rate=1.0)
        logger = Mock()
        event_dict = {"level": "INFO", "message": "test"}

        stats = processor.get_stats()
        assert stats["attempts"] == 0
        assert stats["failures"] == 0
        assert stats["successes"] == 0

        # Trigger some failures
        for _ in range(3):
            try:
                processor.process(logger, "info", event_dict)
            except ProcessorExecutionError:
                pass

        stats = processor.get_stats()
        assert stats["attempts"] == 3
        assert stats["failures"] == 3
        assert stats["successes"] == 0

    def test_reset_stats(self):
        """Test resetting failure statistics."""
        processor = FailingProcessor(failure_rate=1.0)
        logger = Mock()
        event_dict = {"level": "INFO", "message": "test"}

        # Generate some stats
        try:
            processor.process(logger, "info", event_dict)
        except ProcessorExecutionError:
            pass

        assert processor._attempt_count == 1
        assert processor._failure_count == 1

        # Reset
        processor.reset_stats()

        assert processor._attempt_count == 0
        assert processor._failure_count == 0

    def test_custom_failure_message(self):
        """Test custom failure message."""
        custom_message = "Custom error occurred"
        processor = FailingProcessor(failure_rate=1.0, failure_message=custom_message)
        logger = Mock()
        event_dict = {"level": "INFO", "message": "test"}

        with pytest.raises(ProcessorExecutionError, match=custom_message):
            processor.process(logger, "info", event_dict)


class TestSlowProcessor:
    """Test SlowProcessor functionality."""

    def test_initialization_defaults(self):
        """Test processor initialization with defaults."""
        processor = SlowProcessor()
        assert processor.delay_ms == 100
        assert processor._total_delay == 0.0
        assert processor._call_count == 0

    def test_initialization_custom(self):
        """Test processor initialization with custom delay."""
        processor = SlowProcessor(delay_ms=50)
        assert processor.delay_ms == 50

    def test_process_with_delay(self):
        """Test processing with artificial delay."""
        processor = SlowProcessor(delay_ms=10)  # Short delay for testing
        logger = Mock()
        event_dict = {"level": "INFO", "message": "test"}

        start_time = time.time()
        result = processor.process(logger, "info", event_dict)
        end_time = time.time()

        # Check delay was applied (with some tolerance)
        elapsed_ms = (end_time - start_time) * 1000
        assert elapsed_ms >= 8  # Allow some tolerance

        # Check result contains timing info
        assert result["level"] == "INFO"
        assert result["message"] == "test"
        assert result["_processing_delay_ms"] == 10
        assert result["_call_count"] == 1

        # Check internal stats
        assert processor._call_count == 1
        assert processor._total_delay >= 0.008  # 8ms in seconds

    def test_multiple_calls_timing(self):
        """Test timing statistics with multiple calls."""
        processor = SlowProcessor(delay_ms=5)  # Very short delay
        logger = Mock()

        for i in range(3):
            event_dict = {"level": "INFO", "message": f"test{i}"}
            result = processor.process(logger, "info", event_dict)
            assert result["_call_count"] == i + 1

        assert processor._call_count == 3

    def test_get_timing_stats(self):
        """Test getting timing statistics."""
        processor = SlowProcessor(delay_ms=10)
        logger = Mock()

        # No calls yet
        stats = processor.get_timing_stats()
        assert stats["total_delay_seconds"] == 0.0
        assert stats["call_count"] == 0
        assert stats["average_delay_seconds"] == 0
        assert stats["configured_delay_ms"] == 10

        # After some calls
        for _ in range(2):
            event_dict = {"level": "INFO", "message": "test"}
            processor.process(logger, "info", event_dict)

        stats = processor.get_timing_stats()
        assert stats["call_count"] == 2
        assert stats["total_delay_seconds"] > 0
        assert stats["average_delay_seconds"] > 0
        assert stats["configured_delay_ms"] == 10


class TestTransformProcessor:
    """Test TransformProcessor functionality."""

    def test_initialization_default(self):
        """Test processor initialization with default transform."""
        processor = TransformProcessor()
        logger = Mock()
        event_dict = {"level": "INFO", "message": "test"}

        # Default transform should be identity function
        result = processor.process(logger, "info", event_dict)
        assert result == event_dict
        assert processor._transformation_count == 1

    def test_initialization_custom_transform(self):
        """Test processor initialization with custom transform."""

        def add_prefix(event: Dict[str, Any]) -> Dict[str, Any]:
            result = event.copy()
            result["message"] = f"PREFIX: {result.get('message', '')}"
            return result

        processor = TransformProcessor(transform_func=add_prefix)
        logger = Mock()
        event_dict = {"level": "INFO", "message": "test"}

        result = processor.process(logger, "info", event_dict)
        assert result["level"] == "INFO"
        assert result["message"] == "PREFIX: test"
        assert processor._transformation_count == 1

    def test_transform_count(self):
        """Test transformation count tracking."""
        processor = TransformProcessor()
        logger = Mock()

        assert processor.get_transformation_count() == 0

        for i in range(3):
            event_dict = {"level": "INFO", "message": f"test{i}"}
            processor.process(logger, "info", event_dict)

        assert processor.get_transformation_count() == 3

    def test_transform_function_returns_non_dict(self):
        """Test transform function returning non-dict."""

        def bad_transform(event: Dict[str, Any]) -> str:  # type: ignore
            return "not a dict"

        processor = TransformProcessor(transform_func=bad_transform)
        logger = Mock()
        event_dict = {"level": "INFO", "message": "test"}

        with pytest.raises(
            ProcessorExecutionError, match="Transform function must return dict"
        ):
            processor.process(logger, "info", event_dict)

        # Count increments before validation, so it will be 1 even on failure
        assert processor._transformation_count == 1

    def test_transform_function_raises_exception(self):
        """Test transform function raising an exception."""

        def failing_transform(event: Dict[str, Any]) -> Dict[str, Any]:
            raise ValueError("Transform failed")

        processor = TransformProcessor(transform_func=failing_transform)
        logger = Mock()
        event_dict = {"level": "INFO", "message": "test"}

        with pytest.raises(
            ProcessorExecutionError, match="Transform function failed: Transform failed"
        ):
            processor.process(logger, "info", event_dict)

        # Count doesn't increment on exception during transform
        assert processor._transformation_count == 0

    def test_transform_function_raises_processor_error(self):
        """Test transform function raising ProcessorExecutionError directly."""

        def error_transform(event: Dict[str, Any]) -> Dict[str, Any]:
            raise ProcessorExecutionError("Direct processor error")

        processor = TransformProcessor(transform_func=error_transform)
        logger = Mock()
        event_dict = {"level": "INFO", "message": "test"}

        with pytest.raises(ProcessorExecutionError, match="Direct processor error"):
            processor.process(logger, "info", event_dict)

        # Count doesn't increment on exception during transform
        assert processor._transformation_count == 0


class TestConditionalFailingProcessor:
    """Test ConditionalFailingProcessor functionality."""

    def test_initialization(self):
        """Test processor initialization."""
        processor = ConditionalFailingProcessor()
        assert processor.fail_on_level is None
        assert processor.fail_on_field is None
        assert processor.fail_on_value is None
        assert processor._failure_conditions_met == 0

    def test_fail_on_level(self):
        """Test failing on specific log level."""
        processor = ConditionalFailingProcessor(fail_on_level="ERROR")
        logger = Mock()

        # Should pass INFO level
        info_event = {"level": "INFO", "message": "info"}
        result = processor.process(logger, "info", info_event)
        assert result == info_event

        # Should fail on ERROR level
        error_event = {"level": "ERROR", "message": "error"}
        with pytest.raises(
            ProcessorExecutionError, match="Conditional failure: level=ERROR"
        ):
            processor.process(logger, "error", error_event)

        assert processor.get_failure_count() == 1

    def test_fail_on_field(self):
        """Test failing on specific field presence."""
        processor = ConditionalFailingProcessor(fail_on_field="sensitive_data")
        logger = Mock()

        # Should pass without the field
        normal_event = {"level": "INFO", "message": "normal"}
        result = processor.process(logger, "info", normal_event)
        assert result == normal_event

        # Should fail with the field
        sensitive_event = {
            "level": "INFO",
            "message": "test",
            "sensitive_data": "secret",
        }
        with pytest.raises(
            ProcessorExecutionError, match="Conditional failure: field=sensitive_data"
        ):
            processor.process(logger, "info", sensitive_event)

        assert processor.get_failure_count() == 1

    def test_fail_on_value(self):
        """Test failing on specific value presence."""
        processor = ConditionalFailingProcessor(fail_on_value="forbidden")
        logger = Mock()

        # Should pass without the value
        normal_event = {"level": "INFO", "message": "normal"}
        result = processor.process(logger, "info", normal_event)
        assert result == normal_event

        # Should fail with the value
        forbidden_event = {"level": "INFO", "data": "forbidden"}
        with pytest.raises(
            ProcessorExecutionError, match="Conditional failure: value=forbidden"
        ):
            processor.process(logger, "info", forbidden_event)

        assert processor.get_failure_count() == 1

    def test_multiple_conditions(self):
        """Test multiple failure conditions."""
        processor = ConditionalFailingProcessor(
            fail_on_level="ERROR", fail_on_field="secret", fail_on_value="bad"
        )
        logger = Mock()

        # Event that triggers all conditions
        bad_event = {"level": "ERROR", "secret": "data", "other": "bad"}
        with pytest.raises(ProcessorExecutionError) as exc_info:
            processor.process(logger, "error", bad_event)

        # Should mention all triggered conditions
        error_msg = str(exc_info.value)
        assert "level=ERROR" in error_msg
        assert "field=secret" in error_msg
        assert "value=bad" in error_msg

        assert processor.get_failure_count() == 1

    def test_no_conditions_met(self):
        """Test event that doesn't meet any failure conditions."""
        processor = ConditionalFailingProcessor(
            fail_on_level="ERROR", fail_on_field="secret", fail_on_value="bad"
        )
        logger = Mock()

        normal_event = {"level": "INFO", "message": "normal"}
        result = processor.process(logger, "info", normal_event)
        assert result == normal_event
        assert processor.get_failure_count() == 0


class TestBatchingProcessor:
    """Test BatchingProcessor functionality."""

    def test_initialization(self):
        """Test processor initialization."""
        processor = BatchingProcessor()
        assert processor.batch_size == 5
        assert processor.auto_process is True
        assert processor._current_batch == []
        assert processor._processed_batches == []

    def test_initialization_custom(self):
        """Test processor initialization with custom values."""
        processor = BatchingProcessor(batch_size=3, auto_process=False)
        assert processor.batch_size == 3
        assert processor.auto_process is False

    def test_process_without_auto_flush(self):
        """Test processing without auto-flush."""
        processor = BatchingProcessor(batch_size=3, auto_process=False)
        logger = Mock()

        events = [
            {"level": "INFO", "message": "event1"},
            {"level": "INFO", "message": "event2"},
        ]

        for i, event in enumerate(events):
            result = processor.process(logger, "info", event)

            # Check batch metadata
            assert result["_batch_position"] == i
            assert result["_current_batch_size"] == i + 1
            assert result["_batch_id"] == 0

            # Original event data should be preserved
            assert result["level"] == "INFO"
            assert result["message"] == event["message"]

        # Should not have auto-flushed
        assert len(processor._processed_batches) == 0
        assert len(processor._current_batch) == 2

    def test_process_with_auto_flush(self):
        """Test processing with auto-flush."""
        processor = BatchingProcessor(batch_size=2, auto_process=True)
        logger = Mock()

        events = [
            {"level": "INFO", "message": "event1"},
            {"level": "INFO", "message": "event2"},
            {"level": "INFO", "message": "event3"},
        ]

        for i, event in enumerate(events):
            result = processor.process(logger, "info", event)

            if i < 2:
                # First two events in first batch
                assert result["_batch_id"] == 0
            else:
                # Third event starts new batch
                assert result["_batch_id"] == 1

        # Should have auto-flushed first batch
        assert len(processor._processed_batches) == 1
        assert len(processor._current_batch) == 1  # Third event in new batch

    def test_manual_flush(self):
        """Test manual batch flush."""
        processor = BatchingProcessor(batch_size=5, auto_process=False)
        logger = Mock()

        # Add some events
        for i in range(3):
            event = {"level": "INFO", "message": f"event{i}"}
            processor.process(logger, "info", event)

        # Manual flush
        flushed_batch = processor.flush_batch()

        assert len(flushed_batch) == 3
        assert len(processor._processed_batches) == 1
        assert len(processor._current_batch) == 0

        # Flush empty batch
        empty_batch = processor.flush_batch()
        assert empty_batch == []

    def test_get_batches(self):
        """Test getting processed batches."""
        processor = BatchingProcessor(batch_size=2, auto_process=True)
        logger = Mock()

        # Process enough events to create multiple batches
        for i in range(5):
            event = {"level": "INFO", "message": f"event{i}"}
            processor.process(logger, "info", event)

        batches = processor.get_batches()
        assert len(batches) == 2  # Two full batches processed
        assert len(batches[0]) == 2
        assert len(batches[1]) == 2

    def test_get_current_batch(self):
        """Test getting current unflushed batch."""
        processor = BatchingProcessor(batch_size=5, auto_process=False)
        logger = Mock()

        # Add some events
        for i in range(3):
            event = {"level": "INFO", "message": f"event{i}"}
            processor.process(logger, "info", event)

        current_batch = processor.get_current_batch()
        assert len(current_batch) == 3
        assert current_batch[0]["message"] == "event0"

    def test_get_stats(self):
        """Test getting batch statistics."""
        processor = BatchingProcessor(batch_size=2, auto_process=True)
        logger = Mock()

        # Initial stats
        stats = processor.get_stats()
        assert stats["processed_batches"] == 0
        assert stats["current_batch_size"] == 0
        assert stats["total_events"] == 0
        assert stats["configured_batch_size"] == 2

        # Add events
        for i in range(5):
            event = {"level": "INFO", "message": f"event{i}"}
            processor.process(logger, "info", event)

        stats = processor.get_stats()
        assert stats["processed_batches"] == 2  # Two full batches
        assert stats["current_batch_size"] == 1  # One event in current batch
        assert stats["total_events"] == 5
        assert stats["configured_batch_size"] == 2


class TestFilteringProcessor:
    """Test FilteringProcessor functionality."""

    def test_initialization(self):
        """Test processor initialization."""
        processor = FilteringProcessor()
        assert processor.filter_level is None
        assert processor.filter_field is None
        assert processor.filter_value is None
        assert processor.invert_filter is False
        assert processor._filtered_count == 0
        assert processor._passed_count == 0

    def test_filter_by_level(self):
        """Test filtering by log level."""
        processor = FilteringProcessor(filter_level="ERROR")
        logger = Mock()

        # Should pass ERROR level
        error_event = {"level": "ERROR", "message": "error"}
        result = processor.process(logger, "error", error_event)
        assert result == error_event

        # Should filter out INFO level
        info_event = {"level": "INFO", "message": "info"}
        result = processor.process(logger, "info", info_event)
        assert result is None

        stats = processor.get_filter_stats()
        assert stats["passed"] == 1
        assert stats["filtered"] == 1

    def test_filter_by_field(self):
        """Test filtering by field presence."""
        processor = FilteringProcessor(filter_field="important")
        logger = Mock()

        # Should pass event with the field
        important_event = {"level": "INFO", "message": "test", "important": True}
        result = processor.process(logger, "info", important_event)
        assert result == important_event

        # Should filter out event without the field
        normal_event = {"level": "INFO", "message": "test"}
        result = processor.process(logger, "info", normal_event)
        assert result is None

        stats = processor.get_filter_stats()
        assert stats["passed"] == 1
        assert stats["filtered"] == 1

    def test_filter_by_value(self):
        """Test filtering by value presence."""
        processor = FilteringProcessor(filter_value="allowed")
        logger = Mock()

        # Should pass event with the value
        allowed_event = {"level": "INFO", "status": "allowed"}
        result = processor.process(logger, "info", allowed_event)
        assert result == allowed_event

        # Should filter out event without the value
        other_event = {"level": "INFO", "status": "denied"}
        result = processor.process(logger, "info", other_event)
        assert result is None

        stats = processor.get_filter_stats()
        assert stats["passed"] == 1
        assert stats["filtered"] == 1

    def test_inverted_filter(self):
        """Test inverted filter logic."""
        processor = FilteringProcessor(filter_level="ERROR", invert_filter=True)
        logger = Mock()

        # Should filter out ERROR level (inverted)
        error_event = {"level": "ERROR", "message": "error"}
        result = processor.process(logger, "error", error_event)
        assert result is None

        # Should pass INFO level (inverted)
        info_event = {"level": "INFO", "message": "info"}
        result = processor.process(logger, "info", info_event)
        assert result == info_event

        stats = processor.get_filter_stats()
        assert stats["passed"] == 1
        assert stats["filtered"] == 1

    def test_multiple_filter_conditions(self):
        """Test multiple filter conditions (AND logic)."""
        processor = FilteringProcessor(
            filter_level="ERROR", filter_field="critical", filter_value="important"
        )
        logger = Mock()

        # Should pass event meeting all conditions
        matching_event = {"level": "ERROR", "critical": True, "priority": "important"}
        result = processor.process(logger, "error", matching_event)
        assert result == matching_event

        # Should filter out event missing one condition
        partial_event = {"level": "ERROR", "critical": True}  # Missing value
        result = processor.process(logger, "error", partial_event)
        assert result is None

        stats = processor.get_filter_stats()
        assert stats["passed"] == 1
        assert stats["filtered"] == 1

    def test_get_filter_stats(self):
        """Test getting filter statistics."""
        processor = FilteringProcessor(filter_level="INFO")
        logger = Mock()

        # Initial stats
        stats = processor.get_filter_stats()
        assert stats["total_processed"] == 0
        assert stats["passed"] == 0
        assert stats["filtered"] == 0
        assert stats["pass_rate_percent"] == 0

        # Process some events
        events = [
            {"level": "INFO", "message": "pass1"},
            {"level": "ERROR", "message": "filtered1"},
            {"level": "INFO", "message": "pass2"},
            {"level": "DEBUG", "message": "filtered2"},
        ]

        for event in events:
            processor.process(logger, "log", event)

        stats = processor.get_filter_stats()
        assert stats["total_processed"] == 4
        assert stats["passed"] == 2
        assert stats["filtered"] == 2
        assert stats["pass_rate_percent"] == 50.0

    def test_filter_stats_no_events(self):
        """Test filter stats with no events processed."""
        processor = FilteringProcessor()
        stats = processor.get_filter_stats()

        assert stats["total_processed"] == 0
        assert stats["passed"] == 0
        assert stats["filtered"] == 0
        assert stats["pass_rate_percent"] == 0


class TestProcessorIntegration:
    """Integration tests for multiple processors together."""

    def test_recording_and_filtering_combined(self):
        """Test using RecordingProcessor with filtering logic."""
        # This tests the interaction between different processor patterns
        recording_processor = RecordingProcessor()
        logger = Mock()

        events = [
            {"level": "INFO", "message": "info1"},
            {"level": "ERROR", "message": "error1"},
            {"level": "INFO", "message": "info2"},
        ]

        for event in events:
            recording_processor.process(logger, "log", event)

        # Check that all events were recorded
        assert len(recording_processor.recorded_events) == 3

        # Get only INFO events
        info_events = recording_processor.get_events(level="INFO")
        assert len(info_events) == 2

        # Check stats
        stats = recording_processor.get_stats()
        assert stats["level_counts"]["INFO"] == 2  # type: ignore[index]
        assert stats["level_counts"]["ERROR"] == 1  # type: ignore[index]

    def test_slow_and_transform_combined(self):
        """Test processor patterns that modify event timing and content."""

        def add_timestamp(event: Dict[str, Any]) -> Dict[str, Any]:
            result = event.copy()
            result["processed_timestamp"] = time.time()
            return result

        transform_processor = TransformProcessor(transform_func=add_timestamp)
        slow_processor = SlowProcessor(delay_ms=5)
        logger = Mock()

        event = {"level": "INFO", "message": "test"}

        # Process with transform first
        transformed = transform_processor.process(logger, "log", event)
        assert "processed_timestamp" in transformed

        # Then process with slow processor
        result = slow_processor.process(logger, "log", transformed)
        assert "processed_timestamp" in result
        assert "_processing_delay_ms" in result
        assert result["_processing_delay_ms"] == 5
