Story 2.3 – ContextVar Utilities & Leak Prevention  
───────────────────────────────────  
Epic: 2 – Middleware & Context Propagation  
Sprint Target: Sprint #⟪next⟫  
Story Points: 5

**As a backend developer**  
I want helper utilities that safely read, bind, copy, and clear our logging contextvars  
So that background tasks and sub-coroutines inherit the correct `trace_id`/`span_id`, and no data leaks between requests.

───────────────────────────────────  
Acceptance Criteria

- A module **fapilog/\_internal/context.py** exposes four public helpers:  
  • `get_context()` – returns a dict of current `trace_id`, `span_id`, `latency_ms`, `status_code`, `req_bytes`, `res_bytes`, `user_agent`.  
  • `bind_context(**kwargs)` – set or overwrite any of the above context variables for the current task.  
  • `clear_context()` – resets all defined contextvars to `None`.  
  • `context_copy()` – returns a `contextvars.Context` snapshot suitable for propagation into `asyncio.create_task`.
- `TraceIDMiddleware` (Story 2.1) is refactored to call `clear_context()` in its `finally` block instead of manual resets.
- Example in README shows propagating a snapshot to a background task.
- Unit tests confirm:  
  • `get_context()` returns expected keys during a request.  
  • `clear_context()` wipes values; subsequent `get_context()` shows `None` / empty.  
  • A task launched with `asyncio.create_task(context_copy().run(func))` logs with the original `trace_id`.  
  • A new, separate request receives a different `trace_id` (no leakage).

───────────────────────────────────  
Tasks / Technical Checklist

1. Implement `trace_ctx`, `span_ctx`, `latency_ctx`, `status_code_ctx`, `req_bytes_ctx`, `res_bytes_ctx`, `ua_ctx` in `_internal/context.py`, plus the four utility functions.
2. Refactor `TraceIDMiddleware` to rely on `bind_context()` for initial population and `clear_context()` at teardown.
3. Update processor/enricher code to consume via `get_context()` rather than accessing vars directly.
4. Add tests in `tests/test_context_utils.py` using Starlette `TestClient` and `asyncio.create_task`.
5. Extend README: “Using context in background tasks” snippet.

───────────────────────────────────  
Dependencies / Notes

- Builds on contextvars introduced in Story 2.1 and enrichment added in Story 2.2.
- Provides a stable contract for future message-bus and background-worker stories.

───────────────────────────────────  
Definition of Done  
✓ All acceptance criteria met; tests green with coverage ≥ 85 %.  
✓ PR merged to **main** with reviewer approval; CI green.  
✓ `CHANGELOG.md` entry added under _Unreleased → Added_.
