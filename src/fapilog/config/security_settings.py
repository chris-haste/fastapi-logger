"""Security configuration settings for fapilog."""

from typing import Any, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from ..exceptions import ConfigurationError


class SecuritySettings(BaseSettings):
    """Configuration settings for security features including redaction, PII detection, throttling, and deduplication."""

    # Redaction settings
    redact_patterns: List[str] = Field(
        default_factory=lambda: [],
        description="List of regex patterns to redact from log messages "
        "(comma-separated or list)",
    )
    redact_fields: List[str] = Field(
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

    # PII Detection settings
    enable_auto_redact_pii: bool = Field(
        default=False,
        description="Enable automatic PII detection and redaction using built-in patterns",
    )
    custom_pii_patterns: List[str] = Field(
        default_factory=lambda: [],
        description="Custom PII patterns to add to the default set "
        "(comma-separated or list)",
    )

    # Throttling settings
    enable_throttling: bool = Field(
        default=False,
        description="Enable log throttling to prevent flooding",
    )
    throttle_max_rate: int = Field(
        default=100,
        description="Maximum events per window per key",
    )
    throttle_window_seconds: int = Field(
        default=60,
        description="Throttling window in seconds",
    )
    throttle_key_field: str = Field(
        default="source",
        description="Field to use as throttling key",
    )
    throttle_strategy: str = Field(
        default="drop",
        description="Throttling strategy: drop, sample",
    )

    # Deduplication settings
    enable_deduplication: bool = Field(
        default=False,
        description="Enable log deduplication to remove duplicates",
    )
    dedupe_window_seconds: int = Field(
        default=300,
        description="Deduplication window in seconds",
    )
    dedupe_fields: List[str] = Field(
        default_factory=lambda: ["event", "level", "hostname"],
        description="Fields to use for deduplication signature",
    )
    dedupe_max_cache_size: int = Field(
        default=10000,
        description="Maximum deduplication cache size",
    )
    dedupe_hash_algorithm: str = Field(
        default="md5",
        description="Hash algorithm for signatures: md5, sha1, sha256",
    )

    model_config = SettingsConfigDict(
        env_prefix="FAPILOG_SECURITY_",
        case_sensitive=False,
    )

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
