Story 7.2 – Redactor: Structured PII Auto-Detection  
───────────────────────────────────  
Epic: 7 – Data Redaction  
Sprint Target: Sprint #⟪next⟫  
Story Points: 8

**As a developer working with user data**  
I want the logger to automatically detect and redact common PII patterns  
So that I don't need to manually enumerate every sensitive field.

───────────────────────────────────  
Acceptance Criteria

- ✅ A regex-based PII scanner is implemented as a post-processor
- ✅ Detects and redacts common sensitive values, including:  
  • Email addresses  
  • Credit card numbers (basic pattern, not Luhn)  
  • Phone numbers  
  • IPv4 addresses
- ✅ Patterns are configurable via settings (add/remove patterns, toggle feature)
- ✅ Redaction happens recursively across all string values in the event_dict
- ✅ Replacements use the same `REDACT_REPLACEMENT` setting as field redaction
- ✅ Unit tests confirm detection, replacement, and opt-out behavior
- ✅ README includes explanation, limitations, and opt-out

───────────────────────────────────  
Tasks / Technical Checklist

1. ✅ Implement `auto_redact_pii(event_dict)` processor

   - ✅ Recursive walk of all string values in the dict
   - ✅ Apply PII regex patterns to each string
   - ✅ Replace matches with the redaction placeholder

2. ✅ Add default regexes to `fapilog/_internal/pii_patterns.py` (or inline constants):

   - ✅ Email: `[\w\.-]+@[\w\.-]+\.\w+`
   - ✅ Phone: `(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}`
   - ✅ Credit card: `\b\d{4}(?:[ -]?\d{4}){3}\b` (improved 16-digit pattern)
   - ✅ IPv4: `\b(?:\d{1,3}\.){3}\d{1,3}\b`

3. ✅ Add settings to `fapilog/settings.py`:

   - ✅ `ENABLE_AUTO_REDACT_PII: bool = True`
   - ✅ `CUSTOM_PII_PATTERNS: list[str] = []`
   - ✅ `REDACT_REPLACEMENT: str = "REDACTED"`

4. ✅ Insert PII processor after manual field redactor but before sink/render stage

5. ✅ Unit tests in `tests/test_auto_redactor.py`:

   - ✅ `test_email_redacted()`
   - ✅ `test_credit_card_redacted()`
   - ✅ `test_custom_pattern_addition()`
   - ✅ `test_opt_out_behavior()`
   - ✅ Plus 17 additional comprehensive tests

6. ✅ README updates:
   - ✅ "Automatic PII Redaction" section
   - ✅ List built-in patterns
   - ✅ Show how to disable or extend the feature
   - ✅ Note edge cases and known false positives

───────────────────────────────────  
Dependencies / Notes

- ✅ Regex-based, not NLP or semantic parsing
- ✅ Performance tradeoff acceptable for low-frequency log events (e.g., errors, audit)

───────────────────────────────────  
Review Findings

**Implementation Status: ✅ COMPLETE**

**Core Implementation:**

- **File**: `src/fapilog/_internal/pii_patterns.py` (124 lines)
- **Key Functions**:
  - `auto_redact_pii_processor()` - Creates structlog processor
  - `_redact_pii_recursive()` - Recursive PII scanning
  - `_redact_string_value()` - String-level redaction with non-overlapping matches
  - `_compile_pii_patterns()` - Pattern compilation with error handling

**Pipeline Integration:**

- **File**: `src/fapilog/pipeline.py` (lines 108-113)
- **Position**: After manual field redactor, before sink/render stage
- **Conditional**: Only enabled when `settings.enable_auto_redact_pii=True`

**Settings Configuration:**

- **File**: `src/fapilog/settings.py` (lines 75-85)
- **Environment Variables**: `FAPILOG_ENABLE_AUTO_REDACT_PII`, `FAPILOG_CUSTOM_PII_PATTERNS`, `FAPILOG_REDACT_REPLACEMENT`

**Test Coverage:**

- **21 comprehensive tests** in `tests/test_auto_redactor.py`
- **100% coverage** for the PII patterns module
- Tests cover: pattern compilation, string redaction, recursive structures, processor behavior, integration scenarios
- All tests pass ✅

**Documentation:**

- **Complete README section** (lines 1461-1520) explaining feature, configuration, limitations
- **Comprehensive example** in `examples/20_automatic_pii_redaction.py`
- **User guide reference** in `docs/user-guide.md`

**Verification:**

```python
# Test verification - working correctly
processor = auto_redact_pii_processor(DEFAULT_PII_PATTERNS)
event_dict = {'email': 'user@example.com', 'phone': '555-123-4567'}
result = processor(mock_logger, 'info', event_dict)
# Result: {'email': 'REDACTED', 'phone': 'REDACTED'} ✅
```

**Additional Features Beyond Requirements:**

- ✅ Custom pattern support via `custom_pii_patterns` setting
- ✅ Environment variable configuration
- ✅ Comprehensive error handling for invalid regex patterns
- ✅ Non-overlapping match replacement to prevent double-redaction
- ✅ Recursive scanning of nested dictionaries and lists
- ✅ Preservation of non-string values (int, float, bool, None)

───────────────────────────────────  
Definition of Done  
✅ PII redactor works out of the box and is configurable  
✅ Unit tests pass and demonstrate correctness  
✅ PR merged to **main** with reviewer approval  
✅ `CHANGELOG.md` and README updated under _Unreleased → Added_

**Status: ✅ COMPLETE - Ready for Production**
