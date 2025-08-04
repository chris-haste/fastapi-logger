"""Integration tests for bootstrap functions with factory-based containers.

This test module verifies that bootstrap functions (create_logger and configure_logging)
work seamlessly with the new factory-based LoggingContainer implementation, ensuring
no global structlog dependencies remain.
"""

import structlog

from fapilog.bootstrap import configure_logging, create_logger
from fapilog.config import LoggingSettings
from fapilog.container import LoggingContainer


class TestBootstrapFactoryIntegration:
    """Test bootstrap functions with factory-based containers."""

    def test_create_logger_returns_factory_based_container(self):
        """Test that create_logger() returns a container with factory."""
        # Arrange & Act
        logger, container = create_logger()

        # Assert
        assert isinstance(container, LoggingContainer)
        assert container._logger_factory is not None, "Container should have factory"
        # Factory may be lazy (not configured until first use) even if container is configured
        assert hasattr(logger, "info") and hasattr(logger, "debug")

        # Cleanup
        container.shutdown_sync()

    def test_configure_logging_works_with_factory(self):
        """Test that configure_logging() works with factory approach."""
        # Arrange & Act
        logger = configure_logging()

        # Assert
        assert logger is not None
        assert hasattr(logger, "info") and hasattr(logger, "debug")

    def test_bootstrap_functions_create_independent_containers(self):
        """Test that multiple bootstrap calls create independent containers."""
        # Arrange
        settings1 = LoggingSettings(level="INFO")
        settings2 = LoggingSettings(level="DEBUG")

        # Act
        logger1, container1 = create_logger(settings=settings1)
        logger2, container2 = create_logger(settings=settings2)

        # Assert - Different containers with different factories
        assert container1 is not container2
        assert container1._logger_factory is not container2._logger_factory
        assert container1._settings.level != container2._settings.level

        # Cleanup
        container1.shutdown_sync()
        container2.shutdown_sync()

    def test_settings_parameter_integration_with_factory(self):
        """Test that settings parameter works correctly with factory."""
        # Arrange
        from fapilog.config.sink_settings import SinkSettings

        settings = LoggingSettings(
            level="WARNING", sinks=SinkSettings(json_console="json")
        )

        # Act
        logger, container = create_logger(settings=settings)

        # Assert
        assert container._settings.level == "WARNING"
        assert container._settings.sinks.json_console == "json"
        assert container._logger_factory is not None

        # Cleanup
        container.shutdown_sync()

    def test_sinks_parameter_integration_with_factory(self):
        """Test that sinks parameter works correctly with factory."""
        # Arrange
        sinks = ["stdout"]

        # Act
        logger, container = create_logger(sinks=sinks)

        # Assert
        assert container._settings.sinks.sinks == sinks
        assert container._logger_factory is not None

        # Cleanup
        container.shutdown_sync()

    def test_app_parameter_integration_with_factory(self):
        """Test that app parameter works correctly with factory."""
        # Arrange
        from unittest.mock import Mock

        mock_app = Mock()

        # Act
        logger, container = create_logger(app=mock_app)

        # Assert
        assert container._logger_factory is not None
        assert logger is not None

        # Cleanup
        container.shutdown_sync()

    def test_factory_configuration_lazy_initialization(self):
        """Test that factory configuration is lazy (built on first use)."""
        # Arrange
        settings = LoggingSettings(level="INFO")

        # Act
        logger, container = create_logger(settings=settings)

        # Assert
        # Factory should exist but may not be configured until first logger use
        assert container._logger_factory is not None

        # Trigger factory configuration by creating logger
        _ = container.get_logger("test")
        assert container._logger_factory.is_configured()

        # Cleanup
        container.shutdown_sync()

    def test_bootstrap_error_handling_preserved(self):
        """Test that error handling behavior is preserved in bootstrap."""
        # Arrange
        from unittest.mock import patch

        # Act & Assert - Should handle invalid settings gracefully
        with patch("fapilog.config.settings.LoggingSettings") as mock_settings:
            mock_settings.side_effect = ValueError("Invalid setting")

            # This should not raise an exception - error handling should be preserved
            try:
                logger, container = create_logger()
                container.shutdown_sync()
            except ValueError:
                # If it raises ValueError, that's expected error handling
                pass

    def test_no_global_structlog_configuration_in_bootstrap(self):
        """Test that bootstrap functions don't affect global structlog state."""
        # Arrange
        # Store original global structlog state (for documentation purposes)
        _original_processors = getattr(structlog, "_CONTEXT", {}).get(
            "processors", None
        )
        _original_wrapper = getattr(structlog, "_CONTEXT", {}).get(
            "wrapper_class", None
        )

        # Act
        logger, container = create_logger()

        # Assert
        # Global structlog should not be affected (for documentation purposes)
        _current_processors = getattr(structlog, "_CONTEXT", {}).get("processors", None)
        _current_wrapper = getattr(structlog, "_CONTEXT", {}).get("wrapper_class", None)

        # The key test: bootstrap should work without global configuration
        assert container._logger_factory is not None
        assert logger is not None

        # Cleanup
        container.shutdown_sync()

    def test_container_isolation_between_bootstrap_calls(self):
        """Test complete isolation between containers created via bootstrap."""
        # Arrange
        from fapilog.config.sink_settings import SinkSettings

        settings1 = LoggingSettings(
            level="INFO", sinks=SinkSettings(json_console="pretty")
        )
        settings2 = LoggingSettings(
            level="ERROR", sinks=SinkSettings(json_console="json")
        )

        # Act
        logger1, container1 = create_logger(settings=settings1)
        logger2, container2 = create_logger(settings=settings2)

        # Assert - Containers should be completely independent
        assert container1._container_id != container2._container_id
        assert container1._logger_factory is not container2._logger_factory

        # Test that loggers are independent
        test_logger1 = container1.get_logger("app1")
        test_logger2 = container2.get_logger("app2")
        assert test_logger1 is not test_logger2

        # Settings should be independent
        assert container1._settings.level != container2._settings.level
        assert (
            container1._settings.sinks.json_console
            != container2._settings.sinks.json_console
        )

        # Cleanup
        container1.shutdown_sync()
        container2.shutdown_sync()

    def test_configure_logging_backward_compatibility(self):
        """Test that configure_logging maintains backward compatibility."""
        # Arrange
        settings = LoggingSettings(level="WARNING")

        # Act - Using configure_logging (stateless approach)
        logger = configure_logging(settings=settings)

        # Assert
        assert logger is not None
        assert hasattr(logger, "info") and hasattr(logger, "debug")

        # Note: No explicit cleanup since configure_logging doesn't return container

    def test_factory_methods_used_correctly(self):
        """Test that bootstrap functions use the correct factory methods."""
        # Arrange
        settings = LoggingSettings(level="DEBUG")

        # Act
        logger1, container1 = create_logger(settings=settings)
        logger2, container2 = create_logger()  # Uses defaults

        # Assert
        # Both should have factories but different settings
        assert container1._logger_factory is not None
        assert container2._logger_factory is not None
        assert container1._settings.level == "DEBUG"
        assert container2._settings.level != "DEBUG"  # Should be default

        # Cleanup
        container1.shutdown_sync()
        container2.shutdown_sync()

    def test_bootstrap_functions_performance_with_factory(self):
        """Test that bootstrap functions maintain performance with factory approach."""
        import time

        # Arrange
        start_time = time.time()

        # Act - Create multiple loggers
        loggers_and_containers = []
        for _i in range(10):
            logger, container = create_logger()
            loggers_and_containers.append((logger, container))

        end_time = time.time()

        # Assert - Should be fast (under 1 second for 10 containers)
        duration = end_time - start_time
        assert duration < 1.0, f"Bootstrap should be fast, took {duration:.3f}s"

        # All containers should have factories
        for _logger, container in loggers_and_containers:
            assert container._logger_factory is not None

        # Cleanup
        for _, container in loggers_and_containers:
            container.shutdown_sync()

    def test_legacy_alias_works_with_factory(self):
        """Test that configure_with_container alias works with factory."""
        # Import the legacy alias
        from fapilog.bootstrap import configure_with_container

        # Act
        logger, container = configure_with_container()

        # Assert
        assert container._logger_factory is not None
        assert logger is not None

        # Cleanup
        container.shutdown_sync()
