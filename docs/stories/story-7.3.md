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

- [x] Redaction processors (both manual and PII) are conditionally applied based on the log level of the event
- [x] `FAPILOG_REDACT_LEVEL` setting defines the minimum log level for redaction (e.g., "INFO")
- [x] DEBUG and lower logs bypass redaction unless configured otherwise
- [x] Log level comparison uses standard order: DEBUG < INFO < WARNING < ERROR < CRITICAL
- [x] Unit tests verify behavior at different log levels
- [x] README includes an example of level-aware redaction and usage guidance

───────────────────────────────────  
Tasks / Technical Checklist

1. [x] Add `REDACT_LEVEL: str = "INFO"` to `fapilog/settings.py`

   - [x] Parse and normalize to enum or integer for comparison

2. [x] Wrap `redact_sensitive_fields()` and `auto_redact_pii()` processors

   - [x] Check event_dict["level"] before applying redaction logic
   - [x] Skip processing if level is lower than configured threshold

3. [x] Add helper to map level strings to numeric values (e.g., INFO = 20)

4. [x] Add unit tests in `tests/test_level_redaction.py`:

   - [x] `test_debug_log_not_redacted()`
   - [x] `test_info_log_redacted()`
   - [x] `test_custom_redact_level()`
   - [x] `test_missing_level_defaults_to_redact()`

5. [x] Update README:
   - [x] Add section "Level-Aware Redaction"
   - [x] Example showing DEBUG vs INFO log output
   - [x] Explain how to configure the `FAPILOG_REDACT_LEVEL` setting

───────────────────────────────────  
Dependencies / Notes

- [x] Assumes `event_dict["level"]` is normalized early in the processing pipeline
- [x] Aids dev debugging while enforcing data safety in production

───────────────────────────────────  
QA Review Findings

**Implementation Status: ✅ COMPLETE**

**Core Implementation:**

- **File**: `src/fapilog/redactors.py` (lines 6-48)
- **Key Functions**:
  - `_get_log_level_numeric()` - Converts log level strings to numeric values for comparison
  - `_should_redact_at_level()` - Determines if redaction should be applied based on event and redact levels
  - All redaction processors updated to respect `redact_level` parameter
- **Log Level Mapping**: Standard Python logging levels (DEBUG=10, INFO=20, WARNING=30, ERROR=40, CRITICAL=50)
- **Safe Defaults**: Invalid log levels default to applying redaction for security

**Settings Integration:**

- **File**: `src/fapilog/settings.py` (lines 44-47)
- **Setting**: `redact_level: str = Field(default="INFO", description="Minimum log level for redaction")`
- **Environment Variable**: `FAPILOG_REDACT_LEVEL` for environment-based configuration
- **Validation**: Case-insensitive level parsing with proper error handling

**Processor Integration:**

- **Pattern Redaction**: `_redact_processor()` in `src/fapilog/pipeline.py` supports `redact_level` parameter
- **Field Redaction**: `field_redactor()` in `src/fapilog/redactors.py` supports `redact_level` parameter
- **PII Auto-Redaction**: `auto_redact_pii_processor()` in `src/fapilog/_internal/pii_patterns.py` supports `redact_level` parameter
- **Consistent Behavior**: All redaction types respect the same level checking logic

**Test Coverage:**

- **File**: `tests/test_level_redaction.py` (325 lines, 19 comprehensive tests)
- **Coverage Areas**:
  - ✅ Log level helper functions (5 tests)
  - ✅ Pattern-based redaction with levels (4 tests)
  - ✅ Field-based redaction with levels (4 tests)
  - ✅ PII auto-redaction with levels (4 tests)
  - ✅ Integration scenarios (2 tests)
- **All tests pass**: 19/19 tests successful
- **Edge Cases**: Invalid levels, missing levels, different redact thresholds

**Documentation:**

- **README.md**: Complete "Level-Aware Redaction" section with configuration examples
- **User Guide**: Updated with level-aware redaction configuration and use cases
- **Example**: `examples/21_level_aware_redaction.py` (284 lines) demonstrating all functionality
- **CHANGELOG.md**: Feature implementation documented

**Functional Verification:**

✅ **DEBUG logs**: No redaction applied (full context preserved)  
✅ **INFO+ logs**: Redaction applied (sensitive data protected)  
✅ **Custom levels**: Configurable thresholds work correctly (DEBUG, INFO, WARNING, ERROR, CRITICAL)  
✅ **All redaction types**: Pattern, field, and PII redaction all respect level settings  
✅ **Environment config**: `FAPILOG_REDACT_LEVEL` environment variable works properly  
✅ **Safe defaults**: Missing or invalid levels default to applying redaction

**Real-World Use Cases Tested:**

✅ **Development**: Full debugging context (REDACT_LEVEL=CRITICAL)  
✅ **Staging**: Realistic production testing (REDACT_LEVEL=WARNING)  
✅ **Production**: Maximum security compliance (REDACT_LEVEL=INFO)

**Performance Characteristics:**

- ✅ **O(1) level checking**: Constant time lookup with numeric comparison
- ✅ **Early exit**: DEBUG logs bypass all redaction processing when threshold is INFO+
- ✅ **Zero overhead**: No performance impact on production logging
- ✅ **Memory efficient**: No additional memory allocation for level checking

**Example Output Verification:**

```bash
# DEBUG level (redact_level=INFO) - No redaction
DEBUG: user_data={'password': 'secret123', 'email': 'user@example.com'}

# INFO level (redact_level=INFO) - Redaction applied
INFO: user_data={'password': '[REDACTED]', 'email': '[REDACTED]'}
```

**Security Analysis:**

- ✅ **Fail-safe design**: Invalid levels default to applying redaction
- ✅ **Non-destructive**: Original data never modified, only log output redacted
- ✅ **Comprehensive coverage**: All sensitive data types protected at appropriate levels
- ✅ **Environment isolation**: Clear separation between dev/prod security postures

**Integration Testing:**

- ✅ **Multi-processor**: All redaction types work together with consistent level respect
- ✅ **Pipeline position**: Level checking occurs before redaction processing for efficiency
- ✅ **Configuration inheritance**: Settings properly propagate to all processors
- ✅ **Error handling**: Graceful degradation with invalid configuration

───────────────────────────────────  
Definition of Done  
✅ Redaction logic respects configured log level  
✅ Tests confirm enforcement at all log levels  
✅ PR merged to **main** with reviewer approval  
✅ `CHANGELOG.md` and README updated under _Unreleased → Added_

**Status: ✅ COMPLETE - Ready for Production**
