"""Enrichers for adding metadata to log events."""

import os
import socket
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Callable, Dict, List

from ._internal.context import get_context

if TYPE_CHECKING:
    import psutil


@lru_cache(maxsize=1)
def _get_process() -> "psutil.Process":
    """Get the current process object, cached for performance."""
    try:
        import psutil

        return psutil.Process()
    except ImportError:
        # Return None if psutil is not available
        return None


@lru_cache(maxsize=1)
def _get_hostname() -> str:
    """Get the system hostname, cached for performance."""
    return socket.gethostname()


@lru_cache(maxsize=1)
def _get_pid() -> int:
    """Get the current process ID, cached for performance."""
    return os.getpid()


def host_process_enricher(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Enrich log events with hostname and process ID.

    This processor adds system metadata to every log event:
    - hostname: System hostname (via socket.gethostname())
    - pid: Process ID (via os.getpid())

    These fields are only added if not already present in the event_dict,
    allowing manual override of these values.

    Args:
        logger: The logger instance
        method_name: The logging method name
        event_dict: The event dictionary to enrich

    Returns:
        The enriched event dictionary
    """
    # Add hostname if not already present or if it's None
    if "hostname" not in event_dict or event_dict["hostname"] is None:
        event_dict["hostname"] = _get_hostname()

    # Add pid if not already present or if it's None
    if "pid" not in event_dict or event_dict["pid"] is None:
        event_dict["pid"] = _get_pid()

    return event_dict


def resource_snapshot_enricher(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Enrich log events with memory and CPU usage metrics.

    This processor adds system resource metrics to every log event:
    - memory_mb: Resident memory usage of the current process in megabytes (rounded float)
    - cpu_percent: Process CPU usage percentage (float, 0.0-100.0)

    These fields are only added if not already present in the event_dict,
    allowing manual override of these values.

    Args:
        logger: The logger instance
        method_name: The logging method name
        event_dict: The event dictionary to enrich

    Returns:
        The enriched event dictionary
    """
    process = _get_process()
    if process is None:
        # psutil not available, skip enrichment
        return event_dict

    try:
        # Add memory_mb if not already present or if it's None
        if "memory_mb" not in event_dict or event_dict["memory_mb"] is None:
            memory_info = process.memory_info()
            memory_mb = round(memory_info.rss / (1024 * 1024), 2)
            event_dict["memory_mb"] = memory_mb

        # Add cpu_percent if not already present or if it's None
        if "cpu_percent" not in event_dict or event_dict["cpu_percent"] is None:
            cpu_percent = process.cpu_percent(interval=None)
            event_dict["cpu_percent"] = round(cpu_percent, 2)

    except (OSError, AttributeError):
        # Handle cases where process info cannot be retrieved
        # (e.g., process terminated, permission issues)
        pass

    return event_dict


def body_size_enricher(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Enrich log events with request and response body sizes.

    This processor reads from context variables populated by TraceIDMiddleware
    and adds request/response body size metadata to every event:
    - req_bytes: Size of request body in bytes (0 if no body or streaming)
    - res_bytes: Size of response body in bytes (0 if streaming)

    These values are extracted by TraceIDMiddleware and stored in contextvars.
    Works for standard JSON, form, and plain requests; req_bytes falls back to
    Content-Length header if body not read. res_bytes is set based on
    len(response.body) (when available).

    Args:
        logger: The logger instance
        method_name: The logging method name
        event_dict: The event dictionary to enrich

    Returns:
        The enriched event dictionary
    """
    # Get context metadata
    context = get_context()

    # Add req_bytes if available in context
    req_bytes = context.get("req_bytes")
    if req_bytes is not None:
        event_dict["req_bytes"] = req_bytes

    # Add res_bytes if available in context
    res_bytes = context.get("res_bytes")
    if res_bytes is not None:
        event_dict["res_bytes"] = res_bytes

    return event_dict


def request_response_enricher(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Enrich log events with request and response metadata.

    This processor reads from context variables populated by TraceIDMiddleware
    and adds request/response metadata to every event:
    - status_code: HTTP status integer
    - latency_ms: Request latency in milliseconds
    - req_bytes: Size of request body in bytes (0 if no body or streaming)
    - res_bytes: Size of response body in bytes (0 if streaming)
    - user_agent: Value of User-Agent header or "-"

    Args:
        logger: The logger instance
        method_name: The logging method name
        event_dict: The event dictionary to enrich

    Returns:
        The enriched event dictionary
    """
    # Get all context metadata
    context = get_context()

    # Add non-None values to event_dict
    for key, value in context.items():
        if value is not None:
            event_dict[key] = value

    return event_dict


# Custom enricher registry
_registered_enrichers: List[Callable] = []


def register_enricher(fn: Callable) -> None:
    """Register a custom enricher function.

    Custom enrichers are called at the end of the processor chain, after all
    built-in enrichers. They follow the structlog processor signature:
    `(logger, method_name, event_dict) -> event_dict`

    Args:
        fn: The enricher function to register

    Raises:
        ValueError: If the function doesn't have the correct signature
    """
    # Validate function signature
    import inspect

    sig = inspect.signature(fn)
    params = list(sig.parameters.keys())

    if len(params) != 3 or params != ["logger", "method_name", "event_dict"]:
        raise ValueError(
            f"Enricher function must have signature "
            f"(logger, method_name, event_dict), got {params}"
        )

    # Check if function is already registered (by reference)
    if fn not in _registered_enrichers:
        _registered_enrichers.append(fn)


def clear_enrichers() -> None:
    """Clear all registered custom enrichers.

    This is primarily used for test isolation.
    """
    _registered_enrichers.clear()


def run_registered_enrichers(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Run all registered custom enrichers in registration order.

    Args:
        logger: The logger instance
        method_name: The logging method name
        event_dict: The event dictionary to enrich

    Returns:
        The enriched event dictionary
    """
    result = event_dict
    for enricher in _registered_enrichers:
        try:
            result = enricher(logger, method_name, result)
        except Exception as e:
            # Log enricher failures for debugging but don't break the logging
            # chain
            import logging

            enricher_logger = logging.getLogger(__name__)
            enricher_logger.debug(
                f"Enricher {enricher.__name__} failed: {e}",
                exc_info=True,
            )
    return result
