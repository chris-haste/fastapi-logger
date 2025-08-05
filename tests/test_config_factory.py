"""Tests for ConfigurationFactory preset configurations."""

import pytest

from fapilog.config.factory import ConfigurationFactory
from fapilog.config.metrics_settings import MetricsSettings
from fapilog.config.queue_settings import QueueSettings
from fapilog.config.security_settings import SecuritySettings
from fapilog.config.settings import LoggingSettings
from fapilog.config.sink_settings import SinkSettings
from fapilog.config.validation_settings import ValidationSettings


class TestConfigurationFactory:
    """Test suite for ConfigurationFactory preset methods."""

    def test_development_preset_defaults(self):
        """Test development preset returns correct default configuration."""
        config = ConfigurationFactory.development()

        assert isinstance(config, LoggingSettings)
        assert config.level == "DEBUG"
        assert config.enable_resource_metrics is False
        assert config.enable_httpx_trace_propagation is True
        assert config.user_context_enabled is True

        # Check sink settings
        assert isinstance(config.sinks, SinkSettings)
        assert config.sinks.sinks == ["stdout"]
        assert config.sinks.json_console == "pretty"
        assert config.sinks.sampling_rate == 1.0

        # Check queue settings
        assert isinstance(config.queue, QueueSettings)
        assert config.queue.enabled is True
        assert config.queue.maxsize == 100
        assert config.queue.batch_size == 1
        assert config.queue.batch_timeout == 0.1
        assert config.queue.overflow == "block"

        # Check security settings
        assert isinstance(config.security, SecuritySettings)
        assert config.security.enable_auto_redact_pii is False
        assert config.security.redact_level == "CRITICAL"

        # Check metrics settings
        assert isinstance(config.metrics, MetricsSettings)
        assert config.metrics.enabled is False
        assert config.metrics.prometheus_enabled is False

    def test_production_preset_defaults(self):
        """Test production preset returns correct default configuration."""
        config = ConfigurationFactory.production()

        assert isinstance(config, LoggingSettings)
        assert config.level == "INFO"
        assert config.enable_resource_metrics is True
        assert config.enable_httpx_trace_propagation is True
        assert config.user_context_enabled is True

        # Check sink settings
        assert isinstance(config.sinks, SinkSettings)
        assert config.sinks.sinks == ["stdout"]
        assert config.sinks.json_console == "json"
        assert config.sinks.sampling_rate == 1.0

        # Check queue settings
        assert isinstance(config.queue, QueueSettings)
        assert config.queue.enabled is True
        assert config.queue.maxsize == 1000
        assert config.queue.batch_size == 10
        assert config.queue.batch_timeout == 1.0
        assert config.queue.overflow == "drop"
        assert config.queue.retry_delay == 2.0
        assert config.queue.max_retries == 5

        # Check security settings
        assert isinstance(config.security, SecuritySettings)
        assert config.security.enable_auto_redact_pii is True
        assert config.security.redact_level == "INFO"
        assert config.security.redact_replacement == "[REDACTED]"
        assert config.security.enable_throttling is True
        assert config.security.throttle_max_rate == 100
        assert config.security.throttle_window_seconds == 60
        assert config.security.enable_deduplication is True
        assert config.security.dedupe_window_seconds == 300

        # Check metrics settings
        assert isinstance(config.metrics, MetricsSettings)
        assert config.metrics.enabled is True
        assert config.metrics.sample_window == 60
        assert config.metrics.prometheus_enabled is True
        assert config.metrics.prometheus_port == 9090

    def test_testing_preset_defaults(self):
        """Test testing preset returns correct default configuration."""
        config = ConfigurationFactory.testing()

        assert isinstance(config, LoggingSettings)
        assert config.level == "DEBUG"
        assert config.enable_resource_metrics is False
        assert config.enable_httpx_trace_propagation is False
        assert config.user_context_enabled is False

        # Check sink settings
        assert isinstance(config.sinks, SinkSettings)
        assert config.sinks.sinks == ["stdout"]
        assert config.sinks.json_console == "auto"
        assert config.sinks.sampling_rate == 1.0

        # Check queue settings - disabled for testing
        assert isinstance(config.queue, QueueSettings)
        assert config.queue.enabled is False

        # Check security settings - minimal for testing
        assert isinstance(config.security, SecuritySettings)
        assert config.security.enable_auto_redact_pii is False
        assert config.security.enable_throttling is False
        assert config.security.enable_deduplication is False

        # Check metrics settings - disabled for testing
        assert isinstance(config.metrics, MetricsSettings)
        assert config.metrics.enabled is False
        assert config.metrics.prometheus_enabled is False

    def test_high_performance_preset_defaults(self):
        """Test high_performance preset returns correct default configuration."""
        config = ConfigurationFactory.high_performance()

        assert isinstance(config, LoggingSettings)
        assert config.level == "WARNING"
        assert config.enable_resource_metrics is False
        assert config.enable_httpx_trace_propagation is False
        assert config.user_context_enabled is False

        # Check sink settings - optimized for performance
        assert isinstance(config.sinks, SinkSettings)
        assert config.sinks.sinks == ["stdout"]
        assert config.sinks.json_console == "json"
        assert config.sinks.sampling_rate == 0.1  # Heavy sampling

        # Check queue settings - large queues for performance
        assert isinstance(config.queue, QueueSettings)
        assert config.queue.enabled is True
        assert config.queue.maxsize == 5000
        assert config.queue.batch_size == 100
        assert config.queue.batch_timeout == 5.0
        assert config.queue.overflow == "drop"
        assert config.queue.retry_delay == 0.1
        assert config.queue.max_retries == 1

        # Check security settings - disabled for performance
        assert isinstance(config.security, SecuritySettings)
        assert config.security.enable_auto_redact_pii is False
        assert config.security.enable_throttling is False
        assert config.security.enable_deduplication is False

        # Check metrics settings - disabled for performance
        assert isinstance(config.metrics, MetricsSettings)
        assert config.metrics.enabled is False
        assert config.metrics.prometheus_enabled is False

    def test_monitoring_preset_defaults(self):
        """Test monitoring preset returns correct default configuration."""
        config = ConfigurationFactory.monitoring()

        assert isinstance(config, LoggingSettings)
        assert config.level == "INFO"
        assert config.enable_resource_metrics is True
        assert config.enable_httpx_trace_propagation is True
        assert config.user_context_enabled is True

        # Check sink settings
        assert isinstance(config.sinks, SinkSettings)
        assert config.sinks.sinks == ["stdout"]
        assert config.sinks.json_console == "json"
        assert config.sinks.sampling_rate == 1.0

        # Check queue settings
        assert isinstance(config.queue, QueueSettings)
        assert config.queue.enabled is True
        assert config.queue.maxsize == 2000
        assert config.queue.batch_size == 20
        assert config.queue.batch_timeout == 2.0
        assert config.queue.overflow == "sample"

        # Check security settings
        assert isinstance(config.security, SecuritySettings)
        assert config.security.enable_auto_redact_pii is True
        assert config.security.redact_level == "INFO"
        assert config.security.enable_throttling is False  # Don't throttle monitoring
        assert config.security.enable_deduplication is True
        assert config.security.dedupe_window_seconds == 60  # Shorter for monitoring

        # Check metrics settings - fully enabled for monitoring
        assert isinstance(config.metrics, MetricsSettings)
        assert config.metrics.enabled is True
        assert config.metrics.sample_window == 30  # Frequent sampling
        assert config.metrics.prometheus_enabled is True
        assert config.metrics.prometheus_port == 9090
        assert config.metrics.prometheus_host == "0.0.0.0"

    def test_development_preset_with_overrides(self):
        """Test development preset accepts and applies overrides."""
        config = ConfigurationFactory.development(
            level="INFO",
            enable_resource_metrics=True,
            sinks=SinkSettings(
                sinks=["stdout", "file:///tmp/dev.log"], json_console="json"
            ),
        )

        # Overridden values
        assert config.level == "INFO"
        assert config.enable_resource_metrics is True
        assert config.sinks.sinks == ["stdout", "file:///tmp/dev.log"]
        assert config.sinks.json_console == "json"

        # Non-overridden values should remain as defaults
        assert config.queue.batch_size == 1
        assert config.security.enable_auto_redact_pii is False

    def test_production_preset_with_overrides(self):
        """Test production preset accepts and applies overrides."""
        custom_security = SecuritySettings(
            enable_auto_redact_pii=False, redact_level="ERROR"
        )

        config = ConfigurationFactory.production(
            level="ERROR", security=custom_security
        )

        # Overridden values
        assert config.level == "ERROR"
        assert config.security.enable_auto_redact_pii is False
        assert config.security.redact_level == "ERROR"

        # Non-overridden values should remain as defaults
        assert config.queue.maxsize == 1000
        assert config.metrics.enabled is True

    def test_testing_preset_with_overrides(self):
        """Test testing preset accepts and applies overrides."""
        config = ConfigurationFactory.testing(
            level="ERROR", queue=QueueSettings(enabled=True, maxsize=50)
        )

        # Overridden values
        assert config.level == "ERROR"
        assert config.queue.enabled is True
        assert config.queue.maxsize == 50

        # Non-overridden values should remain as defaults
        assert config.enable_resource_metrics is False
        assert config.metrics.enabled is False

    def test_custom_with_valid_base_preset(self):
        """Test custom method with valid base presets."""
        # Test with production base
        config = ConfigurationFactory.custom(base_preset="production", level="DEBUG")

        # Should have production defaults with override
        assert config.level == "DEBUG"
        assert config.queue.maxsize == 1000  # Production default
        assert config.security.enable_auto_redact_pii is True  # Production default

        # Test with development base
        config = ConfigurationFactory.custom(
            base_preset="development", queue=QueueSettings(maxsize=200)
        )

        # Should have development defaults with override
        assert config.level == "DEBUG"  # Development default
        assert config.queue.maxsize == 200  # Override
        assert config.sinks.json_console == "pretty"  # Development default

    def test_custom_with_invalid_base_preset(self):
        """Test custom method raises error for invalid base preset."""
        with pytest.raises(ValueError) as exc_info:
            ConfigurationFactory.custom(base_preset="invalid_preset", level="INFO")

        assert "Invalid base_preset 'invalid_preset'" in str(exc_info.value)
        assert "Must be one of:" in str(exc_info.value)
        assert "development" in str(exc_info.value)
        assert "production" in str(exc_info.value)
        assert "testing" in str(exc_info.value)
        assert "high_performance" in str(exc_info.value)
        assert "monitoring" in str(exc_info.value)

    def test_get_available_presets(self):
        """Test get_available_presets returns correct preset information."""
        presets = ConfigurationFactory.get_available_presets()

        assert isinstance(presets, dict)
        assert len(presets) == 5

        # Check all expected presets are present
        expected_presets = {
            "development",
            "production",
            "testing",
            "high_performance",
            "monitoring",
        }
        assert set(presets.keys()) == expected_presets

        # Check descriptions are non-empty strings
        for preset_name, description in presets.items():
            assert isinstance(description, str)
            assert len(description) > 0
            assert preset_name.replace("_", "-") in description.lower()

    def test_all_preset_methods_return_valid_logging_settings(self):
        """Test that all preset methods return valid LoggingSettings instances."""
        preset_methods = [
            ConfigurationFactory.development,
            ConfigurationFactory.production,
            ConfigurationFactory.testing,
            ConfigurationFactory.high_performance,
            ConfigurationFactory.monitoring,
        ]

        for method in preset_methods:
            config = method()
            assert isinstance(config, LoggingSettings)

            # Basic validation that nested settings are correct types
            assert isinstance(config.sinks, SinkSettings)
            assert isinstance(config.queue, QueueSettings)
            assert isinstance(config.security, SecuritySettings)
            assert isinstance(config.metrics, MetricsSettings)
            assert isinstance(config.validation, ValidationSettings)

    def test_preset_configurations_have_different_characteristics(self):
        """Test that different presets have meaningfully different configurations."""
        dev_config = ConfigurationFactory.development()
        prod_config = ConfigurationFactory.production()
        test_config = ConfigurationFactory.testing()
        perf_config = ConfigurationFactory.high_performance()
        monitor_config = ConfigurationFactory.monitoring()

        # Different log levels
        assert dev_config.level == "DEBUG"
        assert prod_config.level == "INFO"
        assert test_config.level == "DEBUG"
        assert perf_config.level == "WARNING"
        assert monitor_config.level == "INFO"

        # Different queue configurations
        assert dev_config.queue.maxsize == 100
        assert prod_config.queue.maxsize == 1000
        assert test_config.queue.enabled is False
        assert perf_config.queue.maxsize == 5000
        assert monitor_config.queue.maxsize == 2000

        # Different security configurations
        assert dev_config.security.enable_auto_redact_pii is False
        assert prod_config.security.enable_auto_redact_pii is True
        assert test_config.security.enable_auto_redact_pii is False
        assert perf_config.security.enable_auto_redact_pii is False
        assert monitor_config.security.enable_auto_redact_pii is True

        # Different metrics configurations
        assert dev_config.metrics.enabled is False
        assert prod_config.metrics.enabled is True
        assert test_config.metrics.enabled is False
        assert perf_config.metrics.enabled is False
        assert monitor_config.metrics.enabled is True

    def test_preset_overrides_preserve_nested_structure(self):
        """Test that overrides properly update nested configuration objects."""
        # Test partial queue override
        config = ConfigurationFactory.production(
            queue=QueueSettings(maxsize=2000, batch_size=20)
        )

        # Override values should be applied
        assert config.queue.maxsize == 2000
        assert config.queue.batch_size == 20

        # Other queue settings should use the override object's defaults
        # not the production preset defaults
        assert config.queue.enabled is True  # QueueSettings default
        assert config.queue.overflow == "drop"  # QueueSettings default

        # Non-queue settings should remain as production defaults
        assert config.level == "INFO"
        assert config.security.enable_auto_redact_pii is True

    def test_preset_methods_are_static(self):
        """Test that all preset methods are static and can be called without instance."""
        # Should be able to call methods without creating an instance
        config1 = ConfigurationFactory.development()
        config2 = ConfigurationFactory.production()
        config3 = ConfigurationFactory.testing()
        config4 = ConfigurationFactory.high_performance()
        config5 = ConfigurationFactory.monitoring()

        assert all(
            isinstance(c, LoggingSettings)
            for c in [config1, config2, config3, config4, config5]
        )

        # Test that multiple calls return equivalent configurations
        config_a = ConfigurationFactory.development()
        config_b = ConfigurationFactory.development()

        assert config_a.level == config_b.level
        assert config_a.queue.maxsize == config_b.queue.maxsize
        assert config_a.sinks.json_console == config_b.sinks.json_console

    def test_edge_case_empty_overrides(self):
        """Test presets work correctly with empty override dictionaries."""
        configs = [
            ConfigurationFactory.development(**{}),
            ConfigurationFactory.production(**{}),
            ConfigurationFactory.testing(**{}),
            ConfigurationFactory.high_performance(**{}),
            ConfigurationFactory.monitoring(**{}),
        ]

        # Should be equivalent to calling without overrides
        default_configs = [
            ConfigurationFactory.development(),
            ConfigurationFactory.production(),
            ConfigurationFactory.testing(),
            ConfigurationFactory.high_performance(),
            ConfigurationFactory.monitoring(),
        ]

        for config, default_config in zip(configs, default_configs):
            assert config.level == default_config.level
            assert config.queue.maxsize == default_config.queue.maxsize
            assert config.sinks.json_console == default_config.sinks.json_console

    def test_complex_nested_overrides(self):
        """Test complex nested overrides work correctly."""
        config = ConfigurationFactory.production(
            level="DEBUG",
            enable_resource_metrics=False,
            sinks=SinkSettings(
                sinks=["stdout", "file:///var/log/app.log"],
                json_console="pretty",
                sampling_rate=0.5,
            ),
            queue=QueueSettings(
                enabled=True,
                maxsize=5000,
                batch_size=50,
                batch_timeout=2.5,
                overflow="sample",
            ),
            security=SecuritySettings(
                enable_auto_redact_pii=False,
                redact_level="ERROR",
                enable_throttling=False,
                enable_deduplication=False,
            ),
            metrics=MetricsSettings(enabled=False, prometheus_enabled=False),
        )

        # Verify all overrides were applied correctly
        assert config.level == "DEBUG"
        assert config.enable_resource_metrics is False

        assert config.sinks.sinks == ["stdout", "file:///var/log/app.log"]
        assert config.sinks.json_console == "pretty"
        assert config.sinks.sampling_rate == 0.5

        assert config.queue.enabled is True
        assert config.queue.maxsize == 5000
        assert config.queue.batch_size == 50
        assert config.queue.batch_timeout == 2.5
        assert config.queue.overflow == "sample"

        assert config.security.enable_auto_redact_pii is False
        assert config.security.redact_level == "ERROR"
        assert config.security.enable_throttling is False
        assert config.security.enable_deduplication is False

        assert config.metrics.enabled is False
        assert config.metrics.prometheus_enabled is False
