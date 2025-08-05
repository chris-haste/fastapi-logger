"""Tests for fapilog settings functionality."""

import os
from unittest.mock import patch

import pytest

from fapilog.bootstrap import configure_logging
from fapilog.config import LoggingSettings
from fapilog.exceptions import ConfigurationError


class TestLoggingSettings:
    """Test the LoggingSettings configuration model."""

    def test_defaults(self) -> None:
        """Test that LoggingSettings has correct defaults."""
        with patch.dict(os.environ, {}, clear=True):
            settings = LoggingSettings()

            assert settings.level == "INFO"
            assert settings.sinks.sinks == ["stdout"]
            assert settings.sinks.json_console == "auto"
            assert settings.security.redact_patterns == []
            assert settings.sinks.sampling_rate == 1.0

    def test_env_override(self) -> None:
        """Test that environment variables override defaults."""
        env_vars = {
            "FAPILOG_LEVEL": "DEBUG",
            "FAPILOG_SINKS__SINKS": "stdout,loki",
            "FAPILOG_SINKS__JSON_CONSOLE": "json",
            "FAPILOG_SECURITY__REDACT_PATTERNS": '["password", "secret"]',
            "FAPILOG_SINKS__SAMPLING_RATE": "0.5",
        }

        with patch.dict(os.environ, env_vars):
            settings = LoggingSettings()

            assert settings.level == "DEBUG"
            assert settings.sinks.sinks == ["stdout", "loki"]
            assert settings.sinks.json_console == "json"
            assert settings.security.redact_patterns == ["password", "secret"]
            assert settings.sinks.sampling_rate == 0.5

    def test_level_validation_valid(self) -> None:
        """Test that valid log levels are accepted."""
        valid_levels = ["DEBUG", "INFO", "WARN", "WARNING", "ERROR", "CRITICAL"]

        for level in valid_levels:
            settings = LoggingSettings(level=level)
            assert settings.level == level.upper()

    def test_level_validation_invalid(self) -> None:
        """Test that invalid log levels raise ConfigurationError."""
        invalid_levels = ["INVALID", "NOT_A_LEVEL", "FOO", "BAR"]

        for level in invalid_levels:
            with pytest.raises(ConfigurationError) as exc_info:
                LoggingSettings.model_validate({"level": level})

            error_msg = str(exc_info.value)
            assert "Invalid level" in error_msg

    def test_json_console_validation_valid(self) -> None:
        """Test that valid json_console values are accepted."""
        valid_values = ["auto", "json", "pretty"]

        from fapilog.config.sink_settings import SinkSettings

        for value in valid_values:
            settings = LoggingSettings.model_validate(
                {"sinks": SinkSettings(json_console=value)}
            )
            assert settings.sinks.json_console == value.lower()

    def test_json_console_validation_invalid(self) -> None:
        """Test that invalid json_console values raise ConfigurationError."""
        invalid_values = ["INVALID", "NOT_A_VALUE", "FOO", "BAR"]

        from fapilog.config.sink_settings import SinkSettings

        for value in invalid_values:
            with pytest.raises(ConfigurationError) as exc_info:
                LoggingSettings.model_validate(
                    {"sinks": SinkSettings(json_console=value)}
                )

            assert "Invalid json_console" in str(exc_info.value)

    def test_sampling_rate_validation_valid(self) -> None:
        """Test that valid sampling rates are accepted."""
        valid_rates = [0.0, 0.1, 0.5, 1.0]

        from fapilog.config.sink_settings import SinkSettings

        for rate in valid_rates:
            settings = LoggingSettings(sinks=SinkSettings(sampling_rate=rate))
            assert settings.sinks.sampling_rate == rate

    def test_sampling_rate_validation_invalid(self) -> None:
        """Test that invalid sampling rates raise ConfigurationError."""
        invalid_rates = [-0.1, 1.1, 2.0, -1.0]

        from fapilog.config.sink_settings import SinkSettings

        for rate in invalid_rates:
            with pytest.raises(ConfigurationError) as exc_info:
                LoggingSettings(sinks=SinkSettings(sampling_rate=rate))

            expected = "Sampling rate must be between 0.0 and 1.0"
            assert expected in str(exc_info.value)

    def test_sinks_parsing(self) -> None:
        """Test that sinks are parsed from comma-separated strings."""
        from fapilog.config.sink_settings import SinkSettings

        settings = LoggingSettings(sinks=SinkSettings(sinks=["stdout", "loki", "file"]))
        assert settings.sinks.sinks == ["stdout", "loki", "file"]

    def test_redact_patterns_parsing(self) -> None:
        """Test that redact patterns are parsed from comma-separated strings."""
        patterns = ["password", "secret", "token"]
        settings = LoggingSettings(security={"redact_patterns": patterns})
        assert settings.security.redact_patterns == patterns

    def test_env_nested_delimiter(self) -> None:
        """Test that nested delimiter environment variables are parsed correctly."""
        env_vars = {
            "FAPILOG_SINKS__SINKS": "stdout,loki,file",
            "FAPILOG_SECURITY__REDACT_PATTERNS": '["password", "secret", "token"]',
        }

        with patch.dict(os.environ, env_vars):
            settings = LoggingSettings()

            assert settings.sinks.sinks == ["stdout", "loki", "file"]
            assert settings.security.redact_patterns == ["password", "secret", "token"]

    def test_case_insensitive_config(self) -> None:
        """Test that environment variables are case-insensitive."""
        env_vars = {
            "fapilog_level": "debug",
            "FAPILOG_SINKS__JSON_CONSOLE": "JSON",
        }

        with patch.dict(os.environ, env_vars):
            settings = LoggingSettings()

            assert settings.level == "DEBUG"
            assert settings.sinks.json_console == "json"

    def test_model_validation(self) -> None:
        """Test that model validation works correctly."""
        # Create settings with valid data
        from fapilog.config.sink_settings import SinkSettings

        settings = LoggingSettings(
            level="INFO",
            sinks=SinkSettings(
                sinks=["stdout"],
                json_console="auto",
                sampling_rate=1.0,
            ),
        )

        # Test that the settings object works correctly
        assert settings.level == "INFO"
        assert settings.sinks.sinks == ["stdout"]
        assert settings.sinks.json_console == "auto"
        assert settings.security.redact_patterns == []  # From nested security settings
        assert settings.sinks.sampling_rate == 1.0

        # Test that we can create a new instance with same data
        validated = LoggingSettings(
            level=settings.level,
            sinks=SinkSettings(
                sinks=settings.sinks.sinks,
                json_console=settings.sinks.json_console,
                sampling_rate=settings.sinks.sampling_rate,
            ),
        )
        assert validated.level == "INFO"
        assert validated.sinks.sinks == ["stdout"]
        assert validated.sinks.json_console == "auto"
        assert validated.security.redact_patterns == []
        assert validated.sinks.sampling_rate == 1.0


def test_configure_logging_function():
    """Test the configure_logging function from bootstrap module."""
    from fapilog.config import LoggingSettings

    # Test the actual configure_logging function
    configure_logging()

    # Test with specific settings
    from fapilog.config.sink_settings import SinkSettings

    settings = LoggingSettings(level="INFO", sinks=SinkSettings(json_console="json"))
    configure_logging(settings=settings)

    # Test with different settings
    settings2 = LoggingSettings(
        level="DEBUG", sinks=SinkSettings(json_console="pretty")
    )
    configure_logging(settings=settings2)
