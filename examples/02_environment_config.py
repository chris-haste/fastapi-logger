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

    print("\n3. Available environment variables:")
    print("-" * 50)
    print(
        "FAPILOG_LEVEL              - Logging level (DEBUG, INFO, WARN, ERROR, CRITICAL)"
    )
    print("FAPILOG_JSON_CONSOLE       - Console format (auto, json, pretty)")
    print("FAPILOG_ENABLE_RESOURCE_METRICS - Enable memory/CPU metrics (true/false)")
    print("FAPILOG_QUEUE_ENABLED      - Enable async queue (true/false)")
    print("FAPILOG_QUEUE_MAXSIZE      - Maximum queue size (default: 1000)")
    print("FAPILOG_QUEUE_OVERFLOW     - Overflow strategy (drop, block, sample)")
    print("FAPILOG_SAMPLING_RATE      - Sampling rate (0.0 to 1.0)")
    print("FAPILOG_REDACT_PATTERNS    - Comma-separated regex patterns to redact")
    print("FAPILOG_SINKS              - Comma-separated list of sinks (stdout, loki)")


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
