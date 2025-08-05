"""Tests for environment configuration utilities."""

import os
from unittest.mock import patch

import pytest

from fapilog.config.env_utils import EnvironmentConfig
from fapilog.exceptions import ConfigurationError


class TestEnvironmentConfig:
    """Test suite for EnvironmentConfig utility."""

    def test_get_validated_string_with_default(self):
        """Test getting string environment variable with default."""
        with patch.dict(os.environ, {}, clear=True):
            result = EnvironmentConfig.get_validated(
                "TEST_VAR", default="default_value", env_type=str
            )
            assert result == "default_value"

    def test_get_validated_string_from_env(self):
        """Test getting string environment variable from environment."""
        with patch.dict(os.environ, {"TEST_VAR": "env_value"}):
            result = EnvironmentConfig.get_validated("TEST_VAR", env_type=str)
            assert result == "env_value"

    def test_get_validated_int_with_default(self):
        """Test getting integer environment variable with default."""
        with patch.dict(os.environ, {}, clear=True):
            result = EnvironmentConfig.get_validated(
                "TEST_INT", default=42, env_type=int
            )
            assert result == 42

    def test_get_validated_int_from_env(self):
        """Test getting integer environment variable from environment."""
        with patch.dict(os.environ, {"TEST_INT": "123"}):
            result = EnvironmentConfig.get_validated("TEST_INT", env_type=int)
            assert result == 123

    def test_get_validated_float_with_default(self):
        """Test getting float environment variable with default."""
        with patch.dict(os.environ, {}, clear=True):
            result = EnvironmentConfig.get_validated(
                "TEST_FLOAT", default=3.14, env_type=float
            )
            assert result == 3.14

    def test_get_validated_float_from_env(self):
        """Test getting float environment variable from environment."""
        with patch.dict(os.environ, {"TEST_FLOAT": "2.718"}):
            result = EnvironmentConfig.get_validated("TEST_FLOAT", env_type=float)
            assert result == 2.718

    def test_get_validated_bool_with_default(self):
        """Test getting boolean environment variable with default."""
        with patch.dict(os.environ, {}, clear=True):
            result = EnvironmentConfig.get_validated(
                "TEST_BOOL", default=False, env_type=bool
            )
            assert result is False

    def test_get_validated_bool_true_values(self):
        """Test boolean conversion for true values."""
        true_values = ["true", "TRUE", "1", "yes", "YES", "on", "ON"]
        for value in true_values:
            with patch.dict(os.environ, {"TEST_BOOL": value}):
                result = EnvironmentConfig.get_validated("TEST_BOOL", env_type=bool)
                assert result is True, f"Failed for value: {value}"

    def test_get_validated_bool_false_values(self):
        """Test boolean conversion for false values."""
        false_values = ["false", "FALSE", "0", "no", "NO", "off", "OFF"]
        for value in false_values:
            with patch.dict(os.environ, {"TEST_BOOL": value}):
                result = EnvironmentConfig.get_validated("TEST_BOOL", env_type=bool)
                assert result is False, f"Failed for value: {value}"

    def test_get_validated_required_missing_error(self):
        """Test error when required environment variable is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ConfigurationError) as exc_info:
                EnvironmentConfig.get_validated("REQUIRED_VAR", required=True)

            assert "Required environment variable 'REQUIRED_VAR' is not set" in str(
                exc_info.value
            )

    def test_get_validated_invalid_int_error(self):
        """Test error for invalid integer conversion."""
        with patch.dict(os.environ, {"INVALID_INT": "not_a_number"}):
            with pytest.raises(ConfigurationError) as exc_info:
                EnvironmentConfig.get_validated("INVALID_INT", env_type=int)

            assert "invalid value 'not_a_number' for type int" in str(exc_info.value)

    def test_get_validated_invalid_float_error(self):
        """Test error for invalid float conversion."""
        with patch.dict(os.environ, {"INVALID_FLOAT": "not_a_float"}):
            with pytest.raises(ConfigurationError) as exc_info:
                EnvironmentConfig.get_validated("INVALID_FLOAT", env_type=float)

            assert "invalid value 'not_a_float' for type float" in str(exc_info.value)

    def test_get_validated_with_validator_success(self):
        """Test successful validation with custom validator."""

        def positive_validator(value: int) -> int:
            if value <= 0:
                raise ValueError("Value must be positive")
            return value

        with patch.dict(os.environ, {"POSITIVE_INT": "42"}):
            result = EnvironmentConfig.get_validated(
                "POSITIVE_INT", env_type=int, validator=positive_validator
            )
            assert result == 42

    def test_get_validated_with_validator_failure(self):
        """Test validation failure with custom validator."""

        def positive_validator(value: int) -> int:
            if value <= 0:
                raise ValueError("Value must be positive")
            return value

        with patch.dict(os.environ, {"NEGATIVE_INT": "-5"}):
            with pytest.raises(ConfigurationError) as exc_info:
                EnvironmentConfig.get_validated(
                    "NEGATIVE_INT", env_type=int, validator=positive_validator
                )

            assert "failed validation" in str(exc_info.value)
            assert "Value must be positive" in str(exc_info.value)

    def test_get_string_convenience_method(self):
        """Test get_string convenience method."""
        with patch.dict(os.environ, {"STRING_VAR": "test_value"}):
            result = EnvironmentConfig.get_string("STRING_VAR")
            assert result == "test_value"

    def test_get_int_convenience_method(self):
        """Test get_int convenience method."""
        with patch.dict(os.environ, {"INT_VAR": "100"}):
            result = EnvironmentConfig.get_int("INT_VAR")
            assert result == 100

    def test_get_float_convenience_method(self):
        """Test get_float convenience method."""
        with patch.dict(os.environ, {"FLOAT_VAR": "1.5"}):
            result = EnvironmentConfig.get_float("FLOAT_VAR")
            assert result == 1.5

    def test_get_bool_convenience_method(self):
        """Test get_bool convenience method."""
        with patch.dict(os.environ, {"BOOL_VAR": "true"}):
            result = EnvironmentConfig.get_bool("BOOL_VAR")
            assert result is True

    def test_convenience_methods_with_defaults(self):
        """Test convenience methods with default values."""
        with patch.dict(os.environ, {}, clear=True):
            # Test with defaults
            assert (
                EnvironmentConfig.get_string("MISSING", default="default") == "default"
            )
            assert EnvironmentConfig.get_int("MISSING", default=42) == 42
            assert EnvironmentConfig.get_float("MISSING", default=3.14) == 3.14
            assert EnvironmentConfig.get_bool("MISSING", default=True) is True

    def test_convenience_methods_required(self):
        """Test convenience methods with required=True."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ConfigurationError):
                EnvironmentConfig.get_string("REQUIRED_STRING", required=True)

            with pytest.raises(ConfigurationError):
                EnvironmentConfig.get_int("REQUIRED_INT", required=True)

            with pytest.raises(ConfigurationError):
                EnvironmentConfig.get_float("REQUIRED_FLOAT", required=True)

            with pytest.raises(ConfigurationError):
                EnvironmentConfig.get_bool("REQUIRED_BOOL", required=True)

    def test_convert_type_unsupported_type(self):
        """Test conversion with unsupported type."""

        # Test with a type that can't be created from a string
        class UnsupportedType:
            def __init__(self):
                pass  # doesn't accept string argument

        with pytest.raises(TypeError) as exc_info:
            EnvironmentConfig._convert_type("test", UnsupportedType)

        assert "Unsupported type conversion" in str(exc_info.value)

    def test_convert_type_custom_type_success(self):
        """Test conversion with custom type that supports string conversion."""

        # Create a simple custom type that can be created from string
        class CustomType:
            def __init__(self, value):
                self.value = str(value)

        result = EnvironmentConfig._convert_type("test_value", CustomType)
        assert isinstance(result, CustomType)
        assert result.value == "test_value"

    def test_edge_case_empty_string(self):
        """Test handling of empty string environment variables."""
        with patch.dict(os.environ, {"EMPTY_VAR": ""}):
            # Empty string should be returned as-is for string type
            result = EnvironmentConfig.get_validated("EMPTY_VAR", env_type=str)
            assert result == ""

            # Empty string should cause error for int type
            with pytest.raises(ConfigurationError):
                EnvironmentConfig.get_validated("EMPTY_VAR", env_type=int)

    def test_edge_case_whitespace_string(self):
        """Test handling of whitespace-only environment variables."""
        with patch.dict(os.environ, {"WHITESPACE_VAR": "   "}):
            # Whitespace should be preserved for string type
            result = EnvironmentConfig.get_validated("WHITESPACE_VAR", env_type=str)
            assert result == "   "

            # Whitespace should cause error for int type
            with pytest.raises(ConfigurationError):
                EnvironmentConfig.get_validated("WHITESPACE_VAR", env_type=int)
