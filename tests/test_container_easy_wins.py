"""Easy win tests for container.py to reach 90% coverage."""

from unittest.mock import patch

import pytest

from fapilog.container import LoggingContainer
from fapilog.exceptions import ConfigurationError, SinkError
from fapilog.settings import LoggingSettings


class TestContainerEasyWins:
    """Test easy win scenarios in container.py."""

    def test_invalid_console_format_error(self):
        """Test invalid console format validation (line 157)."""
        container = LoggingContainer()

        # Try to use an invalid console format
        with pytest.raises(ConfigurationError) as exc_info:
            container._determine_console_format("invalid_format")

        assert "Invalid console_format" in str(exc_info.value)

    def test_loki_sink_import_error_handling(self):
        """Test ImportError handling for loki sink creation (line 223)."""
        settings = LoggingSettings(sinks=["loki://localhost:3100/loki/api/v1/push"])
        container = LoggingContainer(settings)

        # Mock create_loki_sink_from_uri to raise ImportError
        with patch(
            "fapilog.container.create_loki_sink_from_uri",
            side_effect=ImportError("Loki not available"),
        ):
            with pytest.raises(SinkError):
                container.configure()

    def test_console_format_pretty_branch(self):
        """Test console format pretty branch (around line 206)."""
        container = LoggingContainer()

        # Test pretty format specifically
        result = container._determine_console_format("pretty")
        assert result == "pretty"

    def test_console_format_json_branch(self):
        """Test console format json branch (around line 206)."""
        container = LoggingContainer()

        # Test json format specifically
        result = container._determine_console_format("json")
        assert result == "json"

    def test_queue_worker_creation_exception_handling(self):
        """Test exception handling in queue worker creation (lines 251-261)."""
        settings = LoggingSettings()
        container = LoggingContainer(settings)

        # Mock QueueWorker to raise an exception during creation
        with patch(
            "fapilog.container.QueueWorker",
            side_effect=Exception("Queue creation error"),
        ):
            with pytest.raises(ConfigurationError) as exc_info:
                container._setup_queue_worker("pretty")

            assert "queue_worker" in str(exc_info.value)

    def test_settings_validation_exception_handling(self):
        """Test exception handling in settings validation (line 141)."""
        # Mock LoggingSettings.model_validate to raise an exception
        with patch(
            "fapilog.settings.LoggingSettings.model_validate",
            side_effect=ValueError("Validation failed"),
        ):
            container = LoggingContainer()

            # Create a mock settings object
            mock_settings = LoggingSettings()

            with pytest.raises(ConfigurationError):
                container._validate_and_get_settings(mock_settings)

    def test_log_level_attribute_error_handling(self):
        """Test AttributeError handling in logging setup (lines 189-190)."""
        container = LoggingContainer()

        # Mock logging to raise AttributeError
        with patch("fapilog.container.logging.getLogger") as mock_get_logger:
            mock_logger = mock_get_logger.return_value
            mock_logger.setLevel.side_effect = AttributeError("Invalid level")

            with pytest.raises(ConfigurationError) as exc_info:
                container._configure_standard_logging("INVALID_LEVEL")

            assert "log_level" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__])
