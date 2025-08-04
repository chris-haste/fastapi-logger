"""Simple tests to boost settings.py validation coverage."""

import pytest

from fapilog.config import LoggingSettings
from fapilog.exceptions import ConfigurationError


class TestSettingsValidationBoost:
    """Tests targeting validation error paths in LoggingSettings."""

    def test_invalid_level_validation(self):
        """Test validation error for invalid log level."""
        with pytest.raises(ConfigurationError, match="Invalid level 'INVALID'"):
            LoggingSettings(level="INVALID")

    def test_invalid_redact_level_validation(self):
        """Test validation error for invalid redact level."""
        with pytest.raises(ConfigurationError, match="Invalid redact_level 'INVALID'"):
            LoggingSettings(security={"redact_level": "INVALID"})

    def test_level_validation_case_insensitive(self):
        """Test that level validation handles different cases."""
        # These should work
        settings = LoggingSettings(level="debug")
        assert settings.level == "DEBUG"

        settings = LoggingSettings(level="Info")
        assert settings.level == "INFO"

        settings = LoggingSettings(level="WARNING")
        assert settings.level == "WARNING"

    def test_redact_level_validation_case_insensitive(self):
        """Test that redact_level validation handles different cases."""
        # These should work
        settings = LoggingSettings(security={"redact_level": "error"})
        assert settings.security.redact_level == "ERROR"

        settings = LoggingSettings(security={"redact_level": "Critical"})
        assert settings.security.redact_level == "CRITICAL"

    def test_parse_sinks_mixed_types(self):
        """Test sinks parsing with mixed types."""
        # String that gets converted
        settings = LoggingSettings(sinks="stdout,file://test.log")
        assert settings.sinks == ["stdout", "file://test.log"]

        # List with mixed types
        settings = LoggingSettings(sinks=["stdout", 123, None])  # type: ignore[list-item]
        assert len(settings.sinks) == 3
        assert settings.sinks[0] == "stdout"
        assert settings.sinks[1] == "123"  # Converted to string
        assert settings.sinks[2] == "None"  # Converted to string

    def test_parse_redact_patterns_various_inputs(self):
        """Test redact_patterns parsing with various input types."""
        # String input
        settings = LoggingSettings(
            security={"redact_patterns": "password,secret,token"}
        )
        assert settings.security.redact_patterns == ["password", "secret", "token"]

        # List input
        settings = LoggingSettings(security={"redact_patterns": ["password", "secret"]})
        assert settings.security.redact_patterns == ["password", "secret"]

        # Tuple input
        settings = LoggingSettings(security={"redact_patterns": ("password", "secret")})
        assert settings.security.redact_patterns == ["password", "secret"]

        # Single string that's not a list
        settings = LoggingSettings(security={"redact_patterns": "single_pattern"})
        assert settings.security.redact_patterns == ["single_pattern"]

    def test_parse_redact_fields_various_inputs(self):
        """Test redact_fields parsing with various input types."""
        # String input
        settings = LoggingSettings(
            security={"redact_fields": "user.name,user.email,password"}
        )
        assert settings.security.redact_fields == [
            "user.name",
            "user.email",
            "password",
        ]

        # List input
        settings = LoggingSettings(
            security={"redact_fields": ["user.name", "password"]}
        )
        assert settings.security.redact_fields == ["user.name", "password"]

        # Tuple input
        settings = LoggingSettings(
            security={"redact_fields": ("user.name", "password")}
        )
        assert settings.security.redact_fields == ["user.name", "password"]

    def test_parse_custom_pii_patterns_various_inputs(self):
        """Test custom_pii_patterns parsing with various input types."""
        # String input
        settings = LoggingSettings(security={"custom_pii_patterns": "ssn,credit_card"})
        assert settings.security.custom_pii_patterns == ["ssn", "credit_card"]

        # List input
        settings = LoggingSettings(
            security={"custom_pii_patterns": ["ssn", "credit_card"]}
        )
        assert settings.security.custom_pii_patterns == ["ssn", "credit_card"]

        # Tuple input
        settings = LoggingSettings(
            security={"custom_pii_patterns": ("ssn", "credit_card")}
        )
        assert settings.security.custom_pii_patterns == ["ssn", "credit_card"]

    def test_parse_sinks_empty_string_handling(self):
        """Test sinks parsing handles empty strings correctly."""
        # Empty items should be filtered out
        settings = LoggingSettings(sinks="stdout,,file://test.log, ")
        assert settings.sinks == ["stdout", "file://test.log"]

    def test_parse_patterns_empty_string_handling(self):
        """Test patterns parsing handles empty strings correctly."""
        # Empty items should be filtered out
        settings = LoggingSettings(security={"redact_patterns": "password,,secret, "})
        assert settings.security.redact_patterns == ["password", "secret"]

        settings = LoggingSettings(security={"redact_fields": "user.name,,password, "})
        assert settings.security.redact_fields == ["user.name", "password"]

        settings = LoggingSettings(security={"custom_pii_patterns": "ssn,,credit, "})
        assert settings.security.custom_pii_patterns == ["ssn", "credit"]

    def test_settings_with_various_defaults(self):
        """Test settings initialization with various default behaviors."""
        settings = LoggingSettings()

        # Check default factory functions are called
        assert settings.sinks == ["stdout"]
        assert settings.security.redact_patterns == []
        assert settings.security.redact_fields == []
        assert settings.security.custom_pii_patterns == []

        # Check other defaults
        assert settings.level == "INFO"
        assert settings.json_console == "auto"
        assert settings.security.redact_replacement == "REDACTED"
        assert settings.security.redact_level == "INFO"
        assert settings.queue.enabled is True
        assert settings.queue.maxsize == 1000

    def test_environment_variable_mapping(self):
        """Test that environment variable mapping works correctly."""
        import os

        # Test case sensitivity
        original_level = os.environ.get("FAPILOG_LEVEL")

        try:
            os.environ["FAPILOG_LEVEL"] = "debug"
            settings = LoggingSettings()
            assert settings.level == "DEBUG"

        finally:
            if original_level is not None:
                os.environ["FAPILOG_LEVEL"] = original_level
            elif "FAPILOG_LEVEL" in os.environ:
                del os.environ["FAPILOG_LEVEL"]
