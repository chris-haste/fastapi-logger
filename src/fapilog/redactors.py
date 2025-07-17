"""Field redaction functionality for fapilog structured logging."""

from typing import Any, Dict, List, Union


def _get_log_level_numeric(level: str) -> int:
    """Convert log level string to numeric value for comparison.

    Args:
        level: Log level string (case insensitive)

    Returns:
        Numeric level value following Python logging standard

    Raises:
        ValueError: If level is not recognized
    """
    level_map = {
        "DEBUG": 10,
        "INFO": 20,
        "WARN": 30,
        "WARNING": 30,
        "ERROR": 40,
        "CRITICAL": 50,
    }
    level_upper = level.upper()
    if level_upper not in level_map:
        raise ValueError(f"Unknown log level: {level}")
    return level_map[level_upper]


def _should_redact_at_level(event_level: str, redact_level: str) -> bool:
    """Check if redaction should be applied based on log levels.

    Args:
        event_level: Log level of the current event
        redact_level: Minimum level for redaction to be applied

    Returns:
        True if redaction should be applied, False otherwise
    """
    try:
        event_numeric = _get_log_level_numeric(event_level)
        redact_numeric = _get_log_level_numeric(redact_level)
        return event_numeric >= redact_numeric
    except ValueError:
        # If either level is invalid, apply redaction as a safe default
        return True


def _get_nested_value(data: Dict[str, Any], path: str) -> Any:
    """Get a value from a nested dictionary using dot notation.

    Args:
        data: The dictionary to search in
        path: Dot-separated path to the value (e.g., "user.password")

    Returns:
        The value at the path, or None if not found
    """
    keys = path.split(".")
    current = data

    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None

    return current


def _set_nested_value(data: Dict[str, Any], path: str, value: Any) -> None:
    """Set a value in a nested dictionary using dot notation.

    Args:
        data: The dictionary to modify
        path: Dot-separated path to the value (e.g., "user.password")
        value: The value to set
    """
    keys = path.split(".")
    current = data

    # Navigate to the parent of the target key
    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]

    # Set the value at the target key
    current[keys[-1]] = value


def _redact_nested_fields(
    data: Dict[str, Any], fields_to_redact: List[str], replacement: str = "REDACTED"
) -> Dict[str, Any]:
    """Recursively redact fields from a nested dictionary.

    Args:
        data: The dictionary to redact
        fields_to_redact: List of field paths to redact (supports dot notation)
        replacement: Value to use for redacted fields

    Returns:
        A new dictionary with redacted fields
    """
    if not fields_to_redact:
        return data

    # Create a copy to avoid modifying the original
    result = data.copy()

    # Process each field to redact
    for field_path in fields_to_redact:
        if "." in field_path:
            # Nested field - check if it exists and redact it
            if _get_nested_value(result, field_path) is not None:
                _set_nested_value(result, field_path, replacement)
        else:
            # Top-level field
            if field_path in result:
                result[field_path] = replacement

    # Recursively process nested dictionaries and lists
    for key, value in result.items():
        if isinstance(value, dict):
            result[key] = _redact_nested_fields(value, fields_to_redact, replacement)
        elif isinstance(value, list):
            # Handle lists of dictionaries
            result[key] = [
                (
                    _redact_nested_fields(item, fields_to_redact, replacement)
                    if isinstance(item, dict)
                    else item
                )
                for item in value
            ]

    return result


def _redact_nested_fields_v2(
    data: Dict[str, Any], fields_to_redact: List[str], replacement: str = "REDACTED"
) -> Dict[str, Any]:
    """Recursively redact fields from a nested dictionary with better list support.

    Args:
        data: The dictionary to redact
        fields_to_redact: List of field paths to redact (supports dot notation)
        replacement: Value to use for redacted fields

    Returns:
        A new dictionary with redacted fields
    """
    if not fields_to_redact:
        return data

    # Create a copy to avoid modifying the original
    result = data.copy()

    # Process each field to redact
    for field_path in fields_to_redact:
        keys = field_path.split(".")
        _redact_path_in_data(result, keys, replacement)

    # Recursively process nested dictionaries and lists
    for key, value in result.items():
        if isinstance(value, dict):
            result[key] = _redact_nested_fields_v2(value, fields_to_redact, replacement)
        elif isinstance(value, list):
            # Handle lists of dictionaries
            result[key] = [
                (
                    _redact_nested_fields_v2(item, fields_to_redact, replacement)
                    if isinstance(item, dict)
                    else item
                )
                for item in value
            ]

    return result


def _redact_path_in_data(
    data: Dict[str, Any], keys: List[str], replacement: str
) -> None:
    """Redact a specific path in the data structure.

    Args:
        data: The data structure to redact from
        keys: List of keys representing the path
        replacement: Value to use for redacted fields
    """
    if len(keys) == 1:
        # Single key - redact at this level
        key = keys[0]
        if key in data:
            data[key] = replacement
        return

    # Multiple keys - navigate to the target
    current_key = keys[0]
    remaining_keys = keys[1:]

    if current_key not in data:
        return

    current_value = data[current_key]

    if isinstance(current_value, dict):
        # Navigate into dictionary
        _redact_path_in_data(current_value, remaining_keys, replacement)
    elif isinstance(current_value, list):
        # Navigate into list - apply to each dictionary item
        for item in current_value:
            if isinstance(item, dict):
                _redact_path_in_data(item, remaining_keys, replacement)


def field_redactor(
    fields_to_redact: List[str],
    replacement: str = "REDACTED",
    redact_level: str = "INFO",
) -> Any:
    """Create a field redaction processor for structlog.

    Args:
        fields_to_redact: List of field names to redact (supports dot notation)
        replacement: Value to use for redacted fields
        redact_level: Minimum log level for redaction to be applied

    Returns:
        A processor function that redacts specified fields
    """
    if not fields_to_redact:
        return lambda logger, method_name, event_dict: event_dict

    def redactor_processor(
        logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Redact sensitive fields from log entries.

        Args:
            logger: The logger instance
            method_name: The logging method name
            event_dict: The event dictionary to redact

        Returns:
            The redacted event dictionary
        """
        # Check if redaction should be applied based on log level
        event_level = event_dict.get("level", "INFO")
        if not _should_redact_at_level(event_level, redact_level):
            return event_dict

        return _redact_nested_fields_v2(event_dict, fields_to_redact, replacement)

    return redactor_processor
