# Story 17.1 – Audit Legacy Enricher Usage and Create Removal Plan

**Epic:** 17 – Legacy Code Removal  
Sprint Target: Sprint #⟪next⟫  
Story Points: 3

## Status
Draft

## Story

**As a developer maintaining the codebase**  
I want a comprehensive audit of all legacy enricher usage  
So that I can create a precise removal plan without breaking any functionality.

## Acceptance Criteria

1. **Complete Usage Inventory**: All usages of legacy enricher functions are documented with file locations
2. **Impact Analysis**: Each usage is categorized by impact level (critical, moderate, low)
3. **Dependency Mapping**: Dependencies between legacy and new systems are mapped
4. **Test Coverage Analysis**: All tests using legacy enrichers are identified and categorized
5. **Migration Strategy**: Detailed migration plan created for each usage category
6. **Risk Assessment**: Potential risks and mitigation strategies documented
7. **Verification Plan**: Test plan created to verify successful migration

## Tasks / Subtasks

1. **[⏸] Audit Legacy Function Usage**
   - [ ] Find all `register_enricher(fn)` function calls across codebase
   - [ ] Document file locations and usage patterns
   - [ ] Identify direct vs indirect dependencies
   - [ ] Categorize by complexity (simple function vs complex logic)

2. **[⏸] Audit Legacy Pipeline Integration**
   - [ ] Document `run_registered_enrichers` usage in pipeline
   - [ ] Map interactions with new `create_enricher_processor`
   - [ ] Identify processor ordering dependencies
   - [ ] Document performance impact of dual system

3. **[⏸] Audit Test File Dependencies**
   - [ ] Scan all test files for legacy enricher usage
   - [ ] Categorize tests by type (unit, integration, example)
   - [ ] Identify tests that can be easily migrated
   - [ ] Identify tests requiring significant refactoring

4. **[⏸] Create Migration Mapping**
   - [ ] Create mapping from legacy patterns to new patterns
   - [ ] Document parameter conversion requirements
   - [ ] Identify cases requiring custom migration logic
   - [ ] Create conversion examples for each pattern type

5. **[⏸] Document Risk Mitigation**
   - [ ] Identify breaking changes and their scope
   - [ ] Create rollback plan for each change
   - [ ] Document verification steps for each migration
   - [ ] Plan incremental migration approach

## Dev Notes

### Scope Constraints

**Files to Audit:**
- `src/fapilog/enrichers.py` - Legacy registration functions
- `src/fapilog/pipeline.py` - Pipeline integration
- `tests/test_*.py` - All test files using legacy patterns
- `examples/*.py` - Example files with legacy patterns

**Legacy Components to Track:**
- `register_enricher(fn)` function calls
- `run_registered_enrichers()` usage
- `_registered_enrichers` global list access
- `clear_enrichers()` function usage

**Output Requirements:**
- Comprehensive inventory spreadsheet/document
- Migration mapping with before/after examples
- Risk assessment with mitigation strategies
- Test migration plan with effort estimates

### Analysis Methodology

**Usage Pattern Classification:**
1. **Simple Function Registration** - Basic enricher functions
2. **Complex Function Registration** - Functions with dependencies/conditions
3. **Test Utilities** - Helper functions for testing
4. **Example Code** - Documentation and example patterns
5. **Pipeline Integration** - Core system integration points

**Impact Level Scoring:**
- **Critical** - Core functionality, breaking changes
- **Moderate** - Test infrastructure, requires careful migration
- **Low** - Examples, documentation, easy to migrate

### Testing Standards

**Verification Requirements:**
- All legacy usage documented with file:line references
- Migration examples validated with actual code conversion
- Risk assessment includes specific test scenarios
- Output format suitable for subsequent story planning

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|---------|
| 2024-12-30 | 1.0 | Initial story creation for legacy code audit | Quinn (QA) | 