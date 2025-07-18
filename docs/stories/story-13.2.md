# Story 13.2 – Refactor Large Functions into Smaller, Focused Functions

**Epic:** 13 – Architecture Improvements  
Sprint Target: Sprint #⟪next⟫  
Story Points: 8

**As a library maintainer**  
I want to break down large, complex functions into smaller, focused functions  
So that the code is more maintainable, testable, and follows single responsibility principle.

───────────────────────────────────  
Acceptance Criteria

- `configure_logging()` in `bootstrap.py` (224 lines) is broken into focused functions
- `dispatch()` in `middleware.py` (229 lines) is refactored into smaller functions
- `_run()` in `_internal/queue.py` is simplified and broken into focused methods
- Each function has a single, clear responsibility
- All functions are easily testable in isolation
- Code complexity is reduced (cyclomatic complexity < 10 per function)
- Function names clearly describe their purpose
- Error handling is consistent across all functions
- Performance is maintained or improved
- All existing functionality is preserved

───────────────────────────────────  
Tasks / Technical Checklist

1. **Refactor `bootstrap.py:configure_logging()`**:

   - Extract `_validate_and_apply_settings()` for settings validation
   - Extract `_setup_structlog_configuration()` for structlog setup
   - Extract `_register_middleware_and_handlers()` for FastAPI integration
   - Extract `_configure_httpx_trace_propagation()` for httpx setup
   - Main function becomes orchestrator of smaller functions

2. **Refactor `middleware.py:dispatch()`**:

   - Extract `_extract_request_metadata()` for request parsing
   - Extract `_setup_context_variables()` for context binding
   - Extract `_process_response()` for response handling
   - Extract `_add_correlation_headers()` for header management
   - Extract `_handle_exceptions()` for error handling

3. **Refactor `_internal/queue.py:_run()`**:

   - Extract `_collect_batch()` for batch collection logic
   - Extract `_process_batch()` for batch processing
   - Extract `_handle_worker_shutdown()` for graceful shutdown
   - Extract `_drain_remaining_events()` for queue draining

4. **Refactor `redactors.py`**:

   - Remove duplicate `_redact_nested_fields` functions
   - Consolidate redaction logic into single, well-tested function
   - Extract `_compile_redaction_patterns()` for pattern compilation
   - Extract `_apply_redaction_to_field()` for field-level redaction

5. **Add comprehensive unit tests**:

   - Test each extracted function in isolation
   - Verify function contracts and error handling
   - Test edge cases and error conditions
   - Ensure performance characteristics are maintained

6. **Update documentation**:
   - Document the new function structure
   - Add examples of function usage
   - Update architecture documentation

───────────────────────────────────  
Dependencies / Notes

- This refactoring should maintain exact same behavior
- Performance should not degrade
- All existing tests should continue to pass
- New tests should be added for extracted functions
- Function signatures should be designed for easy testing

───────────────────────────────────  
Definition of Done  
✓ All large functions broken into focused, smaller functions  
✓ Each function has single responsibility  
✓ All functions are easily testable  
✓ Code complexity reduced (cyclomatic complexity < 10)  
✓ All existing tests pass  
✓ New unit tests added for extracted functions  
✓ Performance maintained or improved  
✓ Documentation updated with new function structure  
✓ PR merged to **main** with reviewer approval and green CI  
✓ `CHANGELOG.md` updated under _Unreleased → Changed_

───────────────────────────────────  
**CURRENT STATUS: COMPLETED**

**Completed Tasks:**

- ✅ `configure_logging()` (224 lines) → Split into 6 focused functions:
  - `_validate_and_get_settings()`
  - `_apply_deprecated_overrides()`
  - `_determine_console_format()`
  - `_configure_standard_logging()`
  - `_configure_structlog()`
  - `_register_middleware_and_handlers()`
- ✅ `dispatch()` (229 lines) → Split into 7 focused methods:
  - `_extract_request_metadata()`
  - `_generate_trace_ids()`
  - `_set_request_context()`
  - `_calculate_response_size()`
  - `_add_correlation_headers()`
  - `_log_request_success()`
  - `_log_request_error()`
- ✅ Removed duplicate `_redact_nested_fields` functions in `redactors.py`
- ✅ Each function has single responsibility
- ✅ All functions are easily testable
- ✅ Code complexity reduced
- ✅ All existing functionality preserved
- ✅ All tests pass
