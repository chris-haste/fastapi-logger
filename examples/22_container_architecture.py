"""
Example 22: Container Architecture and Dependency Injection

This example demonstrates the advanced container-based architecture of fapilog,
showing how to use multiple isolated logging configurations, thread-safe operations,
and proper resource management.

Key Features Demonstrated:
- Multiple logging containers with different configurations
- Thread-safe concurrent logging
- Container lifecycle management
- Testing with isolated containers
- FastAPI integration with containers
"""

import threading
import time
from typing import Optional

from fastapi import Depends, FastAPI

from fapilog.container import LoggingContainer, cleanup_all_containers
from fapilog.settings import LoggingSettings


def basic_container_usage():
    """Demonstrate basic container usage vs. traditional approach."""
    print("=== Basic Container Usage ===")

    # Traditional approach (still works)
    from fapilog import configure_logging

    logger = configure_logging()
    logger.info("Traditional approach", method="configure_logging")

    # Container approach
    container = LoggingContainer()
    container_logger = container.configure()
    container_logger.info("Container approach", method="LoggingContainer")

    # Clean up
    container.shutdown_sync()
    print()


def multiple_configuration_example():
    """Demonstrate multiple isolated logging configurations."""
    print("=== Multiple Configuration Example ===")

    # Admin service: verbose logging
    admin_settings = LoggingSettings(
        level="DEBUG",
        json_console="pretty",  # Pretty output for development
        sinks=["stdout"],
        redact_fields=["password", "token"],
    )
    admin_container = LoggingContainer(admin_settings)
    admin_logger = admin_container.configure()

    # API service: production logging
    api_settings = LoggingSettings(
        level="INFO",
        json_console="json",  # JSON output for production
        sinks=["stdout"],
        queue_enabled=True,
        sampling_rate=0.8,  # Sample 80% of logs
    )
    api_container = LoggingContainer(api_settings)
    api_logger = api_container.configure()

    # Background worker: minimal logging
    worker_settings = LoggingSettings(
        level="WARNING",
        json_console="json",
        sinks=["stdout"],
        sampling_rate=0.1,  # Only 10% of logs
    )
    worker_container = LoggingContainer(worker_settings)
    worker_logger = worker_container.configure()

    # Each logger operates independently
    admin_logger.debug("Admin debug message", service="admin", user_id="admin123")
    admin_logger.info(
        "Admin processing",
        operation="user_management",
        sensitive_data={"password": "secret123"},
    )

    api_logger.info(
        "API request processed", service="api", endpoint="/users", status_code=200
    )
    api_logger.warning(
        "API rate limit exceeded", service="api", client_ip="192.168.1.100"
    )

    worker_logger.warning(
        "Worker task failed", service="worker", task_id="task-456", retry_count=3
    )
    worker_logger.error("Worker critical error", service="worker", error_code="E001")

    # Clean up all containers
    admin_container.shutdown_sync()
    api_container.shutdown_sync()
    worker_container.shutdown_sync()
    print()


def thread_safe_concurrent_example():
    """Demonstrate thread-safe concurrent logging with containers."""
    print("=== Thread-Safe Concurrent Example ===")

    def service_worker(service_name: str, message_count: int):
        """Worker function that creates its own logging container."""
        # Each thread gets its own container - completely thread-safe
        settings = LoggingSettings(
            level="INFO",
            json_console="json",
            sinks=["stdout"],
            queue_enabled=False,  # Synchronous for predictable demo
        )
        container = LoggingContainer(settings)
        logger = container.configure()

        for i in range(message_count):
            logger.info(
                f"{service_name} processing",
                message_id=i,
                service=service_name,
                thread_id=threading.current_thread().ident,
            )
            time.sleep(0.01)  # Simulate work

        logger.info(
            f"{service_name} completed",
            total_messages=message_count,
            service=service_name,
        )

        # Clean shutdown
        container.shutdown_sync()

    # Start multiple concurrent services
    threads = []
    for service_id in range(3):
        thread = threading.Thread(
            target=service_worker,
            args=(f"service-{service_id}", 5),  # Small count for demo
        )
        threads.append(thread)
        thread.start()

    # Wait for all services to complete
    for thread in threads:
        thread.join()

    print("All concurrent services completed successfully")
    print()


def container_lifecycle_example():
    """Demonstrate proper container lifecycle management."""
    print("=== Container Lifecycle Example ===")

    # Method 1: Manual lifecycle management
    container = LoggingContainer()
    try:
        logger = container.configure()
        logger.info("Application starting", phase="initialization")

        # Simulate application work
        logger.info("Application running", phase="processing")

    finally:
        # Explicit cleanup (recommended for long-running processes)
        container.shutdown_sync()
        logger.info("Application shutdown complete", phase="cleanup")

    # Method 2: Context manager pattern (custom implementation)
    class LoggingContext:
        def __init__(self, settings: Optional[LoggingSettings] = None):
            self.container = LoggingContainer(settings)
            self.logger = None

        def __enter__(self):
            self.logger = self.container.configure()
            return self.logger

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.container.shutdown_sync()

    # Usage with context manager
    with LoggingContext() as logger:
        logger.info("Context manager approach", lifecycle="managed")

    print()


def testing_isolation_example():
    """Demonstrate testing with isolated containers."""
    print("=== Testing Isolation Example ===")

    def simulate_test(test_name: str):
        """Simulate a test function with isolated logging."""
        # Each test gets its own container - no interference
        settings = LoggingSettings(
            level="DEBUG",
            sinks=["stdout"],
            queue_enabled=False,  # Synchronous for testing
            json_console="json",  # Consistent output format
        )
        container = LoggingContainer(settings)
        logger = container.configure()

        # Test logic
        logger.info(f"Running test: {test_name}", test=test_name, isolated=True)
        logger.debug("Test detail", test=test_name, step="validation")

        # Verify container state
        assert container.is_configured
        assert container.settings.level == "DEBUG"

        # Cleanup after test
        container.reset()
        logger.info(f"Test completed: {test_name}", test=test_name, status="passed")

        return True

    # Run multiple "tests" with isolation
    test_results = []
    for i in range(3):
        result = simulate_test(f"test_case_{i}")
        test_results.append(result)

    print(f"All tests passed: {all(test_results)}")
    print()


def fastapi_integration_example():
    """Demonstrate FastAPI integration with containers."""
    print("=== FastAPI Integration Example ===")

    app = FastAPI(title="Container Demo API")

    # Create application-level container
    app_container = LoggingContainer(
        LoggingSettings(
            level="INFO",
            sinks=["stdout"],
            json_console="json",
            trace_id_header="X-Request-ID",
            queue_enabled=True,
        )
    )

    # Configure with automatic middleware registration
    app_logger = app_container.configure(app=app)

    def get_logger():
        """Dependency to inject logger into routes."""
        return app_logger

    @app.get("/users/{user_id}")
    async def get_user(user_id: str, logger=Depends(get_logger)):
        logger.info("Fetching user", user_id=user_id, endpoint="/users")
        return {"user_id": user_id, "name": "John Doe"}

    @app.get("/health")
    async def health_check(logger=Depends(get_logger)):
        logger.info("Health check requested", endpoint="/health")
        return {
            "status": "healthy",
            "container_configured": app_container.is_configured,
        }

    # Simulate FastAPI shutdown
    async def shutdown_event():
        """Clean shutdown of logging resources."""
        await app_container.shutdown()
        print("FastAPI logging container shut down")

    # Register shutdown handler (normally done automatically)
    app.add_event_handler("shutdown", shutdown_event)

    print("FastAPI app configured with container-based logging")
    print(f"Container configured: {app_container.is_configured}")
    print(f"Settings level: {app_container.settings.level}")
    print()


def container_debugging_example():
    """Demonstrate container debugging and introspection."""
    print("=== Container Debugging Example ===")

    settings = LoggingSettings(
        level="DEBUG",
        sinks=["stdout"],
        queue_enabled=True,
        queue_maxsize=100,
        queue_batch_size=10,
    )
    container = LoggingContainer(settings)
    logger = container.configure()

    # Introspection
    print(f"Container configured: {container.is_configured}")
    print(f"Settings level: {container.settings.level}")
    print(f"Queue enabled: {container.settings.queue_enabled}")
    print(f"Queue worker exists: {container.queue_worker is not None}")

    if container.queue_worker:
        queue = container.queue_worker.queue
        print(f"Queue size: {queue.qsize()}")
        print(f"Queue maxsize: {queue.maxsize}")
        print(f"Worker running: {container.queue_worker._running}")

    # Generate some logs for debugging
    for i in range(5):
        logger.info(f"Debug message {i}", debug_index=i)

    # Clean up
    container.shutdown_sync()
    print()


def performance_comparison_example():
    """Compare performance between traditional and container approaches."""
    print("=== Performance Comparison Example ===")

    import time

    # Traditional approach timing
    start_time = time.time()
    from fapilog import configure_logging

    logger = configure_logging()
    for i in range(1000):
        logger.info(f"Traditional message {i}", approach="traditional", index=i)
    traditional_time = time.time() - start_time

    # Container approach timing
    start_time = time.time()
    container = LoggingContainer()
    container_logger = container.configure()
    for i in range(1000):
        container_logger.info(f"Container message {i}", approach="container", index=i)
    container.shutdown_sync()
    container_time = time.time() - start_time

    print(f"Traditional approach: {traditional_time:.4f} seconds")
    print(f"Container approach: {container_time:.4f} seconds")
    print(
        f"Performance difference: {abs(container_time - traditional_time):.4f} seconds"
    )
    print()


def main():
    """Run all container architecture examples."""
    print("FastAPI Logger - Container Architecture Examples")
    print("=" * 55)
    print()

    # Run all examples
    basic_container_usage()
    multiple_configuration_example()
    thread_safe_concurrent_example()
    container_lifecycle_example()
    testing_isolation_example()
    fastapi_integration_example()
    container_debugging_example()
    performance_comparison_example()

    # Global cleanup (automatically called on process exit)
    cleanup_all_containers()

    print("All container architecture examples completed!")
    print()
    print("Key Takeaways:")
    print("- Use configure_logging() for simple applications")
    print("- Use LoggingContainer for advanced scenarios:")
    print("  * Multiple configurations")
    print("  * Better test isolation")
    print("  * Thread-safe concurrent logging")
    print("  * Explicit resource management")
    print("- Containers are fully backward compatible")
    print("- Always clean up containers in production")


if __name__ == "__main__":
    main()
