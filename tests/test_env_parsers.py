"""Tests for centralized environment variable parsing utilities."""

import pytest

from fapilog.config.env_parsers import EnvironmentParsers


class TestEnvironmentParsers:
    """Test suite for EnvironmentParsers utility class."""

    def test_parse_comma_separated_list_string(self) -> None:
        """Test parsing comma-separated string into list."""
        result = EnvironmentParsers.parse_comma_separated_list("a,b,c")
        assert result == ["a", "b", "c"]

        # Test with spaces
        result = EnvironmentParsers.parse_comma_separated_list("a, b , c ")
        assert result == ["a", "b", "c"]

        # Test single item
        result = EnvironmentParsers.parse_comma_separated_list("single")
        assert result == ["single"]

        # Test empty string
        result = EnvironmentParsers.parse_comma_separated_list("")
        assert result == []

        # Test with empty items
        result = EnvironmentParsers.parse_comma_separated_list("a,,b,")
        assert result == ["a", "b"]

    def test_parse_comma_separated_list_list(self) -> None:
        """Test parsing list input."""
        result = EnvironmentParsers.parse_comma_separated_list(["x", "y", "z"])
        assert result == ["x", "y", "z"]

        # Test tuple
        result = EnvironmentParsers.parse_comma_separated_list(("a", "b"))
        assert result == ["a", "b"]

        # Test mixed types
        result = EnvironmentParsers.parse_comma_separated_list([1, "b", 3.0])
        assert result == ["1", "b", "3.0"]

    def test_parse_comma_separated_list_other(self) -> None:
        """Test parsing other input types."""
        result = EnvironmentParsers.parse_comma_separated_list(42)
        assert result == ["42"]

        result = EnvironmentParsers.parse_comma_separated_list(None)
        assert result == []

        result = EnvironmentParsers.parse_comma_separated_list(True)
        assert result == ["True"]

    def test_parse_json_list_valid_json(self) -> None:
        """Test parsing valid JSON arrays."""
        result = EnvironmentParsers.parse_json_list('["a", "b", "c"]')
        assert result == ["a", "b", "c"]

        result = EnvironmentParsers.parse_json_list('["single"]')
        assert result == ["single"]

        result = EnvironmentParsers.parse_json_list("[]")
        assert result == []

        # Test mixed types in JSON
        result = EnvironmentParsers.parse_json_list('[1, "b", true]')
        assert result == ["1", "b", "True"]

    def test_parse_json_list_invalid_json(self) -> None:
        """Test handling of invalid JSON."""
        with pytest.raises(ValueError, match="Invalid JSON format"):
            EnvironmentParsers.parse_json_list('["unclosed')

        with pytest.raises(ValueError, match="Invalid JSON format"):
            EnvironmentParsers.parse_json_list("{not: a list}")

    def test_parse_json_list_non_string(self) -> None:
        """Test parsing non-string inputs."""
        result = EnvironmentParsers.parse_json_list(["a", "b"])
        assert result == ["a", "b"]

        result = EnvironmentParsers.parse_json_list(("x", "y"))
        assert result == ["x", "y"]

        result = EnvironmentParsers.parse_json_list(42)
        assert result == ["42"]

    def test_parse_key_value_pairs_string(self) -> None:
        """Test parsing key:value pairs from string."""
        result = EnvironmentParsers.parse_key_value_pairs("key1:val1,key2:val2")
        assert result == {"key1": "val1", "key2": "val2"}

        # Test with spaces
        result = EnvironmentParsers.parse_key_value_pairs("key1: val1 , key2 : val2")
        assert result == {"key1": "val1", "key2": "val2"}

        # Test single pair
        result = EnvironmentParsers.parse_key_value_pairs("key:value")
        assert result == {"key": "value"}

        # Test empty string
        result = EnvironmentParsers.parse_key_value_pairs("")
        assert result == {}

        # Test malformed pairs (missing colon)
        result = EnvironmentParsers.parse_key_value_pairs("key1:val1,invalid,key2:val2")
        assert result == {"key1": "val1", "key2": "val2"}

    def test_parse_key_value_pairs_dict(self) -> None:
        """Test parsing dictionary input."""
        input_dict = {"a": "b", "c": "d"}
        result = EnvironmentParsers.parse_key_value_pairs(input_dict)
        assert result == {"a": "b", "c": "d"}

        # Test with non-string values
        input_dict = {"num": "42", "bool": "True"}  # Use strings for type consistency
        result = EnvironmentParsers.parse_key_value_pairs(input_dict)
        assert result == {"num": "42", "bool": "True"}

    def test_parse_key_value_pairs_other(self) -> None:
        """Test parsing other input types."""
        result = EnvironmentParsers.parse_key_value_pairs(None)
        assert result == {}

        result = EnvironmentParsers.parse_key_value_pairs(42)
        assert result == {}

    def test_parse_json_dict_valid_json(self) -> None:
        """Test parsing valid JSON objects."""
        result = EnvironmentParsers.parse_json_dict('{"key": "value"}')
        assert result == {"key": "value"}

        result = EnvironmentParsers.parse_json_dict('{"num": 42, "bool": true}')
        assert result == {"num": 42, "bool": True}

        result = EnvironmentParsers.parse_json_dict("{}")
        assert result == {}

    def test_parse_json_dict_invalid_json(self) -> None:
        """Test handling of invalid JSON."""
        with pytest.raises(ValueError, match="Invalid JSON format"):
            EnvironmentParsers.parse_json_dict('{"unclosed": "dict"')

        with pytest.raises(ValueError, match="Invalid JSON format"):
            EnvironmentParsers.parse_json_dict("[not, a, dict]")

    def test_parse_json_dict_non_string(self) -> None:
        """Test parsing non-string inputs."""
        input_dict = {"a": "b"}
        result = EnvironmentParsers.parse_json_dict(input_dict)
        assert result == {"a": "b"}

        result = EnvironmentParsers.parse_json_dict(42)
        assert result == {}

    def test_parse_boolean_string_true_values(self) -> None:
        """Test parsing various true boolean representations."""
        true_values = ["true", "True", "TRUE", "1", "yes", "Yes", "on", "On"]
        for value in true_values:
            result = EnvironmentParsers.parse_boolean_string(value)
            assert result is True, f"Failed for value: {value}"

    def test_parse_boolean_string_false_values(self) -> None:
        """Test parsing various false boolean representations."""
        false_values = ["false", "False", "FALSE", "0", "no", "No", "off", "Off", ""]
        for value in false_values:
            result = EnvironmentParsers.parse_boolean_string(value)
            assert result is False, f"Failed for value: {value}"

    def test_parse_boolean_string_non_string(self) -> None:
        """Test parsing non-string boolean values."""
        assert EnvironmentParsers.parse_boolean_string(True) is True
        assert EnvironmentParsers.parse_boolean_string(False) is False
        assert EnvironmentParsers.parse_boolean_string(1) is True
        assert EnvironmentParsers.parse_boolean_string(0) is False
        assert EnvironmentParsers.parse_boolean_string(None) is False

    def test_parse_mixed_list_comma_separated(self) -> None:
        """Test mixed list parsing with comma-separated strings."""
        result = EnvironmentParsers.parse_mixed_list("a,b,c")
        assert result == ["a", "b", "c"]

    def test_parse_mixed_list_json_array(self) -> None:
        """Test mixed list parsing with JSON arrays."""
        result = EnvironmentParsers.parse_mixed_list('["a", "b", "c"]')
        assert result == ["a", "b", "c"]

        # Test edge case: JSON-like but not actual JSON
        result = EnvironmentParsers.parse_mixed_list("[not,json]")
        assert result == ["[not", "json]"]

    def test_parse_mixed_list_other_types(self) -> None:
        """Test mixed list parsing with other input types."""
        result = EnvironmentParsers.parse_mixed_list(["x", "y"])
        assert result == ["x", "y"]

        result = EnvironmentParsers.parse_mixed_list(("a", "b"))
        assert result == ["a", "b"]

        result = EnvironmentParsers.parse_mixed_list(42)
        assert result == [42]

        result = EnvironmentParsers.parse_mixed_list(None)
        assert result == []

    def test_parse_numeric_string_int(self) -> None:
        """Test parsing numeric strings to integers."""
        result = EnvironmentParsers.parse_numeric_string("42", int)
        assert result == 42
        assert isinstance(result, int)

        result = EnvironmentParsers.parse_numeric_string("-10", int)
        assert result == -10

        result = EnvironmentParsers.parse_numeric_string("0", int)
        assert result == 0

    def test_parse_numeric_string_float(self) -> None:
        """Test parsing numeric strings to floats."""
        result = EnvironmentParsers.parse_numeric_string("3.14", float)
        assert result == 3.14
        assert isinstance(result, float)

        result = EnvironmentParsers.parse_numeric_string("-2.5", float)
        assert result == -2.5

        result = EnvironmentParsers.parse_numeric_string("42", float)
        assert result == 42.0

    def test_parse_numeric_string_invalid(self) -> None:
        """Test handling of invalid numeric strings."""
        with pytest.raises(ValueError, match="Cannot convert 'not_a_number' to int"):
            EnvironmentParsers.parse_numeric_string("not_a_number", int)

        with pytest.raises(ValueError, match="Cannot convert 'not_a_float' to float"):
            EnvironmentParsers.parse_numeric_string("not_a_float", float)

    def test_parse_numeric_string_non_string(self) -> None:
        """Test parsing numeric values that are already numbers."""
        result = EnvironmentParsers.parse_numeric_string(42, int)
        assert result == 42

        result = EnvironmentParsers.parse_numeric_string(3.14, float)
        assert result == 3.14

        result = EnvironmentParsers.parse_numeric_string(42.0, int)
        assert result == 42

    def test_parse_numeric_string_invalid_types(self) -> None:
        """Test handling of invalid input types for numeric parsing."""
        with pytest.raises(ValueError, match="Cannot convert list to int"):
            EnvironmentParsers.parse_numeric_string(["not", "a", "number"], int)

        with pytest.raises(ValueError, match="Cannot convert dict to float"):
            EnvironmentParsers.parse_numeric_string({"not": "a number"}, float)

    def test_backward_compatibility(self) -> None:
        """Test that the new parsers maintain backward compatibility."""
        # Test the exact patterns that were used in the original field validators

        # SecuritySettings patterns
        comma_list = "password,secret,token"
        result = EnvironmentParsers.parse_mixed_list(comma_list)
        assert result == ["password", "secret", "token"]

        json_list = '["password", "secret", "token"]'
        result = EnvironmentParsers.parse_mixed_list(json_list)
        assert result == ["password", "secret", "token"]

        # ValidationSettings patterns
        required_fields = "timestamp,level,event"
        result = EnvironmentParsers.parse_comma_separated_list(required_fields)
        assert result == ["timestamp", "level", "event"]

        field_types = "field1:string,field2:int"
        result = EnvironmentParsers.parse_key_value_pairs(field_types)
        assert result == {"field1": "string", "field2": "int"}

        # SinkSettings patterns
        sinks = "stdout,loki,file"
        result = EnvironmentParsers.parse_comma_separated_list(sinks)
        assert result == ["stdout", "loki", "file"]

    def test_edge_cases(self) -> None:
        """Test various edge cases and error conditions."""
        # Empty inputs
        assert EnvironmentParsers.parse_comma_separated_list("") == []
        assert EnvironmentParsers.parse_json_list("[]") == []
        assert EnvironmentParsers.parse_key_value_pairs("") == {}
        assert EnvironmentParsers.parse_json_dict("{}") == {}
        assert EnvironmentParsers.parse_mixed_list("") == []

        # Whitespace handling
        assert EnvironmentParsers.parse_comma_separated_list("  a  ,  b  ") == [
            "a",
            "b",
        ]
        assert EnvironmentParsers.parse_key_value_pairs("  key : value  ") == {
            "key": "value"
        }

        # Complex JSON structures
        complex_json = '{"nested": {"key": "value"}, "array": [1, 2, 3]}'
        result = EnvironmentParsers.parse_json_dict(complex_json)
        assert result == {"nested": {"key": "value"}, "array": [1, 2, 3]}

        # Unicode handling
        unicode_list = "café,naïve,résumé"
        result = EnvironmentParsers.parse_comma_separated_list(unicode_list)
        assert result == ["café", "naïve", "résumé"]
