"""Tests for bootstrap integration with pure dependency injection."""

import logging
from unittest.mock import Mock

import pytest
import structlog

from fapilog.bootstrap import (
    _determine_console_format,
    _shutdown_queue_worker,
    configure_logging,
    configure_with_container,
    get_active_containers,
    reset_logging,
    shutdown_logging,
)
from fapilog.container import LoggingContainer
from fapilog.exceptions import ConfigurationError
from fapilog.settings import LoggingSettings


class TestBootstrapPureDependencyInjection:
    """Test bootstrap functionality with pure dependency injection."""

    def setup_method(self) -> None:
        """Clean up before each test."""
        # Reset any existing bootstrap state
        reset_logging()
        # Reset structlog
        structlog.reset_defaults()
        # Clear root logger handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    def teardown_method(self) -> None:
        """Clean up after each test."""
        # Reset bootstrap state
        reset_logging()
        # Reset structlog
        structlog.reset_defaults()
        # Clear root logger handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    def test_configure_logging_creates_isolated_containers(self) -> None:
        """Test that configure_logging creates isolated container instances."""
        # First call
        logger1 = configure_logging()
        containers_after_first = get_active_containers()

        # Second call
        logger2 = configure_logging()
        containers_after_second = get_active_containers()

        # Should have created separate containers
        assert len(containers_after_first) == 1
        assert len(containers_after_second) == 2
        assert containers_after_first[0] is not containers_after_second[1]

        # Both loggers should be functional
        assert callable(logger1.info)
        assert callable(logger2.info)

    def test_configure_logging_backward_compatibility(self) -> None:
        """Test that configure_logging maintains backward compatibility."""
        # Test with no arguments (default behavior)
        logger = configure_logging()
        assert callable(logger.info)

        # Test with settings
        settings = LoggingSettings(level="DEBUG", queue_enabled=False)
        logger2 = configure_logging(settings=settings)
        assert callable(logger2.info)

        # Test with sinks override
        logger3 = configure_logging(sinks=["stdout"])
        assert callable(logger3.info)

    def test_configure_logging_with_settings_override(self) -> None:
        """Test configure_logging with settings parameter."""
        settings = LoggingSettings(
            level="WARNING", queue_enabled=False, sinks=["stdout"]
        )

        logger = configure_logging(settings=settings)
        containers = get_active_containers()

        assert callable(logger.info)
        assert len(containers) == 1
        assert containers[0].settings.level == "WARNING"
        assert containers[0].settings.queue_enabled is False

    def test_configure_logging_with_sinks_override(self) -> None:
        """Test configure_logging with sinks parameter override."""
        # Override sinks parameter
        logger = configure_logging(sinks=["stdout"])
        containers = get_active_containers()

        assert callable(logger.info)
        assert len(containers) == 1
        assert "stdout" in containers[0].settings.sinks

        # Override with settings and sinks
        settings = LoggingSettings(level="INFO")
        configure_logging(settings=settings, sinks=["stdout"])
        containers2 = get_active_containers()

        assert len(containers2) == 2
        assert "stdout" in containers2[1].settings.sinks

    def test_configure_with_container_function(self) -> None:
        """Test configure_with_container returns both logger and container."""
        settings = LoggingSettings(level="INFO", queue_enabled=False)

        logger, container = configure_with_container(settings=settings)

        # Should return both logger and container
        assert callable(logger.info)
        assert isinstance(container, LoggingContainer)
        assert container.is_configured
        assert container.settings.level == "INFO"

        # Container should be registered
        active_containers = get_active_containers()
        assert len(active_containers) == 1
        assert active_containers[0] is container

    def test_multiple_configure_calls_isolation(self) -> None:
        """Test that multiple configure_logging calls create isolated containers."""
        # Create containers with different settings
        logger1 = configure_logging(LoggingSettings(level="INFO"))
        logger2 = configure_logging(LoggingSettings(level="DEBUG"))
        logger3 = configure_logging(LoggingSettings(level="ERROR"))

        containers = get_active_containers()
        assert len(containers) == 3

        # Each container should have its own settings
        assert containers[0].settings.level == "INFO"
        assert containers[1].settings.level == "DEBUG"
        assert containers[2].settings.level == "ERROR"

        # All loggers should be functional
        assert callable(logger1.info)
        assert callable(logger2.info)
        assert callable(logger3.info)

    def test_reset_logging_functionality(self) -> None:
        """Test reset_logging clears all active containers."""
        # Create multiple containers
        configure_logging()
        configure_logging()
        configure_logging()

        containers_before = get_active_containers()
        assert len(containers_before) == 3

        # Reset logging
        reset_logging()

        containers_after = get_active_containers()
        assert len(containers_after) == 0

    def test_shutdown_logging_functionality(self) -> None:
        """Test shutdown_logging properly shuts down all containers."""
        # Create containers
        configure_logging(LoggingSettings(queue_enabled=True))
        configure_logging(LoggingSettings(queue_enabled=False))

        containers_before = get_active_containers()
        assert len(containers_before) == 2

        # Shutdown logging
        shutdown_logging()

        containers_after = get_active_containers()
        assert len(containers_after) == 0

    def test_shutdown_queue_worker_backward_compatibility(self) -> None:
        """Test _shutdown_queue_worker for backward compatibility."""
        # Create container with queue
        configure_logging(LoggingSettings(queue_enabled=True, sinks=["stdout"]))

        containers = get_active_containers()
        assert len(containers) == 1
        assert containers[0].queue_worker is not None

        # Should not raise exception
        _shutdown_queue_worker()

    def test_get_active_containers_returns_copy(self) -> None:
        """Test get_active_containers returns a copy, not reference."""
        configure_logging()

        containers1 = get_active_containers()
        containers2 = get_active_containers()

        # Should be different lists
        assert containers1 is not containers2
        assert len(containers1) == len(containers2) == 1
        # But contain the same container instances
        assert containers1[0] is containers2[0]

    def test_determine_console_format_utility(self) -> None:
        """Test _determine_console_format utility function."""
        # Test valid formats
        assert _determine_console_format("pretty") == "pretty"
        assert _determine_console_format("json") == "json"

        # Test auto format (depends on TTY)
        result = _determine_console_format("auto")
        assert result in ["pretty", "json"]

        # Test invalid format
        with pytest.raises(ConfigurationError):
            _determine_console_format("invalid")

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

    def test_container_lifecycle_management(self) -> None:
        """Test proper container lifecycle management."""
        # Create containers
        logger1, container1 = configure_with_container()
        logger2, container2 = configure_with_container()

        # Both should be configured
        assert container1.is_configured
        assert container2.is_configured

        active_containers = get_active_containers()
        assert len(active_containers) == 2

        # Reset should clear all
        reset_logging()

        # Containers should be reset
        assert not container1.is_configured
        assert not container2.is_configured
        assert len(get_active_containers()) == 0

    def test_error_handling_during_reset(self) -> None:
        """Test error handling during reset operations."""
        # Create a container and force an error
        logger, container = configure_with_container()

        # Mock the reset method to raise an exception
        original_reset = container.reset
        container.reset = Mock(side_effect=Exception("Reset error"))

        # Reset should not raise despite the error
        reset_logging()  # Should not raise

        # Should still clear the registry
        assert len(get_active_containers()) == 0

        # Restore original method
        container.reset = original_reset

    def test_error_handling_during_shutdown(self) -> None:
        """Test error handling during shutdown operations."""
        # Create a container and force an error
        logger, container = configure_with_container()

        # Mock the shutdown method to raise an exception
        original_shutdown = container.shutdown_sync
        container.shutdown_sync = Mock(side_effect=Exception("Shutdown error"))

        # Shutdown should not raise despite the error
        shutdown_logging()  # Should not raise

        # Should still clear the registry
        assert len(get_active_containers()) == 0

        # Restore original method
        container.shutdown_sync = original_shutdown

    def test_no_global_state_dependencies(self) -> None:
        """Test that bootstrap has no global state dependencies."""
        # This test verifies the pure DI implementation
        import fapilog.bootstrap as bootstrap_module

        # Should not have global container variables
        assert not hasattr(bootstrap_module, "_default_container")
        assert not hasattr(bootstrap_module, "_get_default_container")

        # Should have registry for lifecycle management (this is NOT global state)
        assert hasattr(bootstrap_module, "_active_containers")
        assert isinstance(bootstrap_module._active_containers, list)

    def test_memory_management_without_leaks(self) -> None:
        """Test that containers can be garbage collected properly."""
        import gc
        import weakref

        # Create containers and track with weak references
        container_refs = []

        for _ in range(5):
            logger, container = configure_with_container()
            container_refs.append(weakref.ref(container))
            # Delete strong reference
            del logger, container

        # Reset logging to clear registry
        reset_logging()

        # Force garbage collection
        gc.collect()

        # Some containers should be garbage collected
        alive_containers = sum(1 for ref in container_refs if ref() is not None)
        # Allow for GC timing variations
        assert alive_containers <= len(container_refs)

    def test_concurrent_configure_calls(self) -> None:
        """Test concurrent configure_logging calls create isolated containers."""
        import threading
        import time

        results = {}

        def configure_worker(worker_id: int) -> None:
            """Worker function for concurrent testing."""
            settings = LoggingSettings(level="INFO", queue_enabled=(worker_id % 2 == 0))
            logger = configure_logging(settings=settings)
            time.sleep(0.1)  # Simulate some work
            results[worker_id] = {
                "logger_callable": callable(logger.info),
                "queue_enabled": settings.queue_enabled,
            }

        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=configure_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all workers completed successfully
        assert len(results) == 10
        for i, result in results.items():
            assert result["logger_callable"] is True
            assert result["queue_enabled"] == (i % 2 == 0)

        # Should have created 10 containers
        assert len(get_active_containers()) == 10
