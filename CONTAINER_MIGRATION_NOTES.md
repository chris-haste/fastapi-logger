# Container Migration Guide - Pure Dependency Injection

## Overview

The LoggingContainer has been completely redesigned to implement pure dependency injection without any global state. This change improves thread safety, testability, and allows perfect container isolation.

## Breaking Changes

### Removed Global Functions

The following global functions have been **REMOVED**:

```python
# ❌ REMOVED - No longer available
from fapilog.container import get_current_container, set_current_container, cleanup_all_containers

# These functions are no longer available:
get_current_container()
set_current_container(container)
cleanup_all_containers()
```

### Removed Global Variables

The following global variables have been **REMOVED**:

```python
# ❌ REMOVED - No longer available
_current_container
_current_container_lock
_container_registry
```

## New Usage Patterns

### 1. Pure Dependency Injection

**Old Pattern (Global State):**

```python
# ❌ OLD - Don't use this pattern
from fapilog.container import LoggingContainer, get_current_container

container = LoggingContainer()
container.configure()
# Global state was automatically set

# Later in code:
current = get_current_container()  # ❌ No longer available
```

**New Pattern (Pure DI):**

```python
# ✅ NEW - Explicit dependency passing
from fapilog.container import LoggingContainer

container = LoggingContainer()
container.configure()

# Pass container explicitly where needed
def my_function(container: LoggingContainer):
    logger = container.get_logger("my_app")
    logger.info("Hello world")

my_function(container)
```

### 2. Context Manager Support

**New Feature - Automatic Configuration and Cleanup:**

```python
# ✅ NEW - Context manager pattern
from fapilog.container import LoggingContainer
from fapilog.settings import LoggingSettings

settings = LoggingSettings(level="INFO", sinks=["stdout"])

with LoggingContainer(settings) as container:
    # Container is automatically configured
    logger = container.get_logger("app")
    logger.info("This will be logged")
# Container is automatically shut down
```

### 3. Scoped Logger Pattern

**New Feature - Scoped Logger Management:**

```python
# ✅ NEW - Scoped logger with automatic cleanup
container = LoggingContainer()

with container.scoped_logger("my_service") as logger:
    logger.info("Service started")
    logger.error("Something went wrong")
# Logger cleanup is handled automatically
```

### 4. Factory Methods

**New Feature - Clean Container Creation:**

```python
# ✅ NEW - Factory methods for clean instantiation
from fapilog.container import LoggingContainer
from fapilog.settings import LoggingSettings

# Create from settings
settings = LoggingSettings(level="DEBUG", queue_enabled=True)
container = LoggingContainer.create_from_settings(settings)

# Create with defaults
container = LoggingContainer.create_with_defaults()
```

### 5. Multiple Container Isolation

**New Capability - Perfect Container Isolation:**

```python
# ✅ NEW - Multiple containers coexist without interference
container1 = LoggingContainer(LoggingSettings(level="INFO"))
container2 = LoggingContainer(LoggingSettings(level="DEBUG"))

logger1 = container1.get_logger("app1")
logger2 = container2.get_logger("app2")

# Containers are completely isolated
container1.reset()  # Only affects container1
# container2 continues working normally
```

## Migration Steps

### Step 1: Remove Global Function Calls

Replace any usage of global functions:

```python
# ❌ Remove these patterns:
from fapilog.container import get_current_container, set_current_container

# Replace with explicit container passing:
def my_logging_function(container: LoggingContainer):
    logger = container.get_logger()
    return logger
```

### Step 2: Update Container Creation

```python
# ✅ Use new factory methods or constructor directly:
container = LoggingContainer.create_with_defaults()
# or
container = LoggingContainer(settings)
```

### Step 3: Use Context Managers for Scoped Access

```python
# ✅ For scoped usage:
with LoggingContainer(settings) as container:
    # Use container here
    pass
```

### Step 4: Update Test Code

```python
# ❌ OLD - Tests using global cleanup
def teardown():
    cleanup_all_containers()  # No longer available

# ✅ NEW - Tests with explicit container management
def test_logging():
    container = LoggingContainer()
    try:
        container.configure()
        # Test code here
    finally:
        container.reset()  # Clean up explicitly
```

## Benefits of Pure Dependency Injection

### 1. Perfect Thread Safety

- No global locks required
- Each container operates independently
- No shared state between containers

### 2. Complete Testability

- Easy to create isolated test containers
- No global state cleanup required
- Perfect test isolation

### 3. Memory Efficiency

- Containers can be garbage collected naturally
- No global registry holding references
- Better resource management

### 4. Clear Dependencies

- Explicit dependency passing
- No hidden global state access
- Easier to reason about code flow

### 5. Multiple Configuration Support

- Run multiple containers with different configs
- Perfect isolation between environments
- No configuration conflicts

## Compatibility Notes

- **No backwards compatibility** - This is a complete redesign
- All existing code using global functions must be updated
- New pattern is cleaner and more maintainable
- Performance improvements due to lack of global locking

## Example: Full Migration

**Before (Global State Pattern):**

```python
from fapilog.container import LoggingContainer, get_current_container

# Global setup
container = LoggingContainer()
container.configure()

# Usage throughout app
def process_request():
    container = get_current_container()
    logger = container.get_logger("api")
    logger.info("Processing request")
```

**After (Pure DI Pattern):**

```python
from fapilog.container import LoggingContainer

class Application:
    def __init__(self):
        self.container = LoggingContainer.create_with_defaults()
        self.container.configure()

    def process_request(self):
        logger = self.container.get_logger("api")
        logger.info("Processing request")

    def shutdown(self):
        self.container.shutdown_sync()

# Usage
app = Application()
app.process_request()
app.shutdown()
```

## Bootstrap Integration Updates (Story 2)

### New Bootstrap Functionality

**Enhanced configure_logging() Function:**

```python
# ✅ NEW - Still backward compatible, now creates isolated containers
from fapilog.bootstrap import configure_logging, configure_with_container

# Basic usage (unchanged API)
logger = configure_logging()

# Advanced usage - get both logger and container
logger, container = configure_with_container()

# Multiple isolated containers
logger1 = configure_logging(LoggingSettings(level="INFO"))
logger2 = configure_logging(LoggingSettings(level="DEBUG"))
# Each call creates a separate, isolated container
```

**New Lifecycle Management:**

```python
# ✅ NEW - Explicit lifecycle management
from fapilog.bootstrap import shutdown_logging, reset_logging, get_active_containers

# Get active containers for advanced use
containers = get_active_containers()

# Shutdown all containers gracefully
shutdown_logging()

# Reset all containers (for testing)
reset_logging()
```

### Bootstrap Migration Changes

**What Changed:**

- Removed global `_default_container` variable
- Removed `_get_default_container()` function
- `configure_logging()` now creates isolated containers per call
- Added container registry for lifecycle management
- Added new utility functions for advanced use cases

**What Stayed the Same:**

- `configure_logging()` API signature unchanged
- Backward compatibility maintained for all public functions
- Same configuration behavior and options

**Key Improvements:**

- Perfect container isolation between calls
- Better memory management
- Thread safety without global locks
- Explicit lifecycle management options
- Enhanced testing capabilities

## Component Integration Updates (Story 3)

### Queue Integration Changes

**Updated Queue Sink Creation:**

```python
# ✅ NEW - Pure dependency injection queue sink
from fapilog._internal.queue_integration import create_queue_sink

# Create queue sink with explicit container
container = LoggingContainer.create_from_settings(settings)
queue_sink_processor = create_queue_sink(container)

# Old global state function is now legacy fallback
# from fapilog._internal.queue_integration import queue_sink  # Legacy
```

**Pipeline Updates:**

```python
# ✅ NEW - Pipeline with container parameter
from fapilog.pipeline import build_processor_chain

# Build processor chain with explicit container for queue support
processors = build_processor_chain(
    settings=settings,
    pretty=False,
    container=container  # Required for queue_enabled=True
)

# Falls back gracefully without container (legacy mode)
processors = build_processor_chain(settings, pretty=False, container=None)
```

### Component Architecture Changes

**What Changed:**

- `queue_integration.py` - Removed `get_current_container()` usage
- `pipeline.py` - Added optional `container` parameter to `build_processor_chain()`
- `container.py` - Updated to pass container to pipeline building
- All components now use pure dependency injection patterns

**What Stayed the Same:**

- Public APIs remain unchanged
- Pipeline building API is backward compatible (container parameter is optional)
- Queue functionality works the same (just with explicit container)
- Middleware components continue to work as before

**Key Improvements:**

- Complete elimination of global state throughout system
- All components operate with perfect isolation
- Queue workers receive containers through explicit injection
- Pipeline processors can access container when needed
- Thread safety without any global locking

### Integration Validation

The complete system now operates with:

- **Zero global state variables** across all components
- **Perfect container isolation** between instances
- **Explicit dependency injection** throughout the pipeline
- **Backward compatibility** for all public APIs
- **Enhanced testing capabilities** with complete isolation

## Questions?

This migration guide covers the complete architectural transformation:

- **Story 1:** Core container redesign with pure dependency injection
- **Story 2:** Bootstrap integration maintaining API compatibility
- **Story 3:** Component updates for complete system-wide pure DI

The new architecture provides better thread safety, testability, and resource management while maintaining backward compatibility for public APIs. All components now operate without global state and support complete isolation.
