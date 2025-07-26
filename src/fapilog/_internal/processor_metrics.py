"""Processor performance metrics collection for fapilog."""

import json
import threading
import time
from typing import Any, Callable, Dict, Optional

from .processor import Processor


class ProcessorMetrics:
    """Track processor performance and health metrics."""

    def __init__(self):
        """Initialize processor metrics tracking."""
        self._metrics = {}  # processor_name -> metrics data
        self._lock = threading.Lock()

    def record_processor_execution(
        self,
        processor_name: str,
        latency_ms: float,
        success: bool,
        error: Optional[str] = None,
        event_size_bytes: Optional[int] = None,
    ) -> None:
        """Record processor execution metrics.

        Args:
            processor_name: Name of the processor
            latency_ms: Execution time in milliseconds
            success: Whether the execution succeeded
            error: Error message if execution failed
            event_size_bytes: Size of processed event in bytes
        """
        with self._lock:
            if processor_name not in self._metrics:
                self._metrics[processor_name] = {
                    "total_executions": 0,
                    "successful_executions": 0,
                    "failed_executions": 0,
                    "total_latency_ms": 0.0,
                    "min_latency_ms": float("inf"),
                    "max_latency_ms": 0.0,
                    "total_bytes_processed": 0,
                    "error_counts": {},
                    "last_execution": None,
                    "last_error": None,
                }

            metrics = self._metrics[processor_name]
            metrics["total_executions"] += 1
            metrics["total_latency_ms"] += latency_ms
            metrics["min_latency_ms"] = min(metrics["min_latency_ms"], latency_ms)
            metrics["max_latency_ms"] = max(metrics["max_latency_ms"], latency_ms)
            metrics["last_execution"] = time.time()

            if success:
                metrics["successful_executions"] += 1
            else:
                metrics["failed_executions"] += 1
                if error:
                    error_count = metrics["error_counts"].get(error, 0) + 1
                    metrics["error_counts"][error] = error_count
                    metrics["last_error"] = error

            if event_size_bytes:
                metrics["total_bytes_processed"] += event_size_bytes

    def get_processor_stats(self, processor_name: str) -> Dict[str, Any]:
        """Get statistics for a specific processor.

        Args:
            processor_name: Name of the processor

        Returns:
            Dictionary containing processor statistics
        """
        with self._lock:
            if processor_name not in self._metrics:
                return {}

            metrics = self._metrics[processor_name].copy()

            # Calculate derived metrics
            if metrics["total_executions"] > 0:
                success_count = metrics["successful_executions"]
                total_count = metrics["total_executions"]
                failed_count = metrics["failed_executions"]

                metrics["success_rate"] = (success_count / total_count) * 100
                metrics["failure_rate"] = (failed_count / total_count) * 100
                metrics["average_latency_ms"] = (
                    metrics["total_latency_ms"] / total_count
                )
            else:
                metrics["success_rate"] = 0.0
                metrics["failure_rate"] = 0.0
                metrics["average_latency_ms"] = 0.0

            # Handle edge case for min_latency_ms
            if metrics["min_latency_ms"] == float("inf"):
                metrics["min_latency_ms"] = 0.0

            return metrics

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all processors.

        Returns:
            Dictionary mapping processor names to their statistics
        """
        return {name: self.get_processor_stats(name) for name in self._metrics.keys()}

    def reset_stats(self, processor_name: Optional[str] = None) -> None:
        """Reset statistics for specific processor or all processors.

        Args:
            processor_name: Name of processor to reset, or None to reset all
        """
        with self._lock:
            if processor_name:
                self._metrics.pop(processor_name, None)
            else:
                self._metrics.clear()


# Global metrics instance
_processor_metrics: Optional[ProcessorMetrics] = None


def get_processor_metrics() -> ProcessorMetrics:
    """Get the global processor metrics instance.

    Returns:
        The global ProcessorMetrics instance
    """
    global _processor_metrics
    if _processor_metrics is None:
        _processor_metrics = ProcessorMetrics()
    return _processor_metrics


def wrap_processor_with_metrics(processor: Processor) -> Callable:
    """Wrap processor with metrics collection.

    Args:
        processor: The processor instance to wrap

    Returns:
        Wrapped processor function with metrics collection
    """
    processor_name = processor.__class__.__name__
    metrics = get_processor_metrics()

    def wrapped_processor(
        logger, method_name: str, event_dict: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        start_time = time.time()
        success = False
        error_msg = None
        result = None

        # Calculate event size for throughput metrics
        event_size = len(json.dumps(event_dict, default=str).encode("utf-8"))

        try:
            result = processor.process(logger, method_name, event_dict)
            success = True
            return result
        except Exception as e:
            error_msg = str(e)
            raise
        finally:
            latency_ms = (time.time() - start_time) * 1000
            metrics.record_processor_execution(
                processor_name=processor_name,
                latency_ms=latency_ms,
                success=success,
                error=error_msg,
                event_size_bytes=event_size,
            )

    return wrapped_processor


def wrap_function_processor_with_metrics(func: Callable, name: str) -> Callable:
    """Wrap function-based processor with metrics collection.

    Args:
        func: The processor function to wrap
        name: Name to use for metrics tracking

    Returns:
        Wrapped function with metrics collection
    """
    metrics = get_processor_metrics()

    def wrapped_function(
        logger, method_name: str, event_dict: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        if event_dict is None:
            return None

        start_time = time.time()
        success = False
        error_msg = None
        result = None

        event_size = len(json.dumps(event_dict, default=str).encode("utf-8"))

        try:
            result = func(logger, method_name, event_dict)
            success = True
            return result
        except Exception as e:
            error_msg = str(e)
            raise
        finally:
            latency_ms = (time.time() - start_time) * 1000
            metrics.record_processor_execution(
                processor_name=name,
                latency_ms=latency_ms,
                success=success,
                error=error_msg,
                event_size_bytes=event_size,
            )

    return wrapped_function
