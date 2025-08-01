"""Tests for SinkManager class."""

from unittest.mock import MagicMock, patch

import pytest

from fapilog._internal.sink_manager import SinkManager
from fapilog.exceptions import SinkConfigurationError
from fapilog.settings import LoggingSettings
from fapilog.sinks.base import Sink


class TestSinkManager:
    """Test suite for SinkManager class."""

    def test_sink_manager_initialization(self):
        """Test SinkManager initialization."""
        container_id = "test_container_123"
        manager = SinkManager(container_id)

        assert manager._container_id == container_id
        assert hasattr(manager, "_lock")
        assert manager._sinks == []
        assert manager._queue_worker is None

    def test_setup_queue_worker_with_stdout_sink_pretty(self):
        """Test setting up queue worker with stdout sink in pretty mode."""
        manager = SinkManager("test")
        settings = LoggingSettings(sinks=["stdout"], queue={"enabled": True})
        mock_container = MagicMock()

        with patch("fapilog._internal.sink_manager.StdoutSink") as mock_stdout, patch(
            "fapilog._internal.sink_manager.QueueWorker"
        ) as mock_queue_worker:
            mock_sink = MagicMock()
            mock_stdout.return_value = mock_sink
            mock_worker = MagicMock()
            mock_queue_worker.return_value = mock_worker

            result = manager.setup_queue_worker(settings, "pretty", mock_container)

            # Verify stdout sink creation
            mock_stdout.assert_called_once_with(mode="pretty", container=mock_container)

            # Verify queue worker creation
            mock_queue_worker.assert_called_once()
            args, kwargs = mock_queue_worker.call_args
            assert kwargs["sinks"] == [mock_sink]

            assert result == mock_worker
            assert manager.get_queue_worker() == mock_worker

    def test_setup_queue_worker_with_stdout_sink_json(self):
        """Test setting up queue worker with stdout sink in json mode."""
        manager = SinkManager("test")
        settings = LoggingSettings(sinks=["stdout"], queue={"enabled": True})
        mock_container = MagicMock()

        with patch("fapilog._internal.sink_manager.StdoutSink") as mock_stdout, patch(
            "fapilog._internal.sink_manager.QueueWorker"
        ) as mock_queue_worker:
            mock_sink = MagicMock()
            mock_stdout.return_value = mock_sink
            mock_worker = MagicMock()
            mock_queue_worker.return_value = mock_worker

            manager.setup_queue_worker(settings, "json", mock_container)

            # Verify stdout sink creation with json mode
            mock_stdout.assert_called_once_with(mode="json", container=mock_container)

    def test_setup_queue_worker_with_stdout_sink_auto(self):
        """Test setting up queue worker with stdout sink in auto mode."""
        manager = SinkManager("test")
        settings = LoggingSettings(sinks=["stdout"], queue={"enabled": True})
        mock_container = MagicMock()

        with patch("fapilog._internal.sink_manager.StdoutSink") as mock_stdout, patch(
            "fapilog._internal.sink_manager.QueueWorker"
        ) as mock_queue_worker:
            mock_sink = MagicMock()
            mock_stdout.return_value = mock_sink
            mock_worker = MagicMock()
            mock_queue_worker.return_value = mock_worker

            manager.setup_queue_worker(settings, "auto", mock_container)

            # Verify stdout sink creation with auto mode
            mock_stdout.assert_called_once_with(mode="auto", container=mock_container)

    def test_setup_queue_worker_with_file_sink(self):
        """Test setting up queue worker with file sink."""
        manager = SinkManager("test")
        settings = LoggingSettings(
            sinks=["file:///tmp/test.log"], queue={"enabled": True}
        )
        mock_container = MagicMock()

        with patch(
            "fapilog._internal.sink_manager.create_file_sink_from_uri"
        ) as mock_file_sink, patch(
            "fapilog._internal.sink_manager.QueueWorker"
        ) as mock_queue_worker:
            mock_sink = MagicMock()
            mock_file_sink.return_value = mock_sink
            mock_worker = MagicMock()
            mock_queue_worker.return_value = mock_worker

            manager.setup_queue_worker(settings, "pretty", mock_container)

            # Verify file sink creation
            mock_file_sink.assert_called_once_with(
                "file:///tmp/test.log", container=mock_container
            )

    def test_setup_queue_worker_with_loki_sink(self):
        """Test setting up queue worker with loki sink."""
        manager = SinkManager("test")
        settings = LoggingSettings(
            sinks=["loki://localhost:3100"], queue={"enabled": True}
        )
        mock_container = MagicMock()

        with patch(
            "fapilog._internal.sink_manager.create_loki_sink_from_uri"
        ) as mock_loki_sink, patch(
            "fapilog._internal.sink_manager.QueueWorker"
        ) as mock_queue_worker:
            mock_sink = MagicMock()
            mock_loki_sink.return_value = mock_sink
            mock_worker = MagicMock()
            mock_queue_worker.return_value = mock_worker

            manager.setup_queue_worker(settings, "pretty", mock_container)

            # Verify loki sink creation
            mock_loki_sink.assert_called_once_with(
                "loki://localhost:3100", container=mock_container
            )

    def test_setup_queue_worker_with_custom_sink(self):
        """Test setting up queue worker with custom sink."""
        manager = SinkManager("test")
        settings = LoggingSettings(sinks=["custom://test"], queue={"enabled": True})
        mock_container = MagicMock()

        with patch(
            "fapilog._internal.sink_manager.create_custom_sink_from_uri"
        ) as mock_custom_sink, patch(
            "fapilog._internal.sink_manager.QueueWorker"
        ) as mock_queue_worker:
            mock_sink = MagicMock()
            mock_custom_sink.return_value = mock_sink
            mock_worker = MagicMock()
            mock_queue_worker.return_value = mock_worker

            manager.setup_queue_worker(settings, "pretty", mock_container)

            # Verify custom sink creation
            mock_custom_sink.assert_called_once_with("custom://test")

    def test_setup_queue_worker_with_direct_sink_instance(self):
        """Test setting up queue worker with direct Sink instance."""
        manager = SinkManager("test")
        mock_sink_instance = MagicMock(spec=Sink)
        settings = LoggingSettings(sinks=[mock_sink_instance], queue={"enabled": True})
        mock_container = MagicMock()

        with patch("fapilog._internal.sink_manager.QueueWorker") as mock_queue_worker:
            mock_worker = MagicMock()
            mock_queue_worker.return_value = mock_worker

            manager.setup_queue_worker(settings, "pretty", mock_container)

            # Verify direct sink instance is used
            mock_queue_worker.assert_called_once()
            args, kwargs = mock_queue_worker.call_args
            assert kwargs["sinks"] == [mock_sink_instance]

    def test_setup_queue_worker_file_sink_error(self):
        """Test file sink creation error handling."""
        manager = SinkManager("test")
        settings = LoggingSettings(sinks=["file:///invalid"], queue={"enabled": True})
        mock_container = MagicMock()

        with patch(
            "fapilog._internal.sink_manager.create_file_sink_from_uri"
        ) as mock_file_sink:
            mock_file_sink.side_effect = Exception("File error")

            with pytest.raises(SinkConfigurationError) as exc_info:
                manager.setup_queue_worker(settings, "pretty", mock_container)

            assert "File error" in str(exc_info.value)
            assert exc_info.value.sink_name == "file"

    def test_setup_queue_worker_loki_import_error(self):
        """Test loki sink import error handling."""
        manager = SinkManager("test")
        settings = LoggingSettings(
            sinks=["loki://localhost:3100"], queue={"enabled": True}
        )
        mock_container = MagicMock()

        with patch(
            "fapilog._internal.sink_manager.create_loki_sink_from_uri"
        ) as mock_loki_sink:
            mock_loki_sink.side_effect = ImportError("Loki not available")

            with pytest.raises(SinkConfigurationError) as exc_info:
                manager.setup_queue_worker(settings, "pretty", mock_container)

            assert "Loki not available" in str(exc_info.value)
            assert exc_info.value.sink_name == "loki"

    def test_setup_queue_worker_loki_general_error(self):
        """Test loki sink general error handling."""
        manager = SinkManager("test")
        settings = LoggingSettings(
            sinks=["loki://localhost:3100"], queue={"enabled": True}
        )
        mock_container = MagicMock()

        with patch(
            "fapilog._internal.sink_manager.create_loki_sink_from_uri"
        ) as mock_loki_sink:
            mock_loki_sink.side_effect = Exception("Loki config error")

            with pytest.raises(SinkConfigurationError) as exc_info:
                manager.setup_queue_worker(settings, "pretty", mock_container)

            assert "Loki config error" in str(exc_info.value)
            assert exc_info.value.sink_name == "loki"

    def test_setup_queue_worker_custom_sink_error(self):
        """Test custom sink error handling."""
        manager = SinkManager("test")
        settings = LoggingSettings(sinks=["custom://invalid"], queue={"enabled": True})
        mock_container = MagicMock()

        with patch(
            "fapilog._internal.sink_manager.create_custom_sink_from_uri"
        ) as mock_custom_sink:
            error = SinkConfigurationError("Custom error", "custom", {})
            mock_custom_sink.side_effect = error

            with pytest.raises(SinkConfigurationError) as exc_info:
                manager.setup_queue_worker(settings, "pretty", mock_container)

            assert "Custom error" in str(exc_info.value)
            assert exc_info.value.sink_name == "custom"

    def test_setup_queue_worker_unknown_sink_type(self):
        """Test unknown sink type error handling."""
        manager = SinkManager("test")
        settings = LoggingSettings(sinks=["unknown://test"], queue={"enabled": True})
        mock_container = MagicMock()

        with patch(
            "fapilog._internal.sink_manager.create_custom_sink_from_uri"
        ) as mock_custom_sink:
            mock_custom_sink.side_effect = Exception("Unknown sink")

            with pytest.raises(SinkConfigurationError) as exc_info:
                manager.setup_queue_worker(settings, "pretty", mock_container)

            assert "Unknown sink type" in str(exc_info.value)
            assert exc_info.value.sink_name == "unknown"

    def test_setup_queue_worker_queue_creation_error(self):
        """Test queue worker creation error handling."""
        manager = SinkManager("test")
        settings = LoggingSettings(sinks=["stdout"], queue={"enabled": True})
        mock_container = MagicMock()

        with patch("fapilog._internal.sink_manager.StdoutSink"), patch(
            "fapilog._internal.sink_manager.QueueWorker"
        ) as mock_queue_worker, patch(
            "fapilog._internal.sink_manager.handle_configuration_error"
        ) as mock_error_handler:
            mock_queue_worker.side_effect = Exception("Queue error")
            mock_error_handler.side_effect = Exception("Config error")

            with pytest.raises(Exception, match="Config error"):
                manager.setup_queue_worker(settings, "pretty", mock_container)

            # Verify error handler was called with queue config
            mock_error_handler.assert_called_once()
            args = mock_error_handler.call_args[0]
            assert "queue_worker" in args

    def test_create_sinks_from_settings_stdout(self):
        """Test creating sinks from settings without queue worker."""
        manager = SinkManager("test")
        settings = LoggingSettings(sinks=["stdout"])
        mock_container = MagicMock()

        with patch("fapilog._internal.sink_manager.StdoutSink") as mock_stdout:
            mock_sink = MagicMock()
            mock_stdout.return_value = mock_sink

            sinks = manager.create_sinks_from_settings(
                settings, "pretty", mock_container
            )

            assert sinks == [mock_sink]
            mock_stdout.assert_called_once_with(mode="pretty", container=mock_container)

    def test_create_sinks_from_settings_multiple_sinks(self):
        """Test creating multiple sinks from settings."""
        manager = SinkManager("test")
        mock_direct_sink = MagicMock(spec=Sink)
        settings = LoggingSettings(sinks=[mock_direct_sink, "stdout"])
        mock_container = MagicMock()

        with patch("fapilog._internal.sink_manager.StdoutSink") as mock_stdout:
            mock_stdout_sink = MagicMock()
            mock_stdout.return_value = mock_stdout_sink

            sinks = manager.create_sinks_from_settings(settings, "json", mock_container)

            assert len(sinks) == 2
            assert sinks[0] == mock_direct_sink
            assert sinks[1] == mock_stdout_sink
            mock_stdout.assert_called_once_with(mode="json", container=mock_container)

    def test_start_sinks(self):
        """Test starting all managed sinks."""
        manager = SinkManager("test")

        # Create mock sinks - some with start method, some without
        mock_sink_with_start = MagicMock()
        mock_sink_without_start = MagicMock()
        del mock_sink_without_start.start  # Remove start method

        manager._sinks = [mock_sink_with_start, mock_sink_without_start]

        manager.start_sinks()

        # Only sink with start method should be called
        mock_sink_with_start.start.assert_called_once()

    def test_stop_sinks(self):
        """Test stopping all managed sinks."""
        manager = SinkManager("test")

        # Create mock sinks - some with stop method, some without
        mock_sink_with_stop = MagicMock()
        mock_sink_without_stop = MagicMock()
        del mock_sink_without_stop.stop  # Remove stop method

        manager._sinks = [mock_sink_with_stop, mock_sink_without_stop]

        manager.stop_sinks()

        # Only sink with stop method should be called
        mock_sink_with_stop.stop.assert_called_once()

    def test_stop_sinks_with_error(self):
        """Test stopping sinks continues even if one sink fails."""
        manager = SinkManager("test")

        # Create mock sinks where one raises an error
        mock_sink1 = MagicMock()
        mock_sink2 = MagicMock()
        mock_sink1.stop.side_effect = Exception("Stop error")

        manager._sinks = [mock_sink1, mock_sink2]

        # Should not raise an exception
        manager.stop_sinks()

        # Both stop methods should have been called
        mock_sink1.stop.assert_called_once()
        mock_sink2.stop.assert_called_once()

    def test_cleanup_sinks(self):
        """Test cleanup of all managed sinks."""
        manager = SinkManager("test")

        mock_sink = MagicMock()
        manager._sinks = [mock_sink]
        manager._queue_worker = MagicMock()

        manager.cleanup_sinks()

        # Verify cleanup actions
        mock_sink.stop.assert_called_once()
        assert manager._sinks == []
        assert manager._queue_worker is None

    def test_get_sinks(self):
        """Test getting current list of managed sinks."""
        manager = SinkManager("test")

        mock_sink1 = MagicMock()
        mock_sink2 = MagicMock()
        manager._sinks = [mock_sink1, mock_sink2]

        sinks = manager.get_sinks()

        # Should return a copy of the sinks list
        assert sinks == [mock_sink1, mock_sink2]
        assert sinks is not manager._sinks  # Should be a copy

    def test_get_queue_worker_none(self):
        """Test getting queue worker when none is set."""
        manager = SinkManager("test")

        assert manager.get_queue_worker() is None

    def test_get_queue_worker_with_worker(self):
        """Test getting queue worker when one is set."""
        manager = SinkManager("test")
        mock_worker = MagicMock()
        manager._queue_worker = mock_worker

        assert manager.get_queue_worker() == mock_worker

    def test_thread_safety_setup_queue_worker(self):
        """Test thread safety of setup_queue_worker operations."""
        import threading

        manager = SinkManager("test")
        settings = LoggingSettings(sinks=["stdout"], queue={"enabled": True})
        mock_container = MagicMock()
        errors = []

        def setup_worker():
            try:
                with patch("fapilog._internal.sink_manager.StdoutSink"), patch(
                    "fapilog._internal.sink_manager.QueueWorker"
                ) as mock_queue_worker:
                    mock_worker = MagicMock()
                    mock_queue_worker.return_value = mock_worker
                    manager.setup_queue_worker(settings, "pretty", mock_container)
            except Exception as e:
                errors.append(e)

        # Run multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=setup_worker)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        assert not errors, f"Thread safety test failed with errors: {errors}"

    def test_sink_manager_isolation(self):
        """Test that multiple SinkManager instances are isolated."""
        manager1 = SinkManager("container_1")
        manager2 = SinkManager("container_2")

        # Add sinks to manager1 only
        mock_sink = MagicMock()
        manager1._sinks = [mock_sink]

        # Manager2 should still be empty
        assert len(manager1._sinks) == 1
        assert len(manager2._sinks) == 0
        assert manager1._container_id != manager2._container_id

    def test_queue_worker_configuration_parameters(self):
        """Test that queue worker is configured with correct parameters."""
        manager = SinkManager("test")
        settings = LoggingSettings(
            sinks=["stdout"],
            queue={
                "enabled": True,
                "maxsize": 1000,
                "batch_size": 10,
                "batch_timeout": 5.0,
                "retry_delay": 1.0,
                "max_retries": 3,
                "overflow": "block",
            },
            sampling_rate=0.8,
        )
        mock_container = MagicMock()

        with patch("fapilog._internal.sink_manager.StdoutSink"), patch(
            "fapilog._internal.sink_manager.QueueWorker"
        ) as mock_queue_worker:
            mock_worker = MagicMock()
            mock_queue_worker.return_value = mock_worker

            manager.setup_queue_worker(settings, "pretty", mock_container)

            # Verify queue worker was called with correct parameters
            mock_queue_worker.assert_called_once()
            args, kwargs = mock_queue_worker.call_args
            assert kwargs["queue_max_size"] == 1000
            assert kwargs["batch_size"] == 10
            assert kwargs["batch_timeout"] == 5.0
            assert kwargs["retry_delay"] == 1.0
            assert kwargs["max_retries"] == 3
            assert kwargs["overflow_strategy"] == "block"
            assert kwargs["sampling_rate"] == 0.8
            assert kwargs["container"] == mock_container
