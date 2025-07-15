"""Stdout sink implementation for async logging."""

import json
import sys
from typing import Any, Dict

from .._internal.queue import Sink


class StdoutSink(Sink):
    """Sink that writes log events to stdout."""

    def __init__(self, pretty: bool = False) -> None:
        """Initialize the stdout sink.

        Args:
            pretty: Whether to use pretty formatting instead of JSON
        """
        self.pretty = pretty

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Write a log event to stdout.

        Args:
            event_dict: The structured log event dictionary
        """
        if self.pretty:
            # Simple pretty formatting
            level = event_dict.get("level", "info").upper()
            event = event_dict.get("event", "")
            timestamp = event_dict.get("timestamp", "")

            # Remove common fields for pretty output
            pretty_dict = event_dict.copy()
            for key in ["level", "event", "timestamp"]:
                pretty_dict.pop(key, None)

            # Format the output
            output = f"[{timestamp}] {level}: {event}"
            if pretty_dict:
                output += f" {json.dumps(pretty_dict, sort_keys=True)}"

            print(output, file=sys.stdout, flush=True)
        else:
            # JSON output
            print(json.dumps(event_dict), file=sys.stdout, flush=True)
