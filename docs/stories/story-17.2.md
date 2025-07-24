# Story 17.2 – Remove Legacy register_enricher Function

**Epic:** 17 – Legacy Code Removal  
Sprint Target: Sprint #⟪next⟫  
Story Points: 2

## Status
Draft

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

1. **[⏸] Remove Core Legacy Function**
   - [ ] Delete `register_enricher(fn)` function from `src/fapilog/enrichers.py`
   - [ ] Remove function signature validation logic
   - [ ] Remove function-to-class wrapping code
   - [ ] Clean up associated helper functions

2. **[⏸] Remove Global State Storage**
   - [ ] Delete `_registered_enrichers` global list
   - [ ] Remove all references to the global list
   - [ ] Clean up list management logic
   - [ ] Remove associated initialization code

3. **[⏸] Update Internal Imports**
   - [ ] Remove `register_enricher` from `__all__` exports
   - [ ] Update any internal imports that reference the function
   - [ ] Clean up import statements in affected modules
   - [ ] Verify no circular import issues

4. **[⏸] Add Migration Error Handling**
   - [ ] Add helpful error message for legacy function attempts
   - [ ] Provide clear migration guidance in error
   - [ ] Include examples of new registration pattern
   - [ ] Ensure error is discoverable and actionable

5. **[⏸] Verify Complete Removal**
   - [ ] Search codebase for any remaining references
   - [ ] Check that no dead code remains
   - [ ] Verify all enricher functionality works via new system
   - [ ] Confirm no performance regressions

## Dev Notes

### Removal Scope

**Target File**: `src/fapilog/enrichers.py`

**Functions to Remove:**
```python
def register_enricher(fn: Callable[..., Any]) -> None:
    # This entire function and its logic
```

**Global Variables to Remove:**
```python
_registered_enrichers: List[Callable[..., Any]] = []
```

**Associated Code to Remove:**
- Function signature validation in `register_enricher`
- `FunctionEnricherWrapper` class creation logic  
- Advanced registry registration from legacy function
- Error handling specific to function registration

### Replacement Strategy

**Before (Legacy):**
```python
@register_enricher
def my_enricher(logger, method_name, event_dict):
    return event_dict
```

**After (New System):**
```python
@register_enricher_advanced(
    name="my_enricher",
    priority=1000,
    async_capable=False
)
class MyEnricher:
    def __call__(self, logger, method_name, event_dict):
        return event_dict
```

### Migration Error Message

**Suggested Error:**
```python
# Add this to enrichers.py to catch legacy usage attempts
def register_enricher(*args, **kwargs):
    raise AttributeError(
        "register_enricher() has been removed. "
        "Please use register_enricher_advanced() instead.\n"
        "See migration guide: [URL to migration docs]"
    )
```

### Verification Steps

**Code Search Patterns:**
- `register_enricher(` - Direct function calls
- `from .enrichers import register_enricher` - Import statements  
- `_registered_enrichers` - Global list usage
- `FunctionEnricherWrapper` - Helper class usage

**Functionality Verification:**
- All enricher registration works via new system
- Pipeline processing maintains same behavior
- No dead code or unused imports remain
- Error messages are clear and helpful

### Dependencies

**Prerequisites:**
- Story 17.1 (audit) must be complete to identify all usage
- All code using legacy patterns should be converted manually

**Impact Areas:**
- `src/fapilog/enrichers.py` - Primary target file
- `src/fapilog/pipeline.py` - Imports may need updating
- Any remaining test files using legacy patterns

### Testing Standards

**Removal Verification:**
- Code search confirms no legacy function references
- Import statements work correctly
- Error message displays for legacy usage attempts
- All enricher functionality works via new system

**Regression Testing:**
- All existing functionality available through new system
- No performance impact from removal
- Clean error messages for migration scenarios
- No dead code or security issues

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|---------|
| 2024-12-30 | 1.0 | Initial story creation for legacy function removal | Quinn (QA) | 