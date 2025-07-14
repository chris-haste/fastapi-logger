Story 8.3 – Loki Sink: Stream Label Customization  
───────────────────────────────────  
Epic: 8 – Loki Integration  
Sprint Target: Sprint #⟪next⟫  
Story Points: 5

**As a developer integrating with Loki**  
I want to customize which fields are used as Loki stream labels  
So that I can organize and filter logs effectively in Grafana.

───────────────────────────────────  
Acceptance Criteria

- The Loki sink supports dynamic stream labels based on configuration
- Default labels include `app`, `env`, and `level`, but can be overridden
- Label values are extracted from each log event (if available)
- Labels must be valid per Loki’s rules (no spaces, lowercase keys, string values)
- Missing label values fallback to `"unknown"` or a configured default
- Configuration supports both static values and dynamic fields from the event
- Unit tests verify label generation and fallback behavior
- README includes label config examples and Grafana usage tips

───────────────────────────────────  
Tasks / Technical Checklist

1. Add setting to `fapilog/settings.py`:

   - `LOKI_STREAM_LABELS: dict[str, str] = {"app": "fapilog", "env": "default", "level": "level"}`
   - Values can be either literal values or event_dict keys

2. Modify `LokiSink` to resolve labels per event:

   - For each key, check if value is a key in `event_dict`; use that value
   - Otherwise, treat as static

3. Sanitize labels to match Loki schema:

   - Lowercase keys
   - Replace invalid characters
   - Convert values to strings

4. Fallback to `"unknown"` if no value is found or empty

5. Unit tests in `tests/sinks/test_loki_labels.py`:

   - `test_static_label_value()`
   - `test_dynamic_label_resolution()`
   - `test_missing_label_fallback()`
   - `test_label_sanitization()`

6. README updates:
   - Add “Custom Stream Labels” section
   - Show examples using `request_id`, `camera_id`, or `service` as dynamic labels
   - Include note on label explosion and Loki best practices

───────────────────────────────────  
Dependencies / Notes

- Label customization is a key differentiator for log aggregation at scale
- Loki charges per cardinality, so conservative defaults are recommended

───────────────────────────────────  
Definition of Done  
✓ Label customization is supported and validated  
✓ Tests confirm default, dynamic, and fallback behavior  
✓ PR merged to **main** with reviewer approval  
✓ `CHANGELOG.md` and README updated under _Unreleased → Added_
