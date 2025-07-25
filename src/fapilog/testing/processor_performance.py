"""Performance testing helpers for custom processors."""

import asyncio
import statistics
import time
from typing import Any, Dict, List

from .._internal.processor import Processor
from .._internal.processor_error_handling import safe_processor_execution


class ProcessorPerformanceTester:
    """Test performance characteristics of custom processors."""

    def __init__(self):
        self.metrics: Dict[str, Any] = {}
        self._test_events: List[Dict[str, Any]] = []

    def _create_test_event(self, index: int) -> Dict[str, Any]:
        """Create a test log event.

        Args:
            index: Event index for uniqueness

        Returns:
            Test event dictionary
        """
        return {
            "level": "info",
            "message": f"Performance test event {index}",
            "timestamp": time.time(),
            "test_index": index,
            "test_data": "x" * 100,  # Some payload
        }

    async def test_throughput(
        self, processor: Processor, num_events: int = 1000
    ) -> float:
        """Test events per second throughput.

        Args:
            processor: Processor instance to test
            num_events: Number of events to process

        Returns:
            Events per second throughput
        """
        # Start processor if needed
        if not processor.is_started:
            await processor.start()

        # Generate test events
        events = [self._create_test_event(i) for i in range(num_events)]

        start_time = time.time()

        # Process events
        for event in events:
            safe_processor_execution(processor, None, "info", event)

        duration = time.time() - start_time
        throughput = num_events / duration if duration > 0 else 0

        # Store metrics
        self.metrics["throughput"] = {
            "events_per_second": throughput,
            "total_events": num_events,
            "duration_seconds": duration,
            "test_type": "sequential",
        }

        return throughput

    async def test_concurrent_throughput(
        self, processor: Processor, num_events: int = 1000, num_workers: int = 10
    ) -> float:
        """Test concurrent processing throughput.

        Args:
            processor: Processor instance to test
            num_events: Total number of events to process
            num_workers: Number of concurrent workers

        Returns:
            Events per second throughput under concurrent load
        """
        # Start processor if needed
        if not processor.is_started:
            await processor.start()

        # Create batches for workers
        events_per_worker = num_events // num_workers
        batches = []

        for worker_id in range(num_workers):
            start_idx = worker_id * events_per_worker
            end_idx = start_idx + events_per_worker
            batch = [self._create_test_event(i) for i in range(start_idx, end_idx)]
            batches.append(batch)

        async def process_batch(batch: List[Dict[str, Any]]) -> int:
            """Process a batch of events."""
            count = 0
            for event in batch:
                safe_processor_execution(processor, None, "info", event)
                count += 1
            return count

        start_time = time.time()

        # Run workers concurrently
        tasks = [process_batch(batch) for batch in batches]
        results = await asyncio.gather(*tasks)

        duration = time.time() - start_time
        total_processed = sum(results)
        throughput = total_processed / duration if duration > 0 else 0

        # Store metrics
        self.metrics["concurrent_throughput"] = {
            "events_per_second": throughput,
            "total_events": total_processed,
            "duration_seconds": duration,
            "num_workers": num_workers,
            "events_per_worker": events_per_worker,
            "test_type": "concurrent",
        }

        return throughput

    async def test_latency(
        self, processor: Processor, num_samples: int = 100
    ) -> Dict[str, float]:
        """Test processing latency characteristics.

        Args:
            processor: Processor instance to test
            num_samples: Number of latency samples to collect

        Returns:
            Dictionary with latency statistics
        """
        # Start processor if needed
        if not processor.is_started:
            await processor.start()

        latencies = []

        for i in range(num_samples):
            event = self._create_test_event(i)

            start_time = time.time()
            safe_processor_execution(processor, None, "info", event)
            end_time = time.time()

            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)

        # Calculate statistics
        avg_latency = statistics.mean(latencies)
        median_latency = statistics.median(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)

        # Calculate percentiles
        sorted_latencies = sorted(latencies)
        p95_latency = sorted_latencies[int(0.95 * len(sorted_latencies))]
        p99_latency = sorted_latencies[int(0.99 * len(sorted_latencies))]

        latency_stats = {
            "avg_latency_ms": avg_latency,
            "median_latency_ms": median_latency,
            "min_latency_ms": min_latency,
            "max_latency_ms": max_latency,
            "p95_latency_ms": p95_latency,
            "p99_latency_ms": p99_latency,
            "num_samples": num_samples,
        }

        # Store metrics
        self.metrics["latency"] = latency_stats

        return latency_stats

    async def test_memory_usage(
        self, processor: Processor, num_events: int = 1000
    ) -> Dict[str, float]:
        """Test processor memory usage.

        Args:
            processor: Processor instance to test
            num_events: Number of events to process

        Returns:
            Dictionary with memory usage statistics
        """
        try:
            import os

            import psutil
        except ImportError:
            return {
                "error": "psutil not available for memory testing",
                "peak_memory_mb": 0,
                "memory_growth_mb": 0,
            }

        # Start processor if needed
        if not processor.is_started:
            await processor.start()

        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Process events
        events = [self._create_test_event(i) for i in range(num_events)]

        for event in events:
            safe_processor_execution(processor, None, "info", event)

        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory

        memory_stats = {
            "initial_memory_mb": initial_memory,
            "final_memory_mb": final_memory,
            "memory_growth_mb": memory_growth,
            "events_processed": num_events,
            "memory_per_event_kb": (memory_growth * 1024) / num_events
            if num_events > 0
            else 0,
        }

        # Store metrics
        self.metrics["memory"] = memory_stats

        return memory_stats

    async def test_cpu_usage(
        self, processor: Processor, duration_seconds: int = 30
    ) -> Dict[str, float]:
        """Test processor CPU usage.

        Args:
            processor: Processor instance to test
            duration_seconds: Duration to run the test

        Returns:
            Dictionary with CPU usage statistics
        """
        try:
            import os

            import psutil
        except ImportError:
            return {
                "error": "psutil not available for CPU testing",
                "avg_cpu_percent": 0,
                "peak_cpu_percent": 0,
            }

        # Start processor if needed
        if not processor.is_started:
            await processor.start()

        process = psutil.Process(os.getpid())
        cpu_samples = []

        end_time = time.time() + duration_seconds
        event_count = 0

        while time.time() < end_time:
            # Process some events
            for _ in range(10):  # Process in small batches
                event = self._create_test_event(event_count)
                safe_processor_execution(processor, None, "info", event)
                event_count += 1

            # Sample CPU usage
            cpu_percent = process.cpu_percent()
            if cpu_percent > 0:  # Only record valid samples
                cpu_samples.append(cpu_percent)

            # Small delay to allow CPU measurement
            await asyncio.sleep(0.1)

        if not cpu_samples:
            cpu_samples = [0.0]

        cpu_stats = {
            "avg_cpu_percent": statistics.mean(cpu_samples),
            "peak_cpu_percent": max(cpu_samples),
            "min_cpu_percent": min(cpu_samples),
            "duration_seconds": duration_seconds,
            "events_processed": event_count,
            "events_per_second": event_count / duration_seconds,
            "num_samples": len(cpu_samples),
        }

        # Store metrics
        self.metrics["cpu"] = cpu_stats

        return cpu_stats

    async def test_batch_performance(
        self,
        processor: Processor,
        batch_sizes: List[int] = None,
        events_per_batch: int = 100,
    ) -> Dict[int, Dict[str, float]]:
        """Test performance with different batch sizes.

        Args:
            processor: Processor instance to test
            batch_sizes: List of batch sizes to test
            events_per_batch: Events per batch test

        Returns:
            Dictionary mapping batch size to performance metrics
        """
        if batch_sizes is None:
            batch_sizes = [1, 5, 10, 20, 50, 100]

        # Start processor if needed
        if not processor.is_started:
            await processor.start()

        results = {}

        for batch_size in batch_sizes:
            # Create batches
            total_events = batch_size * events_per_batch
            batches = []

            for batch_idx in range(events_per_batch):
                batch = [
                    self._create_test_event(batch_idx * batch_size + i)
                    for i in range(batch_size)
                ]
                batches.append(batch)

            # Time batch processing
            start_time = time.time()

            for batch in batches:
                # Process events in the batch
                for event in batch:
                    safe_processor_execution(processor, None, "info", event)

            duration = time.time() - start_time
            throughput = total_events / duration if duration > 0 else 0

            results[batch_size] = {
                "throughput_eps": throughput,
                "duration_seconds": duration,
                "total_events": total_events,
                "num_batches": events_per_batch,
            }

        # Store metrics
        self.metrics["batch_performance"] = results

        return results

    async def run_comprehensive_test(
        self, processor: Processor, test_config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Run a comprehensive performance test suite.

        Args:
            processor: Processor instance to test
            test_config: Optional test configuration

        Returns:
            Complete performance test results
        """
        if test_config is None:
            test_config = {
                "throughput_events": 1000,
                "concurrent_events": 1000,
                "concurrent_workers": 10,
                "latency_samples": 100,
                "memory_events": 1000,
                "cpu_duration": 10,  # Reduced for testing
                "batch_sizes": [1, 10, 50, 100],
                "batch_events_per_size": 50,
            }

        start_time = time.time()

        # Run all tests
        print("Running throughput test...")
        throughput = await self.test_throughput(
            processor, test_config["throughput_events"]
        )

        print("Running concurrent throughput test...")
        concurrent_throughput = await self.test_concurrent_throughput(
            processor,
            test_config["concurrent_events"],
            test_config["concurrent_workers"],
        )

        print("Running latency test...")
        latency = await self.test_latency(processor, test_config["latency_samples"])

        print("Running memory test...")
        memory = await self.test_memory_usage(processor, test_config["memory_events"])

        print("Running CPU test...")
        cpu = await self.test_cpu_usage(processor, test_config["cpu_duration"])

        print("Running batch performance test...")
        batch_perf = await self.test_batch_performance(
            processor, test_config["batch_sizes"], test_config["batch_events_per_size"]
        )

        total_duration = time.time() - start_time

        # Compile comprehensive results
        results = {
            "processor_class": processor.__class__.__name__,
            "test_duration_seconds": total_duration,
            "throughput": {
                "sequential_eps": throughput,
                "concurrent_eps": concurrent_throughput,
            },
            "latency": latency,
            "memory": memory,
            "cpu": cpu,
            "batch_performance": batch_perf,
            "test_config": test_config,
        }

        # Store comprehensive metrics
        self.metrics["comprehensive"] = results

        # Print summary
        print("\nPerformance test summary:")
        print(f"  Sequential throughput: {throughput:.1f} events/sec")
        print(f"  Concurrent throughput: {concurrent_throughput:.1f} events/sec")
        print(f"  Average latency: {latency.get('avg_latency_ms', 0):.2f} ms")
        print(f"  Memory growth: {memory.get('memory_growth_mb', 0):.2f} MB")
        print(f"  Average CPU: {cpu.get('avg_cpu_percent', 0):.1f}%")

        return results

    def get_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics.

        Returns:
            Dictionary with all performance metrics
        """
        return self.metrics.copy()

    def clear_metrics(self) -> None:
        """Clear all collected metrics."""
        self.metrics.clear()

    def export_results(self, filename: str = None) -> str:
        """Export results to JSON format.

        Args:
            filename: Optional filename to save results

        Returns:
            JSON string of results
        """
        import json

        results_json = json.dumps(self.metrics, indent=2, default=str)

        if filename:
            with open(filename, "w") as f:
                f.write(results_json)

        return results_json

    def compare_processors(
        self, results: List[Dict[str, Any]], metric_name: str = "throughput"
    ) -> Dict[str, Any]:
        """Compare performance results from multiple processors.

        Args:
            results: List of performance test results
            metric_name: Metric to compare (throughput, latency, memory, cpu)

        Returns:
            Comparison results
        """
        if not results:
            return {"error": "No results to compare"}

        comparison = {
            "metric": metric_name,
            "processors": {},
            "best_performer": None,
            "worst_performer": None,
        }

        # Extract metrics for comparison
        for result in results:
            processor_name = result.get("processor_class", "Unknown")

            if metric_name == "throughput":
                value = result.get("throughput", {}).get("sequential_eps", 0)
            elif metric_name == "latency":
                value = result.get("latency", {}).get("avg_latency_ms", float("inf"))
            elif metric_name == "memory":
                value = result.get("memory", {}).get("memory_growth_mb", 0)
            elif metric_name == "cpu":
                value = result.get("cpu", {}).get("avg_cpu_percent", 0)
            else:
                value = 0

            comparison["processors"][processor_name] = value

        # Find best and worst performers
        if comparison["processors"]:
            if metric_name == "latency":  # Lower is better
                best_name = min(
                    comparison["processors"], key=comparison["processors"].get
                )
                worst_name = max(
                    comparison["processors"], key=comparison["processors"].get
                )
            else:  # Higher is better
                best_name = max(
                    comparison["processors"], key=comparison["processors"].get
                )
                worst_name = min(
                    comparison["processors"], key=comparison["processors"].get
                )

            comparison["best_performer"] = {
                "processor": best_name,
                "value": comparison["processors"][best_name],
            }
            comparison["worst_performer"] = {
                "processor": worst_name,
                "value": comparison["processors"][worst_name],
            }

        return comparison
