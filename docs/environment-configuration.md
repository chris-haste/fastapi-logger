# Environment Configuration Best Practices

This document outlines the recommended patterns for environment variable access in the fapilog project.

## Policy

**Direct `os.getenv()` usage is discouraged throughout the codebase.** Instead, use the fapilog configuration system to ensure consistent validation, type checking, and error handling.

## Recommended Approaches

### 1. Pydantic Settings (Preferred)

For application configuration, use Pydantic Settings with proper validation:

```python
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from fapilog.exceptions import ConfigurationError

class MyServiceSettings(BaseSettings):
    """Configuration for my service."""

    port: int = Field(
        default=8000,
        description="Service port",
        ge=1,
        le=65535,
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )
    api_key: str = Field(
        description="Required API key",
    )

    model_config = SettingsConfigDict(
        env_prefix="MY_SERVICE_",
        case_sensitive=False,
        extra="forbid",
    )

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        if not v or len(v) < 10:
            raise ConfigurationError(
                "API key must be at least 10 characters",
                setting="api_key",
                value=v,
                expected_type="string with length >= 10",
            )
        return v

# Usage
settings = MyServiceSettings()
print(f"Server running on port {settings.port}")
```

### 2. Environment Utility (For Utilities)

For standalone utilities or scripts that need environment variable access:

```python
from fapilog.config.env_utils import EnvironmentConfig

# Simple usage
debug = EnvironmentConfig.get_bool("DEBUG", default=False)
port = EnvironmentConfig.get_int("PORT", default=8000)
api_url = EnvironmentConfig.get_string("API_URL", required=True)

# With validation
def validate_positive(value: int) -> int:
    if value <= 0:
        raise ValueError("Value must be positive")
    return value

workers = EnvironmentConfig.get_validated(
    "WORKERS",
    default=4,
    env_type=int,
    validator=validate_positive,
)

# Convenience methods
concurrency = EnvironmentConfig.get_int(
    "CONCURRENCY",
    default=10,
    validator=lambda x: max(1, min(x, 100))  # Clamp to 1-100
)
```

### 3. Configuration Classes for Complex Logic

For complex configuration that requires multiple environment variables:

```python
from fapilog.config import LoadTestSettings

class MyComplexSettings(BaseSettings):
    """Complex settings with validation."""

    # Use nested settings for organization
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_nested_delimiter="__",  # APP_DATABASE__HOST
    )

# Usage
settings = MyComplexSettings()
```

## Examples from the Codebase

### Load Test Configuration

The `LoadTestSettings` class demonstrates proper environment variable handling:

```python
# Environment variables with validation
LOAD_TEST_CONCURRENCY=20 python scripts/load_test_log_queue.py

# This automatically validates:
# - concurrency is between 1 and 1000
# - rate is positive and <= 10000
# - duration is positive and <= 3600 seconds
# - All values are properly typed
```

### Environment Utility Usage

The `EnvironmentConfig` utility provides validated access:

```python
from fapilog.config.env_utils import EnvironmentConfig

# Type-safe with defaults
timeout = EnvironmentConfig.get_float("TIMEOUT", default=30.0)

# Required variables with validation
api_key = EnvironmentConfig.get_string("API_KEY", required=True)

# Custom validation
batch_size = EnvironmentConfig.get_validated(
    "BATCH_SIZE",
    default=100,
    env_type=int,
    validator=lambda x: x if x > 0 else ValueError("Batch size must be positive"),
)
```

## Migration Guide

### Before (Discouraged)

```python
import os

# Direct access - no validation, no type checking
port = int(os.getenv("PORT", "8000"))
debug = os.getenv("DEBUG", "false").lower() == "true"
api_key = os.getenv("API_KEY")  # Could be None!
```

### After (Recommended)

```python
from fapilog.config.env_utils import EnvironmentConfig

# Validated access with proper typing
port = EnvironmentConfig.get_int("PORT", default=8000)
debug = EnvironmentConfig.get_bool("DEBUG", default=False)
api_key = EnvironmentConfig.get_string("API_KEY", required=True)
```

## Benefits

1. **Type Safety**: Automatic type conversion with validation
2. **Error Handling**: Clear error messages for invalid values
3. **Documentation**: Built-in field descriptions and constraints
4. **Testing**: Easy to mock and test configuration
5. **Consistency**: Uniform patterns across the codebase
6. **Validation**: Custom validators for business logic

## Testing Configuration

```python
from unittest.mock import patch
from fapilog.config.env_utils import EnvironmentConfig

def test_configuration():
    with patch.dict(os.environ, {"TEST_VAR": "42"}):
        value = EnvironmentConfig.get_int("TEST_VAR")
        assert value == 42

    # Test validation errors
    with patch.dict(os.environ, {"INVALID_INT": "not_a_number"}):
        with pytest.raises(ConfigurationError):
            EnvironmentConfig.get_int("INVALID_INT")
```

## Project Policy

- **Examples**: Can use direct `os.getenv()` for simplicity
- **Source Code**: Must use configuration objects or `EnvironmentConfig`
- **Scripts**: Should use configuration classes for consistency
- **Tests**: Use mocking with `patch.dict(os.environ, ...)`

This approach ensures robust, validated, and testable environment variable handling throughout the fapilog project.
