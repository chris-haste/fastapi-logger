"""Tests for processor metrics functionality."""

import threading
import time
from typing import Any, Dict, Optional
from unittest.mock import patch

import pytest

from fapilog._internal.processor_metrics import (
    ProcessorMetrics,
    wrap_processor_with_metrics,
)
from fapilog.monitoring import (
    get_processor_health_status,
    get_processor_performance_stats,
    get_processor_summary,
    reset_processor_metrics,
)
from fapilog.processors.base import Processor


class TestProcessorMetrics:
    """Test ProcessorMetrics class functionality."""

    def test_init(self):
        """Test ProcessorMetrics initialization."""
        metrics = ProcessorMetrics()
        assert metrics._metrics == {}

        # Cross-platform compatible threading.Lock check
        # Some Python versions/environments don't support isinstance(obj, threading.Lock)
        try:
            assert isinstance(metrics._lock, threading.Lock)
        except TypeError:
            # Fallback for environments where threading.Lock is not a direct class
            lock_type = type(threading.Lock())
            assert isinstance(metrics._lock, lock_type)

        # Verify lock functionality
        assert hasattr(metrics._lock, "acquire")
        assert hasattr(metrics._lock, "release")

    def test_record_processor_execution_success(self):
        """Test recording successful processor execution."""
        metrics = ProcessorMetrics()

        metrics.record_processor_execution(
            processor_name="TestProcessor",
            latency_ms=50.0,
            success=True,
            event_size_bytes=100,
        )

        stats = metrics.get_processor_stats("TestProcessor")
        assert stats["total_executions"] == 1
        assert stats["successful_executions"] == 1
        assert stats["failed_executions"] == 0
        assert stats["total_latency_ms"] == 50.0
        assert stats["min_latency_ms"] == 50.0
        assert stats["max_latency_ms"] == 50.0
        assert stats["total_bytes_processed"] == 100
        assert stats["success_rate"] == 100.0
        assert stats["failure_rate"] == 0.0
        assert stats["average_latency_ms"] == 50.0
        assert stats["last_execution"] is not None
        assert stats["last_error"] is None

    def test_record_processor_execution_failure(self):
        """Test recording failed processor execution."""
        metrics = ProcessorMetrics()

        metrics.record_processor_execution(
            processor_name="TestProcessor",
            latency_ms=25.0,
            success=False,
            error="Test error",
            event_size_bytes=50,
        )

        stats = metrics.get_processor_stats("TestProcessor")
        assert stats["total_executions"] == 1
        assert stats["successful_executions"] == 0
        assert stats["failed_executions"] == 1
        assert stats["total_latency_ms"] == 25.0
        assert stats["total_bytes_processed"] == 50
        assert stats["success_rate"] == 0.0
        assert stats["failure_rate"] == 100.0
        assert stats["average_latency_ms"] == 25.0
        assert stats["error_counts"]["Test error"] == 1
        assert stats["last_error"] == "Test error"

    def test_record_multiple_executions(self):
        """Test recording multiple processor executions."""
        metrics = ProcessorMetrics()

        # Record successful executions
        metrics.record_processor_execution("TestProcessor", 10.0, True)
        metrics.record_processor_execution("TestProcessor", 20.0, True)
        metrics.record_processor_execution("TestProcessor", 30.0, False, "Error")

        stats = metrics.get_processor_stats("TestProcessor")
        assert stats["total_executions"] == 3
        assert stats["successful_executions"] == 2
        assert stats["failed_executions"] == 1
        assert stats["total_latency_ms"] == 60.0
        assert stats["min_latency_ms"] == 10.0
        assert stats["max_latency_ms"] == 30.0
        assert stats["success_rate"] == pytest.approx(66.67, rel=1e-2)
        assert stats["failure_rate"] == pytest.approx(33.33, rel=1e-2)
        assert stats["average_latency_ms"] == 20.0

    def test_get_processor_stats_nonexistent(self):
        """Test getting stats for non-existent processor."""
        metrics = ProcessorMetrics()
        stats = metrics.get_processor_stats("NonExistent")
        assert stats == {}

    def test_get_all_stats(self):
        """Test getting all processor statistics."""
        metrics = ProcessorMetrics()

        metrics.record_processor_execution("Processor1", 10.0, True)
        metrics.record_processor_execution("Processor2", 20.0, False, "Error")

        all_stats = metrics.get_all_stats()
        assert len(all_stats) == 2
        assert "Processor1" in all_stats
        assert "Processor2" in all_stats
        assert all_stats["Processor1"]["success_rate"] == 100.0
        assert all_stats["Processor2"]["failure_rate"] == 100.0

    def test_reset_stats_specific_processor(self):
        """Test resetting stats for specific processor."""
        metrics = ProcessorMetrics()

        metrics.record_processor_execution("Processor1", 10.0, True)
        metrics.record_processor_execution("Processor2", 20.0, True)

        metrics.reset_stats("Processor1")

        assert metrics.get_processor_stats("Processor1") == {}
        assert metrics.get_processor_stats("Processor2")["total_executions"] == 1

    def test_reset_stats_all_processors(self):
        """Test resetting stats for all processors."""
        metrics = ProcessorMetrics()

        metrics.record_processor_execution("Processor1", 10.0, True)
        metrics.record_processor_execution("Processor2", 20.0, True)

        metrics.reset_stats()

        assert metrics.get_processor_stats("Processor1") == {}
        assert metrics.get_processor_stats("Processor2") == {}
        assert metrics.get_all_stats() == {}

    def test_thread_safety(self):
        """Test thread safety of metrics collection."""
        metrics = ProcessorMetrics()
        errors = []

        def worker():
            try:
                for i in range(100):
                    metrics.record_processor_execution(
                        f"Processor{i % 5}", float(i), i % 2 == 0
                    )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert not errors
        stats = metrics.get_all_stats()
        total_executions = sum(s["total_executions"] for s in stats.values())
        assert total_executions == 1000  # 10 threads * 100 executions

    def test_min_latency_edge_case(self):
        """Test min latency handling with no executions."""
        metrics = ProcessorMetrics()
        stats = metrics.get_processor_stats("EmptyProcessor")
        assert stats == {}

        # Test after creating empty metrics entry
        metrics._metrics["EmptyProcessor"] = {
            "total_executions": 0,
            "min_latency_ms": float("inf"),
            "max_latency_ms": 0.0,
        }
        stats = metrics.get_processor_stats("EmptyProcessor")
        assert stats["min_latency_ms"] == 0.0


class MockProcessor(Processor):
    """Mock processor for testing wrapper functionality."""

    def __init__(self, should_fail: bool = False, delay: float = 0.0) -> None:
        """Initialize mock processor."""
        self.should_fail = should_fail
        self.delay = delay
        super().__init__()

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Mock process method."""
        if self.delay > 0:
            time.sleep(self.delay / 1000)  # Convert ms to seconds

        if self.should_fail:
            raise ValueError("Mock processor error")

        return {"processed": True, **event_dict}


class TestProcessorWrappers:
    """Test processor wrapper functions."""

    def test_wrap_processor_with_metrics_success(self):
        """Test wrapping processor with metrics for successful execution."""
        # Create fresh metrics instance
        metrics = ProcessorMetrics()

        processor = MockProcessor()
        wrapped = wrap_processor_with_metrics(processor, metrics)

        event_dict = {"level": "INFO", "message": "test"}
        result = wrapped(None, "info", event_dict)

        assert result["processed"] is True
        assert result["level"] == "INFO"

        stats = metrics.get_processor_stats("MockProcessor")
        assert stats["total_executions"] == 1
        assert stats["successful_executions"] == 1
        assert stats["success_rate"] == 100.0

    def test_wrap_processor_with_metrics_failure(self):
        """Test wrapping processor with metrics for failed execution."""
        # Create fresh metrics instance
        metrics = ProcessorMetrics()

        processor = MockProcessor(should_fail=True)
        wrapped = wrap_processor_with_metrics(processor, metrics)

        event_dict = {"level": "ERROR", "message": "test"}

        with pytest.raises(ValueError, match="Mock processor error"):
            wrapped(None, "error", event_dict)

        stats = metrics.get_processor_stats("MockProcessor")
        assert stats["total_executions"] == 1
        assert stats["failed_executions"] == 1
        assert stats["failure_rate"] == 100.0
        assert "Mock processor error" in stats["error_counts"]

    def test_event_size_calculation(self):
        """Test event size calculation in metrics."""
        # Create fresh metrics instance
        metrics = ProcessorMetrics()

        processor = MockProcessor()
        wrapped = wrap_processor_with_metrics(processor, metrics)

        event_dict = {"level": "INFO", "message": "test message"}
        wrapped(None, "info", event_dict)

        stats = metrics.get_processor_stats("MockProcessor")
        assert stats["total_bytes_processed"] > 0


class TestMonitoringAPI:
    """Test monitoring API functions."""

    def test_get_processor_performance_stats(self):
        """Test getting processor performance stats (legacy API)."""
        # Since monitoring API now uses per-call instances, it returns empty stats
        # This tests the API still works without errors
        stats = get_processor_performance_stats()
        assert stats == {}  # Empty since using per-call instances

    def test_get_processor_health_status(self):
        """Test getting processor health status (legacy API)."""
        # Since monitoring API now uses per-call instances, it returns empty health
        # This tests the API still works without errors
        health = get_processor_health_status()
        assert health == {}  # Empty since using per-call instances

    def test_get_processor_health_status_unknown(self):
        """Test processor health status for processors with no executions."""
        # Create processor entry but don't record executions
        ProcessorMetrics()
        # This will create an empty entry when we get stats

        health = get_processor_health_status()
        # Should be empty since no processors have been executed
        assert len(health) == 0

    def test_reset_processor_metrics_specific(self):
        """Test resetting specific processor metrics (legacy API)."""
        # Since monitoring API now uses per-call instances, reset has no effect
        # This tests the API still works without errors
        reset_processor_metrics("Processor1")

        stats = get_processor_performance_stats()
        assert stats == {}  # Empty since using per-call instances

    def test_reset_processor_metrics_all(self):
        """Test resetting all processor metrics."""
        metrics = ProcessorMetrics()
        metrics.record_processor_execution("Processor1", 10.0, True)
        metrics.record_processor_execution("Processor2", 20.0, True)

        reset_processor_metrics()

        stats = get_processor_performance_stats()
        assert len(stats) == 0

    def test_get_processor_summary(self):
        """Test getting processor summary (legacy API)."""
        # Since monitoring API now uses per-call instances, it returns default summary
        # This tests the API still works without errors
        summary = get_processor_summary()

        # Should return empty/default summary since using per-call instances
        assert summary["total_processors"] == 0

    def test_get_processor_summary_empty(self):
        """Test getting processor summary with no processors."""
        summary = get_processor_summary()
        assert summary["total_processors"] == 0
        assert summary["summary"] == "No processors tracked"

    @patch("fapilog.monitoring.logger")
    def test_monitoring_api_error_handling(self, mock_logger):
        """Test error handling in monitoring API functions."""
        # Mock ProcessorMetrics to raise an exception
        with patch(
            "fapilog._internal.processor_metrics.ProcessorMetrics"
        ) as mock_metrics:
            mock_metrics.side_effect = Exception("Test error")

            stats = get_processor_performance_stats()
            assert "error" in stats
            assert "Test error" in stats["error"]
            mock_logger.error.assert_called()

    def test_container_scoped_metrics_isolation(self):
        """Test container-scoped metrics isolation."""
        from fapilog.container import LoggingContainer

        # Test that different containers have isolated metrics
        container1 = LoggingContainer()
        container2 = LoggingContainer()

        metrics1 = container1.get_processor_metrics()
        metrics2 = container2.get_processor_metrics()

        # Different containers should have different metrics instances
        assert metrics1 is not metrics2

        # Recording in one should not affect the other
        metrics1.record_processor_execution("TestProcessor", 10.0, True)

        stats1 = metrics1.get_processor_stats("TestProcessor")
        stats2 = metrics2.get_processor_stats("TestProcessor")

        assert stats1["total_executions"] == 1
        assert stats2 == {}  # No stats in metrics2


class MockFastProcessor(Processor):
    """Mock fast processor for testing."""

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        return {"processed": True, **event_dict}


class MockSlowProcessor(Processor):
    """Mock slow processor for testing."""

    def __init__(self, delay: float = 0.05) -> None:
        self.delay = delay
        super().__init__()

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        time.sleep(self.delay)
        return {"processed": True, **event_dict}


class MockFailingProcessor(Processor):
    """Mock failing processor for testing."""

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        raise ValueError("Mock processor error")


class TestIntegration:
    """Integration tests for processor metrics."""

    def test_end_to_end_workflow(self):
        """Test complete end-to-end processor metrics workflow."""
        # Create metrics instance and wrap a processor
        metrics = ProcessorMetrics()
        processor = MockProcessor()
        wrapped = wrap_processor_with_metrics(processor, metrics)

        # Process some events
        for i in range(5):
            event_dict = {"level": "INFO", "message": f"test {i}"}
            wrapped(None, "info", event_dict)

        # Check performance stats directly from metrics instance
        stats = metrics.get_all_stats()
        assert len(stats) == 1
        assert "MockProcessor" in stats
        assert stats["MockProcessor"]["total_executions"] == 5

        # Check processor-specific stats
        processor_stats = metrics.get_processor_stats("MockProcessor")
        assert processor_stats["success_rate"] == 100.0  # All successful
        assert processor_stats["total_executions"] == 5

        # Test reset functionality
        metrics.reset_stats("MockProcessor")
        stats = metrics.get_all_stats()
        assert len(stats) == 0

    def test_multiple_processors_workflow(self):
        """Test workflow with multiple different processors."""
        # Create shared metrics instance
        metrics = ProcessorMetrics()

        # Create different processors with distinct class names
        fast_processor = MockFastProcessor()
        slow_processor = MockSlowProcessor()
        failing_processor = MockFailingProcessor()

        # Wrap them with the same metrics instance
        fast_wrapped = wrap_processor_with_metrics(fast_processor, metrics)
        slow_wrapped = wrap_processor_with_metrics(slow_processor, metrics)
        failing_wrapped = wrap_processor_with_metrics(failing_processor, metrics)

        # Process events
        event_dict = {"level": "INFO", "message": "test"}

        # Fast processor - multiple successful executions
        for _ in range(10):
            fast_wrapped(None, "info", event_dict)

        # Slow processor - fewer executions
        for _ in range(2):
            slow_wrapped(None, "info", event_dict)

        # Failing processor - some failures
        for _i in range(5):
            try:
                failing_wrapped(None, "info", event_dict)
            except ValueError:
                pass  # Expected failures

        # Verify stats using the metrics instance
        stats = metrics.get_all_stats()
        assert len(stats) == 3
        assert "MockFastProcessor" in stats
        assert "MockSlowProcessor" in stats
        assert "MockFailingProcessor" in stats

        # Verify specific processor stats
        fast_stats = metrics.get_processor_stats("MockFastProcessor")
        failing_stats = metrics.get_processor_stats("MockFailingProcessor")

        assert fast_stats["success_rate"] == 100.0  # All successful
        assert failing_stats["failure_rate"] == 100.0  # All failures

        # Test monitoring API still works (returns empty)
        api_stats = get_processor_performance_stats()
        assert api_stats == {}  # Empty since using per-call instances
