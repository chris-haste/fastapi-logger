"""Tests for LifecycleManager class."""

import logging
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fapilog._internal.lifecycle_manager import LifecycleManager
from fapilog.exceptions import ConfigurationError
from fapilog.settings import LoggingSettings


class TestLifecycleManager:
    """Test suite for LifecycleManager class."""

    def test_lifecycle_manager_initialization(self):
        """Test LifecycleManager initialization."""
        container_id = "test_container_123"
        manager = LifecycleManager(container_id)

        assert manager._container_id == container_id
        assert hasattr(manager, "_lock")
        assert not manager._shutdown_registered

    def test_configure_standard_logging_info_level(self):
        """Test configuring standard logging with INFO level."""
        manager = LifecycleManager("test")

        with patch("logging.getLogger") as mock_get_logger, patch(
            "logging.StreamHandler"
        ) as mock_handler_class:
            mock_handler = MagicMock()
            mock_handler_class.return_value = mock_handler
            mock_root_logger = MagicMock()
            mock_root_logger.handlers = []
            mock_get_logger.return_value = mock_root_logger

            manager.configure_standard_logging("INFO")

            # Verify handler creation and configuration
            mock_handler_class.assert_called_once_with(sys.stdout)
            mock_handler.setLevel.assert_called_once_with(logging.INFO)
            mock_handler.setFormatter.assert_called_once()

            # Verify root logger configuration
            mock_root_logger.setLevel.assert_called_once_with(logging.INFO)
            mock_root_logger.addHandler.assert_called_once_with(mock_handler)

    def test_configure_standard_logging_debug_level(self):
        """Test configuring standard logging with DEBUG level."""
        manager = LifecycleManager("test")

        with patch("logging.getLogger") as mock_get_logger, patch(
            "logging.StreamHandler"
        ) as mock_handler_class:
            mock_handler = MagicMock()
            mock_handler_class.return_value = mock_handler
            mock_root_logger = MagicMock()
            mock_root_logger.handlers = []
            mock_get_logger.return_value = mock_root_logger

            manager.configure_standard_logging("DEBUG")

            # Verify DEBUG level is set
            mock_handler.setLevel.assert_called_once_with(logging.DEBUG)
            mock_root_logger.setLevel.assert_called_once_with(logging.DEBUG)

    def test_configure_standard_logging_removes_existing_handlers(self):
        """Test that existing handlers are removed when configuring."""
        manager = LifecycleManager("test")

        with patch("logging.getLogger") as mock_get_logger, patch(
            "logging.StreamHandler"
        ) as mock_handler_class:
            # Setup existing handlers
            existing_handler1 = MagicMock()
            existing_handler2 = MagicMock()
            mock_root_logger = MagicMock()
            mock_root_logger.handlers = [existing_handler1, existing_handler2]
            mock_get_logger.return_value = mock_root_logger

            mock_handler = MagicMock()
            mock_handler_class.return_value = mock_handler

            manager.configure_standard_logging("INFO")

            # Verify existing handlers were removed
            assert mock_root_logger.removeHandler.call_count == 2
            mock_root_logger.removeHandler.assert_any_call(existing_handler1)
            mock_root_logger.removeHandler.assert_any_call(existing_handler2)

    def test_configure_standard_logging_invalid_level(self):
        """Test that invalid log levels raise ConfigurationError."""
        manager = LifecycleManager("test")

        with pytest.raises(ConfigurationError):
            manager.configure_standard_logging("INVALID_LEVEL")

    def test_register_middleware_with_shutdown_callback(self):
        """Test registering middleware with shutdown callback."""
        manager = LifecycleManager("test")
        mock_app = MagicMock()
        settings = LoggingSettings(trace_id_header="X-Custom-Trace")
        shutdown_callback = MagicMock()

        manager.register_middleware(mock_app, settings, shutdown_callback)

        # Verify middleware registration
        mock_app.add_middleware.assert_called_once()
        args, kwargs = mock_app.add_middleware.call_args
        assert len(args) >= 1
        assert kwargs.get("trace_id_header") == "X-Custom-Trace"

        # Verify shutdown handler registration is skipped in test environment
        # (Since we're running under pytest, the FastAPI handler should not be registered)
        mock_app.add_event_handler.assert_not_called()

    def test_register_middleware_without_shutdown_callback(self):
        """Test registering middleware without shutdown callback."""
        manager = LifecycleManager("test")
        mock_app = MagicMock()
        settings = LoggingSettings(trace_id_header="X-Request-ID")

        manager.register_middleware(mock_app, settings, None)

        # Verify middleware registration
        mock_app.add_middleware.assert_called_once()

        # Verify no shutdown handler registration
        mock_app.add_event_handler.assert_not_called()

    def test_register_shutdown_handler_first_time(self):
        """Test registering shutdown handler for the first time."""
        manager = LifecycleManager("test")
        cleanup_func = MagicMock()

        with patch("atexit.register") as mock_atexit:
            manager.register_shutdown_handler(cleanup_func)

            mock_atexit.assert_called_once_with(cleanup_func)
            assert manager._shutdown_registered

    def test_register_shutdown_handler_already_registered(self):
        """Test that shutdown handler is only registered once."""
        manager = LifecycleManager("test")
        cleanup_func1 = MagicMock()
        cleanup_func2 = MagicMock()

        with patch("atexit.register") as mock_atexit:
            # First registration
            manager.register_shutdown_handler(cleanup_func1)
            assert mock_atexit.call_count == 1

            # Second registration should be ignored
            manager.register_shutdown_handler(cleanup_func2)
            assert mock_atexit.call_count == 1  # Still only one call

    @pytest.mark.asyncio
    async def test_shutdown_async_success(self):
        """Test successful async shutdown."""
        manager = LifecycleManager("test")

        # Mock components
        mock_registry = MagicMock()
        mock_queue_worker = AsyncMock()
        mock_httpx_propagation = MagicMock()
        mock_sink_manager = AsyncMock()

        # Mock prometheus exporter
        mock_prometheus = AsyncMock()
        mock_registry.get_component.return_value = mock_prometheus

        await manager.shutdown_async(
            registry=mock_registry,
            queue_worker=mock_queue_worker,
            httpx_propagation=mock_httpx_propagation,
            sink_manager=mock_sink_manager,
        )

        # Verify cleanup calls
        mock_sink_manager.cleanup_sinks_async.assert_awaited_once()
        mock_registry.cleanup.assert_called_once()
        mock_prometheus.stop.assert_awaited_once()
        mock_queue_worker.shutdown.assert_awaited_once()
        mock_httpx_propagation.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_async_with_errors(self):
        """Test async shutdown handles errors gracefully."""
        manager = LifecycleManager("test")

        # Mock components that raise errors
        mock_registry = MagicMock()
        mock_registry.cleanup.side_effect = Exception("Registry cleanup error")

        mock_queue_worker = AsyncMock()
        mock_queue_worker.shutdown.side_effect = Exception("Queue shutdown error")

        mock_httpx_propagation = MagicMock()
        mock_httpx_propagation.cleanup.side_effect = Exception("Httpx cleanup error")

        # Mock prometheus exporter with error
        mock_prometheus = AsyncMock()
        mock_prometheus.stop.side_effect = Exception("Prometheus stop error")
        mock_registry.get_component.return_value = mock_prometheus

        # Should not raise exceptions
        with patch("fapilog._internal.lifecycle_manager.logger") as mock_logger:
            await manager.shutdown_async(
                registry=mock_registry,
                queue_worker=mock_queue_worker,
                httpx_propagation=mock_httpx_propagation,
            )

            # Verify warnings were logged
            assert mock_logger.warning.call_count >= 4

    @pytest.mark.asyncio
    async def test_shutdown_async_no_prometheus_exporter(self):
        """Test async shutdown when no Prometheus exporter exists."""
        manager = LifecycleManager("test")

        mock_registry = MagicMock()
        mock_registry.get_component.return_value = None  # No prometheus exporter

        await manager.shutdown_async(registry=mock_registry)

        # Should not try to stop non-existent prometheus exporter
        mock_registry.cleanup.assert_called_once()

    def test_shutdown_sync_success(self):
        """Test successful sync shutdown."""
        manager = LifecycleManager("test")

        # Mock components
        mock_registry = MagicMock()
        mock_queue_worker = MagicMock()
        mock_httpx_propagation = MagicMock()
        mock_sink_manager = MagicMock()

        manager.shutdown_sync(
            registry=mock_registry,
            queue_worker=mock_queue_worker,
            httpx_propagation=mock_httpx_propagation,
            sink_manager=mock_sink_manager,
        )

        # Verify cleanup calls
        mock_sink_manager.cleanup_sinks.assert_called_once()
        mock_registry.cleanup.assert_called_once()
        mock_queue_worker.shutdown_sync.assert_called_once()
        mock_httpx_propagation.cleanup.assert_called_once()

    def test_shutdown_sync_with_errors(self):
        """Test sync shutdown handles errors gracefully."""
        manager = LifecycleManager("test")

        # Mock components that raise errors
        mock_registry = MagicMock()
        mock_registry.cleanup.side_effect = Exception("Registry cleanup error")

        mock_queue_worker = MagicMock()
        mock_queue_worker.shutdown_sync.side_effect = Exception("Queue shutdown error")

        mock_httpx_propagation = MagicMock()
        mock_httpx_propagation.cleanup.side_effect = Exception("Httpx cleanup error")

        # Should not raise exceptions
        with patch("fapilog._internal.lifecycle_manager.logger") as mock_logger:
            manager.shutdown_sync(
                registry=mock_registry,
                queue_worker=mock_queue_worker,
                httpx_propagation=mock_httpx_propagation,
            )

            # Verify warnings were logged
            assert mock_logger.warning.call_count >= 3

    def test_cleanup_resources_method_exists(self):
        """Test that cleanup_resources method exists for interface completeness."""
        manager = LifecycleManager("test")

        # Method should exist and not raise errors
        manager.cleanup_resources(some_resource="value", another_resource=None)

    def test_thread_safety_multiple_configurations(self):
        """Test thread safety of configuration operations."""
        import threading

        manager = LifecycleManager("test")
        errors = []

        def configure_logging():
            try:
                with patch("logging.getLogger") as mock_get_logger, patch(
                    "logging.StreamHandler"
                ):
                    mock_root_logger = MagicMock()
                    mock_root_logger.handlers = []
                    mock_get_logger.return_value = mock_root_logger

                    manager.configure_standard_logging("INFO")
            except Exception as e:
                errors.append(e)

        # Run multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=configure_logging)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        assert not errors, f"Thread safety test failed with errors: {errors}"

    def test_container_id_storage(self):
        """Test that container ID is properly stored and accessible."""
        container_id = "unique_container_456"
        manager = LifecycleManager(container_id)

        assert manager._container_id == container_id

    def test_lifecycle_manager_isolation(self):
        """Test that multiple LifecycleManager instances are isolated."""
        manager1 = LifecycleManager("container_1")
        manager2 = LifecycleManager("container_2")

        # Register shutdown handler for manager1 only
        with patch("atexit.register"):
            manager1.register_shutdown_handler(lambda: None)

        # Manager2 should still be unregistered
        assert manager1._shutdown_registered
        assert not manager2._shutdown_registered

        # Should have different container IDs
        assert manager1._container_id != manager2._container_id

    def test_middleware_registration_with_custom_settings(self):
        """Test middleware registration with various settings configurations."""
        manager = LifecycleManager("test")
        mock_app = MagicMock()

        # Test with custom trace header
        settings = LoggingSettings(trace_id_header="X-Custom-Header")
        manager.register_middleware(mock_app, settings)

        # Verify custom header is used
        args, kwargs = mock_app.add_middleware.call_args
        assert kwargs["trace_id_header"] == "X-Custom-Header"

    @pytest.mark.asyncio
    async def test_shutdown_async_partial_components(self):
        """Test async shutdown with only some components provided."""
        manager = LifecycleManager("test")

        mock_registry = MagicMock()
        mock_registry.get_component.return_value = None

        # Should handle None components gracefully
        await manager.shutdown_async(
            registry=mock_registry,
            queue_worker=None,
            httpx_propagation=None,
            sink_manager=None,
        )

        # Should still cleanup registry
        mock_registry.cleanup.assert_called_once()

    def test_shutdown_sync_partial_components(self):
        """Test sync shutdown with only some components provided."""
        manager = LifecycleManager("test")

        mock_registry = MagicMock()

        # Should handle None components gracefully
        manager.shutdown_sync(
            registry=mock_registry,
            queue_worker=None,
            httpx_propagation=None,
            sink_manager=None,
        )

        # Should still cleanup registry
        mock_registry.cleanup.assert_called_once()
