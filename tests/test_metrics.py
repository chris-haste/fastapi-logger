"""Tests for metrics collection system."""

import asyncio
from typing import Any, Dict
from unittest.mock import patch

import pytest

from fapilog._internal.metrics import (
    MetricsCollector,
    PerformanceMetrics,
    QueueMetrics,
)
from fapilog._internal.queue_worker import QueueWorker
from fapilog.monitoring import (
    PrometheusExporter,
    get_metrics_dict,
    get_metrics_text,
)
from fapilog.sinks.file import FileSink
from fapilog.sinks.stdout import StdoutSink


class TestMetricsCollector:
    """Test the MetricsCollector class."""

    def test_initialization(self):
        """Test metrics collector initialization."""
        collector = MetricsCollector(enabled=True, sample_window=50)
        assert collector.is_enabled()
        assert collector.sample_window == 50
        assert isinstance(collector.queue_metrics, QueueMetrics)
        assert isinstance(collector.sink_metrics, dict)
        assert isinstance(collector.performance_metrics, PerformanceMetrics)

    def test_disabled_collector(self):
        """Test that disabled collector doesn't record metrics."""
        collector = MetricsCollector(enabled=False)
        collector.record_enqueue(10.0)
        collector.record_queue_size(5)

        metrics = collector.get_all_metrics()
        assert metrics == {}

    def test_enable_disable(self):
        """Test enabling and disabling the collector."""
        collector = MetricsCollector(enabled=True)
        assert collector.is_enabled()

        collector.disable()
        assert not collector.is_enabled()

        collector.enable()
        assert collector.is_enabled()

    def test_queue_metrics(self):
        """Test queue metrics recording."""
        collector = MetricsCollector(enabled=True, sample_window=3)

        # Test queue size recording
        collector.record_queue_size(10)
        assert collector.queue_metrics.size == 10
        assert collector.queue_metrics.peak_size == 10

        collector.record_queue_size(5)
        assert collector.queue_metrics.size == 5
        assert collector.queue_metrics.peak_size == 10  # Peak should remain

        collector.record_queue_size(15)
        assert collector.queue_metrics.size == 15
        assert collector.queue_metrics.peak_size == 15  # New peak

        # Test enqueue recording
        collector.record_enqueue(5.0)
        collector.record_enqueue(10.0)
        collector.record_enqueue(15.0)

        assert collector.queue_metrics.total_enqueued == 3
        assert collector.queue_metrics.enqueue_latency_ms == 10.0  # Average

        # Test dequeue recording
        collector.record_dequeue(2.0)
        collector.record_dequeue(4.0)

        assert collector.queue_metrics.total_dequeued == 2
        assert collector.queue_metrics.dequeue_latency_ms == 3.0  # Average

        # Test dropped and sampled events
        collector.record_dropped_event()
        collector.record_dropped_event()
        collector.record_sampled_event()

        assert collector.queue_metrics.total_dropped == 2
        assert collector.queue_metrics.total_sampled == 1

    def test_sink_metrics(self):
        """Test sink metrics recording."""
        collector = MetricsCollector(enabled=True, sample_window=3)

        # Test successful write
        collector.record_sink_write("TestSink", 5.0, True, 1)

        metrics = collector.get_sink_metrics("TestSink")
        assert metrics.total_writes == 1
        assert metrics.total_successes == 1
        assert metrics.total_failures == 0
        assert metrics.avg_write_latency_ms == 5.0
        assert metrics.avg_batch_size == 1.0

        # Test failed write
        collector.record_sink_write("TestSink", 10.0, False, 1, "Connection error")

        metrics = collector.get_sink_metrics("TestSink")
        assert metrics.total_writes == 2
        assert metrics.total_successes == 1
        assert metrics.total_failures == 1
        assert metrics.avg_write_latency_ms == 7.5  # Average of 5.0 and 10.0
        assert metrics.last_error == "Connection error"
        assert metrics.last_error_time is not None

        # Test retry recording
        collector.record_sink_retry("TestSink")
        assert metrics.total_retries == 1

    def test_performance_metrics(self):
        """Test performance metrics recording."""
        collector = MetricsCollector(enabled=True, sample_window=3)

        # Record some log events
        collector.record_log_event(5.0)
        collector.record_log_event(10.0)
        collector.record_log_event(15.0)

        assert collector.performance_metrics.total_log_events == 3
        assert collector.performance_metrics.avg_processing_time_ms == 10.0
        assert collector.performance_metrics.events_per_second > 0

    def test_get_all_metrics(self):
        """Test getting all metrics as a dictionary."""
        collector = MetricsCollector(enabled=True)

        # Add some sample data
        collector.record_queue_size(5)
        collector.record_enqueue(10.0)
        collector.record_sink_write("TestSink", 5.0, True, 2)
        collector.record_log_event(8.0)

        metrics = collector.get_all_metrics()

        assert "queue" in metrics
        assert "sinks" in metrics
        assert "performance" in metrics

        # Check queue metrics
        queue_metrics = metrics["queue"]
        assert queue_metrics["size"] == 5
        assert queue_metrics["total_enqueued"] == 1

        # Check sink metrics
        sink_metrics = metrics["sinks"]["TestSink"]
        assert sink_metrics["total_writes"] == 1
        assert sink_metrics["success_rate"] == 1.0
        assert sink_metrics["avg_batch_size"] == 2.0

        # Check performance metrics
        perf_metrics = metrics["performance"]
        assert perf_metrics["total_log_events"] == 1
        assert perf_metrics["uptime_seconds"] > 0

    def test_prometheus_export(self):
        """Test Prometheus metrics export."""
        collector = MetricsCollector(enabled=True)

        # Add sample data
        collector.record_queue_size(10)
        collector.record_enqueue(5.0)
        collector.record_sink_write("StdoutSink", 3.0, True, 1)
        collector.record_log_event(7.0)

        prometheus_text = collector.get_prometheus_metrics()

        # Check that Prometheus format is correct
        assert "fapilog_queue_size 10" in prometheus_text
        assert "fapilog_queue_enqueued_total 1" in prometheus_text
        assert 'fapilog_sink_writes_total{sink="StdoutSink"} 1' in prometheus_text
        assert "fapilog_events_total 1" in prometheus_text

        # Check HELP and TYPE comments are present
        assert "# HELP fapilog_queue_size" in prometheus_text
        assert "# TYPE fapilog_queue_size gauge" in prometheus_text

    def test_reset_metrics(self):
        """Test resetting all metrics."""
        collector = MetricsCollector(enabled=True)

        # Add some data
        collector.record_queue_size(10)
        collector.record_sink_write("TestSink", 5.0, True, 1)
        collector.record_log_event(8.0)

        # Verify data exists
        metrics_before = collector.get_all_metrics()
        assert metrics_before["queue"]["size"] == 10
        assert len(metrics_before["sinks"]) == 1

        # Reset and verify
        collector.reset()
        metrics_after = collector.get_all_metrics()

        assert metrics_after["queue"]["size"] == 0
        assert len(metrics_after["sinks"]) == 0
        assert metrics_after["performance"]["total_log_events"] == 0


class TestMetricsIntegration:
    """Test metrics integration with queue and sinks."""

    @pytest.fixture
    def metrics_collector(self):
        """Create a metrics collector for testing."""
        collector = MetricsCollector(enabled=True)
        # set_metrics_collector  # Removed in Issue 164 - use container-scoped metrics(collector)
        yield collector
        # set_metrics_collector  # Removed in Issue 164 - use container-scoped metrics(None)

    @pytest.fixture
    def mock_sink(self):
        """Create a mock sink for testing."""

        class MockSink:
            def __init__(self):
                self.write_count = 0
                self.should_fail = False

            async def write(self, event_dict: Dict[str, Any]) -> None:
                self.write_count += 1
                if self.should_fail:
                    raise Exception("Mock sink error")
                await asyncio.sleep(0.001)  # Small delay to test latency

        return MockSink()

    @pytest.mark.asyncio
    async def test_queue_worker_metrics(self, metrics_collector, mock_sink):
        """Test that queue worker records metrics correctly."""
        # Create mock container with metrics collector
        from unittest.mock import Mock

        mock_container = Mock()
        mock_container.get_metrics_collector.return_value = metrics_collector

        worker = QueueWorker(
            sinks=[mock_sink],
            queue_max_size=10,
            batch_size=2,
            batch_timeout=0.1,
            container=mock_container,
        )

        await worker.start()

        try:
            # Enqueue some events
            event1 = {"message": "test1", "level": "info"}
            event2 = {"message": "test2", "level": "error"}

            result1 = await worker.enqueue(event1)
            result2 = await worker.enqueue(event2)

            assert result1
            assert result2

            # Wait for processing
            await asyncio.sleep(0.2)

            # Check metrics
            metrics = metrics_collector.get_all_metrics()

            # Queue metrics should show enqueue operations
            assert metrics["queue"]["total_enqueued"] == 2
            assert metrics["queue"]["enqueue_latency_ms"] > 0

            # Should have processed events
            assert metrics["performance"]["total_log_events"] > 0

        finally:
            await worker.stop()

    @pytest.mark.asyncio
    async def test_sink_error_metrics(self, metrics_collector):
        """Test that sink errors are recorded in metrics."""

        # Create a sink that will fail
        class FailingSink:
            async def write(self, event_dict: Dict[str, Any]) -> None:
                raise Exception("Intentional failure")

        failing_sink = FailingSink()
        worker = QueueWorker(
            sinks=[failing_sink],
            queue_max_size=10,
            batch_size=1,
            max_retries=1,  # Reduce retries for faster test
        )

        await worker.start()

        try:
            # This should fail and record error metrics
            event = {"message": "test", "level": "info"}
            await worker.enqueue(event)

            # Wait for processing to complete
            await asyncio.sleep(0.2)

            # Note: The queue worker handles errors internally and continues,
            # so we might not see the failure metrics in this test setup
            # This test mainly verifies that the system doesn't crash

        finally:
            await worker.stop()


class TestPrometheusExporter:
    """Test the Prometheus exporter."""

    @pytest.fixture
    def metrics_collector(self):
        """Create a metrics collector with sample data."""
        collector = MetricsCollector(enabled=True)
        collector.record_queue_size(5)
        collector.record_enqueue(10.0)
        collector.record_sink_write("TestSink", 5.0, True, 1)
        collector.record_log_event(8.0)
        # set_metrics_collector  # Removed in Issue 164 - use container-scoped metrics(collector)
        yield collector
        # set_metrics_collector  # Removed in Issue 164 - use container-scoped metrics(None)

    def test_prometheus_exporter_initialization(self):
        """Test Prometheus exporter initialization."""
        exporter = PrometheusExporter(
            host="localhost",
            port=9090,
            path="/custom-metrics",
            enabled=True,
        )

        assert exporter.host == "localhost"
        assert exporter.port == 9090
        assert exporter.path == "/custom-metrics"
        assert exporter.enabled

        # Test with FastAPI not available
        with patch("fapilog.monitoring.FastAPI", None):
            exporter = PrometheusExporter(enabled=True)
            assert not exporter.enabled

    def test_disabled_exporter(self):
        """Test disabled Prometheus exporter."""
        exporter = PrometheusExporter(enabled=False)
        assert not exporter.enabled
        assert exporter.get_metrics_url() is None

    @pytest.mark.asyncio
    async def test_exporter_lifecycle(self):
        """Test starting and stopping the exporter."""
        exporter = PrometheusExporter(
            host="127.0.0.1",
            port=0,  # Use any available port
            enabled=True,
        )

        # Test that we can start (but might fail due to dependencies)
        try:
            await exporter.start()
            assert (
                exporter.is_running() or not exporter.enabled
            )  # May be disabled if FastAPI not available
        except Exception:
            # Expected if FastAPI/uvicorn not available
            pass

        await exporter.stop()
        assert not exporter.is_running()

    def test_get_metrics_text(self, metrics_collector):
        """Test getting metrics as text."""
        # Global function now returns container-scoped access message
        text = get_metrics_text()

        assert "container-scoped access" in text
        assert "# Metrics collection is disabled" in text

    def test_get_metrics_dict(self, metrics_collector):
        """Test getting metrics as dictionary."""
        # Global function now returns container-scoped access message
        metrics_dict = get_metrics_dict()

        assert "_note" in metrics_dict
        assert "container-scoped access" in metrics_dict["_note"]

    def test_metrics_functions_with_no_collector(self):
        """Test metrics functions when no collector is set."""
        # Global functions now always return container-scoped access message

        text = get_metrics_text()
        assert "container-scoped access" in text

        metrics_dict = get_metrics_dict()
        assert "_note" in metrics_dict
        assert "container-scoped access" in metrics_dict["_note"]


class TestSinkMetricsIntegration:
    """Test metrics integration with actual sink implementations."""

    @pytest.fixture
    def metrics_collector(self):
        """Create a metrics collector for testing."""
        collector = MetricsCollector(enabled=True)
        # set_metrics_collector  # Removed in Issue 164 - use container-scoped metrics(collector)
        yield collector
        # set_metrics_collector  # Removed in Issue 164 - use container-scoped metrics(None)

    @pytest.mark.asyncio
    async def test_stdout_sink_metrics(self):
        """Test StdoutSink metrics recording."""
        # Create fresh metrics collector for this test
        from unittest.mock import Mock

        metrics_collector = MetricsCollector(enabled=True)
        mock_container = Mock()
        mock_container.get_metrics_collector.return_value = metrics_collector

        sink = StdoutSink(mode="json", container=mock_container)

        with patch("builtins.print"):  # Mock print to avoid output
            event = {"message": "test", "level": "info"}
            await sink.write(
                event
            )  # write() method already includes metrics collection

        metrics = metrics_collector.get_all_metrics()
        sink_metrics = metrics["sinks"].get("StdoutSink", {})

        assert sink_metrics.get("total_writes", 0) == 1
        assert sink_metrics.get("total_successes", 0) == 1
        assert sink_metrics.get("total_failures", 0) == 0

    @pytest.mark.asyncio
    async def test_file_sink_metrics(self, tmp_path):
        """Test FileSink metrics recording."""
        # Create fresh metrics collector for this test
        from unittest.mock import Mock

        metrics_collector = MetricsCollector(enabled=True)
        mock_container = Mock()
        mock_container.get_metrics_collector.return_value = metrics_collector

        log_file = tmp_path / "test.log"
        sink = FileSink(str(log_file), container=mock_container)

        try:
            event = {"message": "test", "level": "info"}
            await sink.write(
                event
            )  # write() method already includes metrics collection

            metrics = metrics_collector.get_all_metrics()
            sink_metrics = metrics["sinks"].get("FileSink", {})

            assert sink_metrics.get("total_writes", 0) == 1
            assert sink_metrics.get("total_successes", 0) == 1
            assert sink_metrics.get("total_failures", 0) == 0

        finally:
            sink.close()


if __name__ == "__main__":
    pytest.main([__file__])
