Story 5.4 – Multi-Sink Fan-out Support  
───────────────────────────────────  
Epic: 5 – Sink Implementations  
Sprint Target: Sprint #⟪next⟫  
Story Points: 5

**As a library user**  
I want to configure multiple sinks simultaneously  
So that logs are written to several destinations (e.g., stdout and Loki) in parallel.

───────────────────────────────────  
Acceptance Criteria

- The `FAPILOG_SINKS` environment variable supports a comma-separated list of sink URIs  
  • Example: `FAPILOG_SINKS=stdout://,loki://loki:3100`
- Each URI is parsed and mapped to the appropriate sink implementation
- All configured sinks receive the same log event
- Logging failures in one sink do not block the others
- Internal sink runner uses `asyncio.gather(*sinks, return_exceptions=True)`
- Unit tests verify:  
  • All sinks receive log events  
  • One sink’s failure does not block others  
  • Misconfigured sink raises during startup, not at runtime
- README updated to show multiple sink usage

───────────────────────────────────  
Tasks / Technical Checklist

1. Update `configure_logging()` to support parsing multiple URIs from `FAPILOG_SINKS`

   - Split by comma
   - Instantiate each sink via factory/loader
   - Store in a list of sink instances

2. In `QueueWorker`, update `emit()` logic:

   - Run all sink `.write()` methods concurrently with `asyncio.gather(..., return_exceptions=True)`
   - Log any exception using a fallback logger (`log.warning(...)`)

3. Add unit tests in `tests/test_multi_sink.py`:

   - `test_both_sinks_receive_logs()`
   - `test_one_sink_fails_others_continue()`
   - `test_invalid_sink_uri_raises_on_config()`

4. Update README:
   - Add “Multiple Sink Support” section
   - Show usage with stdout + file, or stdout + loki
   - Recommend order of sinks (e.g., stdout first for local debugging)

───────────────────────────────────  
Dependencies / Notes

- Assumes that sink loader can already resolve sink types from URIs
- Failure isolation ensures production robustness in multi-destination setups

───────────────────────────────────  
Definition of Done  
✓ Multiple sinks supported concurrently  
✓ Logging continues even if one sink fails  
✓ Unit tests confirm behavior  
✓ PR merged to **main** with reviewer approval  
✓ `CHANGELOG.md` and README updated under _Unreleased → Added_
