"""PII (Personally Identifiable Information) detection patterns and processor."""

import re
from collections import deque
from typing import Any, List, cast

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
    """Apply PII redaction patterns to a string value."""
    for pattern in patterns:
        value = pattern.sub(replacement, value)
    return value


def _redact_pii_iterative(
    data: Any, patterns: List[re.Pattern[str]], replacement: str
) -> Any:
    """Iteratively redact PII from data structures using explicit stack.

    This replaces the recursive approach to eliminate O(n²) memory complexity
    and stack overflow issues for deeply nested structures.

    Args:
        data: The data to process (dict, list, or primitive)
        patterns: List of compiled regex patterns
        replacement: Replacement string for matches

    Returns:
        The data with PII redacted
    """
    if not isinstance(data, (dict, list)):
        # Handle primitive values directly
        if isinstance(data, str):
            return _redact_string_value(data, patterns, replacement)
        return data

    # For complex structures, we need to create a copy to avoid modifying original
    # and use iterative approach
    if isinstance(data, dict):
        result = {}
    else:  # list
        result = []

    # Stack contains: (source_obj, target_obj, processing_stage)
    # processing_stage: 'copy_structure' or 'process_values'
    stack = deque([(data, result, "copy_structure")])

    while stack:
        source, target, stage = stack.popleft()

        if stage == "copy_structure":
            if isinstance(source, dict):
                # Copy structure and schedule value processing
                target_dict = cast(dict, target)
                for key in source.keys():
                    target_dict[key] = None  # Placeholder
                # Schedule processing of values
                for key, value in source.items():
                    stack.append((value, target_dict, ("dict_value", key)))
            elif isinstance(source, list):
                # Create list structure and schedule item processing
                target_list = cast(list, target)
                target_list.extend([None] * len(source))
                for i, item in enumerate(source):
                    stack.append((item, target_list, ("list_item", i)))

        elif isinstance(stage, tuple) and stage[0] == "dict_value":
            # Process dictionary value
            _, key = stage

            # Check if key matches any pattern (like main RedactionProcessor)
            key_matches = any(pattern.search(str(key)) for pattern in patterns)

            if isinstance(source, str):
                # If key matches, redact entire value regardless of content
                if key_matches:
                    target[key] = replacement
                else:
                    # For values, use partial redaction (only redact matching parts)
                    target[key] = _redact_string_value(source, patterns, replacement)
            elif isinstance(source, (dict, list)):
                # If key matches, redact the entire nested structure
                if key_matches:
                    target[key] = replacement
                else:
                    # Create new nested structure for processing
                    if isinstance(source, dict):
                        target[key] = {}
                    else:
                        target[key] = []
                    stack.append((source, target[key], "copy_structure"))
            else:
                # For other types, redact if key matches
                if key_matches:
                    target[key] = replacement
                else:
                    target[key] = source

        elif isinstance(stage, tuple) and stage[0] == "list_item":
            # Process list item
            _, index = stage
            if isinstance(source, str):
                target[index] = _redact_string_value(source, patterns, replacement)
            elif isinstance(source, (dict, list)):
                # Create new nested structure
                if isinstance(source, dict):
                    target[index] = {}
                else:
                    target[index] = []
                stack.append((source, target[index], "copy_structure"))
            else:
                target[index] = source

    return result


# Keep the original function name for backward compatibility, but use iterative implementation
def _redact_pii_recursive(
    data: Any, patterns: List[re.Pattern[str]], replacement: str
) -> Any:
    """Redact PII from data structures using iterative algorithm.

    Note: Despite the name 'recursive' for backward compatibility, this now
    uses an iterative implementation to eliminate O(n²) memory complexity.

    Args:
        data: The data to process (dict, list, or primitive)
        patterns: List of compiled regex patterns
        replacement: Replacement string for matches

    Returns:
        The data with PII redacted
    """
    return _redact_pii_iterative(data, patterns, replacement)


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

    def pii_processor(logger: Any, method_name: str, event_dict: Any) -> Any:
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
