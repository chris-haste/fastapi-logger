Story 7.3 – Redactor: Context-Aware Redaction by Log Level  
───────────────────────────────────  
Epic: 7 – Data Redaction  
Sprint Target: Sprint #⟪next⟫  
Story Points: 5

**As a developer**  
I want redaction to be applied only at or above a specified log level  
So that full context is available in debug logs, but sensitive data is hidden in production logs.

───────────────────────────────────  
Acceptance Criteria

- Redaction processors (both manual and PII) are conditionally applied based on the log level of the event
- `FAPILOG_REDACT_LEVEL` setting defines the minimum log level for redaction (e.g., "INFO")
- DEBUG and lower logs bypass redaction unless configured otherwise
- Log level comparison uses standard order: DEBUG < INFO < WARNING < ERROR < CRITICAL
- Unit tests verify behavior at different log levels
- README includes an example of level-aware redaction and usage guidance

───────────────────────────────────  
Tasks / Technical Checklist

1. Add `REDACT_LEVEL: str = "INFO"` to `fapilog/settings.py`

   - Parse and normalize to enum or integer for comparison

2. Wrap `redact_sensitive_fields()` and `auto_redact_pii()` processors

   - Check event_dict["level"] before applying redaction logic
   - Skip processing if level is lower than configured threshold

3. Add helper to map level strings to numeric values (e.g., INFO = 20)

4. Add unit tests in `tests/test_level_redaction.py`:

   - `test_debug_log_not_redacted()`
   - `test_info_log_redacted()`
   - `test_custom_redact_level()`
   - `test_missing_level_defaults_to_redact()`

5. Update README:
   - Add section “Level-Aware Redaction”
   - Example showing DEBUG vs INFO log output
   - Explain how to configure the `FAPILOG_REDACT_LEVEL` setting

───────────────────────────────────  
Dependencies / Notes

- Assumes `event_dict["level"]` is normalized early in the processing pipeline
- Aids dev debugging while enforcing data safety in production

───────────────────────────────────  
Definition of Done  
✓ Redaction logic respects configured log level  
✓ Tests confirm enforcement at all log levels  
✓ PR merged to **main** with reviewer approval  
✓ `CHANGELOG.md` and README updated under _Unreleased → Added_
