"""Tests for EnhancedConfigurationFactory functionality."""

import os
from typing import Any

import pytest

from fapilog.config.enhanced_factory import EnhancedConfigurationFactory
from fapilog.config.factory import ConfigurationFactory
from fapilog.config.settings import LoggingSettings
from fapilog.exceptions import ConfigurationError


class TestEnhancedConfigurationFactory:
    """Test suite for EnhancedConfigurationFactory."""

    def setup_method(self):
        """Clear environment variables before each test."""
        # Remove any existing FAPILOG_FACTORY_ variables
        env_vars_to_remove = [
            key for key in os.environ.keys() if key.startswith("FAPILOG_FACTORY_")
        ]
        for key in env_vars_to_remove:
            del os.environ[key]

    def test_development_preset_with_environment_variables(self):
        """Test development preset with environment variable overrides."""
        # Clear any existing environment variables that might interfere
        env_vars_to_remove = [
            key for key in os.environ.keys() if key.startswith("FAPILOG_")
        ]
        for key in env_vars_to_remove:
            del os.environ[key]

        # Set specific environment variables for this test
        os.environ["FAPILOG_FACTORY_DEVELOPMENT_LEVEL"] = "INFO"
        os.environ["FAPILOG_FACTORY_DEVELOPMENT_QUEUE_MAXSIZE"] = "500"
        os.environ["FAPILOG_FACTORY_DEVELOPMENT_SECURITY_ENABLE_AUTO_REDACT_PII"] = (
            "true"
        )

        # Test enhanced factory
        config = EnhancedConfigurationFactory.development()

        # Verify environment variables were applied correctly
        assert config.level == "INFO"  # Overridden from DEBUG
        assert config.queue.maxsize == 500  # Overridden from 100
        assert config.security.enable_auto_redact_pii is True  # Overridden from False

        # Test original factory (should not be affected by environment variables)
        original_config = ConfigurationFactory.development()
        assert original_config.level == "DEBUG"  # Should be original default
        assert original_config.queue.maxsize == 100  # Should be original default
        assert (
            original_config.security.enable_auto_redact_pii is False
        )  # Should be original default

        # Clean up
        del os.environ["FAPILOG_FACTORY_DEVELOPMENT_LEVEL"]
        del os.environ["FAPILOG_FACTORY_DEVELOPMENT_QUEUE_MAXSIZE"]
        del os.environ["FAPILOG_FACTORY_DEVELOPMENT_SECURITY_ENABLE_AUTO_REDACT_PII"]

    def test_production_preset_with_environment_variables(self):
        """Test production preset with environment variable overrides."""
        # Set environment variables
        os.environ["FAPILOG_FACTORY_PRODUCTION_LEVEL"] = "DEBUG"
        os.environ["FAPILOG_FACTORY_PRODUCTION_QUEUE_MAXSIZE"] = "2000"
        os.environ["FAPILOG_FACTORY_PRODUCTION_METRICS_ENABLED"] = "false"

        config = EnhancedConfigurationFactory.production()

        # Verify environment variables were applied
        assert config.level == "DEBUG"  # Overridden from INFO
        assert config.queue.maxsize == 2000  # Overridden from 1000
        assert config.metrics.enabled is False  # Overridden from True

        # Verify other defaults are preserved
        assert config.sinks.json_console == "json"
        assert config.security.enable_auto_redact_pii is True

    def test_environment_variable_precedence(self):
        """Test that programmatic overrides take precedence over environment variables."""
        # Set environment variable
        os.environ["FAPILOG_FACTORY_DEVELOPMENT_LEVEL"] = "INFO"

        # Override with programmatic parameter
        config = EnhancedConfigurationFactory.development(level="WARNING")

        # Programmatic override should win
        assert config.level == "WARNING"  # Not INFO from environment

    def test_partial_updates_in_custom_method(self):
        """Test partial updates in custom method."""
        config = EnhancedConfigurationFactory.custom(
            base_preset="production",
            partial_updates={
                "queue": {"maxsize": 2000, "batch_size": 20},
                "security": {"enable_auto_redact_pii": False},
            },
        )

        # Verify partial updates were applied
        assert config.queue.maxsize == 2000
        assert config.queue.batch_size == 20
        assert config.security.enable_auto_redact_pii is False

        # Verify other production defaults are preserved
        assert config.level == "INFO"
        assert config.sinks.json_console == "json"

    def test_custom_method_with_overrides(self):
        """Test custom method with both partial updates and overrides."""
        config = EnhancedConfigurationFactory.custom(
            base_preset="development",
            partial_updates={"queue": {"maxsize": 500}},
            level="WARNING",  # Override
        )

        # Verify partial updates
        assert config.queue.maxsize == 500

        # Verify override takes precedence
        assert config.level == "WARNING"

        # Verify other development defaults
        assert config.queue.batch_size == 1
        assert config.sinks.json_console == "pretty"

    def test_environment_variable_type_parsing(self):
        """Test that environment variables are parsed to correct types."""
        # Set environment variables with different types
        os.environ["FAPILOG_FACTORY_DEVELOPMENT_QUEUE_MAXSIZE"] = "500"  # int
        os.environ["FAPILOG_FACTORY_DEVELOPMENT_SINKS_SAMPLING_RATE"] = "0.5"  # float
        os.environ["FAPILOG_FACTORY_DEVELOPMENT_SECURITY_ENABLE_AUTO_REDACT_PII"] = (
            "true"  # bool
        )
        os.environ["FAPILOG_FACTORY_DEVELOPMENT_QUEUE_OVERFLOW"] = "drop"  # str

        config = EnhancedConfigurationFactory.development()

        # Verify types are correct
        assert isinstance(config.queue.maxsize, int)
        assert config.queue.maxsize == 500

        assert isinstance(config.sinks.sampling_rate, float)
        assert config.sinks.sampling_rate == 0.5

        assert isinstance(config.security.enable_auto_redact_pii, bool)
        assert config.security.enable_auto_redact_pii is True

        assert isinstance(config.queue.overflow, str)
        assert config.queue.overflow == "drop"

    def test_nested_environment_variables(self):
        """Test nested environment variable parsing."""
        # Set nested environment variables
        os.environ["FAPILOG_FACTORY_DEVELOPMENT_QUEUE_MAXSIZE"] = "750"
        os.environ["FAPILOG_FACTORY_DEVELOPMENT_SECURITY_REDACT_LEVEL"] = "ERROR"
        os.environ["FAPILOG_FACTORY_DEVELOPMENT_METRICS_PROMETHEUS_PORT"] = "9091"

        config = EnhancedConfigurationFactory.development()

        # Verify nested values are set correctly
        assert config.queue.maxsize == 750
        assert config.security.redact_level == "ERROR"
        assert config.metrics.prometheus_port == 9091

    def test_invalid_base_preset(self):
        """Test that invalid base preset raises ValueError."""
        with pytest.raises(ValueError, match="Invalid base_preset"):
            EnhancedConfigurationFactory.custom(base_preset="invalid_preset")

    def test_health_check_warnings(self):
        """Test health check functionality."""
        # Create a configuration that should trigger warnings
        config = LoggingSettings(
            queue=LoggingSettings().queue.model_copy(update={"maxsize": 50}),
            level="DEBUG",
            metrics=LoggingSettings().metrics.model_copy(update={"enabled": True}),
            sinks=LoggingSettings().sinks.model_copy(update={"sampling_rate": 0.05}),
        )

        health_results = EnhancedConfigurationFactory.health_check(config)

        # Verify warnings are generated
        assert health_results["valid"] is True
        assert len(health_results["warnings"]) > 0

        # Check for specific warnings
        warning_messages = [w.lower() for w in health_results["warnings"]]
        assert any("queue maxsize" in msg for msg in warning_messages)
        assert any("debug level with metrics" in msg for msg in warning_messages)
        assert any("low sampling rate" in msg for msg in warning_messages)

    def test_health_check_recommendations(self):
        """Test health check recommendations."""
        # Create a configuration that should trigger recommendations
        config = LoggingSettings(
            queue=LoggingSettings().queue.model_copy(
                update={"maxsize": 500, "overflow": "block"}
            ),
            metrics=LoggingSettings().metrics.model_copy(
                update={"prometheus_enabled": True, "prometheus_port": 8000}
            ),
        )

        health_results = EnhancedConfigurationFactory.health_check(config)

        # Verify recommendations are generated
        assert health_results["valid"] is True
        assert len(health_results["recommendations"]) > 0

        # Check for specific recommendations
        rec_messages = [r.lower() for r in health_results["recommendations"]]
        assert any("queue maxsize" in msg for msg in rec_messages)
        # The actual message is "Consider using a different port for Prometheus metrics (8000 is common for web servers)"
        assert any("different port" in msg for msg in rec_messages)

    def test_get_environment_variables(self):
        """Test getting available environment variables for a preset."""
        env_vars: dict[str, str] = (
            EnhancedConfigurationFactory.get_environment_variables("development")
        )

        # Verify environment variables are documented
        assert "FAPILOG_FACTORY_DEVELOPMENT_LEVEL" in env_vars
        assert "FAPILOG_FACTORY_DEVELOPMENT_QUEUE_MAXSIZE" in env_vars
        assert "FAPILOG_FACTORY_DEVELOPMENT_SECURITY_ENABLE_AUTO_REDACT_PII" in env_vars

        # Verify descriptions are provided
        for _var_name, description in env_vars.items():
            assert isinstance(description, str)
            assert len(description) > 0

    def test_validation_of_factory_configurations(self):
        """Test that factory-generated configurations are validated."""
        # This should work without errors
        config = EnhancedConfigurationFactory.development()
        assert isinstance(config, LoggingSettings)

        # Test with invalid overrides (should raise ConfigurationError)
        with pytest.raises(ConfigurationError):
            EnhancedConfigurationFactory.development(level="INVALID_LEVEL")

    def test_merge_configurations_precedence(self):
        """Test that configuration merging follows correct precedence."""
        # Set environment variable
        os.environ["FAPILOG_FACTORY_DEVELOPMENT_LEVEL"] = "INFO"

        # Override with programmatic parameter
        config = EnhancedConfigurationFactory.development(level="WARNING")

        # Programmatic override should take precedence
        assert config.level == "WARNING"

    def test_apply_partial_updates(self):
        """Test applying partial updates to configuration."""
        base_config = LoggingSettings()

        partial_updates = {
            "queue": {"maxsize": 2000, "batch_size": 20},
            "security": {"enable_auto_redact_pii": True},
        }

        updated_config = EnhancedConfigurationFactory._apply_partial_updates(
            base_config, partial_updates
        )

        # Verify partial updates were applied
        assert updated_config.queue.maxsize == 2000
        assert updated_config.queue.batch_size == 20
        assert updated_config.security.enable_auto_redact_pii is True

        # Verify other settings are unchanged
        assert updated_config.level == base_config.level
        assert updated_config.sinks.json_console == base_config.sinks.json_console

    def test_parse_env_value_types(self):
        """Test environment value parsing for different types."""
        # Test boolean parsing
        assert EnhancedConfigurationFactory._parse_env_value("true") is True
        assert EnhancedConfigurationFactory._parse_env_value("false") is False
        assert EnhancedConfigurationFactory._parse_env_value("TRUE") is True
        assert EnhancedConfigurationFactory._parse_env_value("FALSE") is False

        # Test integer parsing
        assert EnhancedConfigurationFactory._parse_env_value("123") == 123
        assert EnhancedConfigurationFactory._parse_env_value("0") == 0
        assert EnhancedConfigurationFactory._parse_env_value("-456") == -456

        # Test float parsing
        assert EnhancedConfigurationFactory._parse_env_value("1.5") == 1.5
        assert EnhancedConfigurationFactory._parse_env_value("0.0") == 0.0

        # Test string parsing (default)
        assert EnhancedConfigurationFactory._parse_env_value("hello") == "hello"
        assert EnhancedConfigurationFactory._parse_env_value("") == ""

    def test_set_nested_value(self):
        """Test setting nested values in configuration dictionary."""
        config_dict: dict[str, Any] = {"queue": {"maxsize": 1000}, "level": "INFO"}

        # Test setting nested value
        EnhancedConfigurationFactory._set_nested_value(
            config_dict, "queue.maxsize", 2000
        )
        assert config_dict["queue"]["maxsize"] == 2000

        # Test setting new nested value
        EnhancedConfigurationFactory._set_nested_value(
            config_dict, "security.enable_auto_redact_pii", True
        )
        assert config_dict["security"]["enable_auto_redact_pii"] is True

        # Test setting top-level value
        EnhancedConfigurationFactory._set_nested_value(config_dict, "level", "DEBUG")
        assert config_dict["level"] == "DEBUG"

    def test_all_presets_with_environment_support(self):
        """Test that all presets support environment variables."""
        presets = [
            "development",
            "production",
            "testing",
            "high_performance",
            "monitoring",
        ]

        for preset in presets:
            # Set a test environment variable
            env_var = f"FAPILOG_FACTORY_{preset.upper()}_LEVEL"
            os.environ[env_var] = "WARNING"

            # Get the preset method
            preset_method = getattr(EnhancedConfigurationFactory, preset)
            config = preset_method()

            # Verify environment variable was applied
            assert config.level == "WARNING"

            # Clean up
            del os.environ[env_var]

    def test_debug_environment_parsing(self):
        """Debug test to see what environment variable parsing produces."""
        # Set environment variables
        os.environ["FAPILOG_FACTORY_DEVELOPMENT_LEVEL"] = "INFO"
        os.environ["FAPILOG_FACTORY_DEVELOPMENT_QUEUE_MAXSIZE"] = "500"
        os.environ["FAPILOG_FACTORY_DEVELOPMENT_SECURITY_ENABLE_AUTO_REDACT_PII"] = (
            "true"
        )

        # Get environment overrides
        env_overrides = EnhancedConfigurationFactory._get_environment_overrides(
            "development"
        )
        print(f"Environment overrides: {env_overrides}")

        # Get base config
        base_config = EnhancedConfigurationFactory.development()
        config_dict = base_config.model_dump()
        print(
            f"Base config queue maxsize: {config_dict.get('queue', {}).get('maxsize')}"
        )

        # Apply environment overrides
        for key, value in env_overrides.items():
            EnhancedConfigurationFactory._set_nested_value(config_dict, key, value)

        print(
            f"After applying overrides: {config_dict.get('queue', {}).get('maxsize')}"
        )

        # Create final config
        config = LoggingSettings(**config_dict)
        print(f"Final config queue maxsize: {config.queue.maxsize}")

        # Clean up
        del os.environ["FAPILOG_FACTORY_DEVELOPMENT_LEVEL"]
        del os.environ["FAPILOG_FACTORY_DEVELOPMENT_QUEUE_MAXSIZE"]
        del os.environ["FAPILOG_FACTORY_DEVELOPMENT_SECURITY_ENABLE_AUTO_REDACT_PII"]

    def test_original_development_preset(self):
        """Test original development preset without environment variables."""
        # Clear any existing environment variables
        env_vars_to_remove = [
            key for key in os.environ.keys() if key.startswith("FAPILOG_")
        ]
        for key in env_vars_to_remove:
            del os.environ[key]

        # Get the original development preset
        config = EnhancedConfigurationFactory.development()

        # Verify the original defaults
        assert config.level == "DEBUG"
        assert config.queue.maxsize == 100
        assert config.queue.batch_size == 1
        assert config.queue.overflow == "block"
        assert config.security.enable_auto_redact_pii is False
        assert config.sinks.json_console == "pretty"

    def test_debug_configuration_creation(self):
        """Debug test to see what configuration is actually being created."""
        # Clear any existing environment variables
        env_vars_to_remove = [
            key for key in os.environ.keys() if key.startswith("FAPILOG_")
        ]
        for key in env_vars_to_remove:
            del os.environ[key]

        # Set specific environment variables for this test
        os.environ["FAPILOG_FACTORY_DEVELOPMENT_LEVEL"] = "INFO"
        os.environ["FAPILOG_FACTORY_DEVELOPMENT_QUEUE_MAXSIZE"] = "500"
        os.environ["FAPILOG_FACTORY_DEVELOPMENT_SECURITY_ENABLE_AUTO_REDACT_PII"] = (
            "true"
        )

        # Get the configuration
        config = EnhancedConfigurationFactory.development()

        # Print the actual configuration
        print("Actual configuration:")
        print(f"  Level: {config.level}")
        print(f"  Queue maxsize: {config.queue.maxsize}")
        print(f"  Queue batch_size: {config.queue.batch_size}")
        print(f"  Queue overflow: {config.queue.overflow}")
        print(
            f"  Security enable_auto_redact_pii: {config.security.enable_auto_redact_pii}"
        )

        # Get the original configuration for comparison
        original_config = ConfigurationFactory.development()
        print("\nOriginal configuration:")
        print(f"  Level: {original_config.level}")
        print(f"  Queue maxsize: {original_config.queue.maxsize}")
        print(f"  Queue batch_size: {original_config.queue.batch_size}")
        print(f"  Queue overflow: {original_config.queue.overflow}")
        print(
            f"  Security enable_auto_redact_pii: {original_config.security.enable_auto_redact_pii}"
        )

        # Clean up
        del os.environ["FAPILOG_FACTORY_DEVELOPMENT_LEVEL"]
        del os.environ["FAPILOG_FACTORY_DEVELOPMENT_QUEUE_MAXSIZE"]
        del os.environ["FAPILOG_FACTORY_DEVELOPMENT_SECURITY_ENABLE_AUTO_REDACT_PII"]
