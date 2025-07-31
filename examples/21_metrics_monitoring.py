"""Example: Metrics Collection and Monitoring

This example demonstrates how to:
1. Enable metrics collection
2. Set up a Prometheus metrics exporter
3. Monitor logging performance
4. Access metrics programmatically
"""

import asyncio
from typing import Any, Dict

# Import fapilog components
from fapilog.monitoring import (
    get_metrics_dict,
    get_metrics_text,
)
from fapilog.settings import LoggingSettings


class MetricsExample:
    """Example demonstrating metrics collection and monitoring."""

    def __init__(self):
        """Initialize the metrics example."""
        self.logger = None
        self.container = None
        self.metrics_collector = None
        self.prometheus_exporter = None

    async def setup_logging_with_metrics(self):
        """Set up logging with metrics collection enabled."""
        # Configure logging settings with metrics enabled
        settings = LoggingSettings(
            level="INFO",
            sinks=["stdout", "file:///tmp/metrics_example.log"],
            json_console="json",
            queue_enabled=True,
            queue_batch_size=5,
            queue_batch_timeout=1.0,
            # Enable metrics collection
            metrics_enabled=True,
            metrics_sample_window=50,
            # Enable Prometheus exporter
            metrics_prometheus_enabled=True,
            metrics_prometheus_port=8001,
            metrics_prometheus_host="0.0.0.0",
        )

        # Create logger and container using the new API
        from fapilog.bootstrap import create_logger

        self.logger, self.container = create_logger(settings)

        # Get metrics collector from container
        self.metrics_collector = self.container.get_metrics_collector()

        # Create Prometheus exporter with container for metrics access
        from fapilog.monitoring import PrometheusExporter

        self.prometheus_exporter = PrometheusExporter(
            host="0.0.0.0",
            port=8001,
            path="/metrics",
            enabled=True,
            container=self.container,
        )

        # Start Prometheus exporter
        try:
            await self.prometheus_exporter.start()
            print(
                f"Prometheus metrics available at: "
                f"{self.prometheus_exporter.get_metrics_url()}"
            )
        except Exception as e:
            print(f"Could not start Prometheus exporter: {e}")
            print("(This is expected if FastAPI/uvicorn is not installed)")

    async def generate_sample_logs(self):
        """Generate sample log messages to populate metrics."""
        print("\n--- Generating sample log messages ---")

        # Generate various types of log messages
        for i in range(20):
            await asyncio.sleep(0.1)  # Small delay between logs

            if i % 5 == 0:
                self.logger.error(
                    "Error message",
                    extra={
                        "error_code": f"E{i:03d}",
                        "user_id": f"user_{i % 3}",
                        "operation": "database_query",
                    },
                )
            elif i % 3 == 0:
                self.logger.warning(
                    "Warning message",
                    extra={
                        "warning_code": f"W{i:03d}",
                        "resource": "memory",
                        "threshold": 85.5,
                    },
                )
            else:
                self.logger.info(
                    "Info message",
                    extra={
                        "request_id": f"req_{i:04d}",
                        "endpoint": f"/api/v1/endpoint_{i % 4}",
                        "response_time_ms": 50 + (i * 10) % 200,
                    },
                )

        # Wait a bit for queue processing
        await asyncio.sleep(2.0)
        print("Sample log generation completed")

    def display_metrics_summary(self):
        """Display a summary of collected metrics."""
        if not self.metrics_collector or not self.metrics_collector.is_enabled():
            print("Metrics collection is not enabled")
            return

        print("\n--- Metrics Summary ---")

        # Get all metrics
        all_metrics = self.metrics_collector.get_all_metrics()

        # Display queue metrics
        queue_metrics = all_metrics.get("queue", {})
        print("\nQueue Metrics:")
        print(f"  Current Size: {queue_metrics.get('size', 0)}")
        print(f"  Peak Size: {queue_metrics.get('peak_size', 0)}")
        print(f"  Total Enqueued: {queue_metrics.get('total_enqueued', 0)}")
        print(f"  Total Dequeued: {queue_metrics.get('total_dequeued', 0)}")
        print(f"  Total Dropped: {queue_metrics.get('total_dropped', 0)}")
        print(
            f"  Avg Enqueue Latency: "
            f"{queue_metrics.get('enqueue_latency_ms', 0):.2f} ms"
        )
        print(
            f"  Avg Batch Processing: "
            f"{queue_metrics.get('batch_processing_time_ms', 0):.2f} ms"
        )

        # Display sink metrics
        sink_metrics = all_metrics.get("sinks", {})
        print("\nSink Metrics:")
        for sink_name, metrics in sink_metrics.items():
            print(f"  {sink_name}:")
            print(f"    Total Writes: {metrics.get('total_writes', 0)}")
            print(f"    Success Rate: {metrics.get('success_rate', 0):.2%}")
            print(f"    Avg Latency: {metrics.get('avg_write_latency_ms', 0):.2f} ms")
            print(f"    Avg Batch Size: {metrics.get('avg_batch_size', 0):.1f}")
            if metrics.get("last_error"):
                print(f"    Last Error: {metrics.get('last_error')}")

        # Display performance metrics
        perf_metrics = all_metrics.get("performance", {})
        print("\nPerformance Metrics:")
        print(f"  Total Log Events: {perf_metrics.get('total_log_events', 0)}")
        print(f"  Events per Second: {perf_metrics.get('events_per_second', 0):.1f}")
        print(
            f"  Avg Processing Time: "
            f"{perf_metrics.get('avg_processing_time_ms', 0):.2f} ms"
        )
        print(
            f"  Memory Usage: "
            f"{perf_metrics.get('memory_usage_bytes', 0) / 1024 / 1024:.1f} MB"
        )
        print(f"  CPU Usage: {perf_metrics.get('cpu_usage_percent', 0):.1f}%")
        print(f"  Uptime: {perf_metrics.get('uptime_seconds', 0):.1f} seconds")

    def display_prometheus_metrics(self):
        """Display metrics in Prometheus format."""
        print("\n--- Prometheus Format Metrics ---")
        prometheus_text = get_metrics_text()

        # Show a subset of the metrics to avoid too much output
        lines = prometheus_text.split("\n")
        important_metrics = [
            "fapilog_queue_size",
            "fapilog_queue_enqueued_total",
            "fapilog_events_total",
            "fapilog_events_per_second",
            "fapilog_sink_writes_total",
            "fapilog_sink_success_rate",
        ]

        for line in lines:
            if any(metric in line for metric in important_metrics):
                print(line)

    async def demonstrate_error_scenarios(self):
        """Demonstrate how metrics capture error scenarios."""
        print("\n--- Demonstrating Error Scenarios ---")

        # Create a temporary failing sink to simulate errors
        class TemporaryFailingSink:
            def __init__(self):
                self.call_count = 0

            async def write(self, event_dict: Dict[str, Any]) -> None:
                self.call_count += 1
                if self.call_count % 3 == 0:  # Fail every 3rd call
                    raise Exception("Simulated sink failure")
                await asyncio.sleep(0.01)  # Simulate work

        # Note: In a real implementation, you would add this sink to the container
        # For this example, we'll just show what the metrics would look like
        print(
            "Note: This would normally involve adding a failing sink to the logging container"
        )
        print("The metrics would then show increased failure rates and retry counts")

    async def cleanup(self):
        """Clean up resources."""
        print("\n--- Cleaning up ---")

        if self.prometheus_exporter:
            await self.prometheus_exporter.stop()

        # Clean up the container
        if self.container:
            await self.container.shutdown()

        print("Cleanup completed")


async def main():
    """Main example function."""
    print("=== Fapilog Metrics Collection and Monitoring Example ===")

    example = MetricsExample()

    try:
        # Set up logging with metrics
        await example.setup_logging_with_metrics()

        print("\nLogging container set up with metrics collection enabled")
        print("You can monitor metrics at: http://localhost:8001/metrics")
        print("Health check available at: http://localhost:8001/health")

        # Generate sample logs
        await example.generate_sample_logs()

        # Display metrics
        example.display_metrics_summary()
        example.display_prometheus_metrics()

        # Demonstrate error scenarios
        await example.demonstrate_error_scenarios()

        # Keep running for a bit to allow monitoring
        print("\n--- Keeping service running for 30 seconds for monitoring ---")
        print("You can now:")
        print("1. Visit http://localhost:8001/metrics to see Prometheus metrics")
        print("2. Visit http://localhost:8001/health for health check")
        print("3. Use curl to fetch metrics: curl http://localhost:8001/metrics")

        # Generate some more logs during the monitoring period
        for i in range(10):
            await asyncio.sleep(3)
            example.logger.info(
                f"Monitoring message {i + 1}",
                extra={"monitoring": True, "iteration": i + 1},
            )

    except KeyboardInterrupt:
        print("\nExample interrupted by user")
    except Exception as e:
        print(f"Example failed with error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await example.cleanup()


def manual_metrics_access():
    """Demonstrate how to access metrics manually using container-scoped access."""
    print("\n=== Manual Metrics Access ===")

    print("Note: Global metrics functions now require container-scoped access.")
    print("For proper metrics access, use the container from your logging setup.")

    # Show what the global functions now return
    metrics_dict = get_metrics_dict()
    print(f"\nGlobal get_metrics_dict() now returns: {metrics_dict}")

    prometheus_text = get_metrics_text()
    print(f"Global get_metrics_text() now returns: {prometheus_text}")

    print("\nFor real metrics access, use:")
    print("  container = create_logging_container()")
    print("  metrics = container.get_metrics_collector()")
    print("  if metrics:")
    print("      metrics_dict = metrics.get_all_metrics()")
    print("      prometheus_text = metrics.get_prometheus_metrics()")


if __name__ == "__main__":
    # Run the async example
    asyncio.run(main())

    # Show manual access methods
    manual_metrics_access()
