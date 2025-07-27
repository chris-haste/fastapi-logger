"""Performance and async tests for improved DeduplicationProcessor."""

import asyncio
import threading
import time

import pytest

from fapilog._internal.processors import DeduplicationProcessor


class TestDeduplicationProcessorPerformance:
    """Test async performance and thread safety improvements."""

    def test_minimal_lock_contention(self):
        """Test that lock contention is minimized in hot path."""
        processor = DeduplicationProcessor(
            window_seconds=300, dedupe_fields=["event", "worker_id"]
        )

        # Measure time for processing unique events (no lock contention)
        start_time = time.time()

        # Process many unique events in parallel
        def worker(worker_id: int):
            for i in range(100):
                event = {
                    "event": f"Message {i}",
                    "worker_id": worker_id,
                    "timestamp": time.time(),
                }
                processor.process(None, "info", event)

        threads = []
        for i in range(20):  # 20 threads
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        processing_time = time.time() - start_time

        # Should be fast due to minimal locking
        assert processing_time < 2.0  # Should complete in under 2 seconds
        assert len(processor._event_cache) == 2000  # 20 workers * 100 events

    def test_background_cleanup_non_blocking(self):
        """Test that background cleanup doesn't block event processing."""
        processor = DeduplicationProcessor(
            window_seconds=1,  # Short window for testing
            dedupe_fields=["event"],
            max_cache_size=100,
        )

        # Fill cache with events that will expire
        for i in range(80):  # Fill close to threshold
            event = {"event": f"Old message {i}"}
            processor.process(None, "info", event)

        # Wait for events to expire
        time.sleep(1.1)

        # Process new events and measure time (should trigger cleanup)
        start_time = time.time()
        for i in range(50):
            event = {"event": f"New message {i}"}
            result = processor.process(None, "info", event)
            assert result is not None  # Event should be processed

        processing_time = time.time() - start_time

        # Should be fast even with cleanup happening
        assert processing_time < 0.5  # Should be very fast

    def test_high_throughput_performance(self):
        """Test processing high event throughput."""
        processor = DeduplicationProcessor(
            window_seconds=60, dedupe_fields=["event", "sequence"]
        )

        event_count = 10000
        start_time = time.time()

        # Process many unique events
        for i in range(event_count):
            event = {
                "event": "High throughput test",
                "sequence": i,
                "timestamp": time.time(),
            }
            result = processor.process(None, "info", event)
            assert result is not None

        processing_time = time.time() - start_time
        throughput = event_count / processing_time

        # Should handle 10,000+ events/second
        assert throughput > 5000  # At least 5K events/second (conservative)
        print(f"Throughput: {throughput:.0f} events/second")

    def test_concurrent_duplicate_detection(self):
        """Test duplicate detection under concurrent load."""
        processor = DeduplicationProcessor(window_seconds=60, dedupe_fields=["event"])

        results = []

        def worker():
            # Each worker sends the same event multiple times
            for _ in range(50):
                event = {"event": "Duplicate test message"}
                result = processor.process(None, "info", event)
                results.append(result is not None)

        # Run multiple workers concurrently
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Only the first event should pass, rest should be duplicates
        passed_events = sum(results)
        assert passed_events == 1  # Only one unique event should pass
        assert len(results) == 500  # 10 workers * 50 attempts

    def test_async_compatibility(self):
        """Test async compatibility of the processor."""
        processor = DeduplicationProcessor(
            window_seconds=60, dedupe_fields=["event", "async_id"]
        )

        async def async_worker(worker_id: int):
            results = []
            for i in range(50):
                event = {
                    "event": f"Async message {i}",
                    "async_id": worker_id,
                    "timestamp": time.time(),
                }
                # The processor should handle async context gracefully
                result = processor.process(None, "info", event)
                results.append(result is not None)
            return results

        async def run_async_test():
            tasks = []
            for i in range(5):
                task = asyncio.create_task(async_worker(i))
                tasks.append(task)

            results = await asyncio.gather(*tasks)
            return results

        # Run the async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            all_results = loop.run_until_complete(run_async_test())

            # All async workers should succeed
            for worker_results in all_results:
                assert all(worker_results)  # All events unique per worker

            # Should have entries for all workers
            assert len(processor._event_cache) == 250  # 5 workers * 50 events
        finally:
            loop.close()

    def test_memory_bounded_growth(self):
        """Test that memory usage remains bounded."""
        processor = DeduplicationProcessor(
            window_seconds=60, dedupe_fields=["event"], max_cache_size=1000
        )

        # Process more events than cache limit
        for i in range(1500):
            event = {"event": f"Message {i}"}
            processor.process(None, "info", event)

        # Cache should not exceed max size
        assert len(processor._event_cache) <= 1000

    def test_cache_stats_non_blocking(self):
        """Test that cache stats don't block processing."""
        processor = DeduplicationProcessor(window_seconds=60, dedupe_fields=["event"])

        # Add some events
        for i in range(100):
            event = {"event": f"Stats test {i}"}
            processor.process(None, "info", event)

        # Get stats multiple times concurrently
        def get_stats():
            for _ in range(100):
                stats = processor.cache_stats
                assert "unique_signatures" in stats
                assert "total_events_seen" in stats

        threads = []
        for _ in range(5):
            thread = threading.Thread(target=get_stats)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Should complete without issues

    def test_cleanup_scheduling_intelligence(self):
        """Test intelligent cleanup scheduling."""
        processor = DeduplicationProcessor(
            window_seconds=2,  # Short window
            dedupe_fields=["event"],
            max_cache_size=100,
        )

        # Fill cache below threshold - no cleanup should be triggered
        for i in range(50):  # Below 80% threshold
            event = {"event": f"Message {i}"}
            processor.process(None, "info", event)

        initial_size = len(processor._event_cache)

        # Wait and process more - should not trigger cleanup yet
        time.sleep(0.5)
        for i in range(10):
            event = {"event": f"More {i}"}
            processor.process(None, "info", event)

        # Cache should still contain expired entries (no cleanup yet)
        assert len(processor._event_cache) >= initial_size

        # Fill above threshold - should trigger cleanup
        for i in range(50):  # Push above 80% threshold
            event = {"event": f"Trigger {i}"}
            processor.process(None, "info", event)

        # Allow some time for potential background cleanup
        time.sleep(0.1)

        # Cache management should be working
        assert len(processor._event_cache) <= 100  # Respects max size


class TestDeduplicationProcessorAsyncMethods:
    """Test new async-specific methods."""

    @pytest.mark.asyncio
    async def test_async_cache_stats(self):
        """Test async cache statistics method."""
        processor = DeduplicationProcessor(window_seconds=60, dedupe_fields=["event"])

        # Add events directly to cache to avoid async processing complexities
        for i in range(10):
            signature = f"test_signature_{i}"
            current_time = time.time()
            async with processor._async_lock:
                processor._event_cache[signature] = (current_time, 1)

        # Test async stats method
        stats = await processor.cache_stats_async()

        assert stats["unique_signatures"] == 10
        assert stats["total_events_seen"] == 10
        assert stats["cache_size"] == 10
        assert stats["max_cache_size"] == 10000

    @pytest.mark.asyncio
    async def test_background_cleanup_async(self):
        """Test background cleanup in async context."""
        processor = DeduplicationProcessor(window_seconds=1, dedupe_fields=["event"])

        # Add events directly to cache that will expire
        old_time = time.time() - 2  # 2 seconds ago (expired)
        for i in range(5):
            signature = f"expire_test_{i}"
            async with processor._async_lock:
                processor._event_cache[signature] = (old_time, 1)

        assert len(processor._event_cache) == 5

        # Trigger background cleanup
        current_time = time.time()
        await processor._background_cleanup(current_time)

        # All entries should be cleaned up
        assert len(processor._event_cache) == 0

    @pytest.mark.asyncio
    async def test_concurrent_async_processing(self):
        """Test concurrent async event processing."""
        processor = DeduplicationProcessor(
            window_seconds=60, dedupe_fields=["event", "worker"]
        )

        async def async_processor(worker_id: int, event_count: int):
            for i in range(event_count):
                event = {
                    "event": f"Concurrent test {i}",
                    "worker": worker_id,
                }
                result = processor.process(None, "info", event)
                assert result is not None
                await asyncio.sleep(0.001)  # Small delay to test concurrency

        # Run multiple async processors concurrently
        tasks = []
        worker_count = 10
        events_per_worker = 20

        for worker_id in range(worker_count):
            task = asyncio.create_task(async_processor(worker_id, events_per_worker))
            tasks.append(task)

        await asyncio.gather(*tasks)

        # Should have processed all events
        expected_events = worker_count * events_per_worker
        assert len(processor._event_cache) == expected_events


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
