"""Integration tests for complete pure dependency injection system."""

import logging
from unittest.mock import Mock

import pytest
import structlog

from fapilog._internal.queue_integration import create_queue_sink
from fapilog.bootstrap import configure_logging, configure_with_container
from fapilog.container import LoggingContainer
from fapilog.middleware import TraceIDMiddleware
from fapilog.pipeline import build_processor_chain
from fapilog.settings import LoggingSettings


class TestComponentIntegrationPureDI:
    """Test complete system integration with pure dependency injection."""

    def setup_method(self) -> None:
        """Clean up before each test."""
        # Reset structlog
        structlog.reset_defaults()
        # Clear root logger handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Track containers for cleanup
        self._containers_to_cleanup = []

    def teardown_method(self) -> None:
        """Clean up after each test."""
        # Reset structlog
        structlog.reset_defaults()
        # Clear root logger handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    def test_container_pipeline_integration(self) -> None:
        """Test container and pipeline integration with pure DI."""
        settings = LoggingSettings(level="INFO", sinks=["stdout"])
        settings.queue.enabled = False

        # Create container with explicit settings
        container = LoggingContainer.create_from_settings(settings)
        self._containers_to_cleanup.append(container)

        # Configure container (calls build_processor_chain with container)
        logger = container.configure()

        # Verify container is configured
        assert container.is_configured
        assert container.settings.level == "INFO"

        # Verify logger is functional
        assert callable(logger.info)
        logger.info("Test message from pure DI system")

    def test_container_queue_integration(self) -> None:
        """Test container and queue integration with pure DI."""
        settings = LoggingSettings(
            level="INFO",
            sinks=["stdout"],
        )
        settings.queue.enabled = True
        settings.queue.maxsize = 10

        # Create container with queue enabled
        container = LoggingContainer.create_from_settings(settings)
        self._containers_to_cleanup.append(container)

        # Configure container
        logger = container.configure()

        # Verify queue worker is created
        assert container.queue_worker is not None
        assert container.queue_worker.queue.maxsize == 10

        # Verify logger is functional
        assert callable(logger.info)

    def test_queue_sink_pure_di_creation(self) -> None:
        """Test create_queue_sink function with explicit container."""
        settings = LoggingSettings(level="INFO", sinks=["stdout"])
        settings.queue.enabled = True

        # Create container
        container = LoggingContainer.create_from_settings(settings)
        container.configure()

        # Create queue sink with explicit container
        queue_sink = create_queue_sink(container)

        # Verify queue sink is callable
        assert callable(queue_sink)

        # Test queue sink behavior
        test_event = {"event": "test message", "level": "info"}

        # Queue sink should raise DropEvent when queuing
        with pytest.raises(structlog.DropEvent):
            queue_sink(Mock(), "info", test_event)

    def test_pipeline_container_integration(self) -> None:
        """Test pipeline build_processor_chain with container parameter."""
        settings = LoggingSettings(level="INFO", sinks=["stdout"])
        settings.queue.enabled = True

        # Create container
        container = LoggingContainer.create_from_settings(settings)
        container.configure()

        # Build processor chain with container
        processors = build_processor_chain(
            settings=settings, pretty=False, container=container
        )

        # Verify processors were created
        assert len(processors) > 0

        # The last processor should be the queue sink when queue_enabled=True
        assert callable(processors[-1])

    def test_pipeline_without_container_fallback(self) -> None:
        """Test pipeline falls back gracefully without container."""
        settings = LoggingSettings(level="INFO", sinks=["stdout"])
        settings.queue.enabled = True

        # Build processor chain without container (legacy mode)
        processors = build_processor_chain(
            settings=settings, pretty=False, container=None
        )

        # Verify processors were created
        assert len(processors) > 0

        # Should still create processors (with legacy queue sink)
        assert callable(processors[-1])

    def test_multiple_isolated_containers(self) -> None:
        """Test multiple containers with complete isolation."""
        # Create multiple containers with different settings
        settings1 = LoggingSettings(level="INFO")
        settings1.queue.enabled = False
        settings2 = LoggingSettings(level="DEBUG")
        settings2.queue.enabled = True
        settings3 = LoggingSettings(level="WARNING")
        settings3.queue.enabled = False

        containers = [
            LoggingContainer.create_from_settings(settings1),
            LoggingContainer.create_from_settings(settings2),
            LoggingContainer.create_from_settings(settings3),
        ]

        # Configure all containers
        loggers = []
        for container in containers:
            loggers.append(container.configure())

        # Verify complete isolation
        assert containers[0].settings.level == "INFO"
        assert containers[1].settings.level == "DEBUG"
        assert containers[2].settings.level == "WARNING"

        assert containers[0].settings.queue.enabled is False
        assert containers[1].settings.queue.enabled is True
        assert containers[2].settings.queue.enabled is False

        # Only container 1 should have queue worker
        assert containers[0].queue_worker is None
        assert containers[1].queue_worker is not None
        assert containers[2].queue_worker is None

        # All loggers should be functional
        for logger in loggers:
            assert callable(logger.info)

    def test_bootstrap_container_integration(self) -> None:
        """Test bootstrap integration with pure DI containers."""
        # Test basic configure_logging
        logger1 = configure_logging(LoggingSettings(level="INFO"))
        assert callable(logger1.info)

        # Test configure_with_container
        bootstrap_settings = LoggingSettings(level="DEBUG")
        bootstrap_settings.queue.enabled = True
        logger2, container = configure_with_container(bootstrap_settings)

        assert callable(logger2.info)
        assert isinstance(container, LoggingContainer)
        assert container.is_configured
        assert container.queue_worker is not None

    def test_middleware_integration(self) -> None:
        """Test middleware integration with pure DI logging."""
        # Create mock ASGI app
        mock_app = Mock()

        # Create middleware
        middleware = TraceIDMiddleware(mock_app, trace_id_header="X-Request-ID")

        # Verify middleware was created successfully
        assert middleware.trace_id_header == "X-Request-ID"
        assert middleware.app is mock_app

    @pytest.mark.asyncio
    async def test_async_integration_with_pure_di(self) -> None:
        """Test async integration with pure dependency injection."""
        settings = LoggingSettings(
            level="INFO",
            sinks=["stdout"],
        )
        settings.queue.enabled = True
        settings.metrics.enabled = True

        # Create container
        container = LoggingContainer.create_from_settings(settings)

        # Configure container
        logger = container.configure()

        # Setup async components
        await container.setup()

        # Test logging in async context
        logger.info("Async test message", task="integration_test")

        # Cleanup
        await container.shutdown()

    def test_end_to_end_logging_flow(self) -> None:
        """Test complete end-to-end logging flow with pure DI."""
        # Create settings for comprehensive test
        settings = LoggingSettings(
            level="INFO",
            sinks=["stdout"],
            security={
                "enable_auto_redact_pii": True,
                "enable_throttling": False,  # Disable for testing
                "enable_deduplication": False,  # Disable for testing
            },
            user_context_enabled=True,
            enable_resource_metrics=True,
        )
        settings.queue.enabled = False  # Use synchronous for easier testing

        # Create and configure container
        container = LoggingContainer.create_from_settings(settings)
        logger = container.configure()

        # Test various log levels
        logger.debug("Debug message")  # Should be filtered out (level=INFO)
        logger.info("Info message", user_id="12345", action="test")
        logger.warning("Warning message", component="integration_test")
        logger.error("Error message", error_code=500)

        # Verify container state
        assert container.is_configured
        assert container.queue_worker is None  # No queue
        assert container.settings.security.enable_auto_redact_pii is True

    def test_concurrent_container_operations(self) -> None:
        """Test concurrent operations with multiple containers."""
        import threading
        import time

        results = {}

        def container_worker(worker_id: int) -> None:
            """Worker function for concurrent container testing."""
            settings = LoggingSettings(
                level="INFO",
                sinks=["stdout"],
            )
            # Alternate queue enabled status based on worker_id
            settings.queue.enabled = worker_id % 2 == 0

            # Create and configure container
            container = LoggingContainer.create_from_settings(settings)
            logger = container.configure()

            # Simulate some work
            time.sleep(0.1)

            # Log a message
            logger.info(f"Message from worker {worker_id}")

            results[worker_id] = {
                "configured": container.is_configured,
                "has_queue": container.queue_worker is not None,
                "queue_enabled": settings.queue.enabled,
            }

        # Create and start threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=container_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all workers completed successfully
        assert len(results) == 5
        for i, result in results.items():
            assert result["configured"] is True
            expected_queue = i % 2 == 0
            assert result["has_queue"] == expected_queue
            assert result["queue_enabled"] == expected_queue

    def test_system_without_global_state(self) -> None:
        """Test that the complete system operates without global state."""
        # Create multiple containers
        containers = []
        loggers = []

        for i in range(3):
            settings = LoggingSettings(
                level=["DEBUG", "INFO", "WARNING"][i],
                sinks=["stdout"],
            )
            settings.queue.enabled = i == 1  # Only middle container has queue
            container = LoggingContainer.create_from_settings(settings)
            logger = container.configure()

            containers.append(container)
            loggers.append(logger)

        # Verify no global state dependencies by checking module attributes
        import fapilog._internal.queue_integration as queue_module
        import fapilog.bootstrap as bootstrap_module
        import fapilog.container as container_module

        # Container module should not have global container functions
        assert not hasattr(container_module, "get_current_container")
        assert not hasattr(container_module, "set_current_container")
        assert not hasattr(container_module, "cleanup_all_containers")

        # Bootstrap should be stateless (no global container registry)
        assert not hasattr(bootstrap_module, "_active_containers")
        assert hasattr(bootstrap_module, "configure_logging")
        assert hasattr(bootstrap_module, "create_logger")

        # Queue integration should have pure DI functions
        assert hasattr(queue_module, "create_queue_sink")

        # All containers should work independently
        for i, (container, logger) in enumerate(zip(containers, loggers)):
            logger.info(f"Test message from container {i}")
            assert container.is_configured

    def test_fastapi_integration_simulation(self) -> None:
        """Test simulated FastAPI integration with pure DI."""
        # Mock FastAPI app
        mock_app = Mock()
        mock_app.add_middleware = Mock()
        mock_app.add_event_handler = Mock()

        # Configure logging with app integration
        settings = LoggingSettings(level="INFO", sinks=["stdout"])
        settings.queue.enabled = True

        logger = configure_logging(settings=settings, app=mock_app)

        # Verify middleware was registered
        mock_app.add_middleware.assert_called_once()

        # Verify logger is functional
        assert callable(logger.info)
        logger.info("FastAPI integration test", endpoint="/test")

    def test_error_handling_isolation(self) -> None:
        """Test that errors in one container don't affect others."""
        # Create a good container
        good_container = LoggingContainer.create_from_settings(
            LoggingSettings(level="INFO", sinks=["stdout"])
        )
        good_logger = good_container.configure()

        # Create a container and simulate an error
        error_container = LoggingContainer.create_from_settings(
            LoggingSettings(level="INFO", sinks=["stdout"])
        )
        error_container.configure()

        # Simulate error in one container (by resetting it)
        error_container.reset()

        # Good container should still work
        assert good_container.is_configured
        good_logger.info("This should work fine")

        # Error container should be reset
        assert not error_container.is_configured
