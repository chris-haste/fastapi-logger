"""Tests for level-aware redaction functionality."""

import pytest

from fapilog._internal.pii_patterns import auto_redact_pii_processor
from fapilog.exceptions import RedactionError
from fapilog.pipeline import _redact_processor
from fapilog.redactors import (
    _get_log_level_numeric,
    _should_redact_at_level,
    field_redactor,
)


class TestLogLevelHelpers:
    """Test helper functions for log level comparison."""

    def test_get_log_level_numeric(self):
        """Test conversion of log level strings to numeric values."""
        assert _get_log_level_numeric("DEBUG") == 10
        assert _get_log_level_numeric("INFO") == 20
        assert _get_log_level_numeric("WARN") == 30
        assert _get_log_level_numeric("WARNING") == 30
        assert _get_log_level_numeric("ERROR") == 40
        assert _get_log_level_numeric("CRITICAL") == 50

    def test_get_log_level_numeric_case_insensitive(self):
        """Test that log level conversion is case insensitive."""
        assert _get_log_level_numeric("debug") == 10
        assert _get_log_level_numeric("Info") == 20
        assert _get_log_level_numeric("WARNING") == 30

    def test_get_log_level_numeric_invalid(self):
        """Test that invalid log levels raise RedactionError."""
        with pytest.raises(RedactionError, match="Unknown log level"):
            _get_log_level_numeric("INVALID")

    def test_should_redact_at_level(self):
        """Test log level comparison for redaction decisions."""
        # DEBUG < INFO - should not redact
        assert not _should_redact_at_level("DEBUG", "INFO")

        # INFO >= INFO - should redact
        assert _should_redact_at_level("INFO", "INFO")

        # ERROR >= INFO - should redact
        assert _should_redact_at_level("ERROR", "INFO")

        # CRITICAL >= INFO - should redact
        assert _should_redact_at_level("CRITICAL", "INFO")

        # INFO < ERROR - should not redact
        assert not _should_redact_at_level("INFO", "ERROR")

    def test_should_redact_at_level_invalid_defaults_to_redact(self):
        """Test that invalid levels default to applying redaction."""
        # Invalid event level - should redact as safe default
        assert _should_redact_at_level("INVALID", "INFO")

        # Invalid redact level - should redact as safe default
        assert _should_redact_at_level("INFO", "INVALID")

        # Both invalid - should redact as safe default
        assert _should_redact_at_level("INVALID", "INVALID")


class TestPatternRedactionLevel:
    """Test pattern-based redaction with log level checking."""

    def test_debug_log_not_redacted(self):
        """Test that DEBUG logs bypass pattern redaction when redact_level is INFO."""
        patterns = [r"password", r"token"]
        processor = _redact_processor(patterns, redact_level="INFO")

        event_dict = {
            "level": "DEBUG",
            "message": "User login",
            "password": "secret123",
            "token": "abc123",
        }

        result = processor(None, "info", event_dict)

        # Should not be redacted - DEBUG < INFO
        assert result["password"] == "secret123"
        assert result["token"] == "abc123"

    def test_info_log_redacted(self):
        """Test that INFO logs are redacted when redact_level is INFO."""
        patterns = [r"password", r"token"]
        processor = _redact_processor(patterns, redact_level="INFO")

        event_dict = {
            "level": "INFO",
            "message": "User login",
            "password": "secret123",
            "token": "abc123",
        }

        result = processor(None, "info", event_dict)

        # Should be redacted - INFO >= INFO
        assert result["password"] == "[REDACTED]"
        assert result["token"] == "[REDACTED]"

    def test_custom_redact_level(self):
        """Test pattern redaction with custom redact level (ERROR)."""
        patterns = [r"password"]
        processor = _redact_processor(patterns, redact_level="ERROR")

        # INFO < ERROR - should not redact
        event_dict_info = {"level": "INFO", "password": "secret123"}
        result_info = processor(None, "info", event_dict_info)
        assert result_info["password"] == "secret123"

        # ERROR >= ERROR - should redact
        event_dict_error = {"level": "ERROR", "password": "secret123"}
        result_error = processor(None, "error", event_dict_error)
        assert result_error["password"] == "[REDACTED]"

    def test_missing_level_defaults_to_redact(self):
        """Test that events without level field default to being redacted."""
        patterns = [r"password"]
        processor = _redact_processor(patterns, redact_level="INFO")

        event_dict = {"message": "User login", "password": "secret123"}

        result = processor(None, "info", event_dict)

        # Should be redacted - missing level defaults to INFO >= INFO
        assert result["password"] == "[REDACTED]"


class TestFieldRedactionLevel:
    """Test field-based redaction with log level checking."""

    def test_debug_log_not_redacted(self):
        """Test that DEBUG logs bypass field redaction when redact_level is INFO."""
        fields = ["user.password", "auth.token"]
        processor = field_redactor(fields, redact_level="INFO")

        event_dict = {
            "level": "DEBUG",
            "user": {"password": "secret123"},
            "auth": {"token": "abc123"},
        }

        result = processor(None, "info", event_dict)

        # Should not be redacted - DEBUG < INFO
        assert result["user"]["password"] == "secret123"
        assert result["auth"]["token"] == "abc123"

    def test_info_log_redacted(self):
        """Test that INFO logs are redacted when redact_level is INFO."""
        fields = ["user.password", "auth.token"]
        processor = field_redactor(fields, replacement="***", redact_level="INFO")

        event_dict = {
            "level": "INFO",
            "user": {"password": "secret123"},
            "auth": {"token": "abc123"},
        }

        result = processor(None, "info", event_dict)

        # Should be redacted - INFO >= INFO
        assert result["user"]["password"] == "***"
        assert result["auth"]["token"] == "***"

    def test_custom_redact_level(self):
        """Test field redaction with custom redact level (WARNING)."""
        fields = ["password"]
        processor = field_redactor(fields, redact_level="WARNING")

        # INFO < WARNING - should not redact
        event_dict_info = {"level": "INFO", "password": "secret123"}
        result_info = processor(None, "info", event_dict_info)
        assert result_info["password"] == "secret123"

        # WARNING >= WARNING - should redact
        event_dict_warning = {"level": "WARNING", "password": "secret123"}
        result_warning = processor(None, "warning", event_dict_warning)
        assert result_warning["password"] == "REDACTED"

    def test_missing_level_defaults_to_redact(self):
        """Test that events without level field default to being redacted."""
        fields = ["password"]
        processor = field_redactor(fields, redact_level="INFO")

        event_dict = {"message": "User login", "password": "secret123"}

        result = processor(None, "info", event_dict)

        # Should be redacted - missing level defaults to INFO >= INFO
        assert result["password"] == "REDACTED"


class TestPIIRedactionLevel:
    """Test PII auto-detection redaction with log level checking."""

    def test_debug_log_not_redacted(self):
        """Test that DEBUG logs bypass PII redaction when redact_level is INFO."""
        patterns = [r"\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}"]  # Credit card pattern
        processor = auto_redact_pii_processor(patterns, redact_level="INFO")

        event_dict = {
            "level": "DEBUG",
            "message": "Payment processed",
            "card_number": "4532-1234-5678-9012",
        }

        result = processor(None, "info", event_dict)

        # Should not be redacted - DEBUG < INFO
        assert result["card_number"] == "4532-1234-5678-9012"

    def test_info_log_redacted(self):
        """Test that INFO logs are redacted when redact_level is INFO."""
        patterns = [r"\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}"]  # Credit card pattern
        processor = auto_redact_pii_processor(
            patterns, replacement="[PII]", redact_level="INFO"
        )

        event_dict = {
            "level": "INFO",
            "message": "Payment processed",
            "card_number": "4532-1234-5678-9012",
        }

        result = processor(None, "info", event_dict)

        # Should be redacted - INFO >= INFO
        assert result["card_number"] == "[PII]"

    def test_custom_redact_level(self):
        """Test PII redaction with custom redact level (CRITICAL)."""
        patterns = [r"[\w\.-]+@[\w\.-]+\.\w+"]  # Email pattern
        processor = auto_redact_pii_processor(patterns, redact_level="CRITICAL")

        # ERROR < CRITICAL - should not redact
        event_dict_error = {"level": "ERROR", "email": "user@example.com"}
        result_error = processor(None, "error", event_dict_error)
        assert result_error["email"] == "user@example.com"

        # CRITICAL >= CRITICAL - should redact
        event_dict_critical = {"level": "CRITICAL", "email": "user@example.com"}
        result_critical = processor(None, "critical", event_dict_critical)
        assert result_critical["email"] == "REDACTED"

    def test_missing_level_defaults_to_redact(self):
        """Test that events without level field default to being redacted."""
        patterns = [r"[\w\.-]+@[\w\.-]+\.\w+"]  # Email pattern
        processor = auto_redact_pii_processor(patterns, redact_level="INFO")

        event_dict = {"message": "User signup", "email": "user@example.com"}

        result = processor(None, "info", event_dict)

        # Should be redacted - missing level defaults to INFO >= INFO
        assert result["email"] == "REDACTED"


class TestLevelRedactionIntegration:
    """Test integration scenarios with multiple redaction types."""

    def test_all_redactors_respect_level(self):
        """Test that all redaction processors respect the same log level setting."""
        # Pattern-based redaction
        pattern_processor = _redact_processor([r"password"], redact_level="WARNING")

        # Field-based redaction
        field_processor = field_redactor(["api_key"], redact_level="WARNING")

        # PII redaction
        pii_processor = auto_redact_pii_processor(
            [r"[\w\.-]+@[\w\.-]+\.\w+"], redact_level="WARNING"
        )

        # INFO < WARNING - none should redact
        event_dict = {
            "level": "INFO",
            "password": "secret123",
            "api_key": "key123",
            "email": "user@example.com",
        }

        result1 = pattern_processor(None, "info", event_dict.copy())
        result2 = field_processor(None, "info", result1)
        result3 = pii_processor(None, "info", result2)

        assert result3["password"] == "secret123"
        assert result3["api_key"] == "key123"
        assert result3["email"] == "user@example.com"

        # WARNING >= WARNING - all should redact
        event_dict["level"] = "WARNING"

        result1 = pattern_processor(None, "warning", event_dict.copy())
        result2 = field_processor(None, "warning", result1)
        result3 = pii_processor(None, "warning", result2)

        assert result3["password"] == "[REDACTED]"
        assert result3["api_key"] == "REDACTED"
        assert result3["email"] == "REDACTED"

    def test_different_redact_levels(self):
        """Test processors with different redact levels."""
        # Pattern redaction at INFO level
        pattern_processor = _redact_processor([r"password"], redact_level="INFO")

        # Field redaction at ERROR level
        field_processor = field_redactor(["api_key"], redact_level="ERROR")

        # WARNING level event
        event_dict = {"level": "WARNING", "password": "secret123", "api_key": "key123"}

        result1 = pattern_processor(None, "warning", event_dict.copy())
        result2 = field_processor(None, "warning", result1)

        # WARNING >= INFO - password should be redacted
        assert result2["password"] == "[REDACTED]"

        # WARNING < ERROR - api_key should not be redacted
        assert result2["api_key"] == "key123"
