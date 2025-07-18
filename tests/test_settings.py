"""Tests for fapilog settings functionality."""

import os
from unittest.mock import patch

import pytest

from fapilog.bootstrap import configure_logging
from fapilog.exceptions import ConfigurationError
from fapilog.settings import LoggingSettings


class TestLoggingSettings:
    """Test the LoggingSettings configuration model."""

    def test_defaults(self) -> None:
        """Test that LoggingSettings has correct defaults."""
        with patch.dict(os.environ, {}, clear=True):
            settings = LoggingSettings()

            assert settings.level == "INFO"
            assert settings.sinks == ["stdout"]
            assert settings.json_console == "auto"
            assert settings.redact_patterns == []
            assert settings.sampling_rate == 1.0

    def test_env_override(self) -> None:
        """Test that environment variables override defaults."""
        env_vars = {
            "FAPILOG_LEVEL": "DEBUG",
            "FAPILOG_SINKS": "stdout,loki",
            "FAPILOG_JSON_CONSOLE": "json",
            "FAPILOG_REDACT_PATTERNS": "password,secret",
            "FAPILOG_SAMPLING_RATE": "0.5",
        }

        with patch.dict(os.environ, env_vars):
            settings = LoggingSettings()

            assert settings.level == "DEBUG"
            assert settings.sinks == ["stdout", "loki"]
            assert settings.json_console == "json"
            assert settings.redact_patterns == ["password", "secret"]
            assert settings.sampling_rate == 0.5

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

        for value in valid_values:
            settings = LoggingSettings.model_validate({"json_console": value})
            assert settings.json_console == value.lower()

    def test_json_console_validation_invalid(self) -> None:
        """Test that invalid json_console values raise ConfigurationError."""
        invalid_values = ["INVALID", "NOT_A_VALUE", "FOO", "BAR"]

        for value in invalid_values:
            with pytest.raises(ConfigurationError) as exc_info:
                LoggingSettings.model_validate({"json_console": value})

            assert "Invalid json_console" in str(exc_info.value)

    def test_sampling_rate_validation_valid(self) -> None:
        """Test that valid sampling rates are accepted."""
        valid_rates = [0.0, 0.1, 0.5, 1.0]

        for rate in valid_rates:
            settings = LoggingSettings(sampling_rate=rate)
            assert settings.sampling_rate == rate

    def test_sampling_rate_validation_invalid(self) -> None:
        """Test that invalid sampling rates raise ConfigurationError."""
        invalid_rates = [-0.1, 1.1, 2.0, -1.0]

        for rate in invalid_rates:
            with pytest.raises(ConfigurationError) as exc_info:
                LoggingSettings(sampling_rate=rate)

            expected = "Sampling rate must be between 0.0 and 1.0"
            assert expected in str(exc_info.value)

    def test_sinks_parsing(self) -> None:
        """Test that sinks are parsed from comma-separated strings."""
        settings = LoggingSettings(sinks=["stdout", "loki", "file"])
        assert settings.sinks == ["stdout", "loki", "file"]

    def test_redact_patterns_parsing(self) -> None:
        """Test that redact patterns are parsed from comma-separated strings."""
        patterns = ["password", "secret", "token"]
        settings = LoggingSettings(redact_patterns=patterns)
        assert settings.redact_patterns == patterns

    def test_env_nested_delimiter(self) -> None:
        """Test that comma-separated env vars are parsed correctly."""
        env_vars = {
            "FAPILOG_SINKS": "stdout,loki,file",
            "FAPILOG_REDACT_PATTERNS": "password,secret,token",
        }

        with patch.dict(os.environ, env_vars):
            settings = LoggingSettings()

            assert settings.sinks == ["stdout", "loki", "file"]
            assert settings.redact_patterns == ["password", "secret", "token"]

    def test_case_insensitive_config(self) -> None:
        """Test that environment variables are case-insensitive."""
        env_vars = {
            "fapilog_level": "debug",
            "FAPILOG_JSON_CONSOLE": "JSON",
        }

        with patch.dict(os.environ, env_vars):
            settings = LoggingSettings()

            assert settings.level == "DEBUG"
            assert settings.json_console == "json"

    def test_model_validation(self) -> None:
        """Test that model validation works correctly."""
        # Create settings with valid data
        settings = LoggingSettings(
            level="INFO",
            sinks=["stdout"],
            json_console="auto",
            redact_patterns=[],
            sampling_rate=1.0,
        )

        # Validate the model
        validated = LoggingSettings.model_validate(settings.model_dump())

        assert validated.level == "INFO"
        assert validated.sinks == ["stdout"]
        assert validated.json_console == "auto"
        assert validated.redact_patterns == []
        assert validated.sampling_rate == 1.0


def test_configure_logging_function():
    """Test the configure_logging function from bootstrap module."""
    # Test the actual configure_logging function
    configure_logging()
    configure_logging(level="INFO", json_console="json")
    sinks_config = {"stdout": {}}
    configure_logging(level="DEBUG", json_console="pretty", sinks=sinks_config)
