"""Comprehensive tests for URI validation to achieve 100% coverage."""

from unittest.mock import patch

import pytest

from fapilog._internal.uri_validation import (
    check_scheme_with_helpful_error,
    suggest_valid_scheme_name,
    validate_uri_format,
    validate_uri_scheme,
)


class TestURIValidationComprehensive:
    """Comprehensive tests for URI validation functions."""

    def test_validate_uri_scheme_edge_cases(self):
        """Test edge cases for URI scheme validation."""
        # Empty string
        assert validate_uri_scheme("") is False

        # Single character schemes
        assert validate_uri_scheme("a") is True
        assert validate_uri_scheme("A") is True
        assert validate_uri_scheme("1") is False  # starts with digit

        # Valid complex schemes
        assert validate_uri_scheme("http") is True
        assert validate_uri_scheme("my-scheme") is True
        assert validate_uri_scheme("scheme.v2") is True
        assert validate_uri_scheme("redis+cluster") is True

        # Invalid schemes
        assert validate_uri_scheme("_scheme") is False  # starts with underscore
        assert validate_uri_scheme("-scheme") is False  # starts with dash
        assert validate_uri_scheme(".scheme") is False  # starts with dot
        assert validate_uri_scheme("+scheme") is False  # starts with plus
        assert validate_uri_scheme("my_scheme") is False  # contains underscore
        assert validate_uri_scheme("my scheme") is False  # contains space
        assert validate_uri_scheme("my@scheme") is False  # contains invalid char

    def test_validate_uri_format_exception_handling(self):
        """Test exception handling in validate_uri_format."""
        # Test with malformed URI that causes urlparse to fail
        with patch("urllib.parse.urlparse") as mock_urlparse:
            mock_urlparse.side_effect = Exception("Parse error")

            result = validate_uri_format("malformed://uri", "test")
            assert result["valid"] is False
            assert len(result["issues"]) == 1
            assert "Failed to parse URI: Parse error" in result["issues"][0]

    def test_validate_uri_format_no_scheme_with_slashes(self):
        """Test URIs that have :// but no valid scheme."""
        # URI with :// but invalid scheme
        result = validate_uri_format("123invalid://localhost", "sink")
        assert result["valid"] is False
        assert any(
            "Invalid URI scheme '123invalid'" in issue for issue in result["issues"]
        )
        assert any("underscores" in issue for issue in result["issues"])

    def test_validate_uri_format_no_scheme_without_slashes(self):
        """Test URIs without schemes."""
        result = validate_uri_format("localhost/db", "enricher")
        assert result["valid"] is False
        assert any("URI must have a scheme" in issue for issue in result["issues"])
        assert any("enricher" in issue for issue in result["issues"])

    def test_validate_uri_format_potential_scheme_detection(self):
        """Test detection of potential invalid schemes in URIs with ://."""
        # Test case where URI has :// but scheme before it is invalid
        result = validate_uri_format("my_invalid_scheme://localhost", "sink")
        assert result["valid"] is False
        assert any(
            "Invalid URI scheme 'my_invalid_scheme'" in issue
            for issue in result["issues"]
        )
        assert any("underscores" in issue for issue in result["issues"])

    def test_check_scheme_with_helpful_error_edge_cases(self):
        """Test edge cases for check_scheme_with_helpful_error."""
        # Test with None
        with pytest.raises(ValueError) as exc:
            check_scheme_with_helpful_error(None, "test")
        assert "URI must be a non-empty string" in str(exc.value)

        # Test with empty string
        with pytest.raises(ValueError) as exc:
            check_scheme_with_helpful_error("", "test")
        assert "URI must be a non-empty string" in str(exc.value)

        # Test with non-string
        with pytest.raises(ValueError) as exc:
            check_scheme_with_helpful_error(123, "test")
        assert "URI must be a non-empty string" in str(exc.value)

    def test_check_scheme_with_helpful_error_parse_exception(self):
        """Test exception handling during URI parsing."""
        with patch("urllib.parse.urlparse") as mock_urlparse:
            mock_urlparse.side_effect = Exception("Parsing failed")

            with pytest.raises(ValueError) as exc:
                check_scheme_with_helpful_error("valid://uri", "test")
            assert "Invalid URI format: Parsing failed" in str(exc.value)

    def test_check_scheme_with_helpful_error_no_scheme(self):
        """Test error when URI has no scheme."""
        with pytest.raises(ValueError) as exc:
            check_scheme_with_helpful_error("localhost/database", "enricher")
        assert "URI must include a scheme" in str(exc.value)
        assert "enricher" in str(exc.value)

    def test_check_scheme_with_helpful_error_invalid_scheme_no_underscore(self):
        """Test error for invalid scheme without underscores."""
        with pytest.raises(ValueError) as exc:
            check_scheme_with_helpful_error("123invalid://localhost", "sink")
        assert "Invalid URI scheme '123invalid'" in str(exc.value)
        assert "underscores" in str(exc.value)
        assert "Try using hyphens instead: '123invalid://...'" in str(exc.value)

    def test_check_scheme_with_helpful_error_invalid_scheme_with_underscore(self):
        """Test error for invalid scheme with underscores."""
        with pytest.raises(ValueError) as exc:
            check_scheme_with_helpful_error("my_scheme://localhost", "enricher")
        assert "Invalid URI scheme 'my_scheme'" in str(exc.value)
        assert "underscores" in str(exc.value)
        assert "Try using hyphens instead: 'my-scheme://...'" in str(exc.value)

    def test_check_scheme_potential_invalid_scheme(self):
        """Test detection of potential invalid schemes."""
        # Test scheme with underscores
        with pytest.raises(ValueError) as exc:
            check_scheme_with_helpful_error("my_test_scheme://host", "component")
        assert "Invalid URI scheme 'my_test_scheme'" in str(exc.value)
        assert "Try using hyphens instead: 'my-test-scheme://...'" in str(exc.value)

        # Test scheme starting with number
        with pytest.raises(ValueError) as exc:
            check_scheme_with_helpful_error("2cache://host", "component")
        assert "Invalid URI scheme '2cache'" in str(exc.value)

    def test_suggest_valid_scheme_name_edge_cases(self):
        """Test edge cases for scheme name suggestions."""
        # Empty string
        assert suggest_valid_scheme_name("") == "my-scheme"

        # String with only invalid characters
        assert suggest_valid_scheme_name("@#$%") == "scheme-----"

        # String starting with number
        assert suggest_valid_scheme_name("123") == "scheme-123"

        # String with mixed invalid characters
        assert suggest_valid_scheme_name("my@test$scheme") == "my-test-scheme"

        # String starting with underscore
        assert suggest_valid_scheme_name("_test") == "scheme--test"

        # String with multiple underscores
        assert suggest_valid_scheme_name("my__test__scheme") == "my--test--scheme"

        # String with valid characters only
        assert suggest_valid_scheme_name("valid-scheme") == "valid-scheme"

    def test_validate_uri_format_successful_parsing(self):
        """Test successful URI format validation."""
        result = validate_uri_format("https://example.com:443/path?query=value", "sink")
        assert result["valid"] is True
        assert len(result["issues"]) == 0
        assert result["scheme"] == "https"
        assert result["parsed"] is not None
        assert result["parsed"].netloc == "example.com:443"

    def test_validate_uri_format_invalid_scheme_in_parsed_uri(self):
        """Test validation when parsed URI has invalid scheme."""
        # This tests the case where urlparse succeeds but scheme is invalid
        result = validate_uri_format("my_invalid://localhost", "enricher")
        assert result["valid"] is False
        # The scheme is detected as invalid and handled in early validation
        assert any(
            "Invalid URI scheme 'my_invalid'" in issue for issue in result["issues"]
        )

    def test_check_scheme_return_valid_scheme(self):
        """Test that valid schemes are returned correctly."""
        valid_schemes_and_uris = [
            ("http://example.com", "http"),
            ("my-scheme://localhost", "my-scheme"),
            ("redis+cluster://host:6379", "redis+cluster"),
            ("s3.backup://bucket/path", "s3.backup"),
        ]

        for uri, expected_scheme in valid_schemes_and_uris:
            scheme = check_scheme_with_helpful_error(uri, "test")
            assert scheme == expected_scheme

    def test_component_type_in_error_messages(self):
        """Test that component type appears in error messages."""
        # Test with sink component type
        result = validate_uri_format("localhost/path", "sink")
        assert result["valid"] is False
        assert any("sink" in issue for issue in result["issues"])

        # Test with enricher component type
        result = validate_uri_format("localhost/path", "enricher")
        assert result["valid"] is False
        assert any("enricher" in issue for issue in result["issues"])

        # Test in check_scheme_with_helpful_error
        with pytest.raises(ValueError) as exc:
            check_scheme_with_helpful_error("localhost/path", "custom-component")
        assert "custom-component" in str(exc.value)

    def test_all_validation_paths_covered(self):
        """Integration test to ensure all validation paths are covered."""
        # Test successful validation path
        result = validate_uri_format("valid://host:1234/path", "test")
        assert result["valid"] is True

        # Test exception path
        with patch("urllib.parse.urlparse", side_effect=Exception("error")):
            result = validate_uri_format("any://uri", "test")
            assert result["valid"] is False

        # Test no scheme path
        result = validate_uri_format("/path/only", "test")
        assert result["valid"] is False

        # Test invalid scheme in detected potential scheme
        result = validate_uri_format("_invalid://host", "test")
        assert result["valid"] is False

        # Test valid scheme but parsed as invalid
        result = validate_uri_format("my_scheme://host", "test")
        assert result["valid"] is False

    def test_validate_uri_format_parsed_scheme_validation_coverage(self):
        """Test to cover the parsed scheme validation path in validate_uri_format."""
        # Mock urlparse to return a result with invalid scheme
        # This covers lines 75-76 where the parsed scheme is validated
        from urllib.parse import ParseResult

        mock_result = ParseResult(
            scheme="invalid_scheme",
            netloc="localhost",
            path="",
            params="",
            query="",
            fragment="",
        )

        with patch("urllib.parse.urlparse", return_value=mock_result):
            result = validate_uri_format("invalid_scheme://localhost", "test")
            assert result["valid"] is False
            assert result["scheme"] == "invalid_scheme"
            assert any(
                "Invalid URI scheme 'invalid_scheme'" in issue
                for issue in result["issues"]
            )

    def test_check_scheme_invalid_without_underscore_coverage(self):
        """Test to cover the suggestion path without underscores in check_scheme_with_helpful_error."""
        # This covers lines 127-128 where scheme doesn't contain underscores
        # Mock urlparse to return an invalid scheme without underscores
        from urllib.parse import ParseResult

        mock_result = ParseResult(
            scheme="123invalid",
            netloc="localhost",
            path="",
            params="",
            query="",
            fragment="",
        )

        with patch("urllib.parse.urlparse", return_value=mock_result):
            with pytest.raises(ValueError) as exc:
                check_scheme_with_helpful_error("123invalid://localhost", "test")

            error_msg = str(exc.value)
            assert "Invalid URI scheme '123invalid'" in error_msg
            assert "Try using hyphens instead: '123invalid://...'" in error_msg

    def test_check_scheme_invalid_scheme_no_underscore_real_uri(self):
        """Test to cover the exact path for invalid scheme without underscores."""
        # This will test the 'else' branch in line 127: parsed.scheme (no underscores)
        # Use a real URI that will be parsed but has an invalid scheme without underscores
        with pytest.raises(ValueError) as exc:
            check_scheme_with_helpful_error("9invalid://localhost", "test")

        error_msg = str(exc.value)
        assert "Invalid URI scheme '9invalid'" in error_msg
        # This should use the original scheme name as suggestion (no underscore replacement)
        assert "Try using hyphens instead: '9invalid://...'" in error_msg


if __name__ == "__main__":
    pytest.main([__file__])
