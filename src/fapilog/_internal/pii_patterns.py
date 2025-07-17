"""PII (Personally Identifiable Information) detection patterns and processor."""

import re
from typing import Any, Dict, List

from ..redactors import _should_redact_at_level

# NOTE: The order of patterns below is IMPORTANT.
# More specific patterns (e.g., credit card, IP) must come BEFORE more general patterns (e.g., phone, email).
# This prevents general patterns from redacting parts of values that should be matched by specific patterns.
# Always list the most specific patterns first.
#
# Example: If the phone pattern comes before the credit card pattern, it may redact part of a credit card number before the card pattern can match.

# Default PII regex patterns
DEFAULT_PII_PATTERNS = [
    # Credit card numbers (strict 16-digit, not Luhn validation, no overlap, no capture)
    r"\b\d{4}(?:[ -]?\d{4}){3}\b",
    # IPv4 addresses
    r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    # Phone numbers (various formats)
    r"(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}",
    # Email addresses
    r"[\w\.-]+@[\w\.-]+\.\w+",
]


def _compile_pii_patterns(patterns: List[str]) -> List[re.Pattern[str]]:
    """Compile regex patterns for PII detection.

    Args:
        patterns: List of regex pattern strings

    Returns:
        List of compiled regex patterns
    """
    compiled_patterns = []
    for pattern in patterns:
        try:
            compiled_patterns.append(re.compile(pattern, re.IGNORECASE))
        except re.error as e:
            # Log warning but continue with other patterns
            print(f"Warning: Invalid PII pattern '{pattern}': {e}")
    return compiled_patterns


def _redact_string_value(
    value: str, patterns: List[re.Pattern[str]], replacement: str
) -> str:
    """Redact PII from a string value using non-overlapping matches."""
    redacted_value = value
    for pattern in patterns:
        matches = list(pattern.finditer(redacted_value))
        for match in reversed(matches):
            start, end = match.span()
            if redacted_value[start:end] != replacement:
                redacted_value = (
                    redacted_value[:start] + replacement + redacted_value[end:]
                )
        if redacted_value == replacement:
            break
    return redacted_value


def _redact_pii_recursive(
    data: Any, patterns: List[re.Pattern[str]], replacement: str
) -> Any:
    """Recursively redact PII from data structures.

    Args:
        data: The data to process (dict, list, or primitive)
        patterns: List of compiled regex patterns
        replacement: Replacement string for matches

    Returns:
        The data with PII redacted
    """
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            result[key] = _redact_pii_recursive(value, patterns, replacement)
        return result
    elif isinstance(data, list):
        return [_redact_pii_recursive(item, patterns, replacement) for item in data]
    elif isinstance(data, str):
        return _redact_string_value(data, patterns, replacement)
    else:
        # For non-string primitives (int, float, bool, None), return as-is
        return data


def auto_redact_pii_processor(
    patterns: List[str], replacement: str = "REDACTED", redact_level: str = "INFO"
) -> Any:
    """Create a PII auto-detection processor for structlog.

    Args:
        patterns: List of regex patterns for PII detection
        replacement: Replacement value for detected PII
        redact_level: Minimum log level for redaction to be applied

    Returns:
        A processor function that automatically redacts PII
    """
    if not patterns:
        return lambda logger, method_name, event_dict: event_dict

    compiled_patterns = _compile_pii_patterns(patterns)

    def pii_processor(
        logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Automatically detect and redact PII from log entries.

        Args:
            logger: The logger instance
            method_name: The logging method name
            event_dict: The event dictionary to process

        Returns:
            The event dictionary with PII redacted
        """
        # Check if redaction should be applied based on log level
        event_level = event_dict.get("level", "INFO")
        if not _should_redact_at_level(event_level, redact_level):
            return event_dict

        result = _redact_pii_recursive(event_dict, compiled_patterns, replacement)
        return result if isinstance(result, dict) else event_dict

    return pii_processor
