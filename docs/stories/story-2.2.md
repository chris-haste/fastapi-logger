Story 2.2 – Request & Response Metadata Enricher  
───────────────────────────────────  
Epic: 2 – Middleware & Context Propagation  
Sprint Target: Sprint #⟪next⟫  
Story Points: 5

**As an SRE**  
I want each log line to include request and response metadata such as status code, body sizes, and user-agent  
So that I can quickly analyse traffic patterns and troubleshoot issues without additional tooling.

───────────────────────────────────  
Acceptance Criteria

- A new processor `request_response_enricher` is added to **fapilog/enrichers.py**.
- The processor reads from contextvars populated by `TraceIDMiddleware` and adds to every event:  
  • `status_code` – HTTP status integer.  
  • `latency_ms` – already captured, but ensured present for all events.  
  • `req_bytes` – size of request body in bytes (0 if no body or streaming).  
  • `res_bytes` – size of response body in bytes (0 if streaming).  
  • `user_agent` – value of `User-Agent` header or `"-"`.
- Processor is inserted into the default chain directly **before** JSON/Console renderer.
- Works for both sync and async routes; no blocking I/O introduced.
- Logs emitted outside of a request context (e.g., startup) do **not** raise errors—the processor simply leaves fields absent.
- Unit tests verify:  
  • Correct enrichment for a JSON POST (non-empty body).  
  • GET request with no body reports `req_bytes == 0`.  
  • Non-request log (manual call) does not include the request/response fields.

───────────────────────────────────  
Tasks / Technical Checklist

1. **Context variables** – extend `TraceIDMiddleware` to capture:  
    req_size = int(request.headers.get("content-length", 0) or 0)  
    res_size = 0 # set after response body known  
   After `response` is obtained, set `res_size = len(response.body or b"")` (works for JSONResponse / PlainTextResponse).  
   Store both in new contextvars `req_bytes_ctx`, `res_bytes_ctx`.

2. **Implement processor** in fapilog/enrichers.py  
    def request_response_enricher(logger, method_name, event_dict):  
    rb = req_bytes_ctx.get(None)  
    if rb is not None:  
    event_dict["req_bytes"] = rb  
    event_dict["res_bytes"] = res_bytes_ctx.get(0)  
    event_dict["status_code"] = status_code_ctx.get(None)  
    event_dict["latency_ms"] = latency_ctx.get(None)  
    event_dict["user_agent"] = ua_ctx.get("-")  
    return event_dict

3. **Update pipeline builder** (Story 1.4) to include the new enricher.

4. **Unit Tests** (`tests/test_enricher_request.py`) with TestClient

   - `test_post_with_body_sizes`
   - `test_get_no_body`
   - `test_outside_request_no_keys`

5. **README** – extend “Log Fields” table to document the five new keys.

───────────────────────────────────  
Dependencies / Notes

- Builds on `TraceIDMiddleware` (Story 2.1) and processor chain infrastructure from Epic 1.
- Streaming responses will report `res_bytes = 0` (acceptable for now; future enhancement).

───────────────────────────────────  
Definition of Done  
✓ Acceptance criteria met; all tests green.  
✓ PR merged to **main** with reviewer approval; CI green.  
✓ CHANGELOG updated under _Unreleased → Added_.
