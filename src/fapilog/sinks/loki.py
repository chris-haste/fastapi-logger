"""Loki sink implementation for async logging via HTTP push."""

import asyncio
import datetime
import logging
import time
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

try:
    import httpx
except ImportError:
    httpx = None

from .._internal.error_handling import handle_sink_error, retry_with_backoff_async
from .._internal.metrics import get_metrics_collector
from .._internal.utils import safe_json_serialize
from ..exceptions import ConfigurationError
from .base import Sink

logger = logging.getLogger(__name__)


class LokiSink(Sink):
    """Sink that pushes log events to Loki via HTTP."""

    def __init__(
        self,
        url: str,
        labels: Optional[Dict[str, str]] = None,
        batch_size: int = 100,
        batch_interval: float = 2.0,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
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
        """
        if httpx is None:
            raise handle_sink_error(
                ImportError("httpx is required for LokiSink"),
                "loki",
                {"url": url},
                "initialize",
            )

        self.url = url.rstrip("/") + "/loki/api/v1/push"
        self.labels = labels or {}
        self.batch_size = batch_size
        self.batch_interval = batch_interval
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Batch management
        self._batch: List[Dict[str, Any]] = []
        self._last_flush = time.time()
        self._lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task[None]] = None
        self._client: Optional[httpx.AsyncClient] = None
        self._flush_timer: Optional[asyncio.Task[None]] = None

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Write a log event to the batch.

        Args:
            event_dict: The structured log event dictionary
        """
        start_time = time.time()
        metrics = get_metrics_collector()
        success = False
        error_msg = None

        try:
            async with self._lock:
                self._batch.append(event_dict)
                batch_was_empty = len(self._batch) == 1

                should_flush = len(self._batch) >= self.batch_size

                if should_flush:
                    await self._flush_batch()
                elif batch_was_empty:
                    # Start interval flush timer if this is the first log in batch
                    self._start_flush_timer()
            success = True
        except Exception as e:
            error_msg = str(e)
            raise
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

    def _start_flush_timer(self) -> None:
        if self._flush_timer and not self._flush_timer.done():
            self._flush_timer.cancel()
        loop = asyncio.get_running_loop()
        task = loop.create_task(self._interval_flush())
        self._flush_timer = task

    async def _interval_flush(self) -> None:
        try:
            await asyncio.sleep(self.batch_interval)
            async with self._lock:
                if self._batch:
                    await self._flush_batch()
        except asyncio.CancelledError:
            pass

    async def _flush_batch(self) -> None:
        """Flush the current batch to Loki."""
        if not self._batch:
            return

        # Cancel interval flush timer
        if self._flush_timer and not self._flush_timer.done():
            self._flush_timer.cancel()
            self._flush_timer = None

        # Get current batch and reset
        batch_to_send = self._batch.copy()
        self._batch.clear()
        self._last_flush = time.time()

        # Send batch immediately (no async task)
        await self._send_batch(batch_to_send)

    async def _send_batch(self, batch: List[Dict[str, Any]]) -> None:
        """Send a batch of logs to Loki.

        Args:
            batch: List of log event dictionaries
        """
        if not batch:
            return

        start_time = time.time()
        metrics = get_metrics_collector()
        success = False
        error_msg = None

        try:
            # Format batch for Loki
            payload = self._format_loki_payload(batch)

            async def send_request_with_retry() -> None:
                """Send request to Loki with proper error handling."""
                await self._send_request(payload)

            await retry_with_backoff_async(
                send_request_with_retry,
                max_retries=self.max_retries,
                base_delay=self.retry_delay,
                error_handler=lambda e: handle_sink_error(
                    e, "loki", {"url": self.url, "batch_size": len(batch)}, "send"
                ),
            )
            success = True
        except Exception as e:
            error_msg = str(e)
            # Final failure after all retries
            sink_config = {
                "url": self.url,
                "batch_size": len(batch),
                "max_retries": self.max_retries,
                "retry_delay": self.retry_delay,
            }
            raise handle_sink_error(e, "loki", sink_config, "send") from e
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

    async def _send_request(self, payload: Dict[str, Any]) -> None:
        """Send HTTP request to Loki.

        Args:
            payload: The Loki-compatible payload

        Raises:
            SinkError: If the request fails
        """
        try:
            if self._client is None:
                self._client = httpx.AsyncClient(timeout=self.timeout)

            response = await self._client.post(
                self.url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            await response.raise_for_status()
        except httpx.HTTPError as e:
            # HTTP-specific errors
            status_code = None
            if hasattr(e, "response") and e.response is not None:
                status_code = getattr(e.response, "status_code", None)

            sink_config = {
                "url": self.url,
                "status_code": status_code,
                "payload_size": len(str(payload)),
            }
            raise handle_sink_error(e, "loki", sink_config, "http_request") from e
        except httpx.RequestError as e:
            # Network/connection errors
            sink_config = {
                "url": self.url,
                "error_type": type(e).__name__,
            }
            raise handle_sink_error(e, "loki", sink_config, "network_request") from e
        except Exception as e:
            # Other unexpected errors
            sink_config = {
                "url": self.url,
                "error_type": type(e).__name__,
            }
            raise handle_sink_error(e, "loki", sink_config, "request") from e

    def _format_loki_payload(self, batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Format a batch of logs into Loki-compatible payload.

        Args:
            batch: List of log event dictionaries

        Returns:
            Loki-compatible payload dictionary

        Raises:
            SinkError: If payload formatting fails
        """
        try:
            # Convert logs to Loki format
            values = []
            for i, event in enumerate(batch):
                try:
                    # Convert timestamp to nanoseconds (Loki expects nanoseconds)
                    timestamp = event.get("timestamp", time.time())
                    if isinstance(timestamp, str):
                        # Parse ISO timestamp
                        dt = datetime.datetime.fromisoformat(
                            timestamp.replace("Z", "+00:00")
                        )
                        timestamp_ns = int(dt.timestamp() * 1_000_000_000)
                    elif isinstance(timestamp, datetime.datetime):
                        # Handle datetime objects directly
                        timestamp_ns = int(timestamp.timestamp() * 1_000_000_000)
                    else:
                        # Assume Unix timestamp in seconds
                        timestamp_ns = int(timestamp * 1_000_000_000)

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
                    raise handle_sink_error(
                        e, "loki", sink_config, "format_event"
                    ) from e

            return {
                "streams": [
                    {
                        "stream": self.labels,
                        "values": values,
                    }
                ]
            }
        except Exception as e:
            # Handle overall payload formatting errors
            sink_config = {
                "batch_size": len(batch),
                "labels": self.labels,
            }
            raise handle_sink_error(e, "loki", sink_config, "format_payload") from e

    async def close(self) -> None:
        """Close the sink and flush any remaining logs."""
        # Cancel interval flush timer
        if self._flush_timer and not self._flush_timer.done():
            self._flush_timer.cancel()
            try:
                await self._flush_timer
            except asyncio.CancelledError:
                pass
            self._flush_timer = None
        # Flush any remaining logs
        async with self._lock:
            if self._batch:
                await self._send_batch(self._batch)

        # Close HTTP client
        if self._client:
            await self._client.aclose()

    async def flush(self) -> None:
        """Flush any buffered logs immediately (for testing or shutdown)."""
        async with self._lock:
            if self._batch:
                await self._flush_batch()


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


def create_loki_sink_from_uri(uri: str) -> LokiSink:
    """Create a LokiSink instance from a loki:// or https:// URI.

    Args:
        uri: URI string like "loki://loki:3100?labels=app=myapi,env=prod&batch_size=50"

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
    )
