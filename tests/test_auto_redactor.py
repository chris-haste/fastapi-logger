"""Tests for PII auto-detection redactor functionality."""

import warnings
from unittest.mock import Mock

from fapilog._internal.pii_patterns import (
    DEFAULT_PII_PATTERNS,
    _compile_pii_patterns,
    _redact_pii_recursive,
    _redact_string_value,
    auto_redact_pii_processor,
)


class TestPIIPatterns:
    """Test PII pattern compilation and matching."""

    def test_default_patterns_exist(self):
        """Test that default PII patterns are defined."""
        assert len(DEFAULT_PII_PATTERNS) > 0
        assert all(isinstance(pattern, str) for pattern in DEFAULT_PII_PATTERNS)

    def test_compile_valid_patterns(self):
        """Test compilation of valid regex patterns."""
        patterns = [r"\d+", r"[a-z]+"]
        compiled = _compile_pii_patterns(patterns)
        assert len(compiled) == 2
        assert all(hasattr(p, "sub") for p in compiled)

    def test_compile_invalid_patterns(self):
        """Test handling of invalid regex patterns."""
        patterns = [r"\d+", r"[invalid", r"[a-z]+"]
        # Suppress expected warning for invalid pattern
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            compiled = _compile_pii_patterns(patterns)
        # Should compile valid patterns and skip invalid ones
        assert len(compiled) == 2
        assert all(hasattr(p, "sub") for p in compiled)

    def test_compile_empty_patterns(self):
        """Test compilation of empty pattern list."""
        compiled = _compile_pii_patterns([])
        assert compiled == []


class TestStringRedaction:
    """Test string-level PII redaction."""

    def test_redact_email_address(self):
        """Test redaction of email addresses."""
        patterns = _compile_pii_patterns([r"[\w\.-]+@[\w\.-]+\.\w+"])
        value = "Contact us at user@example.com for support"
        result = _redact_string_value(value, patterns, "REDACTED")
        assert "user@example.com" not in result
        assert "REDACTED" in result
        assert "Contact us at" in result

    def test_redact_phone_number(self):
        """Test redaction of phone numbers."""
        patterns = _compile_pii_patterns(
            [r"(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}"]
        )
        value = "Call us at 555-123-4567 or +1-555-123-4567"
        result = _redact_string_value(value, patterns, "REDACTED")
        assert "555-123-4567" not in result
        assert "REDACTED" in result
        assert "Call us at" in result

    def test_redact_credit_card(self):
        """Test redaction of credit card numbers."""
        patterns = _compile_pii_patterns([r"\b\d{4}(?:[ -]?\d{4}){3}\b"])
        value = "Payment with card 1234 5678 9012 3456"
        result = _redact_string_value(value, patterns, "REDACTED")
        assert "1234 5678 9012 3456" not in result
        assert "REDACTED" in result
        assert "Payment with card" in result

    def test_redact_ip_address(self):
        """Test redaction of IPv4 addresses."""
        patterns = _compile_pii_patterns([r"\b(?:\d{1,3}\.){3}\d{1,3}\b"])
        value = "Request from 192.168.1.100"
        result = _redact_string_value(value, patterns, "REDACTED")
        assert "192.168.1.100" not in result
        assert "REDACTED" in result
        assert "Request from" in result

    def test_multiple_patterns(self):
        """Test redaction with multiple patterns."""
        patterns = _compile_pii_patterns(
            [r"[\w\.-]+@[\w\.-]+\.\w+", r"\b\d{4}(?:[ -]?\d{4}){3}\b"]
        )
        value = "Email: user@example.com, Card: 1234 5678 9012 3456"
        result = _redact_string_value(value, patterns, "REDACTED")
        assert "user@example.com" not in result
        assert "1234 5678 9012 3456" not in result
        assert result.count("REDACTED") >= 2

    def test_no_matches(self):
        """Test redaction when no patterns match."""
        patterns = _compile_pii_patterns([r"\d+"])
        value = "This is a test message"
        result = _redact_string_value(value, patterns, "REDACTED")
        assert result == value
        assert "REDACTED" not in result


class TestRecursiveRedaction:
    """Test recursive PII redaction across data structures."""

    def test_redact_dict_values(self):
        """Test redaction in dictionary values."""
        patterns = _compile_pii_patterns([r"[\w\.-]+@[\w\.-]+\.\w+"])
        data = {
            "user": "john@example.com",
            "message": "Contact support",
            "nested": {"email": "admin@example.com"},
        }
        result = _redact_pii_recursive(data, patterns, "REDACTED")
        assert result["user"] == "REDACTED"
        assert result["message"] == "Contact support"
        assert result["nested"]["email"] == "REDACTED"

    def test_redact_list_values(self):
        """Test redaction in list values."""
        patterns = _compile_pii_patterns([r"[\w\.-]+@[\w\.-]+\.\w+"])
        data = {"users": ["user1@example.com", "user2@example.com", "not_an_email"]}
        result = _redact_pii_recursive(data, patterns, "REDACTED")
        assert result["users"][0] == "REDACTED"
        assert result["users"][1] == "REDACTED"
        assert result["users"][2] == "not_an_email"

    def test_redact_nested_structures(self):
        """Test redaction in complex nested structures."""
        patterns = _compile_pii_patterns([r"[\w\.-]+@[\w\.-]+\.\w+"])
        data = {
            "users": [
                {
                    "name": "John",
                    "email": "john@example.com",
                    "contacts": ["admin@example.com", "support@example.com"],
                },
                {"name": "Jane", "email": "jane@example.com"},
            ],
            "system": {"admin_email": "admin@example.com"},
        }
        result = _redact_pii_recursive(data, patterns, "REDACTED")

        # Check nested dictionary
        assert result["users"][0]["email"] == "REDACTED"
        assert result["users"][1]["email"] == "REDACTED"
        assert result["system"]["admin_email"] == "REDACTED"

        # Check nested list
        assert result["users"][0]["contacts"][0] == "REDACTED"
        assert result["users"][0]["contacts"][1] == "REDACTED"

        # Check non-email values are preserved
        assert result["users"][0]["name"] == "John"
        assert result["users"][1]["name"] == "Jane"

    def test_preserve_non_strings(self):
        """Test that non-string values are preserved."""
        patterns = _compile_pii_patterns([r"[\w\.-]+@[\w\.-]+\.\w+"])
        data = {
            "id": 123,
            "active": True,
            "score": 95.5,
            "email": "user@example.com",
            "null_value": None,
        }
        result = _redact_pii_recursive(data, patterns, "REDACTED")
        assert result["id"] == 123
        assert result["active"] is True
        assert result["score"] == 95.5
        assert result["null_value"] is None
        assert result["email"] == "REDACTED"


class TestAutoRedactPIIProcessor:
    """Test the structlog processor for PII auto-detection."""

    def test_processor_creation(self):
        """Test creation of PII processor."""
        processor = auto_redact_pii_processor([r"[\w\.-]+@[\w\.-]+\.\w+"])
        assert callable(processor)

    def test_processor_with_no_patterns(self):
        """Test processor behavior with no patterns."""
        processor = auto_redact_pii_processor([])
        mock_logger = Mock()
        event_dict = {"message": "test", "email": "user@example.com"}
        result = processor(mock_logger, "info", event_dict)
        assert result == event_dict

    def test_processor_redaction(self):
        """Test processor redacts PII from event dict."""
        processor = auto_redact_pii_processor([r"[\w\.-]+@[\w\.-]+\.\w+"])
        mock_logger = Mock()
        event_dict = {
            "message": "User login",
            "user_email": "user@example.com",
            "status": "success",
        }
        result = processor(mock_logger, "info", event_dict)
        assert result["user_email"] == "REDACTED"
        assert result["message"] == "User login"
        assert result["status"] == "success"

    def test_processor_custom_replacement(self):
        """Test processor with custom replacement value."""
        processor = auto_redact_pii_processor(
            [r"[\w\.-]+@[\w\.-]+\.\w+"], replacement="MASKED"
        )
        mock_logger = Mock()
        event_dict = {"email": "user@example.com"}
        result = processor(mock_logger, "info", event_dict)
        assert result["email"] == "MASKED"

    def test_processor_nested_structures(self):
        """Test processor handles nested structures."""
        processor = auto_redact_pii_processor([r"[\w\.-]+@[\w\.-]+\.\w+"])
        mock_logger = Mock()
        event_dict = {
            "request": {
                "user": {"email": "user@example.com", "name": "John"},
                "contacts": ["admin@example.com", "support@example.com"],
            }
        }
        result = processor(mock_logger, "info", event_dict)
        assert result["request"]["user"]["email"] == "REDACTED"
        assert result["request"]["user"]["name"] == "John"
        assert result["request"]["contacts"][0] == "REDACTED"
        assert result["request"]["contacts"][1] == "REDACTED"


class TestIntegration:
    """Integration tests for PII redaction."""

    def test_default_patterns_work(self):
        """Test that default patterns actually work."""
        processor = auto_redact_pii_processor(DEFAULT_PII_PATTERNS)
        mock_logger = Mock()

        # Test email
        event_dict = {"email": "user@example.com"}
        result = processor(mock_logger, "info", event_dict)
        assert result["email"] == "REDACTED"

        # Test phone
        event_dict = {"phone": "555-123-4567"}
        result = processor(mock_logger, "info", event_dict)
        assert result["phone"] == "REDACTED"

        # Test credit card
        event_dict = {"card": "1234 5678 9012 3456"}
        result = processor(mock_logger, "info", event_dict)
        assert result["card"] == "REDACTED"

        # Test IP address
        event_dict = {"ip": "192.168.1.100"}
        result = processor(mock_logger, "info", event_dict)
        assert result["ip"] == "REDACTED"

    def test_mixed_content(self):
        """Test redaction in mixed content."""
        processor = auto_redact_pii_processor(DEFAULT_PII_PATTERNS)
        mock_logger = Mock()
        event_dict = {
            "message": "User login from 192.168.1.100",
            "user": {"email": "user@example.com", "phone": "555-123-4567"},
            "payment": {"card": "1234 5678 9012 3456"},
        }
        result = processor(mock_logger, "info", event_dict)

        # Check that PII is redacted
        assert result["user"]["email"] == "REDACTED"
        assert result["user"]["phone"] == "REDACTED"
        assert result["payment"]["card"] == "REDACTED"

        # Check that non-PII is preserved
        assert "User login from" in result["message"]
        assert result["message"] != "REDACTED"
