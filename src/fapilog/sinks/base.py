"""Base sink interface and implementation for fapilog.

This module provides the base Sink class that all sink implementations
should inherit from. It includes metrics collection and proper lifecycle
management for sink operations.
"""

import time
from typing import Any, Dict

from .._internal.metrics import get_metrics_collector


class Sink:
    """Base class for log sinks."""

    def __init__(self):
        """Initialize the sink."""
        self._sink_name = self.__class__.__name__

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Write a log event to the sink.

        Args:
            event_dict: The structured log event dictionary
        """
        raise NotImplementedError

    async def _write_with_metrics(self, event_dict: Dict[str, Any]) -> None:
        """Write with metrics collection wrapper."""
        start_time = time.time()
        metrics = get_metrics_collector()
        success = False
        error_msg = None

        try:
            await self.write(event_dict)
            success = True
        except Exception as e:
            error_msg = str(e)
            raise
        finally:
            if metrics:
                latency_ms = (time.time() - start_time) * 1000
                metrics.record_sink_write(
                    sink_name=self._sink_name,
                    latency_ms=latency_ms,
                    success=success,
                    batch_size=1,
                    error=error_msg,
                )
