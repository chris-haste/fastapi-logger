#!/usr/bin/env python3
"""
Example 23: Configuration Factory Patterns

This example demonstrates how to use the ConfigurationFactory to create
environment-specific logging configurations with optimal presets.
"""

import asyncio
import os
import time

from fapilog import configure_logging, log
from fapilog.config.factory import ConfigurationFactory
from fapilog.config.queue_settings import QueueSettings
from fapilog.config.security_settings import SecuritySettings
from fapilog.config.sink_settings import SinkSettings


def demonstrate_preset(preset_name: str, config_func: callable) -> None:
    """Demonstrate a specific configuration preset."""
    print(f"\n=== {preset_name.upper()} PRESET ===")

    # Get the configuration
    config = config_func()

    print("📋 Configuration details:")
    print(f"   • Log level: {config.level}")
    print(f"   • Console format: {config.sinks.json_console}")
    print(f"   • Queue enabled: {config.queue.enabled}")
    if config.queue.enabled:
        print(f"   • Queue size: {config.queue.maxsize}")
        print(f"   • Batch size: {config.queue.batch_size}")
        print(f"   • Overflow strategy: {config.queue.overflow}")
    print(f"   • Resource metrics: {config.enable_resource_metrics}")
    print(f"   • PII redaction: {config.security.enable_auto_redact_pii}")
    print(f"   • Metrics collection: {config.metrics.enabled}")

    # Configure logging with this preset
    configure_logging(config)

    print(f"\n📝 Sample logs for {preset_name} preset:")

    # Generate sample logs
    log.debug("Debug message", preset=preset_name, details="verbose debug info")
    log.info("Info message", preset=preset_name, user_id="user123")
    log.warning("Warning message", preset=preset_name, deprecated_feature="old_api")
    log.error("Error message", preset=preset_name, error_code="E001")

    # Sample with sensitive data (for PII redaction demo)
    log.info(
        "User action",
        preset=preset_name,
        email="user@example.com",
        password="secret123",  # Will be redacted if PII is enabled
        credit_card="1234-5678-9012-3456",  # Will be redacted if PII is enabled
    )


def demonstrate_custom_configurations() -> None:
    """Demonstrate custom configurations based on presets."""
    print("\n=== CUSTOM CONFIGURATIONS ===")

    # Example 1: Production with custom sinks
    print("\n1. Production with custom file sink:")
    config = ConfigurationFactory.production(
        sinks=SinkSettings(sinks=["stdout", "file:///tmp/app.log"], json_console="json")
    )
    configure_logging(config)
    log.info("Production log with file output", custom_config="production_with_file")

    # Example 2: Testing with custom log level
    print("\n2. Testing with ERROR level only:")
    config = ConfigurationFactory.testing(level="ERROR")
    configure_logging(config)
    log.info("This won't show", level_test="info")  # Won't show
    log.error("This will show", level_test="error")  # Will show

    # Example 3: High-performance with less sampling
    print("\n3. High-performance with reduced sampling:")
    config = ConfigurationFactory.high_performance(
        sinks=SinkSettings(sampling_rate=0.5)  # Sample 50% instead of 10%
    )
    configure_logging(config)
    for i in range(5):
        log.warning(f"High-performance log {i}", iteration=i)

    # Example 4: Custom configuration based on existing preset
    print("\n4. Custom configuration based on development preset:")
    config = ConfigurationFactory.custom(
        base_preset="development",
        level="INFO",
        queue=QueueSettings(enabled=True, maxsize=500),
        security=SecuritySettings(enable_auto_redact_pii=True),
    )
    configure_logging(config)
    log.info(
        "Custom config log",
        base="development",
        password="hidden123",  # Will be redacted
        public_info="visible",
    )


def demonstrate_environment_based_config() -> None:
    """Demonstrate environment-based configuration selection."""
    print("\n=== ENVIRONMENT-BASED CONFIGURATION ===")

    # Simulate different environments
    environments = {
        "development": ConfigurationFactory.development,
        "testing": ConfigurationFactory.testing,
        "production": ConfigurationFactory.production,
        "monitoring": ConfigurationFactory.monitoring,
    }

    # Get environment from environment variable or default to development
    env = os.getenv("APP_ENV", "development")

    print(f"🌍 Current environment: {env}")
    print(f"📋 Using {env} configuration preset")

    if env in environments:
        config = environments[env]()
        configure_logging(config)

        log.info(
            "Application started",
            environment=env,
            config_preset=env,
            startup_time=time.time(),
        )

        # Log some application events
        log.info("Database connection established", database="postgres", env=env)
        log.info("Cache warming completed", cache_size="100MB", env=env)
        log.info("Ready to serve requests", port=8000, env=env)

    else:
        print(f"❌ Unknown environment: {env}")
        print(f"Available environments: {list(environments.keys())}")


def demonstrate_preset_comparison() -> None:
    """Compare different presets side by side."""
    print("\n=== PRESET COMPARISON ===")

    presets = {
        "development": ConfigurationFactory.development(),
        "production": ConfigurationFactory.production(),
        "testing": ConfigurationFactory.testing(),
        "high_performance": ConfigurationFactory.high_performance(),
        "monitoring": ConfigurationFactory.monitoring(),
    }

    print("\n📊 Preset Comparison Table:")
    print("=" * 80)
    print(
        f"{'Preset':<15} {'Level':<8} {'Queue':<8} {'PII':<8} {'Metrics':<8} {'Console':<10}"
    )
    print("=" * 80)

    for name, config in presets.items():
        queue_info = f"{config.queue.maxsize}" if config.queue.enabled else "Off"
        pii_info = "On" if config.security.enable_auto_redact_pii else "Off"
        metrics_info = "On" if config.metrics.enabled else "Off"

        print(
            f"{name:<15} {config.level:<8} {queue_info:<8} {pii_info:<8} {metrics_info:<8} {config.sinks.json_console:<10}"
        )

    print("=" * 80)


async def demonstrate_async_logging() -> None:
    """Demonstrate async logging with different presets."""
    print("\n=== ASYNC LOGGING WITH PRESETS ===")

    # Configure with monitoring preset for async operations
    config = ConfigurationFactory.monitoring(
        queue=QueueSettings(
            enabled=True, maxsize=1000, batch_size=10, batch_timeout=0.5
        )
    )
    configure_logging(config)

    print("🔄 Performing async operations with monitoring preset...")

    async def async_operation(operation_id: int) -> None:
        """Simulate an async operation with logging."""
        log.info("Operation started", operation_id=operation_id, status="starting")

        # Simulate some work
        await asyncio.sleep(0.1)

        if operation_id % 3 == 0:
            log.error("Operation failed", operation_id=operation_id, error="timeout")
        else:
            log.info("Operation completed", operation_id=operation_id, status="success")

    # Run multiple async operations
    tasks = [async_operation(i) for i in range(10)]
    await asyncio.gather(*tasks)

    log.info("All async operations completed", total_operations=10)


def main():
    """Main demonstration function."""
    print("🏭 ConfigurationFactory Examples")
    print("=" * 50)

    # Show available presets
    print("\n📋 Available Configuration Presets:")
    presets = ConfigurationFactory.get_available_presets()
    for name, description in presets.items():
        print(f"   • {name}: {description}")

    # Demonstrate each preset
    demonstrate_preset("development", ConfigurationFactory.development)
    demonstrate_preset("production", ConfigurationFactory.production)
    demonstrate_preset("testing", ConfigurationFactory.testing)
    demonstrate_preset("high_performance", ConfigurationFactory.high_performance)
    demonstrate_preset("monitoring", ConfigurationFactory.monitoring)

    # Show custom configurations
    demonstrate_custom_configurations()

    # Show environment-based configuration
    demonstrate_environment_based_config()

    # Show preset comparison
    demonstrate_preset_comparison()

    # Demonstrate async logging
    print("\n🔄 Running async logging demonstration...")
    asyncio.run(demonstrate_async_logging())

    print("\n✅ Configuration Factory demonstration completed!")
    print("\n💡 Key Takeaways:")
    print("   • Use ConfigurationFactory for consistent, tested configurations")
    print("   • Choose presets based on your environment and needs")
    print("   • Customize presets with overrides for specific requirements")
    print("   • Use environment variables to select configurations")
    print("   • Monitor logs in production with the monitoring preset")


if __name__ == "__main__":
    main()
