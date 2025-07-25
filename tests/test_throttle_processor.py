"""Tests for ThrottleProcessor rate limiting functionality."""

import threading
import time
from unittest.mock import patch

import pytest

from fapilog._internal.processors import ThrottleProcessor
from fapilog.exceptions import ProcessorConfigurationError


class TestThrottleProcessor:
    """Test ThrottleProcessor functionality."""

    def test_throttle_processor_initialization(self):
        """Test ThrottleProcessor initialization with valid parameters."""
        processor = ThrottleProcessor(
            max_rate=50, window_seconds=30, key_field="service", strategy="sample"
        )

        assert processor.max_rate == 50
        assert processor.window_seconds == 30
        assert processor.key_field == "service"
        assert processor.strategy == "sample"
        assert processor._sample_rate == 0.1
        assert isinstance(processor._rate_tracker, dict)
        assert isinstance(processor._lock, threading.Lock)

    def test_throttle_processor_default_values(self):
        """Test ThrottleProcessor with default configuration."""
        processor = ThrottleProcessor()

        assert processor.max_rate == 100
        assert processor.window_seconds == 60
        assert processor.key_field == "source"
        assert processor.strategy == "drop"

    def test_throttle_processor_config_validation(self):
        """Test configuration validation for ThrottleProcessor."""
        # Valid configuration should work
        processor = ThrottleProcessor(
            max_rate=10, window_seconds=30, key_field="test", strategy="drop"
        )
        processor.validate_config()  # Should not raise

        # Invalid max_rate
        with pytest.raises(
            ProcessorConfigurationError, match="max_rate must be a positive integer"
        ):
            ThrottleProcessor(max_rate=0)

        with pytest.raises(
            ProcessorConfigurationError, match="max_rate must be a positive integer"
        ):
            ThrottleProcessor(max_rate=-5)

        with pytest.raises(
            ProcessorConfigurationError, match="max_rate must be a positive integer"
        ):
            ThrottleProcessor(max_rate="not_int")

        # Invalid window_seconds
        with pytest.raises(
            ProcessorConfigurationError,
            match="window_seconds must be a positive integer",
        ):
            ThrottleProcessor(window_seconds=0)

        with pytest.raises(
            ProcessorConfigurationError,
            match="window_seconds must be a positive integer",
        ):
            ThrottleProcessor(window_seconds=-10)

        # Invalid key_field
        with pytest.raises(
            ProcessorConfigurationError, match="key_field must be a non-empty string"
        ):
            ThrottleProcessor(key_field="")

        with pytest.raises(
            ProcessorConfigurationError, match="key_field must be a non-empty string"
        ):
            ThrottleProcessor(key_field="   ")

        # Invalid strategy
        with pytest.raises(
            ProcessorConfigurationError, match="strategy must be 'drop' or 'sample'"
        ):
            ThrottleProcessor(strategy="invalid")

        with pytest.raises(
            ProcessorConfigurationError, match="strategy must be 'drop' or 'sample'"
        ):
            ThrottleProcessor(strategy="delay")

    def test_extract_key_from_event(self):
        """Test key extraction from event dictionaries."""
        processor = ThrottleProcessor(key_field="service_name")

        # Key exists
        event_dict = {
            "level": "INFO",
            "service_name": "payment-service",
            "message": "test",
        }
        key = processor._extract_key(event_dict)
        assert key == "payment-service"

        # Key doesn't exist - should use default
        event_dict = {"level": "INFO", "message": "test"}
        key = processor._extract_key(event_dict)
        assert key == "default"

        # Key value is not string - should convert to string
        event_dict = {"level": "INFO", "service_name": 123, "message": "test"}
        key = processor._extract_key(event_dict)
        assert key == "123"

    def test_rate_limiting_basic_functionality(self):
        """Test basic rate limiting functionality."""
        # Set very low rate limit for testing
        processor = ThrottleProcessor(max_rate=3, window_seconds=60, strategy="drop")

        test_event = {"level": "INFO", "source": "test-service", "message": "test"}

        # First 3 events should pass through
        for _i in range(3):
            result = processor.process(None, "info", test_event)
            assert result is not None
            assert result == test_event

        # 4th event should be throttled (dropped)
        result = processor.process(None, "info", test_event)
        assert result is None

        # 5th event should also be throttled
        result = processor.process(None, "info", test_event)
        assert result is None

    def test_rate_limiting_different_keys(self):
        """Test that rate limiting is applied per key, not globally."""
        processor = ThrottleProcessor(max_rate=2, window_seconds=60, strategy="drop")

        event1 = {"level": "INFO", "source": "service-1", "message": "test"}
        event2 = {"level": "INFO", "source": "service-2", "message": "test"}

        # Each service should have its own rate limit
        for _i in range(2):
            result1 = processor.process(None, "info", event1)
            result2 = processor.process(None, "info", event2)
            assert result1 is not None
            assert result2 is not None

        # Now both should be throttled
        result1 = processor.process(None, "info", event1)
        result2 = processor.process(None, "info", event2)
        assert result1 is None
        assert result2 is None

    def test_drop_strategy(self):
        """Test drop throttling strategy."""
        processor = ThrottleProcessor(max_rate=1, window_seconds=60, strategy="drop")

        test_event = {"level": "INFO", "source": "test", "message": "test"}

        # First event passes
        result = processor.process(None, "info", test_event)
        assert result == test_event

        # Second event is dropped
        result = processor.process(None, "info", test_event)
        assert result is None

    def test_sample_strategy(self):
        """Test sample throttling strategy."""
        processor = ThrottleProcessor(max_rate=1, window_seconds=60, strategy="sample")

        test_event = {"level": "INFO", "source": "test", "message": "test"}

        # First event passes
        result = processor.process(None, "info", test_event)
        assert result == test_event

        # Mock random to control sampling behavior
        with patch("random.random") as mock_random:
            # Sample rate is 0.1, so if random returns 0.05, event should pass
            mock_random.return_value = 0.05
            result = processor.process(None, "info", test_event)
            assert result == test_event

            # If random returns 0.15, event should be dropped
            mock_random.return_value = 0.15
            result = processor.process(None, "info", test_event)
            assert result is None

    def test_time_window_expiration(self):
        """Test that old events expire from the time window."""
        processor = ThrottleProcessor(max_rate=2, window_seconds=1, strategy="drop")

        test_event = {"level": "INFO", "source": "test", "message": "test"}

        # Fill up the rate limit
        for _i in range(2):
            result = processor.process(None, "info", test_event)
            assert result is not None

        # Next event should be throttled
        result = processor.process(None, "info", test_event)
        assert result is None

        # Wait for window to expire
        time.sleep(1.1)

        # Now events should pass again
        result = processor.process(None, "info", test_event)
        assert result is not None

    def test_cleanup_old_entries(self):
        """Test cleanup of old entries to prevent memory leaks."""
        processor = ThrottleProcessor(max_rate=5, window_seconds=1, strategy="drop")

        test_event = {"level": "INFO", "source": "test", "message": "test"}

        # Add some events
        for _i in range(3):
            processor.process(None, "info", test_event)

        # Check that entries exist
        assert "test" in processor._rate_tracker
        assert len(processor._rate_tracker["test"]) == 3

        # Wait for window expiration
        time.sleep(1.1)

        # Process another event to trigger cleanup
        processor.process(None, "info", test_event)

        # Old entries should be cleaned up
        assert len(processor._rate_tracker["test"]) == 1

    def test_thread_safety(self):
        """Test that the processor is thread-safe."""
        processor = ThrottleProcessor(max_rate=100, window_seconds=60, strategy="drop")

        results = []
        errors = []

        def worker(worker_id: int):
            try:
                for i in range(50):
                    event = {
                        "level": "INFO",
                        "source": f"worker-{worker_id}",
                        "message": f"test-{i}",
                    }
                    result = processor.process(None, "info", event)
                    results.append(result is not None)
            except Exception as e:
                errors.append(e)

        # Run multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # No errors should occur
        assert len(errors) == 0

        # All events should pass (under rate limit)
        assert all(results)

        # Each worker should have its own tracking
        assert len(processor._rate_tracker) == 5

    def test_get_current_rates(self):
        """Test getting current rates for all tracked keys."""
        processor = ThrottleProcessor(max_rate=10, window_seconds=60, strategy="drop")

        # Initially no rates
        rates = processor.get_current_rates()
        assert rates == {}

        # Add some events
        for _i in range(3):
            processor.process(
                None,
                "info",
                {"level": "INFO", "source": "service-1", "message": "test"},
            )

        for _i in range(5):
            processor.process(
                None,
                "info",
                {"level": "INFO", "source": "service-2", "message": "test"},
            )

        # Check rates
        rates = processor.get_current_rates()
        assert rates["service-1"] == 3
        assert rates["service-2"] == 5

    def test_memory_cleanup_empty_keys(self):
        """Test that empty keys are removed to prevent memory leaks."""
        processor = ThrottleProcessor(max_rate=2, window_seconds=1, strategy="drop")

        test_event = {"level": "INFO", "source": "test", "message": "test"}

        # Add events
        processor.process(None, "info", test_event)
        assert "test" in processor._rate_tracker

        # Wait for expiration
        time.sleep(1.1)

        # Process event to trigger cleanup
        current_time = time.time()
        processor._cleanup_old_entries_for_key("test", current_time)

        # Key should be removed since all entries expired
        assert "test" not in processor._rate_tracker

    def test_custom_key_field(self):
        """Test using a custom field as the throttling key."""
        processor = ThrottleProcessor(
            max_rate=2, window_seconds=60, key_field="request_id", strategy="drop"
        )

        event1 = {"level": "INFO", "request_id": "req-123", "message": "test"}
        event2 = {"level": "INFO", "request_id": "req-456", "message": "test"}
        event3 = {
            "level": "INFO",
            "request_id": "req-123",
            "message": "test",
        }  # Same as event1

        # Different request IDs should have separate limits
        result1 = processor.process(None, "info", event1)
        result2 = processor.process(None, "info", event2)
        assert result1 is not None
        assert result2 is not None

        # Same request ID should be limited
        for _i in range(1):  # Already used 1 of 2 allowed
            result = processor.process(None, "info", event3)
            assert result is not None

        # Now should be throttled
        result = processor.process(None, "info", event3)
        assert result is None

    def test_background_cleanup_method(self):
        """Test the background cleanup method."""
        processor = ThrottleProcessor(max_rate=5, window_seconds=1, strategy="drop")

        # Add events for multiple keys
        for key in ["key1", "key2", "key3"]:
            event = {"level": "INFO", "source": key, "message": "test"}
            processor.process(None, "info", event)

        assert len(processor._rate_tracker) == 3

        # Wait for expiration
        time.sleep(1.1)

        # Run background cleanup
        import asyncio

        asyncio.run(processor._cleanup_old_entries())

        # All keys should be cleaned up since entries expired
        assert len(processor._rate_tracker) == 0


class TestThrottleProcessorIntegration:
    """Test ThrottleProcessor integration scenarios."""

    def test_processor_with_real_log_structure(self):
        """Test processor with realistic log event structure."""
        processor = ThrottleProcessor(
            max_rate=3, window_seconds=60, key_field="service", strategy="drop"
        )

        log_event = {
            "event": "User login failed",
            "level": "ERROR",
            "timestamp": "2023-01-01T00:00:00Z",
            "service": "auth-service",
            "user_id": "user123",
            "ip_address": "192.168.1.1",
            "error_code": "INVALID_CREDENTIALS",
        }

        # Should work with real log structure
        for _i in range(3):
            result = processor.process(None, "error", log_event)
            assert result == log_event

        # Fourth should be throttled
        result = processor.process(None, "error", log_event)
        assert result is None

    def test_processor_registration(self):
        """Test that ThrottleProcessor is properly registered."""
        # Import processors module first to ensure registration happens
        import fapilog._internal.processors  # noqa: F401
        from fapilog._internal.processor_registry import ProcessorRegistry

        # Ensure ThrottleProcessor is registered (in case other tests cleared it)
        ProcessorRegistry.register("throttle", ThrottleProcessor)

        # Should be registered as "throttle"
        registered_class = ProcessorRegistry.get("throttle")
        assert registered_class is ThrottleProcessor
