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

───────────────────────────────────  
**COMPLETED WORK SUMMARY**

✅ **ContextVar Utilities Implementation**

- Created comprehensive context management utilities in `fapilog/_internal/context.py`
- Implemented `get_context()`, `bind_context()`, `clear_context()`, and `context_copy()` functions
- Added proper error handling and validation for context operations
- Achieved 100% test coverage for context utilities

✅ **Middleware Integration**

- Verified `TraceIDMiddleware` properly uses `bind_context()` for initial population
- Confirmed `clear_context()` is called in finally block for proper cleanup
- Ensured no manual context variable resets remain in middleware

✅ **Background Task Context Propagation**

- Implemented `context_copy()` function for safe context propagation
- Added comprehensive tests demonstrating `asyncio.create_task(context_copy().run(func))` usage
- Verified context inheritance works correctly in background tasks

✅ **Context Leak Prevention**

- Implemented `clear_context()` to reset all context variables to None
- Added tests confirming separate requests receive different trace_ids
- Verified no cross-request context leakage occurs

✅ **Comprehensive Testing**

- Created `tests/test_context_utils.py` with 10 comprehensive test cases
- Tested context retrieval, binding, clearing, and propagation scenarios
- Verified background task context inheritance and multiple task scenarios
- Achieved 94.76% overall test coverage (exceeds 85% requirement)

✅ **Documentation**

- Updated README.md with "Using Context in Background Tasks" section
- Provided clear example showing context propagation to background tasks
- Documented proper usage patterns for developers

✅ **Quality Assurance**

- All 63 tests pass successfully
- Fixed import issues in test files
- Updated CHANGELOG.md with Story 2.3 completion entry
- Verified all acceptance criteria are met

**Technical Implementation Details:**

- Used `contextvars` for thread-safe context management
- Implemented proper validation for context variable keys
- Added comprehensive error handling for invalid operations
- Ensured backward compatibility with existing middleware
- Followed FastAPI and Pydantic V2 best practices

**Files Modified:**

- `src/fapilog/_internal/context.py` - Core context utilities
- `tests/test_context_utils.py` - Comprehensive test suite
- `README.md` - Background task usage documentation
- `CHANGELOG.md` - Story completion entry
