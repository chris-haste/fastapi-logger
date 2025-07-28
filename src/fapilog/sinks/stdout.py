"""Stdout sink implementation for async logging."""

import sys
import time
from typing import Any, Dict, Literal

import structlog

from .._internal.error_handling import StandardSinkErrorHandling
from .._internal.metrics import get_metrics_collector
from .._internal.utils import safe_json_serialize
from .base import Sink

StdoutMode = Literal["json", "pretty", "auto"]


class StdoutSink(Sink, StandardSinkErrorHandling):
    """Sink that writes log events to stdout."""

    def __init__(self, mode: StdoutMode = "auto") -> None:
        """Initialize the stdout sink.

        Args:
            mode: Output format mode
                - "json":
                    Force JSON output
                - "pretty":
                    Force pretty console output
                - "auto":
                    Pretty if TTY, JSON otherwise
        """
        self.mode = mode
        self._pretty = self._determine_pretty_mode()
        self._console_renderer = None
        if self._pretty:
            self._console_renderer = structlog.dev.ConsoleRenderer(colors=True)

    def _determine_pretty_mode(self) -> bool:
        """Determine if pretty mode should be used based on mode setting."""
        if self.mode == "json":
            return False
        elif self.mode == "pretty":
            return True
        elif self.mode == "auto":
            return sys.stderr.isatty()
        else:
            # Fallback to JSON for unknown modes
            return False

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Write a log event to stdout.

        Args:
            event_dict: The structured log event dictionary
        """
        start_time = time.time()
        metrics = get_metrics_collector()
        success = False
        error_msg = None

        try:
            if self._pretty:
                # Use structlog.dev.ConsoleRenderer for pretty output
                # Convert the event dict to a format that ConsoleRenderer expects
                # ConsoleRenderer expects a tuple of (logger, method_name,
                # event_dict)
                rendered = self._console_renderer(None, "info", event_dict)
                print(rendered, file=sys.stdout, flush=True)
            else:
                # JSON output using safe serialization
                print(safe_json_serialize(event_dict), file=sys.stdout, flush=True)
            success = True
        except Exception as e:
            # Use standardized error handling with stdout-specific context
            additional_context = {
                "mode": self.mode,
                "pretty_output": self._pretty,
                "tty_status": sys.stdout.isatty(),
                "encoding": getattr(sys.stdout, "encoding", "unknown"),
                "stderr_tty": sys.stderr.isatty(),
                "stdout_closed": sys.stdout.closed,
            }

            standardized_error = self._handle_sink_error(
                error=e,
                operation="write_to_stdout",
                event_dict=event_dict,
                additional_context=additional_context,
            )

            # Log the error with full context
            self._log_error_with_context(standardized_error)
            error_msg = str(standardized_error)

            # Raise the standardized error with proper chaining
            raise standardized_error from e
        finally:
            if metrics:
                latency_ms = (time.time() - start_time) * 1000
                metrics.record_sink_write(
                    sink_name="StdoutSink",
                    latency_ms=latency_ms,
                    success=success,
                    batch_size=1,
                    error=error_msg,
                )
