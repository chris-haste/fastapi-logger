"""Comprehensive tests for processor template to improve coverage."""

import asyncio
from unittest.mock import Mock, patch

import pytest

from fapilog._internal.templates.processor_template import (
    TemplateProcessor,
    TestTemplateProcessor,
)
from fapilog.exceptions import ProcessorConfigurationError


class TestTemplateProcessorInit:
    """Test TemplateProcessor initialization and configuration."""

    def test_init_default_parameters(self):
        """Test initialization with default parameters."""
        processor = TemplateProcessor()

        assert processor.max_events_per_key == 100
        assert processor.window_seconds == 60
        assert processor.key_field == "source"
        assert processor._processed_count == 0
        assert processor._dropped_count == 0
        assert processor._error_count == 0

    def test_init_custom_parameters(self):
        """Test initialization with custom parameters."""
        processor = TemplateProcessor(
            max_events_per_key=50,
            window_seconds=30,
            key_field="user_id",
            custom_config="test",
        )

        assert processor.max_events_per_key == 50
        assert processor.window_seconds == 30
        assert processor.key_field == "user_id"

    def test_validate_config_valid(self):
        """Test configuration validation with valid parameters."""
        processor = TemplateProcessor(
            max_events_per_key=100,
            window_seconds=60,
            key_field="source",
        )
        # Should not raise any exception
        processor.validate_config()

    def test_validate_config_invalid_max_events_negative(self):
        """Test configuration validation with negative max_events_per_key."""
        processor = TemplateProcessor()
        processor.max_events_per_key = -1

        with pytest.raises(
            ProcessorConfigurationError,
            match="max_events_per_key must be a positive integer",
        ):
            processor.validate_config()

    def test_validate_config_invalid_max_events_zero(self):
        """Test configuration validation with zero max_events_per_key."""
        processor = TemplateProcessor()
        processor.max_events_per_key = 0

        with pytest.raises(
            ProcessorConfigurationError,
            match="max_events_per_key must be a positive integer",
        ):
            processor.validate_config()

    def test_validate_config_invalid_max_events_type(self):
        """Test configuration validation with invalid max_events_per_key type."""
        processor = TemplateProcessor()
        processor.max_events_per_key = "invalid"

        with pytest.raises(
            ProcessorConfigurationError,
            match="max_events_per_key must be a positive integer",
        ):
            processor.validate_config()

    def test_validate_config_invalid_window_seconds_negative(self):
        """Test configuration validation with negative window_seconds."""
        processor = TemplateProcessor()
        processor.window_seconds = -1

        with pytest.raises(
            ProcessorConfigurationError,
            match="window_seconds must be a positive integer",
        ):
            processor.validate_config()

    def test_validate_config_invalid_window_seconds_zero(self):
        """Test configuration validation with zero window_seconds."""
        processor = TemplateProcessor()
        processor.window_seconds = 0

        with pytest.raises(
            ProcessorConfigurationError,
            match="window_seconds must be a positive integer",
        ):
            processor.validate_config()

    def test_validate_config_invalid_window_seconds_type(self):
        """Test configuration validation with invalid window_seconds type."""
        processor = TemplateProcessor()
        processor.window_seconds = "invalid"

        with pytest.raises(
            ProcessorConfigurationError,
            match="window_seconds must be a positive integer",
        ):
            processor.validate_config()

    def test_validate_config_invalid_key_field_empty(self):
        """Test configuration validation with empty key_field."""
        processor = TemplateProcessor()
        processor.key_field = ""

        with pytest.raises(
            ProcessorConfigurationError, match="key_field must be a non-empty string"
        ):
            processor.validate_config()

    def test_validate_config_invalid_key_field_whitespace(self):
        """Test configuration validation with whitespace-only key_field."""
        processor = TemplateProcessor()
        processor.key_field = "   "

        with pytest.raises(
            ProcessorConfigurationError, match="key_field must be a non-empty string"
        ):
            processor.validate_config()

    def test_validate_config_invalid_key_field_type(self):
        """Test configuration validation with invalid key_field type."""
        processor = TemplateProcessor()
        processor.key_field = 123

        with pytest.raises(
            ProcessorConfigurationError, match="key_field must be a non-empty string"
        ):
            processor.validate_config()


class TestTemplateProcessorSync:
    """Test TemplateProcessor sync processing methods."""

    def test_process_no_event_loop(self):
        """Test process method when no event loop exists."""
        processor = TemplateProcessor()
        event_dict = {"source": "test", "message": "test_message"}

        # Mock RuntimeError when getting event loop
        with patch("asyncio.get_event_loop", side_effect=RuntimeError("No event loop")):
            with patch("asyncio.run") as mock_run:
                mock_run.return_value = event_dict

                result = processor.process(Mock(), "info", event_dict)

                mock_run.assert_called_once()
                assert result == event_dict

    def test_process_event_loop_not_running(self):
        """Test process method when event loop exists but not running."""
        processor = TemplateProcessor()
        event_dict = {"source": "test", "message": "test_message"}

        # Mock event loop that exists but is not running
        mock_loop = Mock()
        mock_loop.is_running.return_value = False

        with patch("asyncio.get_event_loop", return_value=mock_loop):
            with patch("asyncio.run") as mock_run:
                mock_run.return_value = event_dict

                result = processor.process(Mock(), "info", event_dict)

                mock_run.assert_called_once()
                assert result == event_dict

    def test_process_event_loop_running(self):
        """Test process method when event loop is running."""
        processor = TemplateProcessor()
        event_dict = {"source": "test", "message": "test_message"}

        # Mock running event loop
        mock_loop = Mock()
        mock_loop.is_running.return_value = True
        mock_task = Mock()

        with patch("asyncio.get_event_loop", return_value=mock_loop):
            with patch(
                "asyncio.create_task", return_value=mock_task
            ) as mock_create_task:
                result = processor.process(Mock(), "info", event_dict)

                mock_create_task.assert_called_once()
                # When running async, should return event_dict for sync compatibility
                assert result == event_dict


class TestTemplateProcessorAsync:
    """Test TemplateProcessor async processing methods."""

    @pytest.mark.asyncio
    async def test_process_async_success(self):
        """Test successful async event processing."""
        processor = TemplateProcessor(max_events_per_key=5, window_seconds=60)
        await processor.start()

        event_dict = {"source": "test_source", "message": "test_message"}
        result = await processor.process_async(Mock(), "info", event_dict)

        assert result == event_dict
        assert processor._processed_count == 1

        await processor.stop()

    @pytest.mark.asyncio
    async def test_process_async_invalid_event(self):
        """Test async processing with invalid event."""
        processor = TemplateProcessor()
        await processor.start()

        # Test with None event
        result = await processor.process_async(Mock(), "info", None)
        assert result is None

        # Test with non-dict event
        result = await processor.process_async(Mock(), "info", "invalid")
        assert result == "invalid"

        await processor.stop()

    @pytest.mark.asyncio
    async def test_process_async_key_extraction_failure(self):
        """Test async processing when key extraction fails."""
        processor = TemplateProcessor(key_field="missing_field")
        await processor.start()

        # Mock _extract_key to return None
        with patch.object(processor, "_extract_key", return_value=None):
            event_dict = {"source": "test", "message": "test"}
            result = await processor.process_async(Mock(), "info", event_dict)
            assert result == event_dict

        await processor.stop()

    @pytest.mark.asyncio
    async def test_process_async_processing_failure(self):
        """Test async processing when event processing fails."""
        processor = TemplateProcessor()
        await processor.start()

        # Mock _process_event to return None (drop event)
        with patch.object(processor, "_process_event", return_value=None):
            event_dict = {"source": "test", "message": "test"}
            result = await processor.process_async(Mock(), "info", event_dict)
            assert result is None

        await processor.stop()

    @pytest.mark.asyncio
    async def test_process_async_exception_handling(self):
        """Test async processing exception handling."""
        processor = TemplateProcessor()
        await processor.start()

        # Mock _validate_event to raise exception
        with patch.object(
            processor, "_validate_event", side_effect=RuntimeError("Test error")
        ):
            event_dict = {"source": "test", "message": "test"}
            result = await processor.process_async(Mock(), "info", event_dict)
            # Should return original event on error
            assert result == event_dict

        await processor.stop()

    @pytest.mark.asyncio
    async def test_validate_event_valid(self):
        """Test event validation with valid events."""
        processor = TemplateProcessor()

        # Valid dict event
        assert processor._validate_event({"key": "value"}) is True

        # Empty dict is still valid
        assert processor._validate_event({}) is True

    @pytest.mark.asyncio
    async def test_validate_event_invalid(self):
        """Test event validation with invalid events."""
        processor = TemplateProcessor()

        # None event
        assert processor._validate_event(None) is False

        # Non-dict event
        assert processor._validate_event("string") is False
        assert processor._validate_event(123) is False
        assert processor._validate_event([]) is False

    @pytest.mark.asyncio
    async def test_extract_key_success(self):
        """Test successful key extraction."""
        processor = TemplateProcessor(key_field="user_id")

        # Key exists
        event = {"user_id": "123", "message": "test"}
        key = await processor._extract_key(event)
        assert key == "123"

        # Key missing, should return "default"
        event = {"message": "test"}
        key = await processor._extract_key(event)
        assert key == "default"

    @pytest.mark.asyncio
    async def test_extract_key_conversion(self):
        """Test key extraction with type conversion."""
        processor = TemplateProcessor(key_field="number")

        # Number key should be converted to string
        event = {"number": 456, "message": "test"}
        key = await processor._extract_key(event)
        assert key == "456"

    @pytest.mark.asyncio
    async def test_extract_key_exception(self):
        """Test key extraction exception handling."""
        processor = TemplateProcessor(key_field="problematic")

        # Mock event that causes str() to fail
        event = {"problematic": Mock()}
        event["problematic"].__str__ = Mock(
            side_effect=RuntimeError("String conversion failed")
        )

        with patch(
            "fapilog._internal.templates.processor_template.logger"
        ) as mock_logger:
            key = await processor._extract_key(event)
            assert key is None
            mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_event_rate_limiting(self):
        """Test event processing with rate limiting."""
        processor = TemplateProcessor(max_events_per_key=2, window_seconds=60)
        await processor.start()

        key = "test_user"
        event_dict = {"source": key, "message": "test"}

        # First two events should be processed
        result1 = await processor._process_event(key, event_dict)
        assert result1 == event_dict
        assert processor._processed_count == 1

        result2 = await processor._process_event(key, event_dict)
        assert result2 == event_dict
        assert processor._processed_count == 2

        # Third event should be dropped
        result3 = await processor._process_event(key, event_dict)
        assert result3 is None
        assert processor._dropped_count == 1

        await processor.stop()

    @pytest.mark.asyncio
    async def test_process_event_window_expiry(self):
        """Test event processing with window expiry."""
        processor = TemplateProcessor(max_events_per_key=2, window_seconds=1)
        await processor.start()

        key = "test_user"
        event_dict = {"source": key, "message": "test"}

        # Fill up the rate limit
        await processor._process_event(key, event_dict)
        await processor._process_event(key, event_dict)

        # Should be rate limited now
        result = await processor._process_event(key, event_dict)
        assert result is None

        # Wait for window to expire
        await asyncio.sleep(1.1)

        # Should be able to process again
        result = await processor._process_event(key, event_dict)
        assert result == event_dict

        await processor.stop()

    @pytest.mark.asyncio
    async def test_update_metrics(self):
        """Test metrics update method."""
        processor = TemplateProcessor()
        await processor.start()

        # Method should execute without error
        await processor._update_metrics()

        await processor.stop()

    @pytest.mark.asyncio
    async def test_safe_operation_async_function(self):
        """Test safe operation with async function."""
        processor = TemplateProcessor()

        async def async_func(x, y):
            return x + y

        result = await processor._safe_operation(async_func, 1, 2)
        assert result == 3

    @pytest.mark.asyncio
    async def test_safe_operation_sync_function(self):
        """Test safe operation with sync function."""
        processor = TemplateProcessor()

        def sync_func(x, y):
            return x * y

        result = await processor._safe_operation(sync_func, 3, 4)
        assert result == 12

    @pytest.mark.asyncio
    async def test_safe_operation_exception(self):
        """Test safe operation exception handling."""
        processor = TemplateProcessor()

        def failing_func():
            raise RuntimeError("Test error")

        with patch(
            "fapilog._internal.templates.processor_template.logger"
        ) as mock_logger:
            result = await processor._safe_operation(failing_func)
            assert result is None
            assert processor._error_count == 1
            mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_impl(self):
        """Test processor start implementation."""
        processor = TemplateProcessor()

        with patch(
            "fapilog._internal.templates.processor_template.logger"
        ) as mock_logger:
            await processor._start_impl()
            mock_logger.info.assert_called_with("TemplateProcessor started")

    @pytest.mark.asyncio
    async def test_stop_impl(self):
        """Test processor stop implementation."""
        processor = TemplateProcessor()

        with patch(
            "fapilog._internal.templates.processor_template.logger"
        ) as mock_logger:
            await processor._stop_impl()
            mock_logger.info.assert_called_with("TemplateProcessor stopped")

    def test_get_metrics(self):
        """Test metrics collection."""
        processor = TemplateProcessor(
            max_events_per_key=50, window_seconds=30, key_field="user"
        )
        processor._processed_count = 10
        processor._dropped_count = 5
        processor._error_count = 2

        metrics = processor.get_metrics()

        assert metrics["processed_count"] == 10
        assert metrics["dropped_count"] == 5
        assert metrics["error_count"] == 2
        assert metrics["max_events_per_key"] == 50
        assert metrics["window_seconds"] == 30
        assert metrics["key_field"] == "user"

    def test_get_metrics_with_base_metrics(self):
        """Test metrics collection when base class has metrics."""
        processor = TemplateProcessor()

        # Mock super().get_metrics() to return some base metrics
        with patch.object(
            processor.__class__.__bases__[0],
            "get_metrics",
            return_value={"base_metric": "value"},
        ):
            metrics = processor.get_metrics()
            assert "base_metric" in metrics
            assert "processed_count" in metrics


class TestTemplateProcessorConcurrency:
    """Test TemplateProcessor concurrent access patterns."""

    @pytest.mark.asyncio
    async def test_concurrent_processing(self):
        """Test concurrent event processing."""
        processor = TemplateProcessor(max_events_per_key=100, window_seconds=60)
        await processor.start()

        async def process_events(worker_id):
            results = []
            for i in range(10):
                event = {"source": f"worker_{worker_id}", "message": f"msg_{i}"}
                result = await processor.process_async(Mock(), "info", event)
                results.append(result)
            return results

        # Run 5 concurrent workers
        tasks = [process_events(i) for i in range(5)]
        all_results = await asyncio.gather(*tasks)

        # All events should be processed (not rate limited)
        for worker_results in all_results:
            for result in worker_results:
                assert result is not None

        # Should have processed 50 events total
        assert processor._processed_count == 50

        await processor.stop()

    @pytest.mark.asyncio
    async def test_concurrent_rate_limiting(self):
        """Test concurrent processing with rate limiting."""
        processor = TemplateProcessor(max_events_per_key=5, window_seconds=60)
        await processor.start()

        async def process_same_key_events(worker_id):
            results = []
            for i in range(10):
                # All workers use same key to trigger rate limiting
                event = {
                    "source": "shared_key",
                    "message": f"worker_{worker_id}_msg_{i}",
                }
                result = await processor.process_async(Mock(), "info", event)
                results.append(result)
            return results

        # Run concurrent workers with same key
        tasks = [process_same_key_events(i) for i in range(3)]
        all_results = await asyncio.gather(*tasks)

        # Count processed and dropped events
        processed_count = 0
        dropped_count = 0
        for worker_results in all_results:
            for result in worker_results:
                if result is not None:
                    processed_count += 1
                else:
                    dropped_count += 1

        # Should have processed 5 events and dropped the rest
        assert processed_count == 5
        assert dropped_count == 25
        assert processor._processed_count == 5
        assert processor._dropped_count == 25

        await processor.stop()


class TestTestTemplateProcessor:
    """Test the TestTemplateProcessor example class itself."""

    def test_create_processor_default(self):
        """Test creating processor with default config."""
        test_class = TestTemplateProcessor()
        processor = test_class.create_processor()

        assert isinstance(processor, TemplateProcessor)
        assert processor.max_events_per_key == 100
        assert processor.window_seconds == 60

    def test_create_processor_custom_config(self):
        """Test creating processor with custom config."""
        test_class = TestTemplateProcessor()
        processor = test_class.create_processor(
            max_events_per_key=50, window_seconds=30, key_field="custom_field"
        )

        assert isinstance(processor, TemplateProcessor)
        assert processor.max_events_per_key == 50
        assert processor.window_seconds == 30
        assert processor.key_field == "custom_field"

    @pytest.mark.asyncio
    async def test_basic_processing(self):
        """Test the basic processing example."""
        test_class = TestTemplateProcessor()
        processor = test_class.create_processor()
        await processor.start()

        try:
            await test_class.example_basic_processing(processor)
        finally:
            await processor.stop()

    @pytest.mark.asyncio
    async def test_rate_limiting_example(self):
        """Test the rate limiting example."""
        test_class = TestTemplateProcessor()
        processor = test_class.create_processor(max_events_per_key=50)
        await processor.start()

        try:
            await test_class.example_rate_limiting(processor)
        finally:
            await processor.stop()

    @pytest.mark.asyncio
    async def test_concurrent_access_example(self):
        """Test the concurrent access example."""
        test_class = TestTemplateProcessor()
        processor = test_class.create_processor()
        await processor.start()

        try:
            await test_class.example_concurrent_access(processor)
        finally:
            await processor.stop()


class TestTemplateProcessorIntegration:
    """Integration tests for TemplateProcessor."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        """Test complete processor lifecycle."""
        processor = TemplateProcessor(max_events_per_key=10, window_seconds=60)

        # Start processor
        await processor.start()

        # Process various events
        events = [
            {"source": "user1", "message": "msg1"},
            {"source": "user2", "message": "msg2"},
            {"source": "user1", "message": "msg3"},
            {"source": "user3", "message": "msg4"},
            {"source": "user1", "message": "msg5"},
        ]

        results = []
        for event in events:
            result = await processor.process_async(Mock(), "info", event)
            results.append(result)

        # All events should be processed (under rate limit)
        assert all(result is not None for result in results)
        assert processor._processed_count == 5

        # Check metrics
        metrics = processor.get_metrics()
        assert metrics["processed_count"] == 5
        assert metrics["dropped_count"] == 0
        assert metrics["error_count"] == 0

        # Stop processor
        await processor.stop()

    @pytest.mark.asyncio
    async def test_stress_test(self):
        """Stress test with many events."""
        processor = TemplateProcessor(max_events_per_key=100, window_seconds=60)
        await processor.start()

        # Process many events with different keys
        tasks = []
        for user_id in range(10):
            for msg_id in range(20):
                event = {"source": f"user_{user_id}", "message": f"msg_{msg_id}"}
                task = processor.process_async(Mock(), "info", event)
                tasks.append(task)

        results = await asyncio.gather(*tasks)

        # All events should be processed (200 total, 20 per key, under limit)
        assert all(result is not None for result in results)
        assert processor._processed_count == 200

        await processor.stop()
