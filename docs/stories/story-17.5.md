# Story 17.5 – Remove Legacy Enricher Test Files

**Epic:** 17 – Legacy Code Removal  
Sprint Target: Sprint #⟪next⟫  
Story Points: 2

## Status
Draft

## Story

**As a developer maintaining clean test architecture**  
I want to remove test files that test legacy enricher functionality  
So that only tests for the new enricher system remain.

## Acceptance Criteria

1. **Legacy Test Removal**: All test files testing legacy enricher functions removed
2. **Coverage Verification**: Confirm new test files provide equivalent or better coverage
3. **Clean Test Suite**: Test suite runs cleanly with only new enricher tests
4. **No Regressions**: All functionality is still tested via new test files
5. **Performance Maintained**: Test execution time not negatively impacted
6. **Documentation Updated**: Remove references to deleted test files
7. **Import Cleanup**: No orphaned test imports or dependencies

## Tasks / Subtasks

1. **[⏸] Identify and Remove Legacy Test Files**
   - [ ] Remove `tests/test_enricher_registry.py` - Tests legacy `register_enricher(fn)`
   - [ ] Remove `tests/test_pipeline_with_custom_enrichers.py` - Tests legacy pipeline integration
   - [ ] Remove any other test files that primarily test legacy enricher functionality
   - [ ] Clean up test imports and references

2. **[⏸] Verify Coverage Equivalence**
   - [ ] Run coverage analysis before removal to establish baseline
   - [ ] Compare coverage after removal to ensure no gaps
   - [ ] Verify new tests cover all scenarios previously tested by legacy tests
   - [ ] Document any coverage gaps and address if needed

3. **[⏸] Update Test Infrastructure**
   - [ ] Remove any test utilities specific to legacy enricher system
   - [ ] Clean up shared test fixtures that are no longer needed
   - [ ] Update test configuration files if needed
   - [ ] Verify test discovery still works correctly

4. **[⏸] Final Test Suite Validation**
   - [ ] Run complete test suite to ensure all tests pass
   - [ ] Verify test execution time is maintained or improved
   - [ ] Check that no orphaned imports or dependencies remain
   - [ ] Validate test isolation and cleanup work correctly

## Dev Notes

### Files to Remove

**Primary Removal Targets:**
- `tests/test_enricher_registry.py` - Tests legacy `register_enricher(fn)`, `run_registered_enrichers()`, `clear_enrichers()`
- `tests/test_pipeline_with_custom_enrichers.py` - Tests legacy pipeline integration patterns

**Coverage Analysis Required:**
Before removal, verify these scenarios are covered by new tests:
- Enricher registration and execution
- Multiple enricher ordering
- Enricher error handling
- Pipeline integration
- Test isolation and cleanup

### New Test Coverage Verification

**Equivalent Coverage Provided By:**
- `tests/test_enricher_advanced_decorator.py` - Registration patterns (better coverage)
- `tests/test_enricher_registry_enhanced.py` - Registry functionality (superior coverage)
- `tests/test_async_enricher_integration.py` - Pipeline integration (enhanced coverage)
- `tests/test_enricher_conditions.py` - Conditional logic (new functionality)
- `tests/test_enricher_factory.py` - URI-based creation (new functionality)

### Why Deletion vs Migration

**Legacy tests test deprecated functionality:**
```python
# Legacy test patterns (to be deleted):
register_enricher(function)  # Deprecated function
run_registered_enrichers()   # Deprecated processor  
clear_enrichers()           # Deprecated cleanup
```

**New tests test current functionality:**
```python
# New test patterns (already exist):
@register_enricher_advanced(name="test", priority=50)
class TestEnricher: ...      # Current registration

EnricherRegistry.clear_registry()  # Current cleanup
create_enricher_processor()        # Current pipeline
```

### Coverage Analysis Commands

**Before Removal:**
```bash
python -m pytest --cov=src/fapilog --cov-report=html tests/
cp htmlcov/index.html coverage_before_removal.html
```

**After Removal:**
```bash
python -m pytest --cov=src/fapilog --cov-report=html tests/
# Compare coverage reports
```

### Risk Assessment

**Very Low Risk:**
- Legacy test files test functionality we're removing
- New tests provide superior coverage of current functionality
- No functionality loss since legacy code is being removed

**Verification Steps:**
- Coverage analysis confirms no gaps
- All new enricher functionality tested
- Test suite execution time maintained

### Dependencies

**Prerequisites:**
- Stories 17.2-17.4 (legacy code removal) should be complete
- New enricher system fully functional and tested

**Benefits:**
- Cleaner test suite
- Faster test execution
- No maintenance burden for deprecated functionality
- Focus on current enricher system

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|---------|
| 2024-12-30 | 1.0 | Revised to remove legacy tests rather than migrate | Quinn (QA) | 