"""Performance testing utilities for fapilog processors."""

import time
from typing import Any, Dict

from .._internal.processor import Processor
from .._internal.processor_error_handling import simple_processor_execution


def measure_processor_throughput(
    processor: Processor,
    event: Dict[str, Any],
    duration_seconds: int = 5,
    logger_instance: Any = None,
) -> Dict[str, float]:
    """Measure processor throughput (events per second).

    Args:
        processor: The processor to test
        event: Event to process repeatedly
        duration_seconds: How long to run the test
        logger_instance: Logger instance to use

    Returns:
        Dictionary with throughput metrics
    """
    end_time = time.time() + duration_seconds
    processed_count = 0
    error_count = 0

    while time.time() < end_time:
        try:
            simple_processor_execution(processor, logger_instance, "info", event)
            processed_count += 1
        except Exception:
            error_count += 1

    actual_duration = duration_seconds
    throughput = processed_count / actual_duration if actual_duration > 0 else 0

    return {
        "processed_events": processed_count,
        "errors": error_count,
        "duration_seconds": actual_duration,
        "throughput_eps": throughput,
        "error_rate": error_count / (processed_count + error_count)
        if (processed_count + error_count) > 0
        else 0,
    }


def measure_processor_latency(
    processor: Processor,
    event: Dict[str, Any],
    iterations: int = 1000,
    logger_instance: Any = None,
) -> Dict[str, float]:
    """Measure processor latency (time per event).

    Args:
        processor: The processor to test
        event: Event to process repeatedly
        iterations: Number of iterations to run
        logger_instance: Logger instance to use

    Returns:
        Dictionary with latency metrics in milliseconds
    """
    latencies = []

    for _ in range(iterations):
        start_time = time.time()
        try:
            simple_processor_execution(processor, logger_instance, "info", event)
        except Exception:
            # Still measure time even for failed operations
            pass
        latency_ms = (time.time() - start_time) * 1000
        latencies.append(latency_ms)

    if not latencies:
        return {
            "avg_latency_ms": 0.0,
            "min_latency_ms": 0.0,
            "max_latency_ms": 0.0,
            "p50_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "p99_latency_ms": 0.0,
        }

    latencies.sort()
    total_latencies = len(latencies)

    return {
        "avg_latency_ms": sum(latencies) / total_latencies,
        "min_latency_ms": latencies[0],
        "max_latency_ms": latencies[-1],
        "p50_latency_ms": latencies[int(total_latencies * 0.5)],
        "p95_latency_ms": latencies[int(total_latencies * 0.95)],
        "p99_latency_ms": latencies[int(total_latencies * 0.99)],
    }


def stress_test_processor_memory(
    processor: Processor,
    base_event: Dict[str, Any],
    iterations: int = 10000,
    logger_instance: Any = None,
) -> Dict[str, Any]:
    """Stress test processor with varying event sizes for memory performance.

    Args:
        processor: The processor to test
        base_event: Base event to modify
        iterations: Number of iterations per event size
        logger_instance: Logger instance to use

    Returns:
        Dictionary with memory stress test results
    """
    results = {}

    # Test with different event sizes
    event_sizes = ["small", "medium", "large", "xlarge"]
    size_multipliers = [1, 10, 100, 1000]

    for size_name, multiplier in zip(event_sizes, size_multipliers):
        # Create event with varying data size
        test_event = base_event.copy()
        test_event["stress_data"] = "x" * (100 * multiplier)
        test_event["stress_list"] = list(range(10 * multiplier))

        start_time = time.time()
        processed = 0
        errors = 0

        for _ in range(iterations):
            try:
                simple_processor_execution(
                    processor, logger_instance, "info", test_event
                )
                processed += 1
            except Exception:
                errors += 1

        duration = time.time() - start_time

        results[size_name] = {
            "event_size_category": size_name,
            "processed_events": processed,
            "error_count": errors,
            "duration_seconds": duration,
            "throughput_eps": processed / duration if duration > 0 else 0,
            "avg_time_per_event_ms": (duration / processed * 1000)
            if processed > 0
            else 0,
        }

    return results


def load_test_processor_concurrent(
    processor: Processor,
    event: Dict[str, Any],
    total_events: int = 50000,
    logger_instance: Any = None,
) -> Dict[str, Any]:
    """Load test processor with high event volume.

    Args:
        processor: The processor to test
        event: Event to process repeatedly
        total_events: Total number of events to process
        logger_instance: Logger instance to use

    Returns:
        Dictionary with load test results
    """
    start_time = time.time()
    processed = 0
    errors = 0
    latencies = []

    # Process events in batches to track performance over time
    batch_size = 1000
    batch_results = []

    for batch_start in range(0, total_events, batch_size):
        batch_end = min(batch_start + batch_size, total_events)
        batch_processed = 0
        batch_errors = 0
        batch_start_time = time.time()

        for _ in range(batch_start, batch_end):
            event_start = time.time()
            try:
                simple_processor_execution(processor, logger_instance, "info", event)
                batch_processed += 1
                processed += 1
            except Exception:
                batch_errors += 1
                errors += 1

            event_latency = (time.time() - event_start) * 1000
            latencies.append(event_latency)

        batch_duration = time.time() - batch_start_time
        batch_results.append(
            {
                "batch_start": batch_start,
                "batch_end": batch_end,
                "processed": batch_processed,
                "errors": batch_errors,
                "duration_seconds": batch_duration,
                "throughput_eps": batch_processed / batch_duration
                if batch_duration > 0
                else 0,
            }
        )

    total_duration = time.time() - start_time

    return {
        "total_events": total_events,
        "processed_events": processed,
        "error_count": errors,
        "total_duration_seconds": total_duration,
        "overall_throughput_eps": processed / total_duration
        if total_duration > 0
        else 0,
        "error_rate": errors / total_events if total_events > 0 else 0,
        "batch_results": batch_results,
        "latency_stats": {
            "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
            "min_latency_ms": min(latencies) if latencies else 0,
            "max_latency_ms": max(latencies) if latencies else 0,
        },
    }


def profile_processor_resource_usage(
    processor: Processor,
    event: Dict[str, Any],
    duration_seconds: int = 30,
    logger_instance: Any = None,
) -> Dict[str, Any]:
    """Profile processor resource usage over time.

    Args:
        processor: The processor to test
        event: Event to process repeatedly
        duration_seconds: How long to run the profiling
        logger_instance: Logger instance to use

    Returns:
        Dictionary with resource usage profile
    """
    import os

    import psutil

    process = psutil.Process(os.getpid())

    # Baseline measurements
    baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
    baseline_cpu = process.cpu_percent()

    start_time = time.time()
    end_time = start_time + duration_seconds

    processed = 0
    errors = 0
    memory_samples = []
    cpu_samples = []

    while time.time() < end_time:
        # Process some events
        for _ in range(100):  # Process in small batches
            try:
                simple_processor_execution(processor, logger_instance, "info", event)
                processed += 1
            except Exception:
                errors += 1

        # Sample resource usage
        memory_mb = process.memory_info().rss / 1024 / 1024
        cpu_percent = process.cpu_percent()

        memory_samples.append(memory_mb)
        cpu_samples.append(cpu_percent)

    actual_duration = time.time() - start_time

    return {
        "duration_seconds": actual_duration,
        "processed_events": processed,
        "error_count": errors,
        "throughput_eps": processed / actual_duration if actual_duration > 0 else 0,
        "baseline_memory_mb": baseline_memory,
        "baseline_cpu_percent": baseline_cpu,
        "memory_stats": {
            "avg_memory_mb": sum(memory_samples) / len(memory_samples)
            if memory_samples
            else 0,
            "max_memory_mb": max(memory_samples) if memory_samples else 0,
            "min_memory_mb": min(memory_samples) if memory_samples else 0,
            "memory_growth_mb": (max(memory_samples) - baseline_memory)
            if memory_samples
            else 0,
        },
        "cpu_stats": {
            "avg_cpu_percent": sum(cpu_samples) / len(cpu_samples)
            if cpu_samples
            else 0,
            "max_cpu_percent": max(cpu_samples) if cpu_samples else 0,
            "min_cpu_percent": min(cpu_samples) if cpu_samples else 0,
        },
    }


def run_processor_performance_suite(
    processor: Processor,
    test_event: Dict[str, Any],
    logger_instance: Any = None,
) -> Dict[str, Any]:
    """Run a comprehensive processor performance test suite.

    Args:
        processor: The processor to test
        test_event: Event to use for testing
        logger_instance: Logger instance to use

    Returns:
        Dictionary with complete performance results
    """
    results = {}

    # Throughput test
    print("Running throughput test...")
    results["throughput"] = measure_processor_throughput(
        processor, test_event, duration_seconds=5, logger_instance=logger_instance
    )

    # Latency test
    print("Running latency test...")
    results["latency"] = measure_processor_latency(
        processor, test_event, iterations=1000, logger_instance=logger_instance
    )

    # Memory stress test
    print("Running memory stress test...")
    results["memory_stress"] = stress_test_processor_memory(
        processor, test_event, iterations=1000, logger_instance=logger_instance
    )

    # Load test
    print("Running load test...")
    results["load_test"] = load_test_processor_concurrent(
        processor, test_event, total_events=10000, logger_instance=logger_instance
    )

    # Resource profiling
    print("Running resource profiling...")
    results["resource_profile"] = profile_processor_resource_usage(
        processor, test_event, duration_seconds=10, logger_instance=logger_instance
    )

    return results
