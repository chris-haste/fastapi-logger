"""File sink implementation for async logging with rotation support."""

import json
import logging
import logging.handlers
import threading
from pathlib import Path
from typing import Any, Dict
from urllib.parse import parse_qs, urlparse

from .._internal.queue import Sink


class FileSink(Sink):
    """Sink that writes log events to a file with rotation support."""

    def __init__(
        self,
        file_path: str,
        max_bytes: int = 10 * 1024 * 1024,  # 10 MB default
        backup_count: int = 5,
    ) -> None:
        """Initialize the file sink.

        Args:
            file_path: Path to the log file
            max_bytes: Maximum file size before rotation (default: 10 MB)
            backup_count: Number of backup files to keep (default: 5)
        """
        self.file_path = Path(file_path)
        self.max_bytes = max_bytes
        self.backup_count = backup_count

        # Ensure directory exists
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        # Create the rotating file handler
        self._handler = logging.handlers.RotatingFileHandler(
            filename=str(self.file_path),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )

        # Create a logger instance for thread-safe writing
        self._logger = logging.getLogger(f"fapilog.file.{self.file_path.name}")
        self._logger.setLevel(logging.DEBUG)
        self._logger.addHandler(self._handler)
        self._logger.propagate = False  # Prevent double logging

        # Thread lock for thread-safe writing
        self._lock = threading.Lock()

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Write a log event to the file.

        Args:
            event_dict: The structured log event dictionary
        """
        # Convert to JSON string
        log_line = json.dumps(event_dict) + "\n"

        # Create a log record
        record = logging.LogRecord(
            name=self._logger.name,
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg=log_line,
            args=(),
            exc_info=None,
        )

        # Thread-safe writing with immediate flush
        with self._lock:
            self._logger.handle(record)
            self._handler.flush()

    def close(self) -> None:
        """Close the file handler."""
        if hasattr(self, "_handler"):
            self._handler.close()


def parse_file_uri(uri: str) -> tuple[str, int, int]:
    """Parse a file:// URI and extract configuration.

    Args:
        uri: URI string like "file:///var/log/app.log?maxBytes=10485760&backupCount=3"

    Returns:
        Tuple of (file_path, max_bytes, backup_count)

    Raises:
        ValueError: If URI is invalid or parameters are invalid
    """
    try:
        parsed = urlparse(uri)

        if parsed.scheme != "file":
            raise ValueError(f"Invalid scheme '{parsed.scheme}'. Expected 'file'")

        if not parsed.path:
            raise ValueError("File path is required")

        # Handle Windows paths (file:///C:/path/to/file)
        file_path = parsed.path
        if file_path.startswith("/") and len(file_path) > 2 and file_path[2] == ":":
            # Windows absolute path
            file_path = file_path[1:]  # Remove leading slash

        # Parse query parameters
        query_params = parse_qs(parsed.query)

        # Extract maxBytes parameter
        max_bytes = 10 * 1024 * 1024  # 10 MB default
        if "maxBytes" in query_params:
            value = query_params["maxBytes"][0]
            if value == "":
                raise ValueError("maxBytes parameter cannot be empty")
            try:
                max_bytes = int(value)
                if max_bytes <= 0:
                    raise ValueError("maxBytes must be positive")
            except (ValueError, IndexError):
                raise ValueError("Invalid maxBytes parameter")

        # Extract backupCount parameter
        backup_count = 5  # Default
        if "backupCount" in query_params:
            value = query_params["backupCount"][0]
            if value == "":
                raise ValueError("backupCount parameter cannot be empty")
            try:
                backup_count = int(value)
                if backup_count < 0:
                    raise ValueError("backupCount must be non-negative")
            except (ValueError, IndexError):
                raise ValueError("Invalid backupCount parameter")

        return file_path, max_bytes, backup_count

    except Exception as e:
        raise ValueError(f"Invalid file URI '{uri}': {e}")


def create_file_sink_from_uri(uri: str) -> FileSink:
    """Create a FileSink instance from a file:// URI.

    Args:
        uri: URI string like "file:///var/log/app.log?maxBytes=10485760&backupCount=3"

    Returns:
        Configured FileSink instance

    Raises:
        ValueError: If URI is invalid or parameters are invalid
    """
    file_path, max_bytes, backup_count = parse_file_uri(uri)
    return FileSink(
        file_path=file_path,
        max_bytes=max_bytes,
        backup_count=backup_count,
    )
