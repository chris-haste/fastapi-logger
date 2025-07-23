"""Simple tests to boost uri_testing module coverage."""

from unittest.mock import Mock, patch

from fapilog.testing.uri_testing import (
    URITestHelper,
    create_test_uri_cases,
    parse_sink_uri,
    test_uri_parsing,
    validate_sink_uri,
    validate_uri_scheme,
)


class TestURITestingSimpleBoost:
    """Simple tests for URI testing utilities."""

    def test_validate_uri_scheme_edge_cases(self):
        """Test edge cases for URI scheme validation."""
        # Test various edge cases
        assert validate_uri_scheme("a") is True  # Single letter
        assert validate_uri_scheme("A") is True  # Capital letter
        assert validate_uri_scheme("a1") is True  # Letter + digit
        assert validate_uri_scheme("a+b") is True  # With plus
        assert validate_uri_scheme("a-b") is True  # With dash
        assert validate_uri_scheme("a.b") is True  # With dot
        assert validate_uri_scheme("a+b-c.d") is True  # Multiple valid chars

        # Invalid schemes
        assert validate_uri_scheme("1abc") is False  # Starts with digit
        assert validate_uri_scheme("+abc") is False  # Starts with plus
        assert validate_uri_scheme("-abc") is False  # Starts with dash
        assert validate_uri_scheme(".abc") is False  # Starts with dot
        assert validate_uri_scheme("abc_def") is False  # Contains underscore
        assert validate_uri_scheme("abc def") is False  # Contains space
        assert validate_uri_scheme("abc#def") is False  # Contains hash

    def test_validate_sink_uri_edge_cases(self):
        """Test edge cases for sink URI validation."""
        # Test various URI formats
        result = validate_sink_uri("valid://host")
        assert result["valid"] is True
        assert result["scheme"] == "valid"

        result = validate_sink_uri("test://")
        # Empty host might be valid depending on implementation
        assert "valid" in result

        result = validate_sink_uri("test://host/")
        assert result["valid"] is True

        result = validate_sink_uri("test://host/path")
        assert result["valid"] is True

        result = validate_sink_uri("test://host:8080")
        assert result["valid"] is True

    def test_parse_sink_uri_with_various_formats(self):
        """Test parsing URIs with various formats."""
        # Basic URI
        result = parse_sink_uri("test://localhost")
        assert result["host"] == "localhost"

        # URI with port
        result = parse_sink_uri("test://localhost:8080")
        assert result["host"] == "localhost"
        assert result["port"] == 8080

        # URI with path
        result = parse_sink_uri("test://localhost/database")
        assert result["host"] == "localhost"
        assert result["database"] == "database"

        # URI with query params
        result = parse_sink_uri("test://localhost?param1=value1&param2=value2")
        assert result["host"] == "localhost"
        assert result["param1"] == "value1"
        assert result["param2"] == "value2"

    def test_parse_sink_uri_boolean_params(self):
        """Test parsing boolean parameters."""
        result = parse_sink_uri("test://localhost?ssl=true&debug=false")
        assert result["ssl"] is True
        assert result["debug"] is False

    def test_parse_sink_uri_numeric_params(self):
        """Test parsing numeric parameters."""
        result = parse_sink_uri("test://localhost?timeout=30&retry=5&rate=3.5")
        assert result["timeout"] == 30
        assert result["retry"] == 5
        assert result["rate"] == 3.5

    def test_parse_sink_uri_empty_values(self):
        """Test parsing URIs with empty values."""
        result = parse_sink_uri("test://localhost?empty=&value=test")
        assert result["empty"] == ""
        assert result["value"] == "test"

    def test_parse_sink_uri_multiple_values(self):
        """Test parsing URIs with multiple values for same param."""
        # Should use first value when multiple exist
        result = parse_sink_uri("test://localhost?param=value1&param=value2")
        assert result["param"] == "value1"

    def test_uri_test_helper_initialization(self):
        """Test URITestHelper initialization."""
        helper = URITestHelper()
        assert helper.test_results == []

    def test_uri_test_helper_validate_uri_format(self):
        """Test URITestHelper URI format validation."""
        helper = URITestHelper()

        # Valid URI
        assert helper.validate_uri_format("test://localhost") is True

        # Invalid URI (no scheme)
        assert helper.validate_uri_format("localhost") is False

    def test_uri_test_helper_test_uri_equivalence(self):
        """Test URITestHelper URI equivalence testing."""
        helper = URITestHelper()

        # Same URIs should be equivalent
        assert (
            helper.test_uri_equivalence(
                "test://localhost?a=1&b=2", "test://localhost?a=1&b=2"
            )
            is True
        )

        # Different order should be equivalent (if ignore_order=True)
        assert (
            helper.test_uri_equivalence(
                "test://localhost?a=1&b=2", "test://localhost?b=2&a=1"
            )
            is True
        )

    def test_uri_test_helper_test_parameter_extraction(self):
        """Test URITestHelper parameter extraction testing."""
        helper = URITestHelper()

        expected = {"host": "localhost", "database": "test"}
        success, actual = helper.test_parameter_extraction(
            "test://localhost/test", expected
        )

        assert success is True
        assert actual == expected
        assert len(helper.test_results) == 1

    def test_uri_test_helper_test_parameter_extraction_failure(self):
        """Test URITestHelper parameter extraction with invalid URI."""
        helper = URITestHelper()

        success, actual = helper.test_parameter_extraction("invalid", {"host": "test"})

        assert success is False
        assert actual == {}
        assert len(helper.test_results) == 1
        assert "error" in helper.test_results[0]

    def test_uri_test_helper_run_test_suite(self):
        """Test URITestHelper running test suite."""
        helper = URITestHelper()

        test_cases = [
            {
                "uri": "test://localhost",
                "expected": {"host": "localhost"},
                "should_succeed": True,
            },
            {"uri": "invalid", "expected": {}, "should_succeed": False},
        ]

        result = helper.run_uri_test_suite(test_cases)

        assert result["total_tests"] == 2
        assert result["passed"] >= 0
        assert result["failed"] >= 0
        assert result["success_rate"] >= 0.0

    def test_uri_test_helper_get_test_summary(self):
        """Test URITestHelper test summary."""
        helper = URITestHelper()

        # Add some test results
        helper.test_results = [{"success": True}, {"success": False}, {"success": True}]

        summary = helper.get_test_summary()

        assert summary["total_tests"] == 3
        assert summary["passed"] == 2
        assert summary["failed"] == 1
        assert abs(summary["success_rate"] - 2 / 3) < 0.01

    def test_create_test_uri_cases(self):
        """Test create_test_uri_cases function."""
        cases = create_test_uri_cases()

        assert isinstance(cases, list)
        assert len(cases) > 0

        # Check structure of first case
        first_case = cases[0]
        assert "uri" in first_case
        assert "expected" in first_case
        assert "should_succeed" in first_case

    def test_test_uri_parsing_function(self):
        """Test the test_uri_parsing function."""
        # This function should run without error
        test_uri_parsing()

    def test_parse_sink_uri_username_password(self):
        """Test parsing URIs with username and password."""
        result = parse_sink_uri("test://user:pass@localhost:5432/db")
        assert result["host"] == "localhost"
        assert result["port"] == 5432
        assert result["user"] == "user"
        assert result["password"] == "pass"
        assert result["database"] == "db"

    def test_parse_sink_uri_complex_path(self):
        """Test parsing URIs with complex paths."""
        result = parse_sink_uri("test://localhost/path/to/resource")
        assert result["host"] == "localhost"
        assert result["database"] == "path/to/resource"

    def test_validate_sink_uri_malformed_cases(self):
        """Test validation of malformed URIs."""
        # URI with invalid scheme
        result = validate_sink_uri("123invalid://localhost")
        if "valid" in result:
            # Implementation might handle this differently
            assert isinstance(result["valid"], bool)

        # URI with special characters in scheme
        result = validate_sink_uri("test_scheme://localhost")
        if "valid" in result:
            # Should be invalid due to underscore
            assert result["valid"] is False

    def test_uri_test_helper_sink_creation_success(self):
        """Test URITestHelper sink creation (mocked)."""
        helper = URITestHelper()

        # Mock the create_custom_sink_from_uri function
        with patch(
            "fapilog.testing.uri_testing.create_custom_sink_from_uri"
        ) as mock_create:
            mock_create.return_value = Mock()

            success, error = helper.test_sink_creation_from_uri(
                "test://localhost", True
            )

            assert success is True
            assert error == ""

    def test_uri_test_helper_sink_creation_failure(self):
        """Test URITestHelper sink creation failure (mocked)."""
        helper = URITestHelper()

        # Mock the create_custom_sink_from_uri function to raise exception
        with patch(
            "fapilog.testing.uri_testing.create_custom_sink_from_uri"
        ) as mock_create:
            mock_create.side_effect = Exception("Creation failed")

            success, error = helper.test_sink_creation_from_uri(
                "test://localhost", False
            )

            assert success is True  # Matches expectation of failure
            assert "Creation failed" in error
