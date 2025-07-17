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

- Middleware extracts an incoming trace ID from configurable request header (default: `x-request-id`)
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

   - Read incoming header (`x-request-id` by default)
   - Validate or generate UUID
   - Store in `contextvars` for log access
   - Expose `get_current_trace_id()` function

2. Patch `httpx.AsyncClient` (optional monkeypatch or wrapper):

   - Add middleware that injects `x-request-id` header on outgoing requests
   - Only applied if explicitly enabled via settings or import hook

3. Add to settings (`fapilog/settings.py`):

   - `TRACE_HEADER_NAME` (default: `x-request-id`)
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

───────────────────────────────────  
Implementation Status: **✅ COMPLETED**

**Summary:**

- ✅ All acceptance criteria implemented and tested
- ✅ `get_current_trace_id()` API function available
- ✅ httpx trace propagation working (opt-in)
- ✅ Settings added: `trace_id_header`, `enable_httpx_trace_propagation`
- ✅ Unit tests passing (8/8 in `test_trace_propagation.py`)
- ✅ Documentation updated in API reference
- ✅ Example added: `examples/17_trace_propagation.py`
- ✅ README trace propagation section updated

───────────────────────────────────

## 🔍 QA Review Results

**Review Date:** December 2024  
**QA Status:** ✅ **PASSED** - Ready for production deployment

### Test Results Summary

| Component         | Status    | Details                                      |
| ----------------- | --------- | -------------------------------------------- |
| **Unit Tests**    | ✅ PASSED | 8/8 tests passing (100%)                     |
| **Imports & API** | ✅ PASSED | All functions exported correctly             |
| **Examples**      | ✅ PASSED | Working example code provided                |
| **Documentation** | ✅ PASSED | Comprehensive docs in README & API reference |

### Key Validation Points

**✅ Middleware Implementation**

- Trace ID extraction from configurable headers working correctly
- UUID fallback generation when no header present
- Context binding preserves metadata across request lifecycle
- Exception handling maintains trace ID consistency

**✅ Settings Configuration**

- `trace_id_header` configurable (default: "X-Request-ID")
- `enable_httpx_trace_propagation` opt-in feature working
- Environment variable support with `FAPILOG_` prefix
- Proper field validation and error handling

**✅ API Functions**

- `get_current_trace_id()` exported and accessible
- Returns correct trace ID within request context
- Returns `None` safely outside request context
- Thread-safe and async-safe via contextvars

**✅ httpx Trace Propagation**

- Automatic header injection for outgoing requests
- Safe patching with global state tracking
- Graceful fallback when httpx not installed
- Can be safely disabled/re-enabled

**✅ Test Coverage**
All 8 tests in `test_trace_propagation.py` passing:

1. `test_incoming_trace_id_preserved` - Incoming trace IDs respected
2. `test_generated_trace_id_present` - UUIDs generated when needed
3. `test_get_current_trace_id` - API function works in context
4. `test_get_current_trace_id_no_context` - Returns None outside context
5. `test_trace_id_in_httpx_request` - httpx propagation working
6. `test_httpx_propagation_disabled` - Opt-in behavior confirmed
7. `test_custom_trace_header_name` - Custom headers supported
8. `test_trace_propagation_with_httpx_unavailable` - Graceful degradation

**✅ Documentation Quality**

- README.md contains comprehensive trace propagation examples
- API reference includes complete function documentation
- Working example (`examples/17_trace_propagation.py`) demonstrates all features
- Environment variable configuration documented

### Acceptance Criteria Validation

| Criteria                                              | Status    | Implementation                             |
| ----------------------------------------------------- | --------- | ------------------------------------------ |
| Middleware extracts trace ID from configurable header | ✅ PASSED | `TraceIDMiddleware` in `middleware.py`     |
| UUID generated if no trace ID present                 | ✅ PASSED | Automatic fallback with `uuid.uuid4().hex` |
| Trace ID injected into all logs during request        | ✅ PASSED | Context enrichment via `bind_context()`    |
| httpx.AsyncClient propagation (opt-in)                | ✅ PASSED | `httpx_patch.py` implementation            |
| All log events contain trace_id field                 | ✅ PASSED | Verified via context binding               |
| get_current_trace_id() API available                  | ✅ PASSED | Function exported in `__init__.py`         |
| Unit tests validate functionality                     | ✅ PASSED | 8/8 tests passing                          |
| README includes examples                              | ✅ PASSED | Comprehensive documentation                |

### Final Assessment

**✅ PRODUCTION-READY**

- All acceptance criteria fully implemented
- Robust error handling and graceful degradation
- Thread-safe and async-safe implementation
- Follows FastAPI/Pydantic v2 best practices
- Comprehensive test coverage and documentation

**Recommendation: ✅ APPROVE FOR PRODUCTION DEPLOYMENT**
