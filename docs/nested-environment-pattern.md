# Nested Environment Variable Pattern

This document outlines the unified pattern for handling nested environment variables in the fapilog configuration system.

## Pattern Overview

All nested settings classes follow a consistent pattern where they inherit environment variable handling from the parent `LoggingSettings` class, using the `env_nested_delimiter="__"` configuration.

## Environment Variable Structure

### Parent Settings (LoggingSettings)

- **Prefix**: `FAPILOG_`
- **Nested Delimiter**: `__`
- **Example**: `FAPILOG_QUEUE__MAXSIZE=1000`

### Nested Settings Classes

All nested settings classes use this consistent pattern:

```python
class NestedSettings(BaseSettings):
    """Configuration settings for nested functionality."""

    # Field definitions...

    model_config = SettingsConfigDict(
        case_sensitive=False,
    )
```

**Key Points:**

- No explicit `env_prefix` - inherits from parent
- No explicit `env_nested_delimiter` - inherits from parent
- Only `case_sensitive=False` for consistency

## Environment Variable Examples

### Queue Settings

```bash
# Queue configuration via environment variables
export FAPILOG_QUEUE__ENABLED=true
export FAPILOG_QUEUE__MAXSIZE=1000
export FAPILOG_QUEUE__BATCH_SIZE=10
export FAPILOG_QUEUE__OVERFLOW=drop
```

### Security Settings

```bash
# Security configuration via environment variables
export FAPILOG_SECURITY__ENABLE_AUTO_REDACT_PII=true
export FAPILOG_SECURITY__REDACT_LEVEL=INFO
export FAPILOG_SECURITY__REDACT_FIELDS=password,token,secret
export FAPILOG_SECURITY__ENABLE_THROTTLING=true
```

### Sink Settings

```bash
# Sink configuration via environment variables
export FAPILOG_SINKS__SINKS=stdout,file:///logs/app.log
export FAPILOG_SINKS__JSON_CONSOLE=json
export FAPILOG_SINKS__SAMPLING_RATE=1.0
```

### Metrics Settings

```bash
# Metrics configuration via environment variables
export FAPILOG_METRICS__ENABLED=true
export FAPILOG_METRICS__PROMETHEUS_ENABLED=true
export FAPILOG_METRICS__PROMETHEUS_PORT=9090
```

### Validation Settings

```bash
# Validation configuration via environment variables
export FAPILOG_VALIDATION__ENABLED=true
export FAPILOG_VALIDATION__MODE=strict
export FAPILOG_VALIDATION__REQUIRED_FIELDS=timestamp,level,message
```

## Benefits of This Pattern

1. **Consistency**: All nested settings follow the same pattern
2. **Predictability**: Environment variable names are predictable and hierarchical
3. **Maintainability**: Single source of truth for environment configuration
4. **Documentation**: Clear mapping between environment variables and settings
5. **Testing**: Easy to mock and test with predictable variable names

## Migration from Inconsistent Patterns

### Before (Inconsistent)

```python
# Some classes had explicit env_prefix=""
class SinkSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="",  # Inconsistent
        case_sensitive=False,
    )

# Others had no env_prefix (inherited)
class QueueSettings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False,
    )
```

### After (Unified)

```python
# All nested settings classes use consistent pattern
class SinkSettings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False,
    )

class QueueSettings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False,
    )
```

## Implementation Details

### Parent Configuration (LoggingSettings)

```python
model_config = SettingsConfigDict(
    env_prefix="FAPILOG_",
    case_sensitive=False,
    extra="forbid",
    env_nested_delimiter="__",  # Enables nested environment variables
)
```

### Nested Settings Pattern

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

    @field_validator("field_name")
    @classmethod
    def validate_field_name(cls, v: str) -> str:
        # Validation logic
        return v
```

## Testing the Pattern

```python
import os
from fapilog.config import LoggingSettings

def test_nested_environment_variables():
    """Test nested environment variable configuration."""

    # Set nested environment variables
    os.environ["FAPILOG_QUEUE__MAXSIZE"] = "500"
    os.environ["FAPILOG_SECURITY__ENABLE_AUTO_REDACT_PII"] = "true"
    os.environ["FAPILOG_SINKS__JSON_CONSOLE"] = "json"

    # Create settings - should pick up nested variables
    settings = LoggingSettings()

    assert settings.queue.maxsize == 500
    assert settings.security.enable_auto_redact_pii is True
    assert settings.sinks.json_console == "json"
```

## Best Practices

1. **Always use the nested delimiter pattern** for complex configuration
2. **Document environment variables** in field descriptions
3. **Use consistent naming** for environment variables
4. **Test with environment variables** to ensure proper parsing
5. **Provide clear examples** in documentation

This unified pattern ensures consistent, predictable, and maintainable environment variable handling across the entire fapilog configuration system.
