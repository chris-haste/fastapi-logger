"""Main configuration settings for fapilog."""

# os import needed for environment variable handling in field validator
import os
from typing import TYPE_CHECKING

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from ..exceptions import ConfigurationError
from .env_parsers import EnvironmentParsers
from .metrics_settings import MetricsSettings
from .queue_settings import QueueSettings
from .security_settings import SecuritySettings
from .sink_settings import SinkSettings
from .validation_settings import ValidationSettings

if TYPE_CHECKING:
    from ..sinks import Sink
else:
    # Import Sink at runtime for proper isinstance checks
    try:
        from ..sinks import Sink
    except ImportError:
        Sink = None


class LoggingSettings(BaseSettings):
    """Configuration settings for fapilog structured logging.

    Maps environment variables to logging behavior for easy configuration
    without code changes.
    """

    # Core logging settings
    level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARN, ERROR, CRITICAL)",
    )
    enable_resource_metrics: bool = Field(
        default=False,
        description="Enable memory and CPU usage metrics in log entries",
    )
    trace_id_header: str = Field(
        default="X-Request-ID",
        description="HTTP header name for incoming trace ID (default: X-Request-ID)",
    )
    enable_httpx_trace_propagation: bool = Field(
        default=False,
        description="Enable automatic trace ID propagation in httpx.AsyncClient "
        "(default: False)",
    )
    user_context_enabled: bool = Field(
        default=True,
        description="Enable user context enrichment in log entries (default: True)",
    )

    # Nested configuration settings
    queue: QueueSettings = Field(
        default_factory=QueueSettings,
        description="Queue configuration settings",
    )
    metrics: MetricsSettings = Field(
        default_factory=MetricsSettings,
        description="Metrics collection settings",
    )
    validation: ValidationSettings = Field(
        default_factory=ValidationSettings,
        description="Log validation settings",
    )
    security: SecuritySettings = Field(
        default_factory=SecuritySettings,
        description="Security settings including redaction, PII, throttling, deduplication",
    )
    sinks: SinkSettings = Field(
        default_factory=SinkSettings,
        description="Sink and output configuration settings",
    )

    model_config = SettingsConfigDict(
        env_prefix="FAPILOG_",
        case_sensitive=False,
        extra="forbid",  # No backward compatibility needed
        env_nested_delimiter="__",  # Enable nested environment variables
    )

    def __init__(self, **kwargs):
        """Initialize LoggingSettings with simplified environment variable handling."""
        # Handle legacy FAPILOG_SINKS environment variable by converting to nested format
        if "sinks" not in kwargs:
            env_sinks = os.environ.get("FAPILOG_SINKS")
            if env_sinks:
                # Convert legacy format to nested environment variables for Pydantic to parse
                # This eliminates the need for manual os.environ.pop() and restoration
                os.environ["FAPILOG_SINKS__SINKS"] = env_sinks

        super().__init__(**kwargs)

    @field_validator("sinks", mode="before")
    @classmethod
    def validate_sinks(cls, v):
        """Handle sinks field validation using centralized utilities."""
        if isinstance(v, SinkSettings):
            return v
        if isinstance(v, str):
            # Use centralized parsing for comma-separated strings from environment variables
            sink_list = EnvironmentParsers.parse_comma_separated_list(v)
            return SinkSettings(sinks=sink_list)
        if isinstance(v, list):
            # Create SinkSettings from the list
            return SinkSettings(sinks=v)
        if isinstance(v, dict):
            # Handle dict input (from nested environment variables like FAPILOG_SINKS__*)
            return SinkSettings(**v)
        return v

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        valid_levels = {"DEBUG", "INFO", "WARN", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            valid_list = ", ".join(sorted(valid_levels))
            raise ConfigurationError(
                f"Invalid level '{v}'. Must be one of: {valid_list}",
                "level",
                v,
                f"one of {valid_list}",
            )
        return v.upper()

    # Backward compatibility properties for direct access to nested settings
    @property
    def json_console(self) -> str:
        """Access to sinks.json_console for backward compatibility."""
        return self.sinks.json_console

    @property
    def sampling_rate(self) -> float:
        """Access to sinks.sampling_rate for backward compatibility."""
        return self.sinks.sampling_rate
