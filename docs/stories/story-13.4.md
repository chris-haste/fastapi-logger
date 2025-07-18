# Story 13.4 – Simplify Configuration API and Remove Deprecated Patterns

**Epic:** 13 – Architecture Improvements  
Sprint Target: Sprint #⟪next⟫  
Story Points: 3

**As a library maintainer**  
I want to simplify the configuration API by removing deprecated keyword arguments  
So that the API is cleaner, more consistent, and easier to understand.

───────────────────────────────────  
Acceptance Criteria

- Deprecated keyword arguments in `configure_logging()` are removed
- Configuration is standardized on `LoggingSettings` object
- Clear migration path for existing users
- Deprecation warnings are replaced with proper errors
- Configuration examples are updated to use new patterns
- All existing functionality is preserved through `LoggingSettings`
- Configuration validation is improved
- Documentation clearly explains the new configuration approach

───────────────────────────────────  
Tasks / Technical Checklist

1. **Update `configure_logging()` signature**:

   - Remove deprecated parameters: `level`, `sinks`, `json_console`
   - Keep only `settings` and `app` parameters
   - Add proper deprecation warnings for removed parameters
   - Update function signature and docstring

2. **Enhance `LoggingSettings` class**:

   - Ensure all deprecated parameters are available in settings
   - Add validation for all configuration options
   - Improve error messages for invalid configurations
   - Add convenience methods for common configurations

3. **Update `bootstrap.py`**:

   - Remove deprecated parameter handling
   - Simplify configuration logic
   - Improve error messages for invalid configurations
   - Add examples of proper configuration usage

4. **Update all examples and documentation**:

   - Replace deprecated keyword argument examples
   - Add migration guide for existing users
   - Update README with new configuration patterns
   - Update API documentation

5. **Add migration utilities**:

   - Create `migrate_configuration()` helper function
   - Add deprecation warnings with helpful messages
   - Provide clear migration path for users

6. **Update tests**:

   - Remove tests for deprecated parameters
   - Add tests for new configuration patterns
   - Test migration utilities
   - Verify backward compatibility through settings

7. **Update examples directory**:
   - Update all example files to use new configuration
   - Add migration examples
   - Ensure all examples work with new API

───────────────────────────────────  
Dependencies / Notes

- This is a breaking change for users of deprecated parameters
- Should provide clear migration path
- Deprecation warnings should guide users to new API
- All functionality should be available through LoggingSettings

───────────────────────────────────  
Definition of Done  
✓ Deprecated parameters removed from configure*logging()  
✓ Configuration standardized on LoggingSettings  
✓ Clear migration path provided  
✓ All examples updated to new patterns  
✓ Documentation updated with new API  
✓ Migration utilities implemented  
✓ All tests updated and passing  
✓ Deprecation warnings replaced with proper errors  
✓ PR merged to **main** with reviewer approval and green CI  
✓ `CHANGELOG.md` updated under \_Unreleased → Changed*

───────────────────────────────────  
**CURRENT STATUS: PARTIALLY COMPLETED**

**Completed Tasks:**

- ✅ Added deprecation warnings for keyword arguments in `configure_logging()`
- ✅ Maintained backward compatibility through `LoggingSettings`
- ✅ Added `_apply_deprecated_overrides()` function to handle deprecated parameters

**Remaining Tasks:**

- ❌ Remove deprecated parameters entirely from function signature
- ❌ Standardize configuration on `LoggingSettings` only
- ❌ Update all examples and documentation
- ❌ Add migration utilities
- ❌ Update tests to remove deprecated parameter tests
- ❌ Replace deprecation warnings with proper errors
