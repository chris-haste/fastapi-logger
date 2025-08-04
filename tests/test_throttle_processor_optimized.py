"""Comprehensive tests for optimized ThrottleProcessor functionality.

This module tests the core throttling functionality, O(1) cache operations,
and validates the performance improvements achieved in Issue #118.
"""

import asyncio
from unittest.mock import AsyncMock

import pytest

from fapilog.exceptions import ProcessorConfigurationError
from fapilog.processors.throttling import ThrottleProcessor


@pytest.mark.asyncio
class TestThrottleProcessorCore:
    """Test core throttling functionality with optimized implementation."""

    @pytest.fixture
    def processor(self):
        """Create processor for core functionality testing."""
        return ThrottleProcessor(
            max_rate=5,
            window_seconds=60,
            key_field="source",
            strategy="drop",
            max_cache_size=100,
        )

    async def test_basic_throttling(self, processor):
        """Test basic rate limiting functionality."""
        await processor.start()

        # Create events with same source
        events = [{"source": "test_source", "message": f"event_{i}"} for i in range(10)]

        results = []
        for event in events:
            result = await processor.process_async(None, "info", event)
            results.append(result)

        # Should allow max_rate events (5), drop the rest
        allowed_count = sum(1 for r in results if r is not None)
        assert allowed_count == processor.max_rate

        # Verify cache stats
        stats = await processor.get_cache_stats()
        assert stats["tracked_keys"] == 1
        assert stats["cache_utilization"] > 0

        await processor.stop()

    async def test_different_sources_not_throttled(self, processor):
        """Test that different sources are not throttled together."""
        await processor.start()

        events = [{"source": f"source_{i}", "message": f"event_{i}"} for i in range(20)]

        results = []
        for event in events:
            result = await processor.process_async(None, "info", event)
            results.append(result)

        # All events should be allowed (different sources)
        allowed_count = sum(1 for r in results if r is not None)
        assert allowed_count == 20

        # Verify multiple keys are tracked
        stats = await processor.get_cache_stats()
        assert stats["tracked_keys"] == 20

        await processor.stop()

    async def test_window_expiration(self, processor):
        """Test that events expire after the time window."""
        # Use shorter window for testing
        short_processor = ThrottleProcessor(
            max_rate=2,
            window_seconds=2,  # 2 second window
            key_field="source",
        )
        await short_processor.start()

        # Fill up the rate limit
        for i in range(2):
            event = {"source": "test", "message": f"event_{i}"}
            result = await short_processor.process_async(None, "info", event)
            assert result is not None

        # Next event should be throttled
        event = {"source": "test", "message": "throttled_event"}
        result = await short_processor.process_async(None, "info", event)
        assert result is None

        # Wait for window to expire
        await asyncio.sleep(2.1)

        # Now events should be allowed again
        event = {"source": "test", "message": "new_event"}
        result = await short_processor.process_async(None, "info", event)
        assert result is not None

        await short_processor.stop()

    async def test_sample_strategy(self):
        """Test sample throttling strategy."""
        processor = ThrottleProcessor(
            max_rate=2,
            window_seconds=60,
            strategy="sample",
        )
        await processor.start()

        # Fill up rate limit
        for i in range(2):
            event = {"source": "test", "message": f"event_{i}"}
            result = await processor.process_async(None, "info", event)
            assert result is not None

        # Generate many throttled events - some should pass through sampling
        sample_results = []
        for i in range(100):
            event = {"source": "test", "message": f"sample_{i}"}
            result = await processor.process_async(None, "info", event)
            sample_results.append(result is not None)

        # At least some events should pass through (probabilistic test)
        passed_count = sum(sample_results)
        assert passed_count > 0, "Sample strategy should allow some events through"
        assert passed_count < 100, "Sample strategy should not allow all events"

        await processor.stop()

    async def test_custom_key_field(self):
        """Test custom key field for throttling."""
        processor = ThrottleProcessor(
            max_rate=3,
            window_seconds=60,
            key_field="user_id",
        )
        await processor.start()

        # Events with same user_id should be throttled together
        events = [{"user_id": "user123", "message": f"event_{i}"} for i in range(5)]

        results = []
        for event in events:
            result = await processor.process_async(None, "info", event)
            results.append(result)

        allowed_count = sum(1 for r in results if r is not None)
        assert allowed_count == 3  # max_rate

        await processor.stop()

    async def test_missing_key_field_uses_default(self, processor):
        """Test that missing key field uses default value."""
        await processor.start()

        # Events without source field should use "default" key
        events = [{"message": f"event_{i}"} for i in range(10)]

        results = []
        for event in events:
            result = await processor.process_async(None, "info", event)
            results.append(result)

        allowed_count = sum(1 for r in results if r is not None)
        assert allowed_count == processor.max_rate

        # Should have one key tracked (default)
        stats = await processor.get_cache_stats()
        assert stats["tracked_keys"] == 1

        await processor.stop()

    async def test_error_handling_graceful_degradation(self, processor):
        """Test graceful degradation when errors occur."""
        await processor.start()

        # Mock the cache to raise an exception
        original_get = processor._rate_cache.get
        processor._rate_cache.get = AsyncMock(side_effect=Exception("Cache error"))

        event = {"source": "test", "message": "error_event"}
        result = await processor.process_async(None, "info", event)

        # Should return event (graceful degradation)
        assert result is not None
        assert result == event

        # Restore original method
        processor._rate_cache.get = original_get

        await processor.stop()

    async def test_sync_process_method(self, processor):
        """Test sync process method delegation."""
        await processor.start()

        event = {"source": "test", "message": "sync_event"}
        result = processor.process(None, "info", event)

        # Sync method should return event (non-blocking behavior)
        assert result is not None

        await processor.stop()


@pytest.mark.asyncio
class TestThrottleProcessorConfiguration:
    """Test configuration validation for ThrottleProcessor."""

    def test_invalid_max_rate(self):
        """Test invalid max_rate configuration."""
        with pytest.raises(ProcessorConfigurationError):
            ThrottleProcessor(max_rate=0)

        with pytest.raises(ProcessorConfigurationError):
            ThrottleProcessor(max_rate=-1)

        with pytest.raises(ProcessorConfigurationError):
            ThrottleProcessor(max_rate="invalid")

    def test_invalid_window_seconds(self):
        """Test invalid window_seconds configuration."""
        with pytest.raises(ProcessorConfigurationError):
            ThrottleProcessor(window_seconds=0)

        with pytest.raises(ProcessorConfigurationError):
            ThrottleProcessor(window_seconds=-1)

        with pytest.raises(ProcessorConfigurationError):
            ThrottleProcessor(window_seconds="invalid")

    def test_invalid_key_field(self):
        """Test invalid key_field configuration."""
        with pytest.raises(ProcessorConfigurationError):
            ThrottleProcessor(key_field="")

        with pytest.raises(ProcessorConfigurationError):
            ThrottleProcessor(key_field="   ")

        with pytest.raises(ProcessorConfigurationError):
            ThrottleProcessor(key_field=123)

    def test_invalid_strategy(self):
        """Test invalid strategy configuration."""
        with pytest.raises(ProcessorConfigurationError):
            ThrottleProcessor(strategy="invalid")

        with pytest.raises(ProcessorConfigurationError):
            ThrottleProcessor(strategy="")

    def test_invalid_max_cache_size(self):
        """Test invalid max_cache_size configuration."""
        with pytest.raises(ProcessorConfigurationError):
            ThrottleProcessor(max_cache_size=0)

        with pytest.raises(ProcessorConfigurationError):
            ThrottleProcessor(max_cache_size=-1)

    def test_valid_configuration(self):
        """Test valid configuration acceptance."""
        # Should not raise any exceptions
        processor = ThrottleProcessor(
            max_rate=100,
            window_seconds=60,
            key_field="source",
            strategy="drop",
            max_cache_size=1000,
        )
        assert processor.max_rate == 100
        assert processor.window_seconds == 60
        assert processor.key_field == "source"
        assert processor.strategy == "drop"
        assert processor.max_cache_size == 1000


@pytest.mark.asyncio
class TestThrottleProcessorCacheOperations:
    """Test O(1) cache operations and LRU behavior."""

    @pytest.fixture
    def small_cache_processor(self):
        """Create processor with small cache for LRU testing."""
        return ThrottleProcessor(
            max_rate=10,
            window_seconds=60,
            max_cache_size=5,  # Small cache for LRU testing
        )

    async def test_lru_eviction_behavior(self, small_cache_processor):
        """Test LRU eviction when cache is full."""
        processor = small_cache_processor
        await processor.start()

        # Fill cache to capacity
        for i in range(5):
            event = {"source": f"source_{i}", "message": f"event_{i}"}
            await processor.process_async(None, "info", event)

        stats = await processor.get_cache_stats()
        assert stats["tracked_keys"] == 5

        # Add one more key - should trigger LRU eviction
        event = {"source": "source_new", "message": "new_event"}
        await processor.process_async(None, "info", event)

        # Should still have max_cache_size keys due to LRU eviction
        stats = await processor.get_cache_stats()
        assert stats["tracked_keys"] <= 5

        await processor.stop()

    async def test_cache_statistics(self, small_cache_processor):
        """Test cache statistics reporting."""
        processor = small_cache_processor
        await processor.start()

        # Add some events
        for i in range(3):
            event = {"source": f"source_{i}", "message": f"event_{i}"}
            await processor.process_async(None, "info", event)

        stats = await processor.get_cache_stats()

        # Check all expected stats are present
        required_stats = [
            "tracked_keys",
            "max_cache_size",
            "cache_utilization",
            "cache_hit_ratio",
            "cache_evictions",
            "total_events_tracked",
            "window_seconds",
            "max_rate",
            "cleanup_interval",
            "average_events_per_key",
        ]

        for stat in required_stats:
            assert stat in stats

        assert stats["tracked_keys"] == 3
        assert stats["max_cache_size"] == 5
        assert 0 <= stats["cache_utilization"] <= 1
        assert 0 <= stats["cache_hit_ratio"] <= 1

        await processor.stop()

    async def test_current_rates_reporting(self, small_cache_processor):
        """Test current rates reporting functionality."""
        processor = small_cache_processor
        await processor.start()

        # Add events for different sources
        for i in range(3):
            for j in range(2):  # 2 events per source
                event = {"source": f"source_{i}", "message": f"event_{j}"}
                await processor.process_async(None, "info", event)

        rates = await processor.get_current_rates()

        # Should have rates for all 3 sources
        assert len(rates) == 3
        for source, rate in rates.items():
            assert source.startswith("source_")
            assert rate == 2  # 2 events per source

        await processor.stop()

    async def test_background_cleanup_scheduling(self, small_cache_processor):
        """Test background cleanup scheduling."""
        processor = small_cache_processor
        await processor.start()

        # Fill cache to trigger cleanup threshold
        for i in range(4):  # 80% of cache size (5)
            event = {"source": f"source_{i}", "message": f"event_{i}"}
            await processor.process_async(None, "info", event)

        # One more event should trigger cleanup scheduling
        event = {"source": "trigger_cleanup", "message": "cleanup_event"}
        await processor.process_async(None, "info", event)

        # Give cleanup a moment to run
        await asyncio.sleep(0.1)

        # Should still be functional
        stats = await processor.get_cache_stats()
        assert stats["tracked_keys"] > 0

        await processor.stop()


@pytest.mark.asyncio
class TestThrottleProcessorStartStop:
    """Test processor lifecycle management."""

    async def test_start_stop_lifecycle(self):
        """Test start and stop lifecycle."""
        processor = ThrottleProcessor(max_rate=10, window_seconds=60)

        # Start processor
        await processor.start()
        assert processor._last_cleanup > 0

        # Process an event
        event = {"source": "test", "message": "test_event"}
        result = await processor.process_async(None, "info", event)
        assert result is not None

        # Stop processor
        await processor.stop()

        # Should still be able to process (graceful degradation)
        result = await processor.process_async(None, "info", event)
        assert result is not None

    async def test_multiple_start_stop_cycles(self):
        """Test multiple start/stop cycles."""
        processor = ThrottleProcessor(max_rate=10, window_seconds=60)

        for _ in range(3):
            await processor.start()
            event = {"source": "test", "message": "cycle_event"}
            result = await processor.process_async(None, "info", event)
            assert result is not None
            await processor.stop()

        # Final verification
        stats = await processor.get_cache_stats()
        assert isinstance(stats, dict)
