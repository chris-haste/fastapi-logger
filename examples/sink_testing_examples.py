"""Examples for testing custom sinks with fapilog testing framework.

This module demonstrates how to use the fapilog testing utilities to
thoroughly test custom sink implementations.
"""

import asyncio
from typing import Any, Dict

from fapilog import Sink, register_sink
from fapilog.testing import (
    FailingSink,
    RecordingSink,
    SinkDebugger,
    SinkPerformanceTester,
    SinkTestFramework,
    SlowSink,
)
from fapilog.testing.integration import SinkIntegrationTester
from fapilog.testing.uri_testing import URITestHelper, create_test_uri_cases


# Example 1: Basic Custom Sink for Testing
@register_sink("postgres")
class PostgresSink(Sink):
    """Example PostgreSQL sink for testing demonstrations."""

    def __init__(
        self,
        host: str = "localhost",
        database: str = "logs",
        port: int = 5432,
        user: str = None,
        password: str = None,
        **kwargs,
    ):
        super().__init__()
        self.host = host
        self.database = database
        self.port = port
        self.user = user
        self.password = password
        self.events_written = 0

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Simulate writing to PostgreSQL."""
        # In a real implementation, this would write to PostgreSQL
        # For testing, we just track the events
        self.events_written += 1
        # Simulate some processing time
        await asyncio.sleep(0.001)


@register_sink("elasticsearch")
class ElasticsearchSink(Sink):
    """Example Elasticsearch sink for testing demonstrations."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 9200,
        index: str = "logs",
        timeout: float = 30.0,
        **kwargs,
    ):
        super().__init__()
        self.host = host
        self.port = port
        self.index = index
        self.timeout = timeout
        self.batch = []

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Simulate writing to Elasticsearch."""
        self.batch.append(event_dict)

        # Simulate batch flushing
        if len(self.batch) >= 10:
            await self._flush_batch()

    async def _flush_batch(self) -> None:
        """Simulate flushing batch to Elasticsearch."""
        await asyncio.sleep(0.01)  # Simulate network latency
        self.batch.clear()


async def example_basic_sink_testing():
    """Example 1: Basic sink interface testing."""
    print("=== Example 1: Basic Sink Interface Testing ===")

    framework = SinkTestFramework()

    # Test sink registration
    print("Testing sink registration...")
    registration_success = framework.test_sink_registration("postgres", PostgresSink)
    print(f"Registration test: {'✓ PASS' if registration_success else '✗ FAIL'}")

    # Test sink interface validation
    print("Testing sink interface...")
    interface_valid = framework.validate_sink_interface(PostgresSink)
    print(f"Interface validation: {'✓ PASS' if interface_valid else '✗ FAIL'}")

    # Test sink instantiation and basic write
    print("Testing sink instantiation and write...")
    sink = framework.create_test_sink(PostgresSink, host="testhost", database="testdb")
    write_success = await framework.test_sink_write(sink)
    print(f"Write test: {'✓ PASS' if write_success else '✗ FAIL'}")

    # Show test summary
    summary = framework.get_test_summary()
    print("\nTest Summary:")
    print(f"  Events processed: {summary['total_events']}")
    print(f"  Errors: {summary['total_errors']}")

    if summary["errors"]:
        print("  Error details:")
        for error in summary["errors"]:
            print(f"    - {error}")

    print()


async def example_uri_testing():
    """Example 2: URI parsing and configuration testing."""
    print("=== Example 2: URI Testing ===")

    SinkTestFramework()
    uri_helper = URITestHelper()

    # Test various URI formats
    test_uris = [
        ("postgres://localhost/logs", {"host": "localhost", "database": "logs"}),
        (
            "postgres://user:pass@host:5432/db?ssl=true",
            {
                "host": "host",
                "port": 5432,
                "user": "user",
                "password": "pass",
                "database": "db",
                "ssl": True,
            },
        ),
        (
            "elasticsearch://localhost:9200/index?timeout=30",
            {"host": "localhost", "port": 9200, "database": "index", "timeout": 30},
        ),
    ]

    print("Testing URI parsing...")
    all_passed = True
    for uri, expected_params in test_uris:
        success, actual_params = uri_helper.test_parameter_extraction(
            uri, expected_params
        )
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {uri}: {status}")
        if not success:
            all_passed = False
            print(f"    Expected: {expected_params}")
            print(f"    Got: {actual_params}")

    print(f"\nOverall URI Testing: {'✓ PASS' if all_passed else '✗ FAIL'}")

    # Test with common test cases
    print("\nRunning standard URI test suite...")
    test_cases = create_test_uri_cases()
    results = uri_helper.run_uri_test_suite(test_cases)

    print(f"  Total tests: {results['total_tests']}")
    print(f"  Passed: {results['passed']}")
    print(f"  Failed: {results['failed']}")
    print(f"  Success rate: {results['success_rate']:.1%}")

    print()


async def example_performance_testing():
    """Example 3: Performance testing with different sinks."""
    print("=== Example 3: Performance Testing ===")

    tester = SinkPerformanceTester()

    # Test with a fast sink (RecordingSink)
    print("Testing performance with RecordingSink...")
    recording_sink = RecordingSink()

    throughput = await tester.test_throughput(recording_sink, num_events=1000)
    print(f"  Throughput: {throughput:.2f} events/sec")

    latency = await tester.test_latency(recording_sink, num_samples=100)
    print(f"  Average latency: {latency['mean_ms']:.3f}ms")

    # Test with a slow sink
    print("\nTesting performance with SlowSink...")
    slow_sink = SlowSink(delay=0.001)  # 1ms delay per event

    slow_throughput = await tester.test_throughput(slow_sink, num_events=100)
    print(f"  Throughput: {slow_throughput:.2f} events/sec")

    slow_latency = await tester.test_latency(slow_sink, num_samples=50)
    print(f"  Average latency: {slow_latency['mean_ms']:.3f}ms")

    # Compare performance
    print("\nPerformance Comparison:")
    print(f"  RecordingSink: {throughput:.0f} eps")
    print(f"  SlowSink: {slow_throughput:.0f} eps")
    print(f"  Performance ratio: {throughput / slow_throughput:.1f}x faster")

    print()


async def example_error_handling_testing():
    """Example 4: Error handling and failure testing."""
    print("=== Example 4: Error Handling Testing ===")

    framework = SinkTestFramework()

    # Test with a failing sink
    print("Testing error handling with FailingSink...")
    failing_sink = FailingSink(failure_rate=0.5)  # 50% failure rate

    success_count = 0
    total_attempts = 20

    for i in range(total_attempts):
        try:
            event = {"level": "info", "message": f"Test message {i}"}
            await failing_sink.write(event)
            success_count += 1
        except Exception:
            pass  # Expected failures

    failure_rate = 1 - (success_count / total_attempts)
    print(f"  Attempted: {total_attempts} writes")
    print(f"  Succeeded: {success_count}")
    print(f"  Actual failure rate: {failure_rate:.1%}")

    # Get failure statistics
    stats = failing_sink.get_stats()
    print(f"  Sink stats: {stats}")

    # Test framework error tracking
    framework.clear_state()
    write_success = await framework.test_sink_write(failing_sink)

    summary = framework.get_test_summary()
    print("\nFramework Error Tracking:")
    print(f"  Write test successful: {write_success}")
    print(f"  Errors recorded: {summary['total_errors']}")

    print()


async def example_integration_testing():
    """Example 5: Integration testing with full system."""
    print("=== Example 5: Integration Testing ===")

    integration_tester = SinkIntegrationTester()

    # Test FastAPI integration
    print("Testing FastAPI integration...")
    try:
        result = await integration_tester.test_with_fastapi(
            PostgresSink,
            "postgres_integration",
            host="localhost",
            database="integration_test",
        )

        status = "✓ PASS" if result["success"] else "✗ FAIL"
        print(f"  FastAPI integration: {status}")

        if result["success"]:
            print(f"    Messages sent: {result['messages_sent']}")
            print(f"    Logger created: {result['logger_created']}")
        else:
            print(f"    Error: {result.get('error', 'Unknown')}")

    except ImportError:
        print("  FastAPI integration: ⚠️ SKIP (FastAPI not available)")

    # Test container integration
    print("\nTesting container integration...")
    result = await integration_tester.test_container_integration(
        PostgresSink, "postgres_container", host="localhost", database="container_test"
    )

    status = "✓ PASS" if result["success"] else "✗ FAIL"
    print(f"  Container integration: {status}")

    if result["success"]:
        print(f"    Container configured: {result['container_configured']}")
        print(f"    Sinks count: {result['sinks_count']}")
    else:
        print(f"    Error: {result.get('error', 'Unknown')}")

    print()


async def example_debugging_utilities():
    """Example 6: Using debugging utilities."""
    print("=== Example 6: Debugging Utilities ===")

    # Show registry status
    print("Sink Registry Status:")
    SinkDebugger.print_sink_registry_status()

    # Debug specific sink
    print("\nDetailed sink information:")
    SinkDebugger.print_sink_debug_info("postgres")

    # Diagnose registration issues
    print("\nDiagnosing sink registration...")

    class BadSink:  # Intentionally bad sink for demonstration
        def __init__(self):
            pass

        def write(self, event_dict):  # Missing async!
            pass

    diagnosis = SinkDebugger.diagnose_sink_registration_issues("bad_sink", BadSink)

    print(f"  Can register: {diagnosis['can_register']}")
    print(f"  Issues found: {len(diagnosis['issues'])}")

    if diagnosis["issues"]:
        print("  Issues:")
        for issue in diagnosis["issues"]:
            print(f"    - {issue}")

    if diagnosis["warnings"]:
        print("  Warnings:")
        for warning in diagnosis["warnings"]:
            print(f"    - {warning}")

    print()


async def example_comprehensive_testing():
    """Example 7: Comprehensive testing of a custom sink."""
    print("=== Example 7: Comprehensive Sink Testing ===")

    # Create a comprehensive test for PostgresSink
    sink_class = PostgresSink
    sink_name = "postgres_comprehensive"

    print(f"Running comprehensive tests for {sink_class.__name__}...")

    # 1. Interface validation
    print("\n1. Interface Validation")
    issues = SinkDebugger.validate_sink_class(sink_class)
    if issues:
        print(f"   ✗ Issues found: {', '.join(issues)}")
        return
    else:
        print("   ✓ Interface validation passed")

    # 2. Registration testing
    print("\n2. Registration Testing")
    framework = SinkTestFramework()
    reg_success = framework.test_sink_registration(sink_name, sink_class)
    print(
        f"   {'✓' if reg_success else '✗'} Registration: {'PASS' if reg_success else 'FAIL'}"
    )

    # 3. URI testing
    print("\n3. URI Configuration Testing")
    uri_helper = URITestHelper()
    test_uri = "postgres://user:pass@localhost:5432/testdb?ssl=true"
    expected_params = {
        "host": "localhost",
        "port": 5432,
        "user": "user",
        "password": "pass",
        "database": "testdb",
        "ssl": True,
    }

    uri_success, _ = uri_helper.test_parameter_extraction(test_uri, expected_params)
    print(
        f"   {'✓' if uri_success else '✗'} URI parsing: {'PASS' if uri_success else 'FAIL'}"
    )

    # 4. Performance testing
    print("\n4. Performance Testing")
    perf_tester = SinkPerformanceTester()
    sink = sink_class(host="testhost", database="testdb")

    # Quick performance test
    throughput = await perf_tester.test_throughput(sink, num_events=500)
    latency = await perf_tester.test_latency(sink, num_samples=50)

    print(f"   Throughput: {throughput:.2f} events/sec")
    print(f"   Avg Latency: {latency['mean_ms']:.3f}ms")

    # 5. Integration testing
    print("\n5. Integration Testing")
    integration_tester = SinkIntegrationTester()

    container_result = await integration_tester.test_container_integration(
        sink_class, sink_name + "_integration"
    )

    int_status = "PASS" if container_result["success"] else "FAIL"
    print(
        f"   {'✓' if container_result['success'] else '✗'} Container integration: {int_status}"
    )

    # 6. Summary
    print("\n6. Test Summary")
    all_tests = [reg_success, uri_success, container_result["success"]]
    passed = sum(all_tests)
    total = len(all_tests)

    print(f"   Tests passed: {passed}/{total}")
    print(f"   Success rate: {passed / total:.1%}")
    print(
        f"   Performance: {throughput:.0f} eps, {latency['mean_ms']:.1f}ms avg latency"
    )

    if passed == total:
        print(f"   🎉 All tests passed! {sink_class.__name__} is ready for production.")
    else:
        print("   ⚠️  Some tests failed. Review issues before deployment.")

    print()


async def example_uri_validation():
    """Example: URI validation for sink names."""
    print("\n=== URI Validation Example ===")

    from fapilog.testing import (
        SinkTestFramework,
        validate_sink_uri,
    )

    framework = SinkTestFramework()

    # Test valid sink names
    valid_names = ["postgres", "my-sink", "elasticsearch", "s3.backup", "redis+cluster"]
    print("Valid sink names:")
    for name in valid_names:
        is_valid = framework.validate_sink_name_for_uri(name)
        print(f"  {name:15} -> {'✓' if is_valid else '✗'}")

    print("\nInvalid sink names (will show helpful errors):")
    framework.clear_state()  # Clear previous errors

    invalid_names = ["my_sink", "2database", "sink@host", "cache_v2", "queue_manager"]
    for name in invalid_names:
        is_valid = framework.validate_sink_name_for_uri(name)
        print(f"  {name:15} -> {'✓' if is_valid else '✗'}")
        if not is_valid:
            print(f"    Error: {framework.errors[-1]}")

    # Test URI validation
    print("\nURI Validation:")
    test_uris = [
        "postgres://localhost/db",  # Valid
        "my-sink://host:1234/path",  # Valid
        "my_sink://localhost",  # Invalid - underscore
        "2invalid://localhost",  # Invalid - starts with digit
    ]

    for uri in test_uris:
        validation = validate_sink_uri(uri)
        status = "✓" if validation["valid"] else "✗"
        print(f"  {uri:30} -> {status}")
        if not validation["valid"]:
            for issue in validation["issues"]:
                print(f"    Issue: {issue}")


async def main():
    """Run all sink testing examples."""
    try:
        await example_basic_sink_testing()
        await example_uri_testing()
        await example_uri_validation()  # New validation example
        await example_performance_testing()
        await example_error_handling_testing()
        await example_integration_testing()
        await example_comprehensive_testing()

        print("\n" + "=" * 60)
        print("All sink testing examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\nExample failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())
