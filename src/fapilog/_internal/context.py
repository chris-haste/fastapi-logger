"""Context variables for request correlation and tracing."""

import contextvars
from typing import Any, Dict, Optional, Tuple

# Context variables for request correlation
trace_ctx = contextvars.ContextVar("trace_id", default=None)
span_ctx = contextvars.ContextVar("span_id", default=None)

# Context variables for request/response metadata
req_bytes_ctx = contextvars.ContextVar("req_bytes", default=None)
res_bytes_ctx = contextvars.ContextVar("res_bytes", default=None)
status_code_ctx = contextvars.ContextVar("status_code", default=None)
latency_ctx = contextvars.ContextVar("latency_ms", default=None)
user_agent_ctx = contextvars.ContextVar("user_agent", default=None)

# Context variables for request details (Story 6.1)
client_ip_ctx = contextvars.ContextVar("client_ip", default=None)
method_ctx = contextvars.ContextVar("method", default=None)
path_ctx = contextvars.ContextVar("path", default=None)


def get_context() -> Dict[str, Any]:
    """Get the current context as a dictionary.

    Returns:
        Dictionary containing current trace_id, span_id, latency_ms,
        status_code, req_bytes, res_bytes, user_agent, client_ip, method,
        and path values.
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
    }


def bind_context(**kwargs: Any) -> None:
    """Set or overwrite context variables for the current task.

    Args:
        **kwargs: Context variables to set. Valid keys are:
            trace_id, span_id, latency_ms, status_code, req_bytes, res_bytes,
            user_agent, client_ip, method, path
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
    }

    for key, value in kwargs.items():
        if key not in valid_keys:
            raise ValueError(f"Invalid context key: {key}")

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


def set_trace_context(
    trace_id: str, span_id: str
) -> Tuple[contextvars.Token, contextvars.Token]:
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
    token_tid: contextvars.Token, token_sid: contextvars.Token
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
) -> Tuple[contextvars.Token, contextvars.Token]:
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
) -> tuple[contextvars.Token, contextvars.Token, contextvars.Token]:
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
    token_req: contextvars.Token,
    token_ua: contextvars.Token,
) -> None:
    """Reset request metadata context variables.

    Args:
        token_req: Token for req_bytes context variable
        token_ua: Token for user_agent context variable
    """
    req_bytes_ctx.reset(token_req)
    user_agent_ctx.reset(token_ua)


def reset_response_metadata(
    token_res: contextvars.Token,
    token_status: contextvars.Token,
    token_latency: contextvars.Token,
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
