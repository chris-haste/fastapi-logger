"""Comprehensive tests for QueueWorker to improve coverage."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from fapilog.async_components.queue.worker import QueueWorker
from fapilog.sinks import Sink


class MockSink(Sink):
    """Mock sink for testing."""

    def __init__(self, should_fail=False, delay=0.0, container=None):
        super().__init__(container=container)
        self.should_fail = should_fail
        self.delay = delay
        self.write_calls = []

    async def write(self, event_dict):
        """Mock write method."""
        if self.delay > 0:
            await asyncio.sleep(self.delay)

        self.write_calls.append(event_dict)

        if self.should_fail:
            raise RuntimeError("Mock sink failure")


class TestQueueWorkerInit:
    """Test QueueWorker initialization."""

    def test_init_default_parameters(self):
        """Test QueueWorker initialization with default parameters."""
        sink = MockSink()
        worker = QueueWorker([sink])

        assert worker.sinks == [sink]
        assert worker.queue.maxsize == 1000
        assert worker.batch_size == 10
        assert worker.batch_timeout == 1.0
        assert worker.retry_delay == 1.0
        assert worker.max_retries == 3
        assert worker.overflow_strategy == "drop"
        assert worker.sampling_rate == 1.0
        assert worker._task is None
        assert worker._running is False
        assert worker._stopping is False
        assert worker._loop is None

    def test_init_custom_parameters(self):
        """Test QueueWorker initialization with custom parameters."""
        sink = MockSink()
        worker = QueueWorker(
            [sink],
            queue_max_size=500,
            batch_size=20,
            batch_timeout=2.0,
            retry_delay=0.5,
            max_retries=5,
            overflow_strategy="block",
            sampling_rate=0.8,
        )

        assert worker.queue.maxsize == 500
        assert worker.batch_size == 20
        assert worker.batch_timeout == 2.0
        assert worker.retry_delay == 0.5
        assert worker.max_retries == 5
        assert worker.overflow_strategy == "block"
        assert worker.sampling_rate == 0.8

    def test_init_multiple_sinks(self):
        """Test QueueWorker initialization with multiple sinks."""
        sink1 = MockSink()
        sink2 = MockSink()
        worker = QueueWorker([sink1, sink2])

        assert len(worker.sinks) == 2
        assert worker.sinks[0] == sink1
        assert worker.sinks[1] == sink2


class TestQueueWorkerLifecycle:
    """Test QueueWorker lifecycle management."""

    @pytest.mark.asyncio
    async def test_start_worker(self):
        """Test starting the queue worker."""
        sink = MockSink()
        worker = QueueWorker([sink])

        await worker.start()

        assert worker._running is True
        assert worker._stopping is False
        assert worker._task is not None
        assert not worker._task.done()
        assert worker._loop is not None

        # Cleanup
        await worker.stop()

    @pytest.mark.asyncio
    async def test_start_when_already_running(self):
        """Test starting worker when already running."""
        sink = MockSink()
        worker = QueueWorker([sink])

        await worker.start()
        first_task = worker._task

        # Start again - should not create new task
        await worker.start()
        assert worker._task is first_task

        # Cleanup
        await worker.stop()

    @pytest.mark.asyncio
    async def test_stop_worker(self):
        """Test stopping the queue worker."""
        sink = MockSink()
        worker = QueueWorker([sink])

        await worker.start()
        await worker.stop()

        assert worker._running is False
        assert worker._task.done()

    @pytest.mark.asyncio
    async def test_stop_when_task_none(self):
        """Test stopping when task is None."""
        sink = MockSink()
        worker = QueueWorker([sink])

        # Stop without starting
        await worker.stop()
        # Should not raise any exception

    @pytest.mark.asyncio
    async def test_shutdown_worker(self):
        """Test graceful shutdown of worker."""
        sink = MockSink()
        worker = QueueWorker([sink])

        await worker.start()

        # Add some events to queue
        await worker.enqueue({"level": "info", "event": "test1"})
        await worker.enqueue({"level": "info", "event": "test2"})

        await worker.shutdown()

        assert worker._stopping is True
        assert worker._running is False

    @pytest.mark.asyncio
    async def test_shutdown_timeout(self):
        """Test shutdown with timeout."""
        sink = MockSink(delay=10.0)  # Very slow sink
        worker = QueueWorker([sink])

        await worker.start()
        await worker.enqueue({"level": "info", "event": "test"})

        # Mock timeout scenario
        with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
            with patch.object(worker, "_drain_queue", new_callable=AsyncMock):
                await worker.shutdown()

    @pytest.mark.asyncio
    async def test_shutdown_different_loop(self):
        """Test shutdown when task belongs to different loop."""
        sink = MockSink()
        worker = QueueWorker([sink])

        await worker.start()

        # Mock different event loop scenario
        different_loop = Mock()
        with patch("asyncio.get_running_loop", return_value=different_loop):
            await worker.shutdown()

    def test_shutdown_sync(self):
        """Test synchronous shutdown."""
        sink = MockSink()
        worker = QueueWorker([sink])

        # Test shutdown without starting
        worker.shutdown_sync()
        assert worker._stopping is True
        assert worker._running is False

    def test_shutdown_sync_already_stopping(self):
        """Test sync shutdown when already stopping."""
        sink = MockSink()
        worker = QueueWorker([sink])

        worker._stopping = True
        worker.shutdown_sync()  # Should return early

    def test_shutdown_sync_with_task(self):
        """Test sync shutdown with active task."""
        sink = MockSink()
        worker = QueueWorker([sink])

        # Create a mock task
        worker._task = Mock()
        worker._task.done.return_value = False
        worker._task.cancel = Mock()

        # Mock no running loop scenario
        with patch("asyncio.get_running_loop", side_effect=RuntimeError):
            with patch("asyncio.new_event_loop") as mock_new_loop:
                mock_loop = Mock()
                mock_new_loop.return_value = mock_loop
                mock_loop.close = Mock()

                worker.shutdown_sync()

                worker._task.cancel.assert_called_once()

    def test_shutdown_sync_temp_loop_with_matching_task(self):
        """Test sync shutdown with temporary loop and matching task."""
        sink = MockSink()
        worker = QueueWorker([sink])

        # Create a mock task
        worker._task = Mock()
        worker._task.done.return_value = False
        worker._task.cancel = Mock()
        worker._task.get_loop = Mock()

        # Mock no running loop scenario
        with patch("asyncio.get_running_loop", side_effect=RuntimeError):
            with patch("asyncio.new_event_loop") as mock_new_loop:
                with patch("asyncio.set_event_loop"):
                    mock_loop = Mock()
                    mock_new_loop.return_value = mock_loop
                    mock_loop.close = Mock()
                    mock_loop.run_until_complete = Mock()
                    # Make task belong to different loop to skip run_until_complete
                    worker._task.get_loop.return_value = Mock()  # Different loop

                    worker.shutdown_sync(timeout=1.0)

                    # Should still call cancel but skip run_until_complete
                    worker._task.cancel.assert_called_once()


class TestQueueWorkerProcessing:
    """Test QueueWorker event processing."""

    @pytest.mark.asyncio
    async def test_collect_batch_timeout(self):
        """Test batch collection with timeout."""
        sink = MockSink()
        worker = QueueWorker([sink], batch_timeout=0.1)

        # No events in queue - should timeout
        batch = await worker._collect_batch()
        assert batch == []

    @pytest.mark.asyncio
    async def test_collect_batch_single_event(self):
        """Test collecting batch with single event."""
        sink = MockSink()
        worker = QueueWorker([sink], batch_size=5)

        # Add one event
        event = {"level": "info", "event": "test"}
        await worker.queue.put(event)

        batch = await worker._collect_batch()
        assert len(batch) == 1
        assert batch[0] == event

    @pytest.mark.asyncio
    async def test_collect_batch_multiple_events(self):
        """Test collecting batch with multiple events."""
        sink = MockSink()
        worker = QueueWorker([sink], batch_size=3)

        # Add multiple events
        events = [
            {"level": "info", "event": "test1"},
            {"level": "warning", "event": "test2"},
            {"level": "error", "event": "test3"},
            {"level": "debug", "event": "test4"},
        ]

        for event in events:
            await worker.queue.put(event)

        batch = await worker._collect_batch()
        assert len(batch) == 3  # Limited by batch_size
        assert batch[0] == events[0]
        assert batch[1] == events[1]
        assert batch[2] == events[2]

    @pytest.mark.asyncio
    async def test_collect_batch_with_metrics(self):
        """Test batch collection with metrics recording."""
        # Create mock container with metrics collector
        mock_metrics = Mock()
        mock_metrics.record_dequeue = Mock()
        mock_container = Mock()
        mock_container.get_metrics_collector.return_value = mock_metrics

        sink = MockSink()
        worker = QueueWorker([sink], container=mock_container)

        event = {"level": "info", "event": "test"}
        await worker.queue.put(event)

        batch = await worker._collect_batch()
        assert len(batch) == 1

        # Should record dequeue metrics
        assert mock_metrics.record_dequeue.called

    @pytest.mark.asyncio
    async def test_process_batch(self):
        """Test processing a batch of events."""
        sink = MockSink()
        worker = QueueWorker([sink])

        events = [
            {"level": "info", "event": "test1"},
            {"level": "warning", "event": "test2"},
        ]

        await worker._process_batch(events)

        assert len(sink.write_calls) == 2
        assert sink.write_calls[0] == events[0]
        assert sink.write_calls[1] == events[1]

    @pytest.mark.asyncio
    async def test_process_batch_with_metrics(self):
        """Test batch processing with metrics."""
        # Create mock container with metrics collector
        mock_metrics = Mock()
        mock_metrics.record_batch_processing = Mock()
        mock_container = Mock()
        mock_container.get_metrics_collector.return_value = mock_metrics

        sink = MockSink()
        worker = QueueWorker([sink], container=mock_container)

        events = [{"level": "info", "event": "test"}]
        await worker._process_batch(events)

        mock_metrics.record_batch_processing.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_event_success(self):
        """Test successful event processing."""
        sink = MockSink()
        worker = QueueWorker([sink])

        event = {"level": "info", "event": "test"}
        await worker._process_event(event)

        assert len(sink.write_calls) == 1
        assert sink.write_calls[0] == event

    @pytest.mark.asyncio
    async def test_process_event_sink_failure(self):
        """Test event processing with sink failure."""
        sink = MockSink(should_fail=True)
        worker = QueueWorker([sink], max_retries=1)

        event = {"level": "error", "event": "test"}

        # Import the correct exception type
        from fapilog.exceptions import QueueError

        with pytest.raises(QueueError):
            await worker._process_event(event)

    @pytest.mark.asyncio
    async def test_process_event_multiple_sinks_partial_failure(self):
        """Test event processing with multiple sinks where some fail."""
        sink1 = MockSink(should_fail=False)
        sink2 = MockSink(should_fail=True)
        sink3 = MockSink(should_fail=False)
        worker = QueueWorker([sink1, sink2, sink3], max_retries=1)

        event = {"level": "error", "event": "test"}

        # Import the correct exception type
        from fapilog.exceptions import QueueError

        with pytest.raises(QueueError):
            await worker._process_event(event)

        # Non-failing sinks should still have been called
        assert len(sink1.write_calls) >= 1
        assert len(sink3.write_calls) >= 1

    @pytest.mark.asyncio
    async def test_process_event_with_metrics(self):
        """Test event processing with metrics recording."""
        # Create mock container with metrics collector
        mock_metrics = Mock()
        mock_metrics.record_log_event = Mock()
        mock_container = Mock()
        mock_container.get_metrics_collector.return_value = mock_metrics

        sink = MockSink()
        worker = QueueWorker([sink], container=mock_container)

        event = {"level": "info", "event": "test"}
        await worker._process_event(event)

        mock_metrics.record_log_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_drain_queue(self):
        """Test draining remaining events from queue."""
        sink = MockSink()
        worker = QueueWorker([sink])

        # Add events to queue
        events = [
            {"level": "info", "event": "test1"},
            {"level": "warning", "event": "test2"},
        ]

        for event in events:
            await worker.queue.put(event)

        await worker._drain_queue()

        assert len(sink.write_calls) == 2
        assert worker.queue.empty()

    @pytest.mark.asyncio
    async def test_drain_queue_empty(self):
        """Test draining empty queue."""
        sink = MockSink()
        worker = QueueWorker([sink])

        await worker._drain_queue()
        assert len(sink.write_calls) == 0

    @pytest.mark.asyncio
    async def test_run_main_loop(self):
        """Test main worker run loop."""
        sink = MockSink()
        worker = QueueWorker([sink], batch_timeout=0.1)

        # Start worker and add events
        await worker.start()

        events = [
            {"level": "info", "event": "test1"},
            {"level": "warning", "event": "test2"},
        ]

        for event in events:
            await worker.enqueue(event)

        # Let it process for a bit
        await asyncio.sleep(0.2)

        await worker.stop()

        # Events should have been processed
        assert len(sink.write_calls) >= 2

    @pytest.mark.asyncio
    async def test_run_with_exception(self):
        """Test main run loop with exception handling."""
        sink = MockSink()
        worker = QueueWorker([sink])

        # Mock _collect_batch to raise exception
        original_collect = worker._collect_batch
        call_count = 0

        async def failing_collect():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Test exception")
            return await original_collect()

        worker._collect_batch = failing_collect

        await worker.start()
        await asyncio.sleep(0.1)  # Let it handle the exception
        await worker.stop()


class TestQueueWorkerEnqueue:
    """Test QueueWorker enqueue functionality."""

    @pytest.mark.asyncio
    async def test_enqueue_drop_strategy_success(self):
        """Test enqueue with drop strategy - successful case."""
        sink = MockSink()
        worker = QueueWorker([sink], overflow_strategy="drop")

        event = {"level": "info", "event": "test"}
        result = await worker.enqueue(event)

        assert result is True
        assert worker.queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_enqueue_drop_strategy_full_queue(self):
        """Test enqueue with drop strategy - full queue."""
        sink = MockSink()
        worker = QueueWorker([sink], queue_max_size=1, overflow_strategy="drop")

        # Fill the queue
        await worker.queue.put({"level": "info", "event": "first"})

        # Try to enqueue when full
        event = {"level": "info", "event": "test"}
        result = await worker.enqueue(event)

        assert result is False
        assert worker.queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_enqueue_block_strategy_success(self):
        """Test enqueue with block strategy - successful case."""
        sink = MockSink()
        worker = QueueWorker([sink], overflow_strategy="block")

        event = {"level": "info", "event": "test"}
        result = await worker.enqueue(event)

        assert result is True
        assert worker.queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_enqueue_block_strategy_cancelled(self):
        """Test enqueue with block strategy - operation cancelled."""
        sink = MockSink()
        worker = QueueWorker([sink], queue_max_size=1, overflow_strategy="block")

        # Fill the queue
        await worker.queue.put({"level": "info", "event": "first"})

        # Mock asyncio.CancelledError
        with patch.object(worker.queue, "put", side_effect=asyncio.CancelledError):
            event = {"level": "info", "event": "test"}
            result = await worker.enqueue(event)
            assert result is False

    @pytest.mark.asyncio
    async def test_enqueue_sample_strategy_success(self):
        """Test enqueue with sample strategy - successful case."""
        sink = MockSink()
        worker = QueueWorker([sink], overflow_strategy="sample")

        event = {"level": "info", "event": "test"}
        result = await worker.enqueue(event)

        assert result is True
        assert worker.queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_enqueue_sample_strategy_full_queue(self):
        """Test enqueue with sample strategy - full queue."""
        sink = MockSink()
        worker = QueueWorker([sink], queue_max_size=1, overflow_strategy="sample")

        # Fill the queue
        await worker.queue.put({"level": "info", "event": "first"})

        # Try to enqueue when full
        event = {"level": "info", "event": "test"}
        result = await worker.enqueue(event)

        assert result is False

    @pytest.mark.asyncio
    async def test_enqueue_when_stopping(self):
        """Test enqueue when worker is stopping."""
        sink = MockSink()
        worker = QueueWorker([sink])

        worker._stopping = True

        event = {"level": "info", "event": "test"}
        result = await worker.enqueue(event)

        assert result is False

    @pytest.mark.asyncio
    async def test_enqueue_with_sampling_filtered_out(self):
        """Test enqueue with sampling - event filtered out."""
        sink = MockSink()
        worker = QueueWorker([sink], sampling_rate=0.5)

        with patch("fapilog._internal.queue_worker.rnd.random", return_value=0.8):
            event = {"level": "info", "event": "test"}
            result = await worker.enqueue(event)

            assert result is False
            assert worker.queue.qsize() == 0

    @pytest.mark.asyncio
    async def test_enqueue_with_sampling_accepted(self):
        """Test enqueue with sampling - event accepted."""
        sink = MockSink()
        worker = QueueWorker([sink], sampling_rate=0.5)

        with patch("fapilog._internal.queue_worker.rnd.random", return_value=0.3):
            event = {"level": "info", "event": "test"}
            result = await worker.enqueue(event)

            assert result is True
            assert worker.queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_enqueue_with_metrics(self):
        """Test enqueue with metrics recording."""
        # Create mock container with metrics collector
        mock_metrics = Mock()
        mock_metrics.record_enqueue = Mock()
        mock_metrics.record_queue_size = Mock()
        mock_container = Mock()
        mock_container.get_metrics_collector.return_value = mock_metrics

        sink = MockSink()
        worker = QueueWorker([sink], container=mock_container)

        event = {"level": "info", "event": "test"}
        result = await worker.enqueue(event)

        assert result is True
        mock_metrics.record_enqueue.assert_called_once()
        mock_metrics.record_queue_size.assert_called_once()

    @pytest.mark.asyncio
    async def test_enqueue_with_metrics_sampling(self):
        """Test enqueue with metrics recording for sampled events."""
        # Create mock container with metrics collector
        mock_metrics = Mock()
        mock_metrics.record_sampled_event = Mock()
        mock_container = Mock()
        mock_container.get_metrics_collector.return_value = mock_metrics

        sink = MockSink()
        worker = QueueWorker([sink], sampling_rate=0.5, container=mock_container)

        with patch("fapilog._internal.queue_worker.rnd.random", return_value=0.8):
            event = {"level": "info", "event": "test"}
            result = await worker.enqueue(event)

            assert result is False
            mock_metrics.record_sampled_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_enqueue_with_metrics_dropped(self):
        """Test enqueue with metrics recording for dropped events."""
        # Create mock container with metrics collector
        mock_metrics = Mock()
        mock_metrics.record_dropped_event = Mock()
        mock_container = Mock()
        mock_container.get_metrics_collector.return_value = mock_metrics

        sink = MockSink()
        worker = QueueWorker(
            [sink], queue_max_size=1, overflow_strategy="drop", container=mock_container
        )

        # Fill the queue
        await worker.queue.put({"level": "info", "event": "first"})

        event = {"level": "info", "event": "test"}
        result = await worker.enqueue(event)

        assert result is False
        mock_metrics.record_dropped_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_enqueue_exception_handling(self):
        """Test enqueue exception handling."""
        sink = MockSink()
        worker = QueueWorker([sink])

        # Mock an unexpected exception
        with patch.object(
            worker.queue, "put_nowait", side_effect=RuntimeError("Unexpected error")
        ):
            event = {"level": "info", "event": "test"}

            # Import the correct exception type
            from fapilog.exceptions import QueueError

            with pytest.raises(QueueError):
                await worker.enqueue(event)


class TestQueueWorkerIntegration:
    """Integration tests for QueueWorker."""

    @pytest.mark.asyncio
    async def test_full_worker_lifecycle(self):
        """Test complete worker lifecycle with events."""
        sink = MockSink()
        worker = QueueWorker([sink], batch_size=2, batch_timeout=0.1)

        # Start worker
        await worker.start()

        # Enqueue some events
        events = [
            {"level": "info", "event": "test1"},
            {"level": "warning", "event": "test2"},
            {"level": "error", "event": "test3"},
        ]

        for event in events:
            result = await worker.enqueue(event)
            assert result is True

        # Let worker process events
        await asyncio.sleep(0.2)

        # Shutdown gracefully
        await worker.shutdown()

        # All events should be processed
        assert len(sink.write_calls) == 3

    @pytest.mark.asyncio
    async def test_worker_with_failing_sink(self):
        """Test worker behavior with failing sink."""
        sink = MockSink(should_fail=True)
        worker = QueueWorker([sink], max_retries=1, retry_delay=0.1)

        await worker.start()

        # Enqueue event - should fail but not crash worker
        event = {"level": "error", "event": "test"}
        await worker.enqueue(event)

        # Let worker attempt to process
        await asyncio.sleep(0.3)

        await worker.stop()

        # Worker should still be functional despite sink failures
        assert worker._task.done()

    @pytest.mark.asyncio
    async def test_worker_stress_test(self):
        """Stress test with many concurrent events."""
        sink = MockSink()
        worker = QueueWorker([sink], batch_size=5, batch_timeout=0.05)

        await worker.start()

        # Enqueue many events
        tasks = []
        for i in range(50):
            event = {"level": "info", "event": f"test{i}"}
            tasks.append(worker.enqueue(event))

        results = await asyncio.gather(*tasks)
        assert all(results)  # All enqueues should succeed

        # Let worker process
        await asyncio.sleep(1.0)

        await worker.shutdown()

        # All events should eventually be processed
        assert len(sink.write_calls) == 50
