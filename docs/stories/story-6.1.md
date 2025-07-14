Story 6.1 – Context Enricher: Request Metadata  
───────────────────────────────────  
Epic: 6 – Contextual Enrichers  
Sprint Target: Sprint #⟪next⟫  
Story Points: 5

**As a FastAPI developer**  
I want each log to include HTTP request metadata (method, path, status, duration, client IP)  
So that I can trace and diagnose request-specific behavior directly from the logs.

───────────────────────────────────  
Acceptance Criteria

- A `RequestContextEnricher` is implemented and registered via middleware
- For each HTTP request:  
  • `method`, `path`, `status_code`, `client_ip`, `duration_ms`, and `trace_id` are added to logs
- All log events generated during the request share the same context
- `trace_id` is either extracted from headers or generated per request
- Middleware sets up and tears down context per-request safely (supports async)
- Unit tests verify:  
  • Context is injected and accessible during request  
  • Fields appear in emitted logs  
  • Cleanup occurs after request lifecycle
- README updated with explanation and usage example

───────────────────────────────────  
Tasks / Technical Checklist

1. Implement ASGI middleware in `fapilog/middleware.py`:

   - On request start:  
     • Generate `trace_id` if missing  
     • Record method, path, start time, client IP  
     • Inject into task-local context
   - On response:  
     • Compute duration  
     • Store status code  
     • Log enriched access log with context

2. Add Pydantic settings to allow custom header key for incoming `trace_id`

   - Default: `X-Request-ID`

3. Use `contextvars` to manage per-request state safely

   - Ensure nested async tasks inherit the context

4. Unit tests in `tests/test_request_enricher.py`:

   - `test_log_contains_request_fields()`
   - `test_trace_id_propagation()`
   - `test_context_teardown_after_request()`

5. Update README:
   - “Enrichers” section
   - Show how request context is automatically injected
   - Mention supported fields and how to override header for trace ID

───────────────────────────────────  
Dependencies / Notes

- Sets up groundwork for structured correlation between services
- Will be reused by other enrichers (e.g., user context)

───────────────────────────────────  
Definition of Done  
✓ Middleware injects and removes context safely  
✓ Logs include expected request fields  
✓ Tests pass and validate all edge cases  
✓ PR merged to **main** with reviewer approval  
✓ `CHANGELOG.md` and README updated under _Unreleased → Added_
