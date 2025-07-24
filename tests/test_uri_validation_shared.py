"""Tests for shared URI validation utilities."""

import pytest

from fapilog._internal.enricher_factory import EnricherFactory
from fapilog._internal.enricher_registry import EnricherRegistry
from fapilog._internal.uri_validation import (
    check_scheme_with_helpful_error,
    suggest_valid_scheme_name,
    validate_uri_format,
    validate_uri_scheme,
)
from fapilog.exceptions import EnricherConfigurationError


class TestSharedURIValidation:
    """Test shared URI validation utilities."""

    def test_validate_uri_scheme_valid(self):
        """Test URI scheme validation with valid schemes."""
        valid_schemes = [
            "http",
            "https",
            "postgres",
            "test",
            "custom",
            "my-sink",
            "s3.backup",
            "redis+cluster",
            "a",
            "A1",
        ]

        for scheme in valid_schemes:
            assert validate_uri_scheme(scheme) is True, f"'{scheme}' should be valid"

    def test_validate_uri_scheme_invalid(self):
        """Test URI scheme validation with invalid schemes."""
        invalid_schemes = [
            "",
            "123",
            "-test",
            "+test",
            ".test",
            "test space",
            "my_sink",
            "cache_v2",
            "queue_manager",
            "test@host",
        ]

        for scheme in invalid_schemes:
            assert validate_uri_scheme(scheme) is False, f"'{scheme}' should be invalid"

    def test_validate_uri_format_valid(self):
        """Test URI format validation with valid URIs."""
        valid_uris = [
            "postgres://localhost/db",
            "my-sink://host:1234/path",
            "https://example.com:443/api",
            "custom://user:pass@host:5432/db?ssl=true",
        ]

        for uri in valid_uris:
            result = validate_uri_format(uri, "test")
            assert result["valid"] is True, f"'{uri}' should be valid"
            assert len(result["issues"]) == 0

    def test_validate_uri_format_invalid_scheme(self):
        """Test URI format validation with invalid schemes."""
        invalid_uris = [
            "my_sink://localhost",  # underscore
            "2invalid://localhost",  # starts with digit
            "test@host://localhost",  # special char
        ]

        for uri in invalid_uris:
            result = validate_uri_format(uri, "test")
            assert result["valid"] is False, f"'{uri}' should be invalid"
            assert len(result["issues"]) > 0
            assert "underscores" in str(result["issues"]) or "Invalid" in str(
                result["issues"]
            )

    def test_check_scheme_with_helpful_error_valid(self):
        """Test scheme checking with valid URIs."""
        valid_uris = [
            "postgres://localhost/db",
            "my-sink://host:1234/path",
        ]

        for uri in valid_uris:
            scheme = check_scheme_with_helpful_error(uri, "test")
            assert scheme in ["postgres", "my-sink"]

    def test_check_scheme_with_helpful_error_invalid(self):
        """Test scheme checking with invalid URIs gives helpful errors."""
        # Invalid scheme with underscore
        with pytest.raises(ValueError) as exc:
            check_scheme_with_helpful_error("my_sink://localhost", "test")

        error_msg = str(exc.value)
        assert "my_sink" in error_msg
        assert "underscores" in error_msg
        assert "Try using hyphens instead: 'my-sink://...'" in error_msg

        # No scheme
        with pytest.raises(ValueError) as exc:
            check_scheme_with_helpful_error("localhost/db", "test")

        error_msg = str(exc.value)
        assert "must include a scheme" in error_msg

    def test_suggest_valid_scheme_name(self):
        """Test scheme name suggestions."""
        suggestions = [
            ("my_sink", "my-sink"),
            ("cache_v2", "cache-v2"),
            ("2invalid", "scheme-2invalid"),
            ("test@host", "test-host"),
            ("_underscore", "scheme--underscore"),
        ]

        for invalid, expected in suggestions:
            result = suggest_valid_scheme_name(invalid)
            assert result == expected, (
                f"Expected '{expected}' for '{invalid}', got '{result}'"
            )

    def test_enricher_factory_uses_shared_validation(self):
        """Test that enricher factory uses shared validation."""
        # Clear registry
        EnricherRegistry.clear_registry()

        # Register a test enricher
        class TestEnricher:
            def __init__(self, **kwargs):
                pass

        EnricherRegistry.register("testscheme", TestEnricher, "Test")

        # Valid URI should work
        enricher = EnricherFactory.create_enricher_from_uri("testscheme://localhost")
        assert isinstance(enricher, TestEnricher)

        # Invalid URI with underscore should give helpful error
        with pytest.raises(EnricherConfigurationError) as exc:
            EnricherFactory.create_enricher_from_uri("test_scheme://localhost")

        error_msg = str(exc.value)
        assert "test_scheme" in error_msg
        assert "underscores" in error_msg
        assert "Try using hyphens instead: 'test-scheme://...'" in error_msg

    def test_consistent_error_messages_across_components(self):
        """Test that sinks and enrichers give consistent error messages."""
        from fapilog.testing import validate_sink_uri

        # Test same invalid URI for both components
        invalid_uri = "my_sink://localhost"

        # Sink validation
        sink_result = validate_sink_uri(invalid_uri)
        assert sink_result["valid"] is False
        sink_issues = " ".join(sink_result["issues"])

        # Enricher validation
        enricher_result = validate_uri_format(invalid_uri, "enricher")
        assert enricher_result["valid"] is False
        enricher_issues = " ".join(enricher_result["issues"])

        # Both should mention underscores
        assert "underscores" in sink_issues
        assert "underscores" in enricher_issues

        # Both should mention the invalid scheme
        assert "my_sink" in sink_issues
        assert "my_sink" in enricher_issues

    def test_component_type_in_error_messages(self):
        """Test that component type is included in error messages."""
        # Test with no scheme
        sink_result = validate_uri_format("localhost/db", "sink")
        assert "sink" in " ".join(sink_result["issues"])

        enricher_result = validate_uri_format("localhost/db", "enricher")
        assert "enricher" in " ".join(enricher_result["issues"])
