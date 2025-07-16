Story 4.1 – Hostname & Process Info Enricher  
───────────────────────────────────  
Epic: 4 – Field Enrichers  
Sprint Target: Sprint #⟪next⟫  
Story Points: 3  
**Status: ✅ COMPLETED**

**As an infrastructure engineer**  
I want each log entry to include the hostname and process ID  
So that I can trace logs back to the container, host, or process that emitted them in distributed environments.

───────────────────────────────────  
Acceptance Criteria

- ✅ A new processor `host_process_enricher` is implemented in **`fapilog/enrichers.py`**
- ✅ It enriches every log event with:  
  • `hostname`: system hostname (via `socket.gethostname()`)  
  • `pid`: process ID (via `os.getpid()`)
- ✅ These fields are added to the log event **unless already present**
- ✅ The enricher is inserted early in the processor chain (before redaction, rendering)
- ✅ Processor has zero external dependencies and negligible performance cost (values cached)
- ✅ Unit tests verify:  
  • `hostname` and `pid` are present in logs  
  • Values match `socket.gethostname()` and `os.getpid()`  
  • Fields can be overridden manually in the log call

───────────────────────────────────  
Tasks / Technical Checklist

1. ✅ Implement `host_process_enricher(logger, method_name, event_dict)` in `fapilog/enrichers.py`

   - ✅ Use `functools.lru_cache()` or module-level constants to cache values

2. ✅ Add the enricher to the processor chain (in `pipeline.py`), before any rendering

3. ✅ Unit tests in `tests/test_enricher_host_process.py`:

   - ✅ `test_hostname_pid_present()`
   - ✅ `test_fields_can_be_overridden()`
   - ✅ `test_only_missing_fields_added()`
   - ✅ `test_cached_values()`
   - ✅ `test_with_mock_system_calls()`
   - ✅ `test_empty_event_dict()`
   - ✅ `test_logger_and_method_parameters()`
   - ✅ `test_none_values_handling()`
   - ✅ `test_non_string_hostname()`

4. ✅ Update README "Log Fields" section to document `hostname` and `pid`

───────────────────────────────────  
Dependencies / Notes

- ✅ No dependencies beyond stdlib (`socket`, `os`)
- ✅ Positioned before user-overridable fields to preserve intentional values

───────────────────────────────────  
Definition of Done  
✅ Enricher implemented, inserted, and tested  
✅ Logs include hostname and process ID  
✅ PR merged to **main** with reviewer approval and green CI  
✅ `CHANGELOG.md` and README updated under _Unreleased → Added_

───────────────────────────────────  
**QA Review Findings**

**Implementation Status: ✅ COMPLETE**

The story has been fully implemented and is working correctly:

1. **✅ Enricher Implementation**: The `host_process_enricher` is implemented in `src/fapilog/enrichers.py` with:

   - Cached hostname retrieval using `socket.gethostname()` with `@lru_cache`
   - Cached process ID retrieval using `os.getpid()` with `@lru_cache`
   - Proper field override logic (only adds if not present)
   - Zero external dependencies beyond standard library

2. **✅ Pipeline Integration**: The enricher is properly integrated into the processor chain in `src/fapilog/pipeline.py` at position 6 (early in the chain, before redaction and rendering)

3. **✅ Comprehensive Testing**: All 9 unit tests in `tests/test_enricher_host_process.py` are passing:

   - `test_hostname_pid_present()` - verifies fields are added
   - `test_fields_can_be_overridden()` - verifies manual override works
   - `test_only_missing_fields_added()` - verifies selective field addition
   - `test_cached_values()` - verifies performance caching
   - `test_with_mock_system_calls()` - verifies system call behavior
   - `test_empty_event_dict()` - verifies edge case handling
   - `test_logger_and_method_parameters()` - verifies API compatibility
   - `test_none_values_handling()` - verifies None value replacement
   - `test_non_string_hostname()` - verifies type handling

4. **✅ Documentation**:

   - README "Log Fields" section documents `hostname` and `pid` fields
   - CHANGELOG.md includes comprehensive documentation under "Added" section

5. **✅ Integration Test**: Verified the enricher works in practice by running a test log call that shows both `hostname` and `pid` fields are correctly added to log output.

**Performance & Quality Assessment:**

- **Performance**: Uses `@lru_cache` for both hostname and PID retrieval, ensuring negligible overhead
- **Reliability**: Comprehensive test coverage with edge case handling
- **Compatibility**: Works seamlessly with existing logging pipeline
- **Documentation**: Fully documented in both README and CHANGELOG

**Acceptance Criteria - ALL MET:**

- ✅ New processor `host_process_enricher` implemented in `fapilog/enrichers.py`
- ✅ Enriches every log event with `hostname` and `pid` fields
- ✅ Fields added unless already present (allows manual override)
- ✅ Enricher positioned early in processor chain (before redaction, rendering)
- ✅ Zero external dependencies and negligible performance cost (values cached)
- ✅ Unit tests verify field presence, system call matching, and manual override capability
- ✅ README "Log Fields" section updated with `hostname` and `pid` documentation

The implementation follows FastAPI and Pydantic V2 best practices with robust error handling and proper separation of concerns. The enricher is production-ready and provides the infrastructure visibility needed for distributed environments.
