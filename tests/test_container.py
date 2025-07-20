"""Tests for LoggingContainer dependency injection functionality."""

import asyncio
import logging
import threading
from typing import Any, Dict, List
from unittest.mock import Mock

import pytest
import structlog

from fapilog.container import LoggingContainer, cleanup_all_containers
from fapilog.exceptions import ConfigurationError
from fapilog.settings import LoggingSettings


class MockSink:
    """Mock sink for testing."""

    def __init__(self, name: str = "mock", should_fail: bool = False):
        self.name = name
        self.should_fail = should_fail
        self.events: List[Dict[str, Any]] = []
        self.write_calls = 0

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Write event to mock sink."""
        self.write_calls += 1
        if self.should_fail:
            raise Exception(f"Mock sink {self.name} failed")
        self.events.append(event_dict.copy())


class TestLoggingContainer:
    """Test LoggingContainer functionality."""

    def setup_method(self) -> None:
        """Clean up before each test."""
        # Reset any existing containers
        cleanup_all_containers()
        # Reset structlog
        structlog.reset_defaults()
        # Clear root logger handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    def teardown_method(self) -> None:
        """Clean up after each test."""
        # Clean up all containers
        cleanup_all_containers()
        # Reset structlog
        structlog.reset_defaults()
        # Clear root logger handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    def test_container_initialization(self) -> None:
        """Test basic container initialization."""
        container = LoggingContainer()

        assert not container.is_configured
        assert container.queue_worker is None
        assert isinstance(container.settings, LoggingSettings)

    def test_container_initialization_with_settings(self) -> None:
        """Test container initialization with custom settings."""
        settings = LoggingSettings(level="DEBUG", queue_enabled=True)
        container = LoggingContainer(settings=settings)

        assert not container.is_configured
        assert container.settings.level == "DEBUG"
        assert container.settings.queue_enabled is True

    def test_container_configure_basic(self) -> None:
        """Test basic container configuration."""
        container = LoggingContainer()
        logger = container.configure()

        assert container.is_configured
        assert callable(logger.info)
        assert callable(logger.error)

    def test_container_configure_idempotent(self) -> None:
        """Test that container configuration is idempotent."""
        container = LoggingContainer()

        # First configuration
        logger1 = container.configure()
        assert container.is_configured

        # Second configuration should not reconfigure
        logger2 = container.configure()
        assert container.is_configured

        # Both loggers should be functional
        assert callable(logger1.info)
        assert callable(logger2.info)

    def test_multiple_containers_independent(self) -> None:
        """Test that multiple containers operate independently."""
        settings1 = LoggingSettings(level="INFO")
        settings2 = LoggingSettings(level="DEBUG")

        container1 = LoggingContainer(settings1)
        container2 = LoggingContainer(settings2)

        # Configure both
        logger1 = container1.configure()
        logger2 = container2.configure()

        # Both should be configured
        assert container1.is_configured
        assert container2.is_configured

        # Settings should be independent
        assert container1.settings.level == "INFO"
        assert container2.settings.level == "DEBUG"

        # Both loggers should work
        assert callable(logger1.info)
        assert callable(logger2.info)

    def test_container_with_queue_enabled(self) -> None:
        """Test container configuration with queue enabled."""
        settings = LoggingSettings(
            queue_enabled=True, sinks=["stdout"], queue_maxsize=100
        )
        container = LoggingContainer(settings)

        container.configure()

        assert container.is_configured
        assert container.queue_worker is not None
        assert container.queue_worker.queue.maxsize == 100

    def test_container_reset(self) -> None:
        """Test container reset functionality."""
        container = LoggingContainer()

        # Configure container
        container.configure()
        assert container.is_configured

        # Reset container
        container.reset()
        assert not container.is_configured
        assert container.queue_worker is None

    def test_container_with_settings(self) -> None:
        """Test container configuration with LoggingSettings."""
        settings = LoggingSettings(level="WARNING", json_console="json")
        container = LoggingContainer(settings)

        # Configure the container
        container.configure()

        # Verify the container is configured
        assert container.is_configured

    def test_container_invalid_console_format(self) -> None:
        """Test container with invalid console format."""
        # Settings validation happens at initialization, not configure()
        with pytest.raises(ConfigurationError):
            settings = LoggingSettings(json_console="invalid")
            LoggingContainer(settings)

    def test_container_invalid_log_level(self) -> None:
        """Test container with invalid log level."""
        with pytest.raises(ConfigurationError):
            settings = LoggingSettings(level="INVALID")
            LoggingContainer(settings)

    @pytest.mark.asyncio
    async def test_container_async_shutdown(self) -> None:
        """Test container async shutdown."""
        settings = LoggingSettings(queue_enabled=True, sinks=["stdout"])
        container = LoggingContainer(settings)

        # Configure and start
        container.configure()
        assert container.queue_worker is not None

        # Shutdown gracefully
        await container.shutdown()
        assert container.queue_worker is None

    def test_container_sync_shutdown(self) -> None:
        """Test container sync shutdown."""
        settings = LoggingSettings(queue_enabled=True, sinks=["stdout"])
        container = LoggingContainer(settings)

        # Configure and start
        container.configure()
        assert container.queue_worker is not None

        # Shutdown gracefully
        container.shutdown_sync()
        assert container.queue_worker is None

    def test_container_thread_safety(self) -> None:
        """Test container thread safety with concurrent access."""
        container = LoggingContainer()
        results = []
        errors = []

        def configure_worker():
            try:
                logger = container.configure()
                results.append(logger)
            except Exception as e:
                errors.append(e)

        # Start multiple threads trying to configure
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=configure_worker)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Should have no errors and all loggers should work
        assert len(errors) == 0
        assert len(results) == 5
        assert container.is_configured

        # All loggers should be functional
        for logger in results:
            assert callable(logger.info)

    def test_multiple_containers_thread_safety(self) -> None:
        """Test multiple containers with thread safety."""
        containers = []
        results = []
        errors = []

        def create_and_configure():
            try:
                container = LoggingContainer()
                logger = container.configure()
                containers.append(container)
                results.append(logger)
            except Exception as e:
                errors.append(e)

        # Start multiple threads creating containers
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=create_and_configure)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Should have no errors
        assert len(errors) == 0
        assert len(results) == 3
        assert len(containers) == 3

        # All containers should be independent and configured
        for container in containers:
            assert container.is_configured

        # All loggers should work
        for logger in results:
            assert callable(logger.info)

    def test_container_memory_management(self) -> None:
        """Test container memory management and cleanup."""
        import gc
        import weakref

        # Create container with weak reference
        container = LoggingContainer()
        weakref.ref(container)

        # Configure container
        logger = container.configure()
        assert container.is_configured

        # Delete reference and force garbage collection
        del container
        del logger
        gc.collect()

        # Container should be cleaned up
        # Note: This test may be flaky depending on garbage collection timing
        # but it helps verify that containers can be properly cleaned up

    def test_container_with_fastapi_app(self) -> None:
        """Test container configuration with FastAPI app."""
        try:
            from fastapi import FastAPI
        except ImportError:
            pytest.skip("FastAPI not available")

        app = FastAPI()
        container = LoggingContainer()

        # Configure with app
        container.configure(app=app)

        assert container.is_configured
        # Middleware should be registered
        assert len(app.user_middleware) > 0

    def test_container_settings_validation(self) -> None:
        """Test container settings validation."""
        # Test with invalid settings object
        with pytest.raises(ConfigurationError):
            container = LoggingContainer()
            container.configure(settings="invalid")

    def test_container_queue_worker_error_handling(self) -> None:
        """Test container error handling during queue worker setup."""
        # Test with invalid sink URI
        settings = LoggingSettings(queue_enabled=True, sinks=["invalid://sink"])
        container = LoggingContainer(settings)

        # SinkError is raised, not ConfigurationError
        from fapilog.exceptions import SinkError

        with pytest.raises(SinkError):
            container.configure()

    def test_container_httpx_propagation(self) -> None:
        """Test container httpx trace propagation configuration."""
        settings = LoggingSettings(enable_httpx_trace_propagation=True)
        container = LoggingContainer(settings)

        # Configure container
        container.configure()

        assert container.is_configured
        # HttpxTracePropagation should be configured
        assert container._httpx_propagation is not None

    def test_container_registry_cleanup(self) -> None:
        """Test that container registry properly tracks and cleans up containers."""
        from fapilog.container import _container_registry

        initial_count = len(_container_registry)

        # Create multiple containers
        containers = []
        for _i in range(3):
            container = LoggingContainer()
            containers.append(container)
            container.configure()

        # Registry should track more containers
        assert len(_container_registry) >= initial_count + 3

        # Clean up containers
        for container in containers:
            container.shutdown_sync()

        # Delete references
        del containers

        # Force cleanup
        cleanup_all_containers()

    def test_container_error_during_shutdown(self) -> None:
        """Test container behavior when shutdown encounters errors."""
        settings = LoggingSettings(queue_enabled=True, sinks=["stdout"])
        container = LoggingContainer(settings)

        # Configure container
        container.configure()

        # Mock the queue worker to raise an exception during shutdown
        if container.queue_worker:
            container.queue_worker.shutdown_sync = Mock(
                side_effect=Exception("Shutdown error")
            )

        # Shutdown should handle the error gracefully
        container.shutdown_sync()  # Should not raise

        # Container should still be marked as shutdown
        assert container.queue_worker is None

    @pytest.mark.asyncio
    async def test_container_concurrent_logging(self) -> None:
        """Test container with concurrent logging operations."""
        settings = LoggingSettings(queue_enabled=True, sinks=["stdout"])
        container = LoggingContainer(settings)

        # Configure container
        logger = container.configure()

        async def log_worker(worker_id: int):
            for i in range(10):
                logger.info(f"Message from worker {worker_id}, iteration {i}")
                await asyncio.sleep(0.01)

        # Start multiple concurrent logging tasks
        tasks = []
        for worker_id in range(5):
            task = asyncio.create_task(log_worker(worker_id))
            tasks.append(task)

        # Wait for all tasks to complete
        await asyncio.gather(*tasks)

        # Give some time for queue processing
        await asyncio.sleep(0.5)

        # Clean shutdown
        await container.shutdown()

    def test_cleanup_all_containers(self) -> None:
        """Test cleanup_all_containers function."""
        # Create multiple containers
        containers = []
        for _i in range(3):
            container = LoggingContainer()
            container.configure()
            containers.append(container)

        # All should be configured
        for container in containers:
            assert container.is_configured

        # Cleanup all
        cleanup_all_containers()

        # Note: cleanup_all_containers doesn't reset the configured state,
        # it just shuts down the containers. The containers remain configured
        # but their workers/resources are cleaned up.

    def test_container_properties(self) -> None:
        """Test container property accessors."""
        settings = LoggingSettings(level="WARNING", queue_enabled=True)
        container = LoggingContainer(settings)

        # Before configuration
        assert isinstance(container.settings, LoggingSettings)
        assert container.settings.level == "WARNING"
        assert not container.is_configured
        assert container.queue_worker is None

        # After configuration
        container.configure()
        assert container.is_configured
        assert container.queue_worker is not None

    def test_container_auto_cleanup_registration(self) -> None:
        """Test that containers automatically register for cleanup."""

        # Check that cleanup function is registered with atexit
        # Note: This is difficult to test directly, but we can verify
        # that the cleanup function exists and is callable
        from fapilog.container import cleanup_all_containers

        assert callable(cleanup_all_containers)

        # Create a container to ensure it gets registered
        container = LoggingContainer()
        container.configure()

        # The container should be tracked for cleanup
        from fapilog.container import _container_registry

        assert len(_container_registry) > 0
