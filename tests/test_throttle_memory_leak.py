"""Tests for ThrottleProcessor memory leak fixes and memory management."""

import asyncio
import time
from typing import Any, Dict
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from fapilog._internal.processors import ThrottleProcessor
from fapilog.exceptions import ProcessorConfigurationError


class TestThrottleProcessorMemoryManagement:
    """Test memory management features of ThrottleProcessor."""

    @pytest.fixture
    def processor_config(self) -> Dict[str, Any]:
        """Basic processor configuration for testing."""
        return {
            "max_rate": 5,
            "window_seconds": 10,
            "key_field": "source",
            "cleanup_interval": 1,  # Fast cleanup for testing
            "max_cache_size": 10,
        }

    @pytest_asyncio.fixture
    async def processor(self, processor_config: Dict[str, Any]) -> ThrottleProcessor:
        """Create and start a processor for testing."""
        proc = ThrottleProcessor(**processor_config)
        await proc.start()
        yield proc
        await proc.stop()

    @pytest.mark.asyncio
    async def test_background_cleanup_task_starts(
        self, processor_config: Dict[str, Any]
    ) -> None:
        """Test that background cleanup task starts properly."""
        processor = ThrottleProcessor(**processor_config)

        # Task should not exist before start
        assert processor._cleanup_task is None

        await processor.start()

        # Task should be created and running
        assert processor._cleanup_task is not None
        assert not processor._cleanup_task.done()

        await processor.stop()

        # Task should be cleaned up after stop
        assert processor._cleanup_task is None or processor._cleanup_task.cancelled()

    @pytest.mark.asyncio
    async def test_background_cleanup_task_stops_gracefully(
        self, processor_config: Dict[str, Any]
    ) -> None:
        """Test that background cleanup task stops gracefully."""
        processor = ThrottleProcessor(**processor_config)
        await processor.start()

        cleanup_task = processor._cleanup_task
        assert cleanup_task is not None

        await processor.stop()

        # Task should be cancelled or completed
        assert cleanup_task.cancelled() or cleanup_task.done()

    @pytest.mark.asyncio
    async def test_memory_limit_enforcement(self, processor: ThrottleProcessor) -> None:
        """Test that memory limits are enforced with LRU eviction."""
        # Fill cache beyond limit (max_cache_size = 10)

        # Add 15 unique keys to exceed limit
        for i in range(15):
            event_dict = {"source": f"key_{i}", "message": f"test_{i}"}
            processor.process(None, "info", event_dict)
            # Simulate different access times
            time.sleep(0.01)

        # Cache should be limited to max_cache_size
        assert len(processor._rate_tracker) <= processor.max_cache_size

        # Verify LRU tracking is working
        assert len(processor._key_access_times) == len(processor._rate_tracker)

    @pytest.mark.asyncio
    async def test_lru_eviction_removes_oldest_keys(
        self, processor: ThrottleProcessor
    ) -> None:
        """Test that LRU eviction removes the oldest accessed keys."""
        # Add keys with known access times
        keys_added = []
        for i in range(12):  # Exceed max_cache_size of 10
            key = f"key_{i}"
            event_dict = {"source": key, "message": f"test_{i}"}
            processor.process(None, "info", event_dict)
            keys_added.append(key)
            time.sleep(0.01)  # Ensure different timestamps

        # First keys should be evicted (oldest access times)
        remaining_keys = set(processor._rate_tracker.keys())

        # Should have at most max_cache_size keys
        assert len(remaining_keys) <= processor.max_cache_size

        # Newest keys should still be present
        newest_keys = set(keys_added[-processor.max_cache_size :])
        assert newest_keys.issubset(remaining_keys)

    @pytest.mark.asyncio
    async def test_high_cardinality_key_handling(
        self, processor_config: Dict[str, Any]
    ) -> None:
        """Test handling of high cardinality keys (1000+ unique keys)."""
        # Use larger cache for this test
        processor_config["max_cache_size"] = 1500
        processor = ThrottleProcessor(**processor_config)
        await processor.start()

        try:
            # Generate 1000+ unique keys
            for i in range(1200):
                event_dict = {"source": f"high_card_key_{i}", "message": f"test_{i}"}
                result = processor.process(None, "info", event_dict)
                assert result is not None  # Should not be throttled initially

            # Cache should be managed within limits
            assert len(processor._rate_tracker) <= processor.max_cache_size

            # Cache stats should reflect high cardinality handling
            stats = processor.get_cache_stats()
            assert stats["tracked_keys"] <= processor.max_cache_size
            assert stats["cache_utilization"] <= 1.0

        finally:
            await processor.stop()

    @pytest.mark.asyncio
    async def test_cache_cleanup_on_window_expiration(
        self, processor: ThrottleProcessor
    ) -> None:
        """Test that entries are cleaned up when time window expires."""
        # Add some entries
        for i in range(5):
            event_dict = {"source": f"expire_key_{i}", "message": f"test_{i}"}
            processor.process(None, "info", event_dict)

        initial_count = len(processor._rate_tracker)
        assert initial_count == 5

        # Wait for background cleanup to run (cleanup_interval = 1 second)
        await asyncio.sleep(1.5)

        # Simulate time passage beyond window
        future_time = time.time() + processor.window_seconds + 1

        # Manually trigger cleanup with future time
        with processor._lock:
            for key in list(processor._rate_tracker.keys()):
                processor._cleanup_old_entries_for_key(key, future_time)

        # Entries should be cleaned up
        assert len(processor._rate_tracker) == 0

    @pytest.mark.asyncio
    async def test_cache_statistics_accuracy(
        self, processor: ThrottleProcessor
    ) -> None:
        """Test that cache statistics are accurate."""
        # Add known number of events
        for i in range(5):
            for j in range(3):  # 3 events per key
                event_dict = {"source": f"stats_key_{i}", "message": f"test_{i}_{j}"}
                processor.process(None, "info", event_dict)

        # Test the get_cache_stats method thoroughly
        stats = processor.get_cache_stats()

        assert stats["tracked_keys"] == 5
        assert stats["total_events_tracked"] == 15
        assert stats["max_cache_size"] == processor.max_cache_size
        assert stats["cache_utilization"] == 5 / processor.max_cache_size
        assert stats["average_events_per_key"] == 3.0
        assert stats["cleanup_interval"] == processor.cleanup_interval
        assert stats["window_seconds"] == processor.window_seconds

        # Verify all expected keys are present in cache stats
        expected_keys = {
            "tracked_keys",
            "total_events_tracked",
            "max_cache_size",
            "cache_utilization",
            "cleanup_interval",
            "window_seconds",
            "average_events_per_key",
        }
        assert set(stats.keys()) == expected_keys

    @pytest.mark.asyncio
    async def test_memory_cleanup_during_burst_traffic(
        self, processor: ThrottleProcessor
    ) -> None:
        """Test memory management during burst traffic patterns."""
        # Simulate burst traffic with many unique keys
        burst_size = 50

        for burst in range(3):  # 3 bursts
            for i in range(burst_size):
                key = f"burst_{burst}_key_{i}"
                event_dict = {"source": key, "message": f"burst_{burst}_{i}"}
                processor.process(None, "info", event_dict)

            # Memory should be managed within limits
            assert len(processor._rate_tracker) <= processor.max_cache_size

            # Wait a bit between bursts
            await asyncio.sleep(0.1)

    @pytest.mark.asyncio
    async def test_background_cleanup_exception_handling(
        self, processor_config: Dict[str, Any]
    ) -> None:
        """Test that background cleanup handles exceptions gracefully."""
        processor = ThrottleProcessor(**processor_config)

        # Mock the cleanup method to raise an exception
        original_cleanup = processor._cleanup_old_entries
        processor._cleanup_old_entries = AsyncMock(side_effect=Exception("Test error"))

        await processor.start()

        # Wait for cleanup to run and handle exception
        await asyncio.sleep(1.5)

        # Task should still be running despite exception
        assert processor._cleanup_task is not None
        assert not processor._cleanup_task.done()

        # Restore original method and stop
        processor._cleanup_old_entries = original_cleanup
        await processor.stop()

    @pytest.mark.asyncio
    async def test_memory_limit_configuration_validation(self) -> None:
        """Test validation of memory limit configuration parameters."""
        # Test invalid cleanup_interval
        with pytest.raises(ProcessorConfigurationError):
            ThrottleProcessor(cleanup_interval=0)

        with pytest.raises(ProcessorConfigurationError):
            ThrottleProcessor(cleanup_interval=-1)

        # Test invalid max_cache_size
        with pytest.raises(ProcessorConfigurationError):
            ThrottleProcessor(max_cache_size=0)

        with pytest.raises(ProcessorConfigurationError):
            ThrottleProcessor(max_cache_size=-1)

    @pytest.mark.asyncio
    async def test_lru_access_time_tracking(self, processor: ThrottleProcessor) -> None:
        """Test that LRU access times are properly tracked."""
        key1 = "lru_key_1"
        key2 = "lru_key_2"

        # Add first key
        event1 = {"source": key1, "message": "test1"}
        processor.process(None, "info", event1)
        time1 = processor._key_access_times[key1]

        time.sleep(0.01)

        # Add second key
        event2 = {"source": key2, "message": "test2"}
        processor.process(None, "info", event2)
        time2 = processor._key_access_times[key2]

        # Second key should have later access time
        assert time2 > time1

        time.sleep(0.01)

        # Access first key again
        event1_again = {"source": key1, "message": "test1_again"}
        processor.process(None, "info", event1_again)
        time1_updated = processor._key_access_times[key1]

        # First key should now have the latest access time
        assert time1_updated > time2

    @pytest.mark.asyncio
    async def test_concurrent_access_memory_safety(
        self, processor: ThrottleProcessor
    ) -> None:
        """Test memory management under concurrent access."""
        import threading

        def worker(worker_id: int) -> None:
            for i in range(20):
                event_dict = {
                    "source": f"worker_{worker_id}_key_{i}",
                    "message": f"test_{i}",
                }
                processor.process(None, "info", event_dict)

        # Start multiple threads
        threads = []
        for worker_id in range(5):
            thread = threading.Thread(target=worker, args=(worker_id,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Memory should be managed within limits despite concurrent access
        assert len(processor._rate_tracker) <= processor.max_cache_size

        # Cache should be consistent
        stats = processor.get_cache_stats()
        assert stats["tracked_keys"] == len(processor._rate_tracker)

    @pytest.mark.asyncio
    async def test_long_running_memory_stability(
        self, processor_config: Dict[str, Any]
    ) -> None:
        """Test memory stability over extended operation."""
        # Use short cleanup interval for testing (keep as integers)
        processor_config["cleanup_interval"] = 1  # 1 second instead of 0.1
        processor_config["window_seconds"] = 2  # 2 seconds instead of 0.5

        processor = ThrottleProcessor(**processor_config)
        await processor.start()

        try:
            # Run for multiple cleanup cycles
            for cycle in range(3):  # Reduced cycles for faster testing
                # Add events in each cycle
                for i in range(15):
                    key = f"cycle_{cycle}_key_{i}"
                    event_dict = {"source": key, "message": f"test_{cycle}_{i}"}
                    processor.process(None, "info", event_dict)

                # Wait for cleanup
                await asyncio.sleep(0.5)

                # Check memory bounds
                assert len(processor._rate_tracker) <= processor.max_cache_size

                # Simulate old entries expiring
                if cycle > 0:  # After first cycle
                    await asyncio.sleep(2.5)  # Wait for window expiration

                    # Trigger cleanup
                    await processor._cleanup_old_entries()

                    # Some entries should be cleaned up
                    assert len(processor._rate_tracker) <= processor.max_cache_size

        finally:
            await processor.stop()
