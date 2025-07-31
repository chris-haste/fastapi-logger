"""Integration tests for multiple container isolation.

This module provides comprehensive integration tests to validate that multiple
LoggingContainer instances operate with perfect isolation, preventing any
component state interference between containers.

Tests validate:
- Multi-container test framework functionality
- Component isolation between containers
- Concurrent container operations
- Container lifecycle and cleanup isolation
- Memory management and leak prevention
"""

import gc
import threading
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from typing import Any, List, Optional

import pytest

from fapilog._internal.async_lock_manager import ProcessorLockManager
from fapilog._internal.metrics import MetricsCollector
from fapilog._internal.processor_metrics import ProcessorMetrics
from fapilog.container import LoggingContainer
from fapilog.monitoring import PrometheusExporter
from fapilog.settings import LoggingSettings


class ContainerIsolationTestFramework:
    """Test framework for creating and managing multiple LoggingContainer instances.

    Provides utilities for:
    - Container creation and management
    - Component isolation verification
    - Concurrent operation testing
    - Cleanup isolation validation
    - Memory leak detection
    """

    def __init__(self):
        """Initialize the test framework."""
        self._created_containers: List[LoggingContainer] = []
        self._lock = threading.Lock()

    def create_containers(
        self, count: int, settings_list: Optional[List[LoggingSettings]] = None
    ) -> List[LoggingContainer]:
        """Create multiple containers with isolation.

        Args:
            count: Number of containers to create
            settings_list: Optional list of settings for each container

        Returns:
            List of LoggingContainer instances
        """
        containers = []

        if settings_list and len(settings_list) != count:
            raise ValueError("settings_list length must match count")

        for i in range(count):
            if settings_list:
                settings = settings_list[i]
            else:
                # Create varied settings for isolation testing
                settings = LoggingSettings(
                    level="DEBUG" if i % 2 == 0 else "INFO",
                    queue_enabled=i % 3 == 0,
                    metrics_enabled=i % 2 == 1,
                    metrics_prometheus_enabled=i % 4 == 0,
                    metrics_sample_window=100 + (i * 50),
                )

            container = LoggingContainer(settings)
            containers.append(container)

            with self._lock:
                self._created_containers.append(container)

        return containers

    def verify_component_isolation(self, containers: List[LoggingContainer]) -> None:
        """Verify that all components are isolated between containers.

        Args:
            containers: List of containers to verify

        Raises:
            AssertionError: If any component isolation is violated
        """
        if len(containers) < 2:
            raise ValueError("Need at least 2 containers for isolation testing")

        # Configure all containers first
        for container in containers:
            container.configure()

        # Test ProcessorLockManager isolation
        lock_managers = [container.get_lock_manager() for container in containers]
        self._verify_unique_instances(lock_managers, "ProcessorLockManager")

        # Test ProcessorMetrics isolation
        processor_metrics = [
            container.get_processor_metrics() for container in containers
        ]
        self._verify_unique_instances(processor_metrics, "ProcessorMetrics")

        # Test MetricsCollector isolation (when enabled)
        metrics_collectors = []
        for container in containers:
            collector = container.get_metrics_collector()
            if collector is not None:
                metrics_collectors.append(collector)
        if metrics_collectors:
            self._verify_unique_instances(metrics_collectors, "MetricsCollector")

        # Test PrometheusExporter isolation (when enabled)
        prometheus_exporters = []
        for container in containers:
            exporter = container.get_prometheus_exporter()
            if exporter is not None:
                prometheus_exporters.append(exporter)
        if prometheus_exporters:
            self._verify_unique_instances(prometheus_exporters, "PrometheusExporter")

    def _verify_unique_instances(
        self, instances: List[Any], component_name: str
    ) -> None:
        """Verify all instances are unique objects.

        Args:
            instances: List of component instances
            component_name: Name for error reporting
        """
        for i, instance1 in enumerate(instances):
            for j, instance2 in enumerate(instances):
                if i != j:
                    assert instance1 is not instance2, (
                        f"{component_name} instances are not isolated: "
                        f"containers {i} and {j} share the same instance"
                    )
                    assert id(instance1) != id(instance2), (
                        f"{component_name} instances have same id: "
                        f"containers {i} and {j}"
                    )

    def test_concurrent_operations(
        self, containers: List[LoggingContainer], operations_per_container: int = 10
    ) -> None:
        """Test concurrent operations on multiple containers.

        Args:
            containers: List of containers to test
            operations_per_container: Number of operations per container
        """

        def container_operations(
            container: LoggingContainer, container_id: int
        ) -> bool:
            """Perform operations on a single container."""
            try:
                # Configure if not already configured
                if not container.is_configured:
                    container.configure()

                # Access various components
                for _ in range(operations_per_container):
                    _ = container.get_lock_manager()
                    _ = container.get_processor_metrics()
                    _ = container.get_metrics_collector()
                    _ = container.get_prometheus_exporter()
                    _ = container.get_logger(f"test_logger_{container_id}")

                    # Simulate some work
                    time.sleep(0.001)  # 1ms

                return True
            except Exception as e:
                print(f"Error in container {container_id}: {e}")
                return False

        # Use ThreadPoolExecutor for concurrent operations
        with ThreadPoolExecutor(max_workers=len(containers)) as executor:
            futures = []

            for i, container in enumerate(containers):
                future = executor.submit(container_operations, container, i)
                futures.append(future)

            # Wait for all operations to complete
            results = []
            for future in as_completed(futures):
                results.append(future.result())

        # All operations should succeed
        assert all(results), "Some concurrent operations failed"

    def verify_cleanup_isolation(self, containers: List[LoggingContainer]) -> None:
        """Verify that cleanup of one container doesn't affect others.

        Args:
            containers: List of containers to test
        """
        if len(containers) < 3:
            raise ValueError("Need at least 3 containers for cleanup isolation testing")

        # Configure all containers
        for container in containers:
            container.configure()

        # Verify all are configured
        for container in containers:
            assert container.is_configured

        # Reset middle container
        middle_index = len(containers) // 2
        containers[middle_index].reset()

        # Verify middle container is reset
        assert not containers[middle_index].is_configured

        # Verify other containers are still configured
        for i, container in enumerate(containers):
            if i != middle_index:
                assert container.is_configured, (
                    f"Container {i} was affected by reset of container {middle_index}"
                )

    @contextmanager
    def check_memory_leaks(self, containers: List[LoggingContainer]):
        """Context manager for memory leak detection.

        Args:
            containers: List of containers to monitor
        """
        # Start memory tracing
        tracemalloc.start()

        # Force garbage collection
        gc.collect()

        # Take initial memory snapshot
        initial_snapshot = tracemalloc.take_snapshot()
        initial_memory = self._get_memory_usage()

        try:
            yield
        finally:
            # Clean up containers
            for container in containers:
                try:
                    container.shutdown_sync()
                except Exception:
                    pass  # Ignore cleanup errors

            # Force garbage collection
            gc.collect()

            # Take final memory snapshot
            final_snapshot = tracemalloc.take_snapshot()
            final_memory = self._get_memory_usage()

            # Stop tracing
            tracemalloc.stop()

            # Calculate memory difference
            memory_diff = final_memory - initial_memory

            # Allow some memory growth but not excessive
            max_allowed_growth = 10 * 1024 * 1024  # 10MB

            if memory_diff > max_allowed_growth:
                # Get top memory differences
                top_stats = final_snapshot.compare_to(initial_snapshot, "lineno")

                print("Top 5 memory allocations:")
                for stat in top_stats[:5]:
                    print(stat)

                pytest.fail(
                    f"Memory leak detected: {memory_diff / 1024 / 1024:.2f}MB growth "
                    f"(max allowed: {max_allowed_growth / 1024 / 1024:.2f}MB)"
                )

    def _get_memory_usage(self) -> int:
        """Get current memory usage in bytes."""
        try:
            import psutil

            process = psutil.Process()
            return process.memory_info().rss
        except ImportError:
            # Fallback to tracemalloc if psutil not available
            current, peak = tracemalloc.get_traced_memory()
            return current

    def cleanup_all(self) -> None:
        """Clean up all created containers."""
        with self._lock:
            for container in self._created_containers:
                try:
                    container.shutdown_sync()
                except Exception:
                    pass  # Ignore cleanup errors
            self._created_containers.clear()


class TestContainerIsolationIntegration:
    """Integration tests for container isolation."""

    def setup_method(self):
        """Set up test framework for each test."""
        self.framework = ContainerIsolationTestFramework()

    def teardown_method(self):
        """Clean up after each test."""
        self.framework.cleanup_all()

    def test_multi_container_framework(self):
        """Test the multi-container test framework itself."""
        # Create containers
        containers = self.framework.create_containers(3)

        assert len(containers) == 3

        # Each should be a unique LoggingContainer
        for container in containers:
            assert isinstance(container, LoggingContainer)

        # Each should have unique container IDs
        container_ids = [container._container_id for container in containers]
        assert len(set(container_ids)) == 3

    def test_processor_lock_manager_isolation(self):
        """Test ProcessorLockManager isolation between containers."""
        containers = self.framework.create_containers(3)

        # Configure containers
        for container in containers:
            container.configure()

        # Get lock managers
        lock_managers = [container.get_lock_manager() for container in containers]

        # Verify all are ProcessorLockManager instances
        for lock_mgr in lock_managers:
            assert isinstance(lock_mgr, ProcessorLockManager)

        # Verify they are different instances
        self.framework._verify_unique_instances(lock_managers, "ProcessorLockManager")

        # Verify consistent access (cached)
        for i, container in enumerate(containers):
            lock_mgr2 = container.get_lock_manager()
            assert lock_mgr2 is lock_managers[i], (
                f"Container {i} lock manager not cached properly"
            )

    def test_processor_metrics_isolation(self):
        """Test ProcessorMetrics isolation between containers."""
        containers = self.framework.create_containers(3)

        # Configure containers
        for container in containers:
            container.configure()

        # Get processor metrics
        processor_metrics = [
            container.get_processor_metrics() for container in containers
        ]

        # Verify all are ProcessorMetrics instances
        for metrics in processor_metrics:
            assert isinstance(metrics, ProcessorMetrics)

        # Verify they are different instances
        self.framework._verify_unique_instances(processor_metrics, "ProcessorMetrics")

    def test_metrics_collector_isolation(self):
        """Test MetricsCollector isolation between containers."""
        # Create containers with metrics enabled
        settings_list = [
            LoggingSettings(metrics_enabled=True, metrics_sample_window=100),
            LoggingSettings(metrics_enabled=True, metrics_sample_window=200),
            LoggingSettings(metrics_enabled=True, metrics_sample_window=300),
        ]
        containers = self.framework.create_containers(3, settings_list)

        # Configure containers
        for container in containers:
            container.configure()

        # Get metrics collectors
        collectors = [container.get_metrics_collector() for container in containers]

        # Verify all are MetricsCollector instances
        for collector in collectors:
            assert isinstance(collector, MetricsCollector)

        # Verify they are different instances
        self.framework._verify_unique_instances(collectors, "MetricsCollector")

        # Verify different configurations
        assert collectors[0].sample_window == 100
        assert collectors[1].sample_window == 200
        assert collectors[2].sample_window == 300

    def test_prometheus_exporter_isolation(self):
        """Test PrometheusExporter isolation between containers."""
        # Create containers with Prometheus enabled on different ports
        settings_list = [
            LoggingSettings(
                metrics_enabled=True,
                metrics_prometheus_enabled=True,
                metrics_prometheus_port=9090,
            ),
            LoggingSettings(
                metrics_enabled=True,
                metrics_prometheus_enabled=True,
                metrics_prometheus_port=9091,
            ),
            LoggingSettings(
                metrics_enabled=True,
                metrics_prometheus_enabled=True,
                metrics_prometheus_port=9092,
            ),
        ]
        containers = self.framework.create_containers(3, settings_list)

        # Configure containers
        for container in containers:
            container.configure()

        # Get prometheus exporters
        exporters = [container.get_prometheus_exporter() for container in containers]

        # Verify all are PrometheusExporter instances
        for exporter in exporters:
            assert isinstance(exporter, PrometheusExporter)

        # Verify they are different instances
        self.framework._verify_unique_instances(exporters, "PrometheusExporter")

        # Verify different ports
        assert exporters[0].port == 9090
        assert exporters[1].port == 9091
        assert exporters[2].port == 9092

    def test_complete_component_isolation(self):
        """Test complete component isolation using the framework method."""
        # Create varied containers
        settings_list = [
            LoggingSettings(level="DEBUG", queue_enabled=False, metrics_enabled=True),
            LoggingSettings(level="INFO", queue_enabled=True, metrics_enabled=True),
            LoggingSettings(
                level="WARNING", queue_enabled=False, metrics_enabled=False
            ),
        ]
        containers = self.framework.create_containers(3, settings_list)

        # Use framework verification
        self.framework.verify_component_isolation(containers)

    def test_concurrent_container_operations(self):
        """Test concurrent operations on multiple containers."""
        # Create multiple containers
        containers = self.framework.create_containers(5)

        # Test concurrent operations
        self.framework.test_concurrent_operations(
            containers, operations_per_container=20
        )

        # Verify all containers are still configured and functional
        for i, container in enumerate(containers):
            assert container.is_configured, (
                f"Container {i} lost configuration during concurrent operations"
            )

            # Verify components are still accessible
            lock_mgr = container.get_lock_manager()
            metrics = container.get_processor_metrics()
            logger = container.get_logger(f"post_concurrent_test_{i}")

            assert isinstance(lock_mgr, ProcessorLockManager)
            assert isinstance(metrics, ProcessorMetrics)
            assert callable(logger.info)

    def test_container_cleanup_isolation(self):
        """Test that container cleanup doesn't affect other containers."""
        containers = self.framework.create_containers(5)

        # Use framework verification
        self.framework.verify_cleanup_isolation(containers)

    def test_container_lifecycle_integration(self):
        """Test complete container lifecycle with isolation."""
        # Create containers
        containers = self.framework.create_containers(3)

        # Test creation state
        for container in containers:
            assert not container.is_configured

        # Configure containers
        loggers = []
        for container in containers:
            logger = container.configure()
            loggers.append(logger)

        # Test configured state
        for container in containers:
            assert container.is_configured

        # Test logger functionality
        for logger in loggers:
            assert callable(logger.info)

        # Test container recreation after cleanup
        first_container = containers[0]
        first_container.reset()
        assert not first_container.is_configured

        # Reconfigure first container
        new_logger = first_container.configure()
        assert first_container.is_configured
        assert callable(new_logger.info)

        # Verify other containers unaffected
        for i in range(1, len(containers)):
            assert containers[i].is_configured

    def test_memory_leak_detection(self):
        """Test memory leak detection for multiple containers."""
        containers = self.framework.create_containers(10)

        with self.framework.check_memory_leaks(containers):
            # Configure all containers
            for container in containers:
                container.configure()

            # Access components
            for container in containers:
                container.get_lock_manager()
                container.get_processor_metrics()
                container.get_metrics_collector()
                container.get_prometheus_exporter()

            # Create some loggers
            for i, container in enumerate(containers):
                logger = container.get_logger(f"test_logger_{i}")
                logger.info(f"Test message from container {i}")

    def test_stress_test_many_containers(self):
        """Stress test with many concurrent containers."""
        # Create many containers
        container_count = 20
        containers = self.framework.create_containers(container_count)

        # Test concurrent operations with many containers
        self.framework.test_concurrent_operations(
            containers, operations_per_container=5
        )

        # Verify component isolation with many containers
        self.framework.verify_component_isolation(containers)

        # Test cleanup isolation with many containers
        # Reset every 3rd container
        for i in range(0, len(containers), 3):
            containers[i].reset()

        # Verify only reset containers are affected
        for i, container in enumerate(containers):
            if i % 3 == 0:
                assert not container.is_configured, f"Container {i} should be reset"
            else:
                assert container.is_configured, (
                    f"Container {i} should still be configured"
                )

    def test_performance_validation_multi_container(self):
        """Test performance validation for multi-container scenarios."""
        container_count = 10
        containers = self.framework.create_containers(container_count)

        # Time container configuration
        start_time = time.perf_counter()

        for container in containers:
            container.configure()

        config_time = time.perf_counter() - start_time

        # Time component access
        start_time = time.perf_counter()

        for container in containers:
            container.get_lock_manager()
            container.get_processor_metrics()
            container.get_metrics_collector()
            container.get_prometheus_exporter()

        access_time = time.perf_counter() - start_time

        # Performance should be reasonable
        avg_config_time = config_time / container_count
        avg_access_time = access_time / container_count

        # These are generous limits for integration testing
        assert avg_config_time < 1.0, (
            f"Average container configuration time too slow: {avg_config_time:.3f}s"
        )
        assert avg_access_time < 0.1, (
            f"Average component access time too slow: {avg_access_time:.3f}s"
        )

        # Total time should scale linearly
        assert config_time < 10.0, (
            f"Total configuration time too slow: {config_time:.3f}s"
        )
        assert access_time < 1.0, f"Total access time too slow: {access_time:.3f}s"

    def test_container_state_verification_utilities(self):
        """Test utilities for container state verification."""
        containers = self.framework.create_containers(3)

        # Test container ID uniqueness
        container_ids = set()
        for container in containers:
            container_ids.add(container._container_id)

        assert len(container_ids) == 3, "Container IDs are not unique"

        # Test registry isolation
        registries = set()
        for container in containers:
            registries.add(id(container._registry))

        assert len(registries) == 3, "Component registries are not unique"

        # Test factory isolation
        factories = set()
        for container in containers:
            factories.add(id(container._factory))

        assert len(factories) == 3, "Component factories are not unique"
