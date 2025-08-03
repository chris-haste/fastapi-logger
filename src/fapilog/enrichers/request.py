"""Request and response enrichers for fapilog."""

from typing import Any, Dict

from ..utils.context import get_context


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
