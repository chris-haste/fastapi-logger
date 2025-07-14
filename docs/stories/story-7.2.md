Story 7.2 – Redactor: Structured PII Auto-Detection  
───────────────────────────────────  
Epic: 7 – Data Redaction  
Sprint Target: Sprint #⟪next⟫  
Story Points: 8

**As a developer working with user data**  
I want the logger to automatically detect and redact common PII patterns  
So that I don’t need to manually enumerate every sensitive field.

───────────────────────────────────  
Acceptance Criteria

- A regex-based PII scanner is implemented as a post-processor
- Detects and redacts common sensitive values, including:  
  • Email addresses  
  • Credit card numbers (basic pattern, not Luhn)  
  • Phone numbers  
  • IPv4 addresses
- Patterns are configurable via settings (add/remove patterns, toggle feature)
- Redaction happens recursively across all string values in the event_dict
- Replacements use the same `REDACT_REPLACEMENT` setting as field redaction
- Unit tests confirm detection, replacement, and opt-out behavior
- README includes explanation, limitations, and opt-out

───────────────────────────────────  
Tasks / Technical Checklist

1. Implement `auto_redact_pii(event_dict)` processor

   - Recursive walk of all string values in the dict
   - Apply PII regex patterns to each string
   - Replace matches with the redaction placeholder

2. Add default regexes to `fapilog/_internal/pii_patterns.py` (or inline constants):

   - Email: `[\w\.-]+@[\w\.-]+\.\w+`
   - Phone: `(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}`
   - Credit card: `(?:\d[ -]*?){13,16}`
   - IPv4: `\b(?:\d{1,3}\.){3}\d{1,3}\b`

3. Add settings to `fapilog/settings.py`:

   - `ENABLE_AUTO_REDACT_PII: bool = True`
   - `CUSTOM_PII_PATTERNS: list[str] = []`
   - `REDACT_REPLACEMENT: str = "REDACTED"`

4. Insert PII processor after manual field redactor but before sink/render stage

5. Unit tests in `tests/test_auto_redactor.py`:

   - `test_email_redacted()`
   - `test_credit_card_redacted()`
   - `test_custom_pattern_addition()`
   - `test_opt_out_behavior()`

6. README updates:
   - “Automatic PII Redaction” section
   - List built-in patterns
   - Show how to disable or extend the feature
   - Note edge cases and known false positives

───────────────────────────────────  
Dependencies / Notes

- Regex-based, not NLP or semantic parsing
- Performance tradeoff acceptable for low-frequency log events (e.g., errors, audit)

───────────────────────────────────  
Definition of Done  
✓ PII redactor works out of the box and is configurable  
✓ Unit tests pass and demonstrate correctness  
✓ PR merged to **main** with reviewer approval  
✓ `CHANGELOG.md` and README updated under _Unreleased → Added_
