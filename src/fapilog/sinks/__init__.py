"""Sink implementations for fapilog.

This module provides various sink implementations for outputting log data to different
destinations. Each sink implements the Sink interface and can be configured through
the logging settings.

Available sinks:
- StdoutSink: Outputs logs to stdout with configurable formatting
- FileSink: Outputs logs to files with rotation support
- LokiSink: Outputs logs to Grafana Loki for centralized logging

Sinks are automatically configured based on the 'sinks' setting in LoggingSettings.
"""

from .base import Sink
from .file import FileSink, create_file_sink_from_uri
from .loki import LokiSink, create_loki_sink_from_uri
from .stdout import StdoutSink

__all__ = [
    "Sink",
    "FileSink",
    "LokiSink",
    "StdoutSink",
    "create_file_sink_from_uri",
    "create_loki_sink_from_uri",
]
