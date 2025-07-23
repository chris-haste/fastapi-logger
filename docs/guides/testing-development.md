# Testing & Development Guide

**Complete guide to testing custom components, debugging issues, and developing with fapilog.**

Whether you're building custom sinks, debugging configuration issues, or optimizing performance, this guide provides the tools and patterns you need for successful fapilog development. From unit testing to production debugging, learn how to leverage fapilog's comprehensive testing framework.

**For specialized topics, see:**

- **[Configuration Guide](configuration.md)** - Environment setup and settings validation
- **[Sinks Guide](sinks.md)** - Custom sink development and integration
- **[Security & Redaction Guide](security.md)** - Data protection testing and validation

---

## Quick Navigation

**Jump to what you need:**

- **🧪 [Testing Framework](#testing-framework)** - Unit testing and validation tools
- **🔍 [Debugging Tools](#debugging-tools)** - Diagnose and troubleshoot issues
- **⚡ [Performance Testing](#performance-testing)** - Benchmark and optimize components
- **🎭 [Mock Testing](#mock-testing)** - Testing with mock sinks and data
- **🔌 [Integration Testing](#integration-testing)** - Full system testing patterns
- **🏗️ [Development Workflow](#development-workflow)** - Best practices and patterns
- **🐛 [Troubleshooting](#troubleshooting)** - Common issues and solutions

[↑ Back to top](#testing--development-guide)

---

## Table of Contents

1. [Testing Framework](#testing-framework)
2. [Debugging Tools](#debugging-tools)
3. [Performance Testing](#performance-testing)
4. [Mock Testing](#mock-testing)
5. [Integration Testing](#integration-testing)
6. [Development Workflow](#development-workflow)
7. [Configuration Testing](#configuration-testing)
8. [Error Handling & Recovery](#error-handling--recovery)
9. [Production Monitoring](#production-monitoring)
10. [Troubleshooting](#troubleshooting)

[↑ Back to top](#testing--development-guide)

---

## Testing Framework

Fapilog provides a comprehensive testing framework specifically designed for testing custom sinks, enrichers, and integrations. The `fapilog.testing` package includes everything you need to thoroughly test your custom components.

### SinkTestFramework

**Primary testing framework for custom sink development:**

```python
from fapilog.testing import SinkTestFramework
from fapilog import Sink, register_sink

# Define a custom sink for testing
@register_sink("test_api")
class TestAPISink(Sink):
    def __init__(self, api_key: str = None):
        super().__init__()
        self.api_key = api_key
        self.events_sent = []

    async def write(self, event_dict):
        # Simulate API call
        self.events_sent.append(event_dict)

# Test the sink
framework = SinkTestFramework()

# Validate sink interface
assert framework.validate_sink_interface(TestAPISink)

# Create test instance
sink = framework.create_test_sink(TestAPISink, api_key="test-key")

# Test basic write functionality
test_events = [
    {"level": "info", "message": "Test message 1"},
    {"level": "error", "message": "Test error", "error": "Test exception"}
]

success = await framework.test_sink_write(sink, test_events)
assert success

# Get test summary
summary = framework.get_test_summary()
print(f"Events tested: {summary['total_events']}")
print(f"Errors: {summary['total_errors']}")
```

### Interface Validation

**Ensure your sinks implement the required interface correctly:**

```python
from fapilog.testing import SinkTestFramework

# Test sink class validation
framework = SinkTestFramework()

# Valid sink
class ValidSink(Sink):
    def __init__(self):
        super().__init__()

    async def write(self, event_dict):
        pass

assert framework.validate_sink_interface(ValidSink)

# Invalid sink (missing async)
class InvalidSink(Sink):
    def write(self, event_dict):  # Not async!
        pass

assert not framework.validate_sink_interface(InvalidSink)
```

### URI Testing

**Test sink URI parsing and configuration:**

```python
from fapilog.testing import validate_sink_uri, validate_uri_scheme

# Test valid URIs
assert validate_uri_scheme("postgres://localhost/logs")
assert validate_sink_uri("file:///var/log/app.log")

# Test invalid URIs
assert not validate_uri_scheme("invalid-scheme://test")
assert not validate_sink_uri("malformed::uri")

# Test with parameters
uri = "postgres://localhost:5432/logs?table=events&timeout=30"
assert validate_sink_uri(uri)
```

### Testing Examples

**Real-world testing patterns:**

```python
import asyncio
from fapilog.testing import SinkTestFramework

async def test_database_sink():
    """Test a database sink implementation."""
    framework = SinkTestFramework()

    # Mock database sink
    class DatabaseSink(Sink):
        def __init__(self, table_name="logs"):
            super().__init__()
            self.table_name = table_name
            self.connections = 0
            self.queries_executed = []

        async def write(self, event_dict):
            # Simulate database write
            query = f"INSERT INTO {self.table_name} VALUES ..."
            self.queries_executed.append(query)

    # Test sink creation
    sink = framework.create_test_sink(DatabaseSink, table_name="test_logs")

    # Test multiple events
    events = [
        {"level": "info", "message": "User login", "user_id": "123"},
        {"level": "warning", "message": "Rate limit", "ip": "192.168.1.1"},
        {"level": "error", "message": "Database error", "error": "timeout"}
    ]

    success = await framework.test_sink_write(sink, events)
    assert success
    assert len(sink.queries_executed) == 3

    return framework.get_test_summary()

# Run the test
summary = asyncio.run(test_database_sink())
print(f"✅ Database sink test completed: {summary}")
```

[↑ Back to top](#testing--development-guide)

---

## Debugging Tools

Fapilog includes powerful debugging utilities to help diagnose configuration issues, validate sink registrations, and troubleshoot runtime problems.

### SinkDebugger

**Comprehensive debugging utilities for sink development:**

```python
from fapilog.testing import SinkDebugger

# List all registered sinks
sinks = SinkDebugger.list_registered_sinks()
print(f"Registered sinks: {list(sinks.keys())}")

# Get detailed sink information
info = SinkDebugger.get_sink_info("postgres")
print(f"Class: {info['class_name']}")
print(f"Module: {info['module']}")
print(f"Constructor: {info['constructor_signature']}")

# Validate sink class
from fapilog import Sink

class MySink(Sink):
    async def write(self, event_dict):
        pass

issues = SinkDebugger.validate_sink_class(MySink)
if issues:
    print(f"⚠️ Issues found: {issues}")
else:
    print("✅ Sink validation passed")
```

### Registry Status

**Check sink registry status and health:**

```python
from fapilog.testing import SinkDebugger

# Print comprehensive registry status
SinkDebugger.print_sink_registry_status()

# Example output:
# === Sink Registry Status ===
# Total registered sinks: 4
#
# Registered sinks:
#   stdout: StdoutSink
#     ✅ Valid
#   file: FileSink
#     ✅ Valid
#   loki: LokiSink
#     ✅ Valid
#   postgres: PostgresSink
#     ⚠️  Issues: Missing required dependency
```

### Detailed Sink Debugging

**Debug specific sink implementations:**

```python
from fapilog.testing import SinkDebugger

# Debug a specific sink
SinkDebugger.print_sink_debug_info("postgres")

# Example output:
# === Debug Info: postgres ===
# Class: PostgresSink
# Module: myapp.sinks.postgres
# File: /path/to/myapp/sinks/postgres.py
#
# Constructor: (self, host: str = 'localhost', port: int = 5432, ...)
# Parameters: host, port, database, user, password
#
# Methods:
#   write (async): (self, event_dict: Dict[str, Any]) -> None
#   close (async): (self) -> None
#
# ✅ Validation: All checks passed
```

### URI Debugging

**Debug URI parsing and sink creation:**

```python
from fapilog.testing import SinkDebugger

# Test URI configuration
uri = "postgres://localhost:5432/logs?table=events&timeout=30"
debug_info = SinkDebugger.debug_sink_configuration(uri)

print(f"Overall status: {debug_info['overall_status']}")
print(f"URI parsing: {debug_info['uri_parsing']['success']}")
print(f"Sink found: {debug_info['uri_parsing']['sink_found']}")

if debug_info['recommendations']:
    print("Recommendations:")
    for rec in debug_info['recommendations']:
        print(f"  - {rec}")
```

### Configuration Validation

**Test and validate configuration settings:**

```python
from fapilog.settings import LoggingSettings
from fapilog.testing import SinkDebugger

# Test configuration
try:
    settings = LoggingSettings(
        level="INFO",
        sinks=["stdout", "postgres://localhost/logs"],
        redact_patterns=["password", "token"]
    )
    print("✅ Configuration valid")
except Exception as e:
    print(f"❌ Configuration error: {e}")

# Debug each sink URI
for sink_uri in settings.sinks:
    if isinstance(sink_uri, str):
        result = SinkDebugger.test_sink_uri_parsing(sink_uri)
        print(f"Sink {sink_uri}: {'✅' if result['success'] else '❌'}")
```

[↑ Back to top](#testing--development-guide)

---

## Performance Testing

Optimize your custom components with fapilog's performance testing tools. Measure throughput, latency, and resource usage to ensure production readiness.

### SinkPerformanceTester

**Comprehensive performance testing for custom sinks:**

```python
import asyncio
from fapilog.testing import SinkPerformanceTester
from fapilog import Sink

# Example high-performance sink
class HighPerformanceSink(Sink):
    def __init__(self):
        super().__init__()
        self.events_processed = 0

    async def write(self, event_dict):
        # Simulate fast processing
        self.events_processed += 1
        await asyncio.sleep(0.001)  # 1ms processing time

async def test_sink_performance():
    tester = SinkPerformanceTester()
    sink = HighPerformanceSink()

    # Test throughput
    throughput = await tester.test_throughput(sink, num_events=1000)
    print(f"Throughput: {throughput:.2f} events/sec")

    # Test concurrent throughput
    concurrent_throughput = await tester.test_concurrent_throughput(
        sink, num_events=1000, num_workers=10
    )
    print(f"Concurrent throughput: {concurrent_throughput:.2f} events/sec")

    # Test latency
    latency = await tester.test_latency(sink, num_samples=100)
    print(f"Average latency: {latency:.3f}ms")

    # Print summary
    tester.print_summary()

asyncio.run(test_sink_performance())
```

### Comprehensive Performance Suite

**Run full performance test suite:**

```python
import asyncio
from fapilog.testing import SinkPerformanceTester

async def comprehensive_performance_test():
    tester = SinkPerformanceTester()
    sink = YourCustomSink()

    # Custom test configuration
    test_config = {
        "throughput_events": 5000,
        "concurrent_events": 2000,
        "concurrent_workers": 20,
        "latency_samples": 200,
        "memory_events": 1000,
        "batch_sizes": [1, 10, 50, 100, 200],
        "batch_events_per_size": 100
    }

    # Run comprehensive test
    results = await tester.run_comprehensive_test(sink, test_config)

    # Analyze results
    print("\n=== Performance Test Results ===")
    print(f"Sequential throughput: {results['throughput']:.2f} events/sec")
    print(f"Concurrent throughput: {results['concurrent_throughput']:.2f} events/sec")
    print(f"Average latency: {results['latency']['mean_ms']:.3f}ms")
    print(f"P95 latency: {results['latency']['p95_ms']:.3f}ms")

    if 'memory' in results and 'error' not in results['memory']:
        memory_per_event = results['memory']['memory_per_event_bytes']
        print(f"Memory per event: {memory_per_event:.0f} bytes")

    return results

results = asyncio.run(comprehensive_performance_test())
```

### Batch Performance Testing

**Test performance with different batch sizes:**

```python
async def test_batch_performance():
    tester = SinkPerformanceTester()
    sink = YourBatchingSink()

    batch_sizes = [1, 10, 50, 100, 500]
    results = await tester.test_batch_performance(
        sink, batch_sizes, events_per_batch=50
    )

    print("Batch Size | Throughput (events/sec) | Latency (ms)")
    print("-" * 50)
    for size, metrics in results.items():
        throughput = metrics['events_per_second']
        latency = metrics['avg_latency_ms']
        print(f"{size:9d} | {throughput:18.2f} | {latency:10.3f}")

asyncio.run(test_batch_performance())
```

### Memory Usage Testing

**Monitor memory usage during testing:**

```python
async def test_memory_usage():
    tester = SinkPerformanceTester()
    sink = YourSink()

    # Test memory usage over time
    memory_results = await tester.test_memory_usage(sink, num_events=5000)

    if 'error' in memory_results:
        print(f"Memory testing failed: {memory_results['error']}")
    else:
        delta_mb = memory_results['memory_delta_bytes'] / 1024 / 1024
        per_event = memory_results['memory_per_event_bytes']

        print(f"Memory delta: {delta_mb:.2f} MB")
        print(f"Memory per event: {per_event:.0f} bytes")

        if delta_mb > 10:  # More than 10MB growth
            print("⚠️ High memory usage detected")

asyncio.run(test_memory_usage())
```

[↑ Back to top](#testing--development-guide)

---

## Mock Testing

Use fapilog's mock sinks to test error scenarios, validate behavior, and simulate different conditions without external dependencies.

### RecordingSink

**Capture and inspect log events for testing:**

```python
from fapilog.testing import RecordingSink
from fapilog import configure_logging, log

# Set up recording sink
recording_sink = RecordingSink()
configure_logging(sinks=[recording_sink])

# Generate test logs
log.info("User login", user_id="123", action="login")
log.warning("Rate limit reached", ip="192.168.1.1")
log.error("Database error", error="timeout", retry_count=3)

# Inspect recorded events
print(f"Total events recorded: {len(recording_sink.events)}")

# Get events by level
info_events = recording_sink.get_events(level="info")
error_events = recording_sink.get_events(level="error")

print(f"Info events: {len(info_events)}")
print(f"Error events: {len(error_events)}")

# Check last event
last_event = recording_sink.get_last_event()
print(f"Last event: {last_event['event']} (level: {last_event['level']})")

# Clear for next test
recording_sink.clear()
```

### FailingSink

**Test error handling and resilience:**

```python
from fapilog.testing import FailingSink
from fapilog import configure_logging, log

# Create sink that fails 50% of the time
failing_sink = FailingSink(
    failure_rate=0.5,
    failure_message="Simulated network error"
)

configure_logging(sinks=[failing_sink])

# Test error handling
for i in range(10):
    try:
        log.info(f"Test message {i}", iteration=i)
    except Exception as e:
        print(f"Expected failure: {e}")

# Check failure statistics
stats = failing_sink.get_stats()
print(f"Attempts: {stats['attempts']}")
print(f"Failures: {stats['failures']}")
print(f"Success rate: {stats['successes']/stats['attempts']:.2%}")
```

### Conditional Failing

**Test specific failure conditions:**

```python
from fapilog.testing import ConditionalFailingSink

# Sink that fails only on error level logs
conditional_sink = ConditionalFailingSink(
    fail_on_level="error",
    fail_on_field="sensitive_data"
)

configure_logging(sinks=[conditional_sink])

# These will succeed
log.info("Normal log")
log.warning("Warning log")

# These will fail
try:
    log.error("Error log")  # Fails on error level
except Exception as e:
    print(f"Expected error failure: {e}")

try:
    log.info("Data log", sensitive_data="secret")  # Fails on field
except Exception as e:
    print(f"Expected field failure: {e}")

failure_count = conditional_sink.get_failure_count()
print(f"Conditional failures: {failure_count}")
```

### SlowSink

**Test performance under latency conditions:**

```python
import asyncio
from fapilog.testing import SlowSink

# Create sink with 100ms delay
slow_sink = SlowSink(delay_ms=100)

configure_logging(sinks=[slow_sink])

# Test with timing
start_time = asyncio.get_event_loop().time()

for i in range(5):
    log.info(f"Slow message {i}")

elapsed = asyncio.get_event_loop().time() - start_time
print(f"5 messages took {elapsed:.2f}s (expected ~0.5s)")

# Check delay statistics
stats = slow_sink.get_delay_stats()
print(f"Average delay: {stats['avg_delay_ms']:.1f}ms")
print(f"Total delays: {stats['total_delays']}")
```

### Combined Mock Testing

**Use multiple mock sinks together:**

```python
from fapilog.testing import RecordingSink, FailingSink, SlowSink

# Create combined test scenario
recording_sink = RecordingSink()
failing_sink = FailingSink(failure_rate=0.3)  # 30% failure rate
slow_sink = SlowSink(delay_ms=50)

# Test with multiple sinks
configure_logging(sinks=[recording_sink, failing_sink, slow_sink])

# Generate test data
for i in range(20):
    try:
        log.info(f"Test event {i}", event_id=i)
    except Exception:
        pass  # Expected failures

# Analyze results
print(f"Events recorded: {len(recording_sink.events)}")
print(f"Failure rate: {failing_sink.get_stats()['failures']/20:.2%}")
print(f"Average delay: {slow_sink.get_delay_stats()['avg_delay_ms']:.1f}ms")
```

[↑ Back to top](#testing--development-guide)

---

## Integration Testing

Test your components in realistic environments with full system integration, including FastAPI applications and container architectures.

### FastAPI Integration Testing

**Test sinks with FastAPI applications:**

```python
import asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fapilog.testing import SinkIntegrationTester, RecordingSink

async def test_fastapi_integration():
    tester = SinkIntegrationTester()

    # Custom test sink
    class APITestSink(Sink):
        def __init__(self):
            super().__init__()
            self.api_events = []

        async def write(self, event_dict):
            self.api_events.append(event_dict)

    # Test with FastAPI
    result = await tester.test_with_fastapi(
        APITestSink,
        sink_name="api_test",
        timeout=30
    )

    print(f"FastAPI integration: {'✅' if result['success'] else '❌'}")
    if result['success']:
        print(f"App title: {result['app_title']}")
        print(f"Test messages sent: {result['test_messages_sent']}")

    return result

# Run integration test
result = asyncio.run(test_fastapi_integration())
```

### Container Integration Testing

**Test with LoggingContainer architecture:**

```python
import asyncio
from fapilog.testing import SinkIntegrationTester

async def test_container_integration():
    tester = SinkIntegrationTester()

    # Test with container
    result = await tester.test_container_integration(
        YourCustomSink,
        sink_name="container_test",
        database_url="sqlite:///test.db"
    )

    print(f"Container integration: {'✅' if result['success'] else '❌'}")
    print(f"Sinks configured: {result['sinks_count']}")

    return result

result = asyncio.run(test_container_integration())
```

### Error Handling Integration

**Test error scenarios in full integration:**

```python
async def test_error_handling_integration():
    tester = SinkIntegrationTester()

    # Test error handling
    result = await tester.test_error_handling_integration(
        FailingSink,
        sink_name="error_test",
        should_fail=True,
        failure_rate=1.0
    )

    print(f"Error handling test: {'✅' if result['success'] else '❌'}")
    print(f"Error occurred as expected: {result['error_occurred']}")

    return result

result = asyncio.run(test_error_handling_integration())
```

### End-to-End Testing

**Complete end-to-end testing pattern:**

```python
import asyncio
from fastapi import FastAPI
from fapilog import configure_logging, log
from fapilog.testing import RecordingSink

async def end_to_end_test():
    """Complete end-to-end test with real FastAPI app."""

    # Set up test app
    app = FastAPI(title="Test App")
    recording_sink = RecordingSink()

    # Configure logging
    configure_logging(app=app, sinks=[recording_sink])

    @app.get("/test")
    async def test_endpoint():
        log.info("Test endpoint called", endpoint="/test")
        return {"status": "ok"}

    @app.get("/error")
    async def error_endpoint():
        log.error("Test error", endpoint="/error")
        raise Exception("Test error")

    # Test with client
    from fastapi.testclient import TestClient
    client = TestClient(app)

    # Make requests
    response1 = client.get("/test")
    assert response1.status_code == 200

    response2 = client.get("/error")
    assert response2.status_code == 500

    # Verify logging
    events = recording_sink.get_events()
    print(f"Total events captured: {len(events)}")

    # Check for specific events
    test_events = [e for e in events if e.get('endpoint') == '/test']
    error_events = [e for e in events if e.get('endpoint') == '/error']

    print(f"Test endpoint events: {len(test_events)}")
    print(f"Error endpoint events: {len(error_events)}")

    return {
        "total_events": len(events),
        "test_events": len(test_events),
        "error_events": len(error_events)
    }

result = asyncio.run(end_to_end_test())
print(f"End-to-end test results: {result}")
```

[↑ Back to top](#testing--development-guide)

---

## Development Workflow

Best practices and patterns for developing custom fapilog components, from initial setup to production deployment.

### Custom Sink Development

**Complete workflow for building custom sinks:**

```python
# Step 1: Define your sink
from fapilog import Sink, register_sink
import asyncio
import aiohttp

@register_sink("webhook")
class WebhookSink(Sink):
    """Send logs to a webhook endpoint."""

    def __init__(self, url: str, timeout: int = 30, headers: dict = None):
        super().__init__()
        self.url = url
        self.timeout = timeout
        self.headers = headers or {}
        self._session = None

    async def _get_session(self):
        if self._session is None:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(self.timeout))
        return self._session

    async def write(self, event_dict):
        session = await self._get_session()
        try:
            async with session.post(
                self.url,
                json=event_dict,
                headers=self.headers
            ) as response:
                response.raise_for_status()
        except Exception as e:
            # Log error but don't break the application
            import logging
            logging.getLogger(__name__).error(f"Webhook sink failed: {e}")

    async def close(self):
        if self._session:
            await self._session.close()

# Step 2: Test your sink
from fapilog.testing import SinkTestFramework

async def test_webhook_sink():
    framework = SinkTestFramework()

    # Validate interface
    assert framework.validate_sink_interface(WebhookSink)

    # Test instantiation
    sink = framework.create_test_sink(
        WebhookSink,
        url="https://httpbin.org/post",
        headers={"Authorization": "Bearer test-token"}
    )

    # Test writing
    test_events = [
        {"level": "info", "message": "Test webhook"},
        {"level": "error", "message": "Test error", "error": "timeout"}
    ]

    success = await framework.test_sink_write(sink, test_events)
    await sink.close()

    return success

# Step 3: Performance test
from fapilog.testing import SinkPerformanceTester

async def performance_test_webhook():
    tester = SinkPerformanceTester()
    sink = WebhookSink("https://httpbin.org/post")

    try:
        # Test throughput
        throughput = await tester.test_throughput(sink, num_events=100)
        print(f"Webhook throughput: {throughput:.2f} events/sec")

        # Test latency
        latency = await tester.test_latency(sink, num_samples=50)
        print(f"Webhook latency: {latency:.3f}ms")

    finally:
        await sink.close()

# Step 4: Integration test
async def integration_test_webhook():
    from fapilog import configure_logging, log

    # Configure with your sink
    sink = WebhookSink("https://httpbin.org/post")
    configure_logging(sinks=[sink])

    # Test in real usage
    log.info("Integration test", component="webhook_sink")
    log.warning("Test warning", severity="medium")

    await sink.close()

# Run all tests
async def run_all_tests():
    print("=== Webhook Sink Development Tests ===")

    print("1. Interface validation...")
    assert await test_webhook_sink()
    print("✅ Interface test passed")

    print("2. Performance testing...")
    await performance_test_webhook()
    print("✅ Performance test completed")

    print("3. Integration testing...")
    await integration_test_webhook()
    print("✅ Integration test completed")

asyncio.run(run_all_tests())
```

### Debugging Development Issues

**Common development debugging patterns:**

```python
from fapilog.testing import SinkDebugger
from fapilog import register_sink

# Debug sink registration
@register_sink("debug_sink")
class DebugSink(Sink):
    async def write(self, event_dict):
        print(f"Debug: {event_dict}")

# Check registration
print("=== Sink Registration Debug ===")
sinks = SinkDebugger.list_registered_sinks()
print(f"Registered sinks: {list(sinks.keys())}")

# Detailed debugging
SinkDebugger.print_sink_debug_info("debug_sink")

# Test URI parsing
uri = "debug_sink://test?param=value"
result = SinkDebugger.test_sink_uri_parsing(uri)
print(f"URI parsing success: {result['success']}")

# Debug configuration
debug_info = SinkDebugger.debug_sink_configuration(uri)
print(f"Configuration status: {debug_info['overall_status']}")
```

### Error Handling Patterns

**Robust error handling in custom components:**

```python
from fapilog import Sink
from fapilog.exceptions import SinkError
import logging

class RobustSink(Sink):
    """Example of proper error handling in sinks."""

    def __init__(self, max_retries: int = 3):
        super().__init__()
        self.max_retries = max_retries
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def write(self, event_dict):
        """Write with retry logic and proper error handling."""
        retry_count = 0

        while retry_count <= self.max_retries:
            try:
                # Attempt to write
                await self._write_implementation(event_dict)
                return  # Success

            except Exception as e:
                retry_count += 1

                if retry_count > self.max_retries:
                    # Log error but don't break the application
                    self.logger.error(
                        f"Sink write failed after {self.max_retries} retries",
                        extra={
                            "error": str(e),
                            "event_level": event_dict.get("level"),
                            "sink_type": self.__class__.__name__
                        }
                    )
                    # Don't re-raise - logging should never break the app
                    return

                # Wait before retry
                await asyncio.sleep(0.1 * retry_count)

    async def _write_implementation(self, event_dict):
        """Override this with your actual write logic."""
        # Simulate potential failure
        import random
        if random.random() < 0.1:  # 10% failure rate
            raise Exception("Simulated write failure")
```

### Configuration Validation

**Validate configuration during development:**

```python
from fapilog.settings import LoggingSettings
from pydantic import ValidationError

def validate_development_config():
    """Validate configuration for development environment."""

    try:
        # Test development configuration
        dev_settings = LoggingSettings(
            level="DEBUG",
            sinks=["stdout", "file:///tmp/dev.log"],
            json_console="pretty",
            queue_enabled=False,  # Easier for debugging
            redact_patterns=["password", "token"]
        )
        print("✅ Development configuration valid")

    except ValidationError as e:
        print(f"❌ Configuration error: {e}")
        return False

    try:
        # Test production configuration
        prod_settings = LoggingSettings(
            level="INFO",
            sinks=["stdout", "loki://loki:3100"],
            json_console="json",
            queue_enabled=True,
            queue_maxsize=5000,
            enable_auto_redact_pii=True
        )
        print("✅ Production configuration valid")

    except ValidationError as e:
        print(f"❌ Production configuration error: {e}")
        return False

    return True

validate_development_config()
```

[↑ Back to top](#testing--development-guide)

---

## Configuration Testing

Validate configuration settings, test environment variables, and ensure proper configuration loading across different scenarios.

### Settings Validation

**Test configuration validation and error handling:**

```python
from fapilog.settings import LoggingSettings
from fapilog.exceptions import ConfigurationError
import pytest

def test_valid_configurations():
    """Test various valid configuration combinations."""

    # Basic valid configuration
    settings = LoggingSettings(
        level="INFO",
        sinks=["stdout"],
        json_console="auto"
    )
    assert settings.level == "INFO"

    # Advanced configuration
    settings = LoggingSettings(
        level="DEBUG",
        sinks=["stdout", "file:///var/log/app.log", "loki://localhost:3100"],
        redact_patterns=["password", "api_key", r"\d{4}-\d{4}-\d{4}-\d{4}"],
        queue_enabled=True,
        queue_maxsize=10000,
        enable_auto_redact_pii=True
    )
    assert len(settings.sinks) == 3
    assert len(settings.redact_patterns) == 3

def test_invalid_configurations():
    """Test configuration validation errors."""

    # Invalid log level
    with pytest.raises(ConfigurationError):
        LoggingSettings(level="INVALID_LEVEL")

    # Invalid queue size
    with pytest.raises(ConfigurationError):
        LoggingSettings(queue_maxsize=-1)

    # Invalid sampling rate
    with pytest.raises(ConfigurationError):
        LoggingSettings(sampling_rate=1.5)  # Must be 0.0-1.0

# Run tests
test_valid_configurations()
test_invalid_configurations()
print("✅ Configuration validation tests passed")
```

### Environment Variable Testing

**Test environment variable configuration:**

```python
import os
from fapilog.settings import LoggingSettings

def test_environment_variables():
    """Test configuration from environment variables."""

    # Set test environment variables
    test_env = {
        "FAPILOG_LEVEL": "DEBUG",
        "FAPILOG_SINKS": "stdout,file:///tmp/test.log",
        "FAPILOG_JSON_CONSOLE": "pretty",
        "FAPILOG_QUEUE_ENABLED": "true",
        "FAPILOG_QUEUE_MAXSIZE": "5000",
        "FAPILOG_REDACT_PATTERNS": "password,token,api_key"
    }

    # Backup original environment
    original_env = {}
    for key in test_env:
        original_env[key] = os.environ.get(key)

    try:
        # Set test environment
        for key, value in test_env.items():
            os.environ[key] = value

        # Create settings from environment
        settings = LoggingSettings()

        # Validate settings
        assert settings.level == "DEBUG"
        assert len(settings.sinks) == 2
        assert settings.json_console == "pretty"
        assert settings.queue_enabled is True
        assert settings.queue_maxsize == 5000
        assert "password" in settings.redact_patterns

        print("✅ Environment variable configuration test passed")

    finally:
        # Restore original environment
        for key, value in original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

test_environment_variables()
```

### Configuration Override Testing

**Test configuration override scenarios:**

```python
from fapilog.settings import LoggingSettings

def test_configuration_overrides():
    """Test configuration override scenarios."""

    # Base configuration
    base_settings = LoggingSettings(
        level="INFO",
        sinks=["stdout"],
        queue_enabled=False
    )

    # Override with specific values
    override_settings = LoggingSettings(
        **base_settings.model_dump(),
        level="DEBUG",  # Override level
        queue_enabled=True,  # Override queue
        queue_maxsize=2000  # Add new setting
    )

    assert override_settings.level == "DEBUG"
    assert override_settings.queue_enabled is True
    assert override_settings.queue_maxsize == 2000
    assert override_settings.sinks == ["stdout"]  # Preserved

    print("✅ Configuration override test passed")

test_configuration_overrides()
```

### Dynamic Configuration Testing

**Test dynamic configuration changes:**

```python
from fapilog.settings import LoggingSettings
from fapilog import configure_logging, log
from fapilog.testing import RecordingSink

def test_dynamic_configuration():
    """Test changing configuration at runtime."""

    # Initial configuration
    recording_sink = RecordingSink()
    configure_logging(sinks=[recording_sink])

    # Log with initial config
    log.info("Initial message")
    assert len(recording_sink.events) == 1

    # Reconfigure with different settings
    new_settings = LoggingSettings(
        level="WARNING",  # Higher level
        sinks=[recording_sink]
    )
    configure_logging(settings=new_settings)

    # Test new configuration
    log.info("This should be filtered")  # Below WARNING level
    log.warning("This should appear")

    # Should only have 2 events (initial + warning)
    assert len(recording_sink.events) == 2

    print("✅ Dynamic configuration test passed")

test_dynamic_configuration()
```

[↑ Back to top](#testing--development-guide)

---

## Error Handling & Recovery

Test error scenarios, validate recovery mechanisms, and ensure robust operation under failure conditions.

### Exception Testing

**Test custom exception handling:**

```python
from fapilog.exceptions import (
    FapilogError,
    ConfigurationError,
    SinkError,
    QueueError
)

def test_exception_hierarchy():
    """Test exception hierarchy and context."""

    # Test base exception
    base_error = FapilogError("Base error", {"component": "test"})
    assert str(base_error) == "Base error (context: component=test)"

    # Test configuration exception
    config_error = ConfigurationError(
        "Invalid setting",
        setting_name="level",
        provided_value="INVALID",
        expected_value="DEBUG|INFO|WARNING|ERROR|CRITICAL"
    )
    assert "Invalid setting" in str(config_error)
    assert config_error.context["setting_name"] == "level"

    # Test sink exception
    sink_error = SinkError(
        "Connection failed",
        sink_type="postgres",
        operation="connect",
        error_details={"host": "localhost", "port": 5432}
    )
    assert sink_error.context["sink_type"] == "postgres"

    print("✅ Exception hierarchy test passed")

test_exception_hierarchy()
```

### Sink Error Recovery

**Test sink error handling and recovery:**

```python
import asyncio
from fapilog import Sink
from fapilog.testing import FailingSink, RecordingSink

class RecoveringSink(Sink):
    """Sink that recovers from failures."""

    def __init__(self, backup_sink=None):
        super().__init__()
        self.backup_sink = backup_sink
        self.failure_count = 0
        self.recovery_threshold = 3

    async def write(self, event_dict):
        try:
            # Simulate occasional failures
            if self.failure_count < self.recovery_threshold:
                self.failure_count += 1
                raise Exception(f"Failure {self.failure_count}")

            # After threshold, "recover"
            print(f"Recovered! Processing: {event_dict['event']}")

        except Exception as e:
            # Use backup sink if available
            if self.backup_sink:
                await self.backup_sink.write(event_dict)
            else:
                # Log error but don't break the chain
                import logging
                logging.getLogger(__name__).error(f"Sink failed: {e}")

async def test_error_recovery():
    """Test error recovery mechanisms."""

    backup_sink = RecordingSink()
    recovering_sink = RecoveringSink(backup_sink=backup_sink)

    # Send events that will initially fail
    for i in range(5):
        event = {"level": "info", "event": f"Test message {i}"}
        await recovering_sink.write(event)

    # Check backup sink captured failed events
    assert len(backup_sink.events) == 3  # First 3 failures

    print("✅ Error recovery test passed")

asyncio.run(test_error_recovery())
```

### Queue Error Handling

**Test queue overflow and error scenarios:**

```python
from fapilog.settings import LoggingSettings
from fapilog import configure_logging, log
from fapilog.testing import SlowSink

def test_queue_overflow_handling():
    """Test queue overflow strategies."""

    # Configure small queue with slow sink
    slow_sink = SlowSink(delay_ms=100)
    settings = LoggingSettings(
        queue_enabled=True,
        queue_maxsize=5,  # Very small queue
        queue_overflow="drop",  # Drop on overflow
        sinks=[slow_sink]
    )

    configure_logging(settings=settings)

    # Send many messages quickly
    for i in range(20):
        log.info(f"Message {i}", test="queue_overflow")

    # Some messages should be dropped
    print("✅ Queue overflow test completed (some messages dropped)")

test_queue_overflow_handling()
```

### Graceful Degradation

**Test graceful degradation under failures:**

```python
import asyncio
from fapilog import Sink
from fapilog.testing import RecordingSink

class GracefulSink(Sink):
    """Sink that degrades gracefully under failure."""

    def __init__(self):
        super().__init__()
        self.fallback_sink = RecordingSink()
        self.error_count = 0
        self.max_errors = 3
        self.degraded_mode = False

    async def write(self, event_dict):
        if self.degraded_mode:
            # In degraded mode, use fallback
            await self.fallback_sink.write(event_dict)
            return

        try:
            # Simulate primary operation
            if self.error_count < self.max_errors:
                self.error_count += 1
                raise Exception("Primary sink failure")

            # Normal operation
            print(f"Primary: {event_dict['event']}")

        except Exception:
            self.error_count += 1

            if self.error_count >= self.max_errors:
                self.degraded_mode = True
                print("⚠️ Entering degraded mode")

            # Use fallback
            await self.fallback_sink.write(event_dict)

async def test_graceful_degradation():
    """Test graceful degradation behavior."""

    sink = GracefulSink()

    # Send events that trigger degradation
    for i in range(6):
        event = {"level": "info", "event": f"Test {i}"}
        await sink.write(event)

    # Check fallback captured events
    assert len(sink.fallback_sink.events) >= 3
    assert sink.degraded_mode is True

    print("✅ Graceful degradation test passed")

asyncio.run(test_graceful_degradation())
```

[↑ Back to top](#testing--development-guide)

---

## Production Monitoring

Monitor and debug fapilog components in production environments with comprehensive metrics and health checks.

### Metrics Collection Testing

**Test metrics collection and reporting:**

```python
from fapilog.settings import LoggingSettings
from fapilog._internal.metrics import get_metrics_collector
from fapilog import configure_logging, log

def test_metrics_collection():
    """Test metrics collection functionality."""

    # Configure with metrics enabled
    settings = LoggingSettings(
        metrics_enabled=True,
        metrics_sample_window=100,
        queue_enabled=True
    )

    configure_logging(settings=settings)

    # Generate some logs
    for i in range(50):
        log.info(f"Metrics test {i}", iteration=i)

    # Check metrics
    metrics = get_metrics_collector()
    if metrics and metrics.is_enabled():
        queue_metrics = metrics.get_queue_metrics()
        print(f"Queue size: {queue_metrics.size}")
        print(f"Total enqueued: {queue_metrics.total_enqueued}")
        print(f"Enqueue latency: {queue_metrics.enqueue_latency_ms:.3f}ms")

        # Get all metrics
        all_metrics = metrics.get_all_metrics()
        print(f"Available metrics: {list(all_metrics.keys())}")

        print("✅ Metrics collection test passed")
    else:
        print("❌ Metrics collection not available")

test_metrics_collection()
```

### Health Check Implementation

**Implement health checks for your sinks:**

```python
from fapilog import Sink
import asyncio

class HealthCheckableSink(Sink):
    """Sink with health check capabilities."""

    def __init__(self):
        super().__init__()
        self.last_write_time = None
        self.write_count = 0
        self.error_count = 0
        self.healthy = True

    async def write(self, event_dict):
        try:
            # Simulate write operation
            await asyncio.sleep(0.001)

            self.last_write_time = asyncio.get_event_loop().time()
            self.write_count += 1
            self.healthy = True

        except Exception as e:
            self.error_count += 1
            self.healthy = False
            raise

    def get_health_status(self):
        """Get health status for monitoring."""
        now = asyncio.get_event_loop().time()
        time_since_last_write = (
            now - self.last_write_time
            if self.last_write_time else float('inf')
        )

        return {
            "healthy": self.healthy,
            "write_count": self.write_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(self.write_count, 1),
            "time_since_last_write": time_since_last_write,
            "last_write_time": self.last_write_time
        }

async def test_health_checks():
    """Test health check functionality."""

    sink = HealthCheckableSink()

    # Write some events
    for i in range(10):
        await sink.write({"level": "info", "event": f"Health test {i}"})

    # Check health
    health = sink.get_health_status()
    print(f"Sink healthy: {health['healthy']}")
    print(f"Write count: {health['write_count']}")
    print(f"Error rate: {health['error_rate']:.2%}")

    assert health['healthy'] is True
    assert health['write_count'] == 10
    assert health['error_rate'] == 0.0

    print("✅ Health check test passed")

asyncio.run(test_health_checks())
```

### Performance Monitoring

**Monitor performance in production:**

```python
import time
import asyncio
from fapilog import Sink
from collections import deque

class PerformanceMonitoringSink(Sink):
    """Sink with built-in performance monitoring."""

    def __init__(self, sample_window=100):
        super().__init__()
        self.sample_window = sample_window
        self.write_times = deque(maxlen=sample_window)
        self.event_sizes = deque(maxlen=sample_window)
        self.total_events = 0

    async def write(self, event_dict):
        start_time = time.perf_counter()

        try:
            # Simulate write operation
            await asyncio.sleep(0.001)

            # Record performance metrics
            write_time = (time.perf_counter() - start_time) * 1000  # ms
            event_size = len(str(event_dict))

            self.write_times.append(write_time)
            self.event_sizes.append(event_size)
            self.total_events += 1

        except Exception:
            # Still record the attempt time
            write_time = (time.perf_counter() - start_time) * 1000
            self.write_times.append(write_time)
            raise

    def get_performance_stats(self):
        """Get performance statistics."""
        if not self.write_times:
            return {"no_data": True}

        avg_write_time = sum(self.write_times) / len(self.write_times)
        max_write_time = max(self.write_times)
        min_write_time = min(self.write_times)

        avg_event_size = sum(self.event_sizes) / len(self.event_sizes)

        # Calculate throughput (approximate)
        recent_count = min(len(self.write_times), 50)
        if recent_count > 1:
            recent_time = sum(list(self.write_times)[-recent_count:])
            throughput = (recent_count / recent_time) * 1000  # events/sec
        else:
            throughput = 0

        return {
            "total_events": self.total_events,
            "avg_write_time_ms": avg_write_time,
            "max_write_time_ms": max_write_time,
            "min_write_time_ms": min_write_time,
            "avg_event_size_bytes": avg_event_size,
            "estimated_throughput_eps": throughput
        }

async def test_performance_monitoring():
    """Test performance monitoring functionality."""

    sink = PerformanceMonitoringSink()

    # Write events and monitor performance
    for i in range(100):
        event = {
            "level": "info",
            "event": f"Performance test {i}",
            "data": "x" * (50 + i)  # Varying event sizes
        }
        await sink.write(event)

        # Print stats every 25 events
        if (i + 1) % 25 == 0:
            stats = sink.get_performance_stats()
            print(f"After {i+1} events:")
            print(f"  Avg write time: {stats['avg_write_time_ms']:.3f}ms")
            print(f"  Throughput: {stats['estimated_throughput_eps']:.1f} events/sec")

    # Final stats
    final_stats = sink.get_performance_stats()
    print(f"\nFinal performance stats:")
    print(f"  Total events: {final_stats['total_events']}")
    print(f"  Average write time: {final_stats['avg_write_time_ms']:.3f}ms")
    print(f"  Max write time: {final_stats['max_write_time_ms']:.3f}ms")
    print(f"  Average event size: {final_stats['avg_event_size_bytes']:.0f} bytes")

    print("✅ Performance monitoring test passed")

asyncio.run(test_performance_monitoring())
```

[↑ Back to top](#testing--development-guide)

---

## Troubleshooting

Common issues, debugging techniques, and solutions for fapilog development and testing.

### Common Testing Issues

**Resolve frequent testing problems:**

```python
# Issue 1: Sink not registered
from fapilog.testing import SinkDebugger

def debug_sink_registration():
    """Debug sink registration issues."""

    # Check what's registered
    sinks = SinkDebugger.list_registered_sinks()
    print(f"Registered sinks: {list(sinks.keys())}")

    # If your sink is missing:
    from fapilog import register_sink, Sink

    @register_sink("my_test_sink")
    class MyTestSink(Sink):
        async def write(self, event_dict):
            pass

    # Verify registration
    updated_sinks = SinkDebugger.list_registered_sinks()
    assert "my_test_sink" in updated_sinks
    print("✅ Sink registration fixed")

debug_sink_registration()
```

```python
# Issue 2: Async context problems
import asyncio
from fapilog.testing import SinkTestFramework

async def fix_async_testing():
    """Fix async testing context issues."""

    framework = SinkTestFramework()

    # Correct async testing pattern
    class AsyncTestSink(Sink):
        async def write(self, event_dict):
            # Ensure proper async/await usage
            await asyncio.sleep(0.001)

    # Test in proper async context
    sink = framework.create_test_sink(AsyncTestSink)
    success = await framework.test_sink_write(sink, [
        {"level": "info", "message": "Async test"}
    ])

    assert success
    print("✅ Async testing fixed")

asyncio.run(fix_async_testing())
```

### Performance Issues

**Debug and resolve performance problems:**

```python
from fapilog.testing import SinkPerformanceTester
import asyncio

async def debug_performance_issues():
    """Debug performance bottlenecks."""

    # Slow sink for demonstration
    class SlowSink(Sink):
        async def write(self, event_dict):
            # Simulate slow operation
            await asyncio.sleep(0.1)  # 100ms delay

    tester = SinkPerformanceTester()
    sink = SlowSink()

    # Identify bottleneck
    print("Testing throughput...")
    throughput = await tester.test_throughput(sink, num_events=10)
    print(f"Throughput: {throughput:.2f} events/sec")

    if throughput < 50:  # Less than 50 events/sec
        print("⚠️ Performance issue detected")

        # Test latency
        latency = await tester.test_latency(sink, num_samples=5)
        print(f"Average latency: {latency:.3f}ms")

        if latency > 50:  # More than 50ms
            print("💡 High latency detected - consider:")
            print("  - Async batching")
            print("  - Connection pooling")
            print("  - Parallel processing")

asyncio.run(debug_performance_issues())
```

### Configuration Issues

**Debug configuration problems:**

```python
from fapilog.settings import LoggingSettings
from fapilog.testing import SinkDebugger

def debug_configuration_issues():
    """Debug common configuration issues."""

    try:
        # Test problematic configuration
        settings = LoggingSettings(
            sinks=["nonexistent://uri"]
        )

        # Debug each sink
        for sink_uri in settings.sinks:
            if isinstance(sink_uri, str):
                result = SinkDebugger.test_sink_uri_parsing(sink_uri)
                if not result['success']:
                    print(f"❌ Sink URI issue: {sink_uri}")
                    print(f"   Error: {result['error']}")
                    print("💡 Solutions:")
                    print("   - Check sink is registered")
                    print("   - Verify URI format")
                    print("   - Install required dependencies")

    except Exception as e:
        print(f"Configuration error: {e}")

debug_configuration_issues()
```

### Memory Issues

**Debug memory leaks and usage:**

```python
import asyncio
from fapilog.testing import SinkPerformanceTester

async def debug_memory_issues():
    """Debug memory usage problems."""

    class MemoryLeakySink(Sink):
        def __init__(self):
            super().__init__()
            self.stored_events = []  # This could cause memory leaks

        async def write(self, event_dict):
            # Problematic: storing all events
            self.stored_events.append(event_dict)

    tester = SinkPerformanceTester()
    sink = MemoryLeakySink()

    # Test memory usage
    memory_result = await tester.test_memory_usage(sink, num_events=1000)

    if 'error' not in memory_result:
        memory_per_event = memory_result['memory_per_event_bytes']
        total_delta_mb = memory_result['memory_delta_bytes'] / 1024 / 1024

        print(f"Memory per event: {memory_per_event:.0f} bytes")
        print(f"Total memory delta: {total_delta_mb:.2f} MB")

        if memory_per_event > 1000:  # More than 1KB per event
            print("⚠️ High memory usage per event")
            print("💡 Consider:")
            print("  - Don't store events permanently")
            print("  - Use bounded collections")
            print("  - Implement cleanup logic")

asyncio.run(debug_memory_issues())
```

### Integration Issues

**Debug integration problems:**

```python
from fastapi import FastAPI
from fapilog import configure_logging, log
from fapilog.testing import RecordingSink

def debug_integration_issues():
    """Debug FastAPI integration issues."""

    app = FastAPI(title="Debug App")
    recording_sink = RecordingSink()

    try:
        # Configure logging
        configure_logging(app=app, sinks=[recording_sink])

        # Test logging
        log.info("Integration test")

        # Check if events were captured
        if len(recording_sink.events) == 0:
            print("❌ No events captured")
            print("💡 Check:")
            print("  - Sink configuration")
            print("  - Log level settings")
            print("  - Queue processing")
        else:
            print("✅ Integration working")

    except Exception as e:
        print(f"Integration error: {e}")
        print("💡 Common fixes:")
        print("  - Check FastAPI version compatibility")
        print("  - Verify middleware registration")
        print("  - Ensure proper async context")

debug_integration_issues()
```

### Debugging Checklist

**Systematic debugging approach:**

```python
def debugging_checklist():
    """Systematic debugging checklist."""

    print("=== Fapilog Debugging Checklist ===\n")

    # 1. Check registrations
    from fapilog.testing import SinkDebugger
    sinks = SinkDebugger.list_registered_sinks()
    print(f"1. Registered sinks: {list(sinks.keys())}")

    # 2. Validate configuration
    try:
        from fapilog.settings import LoggingSettings
        settings = LoggingSettings()
        print("2. ✅ Configuration valid")
    except Exception as e:
        print(f"2. ❌ Configuration error: {e}")

    # 3. Test basic logging
    try:
        from fapilog import configure_logging, log
        from fapilog.testing import RecordingSink

        recording_sink = RecordingSink()
        configure_logging(sinks=[recording_sink])
        log.info("Debug test")

        if len(recording_sink.events) > 0:
            print("3. ✅ Basic logging working")
        else:
            print("3. ❌ Basic logging not working")
    except Exception as e:
        print(f"3. ❌ Logging error: {e}")

    # 4. Check dependencies
    try:
        import structlog
        import pydantic
        print("4. ✅ Core dependencies available")
    except ImportError as e:
        print(f"4. ❌ Missing dependency: {e}")

    print("\n=== Debugging Complete ===")

debugging_checklist()
```

[↑ Back to top](#testing--development-guide)

---

## See Also

### Related Guides

- **[Configuration Guide](configuration.md)** - Environment setup and settings validation
- **[Sinks Guide](sinks.md)** - Custom sink development and integration
- **[Security & Redaction Guide](security.md)** - Data protection testing and validation
- **[FastAPI Integration Guide](fastapi-integration.md)** - Web application testing patterns

### Testing Resources

- **[API Reference](../api-reference.md)** - Complete testing API documentation
- **[Examples](../examples/index.md)** - Real-world testing examples
- **[Troubleshooting](../troubleshooting.md)** - Production issue resolution

### Development Tools

- **Performance testing examples** - `examples/11_performance_testing.py`
- **Sink testing examples** - `examples/sink_testing_examples.py`
- **Mock sink implementations** - `src/fapilog/testing/mock_sinks.py`

[↑ Back to top](#testing--development-guide)
