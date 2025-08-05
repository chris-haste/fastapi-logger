"""Enhanced Configuration Factory with environment variable support and validation.

This module provides an enhanced ConfigurationFactory that supports:
- Environment variable overrides for factory presets
- Partial configuration updates with deep merging
- Validation of factory-generated configurations
- Configuration health checks and warnings
"""

import os
from typing import Any, Dict, Optional, Union

from pydantic import ValidationError

from ..exceptions import ConfigurationError
from .factory import ConfigurationFactory
from .settings import LoggingSettings


class EnhancedConfigurationFactory:
    """Enhanced factory for creating environment-aware configuration presets.

    Provides advanced configuration management with environment variable support,
    partial updates, and comprehensive validation.
    """

    # Environment variable prefix for factory overrides
    FACTORY_ENV_PREFIX = "FAPILOG_FACTORY_"

    @staticmethod
    def development(**overrides: Any) -> LoggingSettings:
        """Development preset with environment variable support.

        Environment variables that can override defaults:
        - FAPILOG_FACTORY_DEVELOPMENT_LEVEL: Override log level
        - FAPILOG_FACTORY_DEVELOPMENT_QUEUE_MAXSIZE: Override queue size
        - FAPILOG_FACTORY_DEVELOPMENT_SECURITY_ENABLE_AUTO_REDACT_PII: Override PII redaction
        - FAPILOG_FACTORY_DEVELOPMENT_SINKS_JSON_CONSOLE: Override console format

        Args:
            **overrides: Custom settings to override defaults and environment variables

        Returns:
            LoggingSettings configured for development environment

        Example:
            >>> # Set environment variable
            >>> os.environ["FAPILOG_FACTORY_DEVELOPMENT_LEVEL"] = "INFO"
            >>> config = EnhancedConfigurationFactory.development()
            >>> assert config.level == "INFO"  # Environment variable applied
        """
        # Get base configuration from original factory
        base_config = ConfigurationFactory.development()

        # Apply environment variable overrides
        env_overrides = EnhancedConfigurationFactory._get_environment_overrides(
            "development"
        )

        # Merge: base_config + env_overrides + overrides (overrides take precedence)
        final_config = EnhancedConfigurationFactory._merge_configurations(
            base_config, env_overrides, overrides
        )

        # Validate the final configuration
        EnhancedConfigurationFactory._validate_configuration(
            final_config, "development"
        )

        return final_config

    @staticmethod
    def production(**overrides: Any) -> LoggingSettings:
        """Production preset with environment variable support.

        Environment variables that can override defaults:
        - FAPILOG_FACTORY_PRODUCTION_LEVEL: Override log level
        - FAPILOG_FACTORY_PRODUCTION_QUEUE_MAXSIZE: Override queue size
        - FAPILOG_FACTORY_PRODUCTION_SECURITY_ENABLE_AUTO_REDACT_PII: Override PII redaction
        - FAPILOG_FACTORY_PRODUCTION_METRICS_ENABLED: Override metrics collection

        Args:
            **overrides: Custom settings to override defaults and environment variables

        Returns:
            LoggingSettings configured for production environment
        """
        base_config = ConfigurationFactory.production()
        env_overrides = EnhancedConfigurationFactory._get_environment_overrides(
            "production"
        )

        final_config = EnhancedConfigurationFactory._merge_configurations(
            base_config, env_overrides, overrides
        )

        EnhancedConfigurationFactory._validate_configuration(final_config, "production")
        return final_config

    @staticmethod
    def testing(**overrides: Any) -> LoggingSettings:
        """Testing preset with environment variable support.

        Environment variables that can override defaults:
        - FAPILOG_FACTORY_TESTING_LEVEL: Override log level
        - FAPILOG_FACTORY_TESTING_QUEUE_ENABLED: Override queue enabled state
        - FAPILOG_FACTORY_TESTING_SECURITY_ENABLE_AUTO_REDACT_PII: Override PII redaction

        Args:
            **overrides: Custom settings to override defaults and environment variables

        Returns:
            LoggingSettings configured for testing environment
        """
        base_config = ConfigurationFactory.testing()
        env_overrides = EnhancedConfigurationFactory._get_environment_overrides(
            "testing"
        )

        final_config = EnhancedConfigurationFactory._merge_configurations(
            base_config, env_overrides, overrides
        )

        EnhancedConfigurationFactory._validate_configuration(final_config, "testing")
        return final_config

    @staticmethod
    def high_performance(**overrides: Any) -> LoggingSettings:
        """High-performance preset with environment variable support.

        Environment variables that can override defaults:
        - FAPILOG_FACTORY_HIGH_PERFORMANCE_LEVEL: Override log level
        - FAPILOG_FACTORY_HIGH_PERFORMANCE_QUEUE_MAXSIZE: Override queue size
        - FAPILOG_FACTORY_HIGH_PERFORMANCE_SINKS_SAMPLING_RATE: Override sampling rate

        Args:
            **overrides: Custom settings to override defaults and environment variables

        Returns:
            LoggingSettings configured for high-performance environment
        """
        base_config = ConfigurationFactory.high_performance()
        env_overrides = EnhancedConfigurationFactory._get_environment_overrides(
            "high_performance"
        )

        final_config = EnhancedConfigurationFactory._merge_configurations(
            base_config, env_overrides, overrides
        )

        EnhancedConfigurationFactory._validate_configuration(
            final_config, "high_performance"
        )
        return final_config

    @staticmethod
    def monitoring(**overrides: Any) -> LoggingSettings:
        """Monitoring preset with environment variable support.

        Environment variables that can override defaults:
        - FAPILOG_FACTORY_MONITORING_LEVEL: Override log level
        - FAPILOG_FACTORY_MONITORING_METRICS_ENABLED: Override metrics collection
        - FAPILOG_FACTORY_MONITORING_METRICS_PROMETHEUS_PORT: Override Prometheus port

        Args:
            **overrides: Custom settings to override defaults and environment variables

        Returns:
            LoggingSettings configured for monitoring environment
        """
        base_config = ConfigurationFactory.monitoring()
        env_overrides = EnhancedConfigurationFactory._get_environment_overrides(
            "monitoring"
        )

        final_config = EnhancedConfigurationFactory._merge_configurations(
            base_config, env_overrides, overrides
        )

        EnhancedConfigurationFactory._validate_configuration(final_config, "monitoring")
        return final_config

    @staticmethod
    def custom(
        base_preset: str = "production",
        partial_updates: Optional[Dict[str, Any]] = None,
        **overrides: Any,
    ) -> LoggingSettings:
        """Create a custom configuration with partial updates and environment support.

        Args:
            base_preset: Name of the base preset to start from
            partial_updates: Dictionary of partial updates to apply
            **overrides: Custom settings to override (highest precedence)

        Returns:
            LoggingSettings with customized configuration

        Example:
            >>> config = EnhancedConfigurationFactory.custom(
            ...     base_preset="production",
            ...     partial_updates={
            ...         "queue": {"maxsize": 2000},
            ...         "security": {"enable_auto_redact_pii": True}
            ...     },
            ...     level="DEBUG"
            ... )
        """
        preset_methods = {
            "development": EnhancedConfigurationFactory.development,
            "production": EnhancedConfigurationFactory.production,
            "testing": EnhancedConfigurationFactory.testing,
            "high_performance": EnhancedConfigurationFactory.high_performance,
            "monitoring": EnhancedConfigurationFactory.monitoring,
        }

        if base_preset not in preset_methods:
            valid_presets = ", ".join(preset_methods.keys())
            raise ValueError(
                f"Invalid base_preset '{base_preset}'. Must be one of: {valid_presets}"
            )

        # Get base configuration
        base_config = preset_methods[base_preset]()

        # Apply partial updates if provided
        if partial_updates:
            base_config = EnhancedConfigurationFactory._apply_partial_updates(
                base_config, partial_updates
            )

        # Apply final overrides
        if overrides:
            base_config = EnhancedConfigurationFactory._apply_overrides(
                base_config, overrides
            )

        return base_config

    @staticmethod
    def _get_environment_overrides(preset_name: str) -> Dict[str, Any]:
        """Extract environment variable overrides for a specific preset.

        Args:
            preset_name: Name of the preset (e.g., "development", "production")

        Returns:
            Dictionary of environment variable overrides
        """
        # Define the mapping from environment variable names to configuration paths
        env_var_mapping = {
            # Top-level settings
            "level": "level",
            "enable_resource_metrics": "enable_resource_metrics",
            "trace_id_header": "trace_id_header",
            "enable_httpx_trace_propagation": "enable_httpx_trace_propagation",
            "user_context_enabled": "user_context_enabled",
            # Queue settings
            "queue_enabled": "queue.enabled",
            "queue_maxsize": "queue.maxsize",
            "queue_overflow": "queue.overflow",
            "queue_batch_size": "queue.batch_size",
            "queue_batch_timeout": "queue.batch_timeout",
            "queue_retry_delay": "queue.retry_delay",
            "queue_max_retries": "queue.max_retries",
            # Security settings
            "security_redact_patterns": "security.redact_patterns",
            "security_redact_fields": "security.redact_fields",
            "security_redact_replacement": "security.redact_replacement",
            "security_redact_level": "security.redact_level",
            "security_enable_auto_redact_pii": "security.enable_auto_redact_pii",
            "security_custom_pii_patterns": "security.custom_pii_patterns",
            "security_enable_throttling": "security.enable_throttling",
            "security_throttle_max_rate": "security.throttle_max_rate",
            "security_throttle_window_seconds": "security.throttle_window_seconds",
            "security_throttle_key_field": "security.throttle_key_field",
            "security_throttle_strategy": "security.throttle_strategy",
            "security_enable_deduplication": "security.enable_deduplication",
            "security_dedupe_window_seconds": "security.dedupe_window_seconds",
            "security_dedupe_fields": "security.dedupe_fields",
            "security_dedupe_max_cache_size": "security.dedupe_max_cache_size",
            "security_dedupe_hash_algorithm": "security.dedupe_hash_algorithm",
            # Sink settings
            "sinks_sinks": "sinks.sinks",
            "sinks_json_console": "sinks.json_console",
            "sinks_sampling_rate": "sinks.sampling_rate",
            # Metrics settings
            "metrics_enabled": "metrics.enabled",
            "metrics_sample_window": "metrics.sample_window",
            "metrics_prometheus_enabled": "metrics.prometheus_enabled",
            "metrics_prometheus_port": "metrics.prometheus_port",
            "metrics_prometheus_host": "metrics.prometheus_host",
            "metrics_processor_enabled": "metrics.processor_enabled",
            "metrics_processor_include_enrichers": "metrics.processor_include_enrichers",
            "metrics_processor_reset_interval": "metrics.processor_reset_interval",
            # Validation settings
            "validation_enabled": "validation.enabled",
            "validation_mode": "validation.mode",
            "validation_required_fields": "validation.required_fields",
            "validation_field_types": "validation.field_types",
        }

        env_overrides = {}
        env_prefix = (
            f"{EnhancedConfigurationFactory.FACTORY_ENV_PREFIX}{preset_name.upper()}_"
        )

        for key, value in os.environ.items():
            if key.startswith(env_prefix):
                # Extract the configuration key from environment variable
                config_key = key[len(env_prefix) :].lower()
                parsed_value = EnhancedConfigurationFactory._parse_env_value(value)

                # Map to the correct configuration path
                if config_key in env_var_mapping:
                    config_path = env_var_mapping[config_key]
                    EnhancedConfigurationFactory._set_nested_value(
                        env_overrides, config_path, parsed_value
                    )

        return env_overrides

    @staticmethod
    def _convert_flat_to_nested(flat_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Convert flat dictionary with underscore-separated keys to nested structure.

        Args:
            flat_dict: Flat dictionary with keys like "queue_maxsize"

        Returns:
            Nested dictionary with structure like {"queue": {"maxsize": value}}
        """
        nested_dict = {}

        for key, value in flat_dict.items():
            # Convert underscore-separated keys to nested structure
            parts = key.split("_")
            current = nested_dict

            # Navigate to the parent of the target key
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            # Set the final value
            current[parts[-1]] = value

        return nested_dict

    @staticmethod
    def _parse_env_value(value: str) -> Union[str, int, float, bool]:
        """Parse environment variable value to appropriate type.

        Args:
            value: Raw environment variable value

        Returns:
            Parsed value with appropriate type
        """
        # Boolean values
        if value.lower() in ("true", "false"):
            return value.lower() == "true"

        # Integer values
        try:
            return int(value)
        except ValueError:
            # Not an integer, try float
            try:
                return float(value)
            except ValueError:
                # Not a float, return as string
                return value

    @staticmethod
    def _set_nested_value(config_dict: Dict[str, Any], path: str, value: Any) -> None:
        """Set a nested value in configuration dictionary.

        Args:
            config_dict: Configuration dictionary to modify
            path: Dot-separated path to the value (e.g., "queue.maxsize")
            value: Value to set
        """
        keys = path.split(".")
        current = config_dict

        # Navigate to the parent of the target key
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        # Set the final value
        current[keys[-1]] = value

    @staticmethod
    def _merge_configurations(
        base_config: LoggingSettings,
        env_overrides: Dict[str, Any],
        overrides: Dict[str, Any],
    ) -> LoggingSettings:
        """Merge configurations with proper precedence.

        Precedence order: base_config < env_overrides < overrides

        Args:
            base_config: Base configuration from factory preset
            env_overrides: Environment variable overrides
            overrides: Programmatic overrides (highest precedence)

        Returns:
            Merged LoggingSettings configuration
        """
        # Convert base config to dict
        config_dict = base_config.model_dump()

        # Apply environment overrides
        for key, value in env_overrides.items():
            EnhancedConfigurationFactory._set_nested_value(config_dict, key, value)

        # Apply programmatic overrides
        for key, value in overrides.items():
            EnhancedConfigurationFactory._set_nested_value(config_dict, key, value)

        # Create new LoggingSettings from merged dict
        try:
            return LoggingSettings(**config_dict)
        except Exception:
            # If direct creation fails, try to handle nested structures properly
            # This is a fallback for complex nested configurations
            return EnhancedConfigurationFactory._create_settings_safely(config_dict)

    @staticmethod
    def _apply_partial_updates(
        config: LoggingSettings, partial_updates: Dict[str, Any]
    ) -> LoggingSettings:
        """Apply partial updates to configuration.

        Args:
            config: Base configuration
            partial_updates: Dictionary of partial updates

        Returns:
            Updated LoggingSettings configuration
        """
        config_dict = config.model_dump()

        for section, updates in partial_updates.items():
            if section in config_dict and isinstance(updates, dict):
                if isinstance(config_dict[section], dict):
                    config_dict[section].update(updates)
                else:
                    # Handle nested settings objects
                    section_config = getattr(config, section)
                    if hasattr(section_config, "model_dump"):
                        section_dict = section_config.model_dump()
                        section_dict.update(updates)
                        config_dict[section] = section_dict

        return LoggingSettings(**config_dict)

    @staticmethod
    def _apply_overrides(
        config: LoggingSettings, overrides: Dict[str, Any]
    ) -> LoggingSettings:
        """Apply overrides to configuration.

        Args:
            config: Base configuration
            overrides: Override values

        Returns:
            Updated LoggingSettings configuration
        """
        config_dict = config.model_dump()
        config_dict.update(overrides)
        return LoggingSettings(**config_dict)

    @staticmethod
    def _validate_configuration(config: LoggingSettings, preset_name: str) -> None:
        """Validate factory-generated configuration.

        Args:
            config: Configuration to validate
            preset_name: Name of the preset for context

        Raises:
            ConfigurationError: If configuration is invalid
        """
        try:
            # Validate the configuration by creating a new instance
            LoggingSettings(**config.model_dump())
        except ValidationError as e:
            raise ConfigurationError(
                f"Invalid configuration for {preset_name} preset: {e}",
                "factory_configuration",
                str(config),
                "valid LoggingSettings configuration",
            ) from e

    @staticmethod
    def health_check(config: LoggingSettings) -> Dict[str, Any]:
        """Perform a health check on configuration.

        Args:
            config: Configuration to check

        Returns:
            Dictionary with health check results
        """

        health_results: Dict[str, Any] = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "recommendations": [],
        }

        # Check for common issues
        if config.queue.enabled and config.queue.maxsize < 100:
            health_results["warnings"].append(
                "Queue maxsize is very small for production use"
            )

        if config.level == "DEBUG" and config.metrics.enabled:
            health_results["warnings"].append(
                "DEBUG level with metrics enabled may impact performance"
            )

        if config.security.enable_auto_redact_pii and config.level == "DEBUG":
            health_results["warnings"].append(
                "PII redaction enabled at DEBUG level may hide useful information"
            )

        if config.sinks.sampling_rate < 0.1:
            health_results["warnings"].append(
                "Very low sampling rate may miss important logs"
            )

        # Check for potential conflicts
        if config.queue.overflow == "block" and config.queue.maxsize < 1000:
            health_results["recommendations"].append(
                "Consider increasing queue maxsize or using 'drop' overflow strategy"
            )

        if config.metrics.prometheus_enabled and config.metrics.prometheus_port == 8000:
            health_results["recommendations"].append(
                "Consider using a different port for Prometheus metrics (8000 is common for web servers)"
            )

        return health_results

    @staticmethod
    def get_environment_variables(preset_name: str) -> Dict[str, str]:
        """Get available environment variables for a preset.

        Args:
            preset_name: Name of the preset

        Returns:
            Dictionary mapping environment variable names to descriptions
        """
        env_vars = {
            f"{EnhancedConfigurationFactory.FACTORY_ENV_PREFIX}{preset_name.upper()}_LEVEL": (
                f"Override log level for {preset_name} preset"
            ),
            f"{EnhancedConfigurationFactory.FACTORY_ENV_PREFIX}{preset_name.upper()}_QUEUE_MAXSIZE": (
                f"Override queue maxsize for {preset_name} preset"
            ),
            f"{EnhancedConfigurationFactory.FACTORY_ENV_PREFIX}{preset_name.upper()}_SECURITY_ENABLE_AUTO_REDACT_PII": (
                f"Override PII redaction for {preset_name} preset"
            ),
            f"{EnhancedConfigurationFactory.FACTORY_ENV_PREFIX}{preset_name.upper()}_SINKS_JSON_CONSOLE": (
                f"Override console format for {preset_name} preset"
            ),
            f"{EnhancedConfigurationFactory.FACTORY_ENV_PREFIX}{preset_name.upper()}_METRICS_ENABLED": (
                f"Override metrics collection for {preset_name} preset"
            ),
        }

        return env_vars

    @staticmethod
    def _create_settings_safely(config_dict: Dict[str, Any]) -> LoggingSettings:
        """Create LoggingSettings safely by handling nested structures properly.

        Args:
            config_dict: Configuration dictionary with nested structures

        Returns:
            LoggingSettings instance
        """
        # Extract nested settings
        queue_config = config_dict.get("queue", {})
        security_config = config_dict.get("security", {})
        sinks_config = config_dict.get("sinks", {})
        metrics_config = config_dict.get("metrics", {})
        validation_config = config_dict.get("validation", {})

        # Create nested settings objects
        from .metrics_settings import MetricsSettings
        from .queue_settings import QueueSettings
        from .security_settings import SecuritySettings
        from .sink_settings import SinkSettings
        from .validation_settings import ValidationSettings

        # Create the main settings with nested objects
        return LoggingSettings(
            level=config_dict.get("level", "INFO"),
            enable_resource_metrics=config_dict.get("enable_resource_metrics", False),
            trace_id_header=config_dict.get("trace_id_header", "X-Request-ID"),
            enable_httpx_trace_propagation=config_dict.get(
                "enable_httpx_trace_propagation", False
            ),
            user_context_enabled=config_dict.get("user_context_enabled", True),
            queue=QueueSettings(**queue_config) if queue_config else QueueSettings(),
            security=SecuritySettings(**security_config)
            if security_config
            else SecuritySettings(),
            sinks=SinkSettings(**sinks_config) if sinks_config else SinkSettings(),
            metrics=MetricsSettings(**metrics_config)
            if metrics_config
            else MetricsSettings(),
            validation=ValidationSettings(**validation_config)
            if validation_config
            else ValidationSettings(),
        )
