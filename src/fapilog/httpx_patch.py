"""Optional httpx trace propagation for downstream request tracing."""

import functools
from typing import Any, Optional

try:
    import httpx
except ImportError:
    httpx = None

from .exceptions import ConfigurationError
from .settings import LoggingSettings
from .utils.context import get_trace_id


class HttpxTracePropagation:
    """Manages httpx trace propagation state and operations.

    This class provides a cleaner interface for managing httpx trace propagation
    without relying on global state variables.
    """

    def __init__(self):
        """Initialize the trace propagation manager."""
        self._patching_enabled = False
        self._original_request_method: Optional[Any] = None
        self._trace_header_name = "X-Request-ID"

    def enable(self, trace_header_name: str = "X-Request-ID") -> None:
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
        if httpx is None:
            raise ConfigurationError(
                "httpx is required for trace propagation. Install with: pip install httpx",
                "httpx_trace_propagation",
                None,
                "httpx package",
            )

        if self._patching_enabled:
            raise ConfigurationError(
                "httpx trace propagation is already enabled",
                "httpx_trace_propagation",
                "enabled",
                "disabled state",
            )

        # Store the original request method
        self._original_request_method = httpx.AsyncClient.request
        self._trace_header_name = trace_header_name

        # Create the patched method
        @functools.wraps(self._original_request_method)
        async def patched_request(
            self: Any, method: Any, url: Any, **kwargs: Any
        ) -> Any:
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
                if self._trace_header_name not in headers:
                    headers[self._trace_header_name] = trace_id
                    kwargs["headers"] = headers

            # Call the original method
            return await self._original_request_method(method, url, **kwargs)

        # Apply the patch
        httpx.AsyncClient.request = patched_request
        self._patching_enabled = True

    def disable(self) -> None:
        """Disable automatic trace ID propagation in httpx.AsyncClient.

        This restores the original httpx.AsyncClient.request method.

        Raises:
            RuntimeError: If patching is not currently enabled
        """
        if not self._patching_enabled:
            raise ConfigurationError(
                "httpx trace propagation is not currently enabled",
                "httpx_trace_propagation",
                "disabled",
                "enabled state",
            )

        if httpx is None or self._original_request_method is None:
            raise ConfigurationError(
                "Cannot disable patching: original method not found",
                "httpx_trace_propagation",
                "missing_method",
                "valid method reference",
            )

        # Restore the original method
        httpx.AsyncClient.request = self._original_request_method
        self._patching_enabled = False
        self._original_request_method = None

    def is_enabled(self) -> bool:
        """Check if httpx trace propagation is currently enabled.

        Returns:
            True if trace propagation is enabled, False otherwise
        """
        return self._patching_enabled

    def configure(self, settings: LoggingSettings) -> None:
        """Configure httpx trace propagation based on settings.

        This is called automatically during bootstrap if the setting is enabled.

        Args:
            settings: The LoggingSettings instance to use for configuration
        """
        if settings.enable_httpx_trace_propagation and not self._patching_enabled:
            try:
                self.enable(settings.trace_id_header)
            except ImportError:
                # Log a warning if httpx is not available but propagation is requested
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(
                    "httpx trace propagation is enabled but httpx is not "
                    "installed. Install httpx to enable this feature."
                )

    def cleanup(self) -> None:
        """Clean up httpx trace propagation.

        This is an alias for disable() that provides a consistent cleanup
        interface.
        """
        if self._patching_enabled:
            self.disable()


# Global instance for backward compatibility
_global_propagation = HttpxTracePropagation()


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
    _global_propagation.enable(trace_header_name)


def disable_httpx_trace_propagation() -> None:
    """Disable automatic trace ID propagation in httpx.AsyncClient.

    This restores the original httpx.AsyncClient.request method.

    Raises:
        RuntimeError: If patching is not currently enabled
    """
    _global_propagation.disable()


def is_httpx_trace_propagation_enabled() -> bool:
    """Check if httpx trace propagation is currently enabled.

    Returns:
        True if trace propagation is enabled, False otherwise
    """
    return _global_propagation.is_enabled()


def configure_httpx_trace_propagation(settings: "LoggingSettings") -> None:
    """Configure httpx trace propagation based on settings.

    This function is provided for test compatibility.

    Args:
        settings: The LoggingSettings instance to use for configuration
    """
    _global_propagation.configure(settings)
