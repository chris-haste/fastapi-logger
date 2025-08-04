"""Testing utilities for fapilog processors."""

import logging
import time
from typing import Any, Dict, List, Optional

from ..processors.base import Processor
from ..processors.error_handling import (
    log_processor_error_with_context,
    simple_processor_execution,
)

logger = logging.getLogger(__name__)


class ProcessorTestResult:
    """Result of processor testing."""

    def __init__(
        self,
        processor_name: str,
        total_events: int,
        successful_events: int,
        failed_events: int,
        average_duration: float,
        errors: List[Exception],
    ) -> None:
        self.processor_name = processor_name
        self.total_events = total_events
        self.successful_events = successful_events
        self.failed_events = failed_events
        self.average_duration = average_duration
        self.errors = errors

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_events == 0:
            return 0.0
        return (self.successful_events / self.total_events) * 100

    @property
    def error_rate(self) -> float:
        """Calculate error rate."""
        if self.total_events == 0:
            return 0.0
        return (self.failed_events / self.total_events) * 100

    def __repr__(self) -> str:
        return (
            f"ProcessorTestResult("
            f"processor='{self.processor_name}', "
            f"total={self.total_events}, "
            f"success_rate={self.success_rate:.1f}%, "
            f"avg_duration={self.average_duration:.4f}s)"
        )


def run_processor_with_events(
    processor: Processor,
    events: List[Dict[str, Any]],
    logger_instance: Optional[Any] = None,
) -> ProcessorTestResult:
    """Test a processor with a list of events.

    Args:
        processor: The processor to test
        events: List of event dictionaries to process
        logger_instance: Optional logger instance (will use None if not provided)

    Returns:
        ProcessorTestResult with test statistics and results
    """
    processor_name = processor.__class__.__name__
    total_events = len(events)
    successful_events = 0
    failed_events = 0
    total_duration = 0.0
    errors: List[Exception] = []

    for event in events:
        start_time = time.time()
        try:
            # Test with simple error handling - we don't use the result
            simple_processor_execution(processor, logger_instance, "info", event)

            # If no exception was raised, processor succeeded
            successful_events += 1
        except Exception as e:
            failed_events += 1
            errors.append(e)
            log_processor_error_with_context(
                e, {"event": event, "processor": processor_name}
            )
        finally:
            total_duration += time.time() - start_time

    average_duration = total_duration / total_events if total_events > 0 else 0.0

    return ProcessorTestResult(
        processor_name=processor_name,
        total_events=total_events,
        successful_events=successful_events,
        failed_events=failed_events,
        average_duration=average_duration,
        errors=errors,
    )


def validate_processor_behavior(
    processor: Processor,
    valid_event: Dict[str, Any],
    invalid_event: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[Any] = None,
) -> Dict[str, Any]:
    """Validate basic processor behavior with known good and bad inputs.

    Args:
        processor: The processor to validate
        valid_event: Event that should be processed successfully
        invalid_event: Event that should cause processor to fail gracefully
        logger_instance: Optional logger instance

    Returns:
        Dictionary with validation results
    """
    results = {
        "processor_name": processor.__class__.__name__,
        "valid_event_result": None,
        "invalid_event_result": None,
        "valid_event_error": None,
        "invalid_event_error": None,
    }

    # Test valid event
    try:
        result = simple_processor_execution(
            processor, logger_instance, "info", valid_event
        )
        results["valid_event_result"] = result
    except Exception as e:
        results["valid_event_error"] = str(e)

    # Test invalid event if provided
    if invalid_event is not None:
        try:
            result = simple_processor_execution(
                processor, logger_instance, "info", invalid_event
            )
            results["invalid_event_result"] = result
        except Exception as e:
            results["invalid_event_error"] = str(e)

    return results


def stress_test_processor(
    processor: Processor,
    event_template: Dict[str, Any],
    num_events: int = 1000,
    logger_instance: Optional[Any] = None,
) -> ProcessorTestResult:
    """Stress test a processor with many events.

    Args:
        processor: The processor to test
        event_template: Template event to replicate
        num_events: Number of events to generate and process
        logger_instance: Optional logger instance

    Returns:
        ProcessorTestResult with stress test statistics
    """
    # Generate events based on template
    events = []
    for i in range(num_events):
        event = event_template.copy()
        event["event_id"] = i
        event["message"] = f"{event.get('message', 'test')} #{i}"
        events.append(event)

    return run_processor_with_events(processor, events, logger_instance)


def run_processor_edge_cases(
    processor: Processor, logger_instance: Optional[Any] = None
) -> Dict[str, Any]:
    """Test processor with edge case inputs.

    Args:
        processor: The processor to test
        logger_instance: Optional logger instance

    Returns:
        Dictionary with edge case test results
    """
    edge_cases = [
        {},  # Empty dict
        {"message": ""},  # Empty message
        {"message": None},  # None message
        {"level": "INVALID"},  # Invalid level
        {"very_long_key_" * 100: "test"},  # Very long key
        {
            "message": "test",
            "level": "INFO",
            **{f"key_{i}": f"value_{i}" for i in range(100)},
        },  # Many keys
    ]

    results: Dict[str, Any] = {}
    for i, edge_case in enumerate(edge_cases):
        case_name = f"edge_case_{i}"
        try:
            result = simple_processor_execution(
                processor, logger_instance, "info", edge_case
            )
            results[case_name] = {"success": True, "result": result, "error": None}
        except Exception as e:
            results[case_name] = {"success": False, "result": None, "error": str(e)}

    return results


def benchmark_processor_performance(
    processor: Processor,
    event: Dict[str, Any],
    iterations: int = 10000,
    logger_instance: Optional[Any] = None,
) -> Dict[str, float]:
    """Benchmark processor performance.

    Args:
        processor: The processor to benchmark
        event: Event to process repeatedly
        iterations: Number of iterations to run
        logger_instance: Optional logger instance

    Returns:
        Dictionary with performance metrics
    """
    durations = []

    for _ in range(iterations):
        start_time = time.time()
        try:
            simple_processor_execution(processor, logger_instance, "info", event)
        except Exception:
            # Continue benchmarking even if some events fail
            pass
        durations.append(time.time() - start_time)

    return {
        "total_iterations": iterations,
        "total_time": sum(durations),
        "average_duration": sum(durations) / len(durations),
        "min_duration": min(durations),
        "max_duration": max(durations),
        "median_duration": sorted(durations)[len(durations) // 2],
    }
