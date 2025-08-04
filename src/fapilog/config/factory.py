"""Configuration factory for creating environment-specific presets for fapilog.

This module provides the ConfigurationFactory class that creates optimized
configuration presets for common deployment environments and use cases.
"""

from typing import Any, Dict

from .metrics_settings import MetricsSettings
from .queue_settings import QueueSettings
from .security_settings import SecuritySettings
from .settings import LoggingSettings
from .sink_settings import SinkSettings
from .validation_settings import ValidationSettings


class ConfigurationFactory:
    """Factory for creating environment-specific configuration presets.

    Provides tested, optimized configuration presets for common environments
    and use cases, reducing duplication and ensuring consistent setups.
    """

    @staticmethod
    def development(**overrides: Any) -> LoggingSettings:
        """Development preset: pretty console, debug level, fast queues.

        Optimized for development with:
        - DEBUG logging level for detailed information
        - Pretty console output for readability
        - Small queue sizes for immediate feedback
        - Fast batch processing
        - Resource metrics disabled for performance

        Args:
            **overrides: Custom settings to override defaults

        Returns:
            LoggingSettings configured for development environment

        Example:
            >>> config = ConfigurationFactory.development(level="INFO")
            >>> logger, container = create_logger(config)
        """
        defaults = {
            "level": "DEBUG",
            "enable_resource_metrics": False,
            "enable_httpx_trace_propagation": True,
            "user_context_enabled": True,
            "sinks": SinkSettings(
                sinks=["stdout"],
                json_console="pretty",
                sampling_rate=1.0,
            ),
            "queue": QueueSettings(
                enabled=True,
                maxsize=100,
                batch_size=1,
                batch_timeout=0.1,
                overflow="block",  # Block in dev for debugging
                retry_delay=0.5,
                max_retries=3,
            ),
            "security": SecuritySettings(
                enable_auto_redact_pii=False,  # Disabled for development
                redact_level="CRITICAL",  # Only redact critical logs in dev
            ),
            "metrics": MetricsSettings(
                enabled=False,  # Disabled for development
                sample_window=30,
                prometheus_enabled=False,
            ),
            "validation": ValidationSettings(
                required_fields=[],  # Minimal validation in dev
                field_types={},
            ),
        }

        # Apply overrides
        defaults.update(overrides)
        return LoggingSettings(**defaults)

    @staticmethod
    def production(**overrides: Any) -> LoggingSettings:
        """Production preset: JSON output, structured logging.

        Optimized for production with:
        - INFO logging level for performance
        - JSON console output for log aggregation
        - Optimized queue sizes for throughput
        - PII redaction enabled for security
        - Metrics collection enabled

        Args:
            **overrides: Custom settings to override defaults

        Returns:
            LoggingSettings configured for production environment

        Example:
            >>> config = ConfigurationFactory.production(
            ...     sinks=SinkSettings(sinks=["stdout", "file:///logs/app"])
            ... )
            >>> logger, container = create_logger(config)
        """
        defaults = {
            "level": "INFO",
            "enable_resource_metrics": True,
            "enable_httpx_trace_propagation": True,
            "user_context_enabled": True,
            "sinks": SinkSettings(
                sinks=["stdout"],
                json_console="json",
                sampling_rate=1.0,
            ),
            "queue": QueueSettings(
                enabled=True,
                maxsize=1000,
                batch_size=10,
                batch_timeout=1.0,
                overflow="drop",  # Drop excess logs in production
                retry_delay=2.0,
                max_retries=5,
            ),
            "security": SecuritySettings(
                enable_auto_redact_pii=True,
                redact_level="INFO",
                redact_replacement="[REDACTED]",
                enable_throttling=True,
                throttle_max_rate=100,  # 100 logs per window per source
                throttle_window_seconds=60,
                enable_deduplication=True,
                dedupe_window_seconds=300,  # 5 minutes
            ),
            "metrics": MetricsSettings(
                enabled=True,
                sample_window=60,
                prometheus_enabled=True,
                prometheus_port=9090,
            ),
            "validation": ValidationSettings(
                required_fields=["timestamp", "level", "message"],
                field_types={
                    "timestamp": "datetime",
                    "level": "str",
                    "message": "str",
                },
            ),
        }

        # Apply overrides
        defaults.update(overrides)
        return LoggingSettings(**defaults)

    @staticmethod
    def testing(**overrides: Any) -> LoggingSettings:
        """Testing preset: minimal overhead, synchronous processing.

        Optimized for testing with:
        - DEBUG logging level for test debugging
        - Synchronous processing for predictable behavior
        - No queues or batching
        - Minimal security features
        - No metrics collection

        Args:
            **overrides: Custom settings to override defaults

        Returns:
            LoggingSettings configured for testing environment

        Example:
            >>> config = ConfigurationFactory.testing(level="ERROR")
            >>> logger, container = create_logger(config)
        """
        defaults = {
            "level": "DEBUG",
            "enable_resource_metrics": False,
            "enable_httpx_trace_propagation": False,
            "user_context_enabled": False,
            "sinks": SinkSettings(
                sinks=["stdout"],
                json_console="auto",
                sampling_rate=1.0,
            ),
            "queue": QueueSettings(
                enabled=False,  # Synchronous for predictable testing
            ),
            "security": SecuritySettings(
                enable_auto_redact_pii=False,
                enable_throttling=False,
                enable_deduplication=False,
            ),
            "metrics": MetricsSettings(
                enabled=False,
                prometheus_enabled=False,
            ),
            "validation": ValidationSettings(
                required_fields=[],
                field_types={},
            ),
        }

        # Apply overrides
        defaults.update(overrides)
        return LoggingSettings(**defaults)

    @staticmethod
    def high_performance(**overrides: Any) -> LoggingSettings:
        """High-performance preset: optimized for throughput.

        Optimized for high-throughput scenarios with:
        - WARNING logging level to reduce volume
        - Aggressive sampling to reduce overhead
        - Large queue sizes for buffering
        - Drop overflow strategy for performance
        - Minimal security processing

        Args:
            **overrides: Custom settings to override defaults

        Returns:
            LoggingSettings configured for high-performance scenarios

        Example:
            >>> config = ConfigurationFactory.high_performance()
            >>> logger, container = create_logger(config)
        """
        defaults = {
            "level": "WARNING",
            "enable_resource_metrics": False,  # Disabled for performance
            "enable_httpx_trace_propagation": False,
            "user_context_enabled": False,  # Disabled for performance
            "sinks": SinkSettings(
                sinks=["stdout"],
                json_console="json",
                sampling_rate=0.1,  # Sample only 10% of logs
            ),
            "queue": QueueSettings(
                enabled=True,
                maxsize=5000,  # Large queue for buffering
                batch_size=100,  # Large batches for efficiency
                batch_timeout=5.0,  # Longer timeout for bigger batches
                overflow="drop",  # Drop excess for performance
                retry_delay=0.1,  # Fast retries
                max_retries=1,  # Minimal retries
            ),
            "security": SecuritySettings(
                enable_auto_redact_pii=False,  # Disabled for performance
                enable_throttling=False,  # Disabled for performance
                enable_deduplication=False,  # Disabled for performance
            ),
            "metrics": MetricsSettings(
                enabled=False,  # Disabled for performance
                prometheus_enabled=False,
            ),
            "validation": ValidationSettings(
                required_fields=[],  # Minimal validation for performance
                field_types={},
            ),
        }

        # Apply overrides
        defaults.update(overrides)
        return LoggingSettings(**defaults)

    @staticmethod
    def monitoring(**overrides: Any) -> LoggingSettings:
        """Monitoring preset: optimized for observability and metrics.

        Optimized for monitoring and observability with:
        - INFO logging level for operational insight
        - Full metrics collection enabled
        - Resource monitoring enabled
        - Structured logging for analysis
        - Security features for compliance

        Args:
            **overrides: Custom settings to override defaults

        Returns:
            LoggingSettings configured for monitoring scenarios

        Example:
            >>> config = ConfigurationFactory.monitoring(
            ...     metrics=MetricsSettings(prometheus_port=9091)
            ... )
            >>> logger, container = create_logger(config)
        """
        defaults = {
            "level": "INFO",
            "enable_resource_metrics": True,
            "enable_httpx_trace_propagation": True,
            "user_context_enabled": True,
            "sinks": SinkSettings(
                sinks=["stdout"],
                json_console="json",
                sampling_rate=1.0,
            ),
            "queue": QueueSettings(
                enabled=True,
                maxsize=2000,
                batch_size=20,
                batch_timeout=2.0,
                overflow="sample",  # Sample when full
                retry_delay=1.0,
                max_retries=3,
            ),
            "security": SecuritySettings(
                enable_auto_redact_pii=True,
                redact_level="INFO",
                enable_throttling=False,  # Don't throttle monitoring logs
                enable_deduplication=True,
                dedupe_window_seconds=60,  # Shorter window for monitoring
            ),
            "metrics": MetricsSettings(
                enabled=True,
                sample_window=30,  # Frequent sampling for monitoring
                prometheus_enabled=True,
                prometheus_port=9090,
                prometheus_host="0.0.0.0",
            ),
            "validation": ValidationSettings(
                required_fields=["timestamp", "level", "message"],
                field_types={
                    "timestamp": "datetime",
                    "level": "str",
                    "message": "str",
                    "trace_id": "str",
                },
            ),
        }

        # Apply overrides
        defaults.update(overrides)
        return LoggingSettings(**defaults)

    @staticmethod
    def custom(base_preset: str = "production", **overrides: Any) -> LoggingSettings:
        """Create a custom configuration based on an existing preset.

        Allows starting with a preset and customizing specific aspects.

        Args:
            base_preset: Name of the base preset to start from
                ("development", "production", "testing", "high_performance",
                "monitoring")
            **overrides: Custom settings to override the base preset

        Returns:
            LoggingSettings with customized configuration

        Raises:
            ValueError: If base_preset is not a valid preset name

        Example:
            >>> config = ConfigurationFactory.custom(
            ...     base_preset="production",
            ...     level="DEBUG",
            ...     queue=QueueSettings(maxsize=2000)
            ... )
            >>> logger, container = create_logger(config)
        """
        preset_methods = {
            "development": ConfigurationFactory.development,
            "production": ConfigurationFactory.production,
            "testing": ConfigurationFactory.testing,
            "high_performance": ConfigurationFactory.high_performance,
            "monitoring": ConfigurationFactory.monitoring,
        }

        if base_preset not in preset_methods:
            valid_presets = ", ".join(preset_methods.keys())
            raise ValueError(
                f"Invalid base_preset '{base_preset}'. Must be one of: {valid_presets}"
            )

        return preset_methods[base_preset](**overrides)

    @staticmethod
    def get_available_presets() -> Dict[str, str]:
        """Get a list of available configuration presets with descriptions.

        Returns:
            Dictionary mapping preset names to their descriptions

        Example:
            >>> presets = ConfigurationFactory.get_available_presets()
            >>> print(presets["development"])
            'Development preset: pretty console, debug level, fast queues'
        """
        return {
            "development": (
                "Development preset: pretty console, debug level, fast queues"
            ),
            "production": (
                "Production preset: JSON output, structured logging, optimized queues"
            ),
            "testing": ("Testing preset: minimal overhead, synchronous processing"),
            "high_performance": ("High-performance preset: optimized for throughput"),
            "monitoring": (
                "Monitoring preset: optimized for observability and metrics"
            ),
        }
