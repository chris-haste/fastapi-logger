"""Additional tests to boost queue.py coverage for uncovered lines."""

import asyncio
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest
import structlog

from fapilog._internal.queue_integration import queue_sink, queue_sink_async
from fapilog._internal.queue_worker import QueueWorker
from fapilog.container import set_current_container
from fapilog.exceptions import QueueError
from fapilog.sinks import Sink


class FailingSink(Sink):
    """A sink that always fails for testing error paths."""

    def __init__(self, fail_with: Exception = None):
        super().__init__()
        self.fail_with = fail_with or Exception("Test sink failure")
        self.write_count = 0

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Always fails to test error handling."""
        self.write_count += 1
        raise self.fail_with


class MetricsTestSink(Sink):
    """A sink for testing metrics recording during exceptions."""

    def __init__(self, should_fail: bool = False):
        super().__init__()
        self.should_fail = should_fail
        self.events = []

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Write or fail based on should_fail flag."""
        if self.should_fail:
            raise ValueError("Metrics test failure")
        self.events.append(event_dict)


class TestSinkMetricsOnException:
    """Test Sink._write_with_metrics exception handling (lines 38-52)."""

    @pytest.mark.asyncio
    async def test_write_with_metrics_records_failure(self):
        """Test that _write_with_metrics records metrics on failure."""
        sink = MetricsTestSink(should_fail=True)

        # Mock metrics collector
        mock_path = "fapilog.sinks.base.get_metrics_collector"
        with patch(mock_path) as mock_get_metrics:
            mock_metrics = Mock()
            mock_get_metrics.return_value = mock_metrics

            # Test that exception is propagated and metrics are recorded
            with pytest.raises(ValueError, match="Metrics test failure"):
                await sink._write_with_metrics({"test": "event"})

            # Verify metrics were recorded with failure
            mock_metrics.record_sink_write.assert_called_once()
            call_args = mock_metrics.record_sink_write.call_args
            assert call_args[1]["sink_name"] == "MetricsTestSink"
            assert call_args[1]["success"] is False
            assert call_args[1]["error"] == "Metrics test failure"
            assert call_args[1]["batch_size"] == 1
            assert "latency_ms" in call_args[1]

    @pytest.mark.asyncio
    async def test_write_with_metrics_no_metrics_collector(self):
        """Test _write_with_metrics when no metrics collector available."""
        sink = MetricsTestSink(should_fail=True)

        # Mock no metrics collector
        mock_path = "fapilog._internal.queue_worker.get_metrics_collector"
        with patch(mock_path, return_value=None):
            # Should still propagate exception even without metrics
            with pytest.raises(ValueError, match="Metrics test failure"):
                await sink._write_with_metrics({"test": "event"})


class TestQueueWorkerShutdownEdgeCases:
    """Test QueueWorker shutdown edge cases (lines 214-238 and others)."""

    @pytest.mark.asyncio
    async def test_shutdown_sync_already_stopping(self):
        """Test shutdown_sync when already stopping."""
        worker = QueueWorker(sinks=[MetricsTestSink()])
        worker._stopping = True

        # Should return early without doing anything
        worker.shutdown_sync()
        assert worker._stopping is True

    @pytest.mark.asyncio
    async def test_shutdown_sync_no_task(self):
        """Test shutdown_sync when no task exists."""
        worker = QueueWorker(sinks=[MetricsTestSink()])
        worker._task = None

        # Should handle gracefully
        worker.shutdown_sync()
        assert worker._stopping is True
        assert worker._running is False

    @pytest.mark.asyncio
    async def test_shutdown_sync_task_already_done(self):
        """Test shutdown_sync when task is already done."""
        worker = QueueWorker(sinks=[MetricsTestSink()])

        # Create a done task
        async def dummy():
            pass

        worker._task = asyncio.create_task(dummy())
        await worker._task  # Make it done

        worker.shutdown_sync()
        assert worker._stopping is True
        assert worker._running is False

    @pytest.mark.asyncio
    async def test_shutdown_sync_different_event_loop(self):
        """Test shutdown_sync from different event loop context."""
        worker = QueueWorker(sinks=[MetricsTestSink()])

        # Start worker in current loop
        await worker.start()
        current_loop = asyncio.get_running_loop()
        worker._loop = current_loop

        # Mock being in a different loop
        with patch("asyncio.get_running_loop", side_effect=RuntimeError("No loop")):
            worker.shutdown_sync()

        assert worker._stopping is True
        assert worker._running is False

    @pytest.mark.asyncio
    async def test_shutdown_sync_with_timeout_error(self):
        """Test shutdown_sync with task timeout during cleanup."""
        worker = QueueWorker(sinks=[MetricsTestSink()])

        # Create a long-running task
        async def long_task():
            await asyncio.sleep(10)

        worker._task = asyncio.create_task(long_task())
        worker._loop = None  # Trigger different loop path

        # Mock the temporary event loop to timeout
        with patch("asyncio.new_event_loop") as mock_new_loop:
            mock_loop = Mock()
            mock_new_loop.return_value = mock_loop
            mock_loop.run_until_complete.side_effect = asyncio.TimeoutError()

            worker.shutdown_sync(timeout=0.1)

        assert worker._stopping is True

    @pytest.mark.asyncio
    async def test_shutdown_different_loop_debug_path(self):
        """Test shutdown when worker loop differs from current loop."""
        worker = QueueWorker(sinks=[MetricsTestSink()])
        await worker.start()

        # Mock being in different loop
        original_loop = worker._loop
        different_loop = Mock()
        worker._loop = different_loop

        with patch("asyncio.get_running_loop", return_value=original_loop):
            await worker.shutdown()

        assert worker._stopping is True


class TestEnqueueExceptionHandling:
    """Test enqueue method exception handling (lines 459-466, 497)."""

    @pytest.mark.asyncio
    async def test_enqueue_unexpected_error_drop_strategy(self):
        """Test enqueue with unexpected error in drop strategy."""
        worker = QueueWorker(sinks=[MetricsTestSink()], overflow_strategy="drop")

        # Mock queue to raise unexpected error
        error_msg = "Unexpected error"
        with patch.object(
            worker.queue, "put_nowait", side_effect=RuntimeError(error_msg)
        ):
            with pytest.raises(QueueError) as exc_info:
                await worker.enqueue({"test": "event"})

            assert "enqueue" in str(exc_info.value)
            assert "queue_state" in exc_info.value.context

    @pytest.mark.asyncio
    async def test_enqueue_unexpected_error_block_strategy(self):
        """Test enqueue with unexpected error in block strategy."""
        worker = QueueWorker(sinks=[MetricsTestSink()], overflow_strategy="block")

        # Mock queue to raise unexpected error
        error_msg = "Unexpected error"
        with patch.object(worker.queue, "put", side_effect=RuntimeError(error_msg)):
            with pytest.raises(QueueError) as exc_info:
                await worker.enqueue({"test": "event"})

            assert "enqueue" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_enqueue_unexpected_error_sample_strategy(self):
        """Test enqueue with unexpected error in sample strategy."""
        worker = QueueWorker(sinks=[MetricsTestSink()], overflow_strategy="sample")

        # Mock queue to raise unexpected error
        error_msg = "Unexpected error"
        with patch.object(
            worker.queue, "put_nowait", side_effect=RuntimeError(error_msg)
        ):
            with pytest.raises(QueueError) as exc_info:
                await worker.enqueue({"test": "event"})

            assert "enqueue" in str(exc_info.value)


class TestProcessEventExceptionHandling:
    """Test _process_event exception handling."""

    @pytest.mark.asyncio
    async def test_process_event_individual_sink_failure_logging(self):
        """Test individual sink failure logging in _process_event."""
        good_sink = MetricsTestSink()
        bad_sink = FailingSink(ValueError("Sink failure"))
        worker = QueueWorker(sinks=[good_sink, bad_sink])

        mock_path = "fapilog._internal.queue_worker.log_error_with_context"
        with patch(mock_path) as mock_log_error:
            with pytest.raises(QueueError):
                await worker._process_event({"test": "event"})

            # Should log individual sink failures
            mock_log_error.assert_called()
            call_args = mock_log_error.call_args
            assert isinstance(call_args[0][0], ValueError)
            assert call_args[0][1]["sink_index"] == 1
            assert call_args[0][1]["sink_type"] == "FailingSink"

    @pytest.mark.asyncio
    async def test_process_event_handles_queue_error_from_retry(self):
        """Test _process_event handles QueueError from retry logic."""
        failing_sink = FailingSink()
        worker = QueueWorker(sinks=[failing_sink], max_retries=1, retry_delay=0.01)

        mock_path = "fapilog._internal.queue_worker.handle_queue_error"
        with patch(mock_path, side_effect=QueueError("Retry failed")):
            with pytest.raises(QueueError, match="Retry failed"):
                await worker._process_event({"test": "event"})

    @pytest.mark.asyncio
    async def test_process_event_final_failure_context(self):
        """Test _process_event final failure includes queue state context."""
        failing_sink = FailingSink()
        worker = QueueWorker(sinks=[failing_sink], max_retries=0)

        # Add an event to the queue first
        await worker.enqueue({"other": "event"})

        with pytest.raises(QueueError) as exc_info:
            await worker._process_event({"test": "event"})

        # Should include queue state in final error
        context = exc_info.value.context
        assert "queue_state" in context
        queue_state = context["queue_state"]
        assert "queue_size" in queue_state
        assert "max_retries" in queue_state
        assert "total_sinks" in queue_state
        assert queue_state["max_retries"] == 0


class TestQueueSinkEdgeCases:
    """Test queue_sink function edge cases (lines 525, 534, 539)."""

    def setup_method(self):
        """Clear container before each test."""
        set_current_container(None)

    def test_queue_sink_no_container(self):
        """Test queue_sink when no container is available."""
        result = queue_sink(Mock(), "info", {"test": "event"})
        # Should return event_dict for further processing
        assert result == {"test": "event"}

    def test_queue_sink_no_queue_worker(self):
        """Test queue_sink when container has no queue worker."""
        container = Mock()
        container.queue_worker = None
        set_current_container(container)

        result = queue_sink(Mock(), "info", {"test": "event"})
        # Should return event_dict for further processing
        assert result == {"test": "event"}

    def test_queue_sink_worker_stopping(self):
        """Test queue_sink when worker is stopping."""
        container = Mock()
        worker = Mock()
        worker._stopping = True
        container.queue_worker = worker
        set_current_container(container)

        # Should drop event (raise DropEvent)
        with pytest.raises(structlog.DropEvent):
            queue_sink(Mock(), "info", {"test": "event"})

    def test_queue_sink_no_running_loop(self):
        """Test queue_sink when no event loop is running."""
        container = Mock()
        worker = Mock()
        worker._stopping = False
        worker._running = False
        container.queue_worker = worker
        set_current_container(container)

        with patch("asyncio.get_running_loop", side_effect=RuntimeError("No loop")):
            with pytest.raises(structlog.DropEvent):
                queue_sink(Mock(), "info", {"test": "event"})

    def test_queue_sink_closed_event_loop(self):
        """Test queue_sink when event loop is closed."""
        container = Mock()
        worker = Mock()
        worker._stopping = False
        worker._running = False
        container.queue_worker = worker
        set_current_container(container)

        mock_loop = Mock()
        mock_loop.is_closed.return_value = True

        with patch("asyncio.get_running_loop", return_value=mock_loop):
            with pytest.raises(structlog.DropEvent):
                queue_sink(Mock(), "info", {"test": "event"})

    def test_queue_sink_startup_exception(self):
        """Test queue_sink when worker startup raises exception."""
        container = Mock()
        worker = Mock()
        worker._stopping = False
        worker._running = False
        container.queue_worker = worker
        set_current_container(container)

        mock_loop = Mock()
        mock_loop.is_closed.return_value = False
        mock_loop.create_task.side_effect = Exception("Startup failed")

        with patch("asyncio.get_running_loop", return_value=mock_loop):
            with pytest.raises(structlog.DropEvent):
                queue_sink(Mock(), "info", {"test": "event"})


class TestQueueSinkAsyncEdgeCases:
    """Test queue_sink_async function edge cases (lines 567, 575)."""

    def setup_method(self):
        """Clear container before each test."""
        set_current_container(None)

    @pytest.mark.asyncio
    async def test_queue_sink_async_no_container(self):
        """Test queue_sink_async when no container is available."""
        result = await queue_sink_async(Mock(), "info", {"test": "event"})
        # Should return event_dict for further processing
        assert result == {"test": "event"}

    @pytest.mark.asyncio
    async def test_queue_sink_async_no_queue_worker(self):
        """Test queue_sink_async when container has no queue worker."""
        container = Mock()
        container.queue_worker = None
        set_current_container(container)

        result = await queue_sink_async(Mock(), "info", {"test": "event"})
        # Should return event_dict for further processing
        assert result == {"test": "event"}

    @pytest.mark.asyncio
    async def test_queue_sink_async_enqueue_failed(self):
        """Test queue_sink_async when enqueue fails."""
        container = Mock()
        worker = AsyncMock()
        worker.enqueue.return_value = False
        container.queue_worker = worker
        set_current_container(container)

        result = await queue_sink_async(Mock(), "info", {"test": "event"})
        # Should return None when enqueue fails
        assert result is None

    @pytest.mark.asyncio
    async def test_queue_sink_async_enqueue_success(self):
        """Test queue_sink_async when enqueue succeeds."""
        container = Mock()
        worker = AsyncMock()
        worker.enqueue.return_value = True
        container.queue_worker = worker
        set_current_container(container)

        result = await queue_sink_async(Mock(), "info", {"test": "event"})
        # Should return None to prevent further processing
        assert result is None


class TestOverflowStrategySampling:
    """Test sampling in queue_sink for different overflow strategies."""

    def setup_method(self):
        """Clear container before each test."""
        set_current_container(None)

    def test_queue_sink_sample_strategy_sampling(self):
        """Test queue_sink sample strategy applies sampling."""
        container = Mock()
        worker = Mock()
        worker._stopping = False
        worker._running = True
        worker.overflow_strategy = "sample"
        worker.sampling_rate = 0.0  # Always drop
        worker.queue = Mock()
        container.queue_worker = worker
        set_current_container(container)

        with patch("fapilog._internal.queue_integration.rnd.random", return_value=0.5):
            with pytest.raises(structlog.DropEvent):
                queue_sink(Mock(), "info", {"test": "event"})

    def test_queue_sink_block_strategy_queue_full(self):
        """Test queue_sink block strategy when queue is full."""
        container = Mock()
        worker = Mock()
        worker._stopping = False
        worker._running = True
        worker.overflow_strategy = "block"
        worker.queue = Mock()
        worker.queue.put_nowait.side_effect = asyncio.QueueFull()
        container.queue_worker = worker
        set_current_container(container)

        with pytest.raises(structlog.DropEvent):
            queue_sink(Mock(), "info", {"test": "event"})


class TestShutdownSyncRobustness:
    """Test shutdown_sync method robustness for edge cases."""

    def test_shutdown_sync_exception_during_cancel(self):
        """Test shutdown_sync handles exception during task cancellation."""
        worker = QueueWorker(sinks=[MetricsTestSink()])

        # Mock task that raises exception on cancel
        mock_task = Mock()
        mock_task.done.return_value = False
        mock_task.cancel.side_effect = Exception("Cancel failed")
        worker._task = mock_task

        # Should handle exception gracefully
        worker.shutdown_sync()
        assert worker._stopping is True
        assert worker._running is False

    def test_shutdown_sync_loop_creation_failure(self):
        """Test shutdown_sync when event loop creation fails."""
        worker = QueueWorker(sinks=[MetricsTestSink()])

        # Mock a running task instead of creating one
        mock_task = Mock()
        mock_task.done.return_value = False
        worker._task = mock_task
        worker._loop = None

        # Mock event loop creation to fail
        with patch(
            "asyncio.new_event_loop", side_effect=Exception("Loop creation failed")
        ):
            with patch("asyncio.get_running_loop", side_effect=RuntimeError("No loop")):
                worker.shutdown_sync()

        assert worker._stopping is True
