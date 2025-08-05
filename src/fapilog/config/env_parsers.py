"""Centralized environment variable parsing utilities for fapilog configuration."""

import json
from typing import Any, Dict, List, Type, Union


class EnvironmentParsers:
    """Centralized environment variable parsing utilities.

    Provides consistent parsing behavior across all settings classes
    to eliminate code duplication and ensure uniform handling.
    """

    @staticmethod
    def parse_comma_separated_list(value: Any) -> List[str]:
        """Parse comma-separated string into list of strings.

        Args:
            value: Input value to parse (string, list, tuple, or other)

        Returns:
            List of string values

        Examples:
            >>> EnvironmentParsers.parse_comma_separated_list("a,b,c")
            ['a', 'b', 'c']
            >>> EnvironmentParsers.parse_comma_separated_list(["x", "y"])
            ['x', 'y']
            >>> EnvironmentParsers.parse_comma_separated_list("single")
            ['single']
        """
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        elif isinstance(value, (list, tuple)):
            return [str(item) for item in value]
        else:
            return [str(value)] if value is not None else []

    @staticmethod
    def parse_json_list(value: Any) -> List[str]:
        """Parse JSON array string into list of strings.

        Args:
            value: Input value to parse (JSON string, list, tuple, or other)

        Returns:
            List of string values

        Raises:
            ValueError: If JSON string is malformed

        Examples:
            >>> EnvironmentParsers.parse_json_list('["a", "b", "c"]')
            ['a', 'b', 'c']
            >>> EnvironmentParsers.parse_json_list(["x", "y"])
            ['x', 'y']
        """
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
                else:
                    return [str(parsed)]
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON format for list: {value}") from e
        elif isinstance(value, (list, tuple)):
            return [str(item) for item in value]
        else:
            return [str(value)] if value is not None else []

    @staticmethod
    def parse_key_value_pairs(value: Any) -> Dict[str, str]:
        """Parse comma-separated key:value pairs into dictionary.

        Args:
            value: Input value to parse (string or dict)

        Returns:
            Dictionary of string key-value pairs

        Examples:
            >>> EnvironmentParsers.parse_key_value_pairs("key1:val1,key2:val2")
            {'key1': 'val1', 'key2': 'val2'}
            >>> EnvironmentParsers.parse_key_value_pairs({"a": "b"})
            {'a': 'b'}
        """
        if isinstance(value, str):
            result = {}
            for item in value.split(","):
                if ":" in item:
                    key, val = item.split(":", 1)
                    result[key.strip()] = val.strip()
            return result
        elif isinstance(value, dict):
            return {str(k): str(v) for k, v in value.items()}
        else:
            return {}

    @staticmethod  # vulture: disable
    def parse_json_dict(value: Any) -> Dict[str, Any]:
        """Parse JSON object string into dictionary.

        Args:
            value: Input value to parse (JSON string or dict)

        Returns:
            Dictionary of parsed values

        Raises:
            ValueError: If JSON string is malformed

        Examples:
            >>> EnvironmentParsers.parse_json_dict('{"key": "value"}')
            {'key': 'value'}
            >>> EnvironmentParsers.parse_json_dict({"a": "b"})
            {'a': 'b'}
        """
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, dict):
                    return parsed
                else:
                    return {"value": parsed}
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON format for dict: {value}") from e
        elif isinstance(value, dict):
            return value
        else:
            return {}

    @staticmethod  # vulture: disable
    def parse_boolean_string(value: Any) -> bool:
        """Parse string boolean values consistently.

        Args:
            value: Input value to parse

        Returns:
            Boolean value

        Examples:
            >>> EnvironmentParsers.parse_boolean_string("true")
            True
            >>> EnvironmentParsers.parse_boolean_string("false")
            False
            >>> EnvironmentParsers.parse_boolean_string("1")
            True
            >>> EnvironmentParsers.parse_boolean_string("0")
            False
        """
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return bool(value)

    @staticmethod
    def parse_mixed_list(value: Any) -> List[Union[str, Any]]:
        """Parse mixed input into list, supporting both comma-separated and JSON formats.

        Args:
            value: Input value to parse

        Returns:
            List of values

        Examples:
            >>> EnvironmentParsers.parse_mixed_list("a,b,c")
            ['a', 'b', 'c']
            >>> EnvironmentParsers.parse_mixed_list('["a", "b"]')
            ['a', 'b']
        """
        if isinstance(value, str):
            # Try JSON first
            if value.strip().startswith("[") and value.strip().endswith("]"):
                try:
                    return EnvironmentParsers.parse_json_list(value)
                except ValueError:
                    pass
            # Fall back to comma-separated
            return EnvironmentParsers.parse_comma_separated_list(value)
        elif isinstance(value, (list, tuple)):
            return list(value)
        else:
            return [value] if value is not None else []

    @staticmethod  # vulture: disable
    def parse_numeric_string(
        value: Any, target_type: Type[Union[int, float]] = int
    ) -> Union[int, float]:
        """Parse numeric string values with type conversion.

        Args:
            value: Input value to parse
            target_type: Target numeric type (int or float)

        Returns:
            Numeric value of specified type

        Raises:
            ValueError: If value cannot be converted to target type
        """
        if isinstance(value, str):
            try:
                return target_type(value)
            except ValueError as e:
                raise ValueError(
                    f"Cannot convert '{value}' to {target_type.__name__}"
                ) from e
        elif isinstance(value, (int, float)):
            return target_type(value)
        else:
            try:
                converted_value = target_type(value)
                return converted_value
            except (ValueError, TypeError) as e:
                raise ValueError(
                    f"Cannot convert {type(value).__name__} to {target_type.__name__}"
                ) from e
