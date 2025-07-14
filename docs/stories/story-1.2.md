# Story 1.2 – Logging Facade & Bootstrap

**Epic:** 1 – Core Library Foundation  
Sprint Target: Sprint #⟪next⟫  
Story Points: 8

**As an application developer**  
I want to import `log` and call `configure_logging()` once  
So that every FastAPI service (and any script) gains consistent, structured logging with minimal code.

───────────────────────────────────  
Acceptance Criteria

- `from fapilog import configure_logging, log` succeeds after project scaffold is installed.
- Executing `configure_logging()` returns a **structlog.BoundLogger** instance and registers it as the default logger.
- Subsequent calls to `configure_logging()` **do not** duplicate handlers or re-initialise sinks (idempotent).
- After bootstrap, `log.info("test_event")` emits a JSON log that contains at minimum:  
  • `timestamp` (ISO-8601, UTC)  
  • `level` (`info`)  
  • `event` (`"test_event"`)
- When `FAPILOG_JSON_CONSOLE=pretty` (or interactive TTY detected) logs render in colourised, human-readable form.
- When `FAPILOG_LEVEL=DEBUG`, the root log level honours the override.
- Works in **async** context: logging inside an `async def` does not raise `RuntimeError`.
- Unit tests verify:  
  • Idempotent bootstrap (handler count stable)  
  • JSON schema for a sample log record matches expected keys  
  • Pretty vs JSON rendering toggles based on env var

───────────────────────────────────  
Tasks / Technical Checklist

1.  **Implement facade in `fapilog/__init__.py`**

        import structlog
        __all__ = ["log", "configure_logging"]
        log = structlog.get_logger()

2.  **Create `fapilog/bootstrap.py`**

    - Define the `configure_logging()` function:
      - Accept optional kwargs (`level`, `sinks`, `json_console`) which override `LoggingSettings` (Story 1.3 dependency).
      - Build structlog processor chain: `[structlog.processors.TimeStamper(fmt="iso"), structlog.processors.add_log_level, structlog.processors.EventRenamer("event"), structlog.processors.format_exc_info, structlog.processors.JSONRenderer()]`.
      - Install standard library `logging` handler -> structlog wrapper.
      - Detect interactive TTY (`sys.stderr.isatty()`) for pretty output unless `json_console` explicitly set to `json`.
      - Return configured logger.

3.  **Idempotency Guard**

    - Maintain a module-level flag `_configured` or compare existing handlers before adding new ones.

4.  **Pretty Renderer**

    - Use `structlog.dev.ConsoleRenderer(colors=True)` when pretty mode active.

5.  **Environment Variable Overrides**

    - Read `FAPILOG_LEVEL` and `FAPILOG_JSON_CONSOLE` directly (temporary) until LoggingSettings (Story 1.3) lands; keep helper to merge settings later.

6.  **Unit Tests** (`tests/test_bootstrap.py`)

    - `test_configure_returns_logger()`
    - `test_idempotent()` – call twice, assert len(logging.root.handlers) unchanged.
    - `test_json_event_fields()` – capture log via `caplog`, assert keys.
    - `test_pretty_toggle()` – monkeypatch `isatty` & env var, assert renderer type.

7.  **Update README** – add example snippet under “Quick Start” using new API.

───────────────────────────────────  
Dependencies / Notes

- Relies on the project scaffold from Story 1.1.
- Temporary env-var reading will be refactored to use `LoggingSettings` once Story 1.3 merges.

───────────────────────────────────  
Definition of Done  
✓ All acceptance criteria met.  
✓ PR merged to **main** with reviewer approval and green CI.  
✓ `CHANGELOG.md` entry added under _Unreleased → Added_.  
✓ No duplicated handlers when `configure_logging()` is called multiple times (verified in tests).

───────────────────────────────────  
Delivery Summary

- Implemented `fapilog` logging facade and bootstrap as specified.
- `configure_logging()` is idempotent, returns a structlog logger, and does not duplicate handlers or sinks.
- Logging output includes `timestamp` (ISO-8601, UTC), `level`, and `event` fields as required.
- Supports pretty (colorized) and JSON output, toggled by `FAPILOG_JSON_CONSOLE` or TTY detection.
- Honors `FAPILOG_LEVEL` for log level override.
- Fully async-compatible; logging in async contexts is safe.
- Comprehensive unit tests cover:
  - Idempotent bootstrap (handler count stable)
  - Log event JSON schema
  - Pretty vs JSON rendering
  - Log level overrides
  - Async context safety
- All tests pass and import checks are green.
- Implementation follows FastAPI and Pydantic v2 best practices, with clear separation of API, middleware, and logic layers.
