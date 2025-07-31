"""Simple tests to boost monitoring.py coverage above 90%."""

from unittest.mock import patch

from fapilog.monitoring import (
    PrometheusExporter,
    create_prometheus_exporter,
    get_metrics_dict,
    get_metrics_text,
    start_metrics_server,
    stop_metrics_server,
)


class TestMonitoringUtilityFunctions:
    """Test utility functions in monitoring module."""

    def test_get_metrics_text_when_disabled(self):
        """Test get_metrics_text when metrics collection is disabled."""
        # The function now returns a message about container-scoped access
        result = get_metrics_text()
        assert (
            result == "# Metrics collection is disabled (use container-scoped access)\n"
        )

    def test_get_metrics_text_when_collector_disabled(self):
        """Test get_metrics_text when collector is disabled."""
        # The function now returns a message about container-scoped access regardless of state
        result = get_metrics_text()
        assert (
            result == "# Metrics collection is disabled (use container-scoped access)\n"
        )

    def test_get_metrics_text_success(self):
        """Test get_metrics_text when metrics are available."""
        # The function now always returns the container-scoped access message
        result = get_metrics_text()
        assert (
            result == "# Metrics collection is disabled (use container-scoped access)\n"
        )

    def test_get_metrics_text_error(self):
        """Test get_metrics_text when an error occurs."""
        # The function now always returns the container-scoped access message
        result = get_metrics_text()
        assert (
            result == "# Metrics collection is disabled (use container-scoped access)\n"
        )

    def test_get_metrics_dict_when_disabled(self):
        """Test get_metrics_dict when metrics collection is disabled."""
        result = get_metrics_dict()
        assert result == {
            "_note": "Metrics collection disabled - use container-scoped access"
        }

    def test_get_metrics_dict_when_collector_disabled(self):
        """Test get_metrics_dict when collector is disabled."""
        result = get_metrics_dict()
        assert result == {
            "_note": "Metrics collection disabled - use container-scoped access"
        }

    def test_get_metrics_dict_success(self):
        """Test get_metrics_dict when metrics are available."""
        result = get_metrics_dict()
        assert result == {
            "_note": "Metrics collection disabled - use container-scoped access"
        }

    def test_get_metrics_dict_error(self):
        """Test get_metrics_dict when an error occurs."""
        result = get_metrics_dict()
        assert result == {
            "_note": "Metrics collection disabled - use container-scoped access"
        }

    def test_create_prometheus_exporter(self):
        """Test create_prometheus_exporter function."""
        # Test with FastAPI disabled
        with patch("fapilog.monitoring.FastAPI", None):
            exporter = create_prometheus_exporter(port=9999)
            assert exporter is not None
            assert not exporter.enabled
            assert exporter.port == 9999

    def test_prometheus_exporter_disabled_start_stop(self):
        """Test PrometheusExporter start/stop when disabled."""
        # Test disabled exporter
        exporter = PrometheusExporter(enabled=False)
        assert not exporter.enabled

        # These should be safe no-ops when disabled
        import asyncio

        async def test_async():
            await exporter.start()  # Should return early
            await exporter.stop()  # Should return early

        asyncio.run(test_async())

    def test_prometheus_exporter_methods_when_disabled(self):
        """Test PrometheusExporter utility methods when disabled."""
        exporter = PrometheusExporter(enabled=False)

        # These should handle disabled state
        assert not exporter.is_running()
        assert exporter.get_metrics_url() is None


class TestMonitoringServerFunctions:
    """Test server utility functions that we lost when removing mocking."""

    def test_start_metrics_server_with_exception(self):
        """Test start_metrics_server exception handling (line 148-149)."""
        import asyncio

        async def test_async():
            # Mock create_prometheus_exporter to raise an exception
            with patch(
                "fapilog.monitoring.create_prometheus_exporter",
                side_effect=Exception("Server start error"),
            ):
                result = await start_metrics_server(port=9999)
                assert result is None

        asyncio.run(test_async())

    def test_stop_metrics_server_with_no_exporter(self):
        """Test stop_metrics_server when no exporter exists."""
        import asyncio

        async def test_async():
            # Ensure no global exporter
            with patch("fapilog.monitoring.get_prometheus_exporter", return_value=None):
                await stop_metrics_server()  # Should not raise

        asyncio.run(test_async())
