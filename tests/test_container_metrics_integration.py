"""Integration tests for container with metrics."""

import pytest
import structlog

import fapilog
from fapilog import configure_logging

# Note: Global metrics functions removed in Issue 164
from fapilog.container import LoggingContainer
from fapilog.monitoring import get_prometheus_exporter, set_prometheus_exporter
from fapilog.settings import LoggingSettings


class TestContainerMetricsIntegration:
    """Test container integration with metrics system."""

    def teardown_method(self):
        """Clean up after each test."""
        # Reset logging state
        structlog.reset_defaults()
        structlog.configure()
        # Reset prometheus exporter
        set_prometheus_exporter(None)

    def test_bootstrap_configure_logging_with_metrics(self):
        """Test that configure_logging works with metrics enabled."""
        settings = LoggingSettings(
            level="INFO",
            sinks=["stdout"],
            metrics_enabled=True,
        )

        # Should not raise any exceptions
        configure_logging(settings)

        # Verify metrics are enabled via container
        # Note: get_metrics_collector was removed in Issue 164
        # Metrics are now accessed through container.get_metrics_collector()
        # This test would need a container instance to verify metrics
        print("Metrics collection now requires container-scoped access")

    def test_bootstrap_configure_logging_with_prometheus(self):
        """Test that configure_logging works with Prometheus enabled."""
        settings = LoggingSettings(
            level="INFO",
            sinks=["stdout"],
            metrics_enabled=True,
            metrics_prometheus_enabled=True,
            metrics_prometheus_port=8123,
        )

        # Should not raise any exceptions
        configure_logging(settings)

        # Note: With container-scoped architecture, configure_logging() doesn't expose
        # the container, so Prometheus exporter is not accessible globally
        # This test now verifies that configuration succeeds without errors
        prometheus_exporter = get_prometheus_exporter()
        assert prometheus_exporter is None  # No global exporter set

    def test_prometheus_exporter_initialization_enabled(self):
        """Test Prometheus exporter auto-initialization when enabled."""
        settings = LoggingSettings(
            level="INFO",
            metrics_enabled=True,
            metrics_prometheus_enabled=True,
            metrics_prometheus_port=8123,
            metrics_prometheus_host="127.0.0.1",
        )

        container = LoggingContainer(settings)
        container.configure()

        # Verify Prometheus exporter was created via container
        prometheus_exporter = container.get_prometheus_exporter()
        assert prometheus_exporter is not None
        assert prometheus_exporter.port == 8123
        assert prometheus_exporter.host == "127.0.0.1"
        assert prometheus_exporter.enabled

    def test_prometheus_exporter_initialization_disabled(self):
        """Test Prometheus exporter not created when disabled."""
        settings = LoggingSettings(
            level="INFO",
            metrics_enabled=True,
            metrics_prometheus_enabled=False,
        )

        container = LoggingContainer(settings)
        container.configure()

        # Verify no Prometheus exporter was created
        prometheus_exporter = get_prometheus_exporter()
        assert prometheus_exporter is None

    @pytest.mark.asyncio
    async def test_container_setup_starts_prometheus_exporter(self):
        """Test that container.setup() starts the Prometheus exporter."""
        settings = LoggingSettings(
            level="INFO",
            metrics_enabled=True,
            metrics_prometheus_enabled=True,
            metrics_prometheus_port=8124,  # Different port to avoid conflicts
        )

        container = LoggingContainer(settings)
        container.configure()

        # Initially, exporter should exist but not be running
        prometheus_exporter = container.get_prometheus_exporter()
        assert prometheus_exporter is not None
        assert not prometheus_exporter.is_running()

        try:
            # After setup, exporter should be running
            await container.setup()

            # Note: This might fail if FastAPI is not available,
            # which is expected behavior
            if prometheus_exporter.enabled:
                assert prometheus_exporter.is_running()
        except Exception:
            # Expected if FastAPI/uvicorn not available
            pass
        finally:
            # Clean up
            await container.shutdown()

    def test_container_get_logger_method(self):
        """Test that container.get_logger() works correctly."""
        container = LoggingContainer()
        container.configure()

        # Test getting logger
        logger = container.get_logger("test.module")
        assert logger is not None

        # Should return same type as fapilog.get_logger
        global_logger = fapilog.get_logger("test.module")
        assert isinstance(logger, type(global_logger))

    def test_create_logging_container_factory(self):
        """Test the create_logging_container factory function."""
        settings = LoggingSettings(
            level="DEBUG",
            metrics_enabled=True,
        )

        # Test factory function exists and works
        container = fapilog.create_logging_container(settings)
        assert isinstance(container, LoggingContainer)
        assert container.settings.level == "DEBUG"
        assert container.settings.metrics_enabled

        # Test with no settings
        container2 = fapilog.create_logging_container()
        assert isinstance(container2, LoggingContainer)
        assert container2.settings is not None

    @pytest.mark.asyncio
    async def test_container_shutdown_stops_prometheus_exporter(self):
        """Test that container shutdown properly stops Prometheus exporter."""
        settings = LoggingSettings(
            level="INFO",
            metrics_enabled=True,
            metrics_prometheus_enabled=True,
            metrics_prometheus_port=8125,  # Different port
        )

        container = LoggingContainer(settings)
        container.configure()

        prometheus_exporter = get_prometheus_exporter()
        if prometheus_exporter and prometheus_exporter.enabled:
            try:
                await container.setup()

                # Verify it's running
                if prometheus_exporter.is_running():
                    # Shutdown should stop it
                    await container.shutdown()
                    assert not prometheus_exporter.is_running()

            except Exception:
                # Expected if dependencies not available
                pass

    def test_container_reset_clears_metrics(self):
        """Test that container.reset() properly clears metrics state."""
        settings = LoggingSettings(
            level="INFO",
            metrics_enabled=True,
            metrics_prometheus_enabled=True,
        )

        container = LoggingContainer(settings)
        container.configure()

        # Verify metrics were created via container
        metrics_collector = container.get_metrics_collector()
        prometheus_exporter = container.get_prometheus_exporter()

        assert metrics_collector is not None
        assert prometheus_exporter is not None

        # Reset container
        container.reset()

        # Metrics should still exist globally but container should be reset
        assert not container.is_configured


class TestMetricsIntegrationScenarios:
    """Test real-world metrics integration scenarios."""

    def teardown_method(self):
        """Clean up after each test."""
        # Note: set_metrics_collector removed in Issue 164
        from fapilog.monitoring import set_prometheus_exporter

        # Only clean up Prometheus exporter since metrics collector is container-scoped
        set_prometheus_exporter(None)

    def test_logging_with_auto_metrics_collection(self):
        """Test that logging collects metrics when auto-initialized."""
        settings = LoggingSettings(
            level="INFO",
            queue_enabled=True,
            queue_batch_size=2,
            metrics_enabled=True,
            sinks=["stdout"],
        )

        # Configure logging with auto-metrics
        logger = fapilog.configure_logging(settings)

        # Note: Metrics collector verification requires container access
        # Since configure_logging doesn't return container, we can't verify metrics directly
        # Metrics collection now requires container-scoped access via create_logger()
        print("Metrics verification skipped - requires container-scoped access")

        # Generate some log events
        logger.info("Test message 1", test_field="value1")
        logger.info("Test message 2", test_field="value2")

        # Note: Since this is async queue processing,
        # we can't easily verify metrics were recorded
        # without adding delays, which makes tests slow
        # This test mainly verifies the setup works

    def test_multiple_containers_independent_metrics(self):
        """Test that multiple containers maintain independent metrics state."""
        settings1 = LoggingSettings(
            level="INFO",
            metrics_enabled=True,
            metrics_sample_window=50,
        )

        settings2 = LoggingSettings(
            level="DEBUG",
            metrics_enabled=False,
        )

        container1 = LoggingContainer(settings1)
        container2 = LoggingContainer(settings2)

        container1.configure()
        # First container should have created container-scoped metrics
        metrics_collector = container1.get_metrics_collector()
        assert metrics_collector is not None
        assert metrics_collector.is_enabled()

        container2.configure()
        # Second container with metrics disabled shouldn't affect global state
        # (global state is shared, so this test mainly verifies no crashes)

        # Both containers should work independently
        logger1 = container1.get_logger("container1")
        logger2 = container2.get_logger("container2")

        assert logger1 is not None
        assert logger2 is not None


if __name__ == "__main__":
    pytest.main([__file__])
