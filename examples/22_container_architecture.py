"""
Example 22: Pure Dependency Injection Container Architecture

This example demonstrates the advanced pure dependency injection architecture of fapilog,
showing how to use multiple isolated logging configurations, perfect thread safety,
and clean resource management without any global state.

Key Features Demonstrated:
- Pure dependency injection with zero global state
- Multiple logging containers with perfect isolation
- Thread-safe concurrent logging without global locks
- Container lifecycle management with explicit cleanup
- Testing with complete isolation
- FastAPI integration with pure DI patterns
"""

import threading
import time

from fastapi import Depends, FastAPI

from fapilog import configure_logging
from fapilog.bootstrap import configure_with_container, reset_logging
from fapilog.container import LoggingContainer
from fapilog.settings import LoggingSettings


def basic_pure_di_usage():
    """Demonstrate pure dependency injection vs. traditional approach."""
    print("=== Pure Dependency Injection Usage ===")

    # Traditional approach (still works - uses bootstrap DI)
    from fapilog import configure_logging

    logger = configure_logging()
    logger.info("Traditional approach", method="configure_logging")

    # Pure DI approach with explicit container
    container = LoggingContainer.create_from_settings(
        LoggingSettings(level="INFO", sinks=["stdout"])
    )
    container_logger = container.configure()
    container_logger.info("Pure DI approach", method="LoggingContainer")

    # Clean up (no global state to worry about)
    container.reset()
    print()


def multiple_isolated_containers():
    """Demonstrate multiple completely isolated logging configurations."""
    print("=== Multiple Isolated Containers ===")

    # Admin service: verbose logging with explicit settings
    admin_container = LoggingContainer.create_from_settings(
        LoggingSettings(
            level="DEBUG",
            json_console="pretty",  # Pretty output for development
            sinks=["stdout"],
            redact_fields=["password", "token"],
        )
    )
    admin_logger = admin_container.configure()

    # API service: production logging with queue
    api_container = LoggingContainer.create_from_settings(
        LoggingSettings(
            level="INFO",
            json_console="json",  # JSON output for production
            sinks=["stdout"],
            queue_enabled=True,
            sampling_rate=0.8,  # Sample 80% of logs
        )
    )
    api_logger = api_container.configure()

    # Background worker: minimal logging
    worker_container = LoggingContainer.create_from_settings(
        LoggingSettings(
            level="WARNING",
            json_console="json",
            sinks=["stdout"],
            sampling_rate=0.1,  # Only 10% of logs
        )
    )
    worker_logger = worker_container.configure()

    # Each logger operates in complete isolation
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

    # Clean up each container independently (no global cleanup needed)
    admin_container.reset()
    api_container.reset()
    worker_container.reset()
    print()


def thread_safe_pure_di_example():
    """Demonstrate perfect thread safety with pure dependency injection."""
    print("=== Thread-Safe Pure DI Example ===")

    def service_worker(service_name: str, message_count: int):
        """Worker function that creates its own isolated container."""
        # Each thread gets its own container - zero contention or interference
        container = LoggingContainer.create_from_settings(
            LoggingSettings(
                level="INFO",
                json_console="json",
                sinks=["stdout"],
                queue_enabled=False,  # Synchronous for predictable demo
            )
        )
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

        # Clean shutdown (thread-local, no global impact)
        container.reset()

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

    print("All concurrent services completed with perfect isolation")
    print()


def pure_di_lifecycle_example():
    """Demonstrate pure DI container lifecycle management."""
    print("=== Pure DI Lifecycle Example ===")

    # Method 1: Manual lifecycle management with explicit cleanup
    container = LoggingContainer.create_from_settings(
        LoggingSettings(level="INFO", sinks=["stdout"])
    )
    try:
        logger = container.configure()
        logger.info("Application starting", phase="initialization")

        # Simulate application work
        logger.info("Application running", phase="processing")

    finally:
        # Explicit cleanup (no global state affected)
        logger.info("Application shutting down", phase="cleanup")
        container.reset()

    # Method 2: Context manager pattern (built-in support)
    with LoggingContainer.create_from_settings(
        LoggingSettings(level="INFO", sinks=["stdout"])
    ) as context_container:
        context_logger = context_container.configure()
        context_logger.info("Context manager approach", lifecycle="automatic")
        # Automatic cleanup on exit

    # Method 3: Bootstrap integration with explicit container access
    logger, bootstrap_container = configure_with_container(
        LoggingSettings(level="INFO", sinks=["stdout"])
    )
    logger.info("Bootstrap DI approach", lifecycle="bootstrap_managed")
    # Bootstrap containers are managed by reset_logging()

    print()


def testing_perfect_isolation():
    """Demonstrate testing with perfect isolation using pure DI."""
    print("=== Testing Perfect Isolation ===")

    def simulate_test(test_name: str):
        """Simulate a test function with completely isolated logging."""
        # Each test gets its own container - zero interference possible
        container = LoggingContainer.create_from_settings(
            LoggingSettings(
                level="DEBUG",
                sinks=["stdout"],
                queue_enabled=False,  # Synchronous for testing
                json_console="json",  # Consistent output format
            )
        )
        logger = container.configure()

        # Test logic
        logger.info(f"Running test: {test_name}", test=test_name, isolated=True)
        logger.debug("Test detail", test=test_name, step="validation")

        # Verify container state (no global state to worry about)
        assert container.is_configured
        assert container.settings.level == "DEBUG"

        # Cleanup after test (completely isolated)
        container.reset()

        # Note: Logger may show this message during transition phase
        print(f"Test {test_name} completed with perfect isolation")

        return True

    # Run multiple "tests" with perfect isolation
    test_results = []
    for i in range(3):
        result = simulate_test(f"test_case_{i}")
        test_results.append(result)

    print(f"All tests passed with perfect isolation: {all(test_results)}")
    print()


def fastapi_pure_di_integration():
    """Demonstrate FastAPI integration with pure dependency injection."""
    print("=== FastAPI Pure DI Integration ===")

    app = FastAPI(title="Pure DI Container Demo API")

    # Pure DI approach - get both logger and container explicitly
    app_logger, app_container = configure_with_container(
        LoggingSettings(
            level="INFO",
            sinks=["stdout"],
            json_console="json",
            trace_id_header="X-Request-ID",
            queue_enabled=True,
        ),
        app=app,  # Automatic middleware registration
    )

    def get_logger():
        """Dependency to inject logger into routes."""
        return app_logger

    def get_container():
        """Dependency to inject container into routes (if needed)."""
        return app_container

    @app.get("/users/{user_id}")
    async def get_user(user_id: str, logger=Depends(get_logger)):
        logger.info("Fetching user", user_id=user_id, endpoint="/users")
        return {"user_id": user_id, "name": "John Doe"}

    @app.get("/health")
    async def health_check(
        logger=Depends(get_logger), container=Depends(get_container)
    ):
        logger.info("Health check requested", endpoint="/health")
        return {
            "status": "healthy",
            "container_configured": container.is_configured,
            "pure_di": True,
        }

    # Pure DI shutdown with explicit container access
    async def shutdown_event():
        """Clean shutdown of logging resources."""
        await app_container.shutdown()
        print("FastAPI pure DI container shut down")

    # Register shutdown handler
    app.add_event_handler("shutdown", shutdown_event)

    print("FastAPI app configured with pure dependency injection")
    print(f"Container configured: {app_container.is_configured}")
    print(f"Settings level: {app_container.settings.level}")
    print("Pure DI architecture: True")
    print()


def pure_di_debugging_example():
    """Demonstrate pure DI container debugging and introspection."""
    print("=== Pure DI Debugging Example ===")

    container = LoggingContainer.create_from_settings(
        LoggingSettings(
            level="DEBUG",
            sinks=["stdout"],
            queue_enabled=True,
            queue_maxsize=100,
            queue_batch_size=10,
        )
    )
    logger = container.configure()

    # Introspection (no global state dependencies)
    print(f"Container configured: {container.is_configured}")
    print(f"Settings level: {container.settings.level}")
    print(f"Queue enabled: {container.settings.queue_enabled}")
    print(f"Queue worker exists: {container.queue_worker is not None}")
    print("Pure DI architecture: True")

    if container.queue_worker:
        queue = container.queue_worker.queue
        print(f"Queue size: {queue.qsize()}")
        print(f"Queue maxsize: {queue.maxsize}")
        print(f"Worker running: {container.queue_worker._running}")

    # Generate some logs for debugging
    for i in range(5):
        logger.info(f"Debug message {i}", debug_index=i)

    # Clean up (no global state affected)
    container.reset()
    print()


def performance_pure_di_comparison():
    """Compare performance between traditional and pure DI approaches."""
    print("=== Performance Pure DI Comparison ===")

    import time

    # Traditional approach timing (uses bootstrap DI under the hood)
    start_time = time.time()
    from fapilog import configure_logging

    logger = configure_logging()
    for i in range(1000):
        logger.info(f"Traditional message {i}", approach="bootstrap_di", index=i)
    traditional_time = time.time() - start_time

    # Pure DI approach timing
    start_time = time.time()
    container = LoggingContainer.create_from_settings(
        LoggingSettings(level="INFO", sinks=["stdout"])
    )
    container_logger = container.configure()
    for i in range(1000):
        container_logger.info(f"Pure DI message {i}", approach="pure_di", index=i)
    container.reset()
    pure_di_time = time.time() - start_time

    print(f"Bootstrap DI approach: {traditional_time:.4f} seconds")
    print(f"Pure DI approach: {pure_di_time:.4f} seconds")
    print(f"Performance difference: {abs(pure_di_time - traditional_time):.4f} seconds")
    print(
        f"Pure DI overhead: {((pure_di_time - traditional_time) / traditional_time * 100):.2f}%"
    )
    print()


def bootstrap_container_registry():
    """Demonstrate bootstrap container registry (not global state)."""
    print("=== Bootstrap Container Registry ===")

    from fapilog.bootstrap import get_active_containers

    # Check initial state
    initial_containers = get_active_containers()
    print(f"Initial bootstrap containers: {len(initial_containers)}")

    # Create some bootstrap-managed containers
    logger1 = configure_logging(LoggingSettings(level="INFO"))
    logger2, container2 = configure_with_container(LoggingSettings(level="DEBUG"))

    # Use the loggers briefly to show they work
    logger1.info("Bootstrap logger 1 working")
    logger2.debug("Bootstrap logger 2 working")

    # Check registry (this is not global state - it's explicit bootstrap management)
    active_containers = get_active_containers()
    print(f"Active bootstrap containers: {len(active_containers)}")

    # Create pure DI container (not in bootstrap registry)
    pure_container = LoggingContainer.create_from_settings(
        LoggingSettings(level="WARNING")
    )
    pure_logger = pure_container.configure()

    # Registry unchanged (pure DI containers are completely independent)
    still_active = get_active_containers()
    print(f"Still active bootstrap containers: {len(still_active)}")
    print("Pure DI container not in registry (complete independence)")

    # Clean up bootstrap containers
    reset_logging()
    after_reset = get_active_containers()
    print(f"After reset_logging(): {len(after_reset)} bootstrap containers")

    # Pure DI container unaffected by bootstrap cleanup
    pure_logger.info("Pure DI container still works independently")
    pure_container.reset()

    print()


def main():
    """Run all pure dependency injection architecture examples."""
    print("FastAPI Logger - Pure Dependency Injection Architecture Examples")
    print("=" * 70)
    print()

    # Run all examples
    basic_pure_di_usage()
    multiple_isolated_containers()
    thread_safe_pure_di_example()
    pure_di_lifecycle_example()
    testing_perfect_isolation()
    fastapi_pure_di_integration()
    pure_di_debugging_example()
    performance_pure_di_comparison()
    bootstrap_container_registry()

    # Clean up any remaining bootstrap containers (not global cleanup)
    reset_logging()

    print("All pure dependency injection architecture examples completed!")
    print()
    print("Key Takeaways:")
    print("- Pure dependency injection eliminates all global state")
    print("- Perfect isolation between containers")
    print("- Thread-safe without global locks")
    print("- Use configure_logging() for simple bootstrap-managed containers")
    print("- Use LoggingContainer.create_from_settings() for pure DI:")
    print("  * Complete isolation")
    print("  * Perfect test isolation")
    print("  * Zero global state")
    print("  * Explicit resource management")
    print("- Both approaches provide excellent performance")
    print("- Clean architecture principles throughout")


if __name__ == "__main__":
    main()
