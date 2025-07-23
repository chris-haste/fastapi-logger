# Basic Usage Examples

**Get started with Fapilog - Perfect for new users**

This section covers fundamental Fapilog usage patterns that every developer should know. Start here if you're new to Fapilog or structured logging.

---

## 📚 What You'll Learn

- **Basic Setup** - Minimal configuration to get started
- **Environment Configuration** - Different settings for dev/staging/prod
- **Output Formats** - JSON, pretty, and auto formats
- **Logging Levels** - Control what gets logged

---

## 🚀 Examples

### 01 - Basic Setup

**Minimal setup to get started with structured logging**

```python
#!/usr/bin/env python3
"""
Example 1: Basic Setup

This example demonstrates the minimal setup required to use fapilog.
It shows how to configure logging and use the logger for basic operations.
"""

from fapilog import configure_logging, log


def main():
    """Demonstrate basic fapilog setup and usage."""
    print("=== Basic Setup Example ===\n")

    # Step 1: Configure logging with default settings
    print("1. Configuring logging with default settings...")
    configure_logging()
    print("✅ Logging configured successfully!\n")

    # Step 2: Basic logging operations
    print("2. Basic logging operations:")
    print("-" * 40)

    # Info level logging
    log.info("Application started", version="1.0.0", environment="development")

    # Warning level logging
    log.warning("Deprecated feature used", feature="old_api", replacement="new_api")

    # Error level logging
    log.error(
        "Failed to connect to database",
        database="postgres",
        error="connection timeout",
        retry_count=3,
    )

    # Debug level logging (won't show with default INFO level)
    log.debug("Debug information", debug_data="some debug info")

    # Structured logging with multiple fields
    log.info(
        "User action completed",
        user_id="user_123",
        action="login",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0...",
        duration_ms=45.2,
    )

    print("\n3. Key features demonstrated:")
    print("✅ Structured JSON logging")
    print("✅ Multiple field support")
    print("✅ Log levels (INFO, WARNING, ERROR)")
    print("✅ Automatic timestamp and log level")
    print("✅ Hostname and process ID enrichment")
    print("✅ Trace ID generation (when used with FastAPI)")


if __name__ == "__main__":
    main()
```

**Key Features:**

- ✅ Structured JSON logging
- ✅ Multiple field support
- ✅ Automatic timestamp and enrichment
- ✅ Hostname and process ID

**Sample Output:**

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "info",
  "event": "Application started",
  "hostname": "server-01",
  "pid": 12345,
  "version": "1.0.0",
  "environment": "development"
}
```

---

### 02 - Environment Configuration

**Configure logging using environment variables for different deployments**

```python
#!/usr/bin/env python3
"""
Example 2: Environment Configuration

This example demonstrates how to configure fapilog using environment variables
and programmatic settings. It shows different configuration approaches.
"""

import os

from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings


def demonstrate_environment_config():
    """Show how environment variables control logging behavior."""
    print("=== Environment Configuration Example ===\n")

    # Method 1: Using environment variables
    print("1. Configuration via environment variables:")
    print("-" * 50)

    # Set environment variables for this example
    os.environ["FAPILOG_LEVEL"] = "DEBUG"
    os.environ["FAPILOG_JSON_CONSOLE"] = "json"
    os.environ["FAPILOG_ENABLE_RESOURCE_METRICS"] = "true"

    # Configure with environment variables
    configure_logging()

    print("Environment variables set:")
    print("  FAPILOG_LEVEL=DEBUG")
    print("  FAPILOG_JSON_CONSOLE=json")
    print("  FAPILOG_ENABLE_RESOURCE_METRICS=true")
    print()

    # Log some events to see the configuration
    log.debug("Debug message with environment config")
    log.info("Info message with environment config")
    log.warning("Warning message with environment config")

    print("\n2. Configuration via LoggingSettings:")
    print("-" * 50)

    # Method 2: Using LoggingSettings programmatically
    settings = LoggingSettings(
        level="INFO",
        json_console="pretty",  # Pretty output for development
        enable_resource_metrics=False,  # Disable resource metrics
        queue_enabled=False,  # Disable queue for simpler example
    )

    # Configure with settings
    configure_logging(settings=settings)

    print("Programmatic settings:")
    print("  level=INFO")
    print("  json_console=pretty")
    print("  enable_resource_metrics=False")
    print("  queue_enabled=False")
    print()

    # Log some events to see the new configuration
    log.info("Info message with programmatic config")
    log.warning("Warning message with programmatic config")
    log.error("Error message with programmatic config")


def demonstrate_development_vs_production():
    """Show different configurations for development vs production."""
    print("\n4. Development vs Production Configuration:")
    print("-" * 50)

    # Development configuration
    print("Development Configuration:")
    dev_settings = LoggingSettings(
        level="DEBUG",
        json_console="pretty",  # Pretty output for readability
        enable_resource_metrics=False,  # Disable for performance
        queue_enabled=False,  # Disable queue for simplicity
    )
    configure_logging(settings=dev_settings)
    log.info("Development environment log", env="development", debug_enabled=True)

    # Production configuration
    print("\nProduction Configuration:")
    prod_settings = LoggingSettings(
        level="INFO",
        json_console="json",  # JSON for log aggregation
        enable_resource_metrics=True,  # Enable for monitoring
        queue_enabled=True,  # Enable queue for performance
        queue_maxsize=1000,
        queue_overflow="drop",
    )
    configure_logging(settings=prod_settings)
    log.info("Production environment log", env="production", monitoring_enabled=True)


def main():
    """Run the environment configuration examples."""
    demonstrate_environment_config()
    demonstrate_development_vs_production()

    print("\n" + "=" * 60)
    print("Key takeaways:")
    print("✅ Environment variables provide easy configuration")
    print("✅ LoggingSettings allow programmatic control")
    print("✅ Different configs for dev vs production")
    print("✅ All settings have sensible defaults")
    print("✅ Configuration is validated automatically")


if __name__ == "__main__":
    main()
```

**Key Features:**

- ✅ Environment variable configuration
- ✅ Programmatic settings control
- ✅ Development vs production patterns
- ✅ Automatic validation

**Available Environment Variables:**

```bash
FAPILOG_LEVEL              # Logging level (DEBUG, INFO, WARN, ERROR, CRITICAL)
FAPILOG_JSON_CONSOLE       # Console format (auto, json, pretty)
FAPILOG_ENABLE_RESOURCE_METRICS # Enable memory/CPU metrics (true/false)
FAPILOG_QUEUE_ENABLED      # Enable async queue (true/false)
FAPILOG_QUEUE_MAXSIZE      # Maximum queue size (default: 1000)
FAPILOG_QUEUE_OVERFLOW     # Overflow strategy (drop, block, sample)
FAPILOG_SAMPLING_RATE      # Sampling rate (0.0 to 1.0)
FAPILOG_REDACT_PATTERNS    # Comma-separated regex patterns to redact
FAPILOG_SINKS              # Comma-separated list of sinks (stdout, loki)
```

---

### 03 - Output Formats

**Configure different output formats for different environments**

```python
from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings

# JSON format (production)
json_settings = LoggingSettings(json_console="json")
configure_logging(settings=json_settings)
log.info("JSON format example", user_id="123", action="login")

# Pretty format (development)
pretty_settings = LoggingSettings(json_console="pretty")
configure_logging(settings=pretty_settings)
log.info("Pretty format example", user_id="123", action="login")

# Auto format (detects TTY)
auto_settings = LoggingSettings(json_console="auto")
configure_logging(settings=auto_settings)
log.info("Auto format example", user_id="123", action="login")
```

**Output Comparison:**

**JSON Format (Production):**

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "info",
  "event": "JSON format example",
  "user_id": "123",
  "action": "login"
}
```

**Pretty Format (Development):**

```
2024-01-15 10:30:45.123 | INFO | JSON format example | user_id=123 action=login
```

**Key Features:**

- ✅ JSON format for production log aggregation
- ✅ Pretty format for development readability
- ✅ Auto format detection based on TTY

---

### 04 - Logging Levels

**Configure and use different logging levels effectively**

```python
from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings

# Configure for development (all levels)
dev_settings = LoggingSettings(level="DEBUG")
configure_logging(settings=dev_settings)

# All levels will be logged
log.debug("Debug information", debug_data="some debug info")
log.info("General information", user_count=100)
log.warning("Warning message", deprecated_feature="old_api")
log.error("Error occurred", error_code=500, error_message="timeout")

# Configure for production (INFO and above)
prod_settings = LoggingSettings(level="INFO")
configure_logging(settings=prod_settings)

# Only INFO, WARNING, ERROR, CRITICAL will be logged
log.debug("This won't be logged in production")
log.info("This will be logged")
log.error("This will be logged")
```

**Level Hierarchy:**

```
DEBUG < INFO < WARNING < ERROR < CRITICAL
```

**Key Features:**

- ✅ Level-based filtering
- ✅ Environment-specific levels
- ✅ Performance optimization (higher levels = fewer logs)

---

## 🎯 Next Steps

Ready for more advanced patterns?

### 🔧 **Application Integration**

- **[FastAPI Examples](../fastapi/index.md)** - Web application logging patterns
- **[Production Examples](../production/index.md)** - High-performance configurations

### 🚀 **Advanced Features**

- **[Advanced Patterns](../advanced/index.md)** - Security, tracing, enrichment
- **[Sink Development](../sinks/index.md)** - Custom output destinations

### 📖 **Complete Guide**

- **[User Guide](../../user-guide.md)** - Step-by-step tutorials
- **[Configuration Guide](../../config.md)** - Complete configuration reference

---

## 💡 Tips for Beginners

1. **Start Simple** - Use the basic setup first, then add complexity
2. **Use Environment Variables** - Different configs for different environments
3. **Choose the Right Format** - Pretty for dev, JSON for production
4. **Set Appropriate Levels** - DEBUG for dev, INFO+ for production

Ready to dive deeper? Check out the [FastAPI integration examples](../fastapi/index.md)!
