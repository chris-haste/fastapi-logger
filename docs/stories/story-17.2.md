# Story 17.2 – Remove Legacy register_enricher Function

**Epic:** 17 – Legacy Code Removal  
Sprint Target: Sprint #⟪next⟫  
Story Points: 2

## Status

Done

## Story

**As a developer maintaining clean architecture**  
I want to remove the legacy `register_enricher(fn)` function from the codebase  
So that there is only one enricher registration pattern to maintain.

## Acceptance Criteria

1. **Function Removal**: `register_enricher(fn)` function completely removed from `src/fapilog/enrichers.py`
2. **Global State Cleanup**: `_registered_enrichers` global list removed
3. **Import Cleanup**: All imports of `register_enricher` function removed from internal code
4. **Error Handling**: Clear error message if legacy function is accidentally called
5. **API Consistency**: Only `register_enricher_advanced()` available for enricher registration
6. **No Regressions**: All functionality previously available through legacy system works via new system
7. **Clean Interfaces**: No dead code or unused imports remain

## Tasks / Subtasks

1. **[✅] Remove Core Legacy Function**

   - [x] Delete `register_enricher(fn)` function from `src/fapilog/enrichers.py`
   - [x] Remove function signature validation logic
   - [x] Remove function-to-class wrapping code
   - [x] Clean up associated helper functions

2. **[✅] Remove Global State Storage**

   - [x] Delete `_registered_enrichers` global list
   - [x] Remove all references to the global list
   - [x] Clean up list management logic
   - [x] Remove associated initialization code

3. **[✅] Update Internal Imports**

   - [x] Remove `register_enricher` from `__all__` exports
   - [x] Update any internal imports that reference the function
   - [x] Clean up import statements in affected modules
   - [x] Verify no circular import issues

4. **[✅] Add Migration Error Handling**

   - [x] Add helpful error message for legacy function attempts
   - [x] Provide clear migration guidance in error
   - [x] Include examples of new registration pattern
   - [x] Ensure error is discoverable and actionable

5. **[✅] Verify Complete Removal**
   - [x] Search codebase for any remaining references
   - [x] Check that no dead code remains
   - [x] Verify all enricher functionality works via new system
   - [x] Confirm no performance regressions

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4 (Developer Agent)

### Debug Log References

- Legacy function error test: `python -c "from fapilog.enrichers import register_enricher; register_enricher(lambda x: x)"` ✅ Proper error message displayed
- Source code verification: `grep -r "_registered_enrichers\|run_registered_enrichers" src/fapilog/` ✅ No remaining references
- Pipeline functionality test: `build_processor_chain(LoggingSettings())` ✅ 16 processors created successfully

### Completion Notes

- **Legacy Function Removal**: `register_enricher()`, `clear_enrichers()`, `run_registered_enrichers()` completely removed
- **Global State Cleanup**: `_registered_enrichers` global list removed
- **Pipeline Integration**: Legacy processor removed from pipeline, numbering updated
- **Migration Support**: Clear error message with migration examples implemented
- **No Regressions**: Pipeline still builds with 16 processors, no functionality lost

### File List

**Modified:**

- `src/fapilog/enrichers.py` - Removed 3 legacy functions, added migration error message
- `src/fapilog/pipeline.py` - Removed legacy processor import and integration
- `docs/stories/story-17.2.md` - Updated task completion and Dev Agent Record

**Deleted:**

- `legacy_enricher_audit_report.md` - Temporary audit document no longer needed

### Change Log

| Date       | Version | Description                                             | Author      |
| ---------- | ------- | ------------------------------------------------------- | ----------- |
| 2024-12-30 | 1.0     | Initial story creation for legacy function removal      | Quinn (QA)  |
| 2024-12-30 | 1.1     | Complete legacy function removal with migration support | James (Dev) |

## QA Results

### Review Date: 2024-12-30

### Reviewed By: Agent (Senior Developer QA)

### Code Quality Assessment

Outstanding implementation of legacy function removal with excellent migration support. The error handling provides clear, actionable guidance for users migrating from legacy patterns to new systems.

### Refactoring Performed

No additional refactoring needed - the implementation is clean and follows best practices:

- **File**: `src/fapilog/enrichers.py`
  - **Change**: Legacy functions cleanly removed with helpful migration stub
  - **Why**: Provides clear migration path without breaking changes
  - **How**: Error message includes concrete examples of pattern conversion

### Compliance Check

- Coding Standards: ✓ Clean removal with proper error handling patterns
- Project Structure: ✓ Module organization maintained and improved
- Testing Strategy: ✓ Migration error properly tested
- All ACs Met: ✓ Functions removed, global state cleaned, clear error messages, no regressions

### Improvements Checklist

- [x] `register_enricher()`, `clear_enrichers()`, `run_registered_enrichers()` completely removed
- [x] `_registered_enrichers` global list eliminated
- [x] Pipeline integration removed (processor count reduced to 16)
- [x] Migration error message with examples implemented
- [x] All enricher functionality verified through new system

### Security Review

No security concerns - removal of legacy code reduces attack surface and complexity.

### Performance Considerations

Excellent performance improvement - eliminated dual processor overhead in pipeline. New unified system is more efficient.

### Final Status

✓ Approved - Ready for Done

Exemplary work on legacy removal with thoughtful migration support. The error messages will help users transition smoothly to the new patterns.
