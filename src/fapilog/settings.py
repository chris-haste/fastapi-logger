"""Configuration settings for fapilog."""

from typing import Any, Dict, List, Optional, Union

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LoggingSettings(BaseSettings):
    """Configuration settings for fapilog structured logging.

    Maps environment variables to logging behavior for easy configuration
    without code changes.
    """

    level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARN, ERROR, CRITICAL)",
    )
    sinks: Union[List[str], str] = Field(
        default_factory=lambda: ["stdout"],
        description="List of sink names to use for log output (comma-separated or list)",
    )
    json_console: str = Field(
        default="auto",
        description="Console output format (auto, json, pretty)",
    )
    redact_patterns: Union[List[str], str] = Field(
        default_factory=lambda: [],
        description="List of regex patterns to redact from log messages (comma-separated or list)",
    )
    sampling_rate: float = Field(
        default=1.0,
        description="Sampling rate for log messages (0.0 to 1.0)",
    )
    # Queue settings
    queue_enabled: bool = Field(
        default=True,
        description="Enable async queue for non-blocking logging",
    )
    queue_size: int = Field(
        default=1000,
        description="Maximum size of the async log queue",
    )
    queue_batch_size: int = Field(
        default=10,
        description="Number of events to process in a batch",
    )
    queue_batch_timeout: float = Field(
        default=1.0,
        description="Maximum time to wait for batch completion (seconds)",
    )
    queue_retry_delay: float = Field(
        default=1.0,
        description="Delay between retries on sink failures (seconds)",
    )
    queue_max_retries: int = Field(
        default=3,
        description="Maximum number of retries per event",
    )

    model_config = SettingsConfigDict(
        env_prefix="FAPILOG_",
        case_sensitive=False,
    )

    @field_validator("sinks", mode="before")
    @classmethod
    def parse_sinks(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return list(v) if isinstance(v, (list, tuple)) else [v]

    @field_validator("redact_patterns", mode="before")
    @classmethod
    def parse_redact_patterns(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return list(v) if isinstance(v, (list, tuple)) else [v]

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        valid_levels = {"DEBUG", "INFO", "WARN", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            valid_list = ", ".join(sorted(valid_levels))
            raise ValueError(f"Invalid level '{v}'. Must be one of: {valid_list}")
        return v.upper()

    @field_validator("json_console")
    @classmethod
    def validate_json_console(cls, v: str) -> str:
        valid_values = {"auto", "json", "pretty"}
        if v.lower() not in valid_values:
            valid_list = ", ".join(valid_values)
            raise ValueError(
                f"Invalid json_console '{v}'. Must be one of: {valid_list}"
            )
        return v.lower()

    @field_validator("sampling_rate")
    @classmethod
    def validate_sampling_rate(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"Sampling rate must be between 0.0 and 1.0, got {v}")
        return v

    @field_validator("queue_size")
    @classmethod
    def validate_queue_size(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Queue size must be positive")
        return v

    @field_validator("queue_batch_size")
    @classmethod
    def validate_queue_batch_size(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Queue batch size must be positive")
        return v

    @field_validator("queue_batch_timeout")
    @classmethod
    def validate_queue_batch_timeout(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Queue batch timeout must be positive")
        return v

    @field_validator("queue_retry_delay")
    @classmethod
    def validate_queue_retry_delay(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Queue retry delay must be positive")
        return v

    @field_validator("queue_max_retries")
    @classmethod
    def validate_queue_max_retries(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Queue max retries must be non-negative")
        return v


def configure_logging(
    level: str = "INFO",
    format: str = "json",
    sinks: Optional[Dict[str, Any]] = None,
) -> None:
    """Configure logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format: Output format (json, text)
        sinks: Dictionary of sink configurations
    """
    # TODO: Implement full logging configuration
    pass
