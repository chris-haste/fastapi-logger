"""Context variables for request correlation and tracing."""

import contextvars
from typing import Any, Dict, List, Optional, Tuple

from .error_handling import handle_context_error

# Context variables for request correlation
trace_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "trace_id", default=None
)
span_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "span_id", default=None
)

# Context variables for request/response metadata
req_bytes_ctx: contextvars.ContextVar[Optional[int]] = contextvars.ContextVar(
    "req_bytes", default=None
)
res_bytes_ctx: contextvars.ContextVar[Optional[int]] = contextvars.ContextVar(
    "res_bytes", default=None
)
status_code_ctx: contextvars.ContextVar[Optional[int]] = contextvars.ContextVar(
    "status_code", default=None
)
latency_ctx: contextvars.ContextVar[Optional[float]] = contextvars.ContextVar(
    "latency_ms", default=None
)
user_agent_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "user_agent", default=None
)

# Context variables for request details (Story 6.1)
client_ip_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "client_ip", default=None
)
method_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "method", default=None
)
path_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "path", default=None
)

# Context variables for user authentication (Story 6.3)
user_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "user_id", default=None
)
user_roles_ctx: contextvars.ContextVar[Optional[List[str]]] = contextvars.ContextVar(
    "user_roles", default=None
)
auth_scheme_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "auth_scheme", default=None
)


def get_context() -> Dict[str, Any]:
    """Get the current context as a dictionary.

    Returns:
        Dictionary containing current trace_id, span_id, latency_ms,
        status_code, req_bytes, res_bytes, user_agent, client_ip, method,
        path, user_id, user_roles, and auth_scheme values.
    """
    return {
        "trace_id": trace_ctx.get(),
        "span_id": span_ctx.get(),
        "latency_ms": latency_ctx.get(),
        "status_code": status_code_ctx.get(),
        "req_bytes": req_bytes_ctx.get(),
        "res_bytes": res_bytes_ctx.get(),
        "user_agent": user_agent_ctx.get(),
        "client_ip": client_ip_ctx.get(),
        "method": method_ctx.get(),
        "path": path_ctx.get(),
        "user_id": user_id_ctx.get(),
        "user_roles": user_roles_ctx.get(),
        "auth_scheme": auth_scheme_ctx.get(),
    }


def bind_context(**kwargs: Any) -> None:
    """Set or overwrite context variables for the current task.

    Args:
        **kwargs: Context variables to set. Valid keys are:
            trace_id, span_id, latency_ms, status_code, req_bytes, res_bytes,
            user_agent, client_ip, method, path, user_id, user_roles,
            auth_scheme
    """
    valid_keys = {
        "trace_id",
        "span_id",
        "latency_ms",
        "status_code",
        "req_bytes",
        "res_bytes",
        "user_agent",
        "client_ip",
        "method",
        "path",
        "user_id",
        "user_roles",
        "auth_scheme",
    }

    for key, value in kwargs.items():
        if key not in valid_keys:
            raise handle_context_error(
                ValueError(f"Invalid context key: {key}"), key, "bind"
            )

        if key == "trace_id":
            trace_ctx.set(value)
        elif key == "span_id":
            span_ctx.set(value)
        elif key == "latency_ms":
            latency_ctx.set(value)
        elif key == "status_code":
            status_code_ctx.set(value)
        elif key == "req_bytes":
            req_bytes_ctx.set(value)
        elif key == "res_bytes":
            res_bytes_ctx.set(value)
        elif key == "user_agent":
            user_agent_ctx.set(value)
        elif key == "client_ip":
            client_ip_ctx.set(value)
        elif key == "method":
            method_ctx.set(value)
        elif key == "path":
            path_ctx.set(value)
        elif key == "user_id":
            user_id_ctx.set(value)
        elif key == "user_roles":
            user_roles_ctx.set(value)
        elif key == "auth_scheme":
            auth_scheme_ctx.set(value)


def clear_context() -> None:
    """Reset all defined context variables to None."""
    trace_ctx.set(None)
    span_ctx.set(None)
    latency_ctx.set(None)
    status_code_ctx.set(None)
    req_bytes_ctx.set(None)
    res_bytes_ctx.set(None)
    user_agent_ctx.set(None)
    client_ip_ctx.set(None)
    method_ctx.set(None)
    path_ctx.set(None)
    user_id_ctx.set(None)
    user_roles_ctx.set(None)
    auth_scheme_ctx.set(None)


def context_copy() -> contextvars.Context:
    """Get a context snapshot suitable for propagation into asyncio.create_task.

    Returns:
        A contextvars.Context snapshot that can be used with
        asyncio.create_task(context_copy().run(func))
    """
    return contextvars.copy_context()


def get_trace_id() -> Optional[str]:
    """Get the current trace ID from context."""
    return trace_ctx.get()


def get_span_id() -> Optional[str]:
    """Get the current span ID from context."""
    return span_ctx.get()


def get_user_id() -> Optional[str]:
    """Get the current user ID from context."""
    return user_id_ctx.get()


def get_user_roles() -> Optional[List[str]]:
    """Get the current user roles from context."""
    return user_roles_ctx.get()


def get_auth_scheme() -> Optional[str]:
    """Get the current auth scheme from context."""
    return auth_scheme_ctx.get()


def bind_user_context(
    user_id: Optional[str] = None,
    user_roles: Optional[List[str]] = None,
    auth_scheme: Optional[str] = None,
) -> None:
    """Bind user context variables.

    Args:
        user_id: User identifier
        user_roles: List of user roles/scopes
        auth_scheme: Authentication scheme (e.g., 'Bearer', 'Basic')
    """
    if user_id is not None:
        user_id_ctx.set(user_id)
    if user_roles is not None:
        user_roles_ctx.set(user_roles)
    if auth_scheme is not None:
        auth_scheme_ctx.set(auth_scheme)


def set_trace_context(
    trace_id: str, span_id: str
) -> Tuple[contextvars.Token[Any], contextvars.Token[Any]]:
    """Set trace and span context variables.

    Args:
        trace_id: The trace ID to set
        span_id: The span ID to set

    Returns:
        Tuple of tokens for resetting the context variables
    """
    token_tid = trace_ctx.set(trace_id)
    token_sid = span_ctx.set(span_id)
    return token_tid, token_sid


def reset_trace_context(
    token_tid: contextvars.Token[Any], token_sid: contextvars.Token[Any]
) -> None:
    """Reset trace and span context variables.

    Args:
        token_tid: Token for trace_id context variable
        token_sid: Token for span_id context variable
    """
    trace_ctx.reset(token_tid)
    span_ctx.reset(token_sid)


def set_request_metadata(
    req_bytes: int,
    user_agent: str,
) -> Tuple[contextvars.Token[Any], contextvars.Token[Any]]:
    """Set request metadata context variables.

    Args:
        req_bytes: Request body size in bytes
        user_agent: User-Agent header value

    Returns:
        Tuple of tokens for resetting the context variables
    """
    token_req = req_bytes_ctx.set(req_bytes)
    token_ua = user_agent_ctx.set(user_agent)
    return token_req, token_ua


def set_response_metadata(
    res_bytes: int,
    status_code: int,
    latency_ms: float,
) -> Tuple[contextvars.Token[Any], contextvars.Token[Any], contextvars.Token[Any]]:
    """Set response metadata context variables.

    Args:
        res_bytes: Response body size in bytes
        status_code: HTTP status code
        latency_ms: Request latency in milliseconds

    Returns:
        Tuple of tokens for resetting the context variables
    """
    token_res = res_bytes_ctx.set(res_bytes)
    token_status = status_code_ctx.set(status_code)
    token_latency = latency_ctx.set(latency_ms)
    return token_res, token_status, token_latency


def reset_request_metadata(
    token_req: contextvars.Token[Any],
    token_ua: contextvars.Token[Any],
) -> None:
    """Reset request metadata context variables.

    Args:
        token_req: Token for req_bytes context variable
        token_ua: Token for user_agent context variable
    """
    req_bytes_ctx.reset(token_req)
    user_agent_ctx.reset(token_ua)


def reset_response_metadata(
    token_res: contextvars.Token[Any],
    token_status: contextvars.Token[Any],
    token_latency: contextvars.Token[Any],
) -> None:
    """Reset response metadata context variables.

    Args:
        token_res: Token for res_bytes context variable
        token_status: Token for status_code context variable
        token_latency: Token for latency_ms context variable
    """
    res_bytes_ctx.reset(token_res)
    status_code_ctx.reset(token_status)
    latency_ctx.reset(token_latency)
