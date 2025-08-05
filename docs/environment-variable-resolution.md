# Environment Variable Resolution: Best-in-Class Solution

## Problem Statement

The codebase had inconsistent environment variable handling patterns:

1. **Some nested settings classes** used `env_prefix=""` (explicitly disabled environment parsing)
2. **Other nested settings classes** inherited environment parsing from parent `LoggingSettings`
3. **This created confusion** about which environment variables were used and how

## Root Cause Analysis

The inconsistency stemmed from two different approaches being used simultaneously:

### Before (Inconsistent)

```python
# Some classes had explicit env_prefix=""
class SinkSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="",  # Explicitly disabled
        case_sensitive=False,
    )

# Others had no env_prefix (inherited)
class QueueSettings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False,
    )
```

## Best-in-Class Solution

### Unified Nested Environment Variable Pattern

**All nested settings classes now follow a consistent pattern:**

```python
class NestedSettings(BaseSettings):
    """Example nested settings class."""

    field_name: str = Field(
        default="default_value",
        description="Field description",
    )

    model_config = SettingsConfigDict(
        case_sensitive=False,
    )
```

### Key Principles

1. **No explicit `env_prefix`** - inherits from parent `LoggingSettings`
2. **No explicit `env_nested_delimiter`** - inherits from parent `LoggingSettings`
3. **Only `case_sensitive=False`** for consistency
4. **All nested settings use the same pattern**

### Parent Configuration (LoggingSettings)

```python
model_config = SettingsConfigDict(
    env_prefix="FAPILOG_",
    case_sensitive=False,
    extra="forbid",
    env_nested_delimiter="__",  # Enables nested environment variables
)
```

## Environment Variable Structure

### Consistent Naming Convention

All environment variables follow this pattern:

- **Prefix**: `FAPILOG_`
- **Nested Delimiter**: `__`
- **Example**: `FAPILOG_QUEUE__MAXSIZE=1000`

### Examples by Settings Class

#### Queue Settings

```bash
export FAPILOG_QUEUE__ENABLED=true
export FAPILOG_QUEUE__MAXSIZE=1000
export FAPILOG_QUEUE__BATCH_SIZE=10
export FAPILOG_QUEUE__OVERFLOW=drop
```

#### Security Settings

```bash
export FAPILOG_SECURITY__ENABLE_AUTO_REDACT_PII=true
export FAPILOG_SECURITY__REDACT_LEVEL=INFO
export FAPILOG_SECURITY__REDACT_FIELDS=password,token,secret
export FAPILOG_SECURITY__ENABLE_THROTTLING=true
```

#### Sink Settings

```bash
export FAPILOG_SINKS__SINKS=stdout,file:///logs/app.log
export FAPILOG_SINKS__JSON_CONSOLE=json
export FAPILOG_SINKS__SAMPLING_RATE=1.0
```

#### Metrics Settings

```bash
export FAPILOG_METRICS__ENABLED=true
export FAPILOG_METRICS__PROMETHEUS_ENABLED=true
export FAPILOG_METRICS__PROMETHEUS_PORT=9090
```

#### Validation Settings

```bash
export FAPILOG_VALIDATION__ENABLED=true
export FAPILOG_VALIDATION__MODE=strict
export FAPILOG_VALIDATION__REQUIRED_FIELDS=timestamp,level,message
```

## Implementation Changes

### Files Updated

1. **`src/fapilog/config/sink_settings.py`**

   - Removed `env_prefix=""`
   - Now inherits environment handling from parent

2. **`src/fapilog/config/metrics_settings.py`**

   - Removed `env_prefix=""`
   - Now inherits environment handling from parent

3. **`src/fapilog/config/validation_settings.py`**

   - Removed `env_prefix=""`
   - Now inherits environment handling from parent

4. **`src/fapilog/config/security_settings.py`**
   - Removed `env_prefix=""`
   - Now inherits environment handling from parent

### Files Already Consistent

- **`src/fapilog/config/queue_settings.py`** - Already used the correct pattern

## Benefits of This Solution

### 1. **Consistency**

- All nested settings follow the same pattern
- No confusion about which environment variables are used
- Predictable behavior across all settings classes

### 2. **Maintainability**

- Single source of truth for environment configuration
- Easy to understand and modify
- Clear documentation of environment variable patterns

### 3. **Predictability**

- Environment variable names are hierarchical and predictable
- Clear mapping between environment variables and settings
- Easy to debug configuration issues

### 4. **Testing**

- Easy to mock and test with predictable variable names
- Comprehensive test coverage for all patterns
- Clear test examples for each settings class

### 5. **Documentation**

- Clear examples for each settings class
- Consistent naming conventions
- Easy to understand for new developers

## Testing the Solution

### Comprehensive Test Suite

Created `tests/test_nested_environment_pattern.py` with tests for:

1. **Individual Settings Classes**

   - Queue settings environment parsing
   - Security settings environment parsing
   - Sink settings environment parsing
   - Metrics settings environment parsing
   - Validation settings environment parsing

2. **Mixed Environment Variables**

   - Multiple nested settings simultaneously
   - Case insensitivity testing
   - Partial overrides

3. **Error Handling**

   - Invalid environment variables
   - Validation errors
   - Type conversion errors

4. **Integration**
   - Factory presets with environment variables
   - Complex type parsing
   - Default value handling

### Test Results

All tests pass, confirming the unified pattern works correctly:

```bash
python -m pytest tests/test_nested_environment_pattern.py -v
# All tests pass
```

## Migration Guide

### For Existing Code

No breaking changes - existing environment variables continue to work:

```bash
# These still work exactly as before
export FAPILOG_QUEUE__MAXSIZE=1000
export FAPILOG_SECURITY__ENABLE_AUTO_REDACT_PII=true
export FAPILOG_SINKS__JSON_CONSOLE=json
```

### For New Development

Use the consistent pattern for all nested settings:

```python
class NewSettings(BaseSettings):
    """New settings class following the unified pattern."""

    field_name: str = Field(
        default="default_value",
        description="Field description",
    )

    model_config = SettingsConfigDict(
        case_sensitive=False,
    )
```

## Best Practices

### 1. **Always Use the Unified Pattern**

- No explicit `env_prefix` in nested settings
- No explicit `env_nested_delimiter` in nested settings
- Only `case_sensitive=False` for consistency

### 2. **Document Environment Variables**

- Include environment variable examples in field descriptions
- Provide clear examples in documentation
- Use consistent naming conventions

### 3. **Test Environment Variables**

- Test with actual environment variables
- Mock environment variables in tests
- Verify validation and type conversion

### 4. **Use Hierarchical Naming**

- Follow the `FAPILOG_SECTION__FIELD` pattern
- Use descriptive section names
- Keep field names clear and consistent

## Conclusion

This unified nested environment variable pattern resolves the inconsistency by:

1. **Eliminating confusion** about which environment variables are used
2. **Providing consistency** across all settings classes
3. **Maintaining backward compatibility** with existing configurations
4. **Improving maintainability** with clear patterns and documentation
5. **Enhancing testability** with comprehensive test coverage

The solution follows Pydantic Settings V2 best practices and provides a robust, predictable, and maintainable configuration system for the fapilog project.
