"""Loki sink implementation for async logging via HTTP push."""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

try:
    import httpx
except ImportError:
    httpx = None

from .._internal.queue import Sink

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
            raise ImportError(
                "httpx is required for LokiSink. "
                "Install with: pip install fapilog[loki]"
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
        async with self._lock:
            self._batch.append(event_dict)
            batch_was_empty = len(self._batch) == 1

            should_flush = len(self._batch) >= self.batch_size

            if should_flush:
                await self._flush_batch()
            elif batch_was_empty:
                # Start interval flush timer if this is the first log in batch
                self._start_flush_timer()

    def _start_flush_timer(self) -> None:
        if self._flush_timer and not self._flush_timer.done():
            self._flush_timer.cancel()
        loop = asyncio.get_running_loop()
        self._flush_timer = loop.create_task(self._interval_flush())

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

        # Format batch for Loki
        payload = self._format_loki_payload(batch)

        # Send with retry logic
        for attempt in range(self.max_retries + 1):
            try:
                await self._send_request(payload)
                break  # Success, exit retry loop
            except Exception as e:
                if attempt == self.max_retries:
                    logger.warning(
                        f"Failed to send batch to Loki after "
                        f"{self.max_retries} retries: {e}"
                    )
                else:
                    delay = self.retry_delay * (2**attempt)  # Exponential backoff
                    logger.warning(
                        f"Retrying Loki batch send (attempt {attempt + 1}): {e}"
                    )
                    await asyncio.sleep(delay)

    async def _send_request(self, payload: Dict[str, Any]) -> None:
        """Send HTTP request to Loki.

        Args:
            payload: The Loki-compatible payload

        Raises:
            httpx.HTTPError: If the request fails
        """
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)

        response = await self._client.post(
            self.url,
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        await response.raise_for_status()

    def _format_loki_payload(self, batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Format a batch of logs into Loki-compatible payload.

        Args:
            batch: List of log event dictionaries

        Returns:
            Loki-compatible payload dictionary
        """
        # Convert logs to Loki format
        values = []
        for event in batch:
            # Convert timestamp to nanoseconds (Loki expects nanoseconds)
            timestamp = event.get("timestamp", time.time())
            if isinstance(timestamp, str):
                # Parse ISO timestamp
                import datetime

                dt = datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                timestamp_ns = int(dt.timestamp() * 1_000_000_000)
            else:
                # Assume Unix timestamp in seconds
                timestamp_ns = int(timestamp * 1_000_000_000)

            # Convert event to JSON string
            log_line = json.dumps(event)

            values.append([str(timestamp_ns), log_line])

        return {
            "streams": [
                {
                    "stream": self.labels,
                    "values": values,
                }
            ]
        }

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

    async def flush(self):
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
            raise ValueError(
                f"Invalid scheme '{parsed.scheme}'. Expected 'loki' or 'https'"
            )

        if not parsed.netloc:
            raise ValueError("Host is required")

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
                raise ValueError("batch_size parameter cannot be empty")
            try:
                batch_size = int(value)
                if batch_size <= 0:
                    raise ValueError("batch_size must be positive")
            except (ValueError, IndexError) as e:
                raise ValueError("Invalid batch_size parameter") from e

        # Extract batch_interval
        batch_interval = 2.0  # Default
        if "batch_interval" in query_params:
            value = query_params["batch_interval"][0]
            if value == "":
                raise ValueError("batch_interval parameter cannot be empty")
            try:
                batch_interval = float(value)
                if batch_interval <= 0:
                    raise ValueError("batch_interval must be positive")
            except (ValueError, IndexError) as e:
                raise ValueError("Invalid batch_interval parameter") from e

        return url, labels, batch_size, batch_interval

    except Exception as e:
        raise ValueError(f"Invalid Loki URI '{uri}': {e}") from e


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
