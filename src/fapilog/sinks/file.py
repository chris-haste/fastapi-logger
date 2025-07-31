"""File sink implementation for async logging with rotation support."""

import asyncio
import logging
import logging.handlers
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from .._internal.error_handling import StandardSinkErrorHandling
from .._internal.utils import safe_json_serialize
from ..exceptions import ConfigurationError
from .base import Sink

if TYPE_CHECKING:
    from ..container import LoggingContainer


class FileSink(Sink, StandardSinkErrorHandling):
    """Sink that writes log events to a file with rotation support."""

    def __init__(
        self,
        file_path: str,
        max_bytes: int = 10 * 1024 * 1024,  # 10 MB default
        backup_count: int = 5,
        container: Optional["LoggingContainer"] = None,
    ) -> None:
        """Initialize the file sink.

        Args:
            file_path: Path to the log file
            max_bytes: Maximum file size before rotation (default: 10 MB)
            backup_count: Number of backup files to keep (default: 5)
            container: Optional LoggingContainer for metrics collection
        """
        super().__init__(container=container)
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

        # Async lock for async-safe writing (FIXED: was threading.Lock)
        self._lock = asyncio.Lock()

    def _write_and_flush(self, record: logging.LogRecord) -> None:
        """Write log record and flush handler (sync helper for executor)."""
        self._logger.handle(record)
        self._handler.flush()

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Write a log event to the file.

        Args:
            event_dict: The structured log event dictionary
        """
        start_time = time.time()
        metrics = self._container.get_metrics_collector() if self._container else None
        success = False
        error_msg = None

        try:
            # Convert to JSON string using safe serialization
            log_line = safe_json_serialize(event_dict)

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

            # Async-safe writing with immediate flush
            # (FIXED: was blocking with threading.Lock)
            async with self._lock:
                # File operations should run in executor to avoid blocking
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, lambda: self._write_and_flush(record))
            success = True
        except Exception as e:
            # Use standardized error handling with file-specific context
            additional_context = {
                "file_path": str(self.file_path),
                "max_bytes": self.max_bytes,
                "backup_count": self.backup_count,
                "file_exists": self.file_path.exists(),
                "directory_exists": self.file_path.parent.exists(),
                "is_writable": self.file_path.parent.is_dir()
                and self.file_path.parent.exists(),
            }

            standardized_error = self._handle_sink_error(
                error=e,
                operation="write_to_file",
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
                    sink_name="FileSink",
                    latency_ms=latency_ms,
                    success=success,
                    batch_size=1,
                    error=error_msg,
                )

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
            raise ConfigurationError(
                f"Invalid scheme '{parsed.scheme}'. Expected 'file'",
                "file_uri_scheme",
                parsed.scheme,
                "file",
            )

        if not parsed.path:
            raise ConfigurationError(
                "File path is required", "file_uri_path", None, "valid file path"
            )

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
                raise ConfigurationError(
                    "maxBytes parameter cannot be empty",
                    "maxBytes",
                    value,
                    "positive integer",
                )
            try:
                max_bytes = int(value)
                if max_bytes <= 0:
                    raise ConfigurationError(
                        "maxBytes must be positive",
                        "maxBytes",
                        max_bytes,
                        "positive integer",
                    )
            except (ValueError, IndexError) as e:
                raise ConfigurationError(
                    "Invalid maxBytes parameter", "maxBytes", value, "valid integer"
                ) from e

        # Extract backupCount parameter
        backup_count = 5  # Default
        if "backupCount" in query_params:
            value = query_params["backupCount"][0]
            if value == "":
                raise ConfigurationError(
                    "backupCount parameter cannot be empty",
                    "backupCount",
                    value,
                    "non-negative integer",
                )
            try:
                backup_count = int(value)
                if backup_count < 0:
                    raise ConfigurationError(
                        "backupCount must be non-negative",
                        "backupCount",
                        backup_count,
                        "non-negative integer",
                    )
            except (ValueError, IndexError) as e:
                raise ConfigurationError(
                    "Invalid backupCount parameter",
                    "backupCount",
                    value,
                    "valid integer",
                ) from e

        return file_path, max_bytes, backup_count

    except Exception as e:
        raise ConfigurationError(
            f"Invalid file URI '{uri}': {e}", "file_uri", uri, "valid file URI"
        ) from e


def create_file_sink_from_uri(
    uri: str, container: Optional["LoggingContainer"] = None
) -> FileSink:
    """Create a FileSink instance from a file:// URI.

    Args:
        uri: URI string like "file:///var/log/app.log?maxBytes=10485760&backupCount=3"
        container: Optional LoggingContainer for metrics collection

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
        container=container,
    )
