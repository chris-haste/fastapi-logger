"""Configuration management for fapilog logging components.

This module provides a dedicated ConfigurationManager class that handles
configuration validation and format determination, extracted from LoggingContainer
to follow the single responsibility principle.

Key Features:
- Settings validation and normalization
- Console format determination with auto-detection
- Stateless design for optimal performance
- Thread-safe operations
- Clean interface with no external dependencies
"""

import sys
from typing import Optional, Union

from ..._internal.error_handling import handle_configuration_error
from ...config import LoggingSettings


class ConfigurationManager:
    """Manages configuration validation and format determination.

    This class provides static methods for configuration operations that were
    previously part of LoggingContainer, enabling reuse and better separation
    of concerns.

    Design Principles:
    - Stateless operations for optimal performance
    - Clear separation of configuration concerns
    - Thread-safe by design (no instance state)
    - Fast validation with minimal overhead
    """

    @staticmethod
    def validate_settings(
        settings: Optional[Union[LoggingSettings, dict]],
    ) -> LoggingSettings:
        """Validate and return LoggingSettings instance.

        Efficiently validates and normalizes settings input, handling various
        input types while providing clear error messages for invalid configurations.

        Args:
            settings: LoggingSettings instance, dict, or None

        Returns:
            Validated LoggingSettings instance

        Raises:
            ConfigurationError: If settings are invalid
        """
        try:
            if settings is None:
                return LoggingSettings()
            # If it's already a LoggingSettings instance, return it directly (fast path)
            if isinstance(settings, LoggingSettings):
                return settings
            # If it's a dict or other data, validate it
            return LoggingSettings.model_validate(settings)  # type: ignore[no-any-return]
        except Exception as e:
            raise handle_configuration_error(
                e,
                "settings",
                str(settings) if settings else "None",
                "valid LoggingSettings",
            ) from e

    @staticmethod
    def determine_console_format(console_format: str) -> str:
        """Determine the console output format with auto-detection.

        Efficiently determines the final console format, handling auto-detection
        based on TTY status for optimal user experience.

        Args:
            console_format: Format string ("auto", "pretty", or "json")

        Returns:
            Resolved format string ("pretty" or "json")

        Raises:
            ConfigurationError: If format is invalid
        """
        # Fast path for explicit formats
        if console_format == "pretty" or console_format == "json":
            return console_format

        # Validate format options
        valid_formats = {"auto", "pretty", "json"}
        if console_format not in valid_formats:
            raise handle_configuration_error(
                ValueError(f"Invalid console_format: {console_format}"),
                "console_format",
                console_format,
                f"one of {', '.join(valid_formats)}",
            )

        # Auto-detection for "auto" format
        return "pretty" if sys.stderr.isatty() else "json"
