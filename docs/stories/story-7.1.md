Story 7.1 – Redactor: Field Redaction Support  
───────────────────────────────────  
Epic: 7 – Data Redaction  
Sprint Target: Sprint #⟪next⟫  
Story Points: 5

**As a security-conscious developer**  
I want to automatically redact sensitive fields from log output  
So that private or confidential data (e.g., passwords, tokens) is not exposed.

───────────────────────────────────  
Acceptance Criteria

- A redaction processor is implemented in `fapilog/enrichers.py` (or new `redactors.py`)
- Configurable list of field names to redact via settings (`FAPILOG_REDACT_FIELDS`)
- Redacted fields have values replaced with `"***"` or `"REDACTED"`
- Redaction supports nested dictionaries (e.g., `user.password`)
- Redaction runs after enrichers and before rendering/sink
- Unit tests confirm:  
  • Explicit fields are redacted  
  • Redacted output does not leak original values  
  • Nested fields are correctly handled
- README documents usage, configuration, and limitations

───────────────────────────────────  
Tasks / Technical Checklist

1. Implement `redact_sensitive_fields(event_dict)` processor

   - Accepts list of dot-path fields (e.g., `user.password`, `auth.token`)
   - Walks event_dict and overwrites matching keys
   - Default replacement value: `"REDACTED"`

2. Add redaction config to `fapilog/settings.py`:

   - `REDACT_FIELDS: list[str] = []`
   - `REDACT_REPLACEMENT: str = "REDACTED"`

3. Insert redaction processor in the pipeline before rendering/sinks

4. Add unit tests in `tests/test_redactor.py`:

   - `test_flat_key_redaction()`
   - `test_nested_field_redaction()`
   - `test_custom_redaction_value()`
   - `test_non_matching_fields_untouched()`

5. README updates:
   - “Data Redaction” section
   - Example env config and redacted log output
   - Notes on performance and deep nesting behavior

───────────────────────────────────  
Dependencies / Notes

- No third-party libraries; use recursive walk or `pydash.get/set`-like logic
- Performance must be acceptable for real-time logging

───────────────────────────────────  
Definition of Done  
✓ Sensitive fields are removed from logs based on config  
✓ Redaction is reliable and tested  
✓ PR merged to **main** with reviewer approval  
✓ `CHANGELOG.md` and README updated under _Unreleased → Added_
