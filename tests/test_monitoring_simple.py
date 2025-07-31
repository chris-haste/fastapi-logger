"""Simplified monitoring tests to improve coverage."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# # create_metrics_collector  # Removed in Issue 164, # set_metrics_collector  # Removed in Issue 164 removed in Issue 164
from fapilog.monitoring import (
    PrometheusExporter,
    create_prometheus_exporter,
    get_metrics_dict,
    get_metrics_text,
    get_prometheus_exporter,
    set_prometheus_exporter,
    start_metrics_server,
    stop_metrics_server,
)


class TestPrometheusExporterBasics:
    """Test basic PrometheusExporter functionality."""

    def test_prometheus_exporter_disables_when_fastapi_unavailable(self):
        """Test that PrometheusExporter disables itself when FastAPI is not available."""
        with patch("fapilog.monitoring.FastAPI", None):
            exporter = PrometheusExporter(enabled=True)
            assert not exporter.enabled

    def test_prometheus_exporter_logs_warning_when_fastapi_unavailable(self):
        """Test that PrometheusExporter logs warning when FastAPI is not available."""
        with patch("fapilog.monitoring.FastAPI", None), patch(
            "fapilog.monitoring.logger"
        ) as mock_logger:
            PrometheusExporter(enabled=True)

            mock_logger.warning.assert_called_once()
            assert "FastAPI not available" in mock_logger.warning.call_args[0][0]

    def test_prometheus_exporter_disabled_initialization(self):
        """Test PrometheusExporter initialization when disabled."""
        exporter = PrometheusExporter(enabled=False)
        assert not exporter.enabled
        assert exporter._app is None

    def test_get_metrics_url_when_disabled(self):
        """Test get_metrics_url returns None when disabled."""
        exporter = PrometheusExporter(enabled=False)
        assert exporter.get_metrics_url() is None

    def test_get_metrics_url_when_enabled(self):
        """Test get_metrics_url returns correct URL when enabled."""
        with patch("fapilog.monitoring.FastAPI") as mock_fastapi:
            mock_fastapi.return_value = MagicMock()
            exporter = PrometheusExporter(
                enabled=True, host="localhost", port=9090, path="/custom"
            )
            url = exporter.get_metrics_url()
            assert url == "http://localhost:9090/custom"

    def test_is_running_states(self):
        """Test is_running() in various states."""
        # Disabled exporter
        exporter = PrometheusExporter(enabled=False)
        assert not exporter.is_running()

        # Enabled but no task
        with patch("fapilog.monitoring.FastAPI") as mock_fastapi:
            mock_fastapi.return_value = MagicMock()
            exporter = PrometheusExporter(enabled=True)
            assert not exporter.is_running()

            # With completed task
            mock_task = MagicMock()
            mock_task.done.return_value = True
            exporter._server_task = mock_task
            assert not exporter.is_running()

            # With running task
            mock_task.done.return_value = False
            assert exporter.is_running()


class TestPrometheusExporterServerControl:
    """Test server start/stop functionality."""

    @pytest.fixture
    def mock_fastapi_components(self):
        """Mock FastAPI and uvicorn components."""
        with patch("fapilog.monitoring.FastAPI") as mock_fastapi, patch(
            "fapilog.monitoring.uvicorn"
        ) as mock_uvicorn:
            mock_app = MagicMock()
            mock_fastapi.return_value = mock_app

            yield {"FastAPI": mock_fastapi, "app": mock_app, "uvicorn": mock_uvicorn}

    @pytest.mark.asyncio
    async def test_start_server_when_disabled(self, mock_fastapi_components):
        """Test start() when exporter is disabled."""
        exporter = PrometheusExporter(enabled=False)

        with patch("fapilog.monitoring.logger") as mock_logger:
            await exporter.start()
            mock_logger.debug.assert_called_with(
                "Prometheus exporter not enabled or not configured"
            )

    @pytest.mark.asyncio
    async def test_start_server_already_running(self, mock_fastapi_components):
        """Test start() when server is already running."""
        exporter = PrometheusExporter(enabled=True)

        mock_task = MagicMock()
        mock_task.done.return_value = False
        exporter._server_task = mock_task

        with patch("fapilog.monitoring.logger") as mock_logger:
            await exporter.start()
            mock_logger.debug.assert_called_with("Prometheus exporter already running")

    @pytest.mark.asyncio
    async def test_start_server_success(self, mock_fastapi_components):
        """Test successful server start."""
        mocks = mock_fastapi_components
        exporter = PrometheusExporter(enabled=True, host="127.0.0.1", port=9090)

        mock_config = MagicMock()
        mock_server = MagicMock()
        mock_task = AsyncMock()

        mocks["uvicorn"].Config.return_value = mock_config
        mocks["uvicorn"].Server.return_value = mock_server

        with patch(
            "asyncio.create_task", return_value=mock_task
        ) as mock_create_task, patch("fapilog.monitoring.logger") as mock_logger:
            await exporter.start()

            mocks["uvicorn"].Config.assert_called_once_with(
                app=exporter._app,
                host="127.0.0.1",
                port=9090,
                log_level="error",
                access_log=False,
            )
            mocks["uvicorn"].Server.assert_called_once_with(mock_config)
            mock_create_task.assert_called_once()

            mock_logger.info.assert_called_once()
            assert (
                "started on http://127.0.0.1:9090" in mock_logger.info.call_args[0][0]
            )

    @pytest.mark.asyncio
    async def test_start_server_exception(self, mock_fastapi_components):
        """Test server start with exception."""
        mocks = mock_fastapi_components
        exporter = PrometheusExporter(enabled=True)

        mocks["uvicorn"].Config.side_effect = Exception("Server start error")

        with patch("fapilog.monitoring.logger") as mock_logger:
            await exporter.start()

            mock_logger.error.assert_called_once()
            assert (
                "Failed to start Prometheus metrics server"
                in mock_logger.error.call_args[0][0]
            )
            assert not exporter.enabled

    @pytest.mark.asyncio
    async def test_stop_server_no_task(self):
        """Test stop() when no server task exists."""
        exporter = PrometheusExporter(enabled=True)
        exporter._server_task = None

        await exporter.stop()  # Should not raise exception

    @pytest.mark.asyncio
    async def test_stop_server_task_done(self):
        """Test stop() when task is already done."""
        exporter = PrometheusExporter(enabled=True)

        mock_task = MagicMock()
        mock_task.done.return_value = True
        exporter._server_task = mock_task

        await exporter.stop()

        mock_task.cancel.assert_not_called()


class TestGlobalFunctions:
    """Test global functions in monitoring module."""

    def setup_method(self):
        """Clean up global state before each test."""
        set_prometheus_exporter(None)
        # set_metrics_collector  # Removed in Issue 164(None)

    def teardown_method(self):
        """Clean up global state after each test."""
        set_prometheus_exporter(None)
        # set_metrics_collector  # Removed in Issue 164(None)

    def test_global_prometheus_exporter_management(self):
        """Test global Prometheus exporter get/set functions."""
        assert get_prometheus_exporter() is None

        exporter = PrometheusExporter(enabled=False)
        set_prometheus_exporter(exporter)

        assert get_prometheus_exporter() is exporter

    def test_create_prometheus_exporter_sets_global(self):
        """Test create_prometheus_exporter sets global instance."""
        exporter = create_prometheus_exporter(
            host="127.0.0.1", port=8888, path="/test", enabled=False
        )

        assert exporter.host == "127.0.0.1"
        assert exporter.port == 8888
        assert exporter.path == "/test"
        assert not exporter.enabled
        assert get_prometheus_exporter() is exporter

    @pytest.mark.asyncio
    async def test_start_metrics_server_success(self):
        """Test start_metrics_server function success."""
        with patch("fapilog.monitoring.create_prometheus_exporter") as mock_create:
            mock_exporter = AsyncMock()
            mock_create.return_value = mock_exporter

            result = await start_metrics_server(
                host="0.0.0.0", port=8001, path="/metrics"
            )

            assert result is mock_exporter
            mock_create.assert_called_once_with(
                host="0.0.0.0", port=8001, path="/metrics", enabled=True
            )
            mock_exporter.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_metrics_server_exception(self):
        """Test start_metrics_server with exception."""
        with patch(
            "fapilog.monitoring.create_prometheus_exporter"
        ) as mock_create, patch("fapilog.monitoring.logger") as mock_logger:
            mock_create.side_effect = Exception("Creation failed")

            result = await start_metrics_server()

            assert result is None
            mock_logger.error.assert_called_once()
            assert "Failed to start metrics server" in mock_logger.error.call_args[0][0]

    @pytest.mark.asyncio
    async def test_stop_metrics_server_with_exporter(self):
        """Test stop_metrics_server function."""
        mock_exporter = AsyncMock()
        set_prometheus_exporter(mock_exporter)

        await stop_metrics_server()

        mock_exporter.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_metrics_server_no_exporter(self):
        """Test stop_metrics_server when no exporter exists."""
        set_prometheus_exporter(None)

        await stop_metrics_server()  # Should not raise exception

    def test_get_metrics_text_with_collector(self):
        """Test get_metrics_text when metrics collector exists."""
        # Note: create_metrics_collector was removed in Issue 164
        # get_metrics_text now always returns container-scoped access message
        text = get_metrics_text()

        assert "container-scoped access" in text
        # Legacy behavior no longer applies

    def test_get_metrics_text_no_collector(self):
        """Test get_metrics_text when no metrics collector exists."""
        # Global function now returns container-scoped access message

        text = get_metrics_text()

        assert (
            text == "# Metrics collection is disabled (use container-scoped access)\n"
        )

    def test_get_metrics_text_disabled_collector(self):
        """Test get_metrics_text when metrics collector is disabled."""
        # Global function now returns container-scoped access message

        text = get_metrics_text()

        assert (
            text == "# Metrics collection is disabled (use container-scoped access)\n"
        )

    def test_get_metrics_text_with_exception(self):
        """Test get_metrics_text handling exceptions."""
        # Global function now always returns container-scoped access message
        # Exception handling no longer applies to global functions

        text = get_metrics_text()

        assert (
            text == "# Metrics collection is disabled (use container-scoped access)\n"
        )

    def test_get_metrics_dict_with_collector(self):
        """Test get_metrics_dict when metrics collector exists."""
        # Note: create_metrics_collector was removed in Issue 164
        # get_metrics_dict now always returns container-scoped access message
        metrics = get_metrics_dict()

        assert isinstance(metrics, dict)
        assert "_note" in metrics
        assert "container-scoped access" in metrics["_note"]

    def test_get_metrics_dict_no_collector(self):
        """Test get_metrics_dict when no metrics collector exists."""
        # Global function now returns container-scoped access message

        metrics = get_metrics_dict()

        assert "_note" in metrics
        assert "container-scoped access" in metrics["_note"]

    def test_get_metrics_dict_disabled_collector(self):
        """Test get_metrics_dict when metrics collector is disabled."""
        # Global function now returns container-scoped access message

        metrics = get_metrics_dict()

        assert "_note" in metrics
        assert "container-scoped access" in metrics["_note"]

    def test_get_metrics_dict_with_exception(self):
        """Test get_metrics_dict handling exceptions."""
        # Global function now always returns container-scoped access message
        # Exception handling no longer applies to global functions

        metrics = get_metrics_dict()

        assert "_note" in metrics
        assert "container-scoped access" in metrics["_note"]


if __name__ == "__main__":
    pytest.main([__file__])
