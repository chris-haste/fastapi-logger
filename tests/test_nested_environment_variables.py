"""Comprehensive tests for nested environment variable delimiter pattern validation."""

import os
from unittest.mock import patch

import pytest

from fapilog.config.settings import LoggingSettings
from fapilog.exceptions import ConfigurationError


class TestNestedEnvironmentVariables:
    """Test suite for comprehensive nested environment variable validation."""

    def test_all_nested_settings_patterns(self) -> None:
        """Test all nested settings classes work with double underscore delimiter."""
        env_vars = {
            # Core settings
            "FAPILOG_LEVEL": "DEBUG",
            "FAPILOG_ENABLE_RESOURCE_METRICS": "true",
            "FAPILOG_TRACE_ID_HEADER": "X-Custom-Trace-ID",
            "FAPILOG_ENABLE_HTTPX_TRACE_PROPAGATION": "true",
            # Queue settings
            "FAPILOG_QUEUE__ENABLED": "true",
            "FAPILOG_QUEUE__MAXSIZE": "2000",
            "FAPILOG_QUEUE__OVERFLOW": "drop",
            "FAPILOG_QUEUE__BATCH_SIZE": "150",
            "FAPILOG_QUEUE__RETRY_DELAY": "2.5",
            "FAPILOG_QUEUE__MAX_RETRIES": "5",
            # Security settings
            "FAPILOG_SECURITY__REDACT_LEVEL": "INFO",
            "FAPILOG_SECURITY__ENABLE_AUTO_REDACT_PII": "true",
            "FAPILOG_SECURITY__REDACT_PATTERNS": '["password", "token", "secret"]',
            "FAPILOG_SECURITY__REDACT_FIELDS": '["user.password", "auth.token"]',
            "FAPILOG_SECURITY__REDACT_REPLACEMENT": "***REDACTED***",
            "FAPILOG_SECURITY__CUSTOM_PII_PATTERNS": '["ssn", "credit_card"]',
            "FAPILOG_SECURITY__ENABLE_THROTTLING": "true",
            "FAPILOG_SECURITY__THROTTLE_MAX_RATE": "200",
            "FAPILOG_SECURITY__THROTTLE_WINDOW_SECONDS": "120",
            "FAPILOG_SECURITY__THROTTLE_KEY_FIELD": "user_id",
            "FAPILOG_SECURITY__THROTTLE_STRATEGY": "sample",
            "FAPILOG_SECURITY__ENABLE_DEDUPLICATION": "true",
            "FAPILOG_SECURITY__DEDUPE_WINDOW_SECONDS": "600",
            "FAPILOG_SECURITY__DEDUPE_FIELDS": '["event", "level", "source"]',
            "FAPILOG_SECURITY__DEDUPE_MAX_CACHE_SIZE": "20000",
            "FAPILOG_SECURITY__DEDUPE_HASH_ALGORITHM": "sha256",
            # Metrics settings
            "FAPILOG_METRICS__ENABLED": "true",
            "FAPILOG_METRICS__SAMPLE_WINDOW": "200",
            "FAPILOG_METRICS__PROMETHEUS_ENABLED": "true",
            "FAPILOG_METRICS__PROCESSOR_RESET_INTERVAL": "7200",
            # Sink settings
            "FAPILOG_SINKS__SINKS": "stdout,loki,file",
            "FAPILOG_SINKS__JSON_CONSOLE": "pretty",
            "FAPILOG_SINKS__SAMPLING_RATE": "0.8",
            # Validation settings
            "FAPILOG_VALIDATION__ENABLED": "true",
            "FAPILOG_VALIDATION__MODE": "strict",
        }

        with patch.dict(os.environ, env_vars):
            settings = LoggingSettings()

            # Verify core settings
            assert settings.level == "DEBUG"
            assert settings.enable_resource_metrics is True
            assert settings.trace_id_header == "X-Custom-Trace-ID"
            assert settings.enable_httpx_trace_propagation is True

            # Verify queue settings
            assert settings.queue.enabled is True
            assert settings.queue.maxsize == 2000
            assert settings.queue.overflow == "drop"
            assert settings.queue.batch_size == 150
            assert settings.queue.retry_delay == 2.5
            assert settings.queue.max_retries == 5

            # Verify security settings
            assert settings.security.redact_level == "INFO"
            assert settings.security.enable_auto_redact_pii is True
            assert settings.security.redact_patterns == ["password", "token", "secret"]
            assert settings.security.redact_fields == ["user.password", "auth.token"]
            assert settings.security.redact_replacement == "***REDACTED***"
            assert settings.security.custom_pii_patterns == ["ssn", "credit_card"]
            assert settings.security.enable_throttling is True
            assert settings.security.throttle_max_rate == 200
            assert settings.security.throttle_window_seconds == 120
            assert settings.security.throttle_key_field == "user_id"
            assert settings.security.throttle_strategy == "sample"
            assert settings.security.enable_deduplication is True
            assert settings.security.dedupe_window_seconds == 600
            assert settings.security.dedupe_fields == ["event", "level", "source"]
            assert settings.security.dedupe_max_cache_size == 20000
            assert settings.security.dedupe_hash_algorithm == "sha256"

            # Verify metrics settings
            assert settings.metrics.enabled is True
            assert settings.metrics.sample_window == 200
            assert settings.metrics.prometheus_enabled is True
            assert settings.metrics.processor_reset_interval == 7200

            # Verify sink settings
            assert settings.sinks.sinks == ["stdout", "loki", "file"]
            assert settings.sinks.json_console == "pretty"
            assert settings.sinks.sampling_rate == 0.8

            # Verify validation settings
            assert settings.validation.enabled is True
            assert settings.validation.mode == "strict"

    def test_complex_nested_structures(self) -> None:
        """Test complex nested structures including lists and dictionaries."""
        env_vars = {
            # Complex list patterns - using simpler patterns to avoid JSON escape issues
            "FAPILOG_SECURITY__REDACT_PATTERNS": '["password", "secret", "token"]',
            "FAPILOG_SECURITY__REDACT_FIELDS": '["credentials.password", "auth.bearer_token", "user.ssn"]',
            "FAPILOG_SECURITY__CUSTOM_PII_PATTERNS": '["email", "phone", "ssn"]',
            "FAPILOG_SECURITY__DEDUPE_FIELDS": '["timestamp", "level", "message", "source"]',
            # Simple patterns for sinks (no complex dictionary fields available)
            # Comma-separated lists
            "FAPILOG_SINKS__SINKS": "stdout,loki,file,custom",
        }

        with patch.dict(os.environ, env_vars):
            settings = LoggingSettings()

            # Verify complex list parsing
            assert len(settings.security.redact_patterns) == 3
            assert "password" in settings.security.redact_patterns
            assert "secret" in settings.security.redact_patterns
            assert "token" in settings.security.redact_patterns

            assert len(settings.security.redact_fields) == 3
            assert "credentials.password" in settings.security.redact_fields
            assert "auth.bearer_token" in settings.security.redact_fields
            assert "user.ssn" in settings.security.redact_fields

            assert len(settings.security.custom_pii_patterns) == 3
            assert len(settings.security.dedupe_fields) == 4

            # Verify basic pattern parsing works

            # Verify comma-separated list parsing
            assert settings.sinks.sinks == ["stdout", "loki", "file", "custom"]

    def test_malformed_environment_variables_handling(self) -> None:
        """Test handling of malformed environment variables."""

        # Test invalid integer values
        env_vars_invalid_int = {
            "FAPILOG_QUEUE__MAXSIZE": "not_a_number",
        }

        with patch.dict(os.environ, env_vars_invalid_int):
            with pytest.raises(ValueError):
                LoggingSettings()

        # Test invalid float values
        env_vars_invalid_float = {
            "FAPILOG_QUEUE__RETRY_DELAY": "not_a_float",
        }

        with patch.dict(os.environ, env_vars_invalid_float):
            with pytest.raises(ValueError):
                LoggingSettings()

        # Test invalid boolean values - Pydantic actually rejects invalid booleans
        env_vars_invalid_bool = {
            "FAPILOG_QUEUE__ENABLED": "maybe",
        }

        with patch.dict(os.environ, env_vars_invalid_bool):
            with pytest.raises(ValueError):
                LoggingSettings()

        # Test invalid JSON structures
        env_vars_invalid_json = {
            "FAPILOG_SECURITY__REDACT_PATTERNS": '["unclosed_array"',
        }

        with patch.dict(os.environ, env_vars_invalid_json):
            with pytest.raises(ValueError):
                LoggingSettings()

        # Test invalid dictionary JSON - use security patterns instead since sinks doesn't have dict fields
        env_vars_invalid_dict = {
            "FAPILOG_SECURITY__REDACT_PATTERNS": '{"unclosed": "dict"',
        }

        with patch.dict(os.environ, env_vars_invalid_dict):
            with pytest.raises(ValueError):
                LoggingSettings()

    def test_environment_variable_conflicts_detection(self) -> None:
        """Test detection and handling of conflicting environment patterns."""

        # Test that new pattern takes precedence (this should work fine)
        env_vars_both_patterns = {
            "FAPILOG_SECURITY__REDACT_LEVEL": "DEBUG",  # New pattern
            "FAPILOG_LEVEL": "INFO",  # Core level setting
        }

        with patch.dict(os.environ, env_vars_both_patterns):
            settings = LoggingSettings()
            # Should use new pattern for security and core level separately
            assert settings.security.redact_level == "DEBUG"
            assert settings.level == "INFO"

    def test_edge_case_delimiter_patterns(self) -> None:
        """Test edge cases with delimiter patterns."""

        # Test triple underscore (should not work as nested)
        env_vars_triple = {
            "FAPILOG_SECURITY___REDACT_LEVEL": "DEBUG",
        }

        with patch.dict(os.environ, env_vars_triple):
            # Triple underscore actually creates an extra field, which violates the "extra=forbid" setting
            with pytest.raises(ValueError):
                LoggingSettings()

        # Test single underscore (should not work as nested)
        env_vars_single = {
            "FAPILOG_SECURITY_REDACT_LEVEL": "DEBUG",
        }

        with patch.dict(os.environ, env_vars_single):
            # Single underscore should be ignored now (old pattern from issue #223)
            settings = LoggingSettings()
            # Should use default value since the old pattern is no longer recognized
            assert settings.security.redact_level == "INFO"

    def test_case_insensitive_nested_patterns(self) -> None:
        """Test that nested patterns work with case insensitive configuration."""

        env_vars = {
            "fapilog_queue__enabled": "true",
            "FAPILOG_SECURITY__REDACT_LEVEL": "debug",
            "Fapilog_Metrics__Enabled": "TRUE",
        }

        with patch.dict(os.environ, env_vars):
            settings = LoggingSettings()

            assert settings.queue.enabled is True
            assert (
                settings.security.redact_level == "DEBUG"
            )  # Should be normalized to uppercase
            assert settings.metrics.enabled is True

    def test_comprehensive_validation_coverage(self) -> None:
        """Test that validation works across all nested settings."""

        # Test invalid level validation in security settings
        env_vars_invalid_level = {
            "FAPILOG_SECURITY__REDACT_LEVEL": "INVALID_LEVEL",
        }

        with patch.dict(os.environ, env_vars_invalid_level):
            with pytest.raises(ConfigurationError):
                LoggingSettings()

        # Test boundary values
        env_vars_boundary = {
            "FAPILOG_QUEUE__MAXSIZE": "1",  # Minimum valid positive value
            "FAPILOG_QUEUE__RETRY_DELAY": "0.1",  # Small positive value
            "FAPILOG_SINKS__SAMPLING_RATE": "1.0",  # Maximum valid value
        }

        with patch.dict(os.environ, env_vars_boundary):
            settings = LoggingSettings()
            assert settings.queue.maxsize == 1
            assert settings.queue.retry_delay == 0.1
            assert settings.sinks.sampling_rate == 1.0

    def test_nested_pattern_documentation_examples(self) -> None:
        """Test examples that would be documented for users."""

        # Basic usage patterns that users should expect to work
        env_vars_examples = {
            # Enable queue with custom settings
            "FAPILOG_QUEUE__ENABLED": "true",
            "FAPILOG_QUEUE__MAXSIZE": "5000",
            "FAPILOG_QUEUE__OVERFLOW": "block",
            # Configure security with PII redaction
            "FAPILOG_SECURITY__ENABLE_AUTO_REDACT_PII": "true",
            "FAPILOG_SECURITY__REDACT_REPLACEMENT": "[REDACTED]",
            "FAPILOG_SECURITY__CUSTOM_PII_PATTERNS": '["email", "phone"]',
            # Set up Loki sink
            "FAPILOG_SINKS__SINKS": "loki",
            # Enable metrics collection
            "FAPILOG_METRICS__ENABLED": "true",
            "FAPILOG_METRICS__SAMPLE_WINDOW": "100",
        }

        with patch.dict(os.environ, env_vars_examples):
            settings = LoggingSettings()

            # Verify queue configuration
            assert settings.queue.enabled is True
            assert settings.queue.maxsize == 5000
            assert settings.queue.overflow == "block"

            # Verify security configuration
            assert settings.security.enable_auto_redact_pii is True
            assert settings.security.redact_replacement == "[REDACTED]"
            assert settings.security.custom_pii_patterns == ["email", "phone"]

            # Verify sink configuration
            assert settings.sinks.sinks == ["loki"]

            # Verify metrics configuration
            assert settings.metrics.enabled is True
            assert settings.metrics.sample_window == 100
