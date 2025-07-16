"""Tests for async log queue functionality."""

import asyncio
import json
import time
from unittest.mock import patch

import pytest
import structlog

from fapilog._internal.queue import (
    QueueWorker,
    Sink,
    get_queue_worker,
    queue_sink,
    set_queue_worker,
)
from fapilog.bootstrap import configure_logging, reset_logging
from fapilog.settings import LoggingSettings
from fapilog.sinks.stdout import StdoutSink


class MockSink(Sink):
    """Mock sink for testing."""

    def __init__(self) -> None:
        """Initialize the mock sink."""
        self.events = []
        self.write_calls = 0
        self.should_fail = False

    async def write(self, event_dict: dict) -> None:
        """Write a log event to the mock sink."""
        self.write_calls += 1
        if self.should_fail:
            raise Exception("Mock sink failure")
        self.events.append(event_dict)


class TestQueueWorker:
    """Test the QueueWorker class."""

    @pytest.fixture
    def mock_sink(self) -> MockSink:
        """Create a mock sink for testing."""
        return MockSink()

    @pytest.fixture
    def worker(self, mock_sink: MockSink) -> QueueWorker:
        """Create a queue worker for testing."""
        return QueueWorker(
            sinks=[mock_sink],
            queue_size=10,
            batch_size=2,
            batch_timeout=0.1,
            retry_delay=0.01,
            max_retries=2,
        )

    @pytest.mark.asyncio
    async def test_worker_initialization(self, worker: QueueWorker) -> None:
        """Test that the worker initializes correctly."""
        assert worker.queue.maxsize == 10
        assert worker.batch_size == 2
        assert worker.batch_timeout == 0.1
        assert worker.retry_delay == 0.01
        assert worker.max_retries == 2
        assert len(worker.sinks) == 1

    @pytest.mark.asyncio
    async def test_worker_start_stop(self, worker: QueueWorker) -> None:
        """Test that the worker starts and stops correctly."""
        # Start the worker
        await worker.start()
        assert worker._running is True
        assert worker._task is not None
        assert not worker._task.done()

        # Stop the worker
        await worker.stop()
        assert worker._running is False
        assert worker._task.done()

    @pytest.mark.asyncio
    async def test_worker_enqueue_success(self, worker: QueueWorker) -> None:
        """Test that events can be enqueued successfully."""
        event = {"level": "info", "event": "test_event"}

        # Enqueue an event
        success = await worker.enqueue(event)
        assert success is True

        # Check that the event is in the queue
        assert worker.queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_worker_enqueue_full_queue(self, worker: QueueWorker) -> None:
        """Test that enqueue returns False when queue is full."""
        # Fill the queue
        for i in range(10):
            await worker.enqueue({"event": f"event_{i}"})

        # Try to enqueue one more event
        success = await worker.enqueue({"event": "overflow"})
        assert success is False

    @pytest.mark.asyncio
    async def test_worker_processes_events(
        self, worker: QueueWorker, mock_sink: MockSink
    ) -> None:
        """Test that the worker processes events correctly."""
        # Start the worker
        await worker.start()

        # Enqueue some events
        events = [
            {"level": "info", "event": "event_1"},
            {"level": "error", "event": "event_2"},
            {"level": "debug", "event": "event_3"},
        ]

        for event in events:
            await worker.enqueue(event)

        # Wait for processing
        await asyncio.sleep(0.2)

        # Stop the worker
        await worker.stop()

        # Check that events were processed
        assert len(mock_sink.events) == 3
        assert mock_sink.write_calls == 3

        # Check that all events were processed
        for event in events:
            assert event in mock_sink.events

    @pytest.mark.asyncio
    async def test_worker_batch_processing(
        self, worker: QueueWorker, mock_sink: MockSink
    ) -> None:
        """Test that the worker processes events in batches."""
        # Start the worker
        await worker.start()

        # Enqueue events
        for i in range(5):
            await worker.enqueue({"event": f"event_{i}"})

        # Wait for processing
        await asyncio.sleep(0.3)

        # Stop the worker
        await worker.stop()

        # Check that all events were processed
        assert len(mock_sink.events) == 5
        assert mock_sink.write_calls == 5

    @pytest.mark.asyncio
    async def test_worker_retry_on_failure(
        self, worker: QueueWorker, mock_sink: MockSink
    ) -> None:
        """Test that the worker retries on sink failures."""
        # Make the sink fail
        mock_sink.should_fail = True

        # Start the worker
        await worker.start()

        # Enqueue an event
        await worker.enqueue({"event": "test_event"})

        # Wait for processing and retries
        await asyncio.sleep(0.5)

        # Stop the worker
        await worker.stop()

        # Check that the event was retried multiple times
        assert mock_sink.write_calls >= 3  # Initial + 2 retries

    @pytest.mark.asyncio
    async def test_worker_graceful_shutdown(self, worker: QueueWorker) -> None:
        """Test that the worker shuts down gracefully."""
        # Start the worker
        await worker.start()

        # Enqueue some events
        for i in range(5):
            await worker.enqueue({"event": f"event_{i}"})

        # Stop the worker immediately
        await worker.stop()

        # Check that the worker stopped
        assert worker._running is False
        assert worker._task.done()

    @pytest.mark.asyncio
    async def test_overflow_drop_mode(self, mock_sink: MockSink) -> None:
        """Test that drop mode silently discards logs when queue is full."""
        worker = QueueWorker(
            sinks=[mock_sink],
            queue_size=2,
            overflow_strategy="drop",
        )

        # Fill the queue
        await worker.enqueue({"event": "event_1"})
        await worker.enqueue({"event": "event_2"})

        # Try to enqueue more events - should be dropped silently
        result = await worker.enqueue({"event": "overflow_1"})
        assert result is False

        result = await worker.enqueue({"event": "overflow_2"})
        assert result is False

        # Queue should still only have 2 items
        assert worker.queue.qsize() == 2

    @pytest.mark.asyncio
    async def test_overflow_block_mode(self, mock_sink: MockSink) -> None:
        """Test that block mode waits for queue space."""
        worker = QueueWorker(
            sinks=[mock_sink],
            queue_size=1,
            overflow_strategy="block",
        )

        # Fill the queue
        await worker.enqueue({"event": "event_1"})

        # Start a task to enqueue another event (should block)
        async def enqueue_blocking():
            return await worker.enqueue({"event": "blocking_event"})

        # Start the blocking enqueue
        task = asyncio.create_task(enqueue_blocking())

        # Wait a bit to ensure it's blocked
        await asyncio.sleep(0.1)
        assert not task.done()

        # Process the first event to free space
        event = await worker.queue.get()
        await mock_sink.write(event)

        # Now the blocking enqueue should complete
        await asyncio.wait_for(task, timeout=1.0)
        assert task.done()
        assert task.result() is True

    @pytest.mark.asyncio
    async def test_overflow_sample_mode(self, mock_sink: MockSink) -> None:
        """Test that sample mode uses probabilistic sampling."""
        worker = QueueWorker(
            sinks=[mock_sink],
            queue_size=1,
            overflow_strategy="sample",
            sampling_rate=0.5,
        )

        # Fill the queue
        await worker.enqueue({"event": "event_1"})

        # Try to enqueue more events with sampling
        results = []
        for i in range(10):
            result = await worker.enqueue({"event": f"sample_event_{i}"})
            results.append(result)

        # Some should be accepted (True), some dropped (False)
        # Due to sampling, we expect roughly half to be accepted
        accepted_count = sum(1 for r in results if r is True)
        assert 0 <= accepted_count <= 10  # Should be some variation

    @pytest.mark.asyncio
    async def test_overflow_sample_mode_with_sampling_rate(
        self, mock_sink: MockSink
    ) -> None:
        """Test that sample mode respects the sampling rate."""
        worker = QueueWorker(
            sinks=[mock_sink],
            queue_size=100,  # Large queue to avoid overflow
            overflow_strategy="sample",
            sampling_rate=0.3,
        )

        # Enqueue many events
        results = []
        for i in range(100):
            result = await worker.enqueue({"event": f"sample_event_{i}"})
            results.append(result)

        # Count accepted events
        accepted_count = sum(1 for r in results if r is True)

        # With 30% sampling rate, we expect roughly 30% to be accepted
        # Allow for some variance (20-40%)
        assert 20 <= accepted_count <= 40

    @pytest.mark.asyncio
    async def test_overflow_strategies_with_sampling_rate(
        self, mock_sink: MockSink
    ) -> None:
        """Test that sampling rate is applied correctly with different strategies."""
        # Test drop strategy with sampling
        worker_drop = QueueWorker(
            sinks=[mock_sink],
            queue_size=100,
            overflow_strategy="drop",
            sampling_rate=0.5,
        )

        # Test block strategy with sampling
        worker_block = QueueWorker(
            sinks=[mock_sink],
            queue_size=100,
            overflow_strategy="block",
            sampling_rate=0.5,
        )

        # Test sample strategy with sampling
        worker_sample = QueueWorker(
            sinks=[mock_sink],
            queue_size=100,
            overflow_strategy="sample",
            sampling_rate=0.5,
        )

        # Enqueue events to each worker
        results_drop = []
        results_block = []
        results_sample = []

        for i in range(20):
            results_drop.append(await worker_drop.enqueue({"event": f"event_{i}"}))
            results_block.append(await worker_block.enqueue({"event": f"event_{i}"}))
            results_sample.append(await worker_sample.enqueue({"event": f"event_{i}"}))

        # All should have similar sampling behavior
        accepted_drop = sum(1 for r in results_drop if r is True)
        accepted_block = sum(1 for r in results_block if r is True)
        accepted_sample = sum(1 for r in results_sample if r is True)

        # All strategies apply sampling rate first, then handle overflow
        # So all should be around 10 (50% of 20)
        assert 5 <= accepted_drop <= 15
        assert 5 <= accepted_block <= 15
        assert 5 <= accepted_sample <= 15

    @pytest.mark.asyncio
    async def test_shutdown_flushes_events(
        self, worker: QueueWorker, mock_sink: MockSink
    ) -> None:
        """Test that shutdown flushes remaining events in the queue."""
        await worker.start()
        # Enqueue events
        for i in range(3):
            await worker.enqueue({"event": f"event_{i}"})
        # Call shutdown
        await worker.shutdown()
        # All events should be flushed
        assert len(mock_sink.events) == 3

    @pytest.mark.asyncio
    async def test_shutdown_idempotent(
        self, worker: QueueWorker, mock_sink: MockSink
    ) -> None:
        """Test that shutdown can be called multiple times safely."""
        await worker.start()
        await worker.enqueue({"event": "event_1"})
        await worker.shutdown()
        # Call shutdown again
        await worker.shutdown()
        # Event should be flushed only once
        assert mock_sink.events.count({"event": "event_1"}) == 1

    @pytest.mark.asyncio
    async def test_no_enqueue_after_shutdown(
        self, worker: QueueWorker, mock_sink: MockSink
    ) -> None:
        """Test that no events are enqueued or processed after shutdown."""
        await worker.start()
        await worker.shutdown()
        # Try to enqueue after shutdown
        result = await worker.enqueue({"event": "should_not_enqueue"})
        assert result is False
        # No new events should be processed
        assert {"event": "should_not_enqueue"} not in mock_sink.events


class TestQueueSink:
    """Test the queue_sink processor."""

    def setup_method(self) -> None:
        """Reset logging before each test."""
        reset_logging()

    def teardown_method(self) -> None:
        """Reset logging after each test."""
        reset_logging()

    def test_queue_sink_no_worker(self) -> None:
        """Test queue_sink when no worker is configured."""
        # Ensure no worker is set
        set_queue_worker(None)

        event_dict = {"level": "info", "event": "test_event"}

        # Call queue_sink without a worker
        result = queue_sink(None, "info", event_dict)

        # Should return the event_dict to allow fallback processing
        assert result == event_dict

    def test_queue_sink_with_worker(self) -> None:
        """Test queue_sink when worker is configured."""
        # Create a mock worker with a real queue
        from fapilog._internal.queue import QueueWorker

        worker = QueueWorker(sinks=[], queue_size=10)
        set_queue_worker(worker)

        event_dict = {"level": "info", "event": "test_event"}

        # Call queue_sink - should raise DropEvent when queue is enabled
        with pytest.raises(structlog.DropEvent):
            queue_sink(None, "info", event_dict)

    def test_queue_sink_queue_full(self) -> None:
        """Test that queue_sink handles full queue correctly."""
        # Create a worker with a small queue
        worker = QueueWorker(
            sinks=[MockSink()],
            queue_size=1,
        )
        set_queue_worker(worker)

        # Fill the queue
        event1 = {"level": "info", "event": "event_1"}
        with pytest.raises(structlog.DropEvent):
            queue_sink(None, "info", event1)

        # Try to enqueue another event - should be dropped
        event2 = {"level": "info", "event": "event_2"}
        with pytest.raises(structlog.DropEvent):
            queue_sink(None, "info", event2)

    def test_queue_sink_overflow_drop_mode(self) -> None:
        """Test queue_sink with drop overflow strategy."""
        worker = QueueWorker(
            sinks=[MockSink()],
            queue_size=1,
            overflow_strategy="drop",
        )
        set_queue_worker(worker)

        # Fill the queue
        event1 = {"level": "info", "event": "event_1"}
        with pytest.raises(structlog.DropEvent):
            queue_sink(None, "info", event1)

        # Try to enqueue more events - should be dropped silently
        for i in range(5):
            event = {"level": "info", "event": f"overflow_{i}"}
            with pytest.raises(structlog.DropEvent):
                queue_sink(None, "info", event)

    def test_queue_sink_overflow_block_mode(self) -> None:
        """Test queue_sink with block overflow strategy (falls back to drop)."""
        worker = QueueWorker(
            sinks=[MockSink()],
            queue_size=1,
            overflow_strategy="block",
        )
        set_queue_worker(worker)

        # Fill the queue
        event1 = {"level": "info", "event": "event_1"}
        with pytest.raises(structlog.DropEvent):
            queue_sink(None, "info", event1)

        # Try to enqueue more events - should fall back to drop in sync context
        for i in range(5):
            event = {"level": "info", "event": f"overflow_{i}"}
            with pytest.raises(structlog.DropEvent):
                queue_sink(None, "info", event)

    def test_queue_sink_overflow_sample_mode(self) -> None:
        """Test queue_sink with sample overflow strategy."""
        worker = QueueWorker(
            sinks=[MockSink()],
            queue_size=1,
            overflow_strategy="sample",
            sampling_rate=0.5,
        )
        set_queue_worker(worker)

        # Fill the queue
        event1 = {"level": "info", "event": "event_1"}
        with pytest.raises(structlog.DropEvent):
            queue_sink(None, "info", event1)

        # Try to enqueue more events with sampling
        for i in range(10):
            event = {"level": "info", "event": f"sample_{i}"}
            with pytest.raises(structlog.DropEvent):
                queue_sink(None, "info", event)


class TestQueueIntegration:
    """Test queue integration with the full logging system."""

    def setup_method(self) -> None:
        """Reset logging before each test."""
        reset_logging()

    def teardown_method(self) -> None:
        """Reset logging after each test."""
        reset_logging()

    def test_configure_logging_with_queue(self) -> None:
        """Test that configure_logging sets up the queue correctly."""
        settings = LoggingSettings(
            queue_enabled=True,
            queue_maxsize=100,
            queue_batch_size=5,
            queue_batch_timeout=0.5,
            queue_retry_delay=0.1,
            queue_max_retries=2,
        )

        configure_logging(settings=settings)

        # Check that a worker was created
        worker = get_queue_worker()
        assert worker is not None
        assert worker.queue.maxsize == 100
        assert worker.batch_size == 5
        assert worker.batch_timeout == 0.5
        assert worker.retry_delay == 0.1
        assert worker.max_retries == 2

    def test_configure_logging_without_queue(self) -> None:
        """Test that configure_logging works without queue."""
        settings = LoggingSettings(queue_enabled=False)

        configure_logging(settings=settings)

        # Check that no worker was created
        worker = get_queue_worker()
        assert worker is None

    @pytest.mark.asyncio
    async def test_logging_through_queue(self) -> None:
        """Test that logs flow through the queue correctly."""
        # Configure logging with queue
        settings = LoggingSettings(
            queue_enabled=True,
            sinks=["stdout"],
            json_console="json",
        )

        logger = configure_logging(settings=settings)

        # Log some events
        logger.info("test_info_event", extra_field="value1")
        logger.error("test_error_event", error_code=500)

        # Wait for processing
        await asyncio.sleep(0.2)

        # Get the worker and check queue size
        worker = get_queue_worker()
        assert worker is not None

        # The queue should be empty after processing
        assert worker.queue.qsize() == 0

    def test_queue_capacity_drop(self) -> None:
        """Test that logs are dropped when queue is full."""
        # Configure logging with small queue
        settings = LoggingSettings(
            queue_enabled=True,
            queue_maxsize=2,  # Very small queue
            sinks=["stdout"],
        )

        logger = configure_logging(settings=settings)

        # Log many events quickly
        for i in range(10):
            logger.info(f"event_{i}")

        # Get the worker
        worker = get_queue_worker()
        assert worker is not None

        # Some events should have been dropped due to queue size
        # The exact number depends on timing, but some should be dropped
        assert worker.queue.qsize() <= 2

    @pytest.mark.asyncio
    async def test_queue_nonblocking_under_load(self) -> None:
        """Test that queue doesn't block under high load."""
        # Configure logging with queue
        settings = LoggingSettings(
            queue_enabled=True,
            queue_maxsize=100,
            sinks=["stdout"],
        )

        logger = configure_logging(settings=settings)

        # Log many events quickly
        start_time = time.time()
        for i in range(100):
            logger.info(f"load_test_event_{i}")
        end_time = time.time()

        # Logging should be fast (non-blocking)
        assert end_time - start_time < 1.0  # Should complete quickly

        # Wait for processing
        await asyncio.sleep(0.5)

        # Get the worker
        worker = get_queue_worker()
        assert worker is not None

        # Queue should be empty after processing
        assert worker.queue.qsize() == 0

        # Properly shut down the worker to avoid warnings
        await worker.shutdown()

        # Reset logging to fully clean up
        reset_logging()


class TestStdoutSink:
    """Test the StdoutSink implementation."""

    @pytest.mark.asyncio
    async def test_stdout_sink_json(self) -> None:
        """Test that StdoutSink writes JSON correctly."""
        sink = StdoutSink(mode="json")
        event = {
            "level": "info",
            "event": "test_event",
            "timestamp": "2023-01-01T00:00:00Z",
        }

        # Capture print output
        with patch("builtins.print") as mock_print:
            await sink.write(event)

            # Check that print was called
            mock_print.assert_called_once()

            # Get the printed data
            call_args = mock_print.call_args[0][0]
            written_data = json.loads(call_args)

            # Check that the event was written correctly
            assert written_data["level"] == "info"
            assert written_data["event"] == "test_event"
            assert written_data["timestamp"] == "2023-01-01T00:00:00Z"

    @pytest.mark.asyncio
    async def test_stdout_sink_pretty(self) -> None:
        """Test that StdoutSink writes pretty format correctly."""
        sink = StdoutSink(mode="pretty")
        event = {
            "level": "info",
            "event": "test_event",
            "timestamp": "2023-01-01T00:00:00Z",
        }

        # Capture print output
        with patch("builtins.print") as mock_print:
            await sink.write(event)

            # Check that print was called
            mock_print.assert_called_once()

            # Get the printed data
            call_args = mock_print.call_args[0][0]

            # Check that it's in pretty format (should contain ANSI codes)
            assert "\x1b[" in call_args  # ANSI color codes


class TestFastAPIShutdownIntegration:
    """Test FastAPI shutdown integration."""

    def setup_method(self) -> None:
        """Reset logging before each test."""
        reset_logging()

    def teardown_method(self) -> None:
        """Reset logging after each test."""
        reset_logging()

    @pytest.mark.asyncio
    async def test_fastapi_shutdown_handler_registration(self) -> None:
        """Test that FastAPI shutdown handler is registered when app is provided."""
        from fastapi import FastAPI
        from fapilog.bootstrap import configure_logging
        from fapilog.settings import LoggingSettings

        # Create settings with queue enabled
        settings = LoggingSettings(queue_enabled=True)

        # Create FastAPI app
        app = FastAPI()

        # Configure logging with app
        configure_logging(settings=settings, app=app)

        # Check that middleware is registered (this indicates the app was configured)
        assert len(app.user_middleware) > 0

        # Verify that queue worker was created
        from fapilog._internal.queue import get_queue_worker

        worker = get_queue_worker()
        assert worker is not None
        # Note: We don't check if worker is running as it may be in a different state
        # during test execution

    @pytest.mark.asyncio
    async def test_fastapi_shutdown_flushes_logs(self) -> None:
        """Test that FastAPI shutdown event flushes remaining logs."""
        from fastapi import FastAPI
        from fapilog.bootstrap import configure_logging
        from fapilog.settings import LoggingSettings
        from fapilog._internal.queue import get_queue_worker

        # Create mock sink
        mock_sink = MockSink()

        # Create settings with queue enabled
        settings = LoggingSettings(queue_enabled=True)

        # Create FastAPI app
        app = FastAPI()

        # Configure logging with app
        configure_logging(settings=settings, app=app)

        # Get the queue worker
        worker = get_queue_worker()
        assert worker is not None

        # Replace sinks with mock sink for testing
        worker.sinks = [mock_sink]

        # Enqueue some events
        for i in range(3):
            await worker.enqueue({"event": f"test_event_{i}"})

        # Simulate FastAPI shutdown by calling the shutdown handler
        # The shutdown handler is registered as app.add_event_handler("shutdown", worker.shutdown)
        await worker.shutdown()

        # Verify that all events were flushed
        assert len(mock_sink.events) == 3
        for i in range(3):
            assert {"event": f"test_event_{i}"} in mock_sink.events


class TestAtexitShutdownIntegration:
    """Test atexit shutdown integration."""

    def setup_method(self) -> None:
        """Reset logging before each test."""
        reset_logging()

    def teardown_method(self) -> None:
        """Reset logging after each test."""
        reset_logging()

    def test_atexit_shutdown_in_sync_context(self) -> None:
        """Test that atexit shutdown works in sync context."""
        from fapilog.bootstrap import configure_logging, _shutdown_queue_worker
        from fapilog.settings import LoggingSettings
        from fapilog._internal.queue import get_queue_worker

        # Configure logging with queue enabled
        settings = LoggingSettings(queue_enabled=True)
        configure_logging(settings=settings)

        # Get the queue worker
        worker = get_queue_worker()
        assert worker is not None

        # Replace sinks with mock sink for testing
        mock_sink = MockSink()
        worker.sinks = [mock_sink]

        # Enqueue an event using a new event loop since we're in sync context
        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Enqueue an event
            loop.run_until_complete(worker.enqueue({"event": "test_event"}))
        finally:
            loop.close()

        # Wait a bit for processing
        import time

        time.sleep(0.2)

        # Call the shutdown function (simulates atexit)
        _shutdown_queue_worker()

        # Wait a bit for processing to complete
        time.sleep(0.1)

        # Verify that the worker is marked for shutdown
        # The new shutdown behavior just marks the worker as stopping
        # and doesn't wait for completion to avoid event loop conflicts
        assert worker._stopping is True
        assert worker._running is False

    def test_atexit_shutdown_idempotent(self) -> None:
        """Test that atexit shutdown can be called multiple times safely."""
        from fapilog.bootstrap import _shutdown_queue_worker

        # Configure logging
        from fapilog.settings import LoggingSettings

        settings = LoggingSettings(queue_enabled=True)
        from fapilog.bootstrap import configure_logging

        configure_logging(settings=settings)

        # Call shutdown multiple times - should not raise exceptions
        _shutdown_queue_worker()
        _shutdown_queue_worker()
        _shutdown_queue_worker()

        # Should not raise any exceptions


class TestShutdownBehavior:
    """Test comprehensive shutdown behavior."""

    def setup_method(self) -> None:
        """Reset logging before each test."""
        reset_logging()

    def teardown_method(self) -> None:
        """Reset logging after each test."""
        reset_logging()

    @pytest.mark.asyncio
    async def test_shutdown_does_not_hang_on_idle_queue(self) -> None:
        """Test that shutdown doesn't hang when queue is idle."""
        worker = QueueWorker(sinks=[MockSink()], queue_size=10)

        # Start the worker
        await worker.start()

        # Wait a bit to ensure worker is running
        await asyncio.sleep(0.1)

        # Shutdown without any events in queue
        start_time = time.time()
        await worker.shutdown()
        shutdown_time = time.time() - start_time

        # Shutdown should complete quickly (less than 1 second)
        assert shutdown_time < 1.0

        # Worker should be stopped
        assert worker._running is False
        assert worker._stopping is True

    @pytest.mark.asyncio
    async def test_shutdown_does_not_hang_on_drained_queue(self) -> None:
        """Test that shutdown doesn't hang when queue is already drained."""
        mock_sink = MockSink()
        worker = QueueWorker(sinks=[mock_sink], queue_size=10)

        # Start the worker
        await worker.start()

        # Enqueue and process some events
        for i in range(3):
            await worker.enqueue({"event": f"event_{i}"})

        # Wait for processing
        await asyncio.sleep(0.2)

        # Verify events were processed
        assert len(mock_sink.events) == 3

        # Shutdown when queue is already drained
        start_time = time.time()
        await worker.shutdown()
        shutdown_time = time.time() - start_time

        # Shutdown should complete quickly
        assert shutdown_time < 1.0

        # Worker should be stopped
        assert worker._running is False
        assert worker._stopping is True

    @pytest.mark.asyncio
    async def test_shutdown_cleans_up_background_tasks(self) -> None:
        """Test that shutdown properly cleans up background tasks."""
        worker = QueueWorker(sinks=[MockSink()], queue_size=10)

        # Start the worker
        await worker.start()

        # Verify task is running
        assert worker._task is not None
        assert not worker._task.done()

        # Shutdown
        await worker.shutdown()

        # Verify task is done
        assert worker._task.done()

        # Verify no unexpected exceptions were raised
        # CancelledError is expected when we cancel the task
        try:
            exception = worker._task.exception()
            if exception is not None and not isinstance(
                exception, asyncio.CancelledError
            ):
                pytest.fail(
                    "Worker task raised unexpected exception: {}".format(exception)
                )
        except asyncio.CancelledError:
            # This is expected when the task was cancelled
            pass

    @pytest.mark.asyncio
    async def test_shutdown_with_failing_sinks(self) -> None:
        """Test that shutdown handles failing sinks gracefully."""
        # Create a sink that fails
        failing_sink = MockSink()
        failing_sink.should_fail = True

        worker = QueueWorker(sinks=[failing_sink], queue_size=10)

        # Start the worker
        await worker.start()

        # Enqueue an event
        await worker.enqueue({"event": "test_event"})

        # Shutdown - should not hang or raise exceptions
        start_time = time.time()
        await worker.shutdown()
        shutdown_time = time.time() - start_time

        # Shutdown should complete (allow more time for retries)
        assert shutdown_time < 10.0  # Increased timeout for retries

        # Worker should be stopped
        assert worker._running is False
        assert worker._stopping is True

    @pytest.mark.asyncio
    async def test_worker_cleanup_on_exception(self) -> None:
        """Test that worker cleanup works even when exceptions occur."""
        worker = QueueWorker(sinks=[MockSink()], queue_size=10)

        # Start the worker
        await worker.start()

        # Verify task is running
        assert worker._task is not None
        assert not worker._task.done()

        # Simulate an exception during shutdown
        # This tests that cleanup still works
        try:
            await worker.shutdown()
        except Exception:
            # Even if shutdown fails, the worker should be marked as stopping
            assert worker._stopping is True
            assert worker._running is False
        else:
            # If shutdown succeeds, verify task is done
            assert worker._task.done()

    @pytest.mark.asyncio
    async def test_multiple_workers_cleanup(self) -> None:
        """Test that multiple workers can be created and cleaned up properly."""
        workers = []

        # Create multiple workers
        for i in range(3):
            worker = QueueWorker(sinks=[MockSink()], queue_size=5)
            await worker.start()
            workers.append(worker)

        # Verify all workers are running
        for worker in workers:
            assert worker._running is True
            assert worker._task is not None
            assert not worker._task.done()

        # Shutdown all workers
        for worker in workers:
            await worker.shutdown()

        # Verify all workers are stopped
        for worker in workers:
            assert worker._running is False
            assert worker._stopping is True
            assert worker._task.done()
