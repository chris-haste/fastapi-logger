"""Load test configuration settings for fapilog."""

from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from ..exceptions import ConfigurationError


class LoadTestSettings(BaseSettings):
    """Configuration settings for load testing fapilog logging queue.

    Maps environment variables to load test parameters for easy configuration
    without code changes.
    """

    # Core load test parameters
    concurrency: int = Field(
        default=10,
        description="Number of concurrent workers",
        ge=1,
        le=1000,
    )
    rate: float = Field(
        default=100.0,
        description="Logs per second per worker",
        gt=0.0,
        le=10000.0,
    )
    duration: float = Field(
        default=30.0,
        description="Test duration in seconds",
        gt=0.0,
        le=3600.0,
    )
    queue_size: int = Field(
        default=1000,
        description="Maximum queue size",
        ge=1,
        le=100000,
    )
    overflow: Literal["drop", "block", "sample"] = Field(
        default="drop",
        description="Queue overflow strategy",
    )
    batch_size: int = Field(
        default=10,
        description="Queue batch size",
        ge=1,
        le=1000,
    )
    batch_timeout: float = Field(
        default=1.0,
        description="Queue batch timeout in seconds",
        gt=0.0,
        le=60.0,
    )

    model_config = SettingsConfigDict(
        env_prefix="LOAD_TEST_",
        case_sensitive=False,
        extra="forbid",
        validate_default=True,
    )

    @field_validator("concurrency")
    @classmethod
    def validate_concurrency(cls, v: int) -> int:
        if v <= 0:
            raise ConfigurationError(
                "Concurrency must be positive",
                setting="concurrency",
                value=v,
                expected_type="positive integer",
            )
        if v > 1000:
            raise ConfigurationError(
                "Concurrency is too high, maximum is 1000",
                setting="concurrency",
                value=v,
                expected_type="integer <= 1000",
            )
        return v

    @field_validator("rate")
    @classmethod
    def validate_rate(cls, v: float) -> float:
        if v <= 0:
            raise ConfigurationError(
                "Rate must be positive",
                setting="rate",
                value=v,
                expected_type="positive number",
            )
        if v > 10000:
            raise ConfigurationError(
                "Rate is too high, maximum is 10000 logs/sec per worker",
                setting="rate",
                value=v,
                expected_type="number <= 10000",
            )
        return v

    @field_validator("duration")
    @classmethod
    def validate_duration(cls, v: float) -> float:
        if v <= 0:
            raise ConfigurationError(
                "Duration must be positive",
                setting="duration",
                value=v,
                expected_type="positive number",
            )
        if v > 3600:
            raise ConfigurationError(
                "Duration is too long, maximum is 3600 seconds (1 hour)",
                setting="duration",
                value=v,
                expected_type="number <= 3600",
            )
        return v

    @field_validator("queue_size")
    @classmethod
    def validate_queue_size(cls, v: int) -> int:
        if v <= 0:
            raise ConfigurationError(
                "Queue size must be positive",
                setting="queue_size",
                value=v,
                expected_type="positive integer",
            )
        if v > 100000:
            raise ConfigurationError(
                "Queue size is too large, maximum is 100000",
                setting="queue_size",
                value=v,
                expected_type="integer <= 100000",
            )
        return v

    @field_validator("batch_size")
    @classmethod
    def validate_batch_size(cls, v: int) -> int:
        if v <= 0:
            raise ConfigurationError(
                "Batch size must be positive",
                setting="batch_size",
                value=v,
                expected_type="positive integer",
            )
        if v > 1000:
            raise ConfigurationError(
                "Batch size is too large, maximum is 1000",
                setting="batch_size",
                value=v,
                expected_type="integer <= 1000",
            )
        return v

    @field_validator("batch_timeout")
    @classmethod
    def validate_batch_timeout(cls, v: float) -> float:
        if v <= 0:
            raise ConfigurationError(
                "Batch timeout must be positive",
                setting="batch_timeout",
                value=v,
                expected_type="positive number",
            )
        if v > 60:
            raise ConfigurationError(
                "Batch timeout is too long, maximum is 60 seconds",
                setting="batch_timeout",
                value=v,
                expected_type="number <= 60",
            )
        return v
