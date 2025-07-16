"""Stdout sink implementation for async logging."""

import json
import sys
from typing import Any, Dict, Literal

import structlog

from .._internal.queue import Sink

StdoutMode = Literal["json", "pretty", "auto"]


class StdoutSink(Sink):
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
        if self._pretty:
            # Use structlog.dev.ConsoleRenderer for pretty output
            # Convert the event dict to a format that ConsoleRenderer expects
            # ConsoleRenderer expects a tuple of (logger, method_name,
            # event_dict)
            rendered = self._console_renderer(None, "info", event_dict)
            print(rendered, file=sys.stdout, flush=True)
        else:
            # JSON output
            print(json.dumps(event_dict), file=sys.stdout, flush=True)
