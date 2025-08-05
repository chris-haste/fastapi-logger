# Configuration Factory

The `ConfigurationFactory` provides a convenient way to create optimized, environment-specific logging configurations using tested presets. This eliminates configuration duplication and ensures consistent setups across different deployment environments.

## Overview

Instead of manually creating `LoggingSettings` objects with complex nested configurations, you can use factory presets that provide optimized defaults for common scenarios:

```python
from fapilog import configure_logging
from fapilog.config.factory import ConfigurationFactory

# Simple development setup
config = ConfigurationFactory.development()
configure_logging(config)

# Production-ready configuration
config = ConfigurationFactory.production()
configure_logging(config)
```

## Available Presets

### Development (`development()`)

Optimized for development environments with detailed logging and readable output:

- **Log Level**: DEBUG (shows all log messages)
- **Console Output**: Pretty-formatted for readability
- **Queue Settings**: Small queue (100 items) with immediate processing
- **Security**: PII redaction disabled for debugging
- **Metrics**: Disabled for performance
- **Resource Monitoring**: Disabled

```python
config = ConfigurationFactory.development()
# Logs will show in pretty format with DEBUG level
```

### Production (`production()`)

Optimized for production environments with security, performance, and monitoring:

- **Log Level**: INFO (balanced performance and information)
- **Console Output**: JSON format for log aggregation
- **Queue Settings**: Optimized queue (1000 items) with batching
- **Security**: PII redaction enabled, throttling, deduplication
- **Metrics**: Full metrics collection with Prometheus
- **Resource Monitoring**: Enabled

```python
config = ConfigurationFactory.production()
# Secure, performant logging with full monitoring
```

### Testing (`testing()`)

Optimized for test environments with minimal overhead:

- **Log Level**: DEBUG (for test debugging)
- **Console Output**: Auto-format
- **Queue Settings**: Disabled (synchronous for predictable tests)
- **Security**: All security features disabled
- **Metrics**: Disabled
- **Resource Monitoring**: Disabled

```python
config = ConfigurationFactory.testing()
# Synchronous, predictable logging for tests
```

### High Performance (`high_performance()`)

Optimized for high-throughput scenarios with minimal overhead:

- **Log Level**: WARNING (reduced log volume)
- **Console Output**: JSON format
- **Queue Settings**: Large queue (5000 items) with big batches
- **Security**: All security features disabled for performance
- **Metrics**: Disabled
- **Sampling**: Heavy sampling (10% of logs)

```python
config = ConfigurationFactory.high_performance()
# Maximum throughput with minimal processing
```

### Monitoring (`monitoring()`)

Optimized for observability and monitoring scenarios:

- **Log Level**: INFO
- **Console Output**: JSON format for analysis
- **Queue Settings**: Balanced queue (2000 items) with frequent batching
- **Security**: PII redaction enabled, no throttling for monitoring
- **Metrics**: Full metrics with frequent sampling
- **Resource Monitoring**: Enabled

```python
config = ConfigurationFactory.monitoring()
# Full observability with detailed metrics
```

## Customizing Presets

All factory methods accept keyword arguments to override specific settings:

### Simple Overrides

```python
# Development with custom log level
config = ConfigurationFactory.development(level="INFO")

# Production with custom sinks
config = ConfigurationFactory.production(
    sinks=SinkSettings(
        sinks=["stdout", "file:///var/log/app.log"],
        json_console="pretty"
    )
)
```

### Complex Overrides

```python
from fapilog.config.queue_settings import QueueSettings
from fapilog.config.security_settings import SecuritySettings

# Custom production configuration
config = ConfigurationFactory.production(
    level="DEBUG",
    queue=QueueSettings(
        maxsize=2000,
        batch_size=20,
        overflow="sample"
    ),
    security=SecuritySettings(
        enable_auto_redact_pii=False,
        enable_throttling=False
    )
)
```

### Custom Preset Based on Existing

Use the `custom()` method to build upon existing presets:

```python
# Start with development preset and customize
config = ConfigurationFactory.custom(
    base_preset="development",
    level="INFO",
    queue=QueueSettings(enabled=True, maxsize=500),
    security=SecuritySettings(enable_auto_redact_pii=True)
)

# Start with production preset
config = ConfigurationFactory.custom(
    base_preset="production",
    level="DEBUG"  # More verbose production logging
)
```

## Environment-Based Configuration

Use environment variables to select configurations dynamically:

```python
import os
from fapilog.config.factory import ConfigurationFactory

# Environment-based configuration selection
environments = {
    "development": ConfigurationFactory.development,
    "testing": ConfigurationFactory.testing,
    "production": ConfigurationFactory.production,
    "monitoring": ConfigurationFactory.monitoring,
}

env = os.getenv("APP_ENV", "development")
config_func = environments.get(env, ConfigurationFactory.development)
config = config_func()

configure_logging(config)
```

## Preset Information

Get information about available presets programmatically:

```python
# Get all available presets with descriptions
presets = ConfigurationFactory.get_available_presets()
for name, description in presets.items():
    print(f"{name}: {description}")

# Output:
# development: Development preset: pretty console, debug level, fast queues
# production: Production preset: JSON output, structured logging, optimized queues
# testing: Testing preset: minimal overhead, synchronous processing
# high_performance: High-performance preset: optimized for throughput
# monitoring: Monitoring preset: optimized for observability and metrics
```

## FastAPI Integration

Factory presets work seamlessly with FastAPI applications:

```python
from fastapi import FastAPI
from fapilog import configure_logging
from fapilog.config.factory import ConfigurationFactory

def create_app() -> FastAPI:
    # Configure logging for development
    config = ConfigurationFactory.development()
    configure_logging(config)
    
    app = FastAPI(title="My API")
    return app

# For production deployment
def create_production_app() -> FastAPI:
    config = ConfigurationFactory.production(
        sinks=SinkSettings(
            sinks=["stdout", "file:///var/log/api.log"]
        )
    )
    configure_logging(config)
    
    app = FastAPI(title="My API")
    return app
```

## Docker and Container Environments

Factory presets are ideal for containerized applications:

```python
import os
from fapilog.config.factory import ConfigurationFactory

# Dockerfile can set APP_ENV environment variable
env = os.getenv("APP_ENV", "production")

if env == "development":
    config = ConfigurationFactory.development()
elif env == "testing":
    config = ConfigurationFactory.testing()
elif env == "production":
    config = ConfigurationFactory.production()
else:
    # Default to production for unknown environments
    config = ConfigurationFactory.production()

configure_logging(config)
```

## Best Practices

### 1. Use Presets as Starting Points

Start with the preset that best matches your environment, then customize as needed:

```python
# Good: Start with preset and customize
config = ConfigurationFactory.production(
    level="DEBUG",  # Temporary for debugging
    sinks=SinkSettings(sinks=["stdout", "loki://localhost:3100"])
)

# Avoid: Building from scratch
config = LoggingSettings(
    level="INFO",
    sinks=SinkSettings(...),
    queue=QueueSettings(...),
    # ... many more settings
)
```

### 2. Environment-Specific Configurations

Use different presets for different environments:

```python
# Development
config = ConfigurationFactory.development()

# Staging (production-like but with more logging)
config = ConfigurationFactory.production(level="DEBUG")

# Production
config = ConfigurationFactory.production()

# Load testing
config = ConfigurationFactory.high_performance()
```

### 3. Override Only What You Need

Keep customizations minimal to benefit from preset optimizations:

```python
# Good: Minimal overrides
config = ConfigurationFactory.production(
    sinks=SinkSettings(sinks=["stdout", "file:///logs/app.log"])
)

# Avoid: Over-customization
config = ConfigurationFactory.production(
    level="DEBUG",
    queue=QueueSettings(...),  # Many overrides
    security=SecuritySettings(...),
    metrics=MetricsSettings(...),
    # Defeats the purpose of using presets
)
```

### 4. Document Your Customizations

When customizing presets, document why:

```python
# Production config with debug logging for incident investigation
config = ConfigurationFactory.production(
    level="DEBUG",  # Temporary: investigating issue #123
    queue=QueueSettings(maxsize=2000)  # Higher volume expected
)
```

## Comparison with Manual Configuration

### Before (Manual Configuration)

```python
from fapilog.config.settings import LoggingSettings
from fapilog.config.queue_settings import QueueSettings
from fapilog.config.sink_settings import SinkSettings
from fapilog.config.security_settings import SecuritySettings

# Manual configuration - error-prone and verbose
config = LoggingSettings(
    level="INFO",
    enable_resource_metrics=True,
    sinks=SinkSettings(
        sinks=["stdout"],
        json_console="json",
        sampling_rate=1.0
    ),
    queue=QueueSettings(
        enabled=True,
        maxsize=1000,
        batch_size=10,
        batch_timeout=1.0,
        overflow="drop"
    ),
    security=SecuritySettings(
        enable_auto_redact_pii=True,
        redact_level="INFO",
        enable_throttling=True,
        # ... many more settings
    ),
    # ... even more nested configurations
)
```

### After (Factory Pattern)

```python
from fapilog.config.factory import ConfigurationFactory

# Simple, tested, optimized
config = ConfigurationFactory.production()

# Or with minimal customization
config = ConfigurationFactory.production(
    sinks=SinkSettings(sinks=["stdout", "file:///logs/app.log"])
)
```

## Migration Guide

If you're currently using manual `LoggingSettings` configuration:

1. **Identify your environment**: development, testing, production, etc.
2. **Choose the closest preset**: Start with the factory method that matches
3. **Add necessary overrides**: Only override what differs from the preset
4. **Test thoroughly**: Verify logging behavior matches your expectations
5. **Remove old configuration**: Clean up manual configuration code

### Example Migration

```python
# Before
config = LoggingSettings(
    level="DEBUG",
    json_console="pretty",
    queue_enabled=True,
    queue_maxsize=100,
    queue_batch_size=1,
    enable_resource_metrics=False
)

# After
config = ConfigurationFactory.development()
# All the same settings with additional optimizations!
```

## Troubleshooting

### Configuration Not Applied

Ensure you're passing the config to `configure_logging()`:

```python
config = ConfigurationFactory.development()
configure_logging(config)  # Don't forget this!
```

### Preset Doesn't Match Needs

Use `custom()` method or override specific settings:

```python
# If no preset is quite right
config = ConfigurationFactory.custom(
    base_preset="production",
    level="DEBUG",
    queue=QueueSettings(enabled=False)
)
```

### Unknown Preset Error

Check available presets:

```python
presets = ConfigurationFactory.get_available_presets()
print(list(presets.keys()))
# ['development', 'production', 'testing', 'high_performance', 'monitoring']
```

## See Also

- [Configuration Settings](configuration.md) - Detailed configuration options
- [FastAPI Integration](quickstart.md) - Using fapilog with FastAPI
- [Examples](../examples/) - Complete working examples
- [Testing](testing.md) - Testing with fapilog configurations