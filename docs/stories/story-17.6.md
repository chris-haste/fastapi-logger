# Story 17.6 – Remove Legacy Direct Sink Instance Support

**Epic:** 17 – Legacy Code Removal  
Sprint Target: Sprint #⟪next⟫  
Story Points: 2

## Status

Done

## Story

**As a developer maintaining clean configuration architecture**  
I want to remove support for direct sink instances in settings configuration  
So that only URI-based sink configuration is supported.

## Acceptance Criteria

1. **Settings Validation**: `LoggingSettings.parse_sinks()` only accepts string URIs
2. **Type Safety**: Remove `Union[str, Sink]` type support from sinks field
3. **Container Updates**: Update `LoggingContainer._setup_queue_worker()` to only handle string URIs
4. **Error Messages**: Clear error messages when direct sink instances are used
5. **Documentation Updated**: Remove references to direct sink instance patterns
6. **No Regressions**: All URI-based sink functionality works identically
7. **Test Updates**: Update any tests using direct sink instances

## Tasks / Subtasks

1. **[✅] Update Settings Validation**

   - [x] Modify `LoggingSettings.parse_sinks()` to reject `Sink` instances
   - [x] Update type annotation from `Union[str, Sink]` to `str`
   - [x] Add validation error for direct sink instances
   - [x] Update field description to reflect URI-only support

2. **[✅] Update Container Logic**

   - [x] Remove `isinstance(sink_item, Sink)` check in `_setup_queue_worker()`
   - [x] Clean up direct sink instance handling code
   - [x] Ensure all sink creation goes through URI factory patterns
   - [x] Verify error handling for invalid URIs

3. **[✅] Update Tests Using Direct Instances**

   - [x] Find tests that create `LoggingSettings(sinks=[SinkInstance()])`
   - [x] Convert to URI patterns: `LoggingSettings(sinks=["stdout"])`
   - [x] Update any bootstrap integration tests
   - [x] Verify all sink functionality tests pass

4. **[✅] Add Migration Error Handling**

   - [x] Clear error message when direct sink instance is used
   - [x] Guidance on converting to URI patterns
   - [x] Examples of URI equivalents for common sinks
   - [x] Helpful validation error messages

5. **[✅] Documentation and Examples Cleanup**
   - [x] Remove direct sink instance examples from docstrings
   - [x] Update module documentation to reflect URI-only patterns
   - [x] Clean up any remaining references to mixed sink types
   - [x] Verify examples use URI patterns consistently

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4 (Developer Agent)

### Debug Log References

- Type annotation update: `Union[List[Union[str, "Sink"]], str]` → `Union[List[str], str]` ✅ Complete
- Validation logic: Added proper error message for direct sink instances ✅ Working
- Container cleanup: Removed `isinstance(sink_item, Sink)` check ✅ Complete
- Test validation: Direct sink instance properly rejected with migration message ✅ Verified
- URI functionality: Container works correctly with URI-only configuration ✅ Confirmed

### Completion Notes

- **Type Safety Improved**: Removed mixed type support from settings field
- **Clear Migration Path**: Helpful error messages guide users to URI patterns
- **Container Simplified**: Removed direct instance handling code paths
- **Test Updates**: Updated tests to verify rejection behavior and URI patterns
- **No Regressions**: All URI-based sink functionality works identically

### File List

**Modified:**

- `src/fapilog/settings.py` - Updated type annotations and validation logic
- `src/fapilog/container.py` - Removed direct sink instance handling
- `tests/test_sink_registry.py` - Updated tests to verify new behavior
- `docs/stories/story-17.6.md` - Updated task completion and Dev Agent Record

### Change Log

| Date       | Version | Description                                    | Author      |
| ---------- | ------- | ---------------------------------------------- | ----------- |
| 2024-12-30 | 1.0     | Initial story creation for sink legacy cleanup | Quinn (QA)  |
| 2024-12-30 | 1.1     | Direct sink instance support removal complete  | James (Dev) |

## QA Results

### Review Date: 2024-12-30

### Reviewed By: Agent (Senior Developer QA)

### Code Quality Assessment

Excellent implementation of sink configuration simplification. The removal of mixed type support improves type safety while maintaining clear migration guidance. The URI-only approach is cleaner and more maintainable.

### Refactoring Performed

High-quality refactoring with improved type safety:

- **File**: `src/fapilog/settings.py`
  - **Change**: Updated type annotations from `Union[str, Sink]` to `str` only
  - **Why**: Simplifies configuration and improves type safety
  - **How**: Clear validation error with migration examples for direct instances
- **File**: `src/fapilog/container.py`
  - **Change**: Removed `isinstance(sink_item, Sink)` handling code
  - **Why**: Eliminates complexity and focuses on URI-based patterns
  - **How**: Streamlined sink creation through URI factory patterns only

### Compliance Check

- Coding Standards: ✓ Clean type annotations and validation patterns
- Project Structure: ✓ Container simplified with consistent URI handling
- Testing Strategy: ✓ Migration error handling properly tested
- All ACs Met: ✓ Type safety improved, container updated, clear errors, no regressions

### Improvements Checklist

- [x] Settings field type annotation cleaned (`Union[List[str], str]` only)
- [x] Container logic simplified (removed direct instance handling)
- [x] Migration error message provides clear URI conversion examples
- [x] Test validation confirms proper rejection of direct instances
- [x] All URI-based sink functionality verified working

### Security Review

No security concerns - simplified configuration reduces complexity and potential error vectors.

### Performance Considerations

Minor performance improvement through simplified validation and container logic.

### Final Status

✓ Approved - Ready for Done

Excellent architectural improvement. The URI-only approach is cleaner, more maintainable, and provides better type safety while maintaining clear migration guidance.
