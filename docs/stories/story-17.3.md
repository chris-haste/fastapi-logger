# Story 17.3 – Remove Legacy run_registered_enrichers from Pipeline

**Epic:** 17 – Legacy Code Removal  
Sprint Target: Sprint #⟪next⟫  
Story Points: 2

## Status
Draft

## Story

**As a developer maintaining efficient pipeline architecture**  
I want to remove the legacy `run_registered_enrichers` processor from the pipeline  
So that enrichers run through a single, unified processing system.

## Acceptance Criteria

1. **Processor Removal**: `run_registered_enrichers` function completely removed from pipeline
2. **Pipeline Cleanup**: Legacy processor import and usage removed from `build_processor_chain()`
3. **Single System**: Only `create_enricher_processor()` handles enricher execution
4. **Performance Improvement**: Eliminate dual processor overhead in pipeline
5. **Functional Equivalence**: All enricher functionality works through unified processor
6. **Import Cleanup**: Remove unused imports related to legacy processor
7. **No Side Effects**: Pipeline ordering and behavior unchanged for existing enrichers

## Tasks / Subtasks

1. **[⏸] Remove Legacy Processor from Pipeline**
   - [ ] Remove `run_registered_enrichers` import from `src/fapilog/pipeline.py`
   - [ ] Delete `processors.append(run_registered_enrichers)` call
   - [ ] Clean up any associated comments or documentation
   - [ ] Verify pipeline processor ordering is maintained

2. **[⏸] Remove Legacy Processor Function**
   - [ ] Delete `run_registered_enrichers()` function from `src/fapilog/enrichers.py`
   - [ ] Remove function from `__all__` exports
   - [ ] Clean up associated error handling and logging
   - [ ] Remove function-specific documentation

3. **[⏸] Verify Unified Processing**
   - [ ] Confirm `create_enricher_processor()` handles all enricher types
   - [ ] Validate same enricher execution order is maintained
   - [ ] Check that error handling behavior is preserved
   - [ ] Ensure performance characteristics are maintained or improved

4. **[⏸] Update Pipeline Architecture**
   - [ ] Document the simplified pipeline architecture
   - [ ] Update processor numbering/comments in pipeline
   - [ ] Verify processor chain integrity
   - [ ] Confirm no gaps in enricher processing

5. **[⏸] Clean Up Dead Code**
   - [ ] Search for any remaining references to legacy processor
   - [ ] Remove unused helper functions or variables
   - [ ] Clean up import statements
   - [ ] Verify no orphaned test references

## Dev Notes

### Removal Targets

**Primary File**: `src/fapilog/pipeline.py`

**Code to Remove:**
```python
# Line ~14: Import statement
from .enrichers import run_registered_enrichers

# Line ~162: Processor addition  
processors.append(run_registered_enrichers)
```

**Secondary File**: `src/fapilog/enrichers.py`

**Function to Remove:**
```python
def run_registered_enrichers(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    # This entire function
```

### Pipeline Architecture Changes

**Before (Dual System):**
```python
# Line 162: Legacy function-based enrichers
processors.append(run_registered_enrichers)

# Line 164: New class-based enrichers  
processors.append(create_enricher_processor(settings, enricher_lifecycle))
```

**After (Unified System):**
```python
# Single enricher processor handles all enrichers
processors.append(create_enricher_processor(settings, enricher_lifecycle))
```

### Performance Impact

**Improvements Expected:**
- Eliminate duplicate processor execution overhead
- Reduce function call overhead in pipeline
- Simplify processor chain traversal
- Remove redundant error handling

**Measurements Required:**
- Pipeline execution time before/after
- Memory usage during enricher processing
- CPU overhead reduction

### Functional Verification

**Enricher Execution:**
- All enrichers previously handled by legacy processor work via new processor
- Enricher execution order preserved (priority-based)
- Error handling behavior maintained
- Performance characteristics maintained or improved

**Pipeline Integration:**
- No gaps in enricher processing
- Correct processor ordering maintained
- No side effects on other processors
- Clean error propagation

### Dependencies

**Prerequisites:**
- Story 17.2 must be complete (legacy registration function removed)
- All enrichers must be migrated to new registration system
- No remaining code should use `_registered_enrichers` global list

**Verification Dependencies:**
- `create_enricher_processor()` must handle all legacy enricher functionality
- New registry system must contain all previously registered enrichers
- Test suite must pass with single processor system

### Risk Mitigation

**Potential Issues:**
- Missing enrichers in new system
- Changed execution order
- Performance regressions
- Error handling differences

**Mitigation Strategies:**
- Comprehensive testing before removal
- Behavior comparison between old and new systems
- Performance benchmarks
- Rollback plan if issues discovered

### Testing Standards

**Functional Testing:**
- All enrichers execute correctly through new processor
- Enricher ordering and dependencies work correctly
- Error handling maintains same behavior
- Performance meets or exceeds previous system

**Pipeline Testing:**
- Complete pipeline execution works correctly
- No processor chain gaps or issues
- Clean error propagation and handling
- No regressions in logging functionality

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|---------|
| 2024-12-30 | 1.0 | Initial story creation for legacy processor removal | Quinn (QA) | 