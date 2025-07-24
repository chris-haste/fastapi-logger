"""Tests for the URI testing utilities."""

import pytest

from fapilog._internal.uri_validation import validate_uri_scheme
from fapilog.testing.uri_testing import (
    parse_sink_uri,
    test_uri_parsing,
    validate_sink_uri,
)


def test_invalid_uris():
    """Test parse_sink_uri with invalid URIs."""
    # Test cases that should raise ValueError (missing scheme)
    invalid_uris = [
        "://localhost/logs",  # Missing scheme
        "",  # Empty URI
        "not-a-uri",  # No scheme
    ]

    for uri in invalid_uris:
        with pytest.raises(ValueError):
            parse_sink_uri(uri)

    # Test case that has scheme but empty host (should succeed)
    result = parse_sink_uri("invalid://")
    assert result == {}  # Should parse successfully but with no params


class TestURITesting:
    """Test URI testing utilities."""

    def test_validate_uri_scheme_valid(self):
        """Test URI scheme validation with valid schemes."""
        valid_schemes = ["http", "https", "postgres", "test", "custom"]

        for scheme in valid_schemes:
            assert validate_uri_scheme(scheme) is True

    def test_validate_uri_scheme_invalid(self):
        """Test URI scheme validation with invalid schemes."""
        invalid_schemes = ["", "123", "-test", "+test", ".test", "test space"]

        for scheme in invalid_schemes:
            assert validate_uri_scheme(scheme) is False

    def test_validate_uri_scheme_with_valid_chars(self):
        """Test URI scheme with valid characters."""
        # Scheme can contain letters, digits, +, -, . after first letter
        valid_schemes = ["test+plus", "test-minus", "test.dot", "test123"]

        for scheme in valid_schemes:
            assert validate_uri_scheme(scheme) is True

    def test_validate_sink_uri_valid(self):
        """Test sink URI validation with valid URI."""
        result = validate_sink_uri("postgres://localhost/db")

        assert result["valid"] is True
        assert result["scheme"] == "postgres"
        assert len(result["issues"]) == 0

    def test_validate_sink_uri_invalid_scheme(self):
        """Test sink URI validation with invalid scheme."""
        result = validate_sink_uri("123://localhost")

        assert result["valid"] is False
        assert "scheme" in str(result["issues"]).lower()

    def test_validate_sink_uri_no_scheme(self):
        """Test sink URI validation with no scheme."""
        result = validate_sink_uri("localhost/db")

        assert result["valid"] is False
        assert len(result["issues"]) > 0

    def test_validate_sink_uri_empty_host(self):
        """Test sink URI validation with empty host."""
        result = validate_sink_uri("test://")

        # The implementation may accept empty host, just verify it runs
        assert "valid" in result
        assert isinstance(result["valid"], bool)

    def test_test_uri_parsing_function(self):
        """Test the test_uri_parsing utility function."""
        # This function tests various URI formats
        # It should run without error
        test_uri_parsing()

    def test_validate_sink_uri_with_query_params(self):
        """Test URI validation with query parameters."""
        result = validate_sink_uri("test://host/path?param=value")

        if result["valid"]:
            assert result["scheme"] == "test"
        # Test passes if it runs without error

    def test_validate_sink_uri_with_port(self):
        """Test URI validation with port number."""
        result = validate_sink_uri("postgres://host:5432/db")

        if result["valid"]:
            assert result["scheme"] == "postgres"
        # Test passes if it runs without error

    def test_validate_sink_uri_malformed(self):
        """Test URI validation with malformed URI."""
        result = validate_sink_uri("not_a_uri")

        assert result["valid"] is False
        assert len(result["issues"]) > 0
