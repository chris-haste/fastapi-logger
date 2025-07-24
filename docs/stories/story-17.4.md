# Story 17.4 – Final Cleanup of Legacy Enricher State and References

**Epic:** 17 – Legacy Code Removal  
Sprint Target: Sprint #⟪next⟫  
Story Points: 2

## Status
Draft

## Story

**As a developer ensuring clean codebase architecture**  
I want to remove all remaining legacy enricher state and references  
So that the codebase has no trace of the old enricher system.

## Acceptance Criteria

1. **State Cleanup**: All legacy global variables and state removed
2. **Import Cleanup**: All legacy enricher imports cleaned up across codebase
3. **Function Cleanup**: Legacy utility functions like `clear_enrichers()` removed
4. **Documentation Cleanup**: Legacy function references removed from docstrings
5. **Export Cleanup**: Legacy functions removed from `__all__` exports
6. **Search Verification**: No remaining references to legacy enricher system
7. **API Consistency**: Clean, unified enricher API with no legacy artifacts

## Tasks / Subtasks

1. **[⏸] Remove Legacy Utility Functions**
   - [ ] Remove `clear_enrichers()` function from `src/fapilog/enrichers.py`
   - [ ] Clean up any other legacy helper functions
   - [ ] Remove legacy function documentation
   - [ ] Update module docstrings

2. **[⏸] Clean Up Exports and Imports**
   - [ ] Remove legacy functions from `__all__` in `src/fapilog/enrichers.py`
   - [ ] Update `src/fapilog/__init__.py` exports if needed
   - [ ] Clean up any remaining internal imports
   - [ ] Verify external API surface is clean

3. **[⏸] Remove Legacy Documentation References**
   - [ ] Update module docstrings to remove legacy references
   - [ ] Clean up function docstrings mentioning legacy patterns
   - [ ] Remove legacy examples from code comments
   - [ ] Update inline documentation

4. **[⏸] Final Codebase Search and Cleanup**
   - [ ] Search for any remaining `register_enricher` references
   - [ ] Search for `_registered_enrichers` usage
   - [ ] Search for `run_registered_enrichers` mentions
   - [ ] Remove any orphaned legacy code

5. **[⏸] Verify API Cleanliness**
   - [ ] Test that only new enricher system is accessible
   - [ ] Verify clean import paths and exports
   - [ ] Check that error messages are consistent
   - [ ] Confirm no legacy artifacts in public API

## Dev Notes

### Cleanup Targets

**Functions to Remove:**
```python
# In src/fapilog/enrichers.py
def clear_enrichers() -> None:
    """Clear all registered enrichers (for testing)."""
    # This entire function should be removed
```

**Export Cleanup:**
```python
# Remove from __all__ in enrichers.py:
__all__ = [
    # Remove these legacy exports:
    "register_enricher",
    "clear_enrichers", 
    "run_registered_enrichers",
    
    # Keep only:
    "register_enricher_advanced",
    # ... other non-legacy exports
]
```

### Search Patterns for Final Verification

**Legacy Function References:**
- `register_enricher(` - Function calls
- `clear_enrichers` - Utility function usage
- `run_registered_enrichers` - Processor function usage
- `_registered_enrichers` - Global state access

**Legacy Import Patterns:**
- `from fapilog.enrichers import register_enricher`
- `from .enrichers import clear_enrichers`
- `import.*register_enricher`

**Documentation Patterns:**
- Docstring references to legacy functions
- Comment mentions of old patterns
- Example code using legacy system

### Module Structure After Cleanup

**src/fapilog/enrichers.py should contain only:**
```python
# New enricher system
register_enricher_advanced()  # Class-based registration decorator

# Built-in enrichers (unchanged)
tenant_enricher()
session_enricher()
user_context_enricher()
environment_enricher()
# ... other built-in enrichers

# Module exports
__all__ = [
    "register_enricher_advanced",
    "tenant_enricher", 
    "session_enricher",
    "user_context_enricher",
    "environment_enricher",
    # ... other non-legacy exports
]
```

### Error Handling for Legacy Usage

**Migration Error Messages:**
```python
# Optional: Add stub functions with helpful errors
def register_enricher(*args, **kwargs):
    raise AttributeError(
        "register_enricher() has been removed. "
        "Use register_enricher_advanced() instead."
    )

def clear_enrichers(*args, **kwargs):
    raise AttributeError(
        "clear_enrichers() has been removed. "
        "Use EnricherRegistry.clear_registry() instead."
    )
```

### API Surface Verification

**Public API After Cleanup:**
- `register_enricher_advanced()` - Primary registration decorator
- Built-in enricher functions (unchanged)
- `EnricherRegistry` - Advanced registry (internal)
- `EnricherFactory` - URI-based creation (internal)

**Removed from Public API:**
- `register_enricher()`
- `clear_enrichers()`
- `run_registered_enrichers()`
- `_registered_enrichers`

### Testing Strategy

**Verification Tests:**
- Import tests to verify clean API surface
- Error message tests for legacy function stubs
- Functional tests to ensure all enricher functionality works
- Performance tests to verify no regressions

**Search Verification:**
- Automated search for legacy patterns
- Grep-based verification of cleanup completeness
- Import analysis to verify clean dependencies
- Documentation scan for legacy references

### Dependencies

**Prerequisites:**
- Story 17.2 (legacy function removal) complete
- Story 17.3 (legacy processor removal) complete
- All tests using legacy patterns migrated

**Verification Requirements:**
- New enricher system handles all functionality
- No functional regressions introduced
- Clean error messages for legacy usage attempts
- Performance maintained or improved

### Risk Assessment

**Low Risk Changes:**
- Removing already-unused functions
- Cleaning up imports and exports
- Documentation updates

**Medium Risk Changes:**
- Final legacy state removal
- API surface modifications

**Mitigation:**
- Comprehensive search before removal
- Test all enricher functionality after cleanup
- Verify error messages work correctly
- Performance benchmarking

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|---------|
| 2024-12-30 | 1.0 | Initial story creation for final legacy cleanup | Quinn (QA) | 