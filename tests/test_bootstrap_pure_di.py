"""Tests for stateless bootstrap functionality."""

import logging
from unittest.mock import Mock

import pytest
import structlog

from fapilog._internal.configuration_manager import ConfigurationManager
from fapilog.bootstrap import (
    configure_logging,
    configure_with_container,
    create_logger,
)
from fapilog.container import LoggingContainer
from fapilog.exceptions import ConfigurationError
from fapilog.settings import LoggingSettings


class TestStatelessBootstrap:
    """Test stateless bootstrap functionality without global state."""

    def setup_method(self) -> None:
        """Clean up before each test."""
        # Reset structlog configuration for test isolation
        structlog.reset_defaults()
        structlog.configure()
        # Clear root logger handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    def teardown_method(self) -> None:
        """Clean up after each test."""
        # Reset structlog configuration
        structlog.reset_defaults()
        structlog.configure()
        # Clear root logger handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    def test_configure_logging_creates_functional_loggers(self) -> None:
        """Test that configure_logging creates functional logger instances."""
        # Multiple calls should work independently
        logger1 = configure_logging()
        logger2 = configure_logging()

        # Both loggers should be functional
        assert callable(logger1.info)
        assert callable(logger2.info)

        # No exceptions when logging
        logger1.info("Test message 1")
        logger2.info("Test message 2")

    def test_create_logger_returns_logger_and_container(self) -> None:
        """Test that create_logger returns both logger and container."""
        logger, container = create_logger()

        # Should return both components
        assert logger is not None
        assert container is not None
        assert isinstance(container, LoggingContainer)
        assert callable(logger.info)

        # Container should have lifecycle methods
        assert hasattr(container, "shutdown_sync")
        assert hasattr(container, "reset")

    def test_configure_with_container_alias(self) -> None:
        """Test that configure_with_container is an alias for create_logger."""
        logger1, container1 = configure_with_container()
        logger2, container2 = create_logger()

        # Both should return the same types
        assert type(logger1) is type(logger2)
        assert type(container1) is type(container2)

        # Both should be functional
        logger1.info("Test with configure_with_container")
        logger2.info("Test with create_logger")

    def test_configure_logging_with_settings(self) -> None:
        """Test configure_logging with custom settings."""
        settings = LoggingSettings(level="DEBUG", json_console="json")

        logger = configure_logging(settings=settings)
        assert callable(logger.info)
        logger.debug("Debug message")

    def test_create_logger_with_settings(self) -> None:
        """Test create_logger with custom settings."""
        settings = LoggingSettings(level="WARNING", json_console="pretty")

        logger, container = create_logger(settings=settings)
        assert callable(logger.warning)
        logger.warning("Warning message")

        # Cleanup
        container.shutdown_sync()

    def test_configure_logging_with_sinks_override(self) -> None:
        """Test configure_logging with sinks parameter override."""
        logger = configure_logging(sinks=["stdout"])
        assert callable(logger.info)
        logger.info("Message to stdout sink")

    def test_create_logger_explicit_lifecycle_management(self) -> None:
        """Test explicit container lifecycle management with create_logger."""
        logger, container = create_logger()

        try:
            # Use the logger
            logger.info("Application started")
            assert callable(logger.error)
        finally:
            # Explicit cleanup
            container.shutdown_sync()

        # Container should handle multiple shutdowns gracefully
        container.shutdown_sync()  # Should not raise

    def test_no_global_state_isolation(self) -> None:
        """Test that there's no shared global state between calls."""
        # Create multiple loggers with different settings
        settings1 = LoggingSettings(level="DEBUG")
        settings2 = LoggingSettings(level="ERROR")

        logger1 = configure_logging(settings=settings1)
        logger2 = configure_logging(settings=settings2)

        # Both should work independently
        logger1.debug("Debug message")
        logger2.error("Error message")

        # No shared state should interfere
        logger1.info("Info message")
        logger2.critical("Critical message")

    def test_configure_logging_backward_compatibility(self) -> None:
        """Test that configure_logging maintains backward compatibility."""
        # Test with no arguments (default behavior)
        logger = configure_logging()
        assert callable(logger.info)

        # Test with settings
        settings = LoggingSettings(level="DEBUG")
        settings.queue.enabled = False
        logger2 = configure_logging(settings=settings)
        assert callable(logger2.info)

        # Test with sinks override
        logger3 = configure_logging(sinks=["stdout"])
        assert callable(logger3.info)

    def test_configure_logging_with_settings_override(self) -> None:
        """Test configure_logging with settings parameter."""
        settings = LoggingSettings(level="WARNING", sinks=["stdout"])
        settings.queue.enabled = False

        logger = configure_logging(settings=settings)
        assert callable(logger.warning)
        logger.warning("Test warning message")
        assert callable(logger.info)

    def test_determine_console_format_utility(self) -> None:
        """Test ConfigurationManager.determine_console_format utility function."""
        # Test valid formats
        assert ConfigurationManager.determine_console_format("pretty") == "pretty"
        assert ConfigurationManager.determine_console_format("json") == "json"

        # Test auto format (depends on TTY)
        result = ConfigurationManager.determine_console_format("auto")
        assert result in ["pretty", "json"]

        # Test invalid format
        with pytest.raises(ConfigurationError):
            ConfigurationManager.determine_console_format("invalid")

    def test_fastapi_app_integration(self) -> None:
        """Test FastAPI app integration through configure_logging."""
        # Mock FastAPI app
        mock_app = Mock()
        mock_app.add_middleware = Mock()
        mock_app.add_event_handler = Mock()

        # Configure with app
        logger = configure_logging(app=mock_app)

        # Should have registered middleware
        mock_app.add_middleware.assert_called_once()

        # Logger should be functional
        assert callable(logger.info)
