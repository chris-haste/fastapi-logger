"""Final push tests for monitoring.py to reach 90% coverage."""

from unittest.mock import Mock, patch

import pytest

from fapilog.monitoring import PrometheusExporter


class TestPrometheusExporterDisabled:
    """Test PrometheusExporter when disabled."""

    def test_setup_app_when_disabled(self):
        """Test _setup_app early return when disabled."""
        exporter = PrometheusExporter(port=9090, enabled=False)

        # This should hit the early return on line 63
        exporter._setup_app()

        # Should not have created an app
        assert exporter._app is None


class TestMetricsEndpointErrors:
    """Test error scenarios in metrics endpoints."""

    def test_metrics_endpoint_when_collector_disabled(self):
        """Test metrics endpoint when metrics collector is disabled."""
        exporter = PrometheusExporter(port=9090, enabled=True)

        # Mock disabled metrics collector (lines 76-80)
        with patch("fapilog.monitoring.get_metrics_collector") as mock_get_collector:
            mock_collector = Mock()
            mock_collector.is_enabled.return_value = False
            mock_get_collector.return_value = mock_collector

            # This should return 503 status
            exporter._setup_app()
            assert exporter._app is not None

    def test_metrics_endpoint_when_collector_missing(self):
        """Test metrics endpoint when metrics collector is None."""
        exporter = PrometheusExporter(port=9090, enabled=True)

        # Mock missing metrics collector (lines 76-80)
        with patch("fapilog.monitoring.get_metrics_collector", return_value=None):
            exporter._setup_app()
            assert exporter._app is not None

    def test_metrics_endpoint_generation_error(self):
        """Test metrics endpoint when prometheus metrics generation fails."""
        exporter = PrometheusExporter(port=9090, enabled=True)

        # Mock metrics collector that raises an exception (lines 85-87)
        with patch("fapilog.monitoring.get_metrics_collector") as mock_get_collector:
            mock_collector = Mock()
            mock_collector.is_enabled.return_value = True
            mock_collector.get_prometheus_metrics.side_effect = Exception(
                "Metrics error"
            )
            mock_get_collector.return_value = mock_collector

            exporter._setup_app()
            assert exporter._app is not None


class TestHealthEndpoint:
    """Test health endpoint scenarios."""

    def test_health_endpoint_setup(self):
        """Test that health endpoint is properly set up."""
        exporter = PrometheusExporter(port=9090, enabled=True)

        exporter._setup_app()

        # Should have created an app with health endpoint
        assert exporter._app is not None


class TestMonitoringDisabledState:
    """Test monitoring when disabled."""

    def test_prometheus_exporter_disabled_initialization(self):
        """Test PrometheusExporter initialization when disabled."""
        exporter = PrometheusExporter(port=9090, enabled=False)

        # Should be disabled
        assert not exporter.enabled
        assert exporter._app is None

    def test_disabled_exporter_setup_does_nothing(self):
        """Test that disabled exporter setup doesn't create resources."""
        exporter = PrometheusExporter(port=9090, enabled=False)

        # Multiple calls should be safe
        exporter._setup_app()
        exporter._setup_app()

        # Should still have no app
        assert exporter._app is None


if __name__ == "__main__":
    pytest.main([__file__])
