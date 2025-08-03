"""Tests for MiddlewareManager class.

This module tests the MiddlewareManager functionality extracted from
LoggingContainer, ensuring proper middleware registration, httpx trace
propagation, and clean separation of concerns.
"""

from unittest.mock import Mock, patch

from fapilog.core.managers.middleware_manager import MiddlewareManager
from fapilog.settings import LoggingSettings


class TestMiddlewareManager:
    """Test cases for MiddlewareManager class."""

    def test_init(self):
        """Test MiddlewareManager initialization."""
        container_id = "test_container_123"
        manager = MiddlewareManager(container_id)

        assert manager._container_id == container_id
        assert manager._httpx_propagation is None
        assert manager._lock is not None

    @patch("fapilog.core.managers.middleware_manager.TraceIDMiddleware")
    def test_register_middleware_basic(self, mock_middleware_class):
        """Test basic middleware registration with FastAPI app."""
        manager = MiddlewareManager("test_container")
        mock_app = Mock()
        settings = LoggingSettings()

        manager.register_middleware(mock_app, settings)

        # Verify TraceIDMiddleware was added
        mock_app.add_middleware.assert_called_once_with(
            mock_middleware_class, trace_id_header=settings.trace_id_header
        )

    @patch("fapilog.core.managers.middleware_manager.TraceIDMiddleware")
    def test_register_middleware_with_trace_id_middleware(self, mock_middleware_class):
        """Test middleware registration includes TraceIDMiddleware."""
        manager = MiddlewareManager("test_container")
        mock_app = Mock()
        settings = LoggingSettings(trace_id_header="X-Custom-Trace-ID")

        manager.register_middleware(mock_app, settings)

        mock_app.add_middleware.assert_called_once_with(
            mock_middleware_class, trace_id_header="X-Custom-Trace-ID"
        )

    @patch("fapilog.core.managers.middleware_manager.sys")
    def test_register_middleware_with_shutdown_callback_production(self, mock_sys):
        """Test middleware registration with shutdown callback in production."""
        # Mock production environment (no pytest)
        mock_sys.modules = {}
        mock_sys.argv = []

        manager = MiddlewareManager("test_container")
        mock_app = Mock()
        mock_app.router = Mock()  # Make it look like FastAPI
        mock_app.state = Mock()
        settings = LoggingSettings()
        shutdown_callback = Mock()

        with patch.dict("os.environ", {}, clear=True):
            manager.register_middleware(mock_app, settings, shutdown_callback)

        # Verify shutdown handler was registered
        mock_app.add_event_handler.assert_called_once_with(
            "shutdown", shutdown_callback
        )

    @patch("fapilog.core.managers.middleware_manager.sys")
    def test_register_middleware_with_shutdown_callback_testing(self, mock_sys):
        """Test middleware registration skips shutdown callback in test environment."""
        # Mock test environment
        mock_sys.modules = {"pytest": Mock()}
        mock_sys.argv = []

        manager = MiddlewareManager("test_container")
        mock_app = Mock()
        settings = LoggingSettings()
        shutdown_callback = Mock()

        manager.register_middleware(mock_app, settings, shutdown_callback)

        # Verify shutdown handler was NOT registered in test environment
        mock_app.add_event_handler.assert_not_called()

    def test_configure_httpx_trace_propagation_enabled(self):
        """Test httpx trace propagation configuration when enabled."""
        manager = MiddlewareManager("test_container")
        settings = LoggingSettings(enable_httpx_trace_propagation=True)

        with patch(
            "fapilog.core.managers.middleware_manager.HttpxTracePropagation"
        ) as mock_propagation_class:
            mock_propagation = Mock()
            mock_propagation_class.return_value = mock_propagation

            manager.configure_httpx_trace_propagation(settings)

            # Verify HttpxTracePropagation was created and configured
            mock_propagation_class.assert_called_once()
            mock_propagation.configure.assert_called_once_with(settings)
            assert manager._httpx_propagation == mock_propagation

    def test_configure_httpx_trace_propagation_disabled(self):
        """Test httpx trace propagation configuration when disabled."""
        manager = MiddlewareManager("test_container")
        settings = LoggingSettings(enable_httpx_trace_propagation=False)

        with patch(
            "fapilog.core.managers.middleware_manager.HttpxTracePropagation"
        ) as mock_propagation_class:
            manager.configure_httpx_trace_propagation(settings)

            # Verify HttpxTracePropagation was NOT created
            mock_propagation_class.assert_not_called()
            assert manager._httpx_propagation is None

    def test_setup_trace_middleware(self):
        """Test setup_trace_middleware convenience method."""
        manager = MiddlewareManager("test_container")
        mock_app = Mock()

        with patch(
            "fapilog.core.managers.middleware_manager.LoggingSettings"
        ) as mock_settings_class, patch(
            "fapilog.core.managers.middleware_manager.TraceIDMiddleware"
        ) as mock_middleware:
            mock_settings = Mock()
            mock_settings.trace_id_header = "X-Request-ID"  # Use actual default value
            mock_settings_class.return_value = mock_settings

            manager.setup_trace_middleware(mock_app)

            # Verify middleware was added with default settings
            mock_app.add_middleware.assert_called_once_with(
                mock_middleware, trace_id_header="X-Request-ID"
            )

    def test_cleanup_httpx_propagation_with_propagation(self):
        """Test cleanup when httpx propagation is configured."""
        manager = MiddlewareManager("test_container")
        mock_propagation = Mock()
        manager._httpx_propagation = mock_propagation

        manager.cleanup_httpx_propagation()

        # Verify cleanup was called and propagation reset
        mock_propagation.cleanup.assert_called_once()
        assert manager._httpx_propagation is None

    def test_cleanup_httpx_propagation_without_propagation(self):
        """Test cleanup when no httpx propagation is configured."""
        manager = MiddlewareManager("test_container")
        assert manager._httpx_propagation is None

        # Should not raise exception
        manager.cleanup_httpx_propagation()
        assert manager._httpx_propagation is None

    def test_cleanup_httpx_propagation_with_exception(self):
        """Test cleanup handles exceptions gracefully."""
        manager = MiddlewareManager("test_container")
        mock_propagation = Mock()
        mock_propagation.cleanup.side_effect = Exception("Cleanup failed")
        manager._httpx_propagation = mock_propagation

        with patch("fapilog.core.managers.middleware_manager.logger") as mock_logger:
            manager.cleanup_httpx_propagation()

            # Verify exception was logged and propagation reset
            mock_logger.warning.assert_called_once()
            assert manager._httpx_propagation is None

    def test_get_httpx_propagation_with_propagation(self):
        """Test getting httpx propagation when configured."""
        manager = MiddlewareManager("test_container")
        mock_propagation = Mock()
        manager._httpx_propagation = mock_propagation

        result = manager.get_httpx_propagation()
        assert result == mock_propagation

    def test_get_httpx_propagation_without_propagation(self):
        """Test getting httpx propagation when not configured."""
        manager = MiddlewareManager("test_container")

        result = manager.get_httpx_propagation()
        assert result is None

    def test_is_httpx_propagation_enabled_true(self):
        """Test is_httpx_propagation_enabled when enabled."""
        manager = MiddlewareManager("test_container")
        manager._httpx_propagation = Mock()

        assert manager.is_httpx_propagation_enabled() is True

    def test_is_httpx_propagation_enabled_false(self):
        """Test is_httpx_propagation_enabled when disabled."""
        manager = MiddlewareManager("test_container")
        assert manager._httpx_propagation is None

        assert manager.is_httpx_propagation_enabled() is False

    def test_thread_safety(self):
        """Test that MiddlewareManager operations are thread-safe."""
        import threading
        import time

        manager = MiddlewareManager("test_container")
        settings = LoggingSettings(enable_httpx_trace_propagation=True)
        errors = []

        def configure_propagation():
            try:
                with patch(
                    "fapilog.core.managers.middleware_manager.HttpxTracePropagation"
                ):
                    manager.configure_httpx_trace_propagation(settings)
                    time.sleep(0.01)  # Small delay to encourage race conditions
                    manager.cleanup_httpx_propagation()
            except Exception as e:
                errors.append(e)

        # Run multiple threads concurrently
        threads = [threading.Thread(target=configure_propagation) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Verify no threading errors occurred
        assert len(errors) == 0
        assert manager._httpx_propagation is None  # Final state should be clean


class TestMiddlewareManagerIntegration:
    """Integration tests for MiddlewareManager with real components."""

    def test_integration_with_logging_settings(self):
        """Test MiddlewareManager works with real LoggingSettings."""
        manager = MiddlewareManager("integration_test")

        # Test with various settings configurations
        settings_configs = [
            {"trace_id_header": "X-Trace-ID", "enable_httpx_trace_propagation": False},
            {"trace_id_header": "X-Request-ID", "enable_httpx_trace_propagation": True},
            {"trace_id_header": "X-Custom", "enable_httpx_trace_propagation": False},
        ]

        for config in settings_configs:
            settings = LoggingSettings(**config)
            mock_app = Mock()

            # Test middleware registration
            with patch(
                "fapilog.core.managers.middleware_manager.TraceIDMiddleware"
            ) as mock_middleware:
                manager.register_middleware(mock_app, settings)
                mock_app.add_middleware.assert_called_with(
                    mock_middleware, trace_id_header=config["trace_id_header"]
                )

            # Test httpx propagation configuration
            with patch(
                "fapilog.core.managers.middleware_manager.HttpxTracePropagation"
            ) as mock_propagation_class:
                manager.configure_httpx_trace_propagation(settings)

                if config["enable_httpx_trace_propagation"]:
                    mock_propagation_class.assert_called()
                    assert manager._httpx_propagation is not None
                else:
                    assert manager._httpx_propagation is None

            # Cleanup for next iteration
            manager.cleanup_httpx_propagation()

    def test_full_lifecycle(self):
        """Test complete lifecycle of MiddlewareManager."""
        manager = MiddlewareManager("lifecycle_test")
        mock_app = Mock()
        mock_app.router = Mock()
        mock_app.state = Mock()
        settings = LoggingSettings(
            trace_id_header="X-Test-ID", enable_httpx_trace_propagation=True
        )
        shutdown_callback = Mock()

        # Test initialization state
        assert not manager.is_httpx_propagation_enabled()
        assert manager.get_httpx_propagation() is None

        # Test configuration
        with patch(
            "fapilog.core.managers.middleware_manager.HttpxTracePropagation"
        ) as mock_propagation_class, patch(
            "fapilog.core.managers.middleware_manager.TraceIDMiddleware"
        ) as mock_middleware, patch(
            "fapilog.core.managers.middleware_manager.sys"
        ) as mock_sys:
            # Mock production environment
            mock_sys.modules = {}
            mock_sys.argv = []

            mock_propagation = Mock()
            mock_propagation_class.return_value = mock_propagation

            # Configure httpx propagation
            manager.configure_httpx_trace_propagation(settings)
            assert manager.is_httpx_propagation_enabled()
            assert manager.get_httpx_propagation() == mock_propagation

            # Register middleware
            with patch.dict("os.environ", {}, clear=True):
                manager.register_middleware(mock_app, settings, shutdown_callback)

            # Verify all registrations
            mock_app.add_middleware.assert_called_with(
                mock_middleware, trace_id_header="X-Test-ID"
            )
            mock_app.add_event_handler.assert_called_with("shutdown", shutdown_callback)
            mock_propagation.configure.assert_called_with(settings)

        # Test cleanup
        manager.cleanup_httpx_propagation()
        assert not manager.is_httpx_propagation_enabled()
        assert manager.get_httpx_propagation() is None
