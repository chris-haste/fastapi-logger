#!/usr/bin/env python3
"""
Example 24: Enhanced Configuration Factory

This example demonstrates the enhanced ConfigurationFactory that supports:
- Environment variable overrides for factory presets
- Partial configuration updates with deep merging
- Validation of factory-generated configurations
- Configuration health checks and warnings
"""

import os

from fapilog import configure_logging, log
from fapilog.config.enhanced_factory import EnhancedConfigurationFactory
from fapilog.config.settings import LoggingSettings


def demonstrate_environment_variable_support():
    """Demonstrate environment variable support in factory presets."""
    print("=== Environment Variable Support ===")
    print()

    # Set environment variables to override factory defaults
    os.environ["FAPILOG_FACTORY_DEVELOPMENT_LEVEL"] = "INFO"
    os.environ["FAPILOG_FACTORY_DEVELOPMENT_QUEUE_MAXSIZE"] = "500"
    os.environ["FAPILOG_FACTORY_DEVELOPMENT_SECURITY_ENABLE_AUTO_REDACT_PII"] = "true"

    print("Environment variables set:")
    print("  FAPILOG_FACTORY_DEVELOPMENT_LEVEL=INFO")
    print("  FAPILOG_FACTORY_DEVELOPMENT_QUEUE_MAXSIZE=500")
    print("  FAPILOG_FACTORY_DEVELOPMENT_SECURITY_ENABLE_AUTO_REDACT_PII=true")
    print()

    # Create development preset with environment overrides
    config = EnhancedConfigurationFactory.development()

    print("Development preset with environment overrides:")
    print(f"  Level: {config.level} (was DEBUG, now INFO)")
    print(f"  Queue maxsize: {config.queue.maxsize} (was 100, now 500)")
    print(
        f"  PII redaction: {config.security.enable_auto_redact_pii} (was False, now True)"
    )
    print(f"  Console format: {config.sinks.json_console} (unchanged: pretty)")
    print()

    # Configure logging with the enhanced preset
    configure_logging(settings=config)
    log.info("Logging configured with environment-aware development preset")

    # Clean up environment variables
    del os.environ["FAPILOG_FACTORY_DEVELOPMENT_LEVEL"]
    del os.environ["FAPILOG_FACTORY_DEVELOPMENT_QUEUE_MAXSIZE"]
    del os.environ["FAPILOG_FACTORY_DEVELOPMENT_SECURITY_ENABLE_AUTO_REDACT_PII"]


def demonstrate_partial_updates():
    """Demonstrate partial configuration updates."""
    print("=== Partial Configuration Updates ===")
    print()

    # Create custom configuration with partial updates
    config = EnhancedConfigurationFactory.custom(
        base_preset="production",
        partial_updates={
            "queue": {"maxsize": 2000, "batch_size": 25, "overflow": "drop"},
            "security": {"enable_auto_redact_pii": False, "redact_level": "ERROR"},
            "metrics": {"prometheus_port": 9091},
        },
    )

    print("Production preset with partial updates:")
    print(f"  Level: {config.level} (production default: INFO)")
    print(f"  Queue maxsize: {config.queue.maxsize} (updated: 2000)")
    print(f"  Queue batch_size: {config.queue.batch_size} (updated: 25)")
    print(f"  Queue overflow: {config.queue.overflow} (updated: drop)")
    print(f"  PII redaction: {config.security.enable_auto_redact_pii} (updated: False)")
    print(f"  Redact level: {config.security.redact_level} (updated: ERROR)")
    print(f"  Prometheus port: {config.metrics.prometheus_port} (updated: 9091)")
    print(f"  Console format: {config.sinks.json_console} (production default: json)")
    print()

    # Configure logging with the custom preset
    configure_logging(settings=config)
    log.info("Logging configured with partial updates")


def demonstrate_precedence_rules():
    """Demonstrate configuration precedence rules."""
    print("=== Configuration Precedence Rules ===")
    print()

    # Set environment variable
    os.environ["FAPILOG_FACTORY_PRODUCTION_LEVEL"] = "WARNING"
    os.environ["FAPILOG_FACTORY_PRODUCTION_QUEUE_MAXSIZE"] = "1500"

    print("Environment variables set:")
    print("  FAPILOG_FACTORY_PRODUCTION_LEVEL=WARNING")
    print("  FAPILOG_FACTORY_PRODUCTION_QUEUE_MAXSIZE=1500")
    print()

    # Override with programmatic parameters (highest precedence)
    config = EnhancedConfigurationFactory.production(
        level="DEBUG",  # Overrides environment variable
        queue={"maxsize": 3000},  # Overrides environment variable
    )

    print("Production preset with programmatic overrides:")
    print(f"  Level: {config.level} (programmatic override: DEBUG)")
    print(f"  Queue maxsize: {config.queue.maxsize} (programmatic override: 3000)")
    print()

    # Clean up environment variables
    del os.environ["FAPILOG_FACTORY_PRODUCTION_LEVEL"]
    del os.environ["FAPILOG_FACTORY_PRODUCTION_QUEUE_MAXSIZE"]


def demonstrate_health_checks():
    """Demonstrate configuration health checks."""
    print("=== Configuration Health Checks ===")
    print()

    # Create configurations that should trigger warnings and recommendations
    problematic_config = LoggingSettings(
        level="DEBUG",
        queue=LoggingSettings().queue.model_copy(
            update={
                "maxsize": 50,  # Very small queue
                "overflow": "block",  # Blocking with small queue
            }
        ),
        metrics=LoggingSettings().metrics.model_copy(
            update={
                "enabled": True,  # Metrics with DEBUG level
                "prometheus_enabled": True,
                "prometheus_port": 8000,  # Common web server port
            }
        ),
        sinks=LoggingSettings().sinks.model_copy(
            update={
                "sampling_rate": 0.05  # Very low sampling
            }
        ),
    )

    print("Configuration with potential issues:")
    print(f"  Level: {problematic_config.level}")
    print(f"  Queue maxsize: {problematic_config.queue.maxsize}")
    print(f"  Queue overflow: {problematic_config.queue.overflow}")
    print(f"  Metrics enabled: {problematic_config.metrics.enabled}")
    print(f"  Prometheus port: {problematic_config.metrics.prometheus_port}")
    print(f"  Sampling rate: {problematic_config.sinks.sampling_rate}")
    print()

    # Perform health check
    health_results = EnhancedConfigurationFactory.health_check(problematic_config)

    print("Health Check Results:")
    print(f"  Valid: {health_results['valid']}")
    print(f"  Warnings: {len(health_results['warnings'])}")
    print(f"  Recommendations: {len(health_results['recommendations'])}")
    print()

    if health_results["warnings"]:
        print("Warnings:")
        for warning in health_results["warnings"]:
            print(f"  ⚠️  {warning}")
        print()

    if health_results["recommendations"]:
        print("Recommendations:")
        for recommendation in health_results["recommendations"]:
            print(f"  💡 {recommendation}")
        print()


def demonstrate_environment_variable_documentation():
    """Demonstrate getting available environment variables."""
    print("=== Environment Variable Documentation ===")
    print()

    presets = ["development", "production", "testing", "high_performance", "monitoring"]

    for preset in presets:
        print(f"{preset.upper()} preset environment variables:")
        env_vars = EnhancedConfigurationFactory.get_environment_variables(preset)

        for var_name, description in env_vars.items():
            print(f"  {var_name}: {description}")
        print()


def demonstrate_validation():
    """Demonstrate configuration validation."""
    print("=== Configuration Validation ===")
    print()

    # Valid configuration should work
    try:
        EnhancedConfigurationFactory.development()
        print("✅ Valid development configuration created successfully")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

    # Invalid configuration should raise error
    try:
        EnhancedConfigurationFactory.development(level="INVALID_LEVEL")
        print("❌ Invalid configuration should have raised an error")
    except Exception as e:
        print(f"✅ Invalid configuration correctly rejected: {type(e).__name__}")
    print()


def main():
    """Run all enhanced factory examples."""
    print("=" * 80)
    print("ENHANCED CONFIGURATION FACTORY EXAMPLES")
    print("=" * 80)
    print()

    demonstrate_environment_variable_support()
    print()

    demonstrate_partial_updates()
    print()

    demonstrate_precedence_rules()
    print()

    demonstrate_health_checks()
    print()

    demonstrate_environment_variable_documentation()
    print()

    demonstrate_validation()
    print()

    print("=" * 80)
    print("Enhanced Configuration Factory examples completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
