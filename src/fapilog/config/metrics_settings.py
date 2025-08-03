"""Metrics configuration settings for fapilog."""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from ..exceptions import ConfigurationError


class MetricsSettings(BaseSettings):
    """Configuration settings for metrics collection."""

    enabled: bool = Field(
        default=False,
        description="Enable metrics collection system (default: False)",
    )
    sample_window: int = Field(
        default=100,
        description="Number of recent samples to keep for averaging "
        "metrics (default: 100)",
    )
    prometheus_enabled: bool = Field(
        default=False,
        description="Enable Prometheus metrics exporter (default: False)",
    )
    prometheus_port: int = Field(
        default=8000,
        description="Port for Prometheus metrics HTTP endpoint (default: 8000)",
    )
    prometheus_host: str = Field(
        default="0.0.0.0",
        description="Host for Prometheus metrics HTTP endpoint (default: 0.0.0.0)",
    )
    processor_enabled: bool = Field(
        default=False,
        description="Enable processor performance metrics collection (default: False)",
    )
    processor_include_enrichers: bool = Field(
        default=True,
        description="Include enrichers in processor metrics (default: True)",
    )
    processor_reset_interval: int = Field(
        default=3600,
        description="Interval to reset processor metrics in seconds (0 = never)",
    )

    model_config = SettingsConfigDict(
        env_prefix="",  # No environment parsing - handled by parent LoggingSettings
        case_sensitive=False,
    )

    @field_validator("processor_reset_interval")
    @classmethod
    def validate_processor_reset_interval(cls, v: int) -> int:
        if v < 0:
            raise ConfigurationError(
                "Processor metrics reset interval must be non-negative",
                "processor_reset_interval",
                v,
                "non-negative integer",
            )
        return v
