"""Shared URI validation utilities for sinks and enrichers."""

import re
import urllib.parse
from typing import Any, Dict


def validate_uri_scheme(scheme: str) -> bool:
    """Validate that a URI scheme follows RFC 3986 rules.

    Valid characters: letters, digits, plus (+), period (.), hyphen (-)
    Must start with a letter.

    Args:
        scheme: The URI scheme to validate

    Returns:
        True if valid, False otherwise
    """
    if not scheme:
        return False

    # Must start with a letter
    if not scheme[0].isalpha():
        return False

    # Valid characters: letters, digits, +, -, .
    valid_pattern = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*$")
    return bool(valid_pattern.match(scheme))


def validate_uri_format(uri: str, component_type: str = "component") -> Dict[str, Any]:
    """Validate a URI and return detailed validation results.

    Args:
        uri: The URI to validate
        component_type: Type of component ("sink" or "enricher")

    Returns:
        Dictionary with validation results and any issues found
    """
    result: Dict[str, Any] = {
        "valid": True,
        "issues": [],
        "scheme": None,
        "parsed": None,
    }

    try:
        parsed = urllib.parse.urlparse(uri)
        result["parsed"] = parsed
        result["scheme"] = parsed.scheme

        # Check if URI looks like it should have a scheme but Python didn't detect one
        if not parsed.scheme and "://" in uri:
            # Extract the part before :// and check if it's an invalid scheme
            potential_scheme = uri.split("://")[0]
            if not validate_uri_scheme(potential_scheme):
                result["valid"] = False
                result["issues"].append(
                    f"Invalid URI scheme '{potential_scheme}'. "
                    "Schemes can only contain letters, digits, +, -, . and must start with a letter. "
                    "Note: underscores (_) are not allowed in URI schemes."
                )
                return result

        if not parsed.scheme:
            result["valid"] = False
            result["issues"].append(
                f"URI must have a scheme (e.g., postgres:// for {component_type}s)"
            )
            return result

        if not validate_uri_scheme(parsed.scheme):
            result["valid"] = False
            result["issues"].append(
                f"Invalid URI scheme '{parsed.scheme}'. "
                "Schemes can only contain letters, digits, +, -, . and must start with a letter. "
                "Note: underscores (_) are not allowed in URI schemes."
            )

    except Exception as e:
        result["valid"] = False
        result["issues"].append(f"Failed to parse URI: {e}")

    return result


def check_scheme_with_helpful_error(uri: str, component_type: str = "component") -> str:
    """Check URI scheme and return the scheme or raise with helpful error.

    Args:
        uri: URI string to validate
        component_type: Type of component ("sink" or "enricher")

    Returns:
        Valid scheme name

    Raises:
        ValueError: If scheme is invalid with helpful error message
    """
    if not uri or not isinstance(uri, str):
        raise ValueError("URI must be a non-empty string")

    # Check if it looks like it should have a scheme but doesn't parse correctly
    if "://" in uri:
        potential_scheme = uri.split("://")[0]
        if not validate_uri_scheme(potential_scheme):
            raise ValueError(
                f"Invalid URI scheme '{potential_scheme}'. "
                "Schemes can only contain letters, digits, +, -, . and must start with a letter. "
                f"Note: underscores (_) are not allowed in URI schemes. "
                f"Try using hyphens instead: '{potential_scheme.replace('_', '-')}://...'"
            )

    try:
        parsed = urllib.parse.urlparse(uri)
    except Exception as e:
        raise ValueError(f"Invalid URI format: {e}") from e

    if not parsed.scheme:
        raise ValueError(
            f"URI must include a scheme (e.g., 'myscheme://...' for {component_type}s)"
        )

    if not validate_uri_scheme(parsed.scheme):
        suggestion = (
            parsed.scheme.replace("_", "-") if "_" in parsed.scheme else parsed.scheme
        )
        raise ValueError(
            f"Invalid URI scheme '{parsed.scheme}'. "
            "Schemes can only contain letters, digits, +, -, . and must start with a letter. "
            f"Note: underscores (_) are not allowed in URI schemes. "
            f"Try using hyphens instead: '{suggestion}://...'"
        )

    return parsed.scheme


def suggest_valid_scheme_name(invalid_scheme: str) -> str:
    """Suggest a valid scheme name based on an invalid one.

    Args:
        invalid_scheme: The invalid scheme name

    Returns:
        Suggested valid scheme name
    """
    # Replace underscores with hyphens
    suggestion = invalid_scheme.replace("_", "-")

    # Ensure it starts with a letter
    if suggestion and not suggestion[0].isalpha():
        suggestion = "scheme-" + suggestion

    # Remove any other invalid characters
    suggestion = re.sub(r"[^a-zA-Z0-9+.-]", "-", suggestion)

    return suggestion or "my-scheme"
