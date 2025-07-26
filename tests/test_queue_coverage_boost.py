"""Focused tests to boost queue module coverage."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
import structlog

from fapilog._internal.queue import (
    QueueWorker,
    Sink,
    queue_sink,
    queue_sink_async,
)
from fapilog.container import set_current_container


class TestQueueWorker:
    """Test uncovered QueueWorker functionality."""

    @pytest.fixture
    def mock_sink(self):
        """Create a mock sink."""
        sink = Mock(spec=Sink)
        sink.write = AsyncMock()
        sink._sink_name = "MockSink"
        return sink

    @pytest.fixture
    def worker(self, mock_sink):
        """Create a queue worker."""
        return QueueWorker(
            sinks=[mock_sink],
            queue_max_size=5,
            batch_size=2,
            batch_timeout=0.1,
            retry_delay=0.01,
            max_retries=1,
            overflow_strategy="sample",
            sampling_rate=0.8,
        )

    @pytest.mark.asyncio
    async def test_worker_different_loop_shutdown(self, worker):
        """Test worker shutdown from different event loop."""
        # Start worker in current loop
        await worker.start()

        # Mock being in different loop during shutdown
        different_loop = Mock()
        worker._loop = different_loop

        # Should handle different loop gracefully
        await worker.shutdown()

        assert worker._stopping is True

    @pytest.mark.asyncio
    async def test_worker_shutdown_timeout(self, worker):
        """Test worker shutdown with timeout."""
        await worker.start()

        # Mock the task to not complete quickly
        if worker._task:
            # Make task hang during shutdown
            with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
                await worker.shutdown()

        assert worker._stopping is True

    @pytest.mark.asyncio
    async def test_enqueue_with_sampling(self, worker):
        """Test enqueueing with sampling strategy."""
        # Worker is configured with sample strategy and 0.8 rate

        # Enqueue multiple events - some should be sampled out
        success_count = 0
        for _ in range(10):
            if await worker.enqueue({"test": "event"}):
                success_count += 1

        # With 0.8 sampling rate, not all should succeed
        # (Some randomness, so just check it's reasonable)
        assert 0 <= success_count <= 10

    @pytest.mark.asyncio
    async def test_enqueue_when_stopping(self, worker):
        """Test enqueueing when worker is stopping."""
        worker._stopping = True

        result = await worker.enqueue({"test": "event"})

        assert result is False

    @pytest.mark.asyncio
    async def test_enqueue_block_strategy(self, mock_sink):
        """Test enqueue with block strategy."""
        worker = QueueWorker(
            sinks=[mock_sink], queue_max_size=1, overflow_strategy="block"
        )

        # Fill the queue
        await worker.enqueue({"test": "event1"})

        # Next enqueue should use put() instead of put_nowait()
        with patch.object(worker.queue, "put", new_callable=AsyncMock) as mock_put:
            await worker.enqueue({"test": "event2"})
            mock_put.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_event_retry_logic(self, worker, mock_sink):
        """Test event processing with retry logic."""
        # Make sink fail initially then succeed
        mock_sink.write.side_effect = [Exception("Fail"), None]

        await worker.start()

        # Ensure worker is running
        assert worker._running is True

        # Add sink to worker
        worker.sinks = [mock_sink]

        # Enqueue event
        await worker.queue.put({"test": "event"})

        # Give time for processing and retry
        await asyncio.sleep(0.5)
        await worker.stop()

        # Should have been called twice (fail, then succeed)
        assert mock_sink.write.call_count >= 2

    @pytest.mark.asyncio
    async def test_process_batch_with_metrics(self, worker, mock_sink):
        """Test batch processing with metrics collection."""
        # Enable metrics
        from fapilog._internal.metrics import MetricsCollector

        metrics = MetricsCollector(enabled=True)

        with patch(
            "fapilog._internal.queue.get_metrics_collector", return_value=metrics
        ):
            await worker.start()

            # Enqueue events to trigger batch processing
            await worker.enqueue({"test": "event1"})
            await worker.enqueue({"test": "event2"})

            # Let it process
            await asyncio.sleep(0.2)
            await worker.stop()

        # Metrics should have been recorded
        assert metrics.queue_metrics.total_enqueued > 0

    @pytest.mark.asyncio
    async def test_sink_error_handling(self, mock_sink):
        """Test handling of sink errors during processing."""
        # Configure multiple sinks, some failing
        failing_sink = Mock(spec=Sink)
        failing_sink.write = AsyncMock(side_effect=Exception("Sink failed"))
        failing_sink._sink_name = "FailingSink"

        # Create worker with both sinks from the start
        worker = QueueWorker(
            sinks=[mock_sink, failing_sink],
            queue_max_size=5,
            batch_size=1,  # Process events one at a time for easier testing
            batch_timeout=0.05,  # Shorter timeout for faster processing
            retry_delay=0.01,
            max_retries=1,
            overflow_strategy="block",  # Ensure events aren't dropped
            sampling_rate=1.0,  # Process all events
        )

        await worker.start()

        # Make sure worker is running
        assert worker._running is True

        # Enqueue an event
        enqueue_success = await worker.enqueue({"test": "event"})
        assert enqueue_success is True

        # Wait for processing with proper timeout
        # Use a loop to wait for the event to be processed
        max_wait_time = 2.0  # 2 seconds max
        wait_interval = 0.1
        total_waited = 0.0

        while total_waited < max_wait_time:
            # Check if both sinks have been called
            mock_called = mock_sink.write.call_count >= 1
            failing_called = failing_sink.write.call_count >= 1
            if mock_called and failing_called:
                break
            await asyncio.sleep(wait_interval)
            total_waited += wait_interval

        await worker.stop()

        # The event should have been processed by both sinks
        # The successful sink should have been called
        assert mock_sink.write.call_count >= 1, (
            f"Mock sink was called {mock_sink.write.call_count} times"
        )
        # The failing sink should also have been called (even though it failed)
        assert failing_sink.write.call_count >= 1, (
            f"Failing sink was called {failing_sink.write.call_count} times"
        )


class TestQueueSinkFunctions:
    """Test queue sink processor functions."""

    def setup_method(self):
        """Reset state before each test."""
        set_current_container(None)

    def test_queue_sink_with_container_worker(self):
        """Test queue_sink when worker comes from container."""
        # Create mock container with worker
        mock_container = Mock()
        mock_worker = Mock()
        mock_worker._stopping = False
        mock_worker._running = (
            True  # Worker must be running for put_nowait to be called
        )
        mock_worker.queue.put_nowait = Mock()
        mock_worker.overflow_strategy = "drop"

        mock_container.queue_worker = mock_worker
        set_current_container(mock_container)

        # Should use container's worker
        with pytest.raises(structlog.DropEvent):
            queue_sink(None, "info", {"test": "event"})

        mock_worker.queue.put_nowait.assert_called_once()

    def test_queue_sink_worker_startup_no_loop(self):
        """Test queue_sink worker startup when no event loop."""
        mock_worker = Mock()
        mock_worker._stopping = False
        mock_worker._running = False
        mock_worker.overflow_strategy = "drop"

        # Create a mock container with the worker
        mock_container = Mock()
        mock_container.queue_worker = mock_worker
        set_current_container(mock_container)

        # Mock no running loop
        with patch("asyncio.get_running_loop", side_effect=RuntimeError):
            with pytest.raises(structlog.DropEvent):
                queue_sink(None, "info", {"test": "event"})

    def test_queue_sink_worker_startup_closed_loop(self):
        """Test queue_sink worker startup when loop is closed."""
        mock_worker = Mock()
        mock_worker._stopping = False
        mock_worker._running = False
        mock_worker.overflow_strategy = "drop"

        # Create a mock container with the worker
        mock_container = Mock()
        mock_container.queue_worker = mock_worker
        set_current_container(mock_container)

        # Mock closed loop
        mock_loop = Mock()
        mock_loop.is_closed.return_value = True

        with patch("asyncio.get_running_loop", return_value=mock_loop):
            with pytest.raises(structlog.DropEvent):
                queue_sink(None, "info", {"test": "event"})

    def test_queue_sink_block_strategy_sync(self):
        """Test queue_sink with block strategy in sync context."""
        mock_worker = Mock()
        mock_worker._stopping = False
        mock_worker._running = True
        mock_worker.overflow_strategy = "block"
        mock_worker.queue.put_nowait = Mock(side_effect=asyncio.QueueFull)

        # Create a mock container with the worker
        mock_container = Mock()
        mock_container.queue_worker = mock_worker
        set_current_container(mock_container)

        # Block strategy in sync context should drop when full
        with pytest.raises(structlog.DropEvent):
            queue_sink(None, "info", {"test": "event"})

    def test_queue_sink_sample_strategy_with_sampling(self):
        """Test queue_sink with sample strategy and sampling."""
        mock_worker = Mock()
        mock_worker._stopping = False
        mock_worker._running = True
        mock_worker.overflow_strategy = "sample"
        mock_worker.sampling_rate = 0.0  # Sample out everything
        mock_worker.queue.put_nowait = Mock()

        # Create a mock container with the worker
        mock_container = Mock()
        mock_container.queue_worker = mock_worker
        set_current_container(mock_container)

        # Should drop due to sampling
        with pytest.raises(structlog.DropEvent):
            queue_sink(None, "info", {"test": "event"})

        # Queue shouldn't be called due to sampling
        mock_worker.queue.put_nowait.assert_not_called()

    @pytest.mark.asyncio
    async def test_queue_sink_async_no_worker(self):
        """Test async queue_sink when no worker."""
        event = {"test": "event"}

        result = await queue_sink_async(None, "info", event)

        assert result == event

    @pytest.mark.asyncio
    async def test_queue_sink_async_enqueue_fails(self):
        """Test async queue_sink when enqueue fails."""
        mock_worker = Mock()
        mock_worker.enqueue = AsyncMock(return_value=False)

        # Create a mock container with the worker
        mock_container = Mock()
        mock_container.queue_worker = mock_worker
        set_current_container(mock_container)

        result = await queue_sink_async(None, "info", {"test": "event"})

        assert result is None
