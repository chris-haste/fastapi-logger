# Enhanced Configuration Factory

The `EnhancedConfigurationFactory` provides advanced configuration management with environment variable support, partial updates, and comprehensive validation.

## Features

### 1. Environment Variable Support

All factory presets support environment variable overrides using the `FAPILOG_FACTORY_` prefix.

### 2. Partial Configuration Updates

Deep merging of configuration sections with the `custom()` method.

### 3. Configuration Validation

Automatic validation of factory-generated configurations with detailed error messages.

### 4. Health Checks

Built-in health checks that identify potential issues and provide recommendations.

## Environment Variable Support

### Environment Variable Format

```
FAPILOG_FACTORY_{PRESET}_{SECTION}_{FIELD}
```

### Examples

#### Development Preset

```bash
export FAPILOG_FACTORY_DEVELOPMENT_LEVEL=INFO
export FAPILOG_FACTORY_DEVELOPMENT_QUEUE_MAXSIZE=500
export FAPILOG_FACTORY_DEVELOPMENT_SECURITY_ENABLE_AUTO_REDACT_PII=true
export FAPILOG_FACTORY_DEVELOPMENT_SINKS_JSON_CONSOLE=json
```

#### Production Preset

```bash
export FAPILOG_FACTORY_PRODUCTION_LEVEL=WARNING
export FAPILOG_FACTORY_PRODUCTION_QUEUE_MAXSIZE=2000
export FAPILOG_FACTORY_PRODUCTION_METRICS_ENABLED=true
export FAPILOG_FACTORY_PRODUCTION_SECURITY_ENABLE_AUTO_REDACT_PII=true
```

#### Testing Preset

```bash
export FAPILOG_FACTORY_TESTING_LEVEL=DEBUG
export FAPILOG_FACTORY_TESTING_QUEUE_ENABLED=false
export FAPILOG_FACTORY_TESTING_SECURITY_ENABLE_AUTO_REDACT_PII=false
```

### Type Parsing

Environment variables are automatically parsed to appropriate types:

- **Boolean**: `true`, `false`, `TRUE`, `FALSE`
- **Integer**: `123`, `0`, `-456`
- **Float**: `1.5`, `0.0`
- **String**: Any other value (default)

## Usage Examples

### Basic Usage with Environment Variables

```python
from fapilog.config.enhanced_factory import EnhancedConfigurationFactory

# Set environment variables
import os
os.environ["FAPILOG_FACTORY_DEVELOPMENT_LEVEL"] = "INFO"
os.environ["FAPILOG_FACTORY_DEVELOPMENT_QUEUE_MAXSIZE"] = "500"

# Create configuration with environment overrides
config = EnhancedConfigurationFactory.development()
print(f"Level: {config.level}")  # INFO (from environment)
print(f"Queue maxsize: {config.queue.maxsize}")  # 500 (from environment)
```

### Partial Updates

```python
from fapilog.config.enhanced_factory import EnhancedConfigurationFactory

# Create custom configuration with partial updates
config = EnhancedConfigurationFactory.custom(
    base_preset="production",
    partial_updates={
        "queue": {
            "maxsize": 2000,
            "batch_size": 25,
            "overflow": "drop"
        },
        "security": {
            "enable_auto_redact_pii": False,
            "redact_level": "ERROR"
        },
        "metrics": {
            "prometheus_port": 9091
        }
    }
)
```

### Precedence Rules

Configuration precedence (highest to lowest):

1. **Programmatic overrides** (highest precedence)
2. **Environment variables**
3. **Factory defaults** (lowest precedence)

```python
# Environment variable
os.environ["FAPILOG_FACTORY_PRODUCTION_LEVEL"] = "WARNING"

# Programmatic override takes precedence
config = EnhancedConfigurationFactory.production(level="DEBUG")
print(config.level)  # DEBUG (not WARNING from environment)
```

### Health Checks

```python
from fapilog.config.enhanced_factory import EnhancedConfigurationFactory
from fapilog.config.settings import LoggingSettings

# Create a configuration that might have issues
config = LoggingSettings(
    level="DEBUG",
    queue=LoggingSettings().queue.model_copy(update={"maxsize": 50}),
    metrics=LoggingSettings().metrics.model_copy(update={"enabled": True})
)

# Perform health check
health_results = EnhancedConfigurationFactory.health_check(config)

print(f"Valid: {health_results['valid']}")
print(f"Warnings: {health_results['warnings']}")
print(f"Recommendations: {health_results['recommendations']}")
```

## Available Presets

### Development Preset

Optimized for development with:

- DEBUG logging level
- Pretty console output
- Small queue sizes for immediate feedback
- PII redaction disabled

**Environment Variables:**

- `FAPILOG_FACTORY_DEVELOPMENT_LEVEL`
- `FAPILOG_FACTORY_DEVELOPMENT_QUEUE_MAXSIZE`
- `FAPILOG_FACTORY_DEVELOPMENT_SECURITY_ENABLE_AUTO_REDACT_PII`
- `FAPILOG_FACTORY_DEVELOPMENT_SINKS_JSON_CONSOLE`

### Production Preset

Optimized for production with:

- INFO logging level
- JSON console output
- Optimized queue sizes
- PII redaction enabled
- Metrics collection enabled

**Environment Variables:**

- `FAPILOG_FACTORY_PRODUCTION_LEVEL`
- `FAPILOG_FACTORY_PRODUCTION_QUEUE_MAXSIZE`
- `FAPILOG_FACTORY_PRODUCTION_SECURITY_ENABLE_AUTO_REDACT_PII`
- `FAPILOG_FACTORY_PRODUCTION_METRICS_ENABLED`

### Testing Preset

Optimized for testing with:

- Minimal overhead
- Synchronous processing
- Disabled features for speed

**Environment Variables:**

- `FAPILOG_FACTORY_TESTING_LEVEL`
- `FAPILOG_FACTORY_TESTING_QUEUE_ENABLED`
- `FAPILOG_FACTORY_TESTING_SECURITY_ENABLE_AUTO_REDACT_PII`

### High-Performance Preset

Optimized for throughput with:

- WARNING logging level
- High sampling rates
- Large queue sizes
- Optimized for speed

**Environment Variables:**

- `FAPILOG_FACTORY_HIGH_PERFORMANCE_LEVEL`
- `FAPILOG_FACTORY_HIGH_PERFORMANCE_QUEUE_MAXSIZE`
- `FAPILOG_FACTORY_HIGH_PERFORMANCE_SINKS_SAMPLING_RATE`

### Monitoring Preset

Optimized for observability with:

- INFO logging level
- Comprehensive metrics
- Prometheus integration
- Detailed monitoring

**Environment Variables:**

- `FAPILOG_FACTORY_MONITORING_LEVEL`
- `FAPILOG_FACTORY_MONITORING_METRICS_ENABLED`
- `FAPILOG_FACTORY_MONITORING_METRICS_PROMETHEUS_PORT`

## Health Check Rules

### Warnings

The health check generates warnings for:

1. **Small queue sizes** (< 100) in production
2. **DEBUG level with metrics enabled** (performance impact)
3. **PII redaction at DEBUG level** (hides useful information)
4. **Very low sampling rates** (< 0.1) (may miss important logs)

### Recommendations

The health check provides recommendations for:

1. **Queue overflow strategy** with small queue sizes
2. **Prometheus port conflicts** with common web server ports
3. **Performance optimizations** based on configuration

## Validation

### Automatic Validation

All factory-generated configurations are automatically validated:

```python
# This will raise ConfigurationError if invalid
try:
    config = EnhancedConfigurationFactory.development(level="INVALID_LEVEL")
except ConfigurationError as e:
    print(f"Invalid configuration: {e}")
```

### Validation Errors

Common validation errors include:

- Invalid log levels
- Invalid queue settings
- Invalid sampling rates
- Invalid security settings

## API Reference

### EnhancedConfigurationFactory

#### Methods

##### `development(**overrides) -> LoggingSettings`

Create development preset with environment variable support.

##### `production(**overrides) -> LoggingSettings`

Create production preset with environment variable support.

##### `testing(**overrides) -> LoggingSettings`

Create testing preset with environment variable support.

##### `high_performance(**overrides) -> LoggingSettings`

Create high-performance preset with environment variable support.

##### `monitoring(**overrides) -> LoggingSettings`

Create monitoring preset with environment variable support.

##### `custom(base_preset: str, partial_updates: Optional[Dict], **overrides) -> LoggingSettings`

Create custom configuration with partial updates and environment support.

##### `health_check(config: LoggingSettings) -> Dict[str, Any]`

Perform health check on configuration.

##### `get_environment_variables(preset_name: str) -> Dict[str, str]`

Get available environment variables for a preset.

### Environment Variable Reference

#### Common Variables

All presets support these environment variables:

- `FAPILOG_FACTORY_{PRESET}_LEVEL`: Override log level
- `FAPILOG_FACTORY_{PRESET}_QUEUE_MAXSIZE`: Override queue size
- `FAPILOG_FACTORY_{PRESET}_SECURITY_ENABLE_AUTO_REDACT_PII`: Override PII redaction
- `FAPILOG_FACTORY_{PRESET}_SINKS_JSON_CONSOLE`: Override console format
- `FAPILOG_FACTORY_{PRESET}_METRICS_ENABLED`: Override metrics collection

#### Preset-Specific Variables

Each preset may support additional environment variables specific to its configuration.

## Migration from Original Factory

### Before (Original Factory)

```python
from fapilog.config.factory import ConfigurationFactory

# No environment variable support
config = ConfigurationFactory.development(level="INFO")
```

### After (Enhanced Factory)

```python
from fapilog.config.enhanced_factory import EnhancedConfigurationFactory

# With environment variable support
os.environ["FAPILOG_FACTORY_DEVELOPMENT_LEVEL"] = "INFO"
config = EnhancedConfigurationFactory.development()
```

## Best Practices

### 1. Use Environment Variables for Deployment

```bash
# Production deployment
export FAPILOG_FACTORY_PRODUCTION_LEVEL=WARNING
export FAPILOG_FACTORY_PRODUCTION_QUEUE_MAXSIZE=2000
export FAPILOG_FACTORY_PRODUCTION_METRICS_ENABLED=true
```

### 2. Use Partial Updates for Customization

```python
# Custom production configuration
config = EnhancedConfigurationFactory.custom(
    base_preset="production",
    partial_updates={
        "queue": {"maxsize": 3000},
        "security": {"enable_auto_redact_pii": False}
    }
)
```

### 3. Perform Health Checks

```python
# Check configuration health
health = EnhancedConfigurationFactory.health_check(config)
if health["warnings"]:
    print("Configuration warnings:", health["warnings"])
```

### 4. Validate Configurations

```python
# Always validate configurations
try:
    config = EnhancedConfigurationFactory.development()
    # Use configuration
except ConfigurationError as e:
    print(f"Configuration error: {e}")
```

## Testing

### Unit Tests

Comprehensive test suite in `tests/test_enhanced_factory.py`:

- Environment variable parsing
- Partial updates
- Precedence rules
- Health checks
- Validation
- Type conversion

### Integration Tests

Test with actual environment variables:

```python
import os
from fapilog.config.enhanced_factory import EnhancedConfigurationFactory

# Set environment variables
os.environ["FAPILOG_FACTORY_DEVELOPMENT_LEVEL"] = "INFO"

# Test configuration
config = EnhancedConfigurationFactory.development()
assert config.level == "INFO"
```

## Conclusion

The `EnhancedConfigurationFactory` provides a robust, flexible, and maintainable way to manage logging configurations with:

- **Environment variable support** for deployment flexibility
- **Partial updates** for fine-grained customization
- **Automatic validation** for configuration safety
- **Health checks** for configuration quality
- **Comprehensive testing** for reliability

This enhanced factory follows best practices for configuration management and provides a solid foundation for production logging systems.
