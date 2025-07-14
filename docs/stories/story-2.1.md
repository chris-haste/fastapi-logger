Story 2.1 – `TraceIDMiddleware` (Correlation & Timing)  
───────────────────────────────────  
Epic: 2 – Middleware & Context Propagation  
Sprint Target: Sprint #⟪next⟫  
Story Points: 8

**As an observability engineer**  
I want middleware that injects a `trace_id` (and `span_id`) into each request’s context and measures request latency  
So that every log line can be correlated across services and performance metrics are recorded consistently.

───────────────────────────────────  
Acceptance Criteria

- Middleware implemented in **fapilog/middleware.py** as `TraceIDMiddleware(BaseHTTPMiddleware)`.
- Behaviour per HTTP request:  
  • Generate a UUID-v4 `trace_id` when header `X-Trace-Id` is absent; otherwise forward the incoming value.  
  • Generate a fresh UUID-v4 `span_id` on every request.  
  • Store both IDs in contextvars (`trace_ctx`, `span_ctx`) for log enrichment.  
  • Record start time; after response, compute latency in ms and add header `X-Response-Time-ms`.  
  • Echo `trace_id` in response header `X-Trace-Id`.
- Logs written during the request contain `trace_id`, `span_id`, `path`, `method`, `status_code`, and `latency_ms`.
- `configure_logging(app=fastapi_app)` registers the middleware once; repeated calls do not duplicate it.
- Works for both sync and async route handlers.
- Unit tests verify:  
  • Forwarding of existing `X-Trace-Id`.  
  • Generation of new IDs when header missing.  
  • Presence and numeric nature of `X-Response-Time-ms`.  
  • No context leakage after request completion.

───────────────────────────────────  
Tasks / Technical Checklist

1. Define context variables (fapilog/\_internal/context.py)  
    import contextvars  
    trace_ctx = contextvars.ContextVar("trace_id", default=None)  
    span_ctx = contextvars.ContextVar("span_id", default=None)

2. Implement TraceIDMiddleware in fapilog/middleware.py  
    class TraceIDMiddleware(BaseHTTPMiddleware):  
    async def dispatch(self, request, call_next):  
    import uuid, time  
    trace_id = request.headers.get("X-Trace-Id") or uuid.uuid4().hex  
    span_id = uuid.uuid4().hex  
    token_tid = trace_ctx.set(trace_id)  
    token_sid = span_ctx.set(span_id)  
    start = time.perf_counter()  
    try:  
    response = await call_next(request)  
    finally:  
    duration = round((time.perf_counter() - start) \* 1000, 2)  
    log.bind(path=request.url.path,  
    method=request.method,  
    status_code=response.status_code,  
    latency_ms=duration)  
    response.headers["X-Trace-Id"] = trace_id  
    response.headers["X-Response-Time-ms"] = str(duration)  
    trace_ctx.reset(token_tid)  
    span_ctx.reset(token_sid)  
    return response

3. Update processor chain (Epic 1) with an enricher that reads trace_ctx/span_ctx and injects IDs + latency into each event.

4. Extend configure_logging()  
   • Accept optional `app` parameter; if provided, add middleware only once.

5. Unit tests (tests/test_trace_middleware.py) using Starlette TestClient  
   • test_forward_trace_header  
   • test_generate_trace_header  
   • test_latency_header_present  
   • test_context_cleanup

6. README – add “Correlation IDs” section documenting headers and log fields.

───────────────────────────────────  
Dependencies / Notes

- Builds on log facade and processor enrichment from Epics 1.
- Contextvars will be reused for background-task and message-bus propagation in later stories.

───────────────────────────────────  
Definition of Done  
✓ All acceptance criteria satisfied; unit tests green.  
✓ PR merged to **main** with reviewer approval; CI green.  
✓ CHANGELOG updated under _Unreleased → Added_.
