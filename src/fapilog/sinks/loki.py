"""Loki sink implementation for async logging via HTTP push."""

import logging
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

try:
    import httpx
except ImportError:
    httpx = None

from .._internal.error_handling import StandardSinkErrorHandling
from .._internal.loki_http_client import LokiHttpClient
from .._internal.loki_payload_formatter import LokiPayloadFormatter
from ..async_components.queue.batch_manager import BatchManager
from ..exceptions import (
    ConfigurationError,
    SinkConfigurationError,
    SinkErrorContextBuilder,
)
from .base import Sink

if TYPE_CHECKING:
    from ..container import LoggingContainer

logger = logging.getLogger(__name__)


class LokiSink(Sink, StandardSinkErrorHandling):
    """Sink that pushes log events to Loki via HTTP using composition."""

    def __init__(
        self,
        url: str,
        labels: Optional[Dict[str, str]] = None,
        batch_size: int = 100,
        batch_interval: float = 2.0,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        container: Optional["LoggingContainer"] = None,
    ) -> None:
        """Initialize the Loki sink.

        Args:
            url: Loki endpoint URL (e.g., "http://loki:3100")
            labels: Static labels to attach to all log streams
            batch_size: Number of logs to batch before pushing (default: 100)
            batch_interval: Maximum time to wait before pushing batch (default: 2.0s)
            timeout: HTTP request timeout in seconds (default: 30.0s)
            max_retries: Maximum number of retries on failure (default: 3)
            retry_delay: Base delay between retries in seconds (default: 1.0s)
            container: Optional LoggingContainer for metrics collection
        """
        super().__init__(container=container)
        if httpx is None:
            context = SinkErrorContextBuilder.build_write_context(
                sink_name="loki", event_dict={"url": url}, operation="initialize"
            )
            raise SinkConfigurationError(
                "httpx is required for LokiSink", "loki", context
            )

        # Store configuration
        self.url = url.rstrip("/") + "/loki/api/v1/push"
        self.labels = labels or {}
        self.batch_size = batch_size
        self.batch_interval = batch_interval
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Initialize composed components
        self._http_client = LokiHttpClient(self.url, timeout)
        self._formatter = LokiPayloadFormatter(self.labels)
        self._batch_manager = BatchManager(batch_size, batch_interval, self._send_batch)

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Write a log event to the batch.

        Args:
            event_dict: The structured log event dictionary
        """
        start_time = time.time()
        metrics = self._container.get_metrics_collector() if self._container else None
        success = False
        error_msg = None

        try:
            # Simple delegation to batch manager
            await self._batch_manager.add_event(event_dict)
            success = True
        except Exception as e:
            # Use standardized error handling with Loki-specific context
            additional_context = {
                "url": self.url,
                "batch_size": self.batch_size,
                "batch_interval": self.batch_interval,
                "timeout": self.timeout,
                "max_retries": self.max_retries,
                "labels": self.labels,
            }

            standardized_error = self._handle_sink_error(
                error=e,
                operation="add_to_batch",
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
                    sink_name="LokiSink",
                    latency_ms=latency_ms,
                    success=success,
                    batch_size=1,
                    error=error_msg,
                )

    async def _send_batch(self, batch: List[Dict[str, Any]]) -> None:
        """Send a batch of logs to Loki using composed components.

        Args:
            batch: List of log event dictionaries
        """
        if not batch:
            return

        start_time = time.time()
        metrics = self._container.get_metrics_collector() if self._container else None
        success = False
        error_msg = None

        try:
            # Format batch using the formatter component
            payload = self._formatter.format_batch(batch)

            # Send using the HTTP client component
            await self._http_client.send_batch(
                payload, self.max_retries, self.retry_delay
            )
            success = True
        except Exception as e:
            # Use standardized error handling with batch-specific context
            # Create a summary event dict for context (avoid logging all events)
            summary_event_dict = {
                "batch_summary": {
                    "batch_size": len(batch),
                    "first_event_keys": list(batch[0].keys()) if batch else [],
                }
            }

            additional_context = {
                "url": self.url,
                "batch_size": len(batch),
                "payload_size": len(str(payload)) if "payload" in locals() else 0,
                "timeout": self.timeout,
                "max_retries": self.max_retries,
            }

            standardized_error = self._handle_sink_error(
                error=e,
                operation="send_batch",
                event_dict=summary_event_dict,
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
                # Record batch operation
                metrics.record_sink_write(
                    sink_name="LokiSink_batch",
                    latency_ms=latency_ms,
                    success=success,
                    batch_size=len(batch),
                    error=error_msg,
                )

    async def close(self) -> None:
        """Close the sink and flush any remaining logs."""
        # Close batch manager (flushes remaining logs)
        await self._batch_manager.close()

        # Close HTTP client
        await self._http_client.close()

    async def flush(self) -> None:
        """Flush any buffered logs immediately (for testing or shutdown)."""
        await self._batch_manager.flush_batch()


def parse_loki_uri(uri: str) -> tuple[str, Dict[str, str], int, float]:
    """Parse a loki:// or https:// URI and extract configuration.

    Args:
        uri: URI string like "loki://loki:3100?labels=app=myapi,env=prod&batch_size=50"

    Returns:
        Tuple of (url, labels, batch_size, batch_interval)

    Raises:
        ValueError: If URI is invalid or parameters are invalid
    """
    try:
        parsed = urlparse(uri)

        # Handle both loki:// and https:// schemes
        if parsed.scheme not in ("loki", "https"):
            raise ConfigurationError(
                f"Invalid scheme '{parsed.scheme}'. Expected 'loki' or 'https'",
                "loki_uri_scheme",
                parsed.scheme,
                "loki or https",
            )

        if not parsed.netloc:
            raise ConfigurationError(
                "Host is required", "loki_uri_hostname", None, "valid hostname"
            )

        # Build base URL
        scheme = "https" if parsed.scheme == "https" else "http"
        url = f"{scheme}://{parsed.netloc}"

        # Parse query parameters
        query_params = parse_qs(parsed.query)

        # Extract labels
        labels = {}
        if "labels" in query_params:
            labels_str = query_params["labels"][0]
            if labels_str:
                for label_pair in labels_str.split(","):
                    if "=" in label_pair:
                        key, value = label_pair.split("=", 1)
                        labels[key.strip()] = value.strip()

        # Extract batch_size
        batch_size = 100  # Default
        if "batch_size" in query_params:
            value = query_params["batch_size"][0]
            if value == "":
                raise ConfigurationError(
                    "batch_size parameter cannot be empty",
                    "batch_size",
                    value,
                    "positive integer",
                )
            try:
                batch_size = int(value)
                if batch_size <= 0:
                    raise ConfigurationError(
                        "batch_size must be positive",
                        "batch_size",
                        batch_size,
                        "positive integer",
                    )
            except (ValueError, IndexError) as e:
                raise ConfigurationError(
                    "Invalid batch_size parameter", "batch_size", value, "valid integer"
                ) from e

        # Extract batch_interval
        batch_interval = 2.0  # Default
        if "batch_interval" in query_params:
            value = query_params["batch_interval"][0]
            if value == "":
                raise ConfigurationError(
                    "batch_interval parameter cannot be empty",
                    "batch_interval",
                    value,
                    "positive float",
                )
            try:
                batch_interval = float(value)
                if batch_interval <= 0:
                    raise ConfigurationError(
                        "batch_interval must be positive",
                        "batch_interval",
                        batch_interval,
                        "positive float",
                    )
            except (ValueError, IndexError) as e:
                raise ConfigurationError(
                    "Invalid batch_interval parameter",
                    "batch_interval",
                    value,
                    "valid float",
                ) from e

        return url, labels, batch_size, batch_interval

    except Exception as e:
        raise ConfigurationError(
            f"Invalid Loki URI '{uri}': {e}", "loki_uri", uri, "valid Loki URI"
        ) from e


def create_loki_sink_from_uri(
    uri: str, container: Optional["LoggingContainer"] = None
) -> LokiSink:
    """Create a LokiSink instance from a loki:// or https:// URI.

    Args:
        uri: URI string like "loki://loki:3100?labels=app=myapi,env=prod&batch_size=50"
        container: Optional LoggingContainer for metrics collection

    Returns:
        Configured LokiSink instance

    Raises:
        ValueError: If URI is invalid or parameters are invalid
        ImportError: If httpx is not installed
    """
    url, labels, batch_size, batch_interval = parse_loki_uri(uri)
    return LokiSink(
        url=url,
        labels=labels,
        batch_size=batch_size,
        batch_interval=batch_interval,
        container=container,
    )
