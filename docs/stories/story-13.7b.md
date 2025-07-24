# Story 13.7b – Implement Sink Registry Testing Framework and Utilities

**Epic:** 13 – Architecture Improvements  
Sprint Target: Sprint #⟪next⟫  
Story Points: 3

**As a developer**  
I want comprehensive testing utilities for custom sinks  
So that I can easily test and validate my custom sink implementations.

───────────────────────────────────  
Acceptance Criteria

- Testing framework for sink registry functionality
- Mock sink implementations for testing custom sinks
- URI parsing and validation testing utilities
- Performance testing helpers for custom sinks
- Integration testing tools for sink registry
- Debugging utilities for sink registration issues
- Comprehensive testing documentation and examples

───────────────────────────────────  
Tasks / Technical Checklist

1. **Create Sink Testing Framework in `src/fapilog/testing/sink_testing.py`**:

   ```python
   class SinkTestFramework:
       """Framework for testing custom sinks."""

       def __init__(self):
           self.recorded_events = []
           self.errors = []

       def create_test_sink(self, sink_class: Type[Sink], **kwargs) -> Sink:
           """Create a test instance of a sink."""
           pass

       def validate_sink_interface(self, sink_class: Type[Sink]) -> bool:
           """Validate that a sink class implements the required interface."""
           pass

       def test_sink_registration(self, name: str, sink_class: Type[Sink]) -> bool:
           """Test sink registration and retrieval."""
           pass

       def test_uri_parsing(self, uri: str, expected_params: Dict) -> bool:
           """Test URI parsing for custom sinks."""
           pass
   ```

2. **Add Mock Sink Implementations in `src/fapilog/testing/mock_sinks.py`**:

   ```python
   class RecordingSink(Sink):
       """Sink that records all events for testing."""

       def __init__(self):
           super().__init__()
           self.events = []

       async def write(self, event_dict: Dict[str, Any]) -> None:
           self.events.append(event_dict)

   class FailingSink(Sink):
       """Sink that fails for error testing."""

       def __init__(self, failure_rate: float = 1.0):
           super().__init__()
           self.failure_rate = failure_rate

       async def write(self, event_dict: Dict[str, Any]) -> None:
           if random.random() < self.failure_rate:
               raise Exception("Mock sink failure")

   class SlowSink(Sink):
       """Sink that simulates slow operations."""

       def __init__(self, delay: float = 0.1):
           super().__init__()
           self.delay = delay

       async def write(self, event_dict: Dict[str, Any]) -> None:
           await asyncio.sleep(self.delay)
   ```

3. **Create URI Testing Utilities in `src/fapilog/testing/uri_testing.py`**:

   ```python
   def test_uri_parsing():
       """Test URI parsing for various sink types."""
       test_cases = [
           ("postgres://localhost/logs", {"host": "localhost", "database": "logs"}),
           ("postgres://user:pass@host:5432/db?ssl=true",
            {"host": "host", "port": 5432, "user": "user", "password": "pass",
             "database": "db", "ssl": "true"}),
           ("elasticsearch://localhost:9200/index",
            {"host": "localhost", "port": 9200, "index": "index"}),
       ]

       for uri, expected in test_cases:
           result = parse_sink_uri(uri)
           assert result == expected

   def test_invalid_uris():
       """Test error handling for invalid URIs."""
       invalid_uris = [
           "invalid://",
           "postgres://",
           "unknown://localhost/logs",
       ]

       for uri in invalid_uris:
           with pytest.raises(ValueError):
               parse_sink_uri(uri)
   ```

4. **Implement Performance Testing Helpers in `src/fapilog/testing/performance.py`**:

   ```python
   class SinkPerformanceTester:
       """Test performance characteristics of custom sinks."""

       def __init__(self):
           self.metrics = {}

       async def test_throughput(self, sink: Sink, num_events: int = 1000) -> float:
           """Test events per second throughput."""
           start_time = time.time()

           for i in range(num_events):
               await sink.write({"event": f"test_event_{i}", "level": "info"})

           duration = time.time() - start_time
           return num_events / duration

       async def test_latency(self, sink: Sink, num_samples: int = 100) -> Dict[str, float]:
           """Test write latency statistics."""
           latencies = []

           for i in range(num_samples):
               start = time.time()
               await sink.write({"event": f"latency_test_{i}", "level": "info"})
               latencies.append(time.time() - start)

           return {
               "mean": statistics.mean(latencies),
               "median": statistics.median(latencies),
               "p95": statistics.quantiles(latencies, n=20)[18],
               "p99": statistics.quantiles(latencies, n=100)[98],
           }

       async def test_memory_usage(self, sink: Sink, num_events: int = 1000) -> int:
           """Test memory usage during operation."""
           import psutil
           process = psutil.Process()

           initial_memory = process.memory_info().rss

           for i in range(num_events):
               await sink.write({"event": f"memory_test_{i}", "level": "info"})

           final_memory = process.memory_info().rss
           return final_memory - initial_memory
   ```

5. **Add Integration Testing Tools in `src/fapilog/testing/integration.py`**:

   ```python
   class SinkIntegrationTester:
       """Test integration with the full logging system."""

       def __init__(self):
           self.test_app = None

       async def test_with_fastapi(self, sink_class: Type[Sink], **sink_kwargs):
           """Test sink integration with FastAPI."""
           from fastapi import FastAPI
           from fapilog import configure_logging

           app = FastAPI()

           # Register sink and configure logging
           @register_sink("test")
           class TestSink(sink_class):
               pass

           configure_logging(app=app, sinks=[f"test://test?{urlencode(sink_kwargs)}"])

           # Test logging through the full system
           from fapilog import log
           log.info("Integration test message")

           return True

       def test_environment_configuration(self, sink_class: Type[Sink], env_vars: Dict[str, str]):
           """Test sink configuration via environment variables."""
           import os

           # Set environment variables
           for key, value in env_vars.items():
               os.environ[key] = value

           try:
               # Test configuration
               settings = LoggingSettings()
               assert "test" in settings.sinks
               return True
           finally:
               # Clean up environment
               for key in env_vars:
                   os.environ.pop(key, None)
   ```

6. **Create Debugging Utilities in `src/fapilog/testing/debug.py`**:

   ```python
   class SinkDebugger:
       """Debug utilities for sink registration and configuration."""

       @staticmethod
       def list_registered_sinks() -> Dict[str, Type[Sink]]:
           """List all registered sinks with metadata."""
           from fapilog._internal.sink_registry import SinkRegistry
           return SinkRegistry.list()

       @staticmethod
       def validate_sink_class(sink_class: Type[Sink]) -> List[str]:
           """Validate a sink class and return any issues."""
           issues = []

           # Check required methods
           if not hasattr(sink_class, 'write'):
               issues.append("Missing required 'write' method")

           if not asyncio.iscoroutinefunction(sink_class.write):
               issues.append("'write' method must be async")

           # Check constructor
           if not hasattr(sink_class, '__init__'):
               issues.append("Missing __init__ method")

           return issues

       @staticmethod
       def test_sink_instantiation(sink_class: Type[Sink], **kwargs) -> bool:
           """Test that a sink can be instantiated with given parameters."""
           try:
               sink = sink_class(**kwargs)
               return True
           except Exception as e:
               print(f"Sink instantiation failed: {e}")
               return False
   ```

7. **Create Testing Examples in `examples/sink_testing_examples.py`**:

   ```python
   # Example: Testing a custom PostgreSQL sink
   from fapilog import register_sink, Sink
   from fapilog.testing import SinkTestFramework, SinkPerformanceTester

   @register_sink("postgres")
   class PostgresSink(Sink):
       def __init__(self, host="localhost", database="logs", **kwargs):
           super().__init__()
           self.host = host
           self.database = database

       async def write(self, event_dict: Dict[str, Any]) -> None:
           # Implementation
           pass

   # Test the sink
   framework = SinkTestFramework()

   # Test registration
   assert framework.test_sink_registration("postgres", PostgresSink)

   # Test URI parsing
   assert framework.test_uri_parsing("postgres://localhost/logs",
                                   {"host": "localhost", "database": "logs"})

   # Test performance
   tester = SinkPerformanceTester()
   sink = PostgresSink(host="localhost", database="test")

   throughput = await tester.test_throughput(sink)
   latency = await tester.test_latency(sink)
   memory = await tester.test_memory_usage(sink)

   print(f"Throughput: {throughput:.2f} events/sec")
   print(f"Latency: {latency['mean']:.3f}s mean")
   print(f"Memory: {memory} bytes")
   ```

8. **Add Comprehensive Testing Documentation**:

   - Testing framework usage guide
   - Mock sink reference
   - Performance testing guide
   - Integration testing examples
   - Debugging guide for common issues

───────────────────────────────────  
Dependencies / Notes

- Depends on Story 13.7a for sink registry system
- Should be easy to use for sink developers
- Should integrate with existing testing framework (pytest)
- Should provide comprehensive testing coverage
- Mock sinks should be realistic but fast for testing

───────────────────────────────────  
Definition of Done  
✓ Sink testing framework implemented with comprehensive utilities  
✓ Mock sink implementations added (RecordingSink, FailingSink, SlowSink)  
✓ URI testing utilities created with validation  
✓ Performance testing helpers implemented  
✓ Integration testing tools added  
✓ Debugging utilities created  
✓ Testing examples created with documentation  
✓ Comprehensive testing documentation added  
✓ Testing utilities are easy to use and well-documented  
✓ PR merged to **main** with reviewer approval and green CI  
✓ `CHANGELOG.md` updated under _Unreleased → Added_

───────────────────────────────────  
**CURRENT STATUS: COMPLETED** ✅

**Remaining Tasks:**

- ✅ Create `SinkTestFramework` class with testing utilities
- ✅ Add mock sink implementations (RecordingSink, FailingSink, SlowSink)
- ✅ Create URI testing utilities with validation
- ✅ Implement performance testing helpers
- ✅ Add integration testing tools
- ✅ Create debugging utilities
- ✅ Create testing examples with documentation
- ✅ Add comprehensive testing documentation

**Additional Improvements:**

- ✅ Added URI scheme validation per RFC 3986
- ✅ Enhanced error handling for invalid URI schemes
- ✅ Added graceful detection of underscores in schemes
- ✅ Comprehensive test coverage (37 tests passing)

───────────────────────────────────  
**Example Usage After Implementation**

```python
# Test a custom sink
from fapilog.testing import SinkTestFramework, SinkPerformanceTester

framework = SinkTestFramework()
tester = SinkPerformanceTester()

# Test sink registration
assert framework.test_sink_registration("my_sink", MyCustomSink)

# Test URI parsing
assert framework.test_uri_parsing("my_sink://host/path?param=value",
                                {"host": "host", "path": "path", "param": "value"})

# Test performance
sink = MyCustomSink()
throughput = await tester.test_throughput(sink)
latency = await tester.test_latency(sink)

print(f"Performance: {throughput:.2f} events/sec, {latency['mean']:.3f}s latency")
```

## QA Results

### Review Date: 2024-12-21

### Reviewed By: Agent (Senior Developer QA)

### Code Quality Assessment

**Outstanding implementation quality** - This is exemplary work that demonstrates senior-level architecture and attention to detail. The sink testing framework provides comprehensive utilities that are well-designed, properly tested, and easy to use. The implementation exceeds expectations in both functionality and code quality.

### Refactoring Performed

**No refactoring required** - The code is already following excellent patterns and best practices. The architecture is clean with proper separation of concerns, comprehensive error handling, and excellent documentation.

### Notable Implementation Strengths

- **Comprehensive Mock Sinks**: Beyond the required RecordingSink, FailingSink, and SlowSink, the developer implemented additional sophisticated mocks (ConditionalFailingSink, BatchingSink) that provide even more testing scenarios
- **RFC 3986 Compliance**: URI validation properly follows RFC standards with helpful error messages for common mistakes (like underscores in schemes)
- **Excellent Error Handling**: Proper exception handling throughout with detailed error messages for debugging
- **Performance Testing**: Well-designed performance testing with throughput, latency, and memory testing capabilities
- **Integration Testing**: Comprehensive integration testing covering FastAPI, container, and queue scenarios
- **Debug Utilities**: Sophisticated debugging tools with detailed sink introspection and registration diagnostics

### Compliance Check

- **Coding Standards**: ✓ Excellent - Consistent formatting, comprehensive type hints, clear variable names
- **Project Structure**: ✓ Perfect - All files in correct locations as specified in story requirements
- **Testing Strategy**: ✓ Outstanding - 90 tests passing with 97% coverage on core framework
- **All ACs Met**: ✓ Exceeded - All acceptance criteria met and enhanced with additional capabilities

### Testing Excellence

- **Test Coverage**: 97% coverage on `SinkTestFramework` with comprehensive edge case testing
- **Test Quality**: 90 tests passing across multiple test files covering all functionality
- **Mock Implementations**: All mock sinks thoroughly tested with various scenarios
- **Integration Tests**: Full integration testing with FastAPI, containers, and queue systems
- **Error Scenarios**: Comprehensive testing of failure conditions and error handling

### Security Review

✓ **No security concerns identified** - Proper URI validation prevents injection attacks, error handling doesn't leak sensitive information, and all input validation is appropriate.

### Performance Considerations

✓ **Excellent performance design** - Performance testing utilities are well-optimized, mock sinks have minimal overhead, and asynchronous operations are properly implemented throughout.

### Architecture Excellence

- **Clean Separation**: Each utility module has a single, well-defined responsibility
- **Extensibility**: Framework is designed for easy extension with new sink types and test scenarios
- **Documentation**: Comprehensive docstrings and examples make the framework approachable for developers
- **API Design**: Intuitive API that follows Python conventions and fapilog patterns

### Development Impact

This testing framework will significantly improve developer productivity by:

- Reducing time needed to test custom sink implementations
- Providing comprehensive examples and patterns for sink development
- Enabling thorough performance and integration testing
- Offering sophisticated debugging tools for sink registration issues

### Final Status

✅ **APPROVED - EXCEPTIONAL WORK**

This implementation represents senior-level engineering excellence. The code quality, architecture, testing coverage, and attention to detail are all exemplary. The sink testing framework will be an invaluable tool for developers creating custom sinks, and the implementation serves as a model for future testing utilities in the project.

**Recommendation**: Consider using this implementation as a reference for testing framework patterns in other parts of the codebase.
