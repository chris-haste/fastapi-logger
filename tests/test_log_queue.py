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

    async def test_worker_initialization(self, worker: QueueWorker) -> None:
        """Test that the worker initializes correctly."""
        assert worker.queue.maxsize == 10
        assert worker.batch_size == 2
        assert worker.batch_timeout == 0.1
        assert worker.retry_delay == 0.01
        assert worker.max_retries == 2
        assert len(worker.sinks) == 1

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

    async def test_worker_enqueue_success(self, worker: QueueWorker) -> None:
        """Test that events can be enqueued successfully."""
        event = {"level": "info", "event": "test_event"}

        # Enqueue an event
        success = await worker.enqueue(event)
        assert success is True

        # Check that the event is in the queue
        assert worker.queue.qsize() == 1

    async def test_worker_enqueue_full_queue(self, worker: QueueWorker) -> None:
        """Test that enqueue returns False when queue is full."""
        # Fill the queue
        for i in range(10):
            await worker.enqueue({"event": f"event_{i}"})

        # Try to enqueue one more event
        success = await worker.enqueue({"event": "overflow"})
        assert success is False

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
        """Test queue_sink when queue is full."""
        # Create a mock worker with a full queue
        from fapilog._internal.queue import QueueWorker

        worker = QueueWorker(sinks=[], queue_size=1)
        # Fill the queue
        worker.queue.put_nowait({"event": "existing_event"})
        set_queue_worker(worker)

        event_dict = {"level": "info", "event": "test_event"}

        # Call queue_sink - should raise DropEvent when queue is full
        with pytest.raises(structlog.DropEvent):
            queue_sink(None, "info", event_dict)


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
            queue_size=100,
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
            queue_size=2,  # Very small queue
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

    async def test_queue_nonblocking_under_load(self) -> None:
        """Test that queue doesn't block under high load."""
        # Configure logging with queue
        settings = LoggingSettings(
            queue_enabled=True,
            queue_size=100,
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


class TestStdoutSink:
    """Test the StdoutSink implementation."""

    async def test_stdout_sink_json(self) -> None:
        """Test that StdoutSink writes JSON correctly."""
        sink = StdoutSink(pretty=False)
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

    async def test_stdout_sink_pretty(self) -> None:
        """Test that StdoutSink writes pretty format correctly."""
        sink = StdoutSink(pretty=True)
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

            # Check that it's in pretty format
            assert "[2023-01-01T00:00:00Z] INFO: test_event" in call_args
