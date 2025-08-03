"""HTTP client for sending batches to Loki endpoints."""

from typing import Any, Dict, Optional

try:
    import httpx
except ImportError:
    httpx = None

from ..._internal.error_handling import retry_with_backoff_async
from ...exceptions import (
    SinkConfigurationError,
    SinkErrorContextBuilder,
    SinkWriteError,
)


class LokiHttpClient:
    """Handles HTTP communication with Loki endpoints."""

    def __init__(self, url: str, timeout: float = 30.0) -> None:
        """Initialize the Loki HTTP client.

        Args:
            url: Loki endpoint URL (e.g., "http://loki:3100/loki/api/v1/push")
            timeout: HTTP request timeout in seconds (default: 30.0s)
        """
        if httpx is None:
            context = SinkErrorContextBuilder.build_write_context(
                sink_name="loki", event_dict={"url": url}, operation="initialize"
            )
            raise SinkConfigurationError(
                "httpx is required for LokiHttpClient", "loki", context
            )

        self.url = url
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    def _create_sink_error(
        self, error: Exception, operation: str, config: Dict[str, Any]
    ) -> SinkWriteError:
        """Create standardized sink error with context."""
        context = SinkErrorContextBuilder.build_write_context(
            sink_name="loki", event_dict=config, operation=operation
        )
        return SinkWriteError(str(error), "loki", context)

    async def send_batch(
        self,
        payload: Dict[str, Any],
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        """Send batch to Loki with proper error handling and retries.

        Args:
            payload: The Loki-compatible payload to send
            max_retries: Maximum number of retries on failure (default: 3)
            retry_delay: Base delay between retries in seconds (default: 1.0s)

        Raises:
            SinkError: If the request fails after all retries
        """

        async def send_request_with_retry() -> None:
            """Send request to Loki with proper error handling."""
            await self._send_request(payload)

        try:
            await retry_with_backoff_async(
                send_request_with_retry,
                max_retries=max_retries,
                base_delay=retry_delay,
                error_handler=lambda e: self._create_sink_error(
                    e, "send", {"url": self.url, "payload_size": len(str(payload))}
                ),
            )
        except Exception as e:
            # Convert final exception to SinkError
            raise self._create_sink_error(
                e, "send", {"url": self.url, "payload_size": len(str(payload))}
            ) from e

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
            response.raise_for_status()
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
            raise self._create_sink_error(e, "http_request", sink_config) from e
        except httpx.RequestError as e:
            # Network/connection errors
            sink_config = {
                "url": self.url,
                "error_type": type(e).__name__,
            }
            raise self._create_sink_error(e, "network_request", sink_config) from e
        except Exception as e:
            # Other unexpected errors
            sink_config = {
                "url": self.url,
                "error_type": type(e).__name__,
            }
            raise self._create_sink_error(e, "request", sink_config) from e

    async def close(self) -> None:
        """Close the HTTP client and clean up resources."""
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def is_connected(self) -> bool:
        """Check if the HTTP client is initialized."""
        return self._client is not None
