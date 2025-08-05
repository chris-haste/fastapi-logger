"""Tests for load test configuration settings."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from fapilog.config.load_test_settings import LoadTestSettings


class TestLoadTestSettings:
    """Test suite for LoadTestSettings configuration."""

    def test_default_values(self):
        """Test default configuration values."""
        with patch.dict(os.environ, {}, clear=True):
            settings = LoadTestSettings()

            assert settings.concurrency == 10
            assert settings.rate == 100.0
            assert settings.duration == 30.0
            assert settings.queue_size == 1000
            assert settings.overflow == "drop"
            assert settings.batch_size == 10
            assert settings.batch_timeout == 1.0

    def test_environment_variable_loading(self):
        """Test loading configuration from environment variables."""
        env_vars = {
            "LOAD_TEST_CONCURRENCY": "20",
            "LOAD_TEST_RATE": "500.0",
            "LOAD_TEST_DURATION": "60.0",
            "LOAD_TEST_QUEUE_SIZE": "2000",
            "LOAD_TEST_OVERFLOW": "block",
            "LOAD_TEST_BATCH_SIZE": "25",
            "LOAD_TEST_BATCH_TIMEOUT": "2.5",
        }

        with patch.dict(os.environ, env_vars):
            settings = LoadTestSettings()

            assert settings.concurrency == 20
            assert settings.rate == 500.0
            assert settings.duration == 60.0
            assert settings.queue_size == 2000
            assert settings.overflow == "block"
            assert settings.batch_size == 25
            assert settings.batch_timeout == 2.5

    def test_case_insensitive_environment_variables(self):
        """Test case insensitive environment variable handling."""
        env_vars = {
            "load_test_concurrency": "15",  # lowercase
            "Load_Test_Rate": "250.0",  # mixed case
            "LOAD_TEST_OVERFLOW": "sample",  # uppercase
        }

        with patch.dict(os.environ, env_vars):
            settings = LoadTestSettings()

            assert settings.concurrency == 15
            assert settings.rate == 250.0
            assert settings.overflow == "sample"

    def test_concurrency_validation_positive(self):
        """Test concurrency validation for positive values."""
        with patch.dict(os.environ, {"LOAD_TEST_CONCURRENCY": "0"}):
            with pytest.raises(ValidationError) as exc_info:
                LoadTestSettings()

            assert "Input should be greater than" in str(exc_info.value)

    def test_concurrency_validation_maximum(self):
        """Test concurrency validation for maximum value."""
        with patch.dict(os.environ, {"LOAD_TEST_CONCURRENCY": "1001"}):
            with pytest.raises(ValidationError) as exc_info:
                LoadTestSettings()

            assert "Input should be less than or equal to 1000" in str(exc_info.value)

    def test_rate_validation_positive(self):
        """Test rate validation for positive values."""
        with patch.dict(os.environ, {"LOAD_TEST_RATE": "0"}):
            with pytest.raises(ValidationError) as exc_info:
                LoadTestSettings()

            assert "Input should be greater than 0" in str(exc_info.value)

    def test_rate_validation_maximum(self):
        """Test rate validation for maximum value."""
        with patch.dict(os.environ, {"LOAD_TEST_RATE": "10001"}):
            with pytest.raises(ValidationError) as exc_info:
                LoadTestSettings()

            assert "Input should be less than or equal to 10000" in str(exc_info.value)

    def test_duration_validation_positive(self):
        """Test duration validation for positive values."""
        with patch.dict(os.environ, {"LOAD_TEST_DURATION": "0"}):
            with pytest.raises(ValidationError) as exc_info:
                LoadTestSettings()

            assert "Input should be greater than 0" in str(exc_info.value)

    def test_duration_validation_maximum(self):
        """Test duration validation for maximum value."""
        with patch.dict(os.environ, {"LOAD_TEST_DURATION": "3601"}):
            with pytest.raises(ValidationError) as exc_info:
                LoadTestSettings()

            assert "Input should be less than or equal to 3600" in str(exc_info.value)

    def test_queue_size_validation_positive(self):
        """Test queue size validation for positive values."""
        with patch.dict(os.environ, {"LOAD_TEST_QUEUE_SIZE": "0"}):
            with pytest.raises(ValidationError) as exc_info:
                LoadTestSettings()

            assert "Input should be greater than or equal to 1" in str(exc_info.value)

    def test_queue_size_validation_maximum(self):
        """Test queue size validation for maximum value."""
        with patch.dict(os.environ, {"LOAD_TEST_QUEUE_SIZE": "100001"}):
            with pytest.raises(ValidationError) as exc_info:
                LoadTestSettings()

            assert "Input should be less than or equal to 100000" in str(exc_info.value)

    def test_overflow_validation_valid_values(self):
        """Test overflow validation for valid values."""
        valid_values = ["drop", "block", "sample"]

        for value in valid_values:
            with patch.dict(os.environ, {"LOAD_TEST_OVERFLOW": value}):
                settings = LoadTestSettings()
                assert settings.overflow == value

    def test_overflow_validation_invalid_value(self):
        """Test overflow validation for invalid values."""
        with patch.dict(os.environ, {"LOAD_TEST_OVERFLOW": "invalid"}):
            with pytest.raises(ValueError):  # Pydantic validation error
                LoadTestSettings()

    def test_batch_size_validation_positive(self):
        """Test batch size validation for positive values."""
        with patch.dict(os.environ, {"LOAD_TEST_BATCH_SIZE": "0"}):
            with pytest.raises(ValidationError) as exc_info:
                LoadTestSettings()

            assert "Input should be greater than or equal to 1" in str(exc_info.value)

    def test_batch_size_validation_maximum(self):
        """Test batch size validation for maximum value."""
        with patch.dict(os.environ, {"LOAD_TEST_BATCH_SIZE": "1001"}):
            with pytest.raises(ValidationError) as exc_info:
                LoadTestSettings()

            assert "Input should be less than or equal to 1000" in str(exc_info.value)

    def test_batch_timeout_validation_positive(self):
        """Test batch timeout validation for positive values."""
        with patch.dict(os.environ, {"LOAD_TEST_BATCH_TIMEOUT": "0"}):
            with pytest.raises(ValidationError) as exc_info:
                LoadTestSettings()

            assert "Input should be greater than 0" in str(exc_info.value)

    def test_batch_timeout_validation_maximum(self):
        """Test batch timeout validation for maximum value."""
        with patch.dict(os.environ, {"LOAD_TEST_BATCH_TIMEOUT": "61"}):
            with pytest.raises(ValidationError) as exc_info:
                LoadTestSettings()

            assert "Input should be less than or equal to 60" in str(exc_info.value)

    def test_pydantic_field_validation(self):
        """Test Pydantic field validation constraints."""
        # Test field minimum constraints using direct instantiation
        with pytest.raises(ValueError):
            LoadTestSettings(concurrency=0)

        with pytest.raises(ValueError):
            LoadTestSettings(rate=0.0)

        with pytest.raises(ValueError):
            LoadTestSettings(duration=0.0)

        with pytest.raises(ValueError):
            LoadTestSettings(queue_size=0)

        with pytest.raises(ValueError):
            LoadTestSettings(batch_size=0)

        with pytest.raises(ValueError):
            LoadTestSettings(batch_timeout=0.0)

    def test_valid_boundary_values(self):
        """Test valid boundary values for all fields."""
        # Test minimum valid values
        settings = LoadTestSettings(
            concurrency=1,
            rate=0.1,
            duration=0.1,
            queue_size=1,
            batch_size=1,
            batch_timeout=0.1,
        )

        assert settings.concurrency == 1
        assert settings.rate == 0.1
        assert settings.duration == 0.1
        assert settings.queue_size == 1
        assert settings.batch_size == 1
        assert settings.batch_timeout == 0.1

    def test_maximum_valid_values(self):
        """Test maximum valid values for all fields."""
        settings = LoadTestSettings(
            concurrency=1000,
            rate=10000.0,
            duration=3600.0,
            queue_size=100000,
            batch_size=1000,
            batch_timeout=60.0,
        )

        assert settings.concurrency == 1000
        assert settings.rate == 10000.0
        assert settings.duration == 3600.0
        assert settings.queue_size == 100000
        assert settings.batch_size == 1000
        assert settings.batch_timeout == 60.0

    def test_env_prefix_configuration(self):
        """Test that environment prefix is correctly configured."""
        # Verify that only LOAD_TEST_ prefixed variables are used
        env_vars = {
            "CONCURRENCY": "999",  # Should not be used
            "LOAD_TEST_CONCURRENCY": "50",  # Should be used
        }

        with patch.dict(os.environ, env_vars):
            settings = LoadTestSettings()
            # Should use the prefixed variable, not the unprefixed one
            assert settings.concurrency == 50

    def test_extra_fields_forbidden(self):
        """Test that extra fields are forbidden."""
        # Test that extra fields are rejected by Pydantic
        with pytest.raises(ValueError):
            # Use dict unpacking to simulate extra field
            LoadTestSettings(**{"extra_field": "not_allowed"})

    def test_field_descriptions_present(self):
        """Test that field descriptions are present for documentation."""
        schema = LoadTestSettings.model_json_schema()
        properties = schema.get("properties", {})

        # Check that all fields have descriptions
        expected_fields = [
            "concurrency",
            "rate",
            "duration",
            "queue_size",
            "overflow",
            "batch_size",
            "batch_timeout",
        ]

        for field in expected_fields:
            assert field in properties
            assert "description" in properties[field]
            assert properties[field]["description"]  # Non-empty description
