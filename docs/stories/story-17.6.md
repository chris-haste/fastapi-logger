# Story 17.6 – Remove Legacy Direct Sink Instance Support

**Epic:** 17 – Legacy Code Removal  
Sprint Target: Sprint #⟪next⟫  
Story Points: 2

## Status
Draft

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

1. **[⏸] Update Settings Validation**
   - [ ] Modify `LoggingSettings.parse_sinks()` to reject `Sink` instances
   - [ ] Update type annotation from `Union[str, Sink]` to `str`
   - [ ] Add validation error for direct sink instances
   - [ ] Update field description to reflect URI-only support

2. **[⏸] Update Container Logic**
   - [ ] Remove `isinstance(sink_item, Sink)` check in `_setup_queue_worker()`
   - [ ] Clean up direct sink instance handling code
   - [ ] Ensure all sink creation goes through URI factory patterns
   - [ ] Verify error handling for invalid URIs

3. **[⏸] Update Tests Using Direct Instances**
   - [ ] Find tests that create `LoggingSettings(sinks=[SinkInstance()])`
   - [ ] Convert to URI patterns: `LoggingSettings(sinks=["stdout"])`
   - [ ] Update any bootstrap integration tests
   - [ ] Verify all sink functionality tests pass

4. **[⏸] Add Migration Error Handling**
   - [ ] Clear error message when direct sink instance is used
   - [ ] Guidance on converting to URI patterns
   - [ ] Examples of URI equivalents for common sinks
   - [ ] Helpful validation error messages

5. **[⏸] Documentation and Examples Cleanup**
   - [ ] Remove direct sink instance examples from docstrings
   - [ ] Update module documentation to reflect URI-only patterns
   - [ ] Clean up any remaining references to mixed sink types
   - [ ] Verify examples use URI patterns consistently

## Dev Notes

### Legacy Pattern Removal

**Target Code in `src/fapilog/settings.py`:**
```python
# REMOVE this type annotation:
sinks: Union[List[Union[str, "Sink"]], str] = Field(...)

# CHANGE TO:
sinks: Union[List[str], str] = Field(...)
```

**Target Code in `parse_sinks()` method:**
```python
# REMOVE this logic:
elif Sink is not None and isinstance(item, Sink):
    result.append(item)

# ADD validation error instead:
elif hasattr(item, 'write') and hasattr(item, '__class__'):
    raise ValueError(
        f"Direct sink instances are no longer supported. "
        f"Use URI configuration instead. "
        f"Example: 'stdout' instead of StdoutSink()"
    )
```

### Container Updates

**Target Code in `src/fapilog/container.py`:**
```python
# REMOVE this block in _setup_queue_worker():
if isinstance(sink_item, Sink):
    self._sinks.append(sink_item)
    continue

# All sinks should be created via URI patterns
```

### Migration Examples

**Legacy Direct Instance Pattern:**
```python
# OLD - No longer supported:
from fapilog.sinks import StdoutSink, FileSink

settings = LoggingSettings(sinks=[
    StdoutSink(mode="json"),
    FileSink("/var/log/app.log")
])
```

**New URI Pattern:**
```python
# NEW - URI-based configuration:
settings = LoggingSettings(sinks=[
    "stdout",  # or "stdout://json" for json mode
    "file:///var/log/app.log"
])
```

### Error Message Examples

**Helpful Migration Errors:**
```python
ValueError: Direct sink instances are no longer supported. Use URI configuration instead.
  - Replace StdoutSink() with "stdout"
  - Replace FileSink(path) with "file://{path}" 
  - Replace CustomSink() with "custom://host" (register custom sinks first)
```

### Test Updates Required

**Files likely needing updates:**
- Tests in `test_sink_registry.py` that use mixed sink types
- Bootstrap tests that pass direct sink instances
- Settings tests that validate mixed type support

**Pattern to Convert:**
```python
# OLD test pattern:
settings = LoggingSettings(sinks=[MockSink(), "stdout"])

# NEW test pattern:  
SinkRegistry.register("mock", MockSink)
settings = LoggingSettings(sinks=["mock://test", "stdout"])
```

### Risk Assessment

**Very Low Risk:**
- Simple type validation change
- Comprehensive URI system already exists and tested
- Clear migration path for any existing usage

**Verification Steps:**
- All existing URI-based sinks work identically
- Clear error messages guide migration
- No functional regressions in sink creation

### Dependencies

**Prerequisites:**
- New URI-based sink system fully functional (already complete)
- Sink registry and factory patterns working (already complete)

**Benefits:**
- Cleaner, more consistent configuration API
- Better type safety
- Unified sink creation patterns
- Simplified container logic

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|---------|
| 2024-12-30 | 1.0 | Initial story creation for sink legacy cleanup | Quinn (QA) | 