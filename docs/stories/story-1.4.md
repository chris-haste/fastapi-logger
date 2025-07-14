Story 1.4 – Default Structlog Processor Pipeline  
───────────────────────────────────  
Epic: 1 – Core Library Foundation  
Sprint Target: Sprint #⟪next⟫  
Story Points: 5

**As an application developer**  
I want a robust default processor chain for `structlog`  
So that emitted logs are consistently structured, enriched, and properly formatted in both JSON and pretty-console modes.

───────────────────────────────────  
Acceptance Criteria

- A default processor chain is defined in **`fapilog/pipeline.py`** and imported by `configure_logging()`.
- The chain, for non-pretty (JSON) mode, executes in the following order:
  1. `add_log_level` – adds `"level"` key.
  2. `TimeStamper(fmt="iso", utc=True)` – adds ISO-8601 `"timestamp"`.
  3. `format_exc_info` – converts `exc_info` to string if present.
  4. `StackInfoRenderer()` – renders stack info when requested.
  5. `EventRenamer("event")` – renames `event` field if missing.
  6. Custom redaction processor (uses `settings.redact_patterns`).
  7. `JSONRenderer()` – outputs compact JSON.
- In pretty mode (`json_console="pretty"` or auto-TTY) the last processor switches to `ConsoleRenderer(colors=True)`, and `add_log_level` shows colourised level names.
- Pipeline honours `settings.sampling_rate` by dropping events probabilistically when < 1.0.
- Unit tests verify:  
  • Order of processors (assert types).  
  • JSON output contains expected keys.  
  • Pretty mode outputs a non-JSON string with ANSI colour codes (regex check).  
  • Sampling drops roughly correct proportion at rate 0.1 within statistical tolerance (flaky-safe).

───────────────────────────────────  
Tasks / Technical Checklist

1. **Create `fapilog/pipeline.py`**

   - Implement `build_processor_chain(settings: LoggingSettings, pretty: bool)` returning list.
   - Include internal `_redact_processor(patterns)` that masks matching values.
   - Include `_sampling_processor(rate)` that returns `None` for skipped events.

2. **Update `configure_logging()`**

   - Call `build_processor_chain(settings, pretty_mode)` and pass to `structlog.configure()`.
   - Ensure idempotence: re-config only if pipeline not already installed.

3. **Implement sampling utility** in `_internal/utils.py` if not already present.

4. **Unit Tests** (`tests/test_pipeline.py`)

   - `test_json_pipeline_keys()` – capture log, parse JSON, assert keys.
   - `test_pretty_pipeline_format()` – monkeypatch TTY, assert non-JSON output.
   - `test_sampling_processor()` – simulate 1 000 logs, assert 5–15 % kept with rate 0.1.

5. **Documentation**
   - README “Processor Chain” subsection describing each processor’s purpose and how to extend it.

───────────────────────────────────  
Dependencies / Notes

- Builds on `LoggingSettings` (Story 1.3) and `configure_logging()` (Story 1.2).
- Redaction regexes and sampling processor can be reused later for security & performance epics.

───────────────────────────────────  
Definition of Done  
✓ Acceptance criteria satisfied; unit tests green.  
✓ PR merged to **main** with reviewer approval; CI green.  
✓ `CHANGELOG.md` updated (_Unreleased → Added_).  
✓ README updated with pipeline documentation.
