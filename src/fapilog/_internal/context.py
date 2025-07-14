"""Context variables for request correlation and tracing."""

import contextvars
from typing import Optional

# Context variables for request correlation
trace_ctx = contextvars.ContextVar("trace_id", default=None)
span_ctx = contextvars.ContextVar("span_id", default=None)


def get_trace_id() -> Optional[str]:
    """Get the current trace ID from context."""
    return trace_ctx.get()


def get_span_id() -> Optional[str]:
    """Get the current span ID from context."""
    return span_ctx.get()


def set_trace_context(
    trace_id: str, span_id: str
) -> tuple[contextvars.Token, contextvars.Token]:
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
