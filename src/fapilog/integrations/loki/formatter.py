"""Payload formatter for converting log events to Loki-compatible format."""

import datetime
import time
from typing import Any, Dict, List

from ...exceptions import SinkErrorContextBuilder, SinkWriteError
from ...utils.helpers import safe_json_serialize


class LokiPayloadFormatter:
    """Handles Loki-specific payload formatting."""

    def __init__(self, labels: Dict[str, str] = None) -> None:
        """Initialize the Loki payload formatter.

        Args:
            labels: Static labels to attach to all log streams
        """
        self.labels = labels or {}

    def format_batch(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert events to Loki-compatible payload format.

        Args:
            events: List of log event dictionaries

        Returns:
            Loki-compatible payload dictionary

        Raises:
            SinkError: If payload formatting fails
        """
        try:
            # Convert logs to Loki format
            values = []
            for i, event in enumerate(events):
                try:
                    # Convert timestamp to nanoseconds (Loki expects nanoseconds)
                    timestamp = event.get("timestamp", time.time())
                    timestamp_ns = self._convert_timestamp_to_nanoseconds(timestamp)

                    # Convert event to JSON string using safe serialization
                    log_line = safe_json_serialize(event)

                    values.append([str(timestamp_ns), log_line])
                except Exception as e:
                    # Handle individual event formatting errors
                    sink_config = {
                        "event_index": i,
                        "event_keys": list(event.keys()),
                        "timestamp_value": event.get("timestamp"),
                    }
                    context = SinkErrorContextBuilder.build_write_context(
                        sink_name="loki",
                        event_dict=sink_config,
                        operation="format_event",
                    )
                    raise SinkWriteError(str(e), "loki", context) from e

            return {"streams": [{"stream": self.labels, "values": values}]}
        except Exception as e:
            # Handle overall payload formatting errors
            sink_config = {
                "batch_size": len(events),
                "labels": self.labels,
            }
            context = SinkErrorContextBuilder.build_write_context(
                sink_name="loki", event_dict=sink_config, operation="format_payload"
            )
            raise SinkWriteError(str(e), "loki", context) from e

    def _convert_timestamp_to_nanoseconds(self, timestamp: Any) -> int:
        """Convert various timestamp formats to nanoseconds.

        Args:
            timestamp: Timestamp in various formats (str, datetime, float)

        Returns:
            Timestamp in nanoseconds as integer

        Raises:
            ValueError: If timestamp format is not supported
        """
        try:
            if isinstance(timestamp, str):
                # Parse ISO timestamp
                dt = datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                return int(dt.timestamp() * 1_000_000_000)
            elif isinstance(timestamp, datetime.datetime):
                # Handle datetime objects directly
                return int(timestamp.timestamp() * 1_000_000_000)
            else:
                # Assume Unix timestamp in seconds (float or int)
                return int(float(timestamp) * 1_000_000_000)
        except (ValueError, TypeError, AttributeError) as e:
            raise ValueError(
                f"Unsupported timestamp format: {timestamp} ({type(timestamp)})"
            ) from e

    def update_labels(self, labels: Dict[str, str]) -> None:
        """Update the labels for the formatter.

        Args:
            labels: New labels to use for log streams
        """
        self.labels = labels or {}

    def add_label(self, key: str, value: str) -> None:
        """Add a single label to the formatter.

        Args:
            key: Label key
            value: Label value
        """
        self.labels[key] = value

    def remove_label(self, key: str) -> None:
        """Remove a label from the formatter.

        Args:
            key: Label key to remove
        """
        self.labels.pop(key, None)
