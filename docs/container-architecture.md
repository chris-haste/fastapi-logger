# Container-Based Architecture

## Overview

FastAPI Logger uses a container-based dependency injection architecture that eliminates global state while maintaining backward compatibility. This architecture provides better testability, thread safety, and supports multiple logging configurations within the same process.

## Architecture Components

### LoggingContainer

The `LoggingContainer` class is the central component that manages all logging dependencies:

- **Settings Management**: Stores and validates `LoggingSettings`
- **Queue Worker**: Manages async logging queue when enabled
- **Sinks**: Handles multiple output destinations (stdout, file, Loki)
- **HttpX Integration**: Manages trace propagation for outbound requests
- **Lifecycle Management**: Proper startup and shutdown procedures

### Key Benefits

1. **Thread Safety**: Each container uses thread-local storage and proper locking
2. **Multiple Configurations**: Different containers can coexist safely
3. **Better Testing**: Isolated instances prevent test interference
4. **Memory Management**: Automatic cleanup prevents memory leaks
5. **Backward Compatibility**: Existing code continues to work unchanged

## Usage Examples

### Basic Usage (Backward Compatible)

Existing code continues to work without changes:

```python
from fapilog import configure_logging

# This still works exactly as before
logger = configure_logging()
logger.info("Hello, world!")
```

### Advanced Usage with Multiple Containers

For advanced scenarios, you can create multiple isolated logging configurations:

```python
from fapilog.container import LoggingContainer
from fapilog.settings import LoggingSettings

# Create separate containers for different services
admin_settings = LoggingSettings(
    level="DEBUG",
    sinks=["stdout", "file:///var/log/admin.log"]
)
admin_container = LoggingContainer(admin_settings)
admin_logger = admin_container.configure()

user_settings = LoggingSettings(
    level="INFO",
    sinks=["stdout", "loki://localhost:3100"]
)
user_container = LoggingContainer(user_settings)
user_logger = user_container.configure()

# Each logger operates independently
admin_logger.debug("Admin debug message")  # Goes to stdout + file
user_logger.info("User activity")          # Goes to stdout + Loki
```

### FastAPI Integration

Containers integrate seamlessly with FastAPI applications:

```python
from fastapi import FastAPI
from fapilog.container import LoggingContainer
from fapilog.settings import LoggingSettings

app = FastAPI()

# Configure logging with automatic middleware registration
settings = LoggingSettings(
    level="INFO",
    sinks=["stdout"],
    trace_id_header="X-Request-ID"
)
container = LoggingContainer(settings)
logger = container.configure(app=app)

@app.get("/")
async def root():
    logger.info("Request received")
    return {"message": "Hello World"}

# Automatic cleanup on app shutdown
@app.on_event("shutdown")
async def shutdown_event():
    await container.shutdown()
```

### Testing with Containers

Containers make testing much easier by providing isolation:

```python
import pytest
from fapilog.container import LoggingContainer
from fapilog.settings import LoggingSettings

@pytest.fixture
def logging_container():
    """Create an isolated logging container for tests."""
    settings = LoggingSettings(
        level="DEBUG",
        sinks=["stdout"],
        queue_enabled=False  # Disable queue for synchronous testing
    )
    container = LoggingContainer(settings)
    logger = container.configure()

    yield container, logger

    # Automatic cleanup
    container.reset()

def test_logging_functionality(logging_container):
    container, logger = logging_container

    # Test logging without affecting other tests
    logger.info("Test message")
    assert container.is_configured
```

## Configuration Options

### LoggingSettings

The `LoggingSettings` class provides comprehensive configuration:

```python
from fapilog.settings import LoggingSettings

settings = LoggingSettings(
    # Basic settings
    level="INFO",                    # Logging level
    json_console="auto",            # Console output format

    # Queue settings
    queue_enabled=True,             # Enable async logging
    queue_maxsize=1000,            # Queue size
    queue_batch_size=10,           # Batch processing size
    queue_batch_timeout=1.0,       # Batch timeout
    queue_overflow="drop",         # Overflow strategy

    # Sink configuration
    sinks=["stdout", "file:///var/log/app.log"],

    # Security settings
    redact_fields=["password", "token"],
    redact_patterns=["\\d{4}-\\d{4}-\\d{4}-\\d{4}"],  # Credit cards

    # Trace propagation
    enable_httpx_trace_propagation=True,
    trace_id_header="X-Request-ID",

    # Performance settings
    sampling_rate=1.0,             # Log sampling rate
    enable_resource_metrics=True,   # Include CPU/memory metrics
)
```

### Environment Variables

All settings can be configured via environment variables:

```bash
export FAPILOG_LEVEL=DEBUG
export FAPILOG_SINKS="stdout,file:///var/log/app.log"
export FAPILOG_QUEUE_ENABLED=true
export FAPILOG_REDACT_FIELDS="password,secret,token"
```

## Thread Safety

The container architecture is fully thread-safe:

```python
import threading
from fapilog.container import LoggingContainer

def worker_function(worker_id):
    # Each thread can safely create its own container
    container = LoggingContainer()
    logger = container.configure()

    for i in range(100):
        logger.info(f"Worker {worker_id}, message {i}")

    container.shutdown_sync()

# Start multiple threads safely
threads = []
for i in range(5):
    thread = threading.Thread(target=worker_function, args=(i,))
    threads.append(thread)
    thread.start()

for thread in threads:
    thread.join()
```

## Memory Management

Containers automatically manage memory and provide cleanup mechanisms:

```python
from fapilog.container import LoggingContainer, cleanup_all_containers

# Manual cleanup for specific container
container = LoggingContainer()
logger = container.configure()
# ... use logger ...
container.shutdown_sync()  # Manual cleanup

# Global cleanup (automatically called on process exit)
cleanup_all_containers()

# Context manager pattern (future enhancement)
async def async_context_example():
    container = LoggingContainer()
    try:
        logger = container.configure()
        # ... use logger ...
    finally:
        await container.shutdown()
```

## Migration Guide

### From Global State to Containers

If you were previously relying on internal global state (not recommended), you'll need to update:

**Before (Internal API - Not Recommended):**

```python
# This was never recommended but might exist in some code
from fapilog._internal.queue import get_queue_worker
worker = get_queue_worker()  # Global state access
```

**After (Proper Container API):**

```python
from fapilog.container import LoggingContainer

container = LoggingContainer()
container.configure()
worker = container.queue_worker  # Access through container
```

### From Deprecated Functions

Some internal functions are now deprecated:

**Before:**

```python
from fapilog.bootstrap import _configure_standard_logging
_configure_standard_logging("INFO")  # Deprecated
```

**After:**

```python
from fapilog.container import LoggingContainer
from fapilog.settings import LoggingSettings

settings = LoggingSettings(level="INFO")
container = LoggingContainer(settings)
container.configure()
```

## Performance Considerations

### Container Creation Overhead

- Container creation is lightweight but not free
- For high-frequency logging, reuse containers
- Consider singleton patterns for application-level containers

### Queue Worker Performance

- Async queues provide better throughput for high-volume logging
- Tune `queue_batch_size` and `queue_batch_timeout` for your workload
- Monitor queue overflow with appropriate `queue_overflow` strategy

### Memory Usage

- Each container maintains its own state and resources
- Use `cleanup_all_containers()` for proper resource management
- Consider container sharing for related components

## Troubleshooting

### Common Issues

1. **Multiple Containers with Same Settings**

   ```python
   # Each container is independent, even with same settings
   container1 = LoggingContainer(settings)
   container2 = LoggingContainer(settings)
   # These are completely separate instances
   ```

2. **Container Not Cleaning Up**

   ```python
   # Always clean up containers explicitly in long-running processes
   container = LoggingContainer()
   try:
       logger = container.configure()
       # ... use logger ...
   finally:
       container.shutdown_sync()
   ```

3. **Thread Safety Issues**

   ```python
   # Don't share containers across threads unless necessary
   # Create thread-local containers instead
   import threading

   thread_local = threading.local()

   def get_logger():
       if not hasattr(thread_local, 'container'):
           thread_local.container = LoggingContainer()
           thread_local.logger = thread_local.container.configure()
       return thread_local.logger
   ```

### Debugging Container State

```python
from fapilog.container import LoggingContainer

container = LoggingContainer()
logger = container.configure()

# Check container state
print(f"Configured: {container.is_configured}")
print(f"Settings: {container.settings}")
print(f"Queue Worker: {container.queue_worker}")

# Debug queue state (if enabled)
if container.queue_worker:
    print(f"Queue size: {container.queue_worker.queue.qsize()}")
    print(f"Running: {container.queue_worker._running}")
```

## Best Practices

1. **Use Default Container for Simple Cases**: The backward-compatible API is perfect for most applications
2. **Create Dedicated Containers for Complex Scenarios**: Use multiple containers when you need different configurations
3. **Always Clean Up**: Explicitly shut down containers in long-running applications
4. **Test with Isolated Containers**: Use separate containers in tests to prevent interference
5. **Monitor Container Resources**: Keep track of queue sizes and memory usage in production
6. **Use Environment Variables**: Configure production settings via environment variables
7. **Follow FastAPI Patterns**: Let containers handle middleware registration automatically

## Future Enhancements

The container architecture provides a foundation for future improvements:

- **Async Context Managers**: For cleaner resource management
- **Container Pools**: For high-performance scenarios
- **Dynamic Reconfiguration**: Runtime configuration changes
- **Metrics Integration**: Built-in performance monitoring
- **Plugin System**: Extensible sink and enricher registration
