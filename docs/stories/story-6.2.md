Story 6.2 – Context Enricher: Correlation + Trace ID Propagation  
───────────────────────────────────  
Epic: 6 – Contextual Enrichers  
Sprint Target: Sprint #⟪next⟫  
Story Points: 5

**As a service developer**  
I want trace and correlation IDs to be consistently propagated in logs and across requests  
So that I can follow requests end-to-end across distributed services.

───────────────────────────────────  
Acceptance Criteria

- Middleware extracts an incoming trace ID from configurable request header (default: `X-Request-ID`)
- If no trace ID is present, a UUID is generated
- The trace ID is injected into all logs during the request lifecycle
- Outgoing HTTP requests made via `httpx.AsyncClient` (opt-in patch) include the trace ID in headers
- All internal log events contain the `trace_id` field
- `trace_id` can be accessed via an API: `get_current_trace_id()`
- Unit tests validate trace propagation and override behavior
- README includes an example of trace header config and downstream propagation

───────────────────────────────────  
Tasks / Technical Checklist

1. Update middleware logic (`fapilog/middleware.py`):

   - Read incoming header (`X-Request-ID` by default)
   - Validate or generate UUID
   - Store in `contextvars` for log access
   - Expose `get_current_trace_id()` function

2. Patch `httpx.AsyncClient` (optional monkeypatch or wrapper):

   - Add middleware that injects `X-Request-ID` header on outgoing requests
   - Only applied if explicitly enabled via settings or import hook

3. Add to settings (`fapilog/settings.py`):

   - `TRACE_HEADER_NAME` (default: `X-Request-ID`)
   - `ENABLE_HTTPX_TRACE_PROPAGATION` (default: False)

4. Unit tests in `tests/test_trace_propagation.py`:

   - `test_incoming_trace_id_preserved()`
   - `test_generated_trace_id_present()`
   - `test_trace_id_in_httpx_request()`
   - `test_get_current_trace_id()`

5. README updates:
   - Explain how trace IDs are propagated
   - Document header name config and `httpx` patching
   - Example showing logs from multiple services with shared trace ID

───────────────────────────────────  
Dependencies / Notes

- Shared context must be thread-safe and async-safe
- Outgoing propagation should be opt-in to avoid side effects in upstream code

───────────────────────────────────  
Definition of Done  
✓ Incoming trace IDs are respected or generated  
✓ Logs include consistent `trace_id`  
✓ Propagation to downstream services supported (opt-in)  
✓ Unit tests pass  
✓ PR merged to **main** with reviewer approval  
✓ `CHANGELOG.md` and README updated under _Unreleased → Added_
