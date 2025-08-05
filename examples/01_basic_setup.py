#!/usr/bin/env python3
"""
Example 1: Basic Setup

This example demonstrates the minimal setup required to use fapilog.
It shows how to configure logging and use the logger for basic operations.
"""

from fapilog import configure_logging, log
from fapilog.config.factory import ConfigurationFactory


def main():
    """Demonstrate basic fapilog setup and usage."""
    print("=== Basic Setup Example ===\n")

    # Step 1: Configure logging using the factory for development
    print("1. Configuring logging using ConfigurationFactory for development...")
    config = ConfigurationFactory.development()
    configure_logging(config)
    print("✅ Logging configured with development preset!\n")

    # Alternative: you can still use default settings
    print("   Alternative - using default settings:")
    print("   configure_logging()  # Uses default configuration")
    print("   But factory presets are recommended for consistency!\n")

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
    print("✅ ConfigurationFactory for consistent presets")
    print("✅ Development preset (DEBUG level, pretty output)")
    print("✅ Structured JSON logging")
    print("✅ Multiple field support")
    print("✅ Log levels (INFO, WARNING, ERROR)")
    print("✅ Automatic timestamp and log level")
    print("✅ Hostname and process ID enrichment")
    print("✅ Trace ID generation (when used with FastAPI)")

    print("\n4. Available factory presets:")
    presets = ConfigurationFactory.get_available_presets()
    for name, description in presets.items():
        print(f"   • {name}: {description}")


if __name__ == "__main__":
    main()
