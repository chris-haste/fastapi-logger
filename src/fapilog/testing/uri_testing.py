"""URI testing utilities for sink configuration."""

from typing import Any, Dict, List, Tuple
from urllib.parse import parse_qs, urlparse

import pytest

from .._internal.sink_factory import SinkConfigurationError, create_custom_sink_from_uri
from .._internal.uri_validation import validate_uri_format


def validate_sink_uri(uri: str) -> Dict[str, Any]:
    """Validate a sink URI and return detailed validation results.

    Args:
        uri: The URI to validate

    Returns:
        Dictionary with validation results and any issues found
    """
    # Use the shared validation function
    return validate_uri_format(uri, "sink")


def parse_sink_uri(uri: str) -> Dict[str, Any]:
    """Parse a sink URI into component parameters.

    Args:
        uri: URI string to parse

    Returns:
        Dictionary of parsed parameters

    Raises:
        ValueError: If URI format is invalid
    """
    try:
        parsed = urlparse(uri)
    except Exception as e:
        raise ValueError(f"Invalid URI format: {e}") from e

    if not parsed.scheme:
        raise ValueError("URI must have a scheme (e.g., postgres://...)")

    result = {}

    # Basic components
    if parsed.hostname:
        result["host"] = parsed.hostname
    if parsed.port:
        result["port"] = parsed.port
    if parsed.username:
        result["user"] = parsed.username
    if parsed.password:
        result["password"] = parsed.password
    if parsed.path and parsed.path != "/":
        # Remove leading slash and use as database/path
        path = parsed.path.lstrip("/")
        if path:
            result["database"] = path

    # Parse query parameters
    if parsed.query:
        query_params = parse_qs(parsed.query, keep_blank_values=True)
        for key, values in query_params.items():
            # Use the first value if multiple values exist
            value = values[0] if values else ""
            # Try to convert to appropriate type
            if value.lower() in ("true", "false"):
                result[key] = value.lower() == "true"
            elif value.isdigit():
                result[key] = int(value)
            elif "." in value and value.replace(".", "").isdigit():
                result[key] = float(value)
            else:
                result[key] = value

    return result


def test_uri_parsing() -> None:
    """Test URI parsing for various sink types."""
    test_cases = [
        ("postgres://localhost/logs", {"host": "localhost", "database": "logs"}),
        (
            "postgres://user:pass@host:5432/db?ssl=true",
            {
                "host": "host",
                "port": 5432,
                "user": "user",
                "password": "pass",
                "database": "db",
                "ssl": True,
            },
        ),
        (
            "elasticsearch://localhost:9200/index",
            {"host": "localhost", "port": 9200, "database": "index"},
        ),
        (
            "redis://localhost:6379?db=1&timeout=30.5",
            {"host": "localhost", "port": 6379, "db": 1, "timeout": 30.5},
        ),
        (
            "custom://host/path?param1=value1&param2=value2",
            {
                "host": "host",
                "database": "path",
                "param1": "value1",
                "param2": "value2",
            },
        ),
    ]

    for uri, expected in test_cases:
        result = parse_sink_uri(uri)
        assert result == expected, f"Failed for {uri}: got {result}"


def test_invalid_uris() -> None:
    """Test error handling for invalid URIs."""
    invalid_uris = [
        "invalid://",
        "://localhost/logs",
        "",
        "not-a-uri",
    ]

    for uri in invalid_uris:
        with pytest.raises(ValueError):
            parse_sink_uri(uri)


class URITestHelper:
    """Helper class for testing URI-based sink configurations."""

    def __init__(self):
        self.test_results: List[Dict[str, Any]] = []

    def validate_uri_format(self, uri: str) -> bool:
        """Validate that a URI has correct format.

        Args:
            uri: URI string to validate

        Returns:
            True if URI format is valid
        """
        try:
            parse_sink_uri(uri)
            return True
        except ValueError:
            return False

    def test_uri_equivalence(
        self, uri1: str, uri2: str, ignore_order: bool = True
    ) -> bool:
        """Test if two URIs are functionally equivalent.

        Args:
            uri1: First URI to compare
            uri2: Second URI to compare
            ignore_order: Whether to ignore parameter order

        Returns:
            True if URIs are equivalent
        """
        try:
            params1 = parse_sink_uri(uri1)
            params2 = parse_sink_uri(uri2)
            return params1 == params2
        except ValueError:
            return False

    def test_parameter_extraction(
        self, uri: str, expected_params: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """Test parameter extraction from URI.

        Args:
            uri: URI to test
            expected_params: Expected parameters

        Returns:
            Tuple of (success, actual_params)
        """
        try:
            actual_params = parse_sink_uri(uri)
            success = actual_params == expected_params

            result = {
                "uri": uri,
                "expected": expected_params,
                "actual": actual_params,
                "success": success,
                "missing_keys": set(expected_params.keys()) - set(actual_params.keys()),
                "extra_keys": set(actual_params.keys()) - set(expected_params.keys()),
            }

            self.test_results.append(result)
            return success, actual_params

        except Exception as e:
            result = {
                "uri": uri,
                "expected": expected_params,
                "actual": {},
                "success": False,
                "error": str(e),
            }
            self.test_results.append(result)
            return False, {}

    def test_sink_creation_from_uri(
        self, uri: str, should_succeed: bool = True
    ) -> Tuple[bool, str]:
        """Test creating a sink from URI.

        Args:
            uri: URI to test
            should_succeed: Whether creation should succeed

        Returns:
            Tuple of (success_matches_expectation, error_message)
        """
        try:
            create_custom_sink_from_uri(uri)
            success = True
            error_msg = ""
        except (SinkConfigurationError, Exception) as e:
            success = False
            error_msg = str(e)

        matches_expectation = success == should_succeed

        result = {
            "uri": uri,
            "expected_success": should_succeed,
            "actual_success": success,
            "matches_expectation": matches_expectation,
            "error": error_msg,
        }
        self.test_results.append(result)

        return matches_expectation, error_msg

    def run_uri_test_suite(self, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run a comprehensive URI test suite.

        Args:
            test_cases: List of test case dictionaries with 'uri' and 'expected'

        Returns:
            Summary of test results
        """
        passed = 0
        failed = 0

        for test_case in test_cases:
            uri = test_case["uri"]
            expected = test_case.get("expected", {})
            should_succeed = test_case.get("should_succeed", True)

            # Test parameter extraction
            param_success, _ = self.test_parameter_extraction(uri, expected)

            # Test sink creation if expected to succeed
            if should_succeed:
                creation_success, _ = self.test_sink_creation_from_uri(
                    uri, should_succeed
                )
                overall_success = param_success and creation_success
            else:
                overall_success = not self.validate_uri_format(uri)

            if overall_success:
                passed += 1
            else:
                failed += 1

        return {
            "total_tests": len(test_cases),
            "passed": passed,
            "failed": failed,
            "success_rate": passed / len(test_cases) if test_cases else 0,
            "detailed_results": self.test_results.copy(),
        }

    def get_test_summary(self) -> Dict[str, Any]:
        """Get summary of all tests run.

        Returns:
            Summary dictionary
        """
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r.get("success", False))

        return {
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": passed / total if total > 0 else 0,
            "results": self.test_results,
        }

    def clear_results(self) -> None:
        """Clear all test results."""
        self.test_results.clear()


def create_test_uri_cases() -> List[Dict[str, Any]]:
    """Create a set of common test cases for URI parsing.

    Returns:
        List of test case dictionaries
    """
    return [
        {
            "uri": "postgres://localhost/logs",
            "expected": {"host": "localhost", "database": "logs"},
            "should_succeed": True,
        },
        {
            "uri": "postgres://user:pass@localhost:5432/db?ssl=true",
            "expected": {
                "host": "localhost",
                "port": 5432,
                "user": "user",
                "password": "pass",
                "database": "db",
                "ssl": True,
            },
            "should_succeed": True,
        },
        {
            "uri": "elasticsearch://localhost:9200/index?timeout=30",
            "expected": {
                "host": "localhost",
                "port": 9200,
                "database": "index",
                "timeout": 30,
            },
            "should_succeed": True,
        },
        {
            "uri": "invalid://",
            "expected": {},
            "should_succeed": False,
        },
        {
            "uri": "",
            "expected": {},
            "should_succeed": False,
        },
    ]
