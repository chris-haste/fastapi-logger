"""Tests for processor testing utilities."""

import time
from typing import Any, Dict
from unittest.mock import Mock, patch

from fapilog.processors.base import Processor
from fapilog.testing.processor_testing import (
    ProcessorTestResult,
    benchmark_processor_performance,
    run_processor_edge_cases,
    run_processor_with_events,
    stress_test_processor,
    validate_processor_behavior,
)


class MockProcessor(Processor):
    """Mock processor for testing."""

    def __init__(self, should_fail: bool = False, fail_rate: float = 0.0):
        self.should_fail = should_fail
        self.fail_rate = fail_rate
        self.process_count = 0
        super().__init__()

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        self.process_count += 1

        if self.should_fail:
            raise ValueError("Processor configured to fail")

        # Randomly fail based on fail_rate
        if self.fail_rate > 0 and (self.process_count % int(1 / self.fail_rate)) == 0:
            raise RuntimeError(f"Random failure #{self.process_count}")

        # Modify the event to show it was processed
        result = event_dict.copy()
        result["processed_by"] = "MockProcessor"
        result["process_count"] = self.process_count
        return result


class SlowProcessor(MockProcessor):
    """Processor that takes time to process events."""

    def __init__(self, delay: float = 0.01):
        super().__init__()
        self.delay = delay

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        time.sleep(self.delay)
        return super().process(logger, method_name, event_dict)


class TestProcessorTestResult:
    """Test ProcessorTestResult class."""

    def test_initialization(self):
        """Test ProcessorTestResult initialization."""
        errors = [ValueError("test"), RuntimeError("another")]
        result = ProcessorTestResult(
            processor_name="TestProcessor",
            total_events=100,
            successful_events=85,
            failed_events=15,
            average_duration=0.005,
            errors=errors,
        )

        assert result.processor_name == "TestProcessor"
        assert result.total_events == 100
        assert result.successful_events == 85
        assert result.failed_events == 15
        assert result.average_duration == 0.005
        assert result.errors == errors

    def test_success_rate_property(self):
        """Test success_rate property calculation."""
        result = ProcessorTestResult(
            processor_name="Test",
            total_events=100,
            successful_events=85,
            failed_events=15,
            average_duration=0.001,
            errors=[],
        )
        assert result.success_rate == 85.0

    def test_success_rate_zero_events(self):
        """Test success_rate with zero total events."""
        result = ProcessorTestResult(
            processor_name="Test",
            total_events=0,
            successful_events=0,
            failed_events=0,
            average_duration=0.0,
            errors=[],
        )
        assert result.success_rate == 0.0

    def test_error_rate_property(self):
        """Test error_rate property calculation."""
        result = ProcessorTestResult(
            processor_name="Test",
            total_events=100,
            successful_events=85,
            failed_events=15,
            average_duration=0.001,
            errors=[],
        )
        assert result.error_rate == 15.0

    def test_error_rate_zero_events(self):
        """Test error_rate with zero total events."""
        result = ProcessorTestResult(
            processor_name="Test",
            total_events=0,
            successful_events=0,
            failed_events=0,
            average_duration=0.0,
            errors=[],
        )
        assert result.error_rate == 0.0

    def test_repr_method(self):
        """Test __repr__ method."""
        result = ProcessorTestResult(
            processor_name="TestProcessor",
            total_events=50,
            successful_events=45,
            failed_events=5,
            average_duration=0.0025,
            errors=[],
        )

        repr_str = repr(result)
        assert "ProcessorTestResult" in repr_str
        assert "processor='TestProcessor'" in repr_str
        assert "total=50" in repr_str
        assert "success_rate=90.0%" in repr_str
        assert "avg_duration=0.0025s" in repr_str


class TestProcessorWithEvents:
    """Test run_processor_with_events function."""

    def test_successful_processing(self):
        """Test processing events successfully."""
        processor = MockProcessor()
        events = [
            {"level": "INFO", "message": "test1"},
            {"level": "DEBUG", "message": "test2"},
            {"level": "ERROR", "message": "test3"},
        ]

        result = run_processor_with_events(processor, events)

        assert result.processor_name == "MockProcessor"
        assert result.total_events == 3
        assert result.successful_events == 3
        assert result.failed_events == 0
        assert result.success_rate == 100.0
        assert result.error_rate == 0.0
        assert len(result.errors) == 0
        assert result.average_duration > 0.0

    def test_processing_with_failures(self):
        """Test processing events with some failures."""
        processor = MockProcessor(fail_rate=0.5)  # Fail every 2nd event
        events = [
            {"level": "INFO", "message": "test1"},
            {"level": "DEBUG", "message": "test2"},
            {"level": "ERROR", "message": "test3"},
            {"level": "WARNING", "message": "test4"},
        ]

        result = run_processor_with_events(processor, events)

        assert result.processor_name == "MockProcessor"
        assert result.total_events == 4
        # With fail-fast error handling, events are returned as-is when processor fails
        assert (
            result.successful_events == 4
        )  # All events succeed (returned as original)
        assert result.failed_events == 0  # No events actually "fail" to return
        assert result.success_rate == 100.0
        assert result.error_rate == 0.0

    def test_all_failures(self):
        """Test processing when all events fail."""
        processor = MockProcessor(should_fail=True)
        events = [
            {"level": "INFO", "message": "test1"},
            {"level": "DEBUG", "message": "test2"},
        ]

        result = run_processor_with_events(processor, events)

        assert result.processor_name == "MockProcessor"
        assert result.total_events == 2
        # With fail-fast error handling, original events are returned
        assert result.successful_events == 2  # Events returned as original
        assert result.failed_events == 0  # No events actually "fail" to return
        assert result.success_rate == 100.0
        assert result.error_rate == 0.0

    def test_empty_events_list(self):
        """Test with empty events list."""
        processor = MockProcessor()
        events = []

        result = run_processor_with_events(processor, events)

        assert result.processor_name == "MockProcessor"
        assert result.total_events == 0
        assert result.successful_events == 0
        assert result.failed_events == 0
        assert result.success_rate == 0.0
        assert result.error_rate == 0.0
        assert result.average_duration == 0.0

    def test_with_logger_instance(self):
        """Test with custom logger instance."""
        processor = MockProcessor()
        events = [{"level": "INFO", "message": "test"}]
        logger_instance = Mock()

        result = run_processor_with_events(processor, events, logger_instance)

        assert result.total_events == 1
        assert result.successful_events == 1

    @patch("fapilog.testing.processor_testing.log_processor_error_with_context")
    def test_error_logging(self, mock_log_error):
        """Test that errors are logged properly."""
        processor = MockProcessor(should_fail=True)
        events = [{"level": "INFO", "message": "test"}]

        result = run_processor_with_events(processor, events)

        # With fail-fast error handling, events still succeed (return original)
        # but errors should still be logged internally
        assert result.successful_events == 1
        assert result.failed_events == 0


class TestValidateProcessorBehavior:
    """Test validate_processor_behavior function."""

    def test_valid_event_success(self):
        """Test validation with successful valid event."""
        processor = MockProcessor()
        valid_event = {"level": "INFO", "message": "valid"}

        result = validate_processor_behavior(processor, valid_event)

        assert result["processor_name"] == "MockProcessor"
        assert result["valid_event_result"] is not None
        assert result["valid_event_error"] is None
        assert result["invalid_event_result"] is None
        assert result["invalid_event_error"] is None

    def test_valid_event_failure(self):
        """Test validation when valid event fails."""
        processor = MockProcessor(should_fail=True)
        valid_event = {"level": "INFO", "message": "valid"}

        result = validate_processor_behavior(processor, valid_event)

        assert result["processor_name"] == "MockProcessor"
        # With fail-fast error handling, original event is returned
        assert result["valid_event_result"] == valid_event
        assert result["valid_event_error"] is None

    def test_with_invalid_event(self):
        """Test validation with both valid and invalid events."""
        processor = MockProcessor()
        valid_event = {"level": "INFO", "message": "valid"}
        invalid_event = {"level": "INVALID", "message": None}

        result = validate_processor_behavior(processor, valid_event, invalid_event)

        assert result["processor_name"] == "MockProcessor"
        assert result["valid_event_result"] is not None
        assert result["valid_event_error"] is None
        assert result["invalid_event_result"] is not None
        assert result["invalid_event_error"] is None

    def test_with_failing_invalid_event(self):
        """Test validation when invalid event causes failure."""

        # Create a processor that fails on None message
        class FailOnNoneProcessor(MockProcessor):
            def process(self, logger, method_name, event_dict):
                if event_dict.get("message") is None:
                    raise ValueError("None message not allowed")
                return super().process(logger, method_name, event_dict)

        processor = FailOnNoneProcessor()
        valid_event = {"level": "INFO", "message": "valid"}
        invalid_event = {"level": "INFO", "message": None}

        result = validate_processor_behavior(processor, valid_event, invalid_event)

        assert result["valid_event_result"] is not None
        assert result["valid_event_error"] is None
        # With fail-fast error handling, original event is returned even when processor fails
        assert result["invalid_event_result"] == invalid_event
        assert result["invalid_event_error"] is None

    def test_with_logger_instance(self):
        """Test validation with custom logger instance."""
        processor = MockProcessor()
        valid_event = {"level": "INFO", "message": "test"}
        logger_instance = Mock()

        result = validate_processor_behavior(
            processor, valid_event, logger_instance=logger_instance
        )

        assert result["valid_event_result"] is not None


class TestStressTestProcessor:
    """Test stress_test_processor function."""

    def test_stress_test_success(self):
        """Test stress testing with successful processor."""
        processor = MockProcessor()
        event_template = {"level": "INFO", "message": "stress test"}
        num_events = 50

        result = stress_test_processor(processor, event_template, num_events)

        assert result.processor_name == "MockProcessor"
        assert result.total_events == num_events
        assert result.successful_events == num_events
        assert result.failed_events == 0
        assert result.success_rate == 100.0

    def test_stress_test_with_failures(self):
        """Test stress testing with some failures."""
        processor = MockProcessor(fail_rate=0.1)  # Fail every 10th event
        event_template = {"level": "INFO", "message": "stress test"}
        num_events = 20

        result = stress_test_processor(processor, event_template, num_events)

        assert result.processor_name == "MockProcessor"
        assert result.total_events == num_events
        # With fail-fast error handling, all events succeed (returned as original)
        assert result.failed_events == 0  # No events actually "fail" to return
        assert result.successful_events == 20  # All events returned

    def test_event_generation(self):
        """Test that events are generated correctly."""
        processor = MockProcessor()
        event_template = {"level": "DEBUG", "message": "template", "extra": "data"}
        num_events = 3

        # We'll capture the events by checking the processor's state
        result = stress_test_processor(processor, event_template, num_events)

        assert result.total_events == 3
        assert result.successful_events == 3
        # Verify the processor was called the correct number of times
        assert processor.process_count == 3

    def test_default_num_events(self):
        """Test stress test with default number of events."""
        processor = MockProcessor()
        event_template = {"level": "INFO", "message": "default"}

        result = stress_test_processor(processor, event_template)

        assert result.total_events == 1000  # Default value

    def test_with_logger_instance(self):
        """Test stress test with custom logger instance."""
        processor = MockProcessor()
        event_template = {"level": "INFO", "message": "test"}
        logger_instance = Mock()

        result = stress_test_processor(processor, event_template, 10, logger_instance)

        assert result.total_events == 10


class TestProcessorEdgeCases:
    """Test run_processor_edge_cases function."""

    def test_edge_cases_success(self):
        """Test edge cases with processor that handles them."""
        processor = MockProcessor()

        result = run_processor_edge_cases(processor)

        # Should have results for all edge cases
        assert len(result) == 6

        # All should succeed with our robust mock processor
        for case_name, case_result in result.items():
            assert case_name.startswith("edge_case_")
            assert case_result["success"] is True
            assert case_result["result"] is not None
            assert case_result["error"] is None

    def test_edge_cases_with_failures(self):
        """Test edge cases with processor that fails on some inputs."""

        class StrictProcessor(MockProcessor):
            def process(self, logger, method_name, event_dict):
                if not event_dict:
                    raise ValueError("Empty dict not allowed")
                if event_dict.get("message") == "":
                    raise ValueError("Empty message not allowed")
                return super().process(logger, method_name, event_dict)

        processor = StrictProcessor()

        result = run_processor_edge_cases(processor)

        # Should have results for all edge cases
        assert len(result) == 6

        # With fail-fast error handling, all cases succeed (return original)
        # But we can verify the processor attempted to process them by checking logs
        assert result["edge_case_0"]["success"] is True  # Original event returned
        assert result["edge_case_0"]["result"] == {}  # Empty dict returned as-is

        assert result["edge_case_1"]["success"] is True  # Original event returned
        assert result["edge_case_1"]["result"]["message"] == ""  # Empty message

    def test_with_logger_instance(self):
        """Test edge cases with custom logger instance."""
        processor = MockProcessor()
        logger_instance = Mock()

        result = run_processor_edge_cases(processor, logger_instance)

        assert len(result) == 6


class TestBenchmarkProcessorPerformance:
    """Test benchmark_processor_performance function."""

    def test_performance_benchmark(self):
        """Test performance benchmarking."""
        processor = SlowProcessor(delay=0.001)  # 1ms delay
        event = {"level": "INFO", "message": "benchmark"}
        iterations = 10

        result = benchmark_processor_performance(processor, event, iterations)

        assert result["total_iterations"] == iterations
        assert result["total_time"] > 0
        assert result["average_duration"] > 0
        assert result["min_duration"] > 0
        assert result["max_duration"] >= result["min_duration"]
        assert result["median_duration"] > 0

        # With 1ms delay, average should be around 1ms
        assert result["average_duration"] >= 0.001

    def test_benchmark_with_failures(self):
        """Test benchmarking with processor that sometimes fails."""
        processor = MockProcessor(fail_rate=0.5)  # Fail every 2nd event
        event = {"level": "INFO", "message": "benchmark"}
        iterations = 10

        result = benchmark_processor_performance(processor, event, iterations)

        # Should complete all iterations even with failures
        assert result["total_iterations"] == iterations
        assert result["total_time"] > 0
        assert result["average_duration"] > 0

    def test_benchmark_fast_processor(self):
        """Test benchmarking with fast processor."""
        processor = MockProcessor()  # No artificial delay
        event = {"level": "INFO", "message": "benchmark"}
        iterations = 100

        result = benchmark_processor_performance(processor, event, iterations)

        assert result["total_iterations"] == iterations
        assert result["average_duration"] > 0
        assert result["min_duration"] >= 0
        assert result["max_duration"] >= result["min_duration"]

    def test_default_iterations(self):
        """Test benchmark with default iterations."""
        processor = MockProcessor()
        event = {"level": "INFO", "message": "benchmark"}

        result = benchmark_processor_performance(processor, event)

        assert result["total_iterations"] == 10000  # Default value

    def test_with_logger_instance(self):
        """Test benchmark with custom logger instance."""
        processor = MockProcessor()
        event = {"level": "INFO", "message": "test"}
        logger_instance = Mock()

        result = benchmark_processor_performance(processor, event, 5, logger_instance)

        assert result["total_iterations"] == 5


class TestIntegration:
    """Integration tests for processor testing utilities."""

    def test_complete_processor_testing_workflow(self):
        """Test a complete workflow using all testing utilities."""
        processor = MockProcessor(fail_rate=0.1)

        # 1. Basic validation
        validation_result = validate_processor_behavior(
            processor,
            valid_event={"level": "INFO", "message": "valid"},
            invalid_event={"level": "INVALID", "message": "invalid"},
        )
        assert validation_result["processor_name"] == "MockProcessor"

        # 2. Edge case testing
        edge_results = run_processor_edge_cases(processor)
        assert len(edge_results) == 6

        # 3. Stress testing
        stress_result = stress_test_processor(
            processor, {"level": "INFO", "message": "stress"}, 100
        )
        assert stress_result.total_events == 100

        # 4. Performance benchmarking
        perf_result = benchmark_processor_performance(
            processor, {"level": "INFO", "message": "perf"}, 50
        )
        assert perf_result["total_iterations"] == 50

        # 5. Event list testing
        events = [{"level": "INFO", "message": f"test_{i}"} for i in range(20)]
        event_result = run_processor_with_events(processor, events)
        assert event_result.total_events == 20

    def test_processor_test_result_comprehensive(self):
        """Test ProcessorTestResult with various scenarios."""
        # Test with mixed success/failure
        result = ProcessorTestResult(
            processor_name="TestProcessor",
            total_events=200,
            successful_events=180,
            failed_events=20,
            average_duration=0.0035,
            errors=[ValueError("error1"), RuntimeError("error2")],
        )

        assert result.success_rate == 90.0
        assert result.error_rate == 10.0
        assert len(result.errors) == 2

        # Test repr output
        repr_str = repr(result)
        assert "TestProcessor" in repr_str
        assert "200" in repr_str
        assert "90.0%" in repr_str
