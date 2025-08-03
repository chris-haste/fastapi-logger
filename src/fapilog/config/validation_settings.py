"""Validation configuration settings for fapilog."""

from typing import Any, Dict, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from ..exceptions import ConfigurationError


class ValidationSettings(BaseSettings):
    """Configuration settings for log event validation."""

    enabled: bool = Field(
        default=False,
        description="Enable log event validation (default: False)",
    )
    mode: str = Field(
        default="lenient",
        description="Validation mode: strict, lenient, fix (default: lenient)",
    )
    required_fields: List[str] = Field(
        default_factory=lambda: ["timestamp", "level", "event"],
        description="Required fields for log events (comma-separated or list)",
    )
    field_types: Dict[str, str] = Field(
        default_factory=dict,
        description="Expected types for specific fields (field -> type mapping)",
    )

    model_config = SettingsConfigDict(
        env_prefix="",  # No environment parsing - handled by parent LoggingSettings
        case_sensitive=False,
    )

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        valid_modes = {"strict", "lenient", "fix"}
        if v.lower() not in valid_modes:
            valid_list = ", ".join(sorted(valid_modes))
            raise ConfigurationError(
                f"Invalid validation_mode '{v}'. Must be one of: {valid_list}",
                "mode",
                v,
                f"one of {valid_list}",
            )
        return v.lower()

    @field_validator("required_fields", mode="before")
    @classmethod
    def parse_required_fields(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return list(v) if isinstance(v, (list, tuple)) else [v]

    @field_validator("field_types", mode="before")
    @classmethod
    def parse_field_types(cls, v: Any) -> Dict[str, str]:
        if isinstance(v, str):
            # Parse comma-separated key:value pairs
            result = {}
            for item in v.split(","):
                if ":" in item:
                    key, value = item.split(":", 1)
                    result[key.strip()] = value.strip()
            return result
        return dict(v) if isinstance(v, dict) else {}
