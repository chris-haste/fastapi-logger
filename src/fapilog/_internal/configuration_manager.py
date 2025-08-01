"""Configuration management for fapilog logging components.

This module provides a dedicated ConfigurationManager class that handles
all configuration-related logic extracted from LoggingContainer, following
the single responsibility principle.

Key Features:
- Stateless configuration validation
- Thread-safe operations
- Clean interface with no external dependencies beyond settings
- Console format determination logic
- Settings validation with proper error handling
"""

import sys
from typing import Optional

from ..settings import LoggingSettings
from .error_handling import handle_configuration_error


class ConfigurationManager:
    """Manages configuration validation and format determination for logging.

    This class is stateless and thread-safe, focusing solely on configuration
    logic without any dependencies on sinks, middleware, or lifecycle
    components.

    Design Principles:
    - Stateless operations (no instance variables)
    - Thread-safe by design
    - Clean interface with minimal dependencies
    - Proper error handling with descriptive messages
    """

    @staticmethod
    def validate_settings(settings: Optional[LoggingSettings]) -> LoggingSettings:
        """Validate and return a LoggingSettings instance.

        Args:
            settings: LoggingSettings instance, dict, or None

        Returns:
            LoggingSettings: Validated LoggingSettings instance

        Raises:
            ConfigurationError: If settings validation fails
        """
        try:
            if settings is None:
                return LoggingSettings()
            # If it's already a LoggingSettings instance, return it directly
            if isinstance(settings, LoggingSettings):
                return settings
            # If it's a dict or other data, validate it
            return LoggingSettings.model_validate(settings)
        except Exception as e:
            raise handle_configuration_error(
                e,
                "settings",
                str(settings) if settings else "None",
                "valid LoggingSettings",
            ) from e

    @staticmethod
    def determine_console_format(json_console: str) -> str:
        """Determine the console output format based on settings and env.

        Args:
            json_console: Console format ("auto", "pretty", or "json")

        Returns:
            str: Final console format ("pretty" or "json")

        Raises:
            ConfigurationError: If json_console value is invalid
        """
        valid_formats = {"auto", "pretty", "json"}
        if json_console not in valid_formats:
            raise handle_configuration_error(
                ValueError(f"Invalid console_format: {json_console}"),
                "console_format",
                json_console,
                f"one of {', '.join(valid_formats)}",
            )

        if json_console == "auto":
            return "pretty" if sys.stderr.isatty() else "json"
        return json_console
