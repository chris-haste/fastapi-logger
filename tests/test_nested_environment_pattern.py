"""Tests for unified nested environment variable pattern."""

import os

import pytest
from pydantic_core import ValidationError

from fapilog.config import LoggingSettings
from fapilog.exceptions import ConfigurationError


class TestNestedEnvironmentPattern:
    """Test suite for unified nested environment variable pattern."""

    def setup_method(self):
        """Clear environment variables before each test."""
        # Remove any existing FAPILOG_ variables
        env_vars_to_remove = [
            key for key in os.environ.keys() if key.startswith("FAPILOG_")
        ]
        for key in env_vars_to_remove:
            del os.environ[key]

    def test_queue_settings_nested_environment(self):
        """Test QueueSettings environment variable parsing."""
        # Set nested environment variables
        os.environ["FAPILOG_QUEUE__ENABLED"] = "false"
        os.environ["FAPILOG_QUEUE__MAXSIZE"] = "500"
        os.environ["FAPILOG_QUEUE__BATCH_SIZE"] = "5"
        os.environ["FAPILOG_QUEUE__OVERFLOW"] = "block"

        settings = LoggingSettings()

        # Verify nested settings are parsed correctly
        assert settings.queue.enabled is False
        assert settings.queue.maxsize == 500
        assert settings.queue.batch_size == 5
        assert settings.queue.overflow == "block"

    def test_security_settings_nested_environment(self):
        """Test SecuritySettings environment variable parsing."""
        # Set nested environment variables
        os.environ["FAPILOG_SECURITY__ENABLE_AUTO_REDACT_PII"] = "true"
        os.environ["FAPILOG_SECURITY__REDACT_LEVEL"] = "DEBUG"
        os.environ["FAPILOG_SECURITY__REDACT_REPLACEMENT"] = "[SENSITIVE]"
        os.environ["FAPILOG_SECURITY__ENABLE_THROTTLING"] = "true"
        os.environ["FAPILOG_SECURITY__THROTTLE_MAX_RATE"] = "50"

        settings = LoggingSettings()

        # Verify nested settings are parsed correctly
        assert settings.security.enable_auto_redact_pii is True
        assert settings.security.redact_level == "DEBUG"
        assert settings.security.redact_replacement == "[SENSITIVE]"
        assert settings.security.enable_throttling is True
        assert settings.security.throttle_max_rate == 50

    def test_sink_settings_nested_environment(self):
        """Test SinkSettings environment variable parsing."""
        # Set nested environment variables
        os.environ["FAPILOG_SINKS__SINKS"] = "stdout,file:///logs/app.log"
        os.environ["FAPILOG_SINKS__JSON_CONSOLE"] = "json"
        os.environ["FAPILOG_SINKS__SAMPLING_RATE"] = "0.5"

        settings = LoggingSettings()

        # Verify nested settings are parsed correctly
        assert "stdout" in settings.sinks.sinks
        assert "file:///logs/app.log" in settings.sinks.sinks
        assert settings.sinks.json_console == "json"
        assert settings.sinks.sampling_rate == 0.5

    def test_metrics_settings_nested_environment(self):
        """Test MetricsSettings environment variable parsing."""
        # Set nested environment variables
        os.environ["FAPILOG_METRICS__ENABLED"] = "true"
        os.environ["FAPILOG_METRICS__SAMPLE_WINDOW"] = "200"
        os.environ["FAPILOG_METRICS__PROMETHEUS_ENABLED"] = "true"
        os.environ["FAPILOG_METRICS__PROMETHEUS_PORT"] = "9091"

        settings = LoggingSettings()

        # Verify nested settings are parsed correctly
        assert settings.metrics.enabled is True
        assert settings.metrics.sample_window == 200
        assert settings.metrics.prometheus_enabled is True
        assert settings.metrics.prometheus_port == 9091

    def test_validation_settings_nested_environment(self):
        """Test ValidationSettings environment variable parsing."""
        # Set nested environment variables
        os.environ["FAPILOG_VALIDATION__ENABLED"] = "true"
        os.environ["FAPILOG_VALIDATION__MODE"] = "strict"
        # Use JSON format for list fields
        os.environ["FAPILOG_VALIDATION__REQUIRED_FIELDS"] = (
            '["timestamp", "level", "event", "message"]'
        )

        settings = LoggingSettings()

        # Verify nested settings are parsed correctly
        assert settings.validation.enabled is True
        assert settings.validation.mode == "strict"
        assert "timestamp" in settings.validation.required_fields
        assert "level" in settings.validation.required_fields
        assert "event" in settings.validation.required_fields
        assert "message" in settings.validation.required_fields

    def test_mixed_nested_environment_variables(self):
        """Test mixed nested environment variables across all settings."""
        # Set environment variables for multiple nested settings
        os.environ["FAPILOG_LEVEL"] = "DEBUG"
        os.environ["FAPILOG_QUEUE__MAXSIZE"] = "750"
        os.environ["FAPILOG_SECURITY__REDACT_LEVEL"] = "WARNING"
        os.environ["FAPILOG_SINKS__JSON_CONSOLE"] = "pretty"
        os.environ["FAPILOG_METRICS__ENABLED"] = "false"
        os.environ["FAPILOG_VALIDATION__MODE"] = "lenient"

        settings = LoggingSettings()

        # Verify all settings are parsed correctly
        assert settings.level == "DEBUG"
        assert settings.queue.maxsize == 750
        assert settings.security.redact_level == "WARNING"
        assert settings.sinks.json_console == "pretty"
        assert settings.metrics.enabled is False
        assert settings.validation.mode == "lenient"

    def test_environment_variable_case_insensitivity(self):
        """Test that environment variables are case-insensitive."""
        # Set environment variables with mixed case
        os.environ["FAPILOG_QUEUE__MAXSIZE"] = "100"
        os.environ["FAPILOG_QUEUE__maxsize"] = "200"  # Should override
        os.environ["FAPILOG_SECURITY__ENABLE_AUTO_REDACT_PII"] = "TRUE"
        os.environ["FAPILOG_SINKS__JSON_CONSOLE"] = "JSON"

        settings = LoggingSettings()

        # Verify case-insensitive parsing
        assert settings.queue.maxsize == 200  # Last one wins
        assert settings.security.enable_auto_redact_pii is True
        assert settings.sinks.json_console == "json"  # Normalized to lowercase

    def test_invalid_nested_environment_variables(self):
        """Test that invalid nested environment variables raise appropriate errors."""
        # Set invalid values
        os.environ["FAPILOG_QUEUE__MAXSIZE"] = "-1"  # Invalid: must be positive
        os.environ["FAPILOG_SINKS__SAMPLING_RATE"] = "1.5"  # Invalid: must be <= 1.0
        os.environ["FAPILOG_SECURITY__REDACT_LEVEL"] = "INVALID"  # Invalid level

        # Should raise ConfigurationError for invalid values
        with pytest.raises(ConfigurationError):
            LoggingSettings()

    def test_nested_environment_with_defaults(self):
        """Test that defaults are used when nested environment variables are not set."""
        # Don't set any environment variables
        settings = LoggingSettings()

        # Verify defaults are used
        assert settings.queue.enabled is True  # Default
        assert settings.queue.maxsize == 1000  # Default
        assert settings.security.enable_auto_redact_pii is False  # Default
        assert settings.sinks.json_console == "auto"  # Default
        assert settings.metrics.enabled is False  # Default
        assert settings.validation.enabled is False  # Default

    def test_nested_environment_partial_override(self):
        """Test that partial nested environment variables work correctly."""
        # Set only some nested environment variables
        os.environ["FAPILOG_QUEUE__MAXSIZE"] = "500"
        os.environ["FAPILOG_SECURITY__ENABLE_AUTO_REDACT_PII"] = "true"

        settings = LoggingSettings()

        # Verify overridden values
        assert settings.queue.maxsize == 500
        assert settings.security.enable_auto_redact_pii is True

        # Verify defaults for non-overridden values
        assert settings.queue.enabled is True  # Default
        assert settings.queue.batch_size == 10  # Default
        assert settings.security.redact_level == "INFO"  # Default

    def test_nested_environment_complex_types(self):
        """Test that complex types in nested environment variables work correctly."""
        # Set complex nested environment variables using JSON format
        os.environ["FAPILOG_SECURITY__REDACT_FIELDS"] = (
            '["password", "token", "secret"]'
        )
        os.environ["FAPILOG_SECURITY__CUSTOM_PII_PATTERNS"] = '["credit_card", "ssn"]'
        os.environ["FAPILOG_VALIDATION__FIELD_TYPES"] = (
            '{"timestamp": "datetime", "level": "str"}'
        )

        settings = LoggingSettings()

        # Verify complex types are parsed correctly
        assert "password" in settings.security.redact_fields
        assert "token" in settings.security.redact_fields
        assert "secret" in settings.security.redact_fields
        assert "credit_card" in settings.security.custom_pii_patterns
        assert "ssn" in settings.security.custom_pii_patterns
        assert settings.validation.field_types["timestamp"] == "datetime"
        assert settings.validation.field_types["level"] == "str"

    def test_nested_environment_validation_errors(self):
        """Test that validation errors in nested settings are properly reported."""
        # Set invalid values that should trigger validation errors
        test_cases = [
            # These raise ConfigurationError (custom validation)
            ("FAPILOG_QUEUE__MAXSIZE", "-1", "must be positive", ConfigurationError),
            (
                "FAPILOG_SINKS__SAMPLING_RATE",
                "1.5",
                "between 0.0 and 1.0",
                ConfigurationError,
            ),
            (
                "FAPILOG_SECURITY__REDACT_LEVEL",
                "INVALID",
                "Must be one of",
                ConfigurationError,
            ),
            # This raises ValidationError (Pydantic built-in validation)
            ("FAPILOG_QUEUE__OVERFLOW", "invalid", "Input should be", ValidationError),
        ]

        for env_var, value, expected_error, expected_exception in test_cases:
            os.environ[env_var] = value

            with pytest.raises(expected_exception) as exc_info:
                LoggingSettings()

            # Verify error message contains expected content
            assert expected_error in str(exc_info.value)

            # Clean up for next test
            del os.environ[env_var]

    def test_nested_environment_with_factory_presets(self):
        """Test that nested environment variables work with LoggingSettings directly."""
        # Note: The original ConfigurationFactory doesn't support environment variables
        # This test verifies that LoggingSettings respects environment variables

        # Set nested environment variables
        os.environ["FAPILOG_QUEUE__MAXSIZE"] = "2000"
        os.environ["FAPILOG_SECURITY__ENABLE_AUTO_REDACT_PII"] = "true"
        os.environ["FAPILOG_LEVEL"] = "INFO"

        try:
            # Create settings that should respect environment variables
            settings = LoggingSettings()

            # Verify environment variables are applied
            assert settings.queue.maxsize == 2000  # From environment
            assert settings.security.enable_auto_redact_pii is True  # From environment
            assert settings.level == "INFO"  # From environment
        finally:
            # Clean up environment variables
            for env_var in [
                "FAPILOG_QUEUE__MAXSIZE",
                "FAPILOG_SECURITY__ENABLE_AUTO_REDACT_PII",
                "FAPILOG_LEVEL",
            ]:
                if env_var in os.environ:
                    del os.environ[env_var]
