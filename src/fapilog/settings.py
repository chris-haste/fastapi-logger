"""Configuration settings for fapilog."""

from typing import Any, Dict, List, Literal, Union

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .exceptions import ConfigurationError

# Forward declaration to avoid circular imports
try:
    from ._internal.queue import Sink
except ImportError:
    # During imports, Sink might not be available yet
    Sink = None


class LoggingSettings(BaseSettings):
    """Configuration settings for fapilog structured logging.

    Maps environment variables to logging behavior for easy configuration
    without code changes.
    """

    level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARN, ERROR, CRITICAL)",
    )
    sinks: Union[List[Union[str, "Sink"]], str] = Field(
        default_factory=lambda: ["stdout"],
        description="List of sink names/URIs or sink instances for log output "
        "(comma-separated string or list)",
    )
    json_console: str = Field(
        default="auto",
        description="Console output format (auto, json, pretty)",
    )
    redact_patterns: Union[List[str], str] = Field(
        default_factory=lambda: [],
        description="List of regex patterns to redact from log messages "
        "(comma-separated or list)",
    )
    redact_fields: Union[List[str], str] = Field(
        default_factory=lambda: [],
        description="List of field names to redact from log messages "
        "(comma-separated or list, supports dot notation for nested fields)",
    )
    redact_replacement: str = Field(
        default="REDACTED",
        description="Replacement value for redacted fields",
    )
    redact_level: str = Field(
        default="INFO",
        description="Minimum log level for redaction (default: INFO)",
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
    queue_maxsize: int = Field(
        default=1000,
        description="Maximum size of the async log queue",
    )
    queue_overflow: Literal["drop", "block", "sample"] = Field(
        default="drop",
        description="Strategy for handling queue overflow: drop (discard), "
        "block (wait), or sample (probabilistic)",
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
    enable_auto_redact_pii: bool = Field(
        default=True,
        description="Enable automatic PII detection and redaction (default: True)",
    )
    custom_pii_patterns: List[str] = Field(
        default_factory=lambda: [],
        description="List of custom regex patterns for PII detection "
        "(comma-separated or list)",
    )
    # Metrics settings
    metrics_enabled: bool = Field(
        default=False,
        description="Enable metrics collection system (default: False)",
    )
    metrics_sample_window: int = Field(
        default=100,
        description="Number of recent samples to keep for averaging "
        "metrics (default: 100)",
    )
    metrics_prometheus_enabled: bool = Field(
        default=False,
        description="Enable Prometheus metrics exporter (default: False)",
    )
    metrics_prometheus_port: int = Field(
        default=8000,
        description="Port for Prometheus metrics HTTP endpoint (default: 8000)",
    )
    metrics_prometheus_host: str = Field(
        default="0.0.0.0",
        description="Host for Prometheus metrics HTTP endpoint (default: 0.0.0.0)",
    )
    # Validation settings
    enable_validation: bool = Field(
        default=False,
        description="Enable log event validation (default: False)",
    )
    validation_mode: str = Field(
        default="lenient",
        description="Validation mode: strict, lenient, fix (default: lenient)",
    )
    validation_required_fields: Union[List[str], str] = Field(
        default_factory=lambda: ["timestamp", "level", "event"],
        description="Required fields for log events (comma-separated or list)",
    )
    validation_field_types: Dict[str, str] = Field(
        default_factory=dict,
        description="Expected types for specific fields (field -> type mapping)",
    )
    # Processor metrics settings
    enable_processor_metrics: bool = Field(
        default=False,
        description="Enable processor performance metrics collection (default: False)",
    )
    processor_metrics_include_enrichers: bool = Field(
        default=True,
        description="Include enrichers in processor metrics (default: True)",
    )
    processor_metrics_reset_interval: int = Field(
        default=3600,
        description="Interval to reset processor metrics in seconds (0 = never)",
    )

    model_config = SettingsConfigDict(
        env_prefix="FAPILOG_",
        case_sensitive=False,
    )

    @field_validator("sinks", mode="before")
    @classmethod
    def parse_sinks(cls, v: Any) -> List[Union[str, "Sink"]]:
        """Parse sinks field to support strings and Sink instances."""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        if isinstance(v, (list, tuple)):
            # Support mixed list of strings and Sink instances
            result = []
            for item in v:
                if isinstance(item, str):
                    result.append(item.strip())
                elif Sink is not None and isinstance(item, Sink):
                    result.append(item)
                else:
                    # Convert other types to string
                    result.append(str(item))
            return result  # type: ignore[return-value]
        return [v]

    @field_validator("redact_patterns", mode="before")
    @classmethod
    def parse_redact_patterns(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return list(v) if isinstance(v, (list, tuple)) else [v]

    @field_validator("redact_fields", mode="before")
    @classmethod
    def parse_redact_fields(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return list(v) if isinstance(v, (list, tuple)) else [v]

    @field_validator("custom_pii_patterns", mode="before")
    @classmethod
    def parse_custom_pii_patterns(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return list(v) if isinstance(v, (list, tuple)) else [v]

    @field_validator("redact_level")
    @classmethod
    def validate_redact_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARN", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid:
            valid_list = ", ".join(sorted(valid))
            raise ConfigurationError(
                f"Invalid redact_level '{v}'. Must be one of: {valid_list}",
                "redact_level",
                v,
                f"one of {valid_list}",
            )
        return v.upper()

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

    @field_validator("json_console")
    @classmethod
    def validate_json_console(cls, v: str) -> str:
        valid_values = {"auto", "json", "pretty"}
        if v.lower() not in valid_values:
            valid_list = ", ".join(valid_values)
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
                f"Sampling rate must be between 0.0 and 1.0, got {v}",
                "sampling_rate",
                v,
                "between 0.0 and 1.0",
            )
        return v

    @field_validator("queue_maxsize")
    @classmethod
    def validate_queue_maxsize(cls, v: int) -> int:
        if v <= 0:
            raise ConfigurationError(
                "Queue maxsize must be positive", "queue_maxsize", v, "positive integer"
            )
        return v

    @field_validator("queue_batch_size")
    @classmethod
    def validate_queue_batch_size(cls, v: int) -> int:
        if v <= 0:
            raise ConfigurationError(
                "Queue batch size must be positive",
                "queue_batch_size",
                v,
                "positive integer",
            )
        return v

    @field_validator("queue_batch_timeout")
    @classmethod
    def validate_queue_batch_timeout(cls, v: float) -> float:
        if v <= 0:
            raise ConfigurationError(
                "Queue batch timeout must be positive",
                "queue_batch_timeout",
                v,
                "positive float",
            )
        return v

    @field_validator("queue_retry_delay")
    @classmethod
    def validate_queue_retry_delay(cls, v: float) -> float:
        if v <= 0:
            raise ConfigurationError(
                "Queue retry delay must be positive",
                "queue_retry_delay",
                v,
                "positive float",
            )
        return v

    @field_validator("queue_max_retries")
    @classmethod
    def validate_queue_max_retries(cls, v: int) -> int:
        if v < 0:
            raise ConfigurationError(
                "Queue max retries must be non-negative",
                "queue_max_retries",
                v,
                "non-negative integer",
            )
        return v

    @field_validator("queue_overflow")
    @classmethod
    def validate_queue_overflow(cls, v: str) -> str:
        valid_strategies = {"drop", "block", "sample"}
        if v.lower() not in valid_strategies:
            valid_list = ", ".join(sorted(valid_strategies))
            raise ConfigurationError(
                f"Invalid queue_overflow '{v}'. Must be one of: {valid_list}",
                "queue_overflow",
                v,
                f"one of {valid_list}",
            )
        return v.lower()

    @field_validator("validation_mode")
    @classmethod
    def validate_validation_mode(cls, v: str) -> str:
        valid_modes = {"strict", "lenient", "fix"}
        if v.lower() not in valid_modes:
            valid_list = ", ".join(sorted(valid_modes))
            raise ConfigurationError(
                f"Invalid validation_mode '{v}'. Must be one of: {valid_list}",
                "validation_mode",
                v,
                f"one of {valid_list}",
            )
        return v.lower()

    @field_validator("validation_required_fields", mode="before")
    @classmethod
    def parse_validation_required_fields(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return list(v) if isinstance(v, (list, tuple)) else [v]

    @field_validator("validation_field_types", mode="before")
    @classmethod
    def parse_validation_field_types(cls, v: Any) -> Dict[str, str]:
        if isinstance(v, str):
            # Parse comma-separated key:value pairs
            result = {}
            for item in v.split(","):
                if ":" in item:
                    key, value = item.split(":", 1)
                    result[key.strip()] = value.strip()
            return result
        return dict(v) if isinstance(v, dict) else {}

    @field_validator("processor_metrics_reset_interval")
    @classmethod
    def validate_processor_metrics_reset_interval(cls, v: int) -> int:
        if v < 0:
            raise ConfigurationError(
                "Processor metrics reset interval must be non-negative",
                "processor_metrics_reset_interval",
                v,
                "non-negative integer",
            )
        return v
