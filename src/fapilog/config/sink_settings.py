"""Sink and output configuration settings for fapilog."""

from typing import TYPE_CHECKING, Any, List, Union

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from ..exceptions import ConfigurationError
from .env_parsers import EnvironmentParsers

if TYPE_CHECKING:
    from ..sinks import Sink
else:
    # Import Sink at runtime for proper isinstance checks
    try:
        from ..sinks import Sink
    except ImportError:
        Sink = None


class SinkSettings(BaseSettings):
    """Configuration settings for sink outputs and formatting."""

    sinks: Union[List[Union[str, "Sink"]], str] = Field(
        default_factory=lambda: ["stdout"],
        description="List of sink names/URIs or sink instances for log output "
        "(comma-separated string or list)",
    )
    json_console: str = Field(
        default="auto",
        description="Console output format (auto, json, pretty)",
    )
    sampling_rate: float = Field(
        default=1.0,
        description="Sampling rate for log messages (0.0 to 1.0)",
    )

    model_config = SettingsConfigDict(
        env_prefix="",  # No environment parsing - handled by parent LoggingSettings
        case_sensitive=False,
    )

    @field_validator("sinks", mode="before")
    @classmethod
    def parse_sinks(cls, v: Any) -> List[Union[str, "Sink"]]:
        """Parse sinks field to support strings and Sink instances."""
        if isinstance(v, str):
            return EnvironmentParsers.parse_comma_separated_list(v)
        if isinstance(v, (list, tuple)):
            # Support mixed list of strings and Sink instances
            result: List[Union[str, Sink]] = []
            for item in v:
                if isinstance(item, str):
                    result.append(item)
                else:
                    # Try to check if it's a Sink instance at runtime
                    if (Sink is not None and isinstance(item, Sink)) or (
                        Sink is None and "Sink" in str(type(item))
                    ):
                        # Fallback check for Sink-like objects
                        result.append(item)
                    elif hasattr(item, "write") and callable(item.write):
                        # If we can't determine the type, treat as Sink if it has write method
                        result.append(item)
                    else:
                        # Convert other types to string for backward compatibility
                        result.append(str(item))
            return result
        raise ConfigurationError(
            f"Invalid sinks value: {v}. Must be string or list",
            "sinks",
            v,
            "string or list",
        )

    @field_validator("json_console")
    @classmethod
    def validate_json_console(cls, v: str) -> str:
        valid_formats = {"auto", "json", "pretty"}
        if v.lower() not in valid_formats:
            valid_list = ", ".join(sorted(valid_formats))
            raise ConfigurationError(
                f"Invalid json_console '{v}'. Must be one of: {valid_list}",
                "json_console",
                v,
                f"one of {valid_list}",
            )
        return v.lower()

    @field_validator("sampling_rate")
    @classmethod
    def validate_sampling_rate(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ConfigurationError(
                "Sampling rate must be between 0.0 and 1.0",
                "sampling_rate",
                v,
                "0.0 <= value <= 1.0",
            )
        return v
