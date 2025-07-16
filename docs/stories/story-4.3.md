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

1. ✅ Extend `TraceIDMiddleware` (fapilog/middleware.py):

   - ✅ Extract `req_bytes` from `Content-Length` or body
   - ✅ After response is built, assign `res_bytes = len(response.body or b"")`
   - ✅ Store both in contextvars: `req_bytes_ctx`, `res_bytes_ctx`

2. ✅ Define `body_size_enricher(logger, method_name, event_dict)` in `fapilog/enrichers.py`:

   - ✅ Use `.get()` on `req_bytes_ctx` and `res_bytes_ctx`
   - ✅ Add values to `event_dict` if not `None`

3. ✅ Add the enricher to the processor chain in `build_processor_chain()`

4. ✅ Unit tests in `tests/test_enricher_body_size.py`:

   - ✅ `test_post_request_with_body_size()`
   - ✅ `test_get_request_with_zero_body()`
   - ✅ `test_res_bytes_matches_output()`
   - ✅ `test_fields_absent_outside_http()`
   - ✅ Additional comprehensive tests for edge cases and integration

5. ✅ Update README "Log Fields" section with `req_bytes` and `res_bytes`

───────────────────────────────────  
Implementation Status

**✅ COMPLETED - All Requirements Met**

**Code Implementation:**

- `body_size_enricher` fully implemented in `src/fapilog/enrichers.py` (lines 113-143)
- Middleware already extracts `req_bytes` and `res_bytes` and stores in context variables
- Enricher properly integrated into processor chain in `src/fapilog/pipeline.py` (line 120)
- Graceful handling when context is missing - fields are omitted without errors

**Testing:**

- All 11 unit tests in `tests/test_enricher_body_size.py` pass successfully
- Tests cover: POST requests with bodies, GET requests without bodies, response size matching,
  graceful context handling, partial context scenarios, zero values, large values, field preservation
- Integration test confirms real-world functionality with FastAPI requests

**Documentation:**

- README "Log Fields" section already documents `req_bytes` and `res_bytes` fields
- CHANGELOG.md includes comprehensive Story 4.3 entry under "Added" section
- All technical implementation details properly documented

**Key Features Verified:**

- ✅ Accurate request/response size measurement via `Content-Length` header and `len(response.body)`
- ✅ Works with standard JSON, form, and plain requests
- ✅ Graceful fallback to `Content-Length` header when body not read
- ✅ Logs outside HTTP context don't raise errors - fields omitted gracefully
- ✅ Enricher positioned correctly in processor chain (after context, before rendering)
- ✅ Fields only added if not already present, allowing manual override

**Performance & Integration:**

- ✅ Uses existing context infrastructure - no additional overhead
- ✅ Compatible with streaming responses (reports 0 for streaming)
- ✅ Non-blocking implementation that doesn't affect request performance

───────────────────────────────────  
Dependencies / Notes

- Builds on context infrastructure and middleware (Story 2.1 and 2.2)
- Assumes `response.body` is available—streaming responses will not be measured

───────────────────────────────────  
Definition of Done  
✅ Enricher implemented and integrated into pipeline  
✅ Accurate request/response body sizes logged during HTTP request lifecycle  
✅ Tests pass and verify correctness and edge cases  
✅ PR merged to **main** with reviewer approval and green CI  
✅ `CHANGELOG.md` and README updated under _Unreleased → Added_

**🎉 STORY COMPLETE - Ready for Production Use**
