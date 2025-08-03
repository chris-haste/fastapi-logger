"""Queue configuration settings for fapilog."""

from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from ..exceptions import ConfigurationError


class QueueSettings(BaseSettings):
    """Configuration settings for async queue behavior."""

    enabled: bool = Field(
        default=True,
        description="Enable async queue for non-blocking logging",
    )
    maxsize: int = Field(
        default=1000,
        description="Maximum size of the async log queue",
    )
    overflow: Literal["drop", "block", "sample"] = Field(
        default="drop",
        description="Strategy for handling queue overflow: drop (discard), "
        "block (wait), or sample (probabilistic)",
    )
    batch_size: int = Field(
        default=10,
        description="Number of events to process in a batch",
    )
    batch_timeout: float = Field(
        default=1.0,
        description="Maximum time to wait for batch completion (seconds)",
    )
    retry_delay: float = Field(
        default=1.0,
        description="Delay between retries on sink failures (seconds)",
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of retries per event",
    )

    model_config = SettingsConfigDict(
        case_sensitive=False,
    )

    @field_validator("maxsize")
    @classmethod
    def validate_maxsize(cls, v: int) -> int:
        if v <= 0:
            raise ConfigurationError(
                "Queue maxsize must be positive", "maxsize", v, "positive integer"
            )
        return v

    @field_validator("batch_size")
    @classmethod
    def validate_batch_size(cls, v: int) -> int:
        if v <= 0:
            raise ConfigurationError(
                "Queue batch size must be positive",
                "batch_size",
                v,
                "positive integer",
            )
        return v

    @field_validator("batch_timeout")
    @classmethod
    def validate_batch_timeout(cls, v: float) -> float:
        if v <= 0:
            raise ConfigurationError(
                "Queue batch timeout must be positive",
                "batch_timeout",
                v,
                "positive float",
            )
        return v

    @field_validator("retry_delay")
    @classmethod
    def validate_retry_delay(cls, v: float) -> float:
        if v <= 0:
            raise ConfigurationError(
                "Queue retry delay must be positive",
                "retry_delay",
                v,
                "positive float",
            )
        return v

    @field_validator("max_retries")
    @classmethod
    def validate_max_retries(cls, v: int) -> int:
        if v < 0:
            raise ConfigurationError(
                "Queue max retries must be non-negative",
                "max_retries",
                v,
                "non-negative integer",
            )
        return v

    @field_validator("overflow")
    @classmethod
    def validate_overflow(cls, v: str) -> str:
        valid_strategies = {"drop", "block", "sample"}
        if v.lower() not in valid_strategies:
            valid_list = ", ".join(sorted(valid_strategies))
            raise ConfigurationError(
                f"Invalid overflow '{v}'. Must be one of: {valid_list}",
                "overflow",
                v,
                f"one of {valid_list}",
            )
        return v.lower()
