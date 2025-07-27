"""Comprehensive tests for processor performance utilities to increase coverage."""

import time
from typing import Any, Dict
from unittest.mock import Mock, patch

from fapilog.testing.mock_processors import FailingProcessor, SlowProcessor
from fapilog.testing.processor_performance import (
    load_test_processor_concurrent,
    measure_processor_latency,
    measure_processor_throughput,
    profile_processor_resource_usage,
    run_processor_performance_suite,
    stress_test_processor_memory,
)


class MockProcessor:
    """Simple mock processor for testing."""

    def __init__(self, should_fail: bool = False, delay_ms: int = 0):
        self.should_fail = should_fail
        self.delay_ms = delay_ms
        self.process_count = 0

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process event with optional delay and failure."""
        self.process_count += 1

        if self.delay_ms > 0:
            time.sleep(self.delay_ms / 1000.0)

        if self.should_fail:
            raise ValueError(f"Mock processor failure #{self.process_count}")

        result = event_dict.copy()
        result["processed_by"] = "MockProcessor"
        result["process_count"] = self.process_count
        return result


class TestMeasureProcessorThroughput:
    """Test measure_processor_throughput function."""

    def test_throughput_measurement_success(self):
        """Test throughput measurement with successful processor."""
        processor = MockProcessor()
        event = {"level": "INFO", "message": "test"}
        logger = Mock()

        result = measure_processor_throughput(
            processor, event, duration_seconds=0.1, logger_instance=logger
        )

        assert "processed_events" in result
        assert "errors" in result
        assert "duration_seconds" in result
        assert "throughput_eps" in result
        assert "error_rate" in result

        assert result["processed_events"] > 0
        assert result["errors"] == 0
        assert result["duration_seconds"] == 0.1
        assert result["throughput_eps"] > 0
        assert result["error_rate"] == 0

    def test_throughput_measurement_with_failures(self):
        """Test throughput measurement with processor that fails."""
        processor = MockProcessor(should_fail=True)
        event = {"level": "INFO", "message": "test"}
        logger = Mock()

        result = measure_processor_throughput(
            processor, event, duration_seconds=0.1, logger_instance=logger
        )

        # With "fail-fast with structured logging", failed processors still return original events
        # so they're counted as "processed", but no exceptions bubble up to performance layer
        assert result["processed_events"] > 0
        assert result["errors"] == 0  # No exceptions bubble up
        assert result["throughput_eps"] > 0
        assert result["error_rate"] == 0.0

    def test_throughput_with_custom_logger(self):
        """Test throughput measurement with custom logger instance."""
        processor = MockProcessor()
        event = {"level": "INFO", "message": "test"}
        custom_logger = Mock()

        result = measure_processor_throughput(
            processor, event, duration_seconds=0.1, logger_instance=custom_logger
        )

        assert result["processed_events"] > 0
        assert result["error_rate"] == 0

    def test_throughput_with_zero_duration_edge_case(self):
        """Test edge case handling when duration calculation might be zero."""
        processor = MockProcessor()
        event = {"level": "INFO", "message": "test"}

        # Test with very short duration
        result = measure_processor_throughput(
            processor, event, duration_seconds=0, logger_instance=None
        )

        # Should handle division by zero gracefully
        assert "throughput_eps" in result
        assert result["duration_seconds"] == 0

    def test_throughput_mixed_success_failure(self):
        """Test throughput with processor that sometimes fails."""
        # Create a processor that fails every other call
        processor = FailingProcessor(failure_rate=0.5)
        event = {"level": "INFO", "message": "test"}

        result = measure_processor_throughput(
            processor, event, duration_seconds=0.1, logger_instance=None
        )

        # With "fail-fast with structured logging", all events are still "processed"
        # (original events returned), but processor errors are logged internally
        assert result["processed_events"] > 0
        assert result["errors"] == 0  # No exceptions bubble up
        assert result["error_rate"] == 0.0


class TestMeasureProcessorLatency:
    """Test measure_processor_latency function."""

    def test_latency_measurement_basic(self):
        """Test basic latency measurement."""
        processor = MockProcessor(delay_ms=1)  # Small delay
        event = {"level": "INFO", "message": "test"}

        result = measure_processor_latency(
            processor, event, iterations=10, logger_instance=None
        )

        assert "avg_latency_ms" in result
        assert "min_latency_ms" in result
        assert "max_latency_ms" in result
        assert "p50_latency_ms" in result
        assert "p95_latency_ms" in result
        assert "p99_latency_ms" in result

        # Should have some measurable latency
        assert result["avg_latency_ms"] >= 0
        assert result["min_latency_ms"] >= 0
        assert result["max_latency_ms"] >= result["min_latency_ms"]

    def test_latency_with_slow_processor(self):
        """Test latency measurement with intentionally slow processor."""
        processor = SlowProcessor(delay_ms=5)
        event = {"level": "INFO", "message": "test"}

        result = measure_processor_latency(
            processor, event, iterations=10, logger_instance=None
        )

        # Should show higher latency due to artificial delay
        assert result["avg_latency_ms"] > 0
        assert result["min_latency_ms"] > 0

    def test_latency_with_failing_processor(self):
        """Test latency measurement when processor fails."""
        processor = MockProcessor(should_fail=True, delay_ms=2)
        event = {"level": "INFO", "message": "test"}

        result = measure_processor_latency(
            processor, event, iterations=5, logger_instance=None
        )

        # Should still measure latency even for failed operations
        assert result["avg_latency_ms"] >= 0
        assert result["min_latency_ms"] >= 0

    def test_latency_edge_case_no_latencies(self):
        """Test edge case when no latencies are recorded."""
        # This is a bit artificial but tests the empty latencies case
        with patch("time.time", side_effect=[0, 0, 0, 0]):  # Mock time to be constant
            processor = MockProcessor()
            event = {"level": "INFO", "message": "test"}

            result = measure_processor_latency(
                processor, event, iterations=1, logger_instance=None
            )

            # Should handle empty latencies gracefully
            assert result["avg_latency_ms"] >= 0

    def test_latency_percentile_calculations(self):
        """Test that percentile calculations are reasonable."""
        processor = MockProcessor(delay_ms=1)
        event = {"level": "INFO", "message": "test"}

        result = measure_processor_latency(
            processor, event, iterations=20, logger_instance=None
        )

        # Percentiles should be in order
        assert result["p50_latency_ms"] <= result["p95_latency_ms"]
        assert result["p95_latency_ms"] <= result["p99_latency_ms"]
        assert result["min_latency_ms"] <= result["p50_latency_ms"]
        assert result["p99_latency_ms"] <= result["max_latency_ms"]


class TestStressTestProcessorMemory:
    """Test stress_test_processor_memory function."""

    def test_memory_stress_basic(self):
        """Test basic memory stress testing."""
        processor = MockProcessor()
        event = {"level": "INFO", "message": "test"}

        result = stress_test_processor_memory(
            processor, event, iterations=5, logger_instance=None
        )

        # Should test different event sizes
        assert "small" in result
        assert "medium" in result
        assert "large" in result
        assert "xlarge" in result

        # Each size should have results
        for size_name in ["small", "medium", "large", "xlarge"]:
            size_result = result[size_name]
            assert "event_size_category" in size_result
            assert "processed_events" in size_result
            assert "error_count" in size_result
            assert "duration_seconds" in size_result
            assert "throughput_eps" in size_result
            assert "avg_time_per_event_ms" in size_result

            assert size_result["event_size_category"] == size_name
            assert size_result["processed_events"] >= 0

    def test_memory_stress_with_failures(self):
        """Test memory stress testing with failing processor."""
        processor = MockProcessor(should_fail=True)
        event = {"level": "INFO", "message": "test"}

        result = stress_test_processor_memory(
            processor, event, iterations=3, logger_instance=None
        )

        # With "fail-fast with structured logging", events are still processed
        for size_name in ["small", "medium", "large", "xlarge"]:
            size_result = result[size_name]
            assert size_result["processed_events"] == 3  # All iterations processed
            assert size_result["error_count"] == 0  # No exceptions bubble up

    def test_memory_stress_throughput_calculations(self):
        """Test throughput calculations in memory stress test."""
        processor = MockProcessor()
        event = {"level": "INFO", "message": "base_event"}

        result = stress_test_processor_memory(
            processor, event, iterations=2, logger_instance=None
        )

        for size_name in ["small", "medium", "large", "xlarge"]:
            size_result = result[size_name]

            if size_result["duration_seconds"] > 0:
                expected_throughput = (
                    size_result["processed_events"] / size_result["duration_seconds"]
                )
                assert abs(size_result["throughput_eps"] - expected_throughput) < 0.001

            if size_result["processed_events"] > 0:
                expected_avg_time = (
                    size_result["duration_seconds"]
                    / size_result["processed_events"]
                    * 1000
                )
                assert (
                    abs(size_result["avg_time_per_event_ms"] - expected_avg_time)
                    < 0.001
                )

    def test_memory_stress_zero_duration_edge_case(self):
        """Test edge case when duration is zero."""
        processor = MockProcessor()
        event = {"level": "INFO", "message": "test"}

        # Mock time to simulate instant execution
        with patch("time.time", side_effect=[0, 0, 0, 0, 0, 0, 0, 0]):
            result = stress_test_processor_memory(
                processor, event, iterations=1, logger_instance=None
            )

            for size_name in ["small", "medium", "large", "xlarge"]:
                size_result = result[size_name]
                # Should handle zero duration gracefully
                assert "throughput_eps" in size_result


class TestLoadTestProcessorConcurrent:
    """Test load_test_processor_concurrent function."""

    def test_load_test_basic(self):
        """Test basic load testing functionality."""
        processor = MockProcessor()
        event = {"level": "INFO", "message": "test"}

        result = load_test_processor_concurrent(
            processor, event, total_events=50, logger_instance=None
        )

        assert "total_events" in result
        assert "processed_events" in result
        assert "error_count" in result
        assert "total_duration_seconds" in result
        assert "overall_throughput_eps" in result
        assert "error_rate" in result
        assert "batch_results" in result
        assert "latency_stats" in result

        assert result["total_events"] == 50
        assert result["processed_events"] + result["error_count"] == 50
        assert result["error_rate"] == 0
        assert len(result["batch_results"]) > 0

        # Check latency stats
        latency_stats = result["latency_stats"]
        assert "avg_latency_ms" in latency_stats
        assert "min_latency_ms" in latency_stats
        assert "max_latency_ms" in latency_stats

    def test_load_test_with_failures(self):
        """Test load testing with failing processor."""
        processor = MockProcessor(should_fail=True)
        event = {"level": "INFO", "message": "test"}

        result = load_test_processor_concurrent(
            processor, event, total_events=25, logger_instance=None
        )

        # With "fail-fast with structured logging", events are still processed
        assert result["processed_events"] == 25
        assert result["error_count"] == 0
        assert result["error_rate"] == 0.0

    def test_load_test_batch_results(self):
        """Test batch results structure in load testing."""
        processor = MockProcessor()
        event = {"level": "INFO", "message": "test"}

        result = load_test_processor_concurrent(
            processor,
            event,
            total_events=2500,
            logger_instance=None,  # 2.5 batches
        )

        batch_results = result["batch_results"]
        assert len(batch_results) >= 1  # Should have at least 1 batch

        for batch in batch_results:
            assert "batch_start" in batch
            assert "batch_end" in batch
            assert "processed" in batch
            assert "errors" in batch
            assert "duration_seconds" in batch
            assert "throughput_eps" in batch

    def test_load_test_throughput_calculation(self):
        """Test throughput calculations in load testing."""
        processor = MockProcessor()
        event = {"level": "INFO", "message": "test"}

        result = load_test_processor_concurrent(
            processor, event, total_events=10, logger_instance=None
        )

        if result["total_duration_seconds"] > 0:
            expected_throughput = (
                result["processed_events"] / result["total_duration_seconds"]
            )
            assert abs(result["overall_throughput_eps"] - expected_throughput) < 0.001

    def test_load_test_zero_events_edge_case(self):
        """Test edge case with zero total events."""
        processor = MockProcessor()
        event = {"level": "INFO", "message": "test"}

        result = load_test_processor_concurrent(
            processor, event, total_events=0, logger_instance=None
        )

        assert result["total_events"] == 0
        assert result["processed_events"] == 0
        assert result["error_count"] == 0
        assert result["error_rate"] == 0
        assert len(result["batch_results"]) == 0


class TestProfileProcessorResourceUsage:
    """Test profile_processor_resource_usage function."""

    @patch("psutil.Process")
    def test_resource_profiling_basic(self, mock_process_class):
        """Test basic resource profiling functionality."""
        # Mock psutil Process
        mock_process = Mock()
        mock_memory_info = Mock()
        mock_memory_info.rss = 100 * 1024 * 1024  # 100MB in bytes
        mock_process.memory_info.return_value = mock_memory_info
        mock_process.cpu_percent.return_value = 10.5
        mock_process_class.return_value = mock_process

        processor = MockProcessor()
        event = {"level": "INFO", "message": "test"}

        result = profile_processor_resource_usage(
            processor, event, duration_seconds=1, logger_instance=None
        )

        assert "duration_seconds" in result
        assert "processed_events" in result
        assert "error_count" in result
        assert "throughput_eps" in result
        assert "baseline_memory_mb" in result
        assert "baseline_cpu_percent" in result
        assert "memory_stats" in result
        assert "cpu_stats" in result

        # Check memory stats structure
        memory_stats = result["memory_stats"]
        assert "avg_memory_mb" in memory_stats
        assert "max_memory_mb" in memory_stats
        assert "min_memory_mb" in memory_stats
        assert "memory_growth_mb" in memory_stats

        # Check CPU stats structure
        cpu_stats = result["cpu_stats"]
        assert "avg_cpu_percent" in cpu_stats
        assert "max_cpu_percent" in cpu_stats
        assert "min_cpu_percent" in cpu_stats

        assert result["processed_events"] > 0
        assert result["error_count"] == 0

    @patch("psutil.Process")
    def test_resource_profiling_with_failures(self, mock_process_class):
        """Test resource profiling with failing processor."""
        # Mock psutil Process
        mock_process = Mock()
        mock_memory_info = Mock()
        mock_memory_info.rss = 50 * 1024 * 1024  # 50MB
        mock_process.memory_info.return_value = mock_memory_info
        mock_process.cpu_percent.return_value = 5.0
        mock_process_class.return_value = mock_process

        processor = MockProcessor(should_fail=True)
        event = {"level": "INFO", "message": "test"}

        result = profile_processor_resource_usage(
            processor, event, duration_seconds=1, logger_instance=None
        )

        # With "fail-fast with structured logging", events are still processed
        assert result["processed_events"] > 0
        assert result["error_count"] == 0

    @patch("psutil.Process")
    def test_resource_profiling_memory_growth(self, mock_process_class):
        """Test memory growth calculation in resource profiling."""
        # Mock memory growth over time - use a cycling pattern to avoid StopIteration
        memory_values = [100, 110, 120, 130, 140]

        mock_process = Mock()
        call_count = [0]  # Use list to allow modification in nested function

        def mock_memory_info():
            mock_info = Mock()
            # Cycle through memory values
            mock_info.rss = (
                memory_values[call_count[0] % len(memory_values)] * 1024 * 1024
            )
            call_count[0] += 1
            return mock_info

        mock_process.memory_info = mock_memory_info
        mock_process.cpu_percent.return_value = 15.0
        mock_process_class.return_value = mock_process

        processor = MockProcessor()
        event = {"level": "INFO", "message": "test"}

        result = profile_processor_resource_usage(
            processor, event, duration_seconds=1, logger_instance=None
        )

        # Should show memory growth when memory increases over time
        assert result["memory_stats"]["memory_growth_mb"] >= 0

    @patch("psutil.Process")
    def test_resource_profiling_zero_samples_edge_case(self, mock_process_class):
        """Test edge case with no resource samples."""
        mock_process = Mock()
        mock_memory_info = Mock()
        mock_memory_info.rss = 75 * 1024 * 1024
        mock_process.memory_info.return_value = mock_memory_info
        mock_process.cpu_percent.return_value = 8.0
        mock_process_class.return_value = mock_process

        processor = MockProcessor()
        event = {"level": "INFO", "message": "test"}

        # Mock time to simulate instant execution (no sampling loop iterations)
        # Provide enough values for baseline + start + end + any additional calls
        time_values = [0, 0, 0, 0, 0, 0]  # Multiple zeros to ensure loop doesn't run
        with patch("time.time", side_effect=time_values):
            result = profile_processor_resource_usage(
                processor, event, duration_seconds=0, logger_instance=None
            )

            # Should handle zero samples gracefully
            assert "memory_stats" in result
            assert "cpu_stats" in result
            # With no samples, stats should have defaults (0 or empty)
            assert result["memory_stats"]["avg_memory_mb"] == 0
            assert result["cpu_stats"]["avg_cpu_percent"] == 0


class TestRunProcessorPerformanceSuite:
    """Test run_processor_performance_suite integration function."""

    def test_performance_suite_basic(self):
        """Test running the complete performance suite."""
        processor = MockProcessor()
        event = {"level": "INFO", "message": "test"}

        # Mock psutil for resource profiling
        with patch("psutil.Process") as mock_process_class:
            mock_process = Mock()
            mock_memory_info = Mock()
            mock_memory_info.rss = 80 * 1024 * 1024
            mock_process.memory_info.return_value = mock_memory_info
            mock_process.cpu_percent.return_value = 12.0
            mock_process_class.return_value = mock_process

            result = run_processor_performance_suite(
                processor, event, logger_instance=None
            )

            # Should contain all test results
            assert "throughput" in result
            assert "latency" in result
            assert "memory_stress" in result
            assert "load_test" in result
            assert "resource_profile" in result

            # Verify each test ran successfully
            assert result["throughput"]["processed_events"] > 0
            assert "avg_latency_ms" in result["latency"]
            assert "small" in result["memory_stress"]
            assert result["load_test"]["total_events"] == 10000
            assert "memory_stats" in result["resource_profile"]

    def test_performance_suite_with_custom_logger(self):
        """Test performance suite with custom logger."""
        processor = MockProcessor()
        event = {"level": "INFO", "message": "test"}
        custom_logger = Mock()

        with patch("psutil.Process") as mock_process_class:
            mock_process = Mock()
            mock_memory_info = Mock()
            mock_memory_info.rss = 90 * 1024 * 1024
            mock_process.memory_info.return_value = mock_memory_info
            mock_process.cpu_percent.return_value = 20.0
            mock_process_class.return_value = mock_process

            result = run_processor_performance_suite(
                processor, event, logger_instance=custom_logger
            )

            # Should still complete all tests
            assert len(result) == 5
            assert all(
                key in result
                for key in [
                    "throughput",
                    "latency",
                    "memory_stress",
                    "load_test",
                    "resource_profile",
                ]
            )

    def test_performance_suite_with_slow_processor(self):
        """Test performance suite with an intentionally slow processor."""
        processor = SlowProcessor(delay_ms=1)  # Small delay
        event = {"level": "INFO", "message": "test"}

        with patch("psutil.Process") as mock_process_class:
            mock_process = Mock()
            mock_memory_info = Mock()
            mock_memory_info.rss = 60 * 1024 * 1024
            mock_process.memory_info.return_value = mock_memory_info
            mock_process.cpu_percent.return_value = 25.0
            mock_process_class.return_value = mock_process

            result = run_processor_performance_suite(
                processor, event, logger_instance=None
            )

            # Should complete but show higher latencies
            assert result["latency"]["avg_latency_ms"] > 0
            assert result["throughput"]["throughput_eps"] > 0

    @patch("builtins.print")  # Mock print statements
    def test_performance_suite_print_statements(self, mock_print):
        """Test that performance suite prints progress messages."""
        processor = MockProcessor()
        event = {"level": "INFO", "message": "test"}

        with patch("psutil.Process") as mock_process_class:
            mock_process = Mock()
            mock_memory_info = Mock()
            mock_memory_info.rss = 70 * 1024 * 1024
            mock_process.memory_info.return_value = mock_memory_info
            mock_process.cpu_percent.return_value = 18.0
            mock_process_class.return_value = mock_process

            run_processor_performance_suite(processor, event, logger_instance=None)

            # Should have printed progress messages
            assert mock_print.call_count >= 5
            print_calls = [call.args[0] for call in mock_print.call_args_list]

            assert any("throughput test" in call for call in print_calls)
            assert any("latency test" in call for call in print_calls)
            assert any("memory stress test" in call for call in print_calls)
            assert any("load test" in call for call in print_calls)
            assert any("resource profiling" in call for call in print_calls)


class TestProcessorPerformanceIntegration:
    """Integration tests for processor performance testing."""

    def test_real_processor_integration(self):
        """Test performance functions with real processor classes."""
        # Test with FailingProcessor - with fail-fast logging, no errors bubble up
        failing_processor = FailingProcessor(failure_rate=0.3)
        event = {"level": "ERROR", "message": "test_failure"}

        throughput_result = measure_processor_throughput(
            failing_processor, event, duration_seconds=0.1, logger_instance=None
        )

        # With "fail-fast with structured logging", error_rate is 0 as events are returned
        assert throughput_result["error_rate"] == 0.0
        assert throughput_result["processed_events"] > 0

        # Test with SlowProcessor
        slow_processor = SlowProcessor(delay_ms=2)
        latency_result = measure_processor_latency(
            slow_processor, event, iterations=5, logger_instance=None
        )

        # Should show measurable latency
        assert (
            latency_result["avg_latency_ms"] >= 0
        )  # May be small but should be non-negative

    def test_edge_case_empty_event(self):
        """Test performance functions with empty event."""
        processor = MockProcessor()
        empty_event = {}

        result = measure_processor_throughput(
            processor, empty_event, duration_seconds=1, logger_instance=None
        )

        # Should handle empty events gracefully
        assert result["processed_events"] > 0
        assert result["error_rate"] == 0

    def test_large_event_handling(self):
        """Test performance functions with large events."""
        processor = MockProcessor()
        large_event = {
            "level": "INFO",
            "message": "test",
            "large_data": "x" * 10000,  # Large string
            "large_list": list(range(1000)),  # Large list
        }

        result = stress_test_processor_memory(
            processor, large_event, iterations=2, logger_instance=None
        )

        # Should handle large events gracefully
        assert "xlarge" in result
        assert result["xlarge"]["processed_events"] >= 0
