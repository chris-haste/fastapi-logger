# Story 13.4 – Simplify Configuration API and Remove Deprecated Patterns

**Epic:** 13 – Architecture Improvements  
Sprint Target: Sprint #⟪next⟫  
Story Points: 3

**As a library maintainer**  
I want to simplify the configuration API by removing deprecated keyword arguments  
So that the API is cleaner, more consistent, and easier to understand.

───────────────────────────────────  
Acceptance Criteria

- ✅ Deprecated keyword arguments in `configure_logging()` are removed
- ✅ Configuration is standardized on `LoggingSettings` object
- ✅ Configuration examples are updated to use new patterns
- ✅ All existing functionality is preserved through `LoggingSettings`
- ✅ Configuration validation is improved
- ✅ Documentation clearly explains the new configuration approach

───────────────────────────────────  
Tasks / Technical Checklist

1. **✅ Update `configure_logging()` signature**:

   - ✅ Remove deprecated parameters: `level`, `sinks`, `json_console`
   - ✅ Keep only `settings` and `app` parameters
   - ✅ Update function signature and docstring

2. **✅ Update `LoggingContainer.configure()` method**:

   - ✅ Remove deprecated parameter handling
   - ✅ Simplify configuration logic to use only `LoggingSettings`
   - ✅ Remove parameter override logic

3. **✅ Update all tests**:

   - ✅ Remove tests for deprecated parameters
   - ✅ Add tests for new configuration patterns
   - ✅ Update existing tests to use `LoggingSettings`

4. **✅ Update examples directory**:
   - ✅ Verify all example files use new configuration
   - ✅ Examples already properly configured with `LoggingSettings`

───────────────────────────────────  
Dependencies / Notes

- Breaking change implemented without backward compatibility concerns
- All functionality available through LoggingSettings
- API is now cleaner and more consistent

───────────────────────────────────  
Definition of Done  
✅ Deprecated parameters removed from configure*logging()  
✅ Configuration standardized on LoggingSettings  
✅ All examples updated to new patterns  
✅ All tests updated and passing  
✅ Function signatures simplified  
✅ API is cleaner and more consistent  
✅ PR merged to **main** with reviewer approval and green CI  
✅ `CHANGELOG.md` updated under \_Unreleased → Changed*

───────────────────────────────────  
**CURRENT STATUS: COMPLETED**

**Completed Tasks:**

- ✅ Removed deprecated parameters (`level`, `sinks`, `json_console`) from `configure_logging()` function signature
- ✅ Updated function to only accept `settings` and `app` parameters
- ✅ Simplified `LoggingContainer.configure()` method to use only `LoggingSettings`
- ✅ Removed all deprecated parameter handling and override logic
- ✅ Updated all test files to use `LoggingSettings` instead of deprecated parameters
- ✅ Verified all examples are already using the correct API patterns
- ✅ Updated function docstrings to reflect simplified API
- ✅ Configuration is now fully standardized on `LoggingSettings` object

**Implementation Summary:**

The configuration API has been successfully simplified with a breaking change that removes all deprecated keyword arguments. The API is now cleaner, more consistent, and easier to understand:

**Before:**

```python
configure_logging(level="DEBUG", json_console="json", sinks={"stdout": {}})
```

**After:**

```python
settings = LoggingSettings(level="DEBUG", json_console="json")
configure_logging(settings=settings)
```

All functionality is preserved through the `LoggingSettings` object, and the API surface is significantly reduced and more maintainable.
