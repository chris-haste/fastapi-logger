# Story 17.7 – Update Examples to Use New Patterns Only

**Epic:** 17 – Legacy Code Removal  
Sprint Target: Sprint #⟪next⟫  
Story Points: 1

## Status
Draft

## Story

**As a developer maintaining consistent examples**  
I want to update all example files to use only new enricher and sink patterns  
So that examples demonstrate current best practices only.

## Acceptance Criteria

1. **Example Updates**: All example files use new enricher and sink patterns
2. **Pattern Consistency**: Examples demonstrate `register_enricher_advanced()` and URI-based sinks
3. **No Legacy Patterns**: No examples show `register_enricher(fn)` or direct sink instances
4. **Documentation Accuracy**: Example comments explain new patterns clearly
5. **Runnable Examples**: All updated examples execute correctly
6. **Best Practices**: Examples demonstrate proper error handling and lifecycle management
7. **Complete Coverage**: Both enricher and sink examples updated

## Tasks / Subtasks

1. **[⏸] Update Enricher Examples**
   - [ ] Replace `@register_enricher` with `@register_enricher_advanced()` in example files
   - [ ] Convert function-based examples to class-based enrichers
   - [ ] Add proper metadata (name, description, priority) to enricher registrations
   - [ ] Update example comments to explain new patterns

2. **[⏸] Update Sink Examples**
   - [ ] Replace direct sink instances with URI-based configuration
   - [ ] Update custom sink examples to use `@register_sink()` decorator
   - [ ] Show proper custom sink registration and URI usage
   - [ ] Update example comments for URI patterns

3. **[⏸] Update Mixed Examples**
   - [ ] Examples showing both enrichers and sinks together
   - [ ] FastAPI integration examples using new patterns
   - [ ] Container usage examples with new configuration
   - [ ] Bootstrap examples with URI-based setup

4. **[⏸] Verify Example Execution**
   - [ ] Test that all updated examples run without errors
   - [ ] Verify example output demonstrates expected functionality
   - [ ] Check that examples use realistic, helpful scenarios
   - [ ] Ensure examples are self-contained and runnable

5. **[⏸] Update Example Documentation**
   - [ ] Add migration notes showing old vs new patterns
   - [ ] Update example docstrings to explain new approaches
   - [ ] Remove any legacy pattern references from comments
   - [ ] Add links to relevant documentation

## Dev Notes

### Example Files to Update

**Primary Example Files:**
- `examples/custom_enricher_example.py` - Convert to class-based enrichers
- `examples/sink_examples/` - Update custom sink examples
- Any other examples using legacy patterns

### Enricher Example Updates

**Legacy Example Pattern:**
```python
# OLD - Remove this pattern:
from fapilog.enrichers import register_enricher

@register_enricher
def custom_enricher(logger, method_name, event_dict):
    event_dict["custom_field"] = "value"
    return event_dict
```

**New Example Pattern:**
```python
# NEW - Use this pattern:
from fapilog.enrichers import register_enricher_advanced

@register_enricher_advanced(
    name="custom_enricher",
    description="Adds custom field to log events",
    priority=100,
    async_capable=False
)
class CustomEnricher:
    def __call__(self, logger, method_name, event_dict):
        event_dict["custom_field"] = "value"
        return event_dict
```

### Sink Example Updates

**Legacy Example Pattern:**
```python
# OLD - Remove this pattern:
from fapilog.sinks import StdoutSink, FileSink
from fapilog.settings import LoggingSettings

settings = LoggingSettings(sinks=[
    StdoutSink(mode="json"),
    FileSink("/var/log/app.log")
])
```

**New Example Pattern:**
```python
# NEW - Use this pattern:
from fapilog.settings import LoggingSettings

settings = LoggingSettings(sinks=[
    "stdout://json",
    "file:///var/log/app.log"
])

# For custom sinks:
from fapilog._internal.sink_registry import register_sink

@register_sink("custom")
class CustomSink(Sink):
    async def write(self, event_dict):
        # Implementation
        pass

# Then use: "custom://config"
```

### Example Categories

**Simple Examples:**
- Basic enricher registration and usage
- Simple sink configuration
- Standard logging setup

**Advanced Examples:**
- Async enricher examples with lifecycle
- Custom sink registration and URI configuration
- Complex enricher dependencies and conditions
- Performance optimization examples

**Integration Examples:**
- FastAPI middleware integration
- Container-based setup
- Production configuration examples
- Testing and debugging examples

### Testing Examples

**Verification Steps:**
- Run each example independently
- Check output matches expected behavior
- Verify no legacy import errors
- Confirm examples are educational and clear

### Risk Assessment

**Very Low Risk:**
- Examples are documentation, not core functionality
- Easy to test and verify independently
- Clear migration path for each pattern

### Dependencies

**Prerequisites:**
- Stories 17.2-17.6 complete (core legacy removal)
- New enricher and sink systems fully functional

**Benefits:**
- Consistent example patterns
- Clear learning path for users
- No confusion from mixed legacy/new patterns
- Demonstrates best practices

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|---------|
| 2024-12-30 | 1.0 | Initial story creation for example updates | Quinn (QA) | 