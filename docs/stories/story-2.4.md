Story 2.4 – Test Coverage for Middleware & Context Propagation  
───────────────────────────────────  
Epic: 2 – Middleware & Context Propagation  
Sprint Target: Sprint #⟪next⟫  
Story Points: 5

**As a contributor or reviewer**  
I want reliable test coverage for all middleware and context utility behavior  
So that I can refactor or extend logging functionality with confidence that trace propagation and request metadata will remain stable.

───────────────────────────────────  
Acceptance Criteria

- All logic introduced in Epics 2.1 to 2.3 is covered by unit or integration tests.
- Test coverage includes:  
  • `TraceIDMiddleware` request cycle: header passthrough, new trace generation, context lifespan  
  • Request/response metadata enrichment (status code, latency, byte sizes, user-agent)  
  • Context utility helpers: `get_context()`, `bind_context()`, `clear_context()`, `context_copy()`  
  • Background task using `context_copy().run()` includes correct trace fields in logs
- Tests ensure isolation between concurrent requests—trace IDs do not leak across `asyncio` tasks
- Coverage report shows ≥ 90% coverage for `fapilog/middleware.py` and `fapilog/_internal/context.py`
- CI (GitHub Actions or Tox) enforces this threshold with `--cov-fail-under=90`
- README’s development section includes command to run middleware tests and view coverage delta

───────────────────────────────────  
Tasks / Technical Checklist

1. Add/complete test modules:  
   • `tests/test_trace_middleware.py`  
   • `tests/test_context_utils.py`  
   • `tests/test_enricher_request.py`
2. Use `TestClient` (Starlette or FastAPI) to simulate HTTP requests with and without `X-Trace-Id`
3. Use `asyncio.create_task()` + `context_copy()` to verify context propagation in background jobs
4. Patch or monkeypatch `contextvars` to simulate context leakage attempts, confirm isolation
5. Generate coverage report locally with:  
    hatch run test -- --cov=fapilog --cov-report=term-missing --cov-fail-under=90
6. Ensure coverage section is present in `pytest.ini` or `pyproject.toml`
7. Update CI workflow to reflect final threshold and output coverage summary on PRs
8. Add README note for contributors:  
    “Middleware and context utilities must retain 90%+ test coverage; PRs below threshold will fail CI.”

───────────────────────────────────  
Dependencies / Notes

- Finalizes testing for Stories 2.1–2.3; no new production logic introduced
- Story ensures defensive coverage for fragile areas (trace propagation, task-local state)

───────────────────────────────────  
Definition of Done  
✓ All acceptance criteria met and coverage ≥ 90% for relevant modules  
✓ PR merged to **main** with reviewer approval and passing CI  
✓ `CHANGELOG.md` updated under _Unreleased → Added_  
✓ README updated with contributor-facing test/coverage instructions
