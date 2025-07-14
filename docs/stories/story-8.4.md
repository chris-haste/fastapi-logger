Story 8.4 – Loki Sink: Structured JSON Log Output  
───────────────────────────────────  
Epic: 8 – Loki Integration  
Sprint Target: Sprint #⟪next⟫  
Story Points: 3

**As a developer using Loki with Grafana**  
I want structured JSON logs to be pushed to Loki  
So that fields like `level`, `event`, and `context` are queryable and filterable in Grafana.

───────────────────────────────────  
Acceptance Criteria

- Log lines sent to Loki are formatted as compact JSON strings
- The entire `event_dict` is serialized using `json.dumps()`
- Timestamp and stream label formatting remain per Loki requirements
- The Loki line format must contain only one JSON object per log line
- Logs appear as structured JSON in Grafana's Explore tab
- Unit tests verify that event_dict is serialized accurately
- README includes an example of structured log output and Grafana filter usage

───────────────────────────────────  
Tasks / Technical Checklist

1. Update `LokiSink` to format log lines using `json.dumps(event_dict)`

   - Ensure encoding preserves non-ASCII and handles datetime correctly
   - Set `separators=(",", ":")` for compact encoding

2. Confirm each Loki line entry is in format:

   - Stream wrapper:
     ```json
     {
       "streams": [
         {
           "stream": { "app": "fapilog", "env": "prod", "level": "info" },
           "values": [["<ts>", "{\"event\":\"user_login\",\"level\":\"info\"}"]]
         }
       ]
     }
     ```

3. Add unit tests in `tests/sinks/test_loki_json_output.py`:

   - `test_json_log_line_format()`
   - `test_special_characters_in_log()`
   - `test_nested_dict_serialization()`

4. README updates:
   - Add section “Structured JSON Output” under Loki
   - Provide example of a Loki stream payload
   - Include Grafana query example: `{app="fapilog"} |= "event"`

───────────────────────────────────  
Dependencies / Notes

- Avoid double serialization (e.g., don’t JSON-encode the whole stream payload more than once)
- Consider logging encoding errors or invalid objects (future enhancement)

───────────────────────────────────  
Definition of Done  
✓ Loki lines contain JSON-formatted log content  
✓ Compatible with Grafana’s JSON log viewer  
✓ Unit tests verify structure and edge cases  
✓ PR merged to **main** with reviewer approval  
✓ `CHANGELOG.md` and README updated under _Unreleased → Added_
