"""Enrichers for adding metadata to log events."""

import asyncio
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


def user_context_enricher(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Enrich log events with user authentication context.

    This processor reads user context variables and adds user authentication
    metadata to every event:
    - user_id: Authenticated user identifier
    - user_roles: List of user roles/scopes
    - auth_scheme: Authentication scheme (e.g., 'Bearer', 'Basic')

    Fields are only added if not already present in the event_dict,
    allowing manual override of these values. If no user is authenticated,
    the fields will be null.

    Args:
        logger: The logger instance
        method_name: The logging method name
        event_dict: The event dictionary to enrich

    Returns:
        The enriched event dictionary
    """
    context = get_context()

    # Add user_id if not already present and available in context
    if "user_id" not in event_dict:
        user_id = context.get("user_id")
        if user_id is not None:
            event_dict["user_id"] = user_id

    # Add user_roles if not already present and available in context
    if "user_roles" not in event_dict:
        user_roles = context.get("user_roles")
        if user_roles is not None:
            event_dict["user_roles"] = user_roles

    # Add auth_scheme if not already present and available in context
    if "auth_scheme" not in event_dict:
        auth_scheme = context.get("auth_scheme")
        if auth_scheme is not None:
            event_dict["auth_scheme"] = auth_scheme

    return event_dict


def create_user_dependency(get_user_func: Callable) -> Callable:
    """Create a FastAPI dependency that extracts user context and binds it.

    This factory function creates a FastAPI dependency that wraps your existing
    user authentication logic and automatically binds user context variables
    for logging enrichment.

    Args:
        get_user_func: Your existing FastAPI dependency function that returns
                      user information. This should be a callable that returns
                      a user object or dict with user information.

    Returns:
        A FastAPI dependency function that binds user context and returns
        the user object.

    Example:
        ```python
        from fastapi import Depends, HTTPException
        from fastapi.security import HTTPBearer
        from fapilog.enrichers import create_user_dependency

        security = HTTPBearer()

        def get_current_user_base(token: str = Depends(security)):
            # Your authentication logic here
            if not validate_token(token):
                raise HTTPException(401, "Invalid token")
            return {
                "user_id": "123",
                "roles": ["admin", "user"],
                "auth_scheme": "Bearer"
            }

        # Create the logging-aware dependency
        get_current_user = create_user_dependency(get_current_user_base)

        @app.get("/protected")
        async def protected_route(user = Depends(get_current_user)):
            # All logs in this request will automatically include user context
            log.info("Protected action", action="view_profile")
            return {"user": user}
        ```
    """
    from ._internal.context import bind_user_context

    async def user_dependency(*args, **kwargs):
        """FastAPI dependency that extracts and binds user context."""
        # Call the original user function
        if asyncio.iscoroutinefunction(get_user_func):
            user = await get_user_func(*args, **kwargs)
        else:
            user = get_user_func(*args, **kwargs)

        # Extract user context from user object
        if user is not None:
            user_id = None
            user_roles = None
            auth_scheme = None

            # Handle different user object types
            if isinstance(user, dict):
                user_id = user.get("user_id") or user.get("id")
                user_roles = user.get("user_roles") or user.get("roles")
                auth_scheme = user.get("auth_scheme") or user.get("scheme")
            else:
                # Handle user objects with attributes
                user_id = getattr(user, "user_id", None) or getattr(user, "id", None)
                user_roles = getattr(user, "user_roles", None) or getattr(
                    user, "roles", None
                )
                auth_scheme = getattr(user, "auth_scheme", None) or getattr(
                    user, "scheme", None
                )

            # Convert user_id to string if it's not None
            if user_id is not None:
                user_id = str(user_id)

            # Ensure user_roles is a list if present
            if user_roles is not None and not isinstance(user_roles, list):
                if isinstance(user_roles, str):
                    user_roles = [user_roles]
                else:
                    # Try to convert iterable to list
                    try:
                        user_roles = list(user_roles)
                    except (TypeError, ValueError):
                        user_roles = [str(user_roles)]

            # Bind user context for logging enrichment
            bind_user_context(
                user_id=user_id,
                user_roles=user_roles,
                auth_scheme=auth_scheme,
            )

        return user

    return user_dependency


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
