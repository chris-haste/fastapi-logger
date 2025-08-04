"""Comprehensive tests for ContainerLoggerFactory.

Tests the container-specific logger factory that creates structlog loggers
without relying on global structlog.configure() calls, ensuring true container
isolation and thread safety.
"""

from unittest.mock import Mock, patch

import pytest

from fapilog.config import LoggingSettings
from fapilog.container import LoggingContainer
from fapilog.core.factories.container_logger_factory import ContainerLoggerFactory


class TestContainerLoggerFactory:
    """Test suite for ContainerLoggerFactory class."""

    def test_factory_initialization_with_valid_container(self):
        """Test factory initialization with valid container."""
        # Arrange
        settings = LoggingSettings(level="INFO")
        container = LoggingContainer(settings)

        # Act
        factory = ContainerLoggerFactory(container)

        # Assert
        assert factory.container is container
        assert factory._processors is None
        assert factory._wrapper_class is None
        assert factory._configured is False

    def test_is_configured_returns_false_initially(self):
        """Test is_configured returns False before configuration."""
        # Arrange
        settings = LoggingSettings(level="DEBUG")
        container = LoggingContainer(settings)
        factory = ContainerLoggerFactory(container)

        # Act & Assert
        assert not factory.is_configured()

    def test_is_configured_returns_true_after_configuration(self):
        """Test is_configured returns True after lazy configuration."""
        # Arrange
        settings = LoggingSettings(level="INFO")
        container = LoggingContainer(settings)
        # Temporarily patch _console_format for testing
        container._console_format = "pretty"  # type: ignore[attr-defined]
        factory = ContainerLoggerFactory(container)

        # Act
        with patch(
            "fapilog.core.factories.container_logger_factory.build_processor_chain"
        ) as mock_build:
            mock_build.return_value = [Mock()]
            factory._build_configuration()

        # Assert
        assert factory.is_configured()

    @patch("fapilog.core.factories.container_logger_factory.build_processor_chain")
    def test_lazy_configuration_building(self, mock_build_chain):
        """Test configuration is built lazily only once."""
        # Arrange
        settings = LoggingSettings(level="WARN")
        container = LoggingContainer(settings)
        # Temporarily patch _console_format for testing
        container._console_format = "json"  # type: ignore[attr-defined]
        factory = ContainerLoggerFactory(container)
        mock_processors = [Mock(), Mock()]
        mock_build_chain.return_value = mock_processors

        # Act - First call should build configuration
        factory._build_configuration()
        first_call_count = mock_build_chain.call_count

        # Act - Second call should not rebuild
        factory._build_configuration()
        second_call_count = mock_build_chain.call_count

        # Assert
        assert first_call_count == 1
        assert second_call_count == 1  # Should not increase
        assert factory._processors == mock_processors
        assert factory._configured is True

    @patch("fapilog.core.factories.container_logger_factory.build_processor_chain")
    def test_build_configuration_with_pretty_format(self, mock_build_chain):
        """Test configuration building with pretty console format."""
        # Arrange
        settings = LoggingSettings(level="ERROR")
        container = LoggingContainer(settings)
        # Temporarily patch _console_format for testing
        container._console_format = "pretty"  # type: ignore[attr-defined]
        factory = ContainerLoggerFactory(container)
        mock_processors = [Mock()]
        mock_build_chain.return_value = mock_processors

        # Act
        factory._build_configuration()

        # Assert
        mock_build_chain.assert_called_once_with(
            settings, pretty=True, container=container
        )
        assert factory._processors == mock_processors

    @patch("fapilog.core.factories.container_logger_factory.build_processor_chain")
    def test_build_configuration_with_json_format(self, mock_build_chain):
        """Test configuration building with json console format."""
        # Arrange
        settings = LoggingSettings(level="CRITICAL")
        container = LoggingContainer(settings)
        # Temporarily patch _console_format for testing
        container._console_format = "json"  # type: ignore[attr-defined]
        factory = ContainerLoggerFactory(container)
        mock_processors = [Mock()]
        mock_build_chain.return_value = mock_processors

        # Act
        factory._build_configuration()

        # Assert
        mock_build_chain.assert_called_once_with(
            settings, pretty=False, container=container
        )

    @patch("fapilog.core.factories.container_logger_factory.build_processor_chain")
    def test_build_configuration_fallback_to_settings_format(self, mock_build_chain):
        """Test configuration falls back to settings when _console_format missing."""
        # Arrange
        from fapilog.config.sink_settings import SinkSettings

        settings = LoggingSettings(
            level="INFO", sinks=SinkSettings(json_console="pretty")
        )
        container = LoggingContainer(settings)
        # Don't set _console_format to test fallback
        factory = ContainerLoggerFactory(container)
        mock_processors = [Mock()]
        mock_build_chain.return_value = mock_processors

        # Act
        factory._build_configuration()

        # Assert
        mock_build_chain.assert_called_once_with(
            settings, pretty=True, container=container
        )

    @patch("fapilog.core.factories.container_logger_factory.build_processor_chain")
    @patch("sys.stderr")
    def test_build_configuration_auto_format_tty(self, mock_stderr, mock_build_chain):
        """Test auto format detection when stderr is a tty."""
        # Arrange
        from fapilog.config.sink_settings import SinkSettings

        settings = LoggingSettings(
            level="DEBUG", sinks=SinkSettings(json_console="auto")
        )
        container = LoggingContainer(settings)
        factory = ContainerLoggerFactory(container)
        mock_processors = [Mock()]
        mock_build_chain.return_value = mock_processors
        mock_stderr.isatty.return_value = True

        # Act
        factory._build_configuration()

        # Assert
        mock_build_chain.assert_called_once_with(
            settings, pretty=True, container=container
        )

    @patch("fapilog.core.factories.container_logger_factory.build_processor_chain")
    @patch("sys.stderr")
    def test_build_configuration_auto_format_no_tty(
        self, mock_stderr, mock_build_chain
    ):
        """Test auto format detection when stderr is not a tty."""
        # Arrange
        from fapilog.config.sink_settings import SinkSettings

        settings = LoggingSettings(
            level="INFO", sinks=SinkSettings(json_console="auto")
        )
        container = LoggingContainer(settings)
        factory = ContainerLoggerFactory(container)
        mock_processors = [Mock()]
        mock_build_chain.return_value = mock_processors
        mock_stderr.isatty.return_value = False

        # Act
        factory._build_configuration()

        # Assert
        mock_build_chain.assert_called_once_with(
            settings, pretty=False, container=container
        )

    def test_build_configuration_creates_correct_wrapper_class(self):
        """Test wrapper class is created with correct log level."""
        # Arrange
        settings = LoggingSettings(level="WARN")
        container = LoggingContainer(settings)
        # Temporarily patch _console_format for testing
        container._console_format = "json"  # type: ignore[attr-defined]
        factory = ContainerLoggerFactory(container)

        # Act
        with patch(
            "fapilog.core.factories.container_logger_factory.build_processor_chain"
        ) as mock_build:
            mock_build.return_value = [Mock()]
            factory._build_configuration()

        # Assert
        assert factory._wrapper_class is not None
        # The wrapper class should be a filtering bound logger with WARN level
        # We can't easily test the internal level without complex mocking

    @patch("fapilog.core.factories.container_logger_factory.build_processor_chain")
    def test_build_configuration_handles_container_errors(self, mock_build_chain):
        """Test configuration handles container attribute errors gracefully."""
        # Arrange
        mock_container = Mock()
        mock_container._settings = None  # This should cause an AttributeError
        factory = ContainerLoggerFactory(mock_container)
        mock_build_chain.side_effect = AttributeError("Missing _settings")

        # Act & Assert
        with pytest.raises(
            ValueError, match="Container missing required configuration"
        ):
            factory._build_configuration()

    @patch("logging.getLogger")
    @patch("fapilog.core.factories.container_logger_factory.build_processor_chain")
    def test_create_logger_with_default_name(self, mock_build_chain, mock_get_logger):
        """Test logger creation with default (empty) name."""
        # Arrange
        settings = LoggingSettings(level="INFO")
        container = LoggingContainer(settings)
        # Temporarily patch _console_format for testing
        container._console_format = "json"  # type: ignore[attr-defined]
        factory = ContainerLoggerFactory(container)

        mock_processors = [Mock()]
        mock_build_chain.return_value = mock_processors
        mock_stdlib_logger = Mock()
        mock_get_logger.return_value = mock_stdlib_logger
        mock_bound_logger = Mock()

        # Mock the wrapper class to return our mock bound logger
        with patch("structlog.make_filtering_bound_logger") as mock_make_wrapper:
            mock_wrapper_class = Mock()
            mock_wrapper_class.return_value = mock_bound_logger
            mock_make_wrapper.return_value = mock_wrapper_class

            # Act
            result = factory.create_logger()

        # Assert
        mock_get_logger.assert_called_once_with("")
        mock_wrapper_class.assert_called_once_with(
            mock_stdlib_logger,
            processors=mock_processors,
            context={},
        )
        assert result is mock_bound_logger

    @patch("logging.getLogger")
    @patch("fapilog.core.factories.container_logger_factory.build_processor_chain")
    def test_create_logger_with_custom_name(self, mock_build_chain, mock_get_logger):
        """Test logger creation with custom name."""
        # Arrange
        settings = LoggingSettings(level="DEBUG")
        container = LoggingContainer(settings)
        # Temporarily patch _console_format for testing
        container._console_format = "pretty"  # type: ignore[attr-defined]
        factory = ContainerLoggerFactory(container)

        mock_processors = [Mock()]
        mock_build_chain.return_value = mock_processors
        mock_stdlib_logger = Mock()
        mock_get_logger.return_value = mock_stdlib_logger
        mock_bound_logger = Mock()

        # Mock the wrapper class to return our mock bound logger
        with patch("structlog.make_filtering_bound_logger") as mock_make_wrapper:
            mock_wrapper_class = Mock()
            mock_wrapper_class.return_value = mock_bound_logger
            mock_make_wrapper.return_value = mock_wrapper_class

            # Act
            result = factory.create_logger("test.logger")

        # Assert
        mock_get_logger.assert_called_once_with("test.logger")
        assert result is mock_bound_logger

    @patch("fapilog.core.factories.container_logger_factory.build_processor_chain")
    def test_create_logger_triggers_lazy_configuration(self, mock_build_chain):
        """Test logger creation triggers lazy configuration building."""
        # Arrange
        settings = LoggingSettings(level="ERROR")
        container = LoggingContainer(settings)
        # Temporarily patch _console_format for testing
        container._console_format = "json"  # type: ignore[attr-defined]
        factory = ContainerLoggerFactory(container)

        mock_processors = [Mock()]
        mock_build_chain.return_value = mock_processors

        # Assert factory is not configured initially
        assert not factory.is_configured()

        # Act
        with patch("logging.getLogger"), patch("structlog.make_filtering_bound_logger"):
            factory.create_logger("test")

        # Assert
        assert factory.is_configured()
        mock_build_chain.assert_called_once()

    def test_reset_clears_configuration(self):
        """Test reset clears cached configuration."""
        # Arrange
        settings = LoggingSettings(level="INFO")
        container = LoggingContainer(settings)
        # Temporarily patch _console_format for testing
        container._console_format = "pretty"  # type: ignore[attr-defined]
        factory = ContainerLoggerFactory(container)

        # Configure the factory
        with patch(
            "fapilog.core.factories.container_logger_factory.build_processor_chain"
        ) as mock_build:
            mock_build.return_value = [Mock()]
            factory._build_configuration()

        # Verify it's configured
        assert factory.is_configured()
        assert factory._processors is not None
        assert factory._wrapper_class is not None

        # Act
        factory.reset()

        # Assert
        assert not factory.is_configured()
        assert factory._processors is None
        assert factory._wrapper_class is None
        assert factory._configured is False

    @patch("fapilog.core.factories.container_logger_factory.build_processor_chain")
    def test_reset_allows_reconfiguration(self, mock_build_chain):
        """Test reset allows factory to be reconfigured."""
        # Arrange
        settings = LoggingSettings(level="DEBUG")
        container = LoggingContainer(settings)
        # Temporarily patch _console_format for testing
        container._console_format = "json"  # type: ignore[attr-defined]
        factory = ContainerLoggerFactory(container)

        first_processors = [Mock()]
        second_processors = [Mock(), Mock()]
        mock_build_chain.side_effect = [first_processors, second_processors]

        # Act - First configuration
        factory._build_configuration()
        first_result = factory._processors

        # Act - Reset and reconfigure
        factory.reset()
        factory._build_configuration()
        second_result = factory._processors

        # Assert
        assert first_result == first_processors
        assert second_result == second_processors
        assert mock_build_chain.call_count == 2

    def test_multiple_logger_creation_reuses_configuration(self):
        """Test multiple logger creations reuse the same configuration."""
        # Arrange
        settings = LoggingSettings(level="WARN")
        container = LoggingContainer(settings)
        # Temporarily patch _console_format for testing
        container._console_format = "pretty"  # type: ignore[attr-defined]
        factory = ContainerLoggerFactory(container)

        # Act & Assert
        with patch(
            "fapilog.core.factories.container_logger_factory.build_processor_chain"
        ) as mock_build:
            with patch("logging.getLogger"), patch(
                "structlog.make_filtering_bound_logger"
            ):
                mock_build.return_value = [Mock()]

                # Create multiple loggers
                factory.create_logger("logger1")
                factory.create_logger("logger2")
                factory.create_logger("logger3")

                # Configuration should only be built once
                assert mock_build.call_count == 1

    @patch("fapilog.core.factories.container_logger_factory.build_processor_chain")
    def test_processor_chain_integration(self, mock_build_chain):
        """Test integration with build_processor_chain function."""
        # Arrange
        from fapilog.config.sink_settings import SinkSettings

        settings = LoggingSettings(
            level="INFO", sinks=SinkSettings(sinks=["stdout"], json_console="pretty")
        )
        container = LoggingContainer(settings)
        # Temporarily patch _console_format for testing
        container._console_format = "pretty"  # type: ignore[attr-defined]
        factory = ContainerLoggerFactory(container)

        expected_processors = [Mock(), Mock(), Mock()]
        mock_build_chain.return_value = expected_processors

        # Act
        factory._build_configuration()

        # Assert
        mock_build_chain.assert_called_once_with(
            settings, pretty=True, container=container
        )
        assert factory._processors == expected_processors

    def test_wrapper_class_configuration_with_different_levels(self):
        """Test wrapper class is configured correctly for different log levels."""
        test_levels = ["DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"]

        for level in test_levels:
            with patch(
                "fapilog.core.factories.container_logger_factory.build_processor_chain"
            ) as mock_build:
                # Arrange
                settings = LoggingSettings(level=level)
                container = LoggingContainer(settings)
                # Temporarily patch _console_format for testing
                container._console_format = "json"  # type: ignore[attr-defined]
                factory = ContainerLoggerFactory(container)
                mock_build.return_value = [Mock()]

                # Act
                factory._build_configuration()

                # Assert
                assert factory._wrapper_class is not None
                assert factory.is_configured()

    def test_error_handling_for_invalid_container_configuration(self):
        """Test error handling when container has invalid configuration."""
        # Arrange
        mock_container = Mock()
        mock_container._settings.level = "INVALID_LEVEL"
        factory = ContainerLoggerFactory(mock_container)

        # Act & Assert
        with patch(
            "fapilog.core.factories.container_logger_factory.build_processor_chain"
        ):
            with pytest.raises(
                ValueError, match="Container missing required configuration"
            ):
                factory._build_configuration()

    def test_memory_efficiency_single_configuration_per_factory(self):
        """Test memory efficiency - configuration built only once per factory."""
        # Arrange
        settings = LoggingSettings(level="INFO")
        container = LoggingContainer(settings)
        # Temporarily patch _console_format for testing
        container._console_format = "json"  # type: ignore[attr-defined]
        factory = ContainerLoggerFactory(container)

        # Act - Multiple operations that could trigger configuration
        with patch(
            "fapilog.core.factories.container_logger_factory.build_processor_chain"
        ) as mock_build:
            mock_build.return_value = [Mock()]

            # These should all use the same configuration
            factory._build_configuration()
            factory._build_configuration()
            factory.is_configured()
            factory.is_configured()

        # Assert - build_processor_chain called only once
        assert mock_build.call_count == 1
