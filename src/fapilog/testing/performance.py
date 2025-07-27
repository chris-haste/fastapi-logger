"""Performance testing helpers for custom sinks."""

import asyncio
import statistics
import time
from typing import Any, Dict, List

from ..sinks import Sink


class SinkPerformanceTester:
    """Test performance characteristics of custom sinks."""

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

    async def test_throughput(self, sink: Sink, num_events: int = 1000) -> float:
        """Test events per second throughput.

        Args:
            sink: Sink instance to test
            num_events: Number of events to send

        Returns:
            Events per second throughput
        """
        # Generate test events
        events = [self._create_test_event(i) for i in range(num_events)]

        start_time = time.time()

        # Send events
        for event in events:
            await sink.write(event)

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
        self, sink: Sink, num_events: int = 1000, concurrency: int = 10
    ) -> float:
        """Test concurrent throughput.

        Args:
            sink: Sink instance to test
            num_events: Total number of events
            concurrency: Number of concurrent tasks

        Returns:
            Events per second throughput
        """
        events_per_task = num_events // concurrency
        remaining_events = num_events % concurrency

        async def write_batch(start_idx: int, count: int) -> None:
            for i in range(count):
                event = self._create_test_event(start_idx + i)
                await sink.write(event)

        start_time = time.time()

        # Create tasks
        tasks = []
        start_idx = 0

        for i in range(concurrency):
            count = events_per_task
            if i < remaining_events:
                count += 1

            task = asyncio.create_task(write_batch(start_idx, count))
            tasks.append(task)
            start_idx += count

        # Wait for all tasks
        await asyncio.gather(*tasks)

        duration = time.time() - start_time
        throughput = num_events / duration if duration > 0 else 0

        # Store metrics
        self.metrics["concurrent_throughput"] = {
            "events_per_second": throughput,
            "total_events": num_events,
            "duration_seconds": duration,
            "concurrency": concurrency,
            "test_type": "concurrent",
        }

        return throughput

    async def test_latency(
        self, sink: Sink, num_samples: int = 100
    ) -> Dict[str, float]:
        """Test write latency statistics.

        Args:
            sink: Sink instance to test
            num_samples: Number of latency samples to collect

        Returns:
            Dictionary with latency statistics
        """
        latencies = []

        for i in range(num_samples):
            event = self._create_test_event(i)
            start = time.time()
            await sink.write(event)
            latency = time.time() - start
            latencies.append(latency)

        # Calculate statistics
        result = {
            "mean_ms": statistics.mean(latencies) * 1000,
            "median_ms": statistics.median(latencies) * 1000,
            "min_ms": min(latencies) * 1000,
            "max_ms": max(latencies) * 1000,
            "std_dev_ms": statistics.stdev(latencies) * 1000
            if len(latencies) > 1
            else 0,
        }

        # Add percentiles if we have enough samples
        if len(latencies) >= 10:
            sorted_latencies = sorted(latencies)
            result["p50_ms"] = statistics.median(sorted_latencies) * 1000
            result["p90_ms"] = sorted_latencies[int(0.9 * len(sorted_latencies))] * 1000
            result["p95_ms"] = (
                sorted_latencies[int(0.95 * len(sorted_latencies))] * 1000
            )
            result["p99_ms"] = (
                sorted_latencies[int(0.99 * len(sorted_latencies))] * 1000
            )

        # Store metrics
        self.metrics["latency"] = result
        self.metrics["latency"]["num_samples"] = num_samples

        return result

    async def test_memory_usage(
        self, sink: Sink, num_events: int = 1000
    ) -> Dict[str, Any]:
        """Test memory usage during operation.

        Args:
            sink: Sink instance to test
            num_events: Number of events to process

        Returns:
            Dictionary with memory usage statistics
        """
        try:
            import psutil

            process = psutil.Process()
        except ImportError:
            return {
                "error": "psutil not available for memory testing",
                "initial_memory_bytes": 0,
                "final_memory_bytes": 0,
                "memory_delta_bytes": 0,
            }

        # Get initial memory
        initial_memory = process.memory_info().rss

        # Process events
        for i in range(num_events):
            event = self._create_test_event(i)
            await sink.write(event)

        # Get final memory
        final_memory = process.memory_info().rss
        memory_delta = final_memory - initial_memory

        result = {
            "initial_memory_bytes": initial_memory,
            "final_memory_bytes": final_memory,
            "memory_delta_bytes": memory_delta,
            "memory_per_event_bytes": memory_delta / num_events
            if num_events > 0
            else 0,
            "num_events": num_events,
        }

        # Store metrics
        self.metrics["memory"] = result

        return result

    async def test_batch_performance(
        self, sink: Sink, batch_sizes: List[int] = None, events_per_batch: int = 100
    ) -> Dict[int, Dict[str, float]]:
        """Test performance with different batch sizes.

        Args:
            sink: Sink instance to test
            batch_sizes: List of batch sizes to test
            events_per_batch: Events per batch test

        Returns:
            Dictionary mapping batch size to performance metrics
        """
        if batch_sizes is None:
            batch_sizes = [1, 5, 10, 20, 50, 100]

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
                # If sink supports batch operations, use it
                if hasattr(sink, "write_batch"):
                    await sink.write_batch(batch)
                else:
                    # Otherwise, write events individually
                    for event in batch:
                        await sink.write(event)

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
        self, sink: Sink, test_config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Run a comprehensive performance test suite.

        Args:
            sink: Sink instance to test
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
                "batch_sizes": [1, 10, 50, 100],
                "batch_events_per_size": 50,
            }

        start_time = time.time()

        # Run all tests
        print("Running throughput test...")
        throughput = await self.test_throughput(sink, test_config["throughput_events"])

        print("Running concurrent throughput test...")
        concurrent_throughput = await self.test_concurrent_throughput(
            sink, test_config["concurrent_events"], test_config["concurrent_workers"]
        )

        print("Running latency test...")
        latency = await self.test_latency(sink, test_config["latency_samples"])

        print("Running memory test...")
        memory = await self.test_memory_usage(sink, test_config["memory_events"])

        print("Running batch performance test...")
        batch_perf = await self.test_batch_performance(
            sink, test_config["batch_sizes"], test_config["batch_events_per_size"]
        )

        total_duration = time.time() - start_time

        # Compile comprehensive results
        results = {
            "test_duration_seconds": total_duration,
            "sink_type": type(sink).__name__,
            "test_config": test_config,
            "throughput": {
                "sequential_eps": throughput,
                "concurrent_eps": concurrent_throughput,
            },
            "latency": latency,
            "memory": memory,
            "batch_performance": batch_perf,
            "summary": {
                "best_sequential_throughput": throughput,
                "best_concurrent_throughput": concurrent_throughput,
                "average_latency_ms": latency.get("mean_ms", 0),
                "p95_latency_ms": latency.get("p95_ms", 0),
                "memory_delta_mb": memory.get("memory_delta_bytes", 0) / 1024 / 1024,
            },
        }

        # Store comprehensive results
        self.metrics["comprehensive"] = results

        return results

    def get_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics.

        Returns:
            Dictionary of all collected metrics
        """
        return self.metrics.copy()

    def clear_metrics(self) -> None:
        """Clear all collected metrics."""
        self.metrics.clear()

    def print_summary(self) -> None:
        """Print a human-readable summary of performance metrics."""
        if not self.metrics:
            print("No performance metrics available.")
            return

        print("\n=== Sink Performance Test Results ===")

        if "throughput" in self.metrics:
            throughput = self.metrics["throughput"]
            print("\nSequential Throughput:")
            print(f"  Events/sec: {throughput['events_per_second']:.2f}")
            print(f"  Duration: {throughput['duration_seconds']:.3f}s")

        if "concurrent_throughput" in self.metrics:
            conc = self.metrics["concurrent_throughput"]
            print("\nConcurrent Throughput:")
            print(f"  Events/sec: {conc['events_per_second']:.2f}")
            print(f"  Concurrency: {conc['concurrency']}")
            print(f"  Duration: {conc['duration_seconds']:.3f}s")

        if "latency" in self.metrics:
            latency = self.metrics["latency"]
            print("\nLatency Statistics:")
            print(f"  Mean: {latency['mean_ms']:.3f}ms")
            print(f"  Median: {latency['median_ms']:.3f}ms")
            if "p95_ms" in latency:
                print(f"  P95: {latency['p95_ms']:.3f}ms")

        if "memory" in self.metrics:
            memory = self.metrics["memory"]
            if "error" not in memory:
                delta_mb = memory["memory_delta_bytes"] / 1024 / 1024
                print("\nMemory Usage:")
                print(f"  Delta: {delta_mb:.2f} MB")
                print(f"  Per event: {memory['memory_per_event_bytes']:.0f} bytes")

        print("\n" + "=" * 40)
