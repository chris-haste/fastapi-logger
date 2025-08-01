"""Comprehensive tests for queue integration to improve coverage."""

import asyncio
from unittest.mock import Mock, patch

import pytest
import structlog

from fapilog._internal.queue_integration import create_queue_sink, queue_sink
from fapilog._internal.queue_worker import QueueWorker
from fapilog.container import LoggingContainer
from fapilog.settings import LoggingSettings


class MockQueueWorker:
    """Mock queue worker for testing various scenarios."""

    def __init__(
        self,
        running=True,
        stopping=False,
        overflow_strategy="drop",
        sampling_rate=1.0,
        queue_full=False,
    ):
        self._running = running
        self._stopping = stopping
        self.overflow_strategy = overflow_strategy
        self.sampling_rate = sampling_rate
        self.queue = Mock()

        if queue_full:
            self.queue.put_nowait.side_effect = asyncio.QueueFull()
        else:
            self.queue.put_nowait.return_value = None

    async def start(self):
        """Mock start method."""
        pass


class TestCreateQueueSink:
    """Test suite for create_queue_sink function."""

    def test_create_queue_sink_none_container(self):
        """Test create_queue_sink when container is None."""
        # Create queue sink with None container
        queue_sink_func = create_queue_sink(None)

        # Test event dict
        event_dict = {"level": "info", "event": "test_message"}

        # Should return event_dict when container is None (line 54)
        result = queue_sink_func(Mock(), "info", event_dict)
        assert result == event_dict

    def test_create_queue_sink_no_queue_worker(self):
        """Test create_queue_sink when container has no queue_worker."""
        # Create mock container without queue_worker
        container = Mock()
        container.queue_worker = None

        queue_sink_func = create_queue_sink(container)
        event_dict = {"level": "info", "event": "test_message"}

        # Should return event_dict when worker is None (line 59)
        result = queue_sink_func(Mock(), "info", event_dict)
        assert result == event_dict

    def test_create_queue_sink_worker_stopping(self):
        """Test create_queue_sink when worker is stopping."""
        # Create container with stopping worker
        container = Mock()
        container.queue_worker = MockQueueWorker(stopping=True)

        queue_sink_func = create_queue_sink(container)
        event_dict = {"level": "info", "event": "test_message"}

        # Should raise DropEvent when worker is stopping (line 67)
        with pytest.raises(structlog.DropEvent):
            queue_sink_func(Mock(), "info", event_dict)

    def test_create_queue_sink_no_running_loop_start_worker(self):
        """Test create_queue_sink when worker needs starting but no running loop."""
        container = Mock()
        container.queue_worker = MockQueueWorker(running=False, stopping=False)

        queue_sink_func = create_queue_sink(container)
        event_dict = {"level": "info", "event": "test_message"}

        # Mock RuntimeError when getting running loop
        with patch(
            "asyncio.get_running_loop", side_effect=RuntimeError("No running loop")
        ):
            # Should raise DropEvent when no running loop (line 84)
            with pytest.raises(structlog.DropEvent):
                queue_sink_func(Mock(), "info", event_dict)

    def test_create_queue_sink_closed_event_loop(self):
        """Test create_queue_sink when event loop is closed."""
        container = Mock()
        container.queue_worker = MockQueueWorker(running=False, stopping=False)

        queue_sink_func = create_queue_sink(container)
        event_dict = {"level": "info", "event": "test_message"}

        # Mock closed event loop
        mock_loop = Mock()
        mock_loop.is_closed.return_value = True

        with patch("asyncio.get_running_loop", return_value=mock_loop):
            # Should raise DropEvent when loop is closed (line 80)
            with pytest.raises(structlog.DropEvent):
                queue_sink_func(Mock(), "info", event_dict)

    def test_create_queue_sink_exception_during_startup(self):
        """Test create_queue_sink when exception occurs during worker startup."""
        container = Mock()
        mock_worker = MockQueueWorker(running=False, stopping=False)

        # Make start() raise an exception
        async def failing_start():
            raise RuntimeError("Startup failed")

        mock_worker.start = failing_start
        container.queue_worker = mock_worker

        queue_sink_func = create_queue_sink(container)
        event_dict = {"level": "info", "event": "test_message"}

        # Mock running loop
        mock_loop = Mock()
        mock_loop.is_closed.return_value = False
        mock_loop.create_task.side_effect = RuntimeError("Task creation failed")

        with patch("asyncio.get_running_loop", return_value=mock_loop):
            # Should raise DropEvent when exception during startup (line 87)
            with pytest.raises(structlog.DropEvent):
                queue_sink_func(Mock(), "info", event_dict)

    def test_create_queue_sink_drop_strategy_success(self):
        """Test create_queue_sink with drop strategy - successful enqueue."""
        container = Mock()
        container.queue_worker = MockQueueWorker(
            overflow_strategy="drop", queue_full=False
        )

        queue_sink_func = create_queue_sink(container)
        event_dict = {"level": "info", "event": "test_message"}

        # Should raise DropEvent after successful enqueue with drop strategy
        with pytest.raises(structlog.DropEvent):
            queue_sink_func(Mock(), "info", event_dict)

        # Verify enqueue was attempted
        container.queue_worker.queue.put_nowait.assert_called_once_with(event_dict)

    def test_create_queue_sink_drop_strategy_queue_full(self):
        """Test create_queue_sink with drop strategy - queue full."""
        container = Mock()
        container.queue_worker = MockQueueWorker(
            overflow_strategy="drop", queue_full=True
        )

        queue_sink_func = create_queue_sink(container)
        event_dict = {"level": "info", "event": "test_message"}

        # Should raise DropEvent when queue is full with drop strategy (line 96)
        with pytest.raises(structlog.DropEvent):
            queue_sink_func(Mock(), "info", event_dict)

    def test_create_queue_sink_block_strategy_success(self):
        """Test create_queue_sink with block strategy - successful enqueue."""
        container = Mock()
        container.queue_worker = MockQueueWorker(
            overflow_strategy="block", queue_full=False
        )

        queue_sink_func = create_queue_sink(container)
        event_dict = {"level": "info", "event": "test_message"}

        # Should raise DropEvent after successful enqueue with block strategy
        with pytest.raises(structlog.DropEvent):
            queue_sink_func(Mock(), "info", event_dict)

    def test_create_queue_sink_block_strategy_queue_full(self):
        """Test create_queue_sink with block strategy - queue full."""
        container = Mock()
        container.queue_worker = MockQueueWorker(
            overflow_strategy="block", queue_full=True
        )

        queue_sink_func = create_queue_sink(container)
        event_dict = {"level": "info", "event": "test_message"}

        # Should raise DropEvent when queue is full with block strategy (lines 102-103)
        with pytest.raises(structlog.DropEvent):
            queue_sink_func(Mock(), "info", event_dict)

    def test_create_queue_sink_sample_strategy_sampled_out(self):
        """Test create_queue_sink with sample strategy - event sampled out."""
        container = Mock()
        container.queue_worker = MockQueueWorker(
            overflow_strategy="sample", sampling_rate=0.5, queue_full=False
        )

        queue_sink_func = create_queue_sink(container)
        event_dict = {"level": "info", "event": "test_message"}

        # Mock random to return value > sampling_rate
        with patch("fapilog._internal.queue_integration.rnd.random", return_value=0.8):
            # Should raise DropEvent when sampled out (line 108)
            with pytest.raises(structlog.DropEvent):
                queue_sink_func(Mock(), "info", event_dict)

        # Queue should not have been called
        container.queue_worker.queue.put_nowait.assert_not_called()

    def test_create_queue_sink_sample_strategy_success(self):
        """Test create_queue_sink with sample strategy - successful enqueue."""
        container = Mock()
        container.queue_worker = MockQueueWorker(
            overflow_strategy="sample", sampling_rate=0.5, queue_full=False
        )

        queue_sink_func = create_queue_sink(container)
        event_dict = {"level": "info", "event": "test_message"}

        # Mock random to return value < sampling_rate
        with patch("fapilog._internal.queue_integration.rnd.random", return_value=0.3):
            # Should raise DropEvent after successful enqueue
            with pytest.raises(structlog.DropEvent):
                queue_sink_func(Mock(), "info", event_dict)

        # Verify enqueue was attempted
        container.queue_worker.queue.put_nowait.assert_called_once_with(event_dict)

    def test_create_queue_sink_sample_strategy_queue_full(self):
        """Test create_queue_sink with sample strategy - queue full."""
        container = Mock()
        container.queue_worker = MockQueueWorker(
            overflow_strategy="sample", sampling_rate=0.5, queue_full=True
        )

        queue_sink_func = create_queue_sink(container)
        event_dict = {"level": "info", "event": "test_message"}

        # Mock random to return value < sampling_rate
        with patch("fapilog._internal.queue_integration.rnd.random", return_value=0.3):
            # Should raise DropEvent when queue is full with sample strategy (lines 112-113)
            with pytest.raises(structlog.DropEvent):
                queue_sink_func(Mock(), "info", event_dict)

    def test_create_queue_sink_worker_start_success(self):
        """Test successful worker start scenario."""
        container = Mock()
        container.queue_worker = MockQueueWorker(
            running=False, stopping=False, overflow_strategy="drop"
        )

        queue_sink_func = create_queue_sink(container)
        event_dict = {"level": "info", "event": "test_message"}

        # Mock running loop and successful task creation
        mock_loop = Mock()
        mock_loop.is_closed.return_value = False
        mock_task = Mock()
        mock_loop.create_task.return_value = mock_task

        with patch("asyncio.get_running_loop", return_value=mock_loop):
            # Should successfully start worker and then enqueue
            with pytest.raises(structlog.DropEvent):
                queue_sink_func(Mock(), "info", event_dict)

        # Verify worker start was called and event was enqueued
        mock_loop.create_task.assert_called_once()
        container.queue_worker.queue.put_nowait.assert_called_once_with(event_dict)


class TestLegacyQueueSink:
    """Test suite for legacy queue_sink function."""

    def test_legacy_queue_sink_returns_event_dict(self):
        """Test that legacy queue_sink returns event_dict and logs warning."""
        event_dict = {"level": "info", "event": "test_message"}
        mock_logger = Mock()

        # Call legacy queue_sink function (lines 137-141)
        result = queue_sink(mock_logger, "info", event_dict)

        # Should return the event_dict unchanged
        assert result == event_dict

        # Should log a warning
        mock_logger.warning.assert_called_once_with(
            "Legacy queue_sink function called - queue functionality disabled during transition",
            event_dict=event_dict,
        )

    def test_legacy_queue_sink_different_levels(self):
        """Test legacy queue_sink with different log levels."""
        test_cases = [
            ("debug", {"level": "debug", "event": "debug_message"}),
            ("error", {"level": "error", "event": "error_message"}),
            ("warning", {"level": "warning", "event": "warning_message"}),
        ]

        for method_name, event_dict in test_cases:
            mock_logger = Mock()
            result = queue_sink(mock_logger, method_name, event_dict)

            assert result == event_dict
            mock_logger.warning.assert_called_once()


class TestQueueIntegrationEdgeCases:
    """Test edge cases and integration scenarios."""

    def test_container_with_actual_queue_worker(self):
        """Test create_queue_sink with actual QueueWorker instance."""
        # Create real container with queue enabled
        settings = LoggingSettings(level="INFO", sinks=["stdout"])
        settings.queue.enabled = True
        settings.queue.maxsize = 5

        container = LoggingContainer.create_from_settings(settings)
        container.configure()

        # Verify we have a real queue worker
        assert container.queue_worker is not None
        assert isinstance(container.queue_worker, QueueWorker)

        # Create queue sink
        queue_sink_func = create_queue_sink(container)
        event_dict = {"level": "info", "event": "integration_test"}

        # Should work with real QueueWorker
        with pytest.raises(structlog.DropEvent):
            queue_sink_func(Mock(), "info", event_dict)

    def test_create_queue_sink_with_hasattr_fallback(self):
        """Test create_queue_sink when container lacks queue_worker attribute."""
        # Create container without queue_worker attribute
        container = Mock(spec=[])  # Empty spec means no attributes

        queue_sink_func = create_queue_sink(container)
        event_dict = {"level": "info", "event": "test_message"}

        # Should return event_dict when queue_worker attribute doesn't exist
        result = queue_sink_func(Mock(), "info", event_dict)
        assert result == event_dict
