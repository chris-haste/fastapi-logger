Story 4.3 – Request Size & Response Size Enricher  
───────────────────────────────────  
Epic: 4 – Field Enrichers  
Sprint Target: Sprint #⟪next⟫  
Story Points: 5

**As an API maintainer**  
I want each log entry to include request and response body sizes  
So that I can track payload volumes for performance tuning and anomaly detection.

───────────────────────────────────  
Acceptance Criteria

- A new processor `body_size_enricher` is implemented in **fapilog/enrichers.py**
- It enriches each log event with the following fields (if present in context):  
  • `req_bytes`: size of the incoming request body in bytes  
  • `res_bytes`: size of the outgoing response body in bytes
- These values are extracted by `TraceIDMiddleware` and stored in contextvars
- Works for standard JSON, form, and plain requests; `req_bytes` falls back to `Content-Length` header if body not read
- `res_bytes` is set based on `len(response.body)` (when available)
- Enricher is inserted after context and before final rendering
- Logs emitted outside an HTTP context do not raise errors—fields are omitted gracefully
- Unit tests verify:  
  • Accurate request/response size measurement for various methods  
  • Enricher skips gracefully when context is missing  
  • Field values are numeric and consistent with real payload sizes

───────────────────────────────────  
Tasks / Technical Checklist

1. Extend `TraceIDMiddleware` (fapilog/middleware.py):

   - Extract `req_bytes` from `Content-Length` or body
   - After response is built, assign `res_bytes = len(response.body or b"")`
   - Store both in contextvars: `req_bytes_ctx`, `res_bytes_ctx`

2. Define `body_size_enricher(logger, method_name, event_dict)` in `fapilog/enrichers.py`:

   - Use `.get()` on `req_bytes_ctx` and `res_bytes_ctx`
   - Add values to `event_dict` if not `None`

3. Add the enricher to the processor chain in `build_processor_chain()`

4. Unit tests in `tests/test_enricher_body_size.py`:

   - `test_post_request_with_body_size()`
   - `test_get_request_with_zero_body()`
   - `test_res_bytes_matches_output()`
   - `test_fields_absent_outside_http()`

5. Update README “Log Fields” section with `req_bytes` and `res_bytes`

───────────────────────────────────  
Dependencies / Notes

- Builds on context infrastructure and middleware (Story 2.1 and 2.2)
- Assumes `response.body` is available—streaming responses will not be measured

───────────────────────────────────  
Definition of Done  
✓ Enricher implemented and integrated into pipeline  
✓ Accurate request/response body sizes logged during HTTP request lifecycle  
✓ Tests pass and verify correctness and edge cases  
✓ PR merged to **main** with reviewer approval and green CI  
✓ `CHANGELOG.md` and README updated under _Unreleased → Added_
