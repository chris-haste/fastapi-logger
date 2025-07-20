"""Metrics collection system for fapilog performance monitoring."""

import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, DefaultDict, Dict, Optional

# Optional dependency for resource monitoring
try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    psutil = None
    HAS_PSUTIL = False

logger = logging.getLogger(__name__)


@dataclass
class QueueMetrics:
    """Queue performance metrics."""

    size: int = 0
    peak_size: int = 0
    total_enqueued: int = 0
    total_dequeued: int = 0
    total_dropped: int = 0
    total_sampled: int = 0
    enqueue_latency_ms: float = 0.0
    dequeue_latency_ms: float = 0.0
    batch_processing_time_ms: float = 0.0
    memory_usage_bytes: int = 0


@dataclass
class SinkMetrics:
    """Sink performance metrics."""

    name: str = ""
    total_writes: int = 0
    total_successes: int = 0
    total_failures: int = 0
    total_retries: int = 0
    avg_write_latency_ms: float = 0.0
    avg_batch_size: float = 0.0
    memory_usage_bytes: int = 0
    last_error: Optional[str] = None
    last_error_time: Optional[float] = None


@dataclass
class PerformanceMetrics:
    """General performance metrics."""

    total_log_events: int = 0
    events_per_second: float = 0.0
    avg_processing_time_ms: float = 0.0
    memory_usage_bytes: int = 0
    cpu_usage_percent: float = 0.0


class MetricsCollector:
    """Centralized metrics collection system for fapilog."""

    def __init__(self, enabled: bool = True, sample_window: int = 100):
        """Initialize the metrics collector.

        Args:
            enabled: Whether metrics collection is enabled
            sample_window: Number of recent samples to keep for averages
        """
        self.enabled = enabled
        self.sample_window = sample_window
        self._lock = threading.RLock()

        # Initialize metrics
        self.queue_metrics = QueueMetrics()
        self.sink_metrics: Dict[str, SinkMetrics] = {}
        self.performance_metrics = PerformanceMetrics()

        # Sliding windows for calculating averages
        self._enqueue_times: deque = deque(maxlen=sample_window)
        self._dequeue_times: deque = deque(maxlen=sample_window)
        self._batch_processing_times: deque = deque(maxlen=sample_window)
        self._sink_write_times: DefaultDict[str, deque] = defaultdict(
            lambda: deque(maxlen=sample_window)
        )
        self._sink_batch_sizes: DefaultDict[str, deque] = defaultdict(
            lambda: deque(maxlen=sample_window)
        )
        self._processing_times: deque = deque(maxlen=sample_window)
        self._event_timestamps: deque = deque(maxlen=sample_window)

        # Start time for metrics
        self._start_time = time.time()

    def is_enabled(self) -> bool:
        """Check if metrics collection is enabled."""
        return self.enabled

    def enable(self) -> None:
        """Enable metrics collection."""
        self.enabled = True

    def disable(self) -> None:
        """Disable metrics collection."""
        self.enabled = False

    def reset(self) -> None:
        """Reset all metrics to initial state."""
        if not self.enabled:
            return

        with self._lock:
            self.queue_metrics = QueueMetrics()
            self.sink_metrics.clear()
            self.performance_metrics = PerformanceMetrics()

            # Clear sliding windows
            self._enqueue_times.clear()
            self._dequeue_times.clear()
            self._batch_processing_times.clear()
            self._sink_write_times.clear()
            self._sink_batch_sizes.clear()
            self._processing_times.clear()
            self._event_timestamps.clear()

            self._start_time = time.time()

    # Queue metrics methods
    def record_queue_size(self, size: int) -> None:
        """Record current queue size."""
        if not self.enabled:
            return

        with self._lock:
            self.queue_metrics.size = size
            if size > self.queue_metrics.peak_size:
                self.queue_metrics.peak_size = size

    def record_enqueue(self, latency_ms: float) -> None:
        """Record an enqueue operation."""
        if not self.enabled:
            return

        with self._lock:
            self.queue_metrics.total_enqueued += 1
            self._enqueue_times.append(latency_ms)
            self.queue_metrics.enqueue_latency_ms = sum(self._enqueue_times) / len(
                self._enqueue_times
            )

    def record_dequeue(self, latency_ms: float) -> None:
        """Record a dequeue operation."""
        if not self.enabled:
            return

        with self._lock:
            self.queue_metrics.total_dequeued += 1
            self._dequeue_times.append(latency_ms)
            self.queue_metrics.dequeue_latency_ms = sum(self._dequeue_times) / len(
                self._dequeue_times
            )

    def record_dropped_event(self) -> None:
        """Record a dropped event."""
        if not self.enabled:
            return

        with self._lock:
            self.queue_metrics.total_dropped += 1

    def record_sampled_event(self) -> None:
        """Record a sampled (skipped) event."""
        if not self.enabled:
            return

        with self._lock:
            self.queue_metrics.total_sampled += 1

    def record_batch_processing(self, processing_time_ms: float) -> None:
        """Record batch processing time."""
        if not self.enabled:
            return

        with self._lock:
            self._batch_processing_times.append(processing_time_ms)
            self.queue_metrics.batch_processing_time_ms = sum(
                self._batch_processing_times
            ) / len(self._batch_processing_times)

    # Sink metrics methods
    def get_sink_metrics(self, sink_name: str) -> SinkMetrics:
        """Get or create sink metrics for a given sink."""
        if not self.enabled:
            return SinkMetrics(name=sink_name)

        with self._lock:
            if sink_name not in self.sink_metrics:
                self.sink_metrics[sink_name] = SinkMetrics(name=sink_name)
            return self.sink_metrics[sink_name]

    def record_sink_write(
        self,
        sink_name: str,
        latency_ms: float,
        success: bool,
        batch_size: int = 1,
        error: Optional[str] = None,
    ) -> None:
        """Record a sink write operation."""
        if not self.enabled:
            return

        with self._lock:
            metrics = self.get_sink_metrics(sink_name)
            metrics.total_writes += 1

            if success:
                metrics.total_successes += 1
            else:
                metrics.total_failures += 1
                if error:
                    metrics.last_error = error
                    metrics.last_error_time = time.time()

            # Update latency average
            self._sink_write_times[sink_name].append(latency_ms)
            metrics.avg_write_latency_ms = sum(self._sink_write_times[sink_name]) / len(
                self._sink_write_times[sink_name]
            )

            # Update batch size average
            self._sink_batch_sizes[sink_name].append(batch_size)
            metrics.avg_batch_size = sum(self._sink_batch_sizes[sink_name]) / len(
                self._sink_batch_sizes[sink_name]
            )

    def record_sink_retry(self, sink_name: str) -> None:
        """Record a sink retry operation."""
        if not self.enabled:
            return

        with self._lock:
            metrics = self.get_sink_metrics(sink_name)
            metrics.total_retries += 1

    # Performance metrics methods
    def record_log_event(self, processing_time_ms: float) -> None:
        """Record a log event processing."""
        if not self.enabled:
            return

        with self._lock:
            now = time.time()
            self.performance_metrics.total_log_events += 1

            # Update processing time average
            self._processing_times.append(processing_time_ms)
            self.performance_metrics.avg_processing_time_ms = sum(
                self._processing_times
            ) / len(self._processing_times)

            # Update events per second
            self._event_timestamps.append(now)
            if len(self._event_timestamps) > 1:
                time_span = self._event_timestamps[-1] - self._event_timestamps[0]
                if time_span > 0:
                    self.performance_metrics.events_per_second = (
                        len(self._event_timestamps) / time_span
                    )

    def update_memory_metrics(self) -> None:
        """Update memory usage metrics."""
        if not self.enabled or not HAS_PSUTIL:
            return

        try:
            process = psutil.Process()
            memory_info = process.memory_info()

            with self._lock:
                self.performance_metrics.memory_usage_bytes = memory_info.rss
                self.performance_metrics.cpu_usage_percent = process.cpu_percent()

                # Estimate queue memory usage (rough approximation)
                # This is a simple heuristic based on queue size
                estimated_event_size = 500  # bytes per event estimate
                self.queue_metrics.memory_usage_bytes = (
                    self.queue_metrics.size * estimated_event_size
                )

        except Exception as e:
            logger.debug(f"Failed to update memory metrics: {e}")

    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all current metrics as a dictionary."""
        if not self.enabled:
            return {}

        with self._lock:
            # Update memory metrics before returning
            self.update_memory_metrics()

            return {
                "queue": {
                    "size": self.queue_metrics.size,
                    "peak_size": self.queue_metrics.peak_size,
                    "total_enqueued": self.queue_metrics.total_enqueued,
                    "total_dequeued": self.queue_metrics.total_dequeued,
                    "total_dropped": self.queue_metrics.total_dropped,
                    "total_sampled": self.queue_metrics.total_sampled,
                    "enqueue_latency_ms": self.queue_metrics.enqueue_latency_ms,
                    "dequeue_latency_ms": self.queue_metrics.dequeue_latency_ms,
                    "batch_processing_time_ms": self.queue_metrics.batch_processing_time_ms,
                    "memory_usage_bytes": self.queue_metrics.memory_usage_bytes,
                },
                "sinks": {
                    name: {
                        "total_writes": metrics.total_writes,
                        "total_successes": metrics.total_successes,
                        "total_failures": metrics.total_failures,
                        "total_retries": metrics.total_retries,
                        "success_rate": (
                            metrics.total_successes / metrics.total_writes
                            if metrics.total_writes > 0
                            else 0.0
                        ),
                        "error_rate": (
                            metrics.total_failures / metrics.total_writes
                            if metrics.total_writes > 0
                            else 0.0
                        ),
                        "avg_write_latency_ms": metrics.avg_write_latency_ms,
                        "avg_batch_size": metrics.avg_batch_size,
                        "memory_usage_bytes": metrics.memory_usage_bytes,
                        "last_error": metrics.last_error,
                        "last_error_time": metrics.last_error_time,
                    }
                    for name, metrics in self.sink_metrics.items()
                },
                "performance": {
                    "total_log_events": self.performance_metrics.total_log_events,
                    "events_per_second": self.performance_metrics.events_per_second,
                    "avg_processing_time_ms": self.performance_metrics.avg_processing_time_ms,
                    "memory_usage_bytes": self.performance_metrics.memory_usage_bytes,
                    "cpu_usage_percent": self.performance_metrics.cpu_usage_percent,
                    "uptime_seconds": time.time() - self._start_time,
                },
            }

    def get_prometheus_metrics(self) -> str:
        """Export metrics in Prometheus format."""
        if not self.enabled:
            return ""

        all_metrics = self.get_all_metrics()
        lines = []

        # Queue metrics
        queue = all_metrics.get("queue", {})
        lines.extend(
            [
                "# HELP fapilog_queue_size Current queue size",
                "# TYPE fapilog_queue_size gauge",
                f"fapilog_queue_size {queue.get('size', 0)}",
                "",
                "# HELP fapilog_queue_peak_size Peak queue size",
                "# TYPE fapilog_queue_peak_size gauge",
                f"fapilog_queue_peak_size {queue.get('peak_size', 0)}",
                "",
                "# HELP fapilog_queue_enqueued_total Total enqueued events",
                "# TYPE fapilog_queue_enqueued_total counter",
                f"fapilog_queue_enqueued_total {queue.get('total_enqueued', 0)}",
                "",
                "# HELP fapilog_queue_dequeued_total Total dequeued events",
                "# TYPE fapilog_queue_dequeued_total counter",
                f"fapilog_queue_dequeued_total {queue.get('total_dequeued', 0)}",
                "",
                "# HELP fapilog_queue_dropped_total Total dropped events",
                "# TYPE fapilog_queue_dropped_total counter",
                f"fapilog_queue_dropped_total {queue.get('total_dropped', 0)}",
                "",
                "# HELP fapilog_queue_enqueue_latency_ms Average enqueue latency",
                "# TYPE fapilog_queue_enqueue_latency_ms gauge",
                f"fapilog_queue_enqueue_latency_ms {queue.get('enqueue_latency_ms', 0)}",
                "",
                "# HELP fapilog_queue_memory_bytes Queue memory usage",
                "# TYPE fapilog_queue_memory_bytes gauge",
                f"fapilog_queue_memory_bytes {queue.get('memory_usage_bytes', 0)}",
                "",
            ]
        )

        # Sink metrics
        sinks = all_metrics.get("sinks", {})
        for sink_name, sink_metrics in sinks.items():
            lines.extend(
                [
                    "# HELP fapilog_sink_writes_total Total sink writes",
                    "# TYPE fapilog_sink_writes_total counter",
                    f'fapilog_sink_writes_total{{sink="{sink_name}"}} {sink_metrics.get("total_writes", 0)}',
                    "",
                    "# HELP fapilog_sink_successes_total Total sink successes",
                    "# TYPE fapilog_sink_successes_total counter",
                    f'fapilog_sink_successes_total{{sink="{sink_name}"}} {sink_metrics.get("total_successes", 0)}',
                    "",
                    "# HELP fapilog_sink_failures_total Total sink failures",
                    "# TYPE fapilog_sink_failures_total counter",
                    f'fapilog_sink_failures_total{{sink="{sink_name}"}} {sink_metrics.get("total_failures", 0)}',
                    "",
                    "# HELP fapilog_sink_success_rate Sink success rate",
                    "# TYPE fapilog_sink_success_rate gauge",
                    f'fapilog_sink_success_rate{{sink="{sink_name}"}} {sink_metrics.get("success_rate", 0)}',
                    "",
                    "# HELP fapilog_sink_latency_ms Average sink write latency",
                    "# TYPE fapilog_sink_latency_ms gauge",
                    f'fapilog_sink_latency_ms{{sink="{sink_name}"}} {sink_metrics.get("avg_write_latency_ms", 0)}',
                    "",
                ]
            )

        # Performance metrics
        perf = all_metrics.get("performance", {})
        lines.extend(
            [
                "# HELP fapilog_events_total Total log events processed",
                "# TYPE fapilog_events_total counter",
                f"fapilog_events_total {perf.get('total_log_events', 0)}",
                "",
                "# HELP fapilog_events_per_second Events per second",
                "# TYPE fapilog_events_per_second gauge",
                f"fapilog_events_per_second {perf.get('events_per_second', 0)}",
                "",
                "# HELP fapilog_memory_bytes Memory usage",
                "# TYPE fapilog_memory_bytes gauge",
                f"fapilog_memory_bytes {perf.get('memory_usage_bytes', 0)}",
                "",
                "# HELP fapilog_cpu_percent CPU usage percentage",
                "# TYPE fapilog_cpu_percent gauge",
                f"fapilog_cpu_percent {perf.get('cpu_usage_percent', 0)}",
                "",
            ]
        )

        return "\n".join(lines)


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> Optional[MetricsCollector]:
    """Get the global metrics collector instance."""
    return _metrics_collector


def set_metrics_collector(collector: Optional[MetricsCollector]) -> None:
    """Set the global metrics collector instance."""
    global _metrics_collector
    _metrics_collector = collector


def create_metrics_collector(
    enabled: bool = True, sample_window: int = 100
) -> MetricsCollector:
    """Create and set a new global metrics collector."""
    collector = MetricsCollector(enabled=enabled, sample_window=sample_window)
    set_metrics_collector(collector)
    return collector
