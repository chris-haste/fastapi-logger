"""Optional httpx trace propagation for downstream request tracing."""

import functools
from typing import Any

try:
    import httpx
except ImportError:
    httpx = None

from ._internal.context import get_trace_id
from .settings import LoggingSettings

# Global flag to track if patching is enabled
_patching_enabled = False
_original_request_method = None


def enable_httpx_trace_propagation(trace_header_name: str = "X-Request-ID") -> None:
    """Enable automatic trace ID propagation in httpx.AsyncClient.

    This patches httpx.AsyncClient.request to automatically include the current
    trace ID in the specified header for all outgoing requests.

    Args:
        trace_header_name: The header name to use for trace ID propagation
                          (default: X-Request-ID)

    Raises:
        ImportError: If httpx is not installed
        RuntimeError: If patching is already enabled
    """
    global _patching_enabled, _original_request_method

    if httpx is None:
        raise ImportError(
            "httpx is required for trace propagation. Install with: pip install httpx"
        )

    if _patching_enabled:
        raise RuntimeError("httpx trace propagation is already enabled")

    # Store the original request method
    _original_request_method = httpx.AsyncClient.request

    # Create the patched method
    @functools.wraps(_original_request_method)
    async def patched_request(self: Any, method: Any, url: Any, **kwargs: Any) -> Any:
        """Patched httpx.AsyncClient.request that adds trace ID header."""
        # Get current trace ID from context
        trace_id = get_trace_id()

        if trace_id is not None:
            # Ensure headers dict exists
            headers = kwargs.get("headers", {})
            if headers is None:
                headers = {}
            elif not isinstance(headers, dict):
                # Convert other header types to dict
                if hasattr(headers, "items"):
                    headers = dict(headers.items())
                else:
                    headers = {}

            # Add trace ID header if not already present
            if trace_header_name not in headers:
                headers[trace_header_name] = trace_id
                kwargs["headers"] = headers

        # Call the original method
        return await _original_request_method(self, method, url, **kwargs)

    # Apply the patch
    httpx.AsyncClient.request = patched_request
    _patching_enabled = True


def disable_httpx_trace_propagation() -> None:
    """Disable automatic trace ID propagation in httpx.AsyncClient.

    This restores the original httpx.AsyncClient.request method.

    Raises:
        RuntimeError: If patching is not currently enabled
    """
    global _patching_enabled, _original_request_method

    if not _patching_enabled:
        raise RuntimeError("httpx trace propagation is not currently enabled")

    if httpx is None or _original_request_method is None:
        raise RuntimeError("Cannot disable patching: original method not found")

    # Restore the original method
    httpx.AsyncClient.request = _original_request_method
    _patching_enabled = False
    _original_request_method = None


def is_httpx_trace_propagation_enabled() -> bool:
    """Check if httpx trace propagation is currently enabled.

    Returns:
        True if trace propagation is enabled, False otherwise
    """
    return _patching_enabled


def configure_httpx_trace_propagation(settings: LoggingSettings) -> None:
    """Configure httpx trace propagation based on settings.

    This is called automatically during bootstrap if the setting is enabled.

    Args:
        settings: The LoggingSettings instance to use for configuration
    """
    if settings.enable_httpx_trace_propagation and not _patching_enabled:
        try:
            enable_httpx_trace_propagation(settings.trace_id_header)
        except ImportError:
            # Log a warning if httpx is not available but propagation is requested
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(
                "httpx trace propagation is enabled but httpx is not "
                "installed. Install httpx to enable this feature."
            )
