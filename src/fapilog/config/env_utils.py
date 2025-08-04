"""Validated environment variable access utility for fapilog.

This module provides a centralized way to access environment variables
with validation and type conversion, ensuring consistent patterns across
the codebase and preventing direct os.getenv() usage.
"""

import os
from typing import Any, Callable, Optional, Type, TypeVar, Union

from ..exceptions import ConfigurationError

T = TypeVar("T")


class EnvironmentConfig:
    """Validated environment variable access utility.

    Provides centralized environment variable access with validation,
    type conversion, and consistent error handling.
    """

    @staticmethod
    def get_validated(
        key: str,
        default: Any = None,
        validator: Optional[Callable[[Any], Any]] = None,
        env_type: Type[T] = str,
        required: bool = False,
    ) -> Union[T, Any]:
        """Get environment variable with validation and type conversion.

        Args:
            key: Environment variable name
            default: Default value if variable is not set
            validator: Optional validation function
            env_type: Expected type for conversion (int, float, bool, str)
            required: Whether the variable is required (error if missing)

        Returns:
            Validated and converted environment variable value

        Raises:
            ConfigurationError: If required variable is missing or
                validation fails

        Examples:
            >>> EnvironmentConfig.get_validated(
            ...     "PORT", default=8000, env_type=int
            ... )
            8000
            >>> EnvironmentConfig.get_validated(
            ...     "DEBUG", default=False, env_type=bool
            ... )
            False
            >>> EnvironmentConfig.get_validated("API_KEY", required=True)
            "your-api-key"
        """
        # Get raw value from environment
        raw_value = os.getenv(key)

        # Handle missing required variables
        if raw_value is None and required and default is None:
            raise ConfigurationError(
                f"Required environment variable '{key}' is not set",
                setting=key,
                value=None,
                expected_type="non-empty value",
            )

        # Use default if not set
        if raw_value is None:
            value = default
        else:
            # Convert type
            try:
                value = EnvironmentConfig._convert_type(raw_value, env_type)
            except (ValueError, TypeError) as e:
                raise ConfigurationError(
                    f"Environment variable '{key}' has invalid value "
                    f"'{raw_value}' for type {env_type.__name__}",
                    setting=key,
                    value=raw_value,
                    expected_type=f"value convertible to {env_type.__name__}",
                ) from e

        # Apply validation if provided
        if validator is not None:
            try:
                value = validator(value)
            except Exception as e:
                raise ConfigurationError(
                    f"Environment variable '{key}' failed validation: {e}",
                    setting=key,
                    value=value,
                    expected_type="value passing validation",
                ) from e

        return value

    @staticmethod
    def _convert_type(value: str, target_type: Type[T]) -> T:
        """Convert string value to target type.

        Args:
            value: String value from environment
            target_type: Target type for conversion

        Returns:
            Converted value

        Raises:
            ValueError: If conversion fails
            TypeError: If target type is not supported
        """
        if target_type is str:
            return value  # type: ignore

        if target_type is int:
            return int(value)  # type: ignore

        if target_type is float:
            return float(value)  # type: ignore

        if target_type is bool:
            # Handle boolean conversion consistently
            return value.lower() in ("true", "1", "yes", "on")  # type: ignore

        # For other types, try direct conversion
        try:
            return target_type(value)  # type: ignore
        except Exception as e:
            msg = f"Unsupported type conversion to {target_type}"
            raise TypeError(msg) from e

    @staticmethod
    def get_string(
        key: str,
        default: Optional[str] = None,
        required: bool = False,
        validator: Optional[Callable[[str], str]] = None,
    ) -> Optional[str]:
        """Get string environment variable with validation.

        Args:
            key: Environment variable name
            default: Default string value
            required: Whether the variable is required
            validator: Optional validation function

        Returns:
            String value or None if not set and not required
        """
        return EnvironmentConfig.get_validated(
            key=key,
            default=default,
            validator=validator,
            env_type=str,
            required=required,
        )

    @staticmethod
    def get_int(
        key: str,
        default: Optional[int] = None,
        required: bool = False,
        validator: Optional[Callable[[int], int]] = None,
    ) -> Optional[int]:
        """Get integer environment variable with validation.

        Args:
            key: Environment variable name
            default: Default integer value
            required: Whether the variable is required
            validator: Optional validation function

        Returns:
            Integer value or None if not set and not required
        """
        return EnvironmentConfig.get_validated(
            key=key,
            default=default,
            validator=validator,
            env_type=int,
            required=required,
        )

    @staticmethod
    def get_float(
        key: str,
        default: Optional[float] = None,
        required: bool = False,
        validator: Optional[Callable[[float], float]] = None,
    ) -> Optional[float]:
        """Get float environment variable with validation.

        Args:
            key: Environment variable name
            default: Default float value
            required: Whether the variable is required
            validator: Optional validation function

        Returns:
            Float value or None if not set and not required
        """
        return EnvironmentConfig.get_validated(
            key=key,
            default=default,
            validator=validator,
            env_type=float,
            required=required,
        )

    @staticmethod
    def get_bool(
        key: str,
        default: Optional[bool] = None,
        required: bool = False,
        validator: Optional[Callable[[bool], bool]] = None,
    ) -> Optional[bool]:
        """Get boolean environment variable with validation.

        Args:
            key: Environment variable name
            default: Default boolean value
            required: Whether the variable is required
            validator: Optional validation function

        Returns:
            Boolean value or None if not set and not required
        """
        return EnvironmentConfig.get_validated(
            key=key,
            default=default,
            validator=validator,
            env_type=bool,
            required=required,
        )
