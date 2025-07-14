Story 4.1 – Hostname & Process Info Enricher  
───────────────────────────────────  
Epic: 4 – Field Enrichers  
Sprint Target: Sprint #⟪next⟫  
Story Points: 3

**As an infrastructure engineer**  
I want each log entry to include the hostname and process ID  
So that I can trace logs back to the container, host, or process that emitted them in distributed environments.

───────────────────────────────────  
Acceptance Criteria

- A new processor `host_process_enricher` is implemented in **`fapilog/enrichers.py`**
- It enriches every log event with:  
  • `hostname`: system hostname (via `socket.gethostname()`)  
  • `pid`: process ID (via `os.getpid()`)
- These fields are added to the log event **unless already present**
- The enricher is inserted early in the processor chain (before redaction, rendering)
- Processor has zero external dependencies and negligible performance cost (values cached)
- Unit tests verify:  
  • `hostname` and `pid` are present in logs  
  • Values match `socket.gethostname()` and `os.getpid()`  
  • Fields can be overridden manually in the log call

───────────────────────────────────  
Tasks / Technical Checklist

1. Implement `host_process_enricher(logger, method_name, event_dict)` in `fapilog/enrichers.py`

   - Use `functools.lru_cache()` or module-level constants to cache values

2. Add the enricher to the processor chain (in `pipeline.py`), before any rendering

3. Unit tests in `tests/test_enricher_host_process.py`:

   - `test_hostname_pid_present()`
   - `test_fields_can_be_overridden()`

4. Update README “Log Fields” section to document `hostname` and `pid`

───────────────────────────────────  
Dependencies / Notes

- No dependencies beyond stdlib (`socket`, `os`)
- Positioned before user-overridable fields to preserve intentional values

───────────────────────────────────  
Definition of Done  
✓ Enricher implemented, inserted, and tested  
✓ Logs include hostname and process ID  
✓ PR merged to **main** with reviewer approval and green CI  
✓ `CHANGELOG.md` and README updated under _Unreleased → Added_
