"""Tests for simplified FAPILOG_SINKS environment processing (Issue #218)."""

import os
from unittest.mock import patch

from fapilog.config.settings import LoggingSettings


class TestFAPILOGSinksEnvironmentProcessing:
    """Test suite for simplified FAPILOG_SINKS environment variable processing."""

    def test_modern_nested_sinks_format(self) -> None:
        """Test modern FAPILOG_SINKS__SINKS nested format works perfectly."""
        env_vars = {
            "FAPILOG_SINKS__SINKS": "stdout,loki,file",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = LoggingSettings()
            assert settings.sinks.sinks == ["stdout", "loki", "file"]

    def test_nested_sinks_variables(self) -> None:
        """Test nested FAPILOG_SINKS__* environment variables work."""
        env_vars = {
            "FAPILOG_SINKS__SINKS": "stdout,loki",
            "FAPILOG_SINKS__JSON_CONSOLE": "pretty",
            "FAPILOG_SINKS__SAMPLING_RATE": "0.8",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = LoggingSettings()
            assert settings.sinks.sinks == ["stdout", "loki"]
            assert settings.sinks.json_console == "pretty"
            assert settings.sinks.sampling_rate == 0.8

    def test_complete_nested_configuration(self) -> None:
        """Test complete nested FAPILOG_SINKS__* configuration works perfectly."""
        env_vars = {
            "FAPILOG_SINKS__SINKS": "stdout,loki,file",
            "FAPILOG_SINKS__JSON_CONSOLE": "json",
            "FAPILOG_SINKS__SAMPLING_RATE": "0.5",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = LoggingSettings()
            assert settings.sinks.sinks == ["stdout", "loki", "file"]
            assert settings.sinks.json_console == "json"
            assert settings.sinks.sampling_rate == 0.5

    def test_default_sinks_behavior(self) -> None:
        """Test behavior with no environment variables - uses defaults."""
        with patch.dict(os.environ, {}, clear=True):
            settings = LoggingSettings()
            # Should use default
            assert settings.sinks.sinks == ["stdout"]

    def test_whitespace_handling_in_nested_format(self) -> None:
        """Test whitespace handling in modern nested format."""
        env_vars = {
            "FAPILOG_SINKS__SINKS": "stdout, loki , file,  ",  # Test whitespace handling
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = LoggingSettings()
            assert settings.sinks.sinks == ["stdout", "loki", "file"]

    def test_single_sink_nested_format(self) -> None:
        """Test single sink in nested format."""
        env_vars = {
            "FAPILOG_SINKS__SINKS": "stdout",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = LoggingSettings()
            assert settings.sinks.sinks == ["stdout"]

    def test_empty_sinks_nested_format(self) -> None:
        """Test empty sinks value in nested format."""
        env_vars = {
            "FAPILOG_SINKS__SINKS": "",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = LoggingSettings()
            # Empty string should result in empty list
            assert settings.sinks.sinks == []

    def test_case_insensitive_nested_configuration(self) -> None:
        """Test that nested environment variables are case-insensitive."""
        env_vars = {
            "fapilog_sinks__sinks": "stdout,loki",  # lowercase
            "FAPILOG_SINKS__JSON_CONSOLE": "json",  # uppercase
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = LoggingSettings()
            assert settings.sinks.sinks == ["stdout", "loki"]
            assert settings.sinks.json_console == "json"

    def test_validation_with_programmatic_input(self) -> None:
        """Test that field validator works with programmatic input."""
        from fapilog.config.sink_settings import SinkSettings

        # Test string input
        settings1 = LoggingSettings(sinks="stdout,loki,file")
        assert settings1.sinks.sinks == ["stdout", "loki", "file"]

        # Test SinkSettings input
        sink_settings = SinkSettings(sinks=["custom", "sink"])
        settings2 = LoggingSettings(sinks=sink_settings)
        assert settings2.sinks.sinks == ["custom", "sink"]

        # Test dict input
        settings3 = LoggingSettings(
            sinks={"sinks": ["dict", "input"], "json_console": "pretty"}
        )
        assert settings3.sinks.sinks == ["dict", "input"]
        assert settings3.sinks.json_console == "pretty"
