"""
Example demonstrating processor performance monitoring in fapilog.

This example shows how to:
1. Enable processor metrics collection
2. Monitor processor performance in real-time
3. Check processor health status
4. Get comprehensive performance summaries
5. Reset metrics for fresh monitoring periods
"""

import asyncio
import time
from typing import Any, Dict, Optional

from fapilog import configure_logging, log
from fapilog._internal.processor import Processor
from fapilog.monitoring import (
    get_processor_health_status,
    get_processor_performance_stats,
    get_processor_summary,
    reset_processor_metrics,
)
from fapilog.settings import LoggingSettings


class CustomSlowProcessor(Processor):
    """Example custom processor that introduces artificial delay."""

    def __init__(self, delay_ms: float = 10.0):
        """Initialize processor with configurable delay."""
        self.delay_ms = delay_ms
        super().__init__()

    def process(
        self, logger, method_name: str, event_dict: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Process event with artificial delay."""
        # Simulate processing time
        time.sleep(self.delay_ms / 1000.0)

        # Add processing metadata
        event_dict["processed_by"] = "CustomSlowProcessor"
        event_dict["processing_delay_ms"] = self.delay_ms

        return event_dict


class CustomFailingProcessor(Processor):
    """Example processor that fails occasionally for testing."""

    def __init__(self, failure_rate: float = 0.1):
        """Initialize processor with configurable failure rate."""
        self.failure_rate = failure_rate
        self.call_count = 0
        super().__init__()

    def process(
        self, logger, method_name: str, event_dict: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Process event with occasional failures."""
        self.call_count += 1

        # Fail at specified rate
        if self.call_count % int(1 / self.failure_rate) == 0:
            raise RuntimeError(f"Simulated failure (call #{self.call_count})")

        event_dict["processed_by"] = "CustomFailingProcessor"
        event_dict["call_count"] = self.call_count

        return event_dict


def example_basic_monitoring():
    """Basic example of enabling processor metrics."""
    print("=== Basic Processor Monitoring ===")

    # Enable processor metrics
    settings = LoggingSettings(
        enable_processor_metrics=True,
        level="INFO",
        enable_sinks=["stdout"],
    )

    configure_logging(settings=settings)

    # Generate some log events
    print("Generating log events...")
    for i in range(10):
        log.info("Processing item", item_id=i, category="example")

    # Check processor performance
    stats = get_processor_performance_stats()
    print("\nProcessor Performance Stats:")
    for processor, metrics in stats.items():
        print(f"  {processor}:")
        print(f"    Total executions: {metrics['total_executions']}")
        print(f"    Success rate: {metrics['success_rate']:.1f}%")
        print(f"    Average latency: {metrics['average_latency_ms']:.2f}ms")
        print(f"    Total bytes processed: {metrics['total_bytes_processed']}")

    return stats


def example_health_monitoring():
    """Example of monitoring processor health status."""
    print("\n=== Processor Health Monitoring ===")

    # Reset metrics for clean start
    reset_processor_metrics()

    settings = LoggingSettings(
        enable_processor_metrics=True,
        level="INFO",
        enable_sinks=["stdout"],
    )

    configure_logging(settings=settings)

    # Simulate different processor behaviors
    print("Simulating normal processing...")
    for i in range(20):
        log.info("Normal processing", iteration=i)

    # Check health status
    health = get_processor_health_status()
    print("\nProcessor Health Status:")
    for processor, status in health.items():
        print(f"  {processor}: {status}")

    return health


def example_custom_processor_monitoring():
    """Example using custom processors with different performance characteristics."""
    print("\n=== Custom Processor Monitoring ===")

    # Reset metrics
    reset_processor_metrics()

    # Configure with processor metrics enabled
    settings = LoggingSettings(
        enable_processor_metrics=True,
        level="INFO",
        enable_sinks=["stdout"],
        processor_metrics_include_enrichers=True,
    )

    logger = configure_logging(settings=settings)

    # Add custom processors with metrics wrapping
    from fapilog._internal.processor_metrics import wrap_processor_with_metrics

    slow_processor = wrap_processor_with_metrics(CustomSlowProcessor(delay_ms=50))
    failing_processor = wrap_processor_with_metrics(
        CustomFailingProcessor(failure_rate=0.2)
    )

    print("Processing with custom processors...")

    # Process events through custom processors
    for i in range(25):
        event_dict = {
            "level": "INFO",
            "message": f"Custom processing {i}",
            "iteration": i,
        }

        try:
            # Process through slow processor
            slow_processor(logger, "info", event_dict.copy())

            # Process through failing processor
            failing_processor(logger, "info", event_dict.copy())

        except RuntimeError as e:
            # Expected failures from failing processor
            print(f"    Expected failure: {e}")

    # Get comprehensive stats
    stats = get_processor_performance_stats()
    health = get_processor_health_status()
    summary = get_processor_summary()

    print("\nCustom Processor Results:")
    print(f"  Total processors tracked: {summary['total_processors']}")
    print(f"  Healthy processors: {summary['healthy_processors']}")
    print(f"  Slow processors: {summary['slow_processors']}")
    print(f"  Unhealthy processors: {summary['unhealthy_processors']}")
    print(f"  Overall success rate: {summary['overall_success_rate']:.1f}%")

    print("\nDetailed Performance:")
    for processor, metrics in stats.items():
        status = health.get(processor, "unknown")
        print(f"  {processor} ({status}):")
        print(f"    Executions: {metrics['total_executions']}")
        print(f"    Success rate: {metrics['success_rate']:.1f}%")
        print(f"    Avg latency: {metrics['average_latency_ms']:.2f}ms")
        print(
            f"    Min/Max latency: {metrics['min_latency_ms']:.2f}/{metrics['max_latency_ms']:.2f}ms"
        )
        if metrics.get("error_counts"):
            print(f"    Error types: {list(metrics['error_counts'].keys())}")

    return summary


def example_performance_thresholds():
    """Example demonstrating performance threshold detection."""
    print("\n=== Performance Threshold Detection ===")

    # Reset metrics
    reset_processor_metrics()

    settings = LoggingSettings(
        enable_processor_metrics=True,
        level="INFO",
        enable_sinks=["stdout"],
    )

    logger = configure_logging(settings=settings)

    # Create processors with different performance characteristics
    from fapilog._internal.processor_metrics import wrap_processor_with_metrics

    # Fast processor (should be healthy)
    fast_processor = wrap_processor_with_metrics(CustomSlowProcessor(delay_ms=5))

    # Slow processor (should be marked as slow)
    slow_processor = wrap_processor_with_metrics(CustomSlowProcessor(delay_ms=150))

    # Failing processor (should be unhealthy)
    failing_processor = wrap_processor_with_metrics(
        CustomFailingProcessor(failure_rate=0.3)
    )

    print("Testing performance thresholds...")

    # Generate events for each processor type
    base_event = {"level": "INFO", "message": "threshold test"}

    # Fast processor - many quick executions
    for i in range(20):
        fast_processor(
            logger, "info", {**base_event, "processor": "fast", "iteration": i}
        )

    # Slow processor - fewer slow executions
    for i in range(5):
        slow_processor(
            logger, "info", {**base_event, "processor": "slow", "iteration": i}
        )

    # Failing processor - mixed success/failure
    for i in range(15):
        try:
            failing_processor(
                logger, "info", {**base_event, "processor": "failing", "iteration": i}
            )
        except RuntimeError:
            pass  # Expected failures

    # Analyze results
    health = get_processor_health_status()
    stats = get_processor_performance_stats()

    print("\nThreshold Analysis:")
    for processor, status in health.items():
        metrics = stats[processor]
        print(f"  {processor}:")
        print(f"    Status: {status}")
        print(
            f"    Avg latency: {metrics['average_latency_ms']:.2f}ms (threshold: 100ms)"
        )
        print(f"    Failure rate: {metrics['failure_rate']:.1f}% (threshold: 10%)")

        # Explain status reasoning
        if status == "slow":
            print("    → Marked slow due to latency > 100ms")
        elif status == "unhealthy":
            print("    → Marked unhealthy due to failure rate > 10%")
        elif status == "healthy":
            print("    → Healthy - within all thresholds")


def example_metrics_reset_and_intervals():
    """Example demonstrating metrics reset functionality."""
    print("\n=== Metrics Reset and Intervals ===")

    # Configure with automatic reset interval
    settings = LoggingSettings(
        enable_processor_metrics=True,
        processor_metrics_reset_interval=5,  # Reset every 5 seconds
        level="INFO",
        enable_sinks=["stdout"],
    )

    configure_logging(settings=settings)

    print("Generating initial metrics...")
    for i in range(10):
        log.info("Initial batch", batch=1, iteration=i)

    initial_stats = get_processor_performance_stats()
    print(
        f"Initial execution count: {sum(s['total_executions'] for s in initial_stats.values())}"
    )

    # Manual reset
    print("\nResetting metrics manually...")
    reset_processor_metrics()

    after_reset_stats = get_processor_performance_stats()
    print(
        f"After reset execution count: {sum(s['total_executions'] for s in after_reset_stats.values())}"
    )

    # Generate new metrics
    print("Generating new metrics after reset...")
    for i in range(15):
        log.info("Second batch", batch=2, iteration=i)

    final_stats = get_processor_performance_stats()
    print(
        f"Final execution count: {sum(s['total_executions'] for s in final_stats.values())}"
    )

    # Reset specific processor (if multiple exist)
    processor_names = list(final_stats.keys())
    if len(processor_names) > 1:
        target_processor = processor_names[0]
        print(f"\nResetting metrics for specific processor: {target_processor}")
        reset_processor_metrics(target_processor)

        partial_reset_stats = get_processor_performance_stats()
        print(f"Remaining processors: {list(partial_reset_stats.keys())}")


async def example_async_monitoring():
    """Example of monitoring processors in async context."""
    print("\n=== Async Processor Monitoring ===")

    reset_processor_metrics()

    settings = LoggingSettings(
        enable_processor_metrics=True,
        level="INFO",
        enable_sinks=["stdout"],
    )

    configure_logging(settings=settings)

    async def background_monitoring():
        """Background task to periodically report metrics."""
        while True:
            await asyncio.sleep(2)
            summary = get_processor_summary()
            if summary.get("total_executions", 0) > 0:
                print(
                    f"  [Monitor] Total executions: {summary['total_executions']}, "
                    f"Success rate: {summary.get('overall_success_rate', 0):.1f}%"
                )

    async def log_generator():
        """Generate logs with async delays."""
        for i in range(30):
            log.info("Async processing", async_id=i, timestamp=time.time())
            await asyncio.sleep(0.1)  # Small async delay

    print("Starting async monitoring...")

    # Run monitoring and log generation concurrently
    monitor_task = asyncio.create_task(background_monitoring())
    log_task = asyncio.create_task(log_generator())

    # Wait for log generation to complete
    await log_task

    # Cancel monitoring and get final stats
    monitor_task.cancel()

    final_summary = get_processor_summary()
    print("\nAsync monitoring complete:")
    print(f"  Total processors: {final_summary['total_processors']}")
    print(f"  Total executions: {final_summary['total_executions']}")
    print(f"  Average latency: {final_summary['average_latency_ms']:.2f}ms")


def main():
    """Run all processor monitoring examples."""
    print("Processor Performance Monitoring Examples")
    print("=========================================")

    try:
        # Basic monitoring
        example_basic_monitoring()

        # Health monitoring
        example_health_monitoring()

        # Custom processors
        example_custom_processor_monitoring()

        # Performance thresholds
        example_performance_thresholds()

        # Metrics reset
        example_metrics_reset_and_intervals()

        # Async monitoring
        print("\nRunning async example...")
        asyncio.run(example_async_monitoring())

        print("\n✅ All processor monitoring examples completed successfully!")

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
