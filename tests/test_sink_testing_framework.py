"""Tests for the sink testing framework."""

import asyncio
from typing import Any, Dict

import pytest

from fapilog.core.registries.sink_registry import SinkRegistry
from fapilog.sinks import Sink
from fapilog.testing import (
    FailingSink,
    RecordingSink,
    SinkDebugger,
    SinkPerformanceTester,
    SinkTestFramework,
    SlowSink,
)
from fapilog.testing.integration import SinkIntegrationTester
from fapilog.testing.uri_testing import URITestHelper, parse_sink_uri


class MockSink(Sink):
    """Mock sink for testing purposes."""

    def __init__(self, should_fail: bool = False, **kwargs: Any) -> None:
        super().__init__()
        self.should_fail = should_fail
        self.events = []
        # Store any additional URI parameters for testing
        self.uri_params = kwargs

    async def write(self, event_dict: Dict[str, Any]) -> None:
        if self.should_fail:
            raise Exception("Test sink failure")
        self.events.append(event_dict)


class FailingConstructorSink(Sink):
    """Sink that fails during construction for testing."""

    def __init__(self, valid_param: bool = True):
        if not valid_param:
            raise ValueError("Invalid parameter for testing")
        super().__init__()

    async def write(self, event_dict: Dict[str, Any]) -> None:
        pass


class BadSink:
    """Intentionally bad sink for testing validation."""

    def __init__(self):
        pass

    def write(self, event_dict):  # Missing async
        pass


@pytest.fixture
def framework():
    """Create a fresh SinkTestFramework for each test."""
    return SinkTestFramework()


@pytest.fixture
def performance_tester():
    """Create a fresh SinkPerformanceTester for each test."""
    return SinkPerformanceTester()


@pytest.fixture
def uri_helper():
    """Create a fresh URITestHelper for each test."""
    return URITestHelper()


@pytest.fixture
def integration_tester():
    """Create a fresh SinkIntegrationTester for each test."""
    return SinkIntegrationTester()


@pytest.fixture(autouse=True)
def cleanup_registry():
    """Clean up sink registry after each test."""
    original_sinks = SinkRegistry._sinks.copy()
    yield
    SinkRegistry._sinks = original_sinks


class TestSinkTestFramework:
    """Test the SinkTestFramework class."""

    def test_create_test_sink(self, framework):
        """Test creating test sink instances."""
        sink = framework.create_test_sink(MockSink)
        assert isinstance(sink, MockSink)

    def test_create_test_sink_invalid_class(self, framework):
        """Test creating test sink with invalid class."""
        with pytest.raises(ValueError):
            framework.create_test_sink(str)

    def test_validate_sink_interface_valid(self, framework):
        """Test validating valid sink interface."""
        assert framework.validate_sink_interface(MockSink) is True

    def test_validate_sink_interface_invalid(self, framework):
        """Test validating invalid sink interface."""

        class InvalidSink:
            pass

        assert framework.validate_sink_interface(InvalidSink) is False

    def test_sink_registration(self, framework):
        """Test sink registration and retrieval."""
        result = framework.test_sink_registration("test-sink", MockSink)
        assert result is True

    def test_uri_parsing_success(self, framework):
        """Test successful URI parsing."""
        expected = {"host": "localhost", "port": 5432}
        result = framework.test_uri_parsing("test://localhost:5432", expected)
        assert result is True

    def test_uri_parsing_failure(self, framework):
        """Test failed URI parsing."""
        expected = {"host": "localhost", "port": 5432}
        result = framework.test_uri_parsing("test://localhost:3306", expected)
        assert result is False

    def test_sink_write_success(self, framework):
        """Test successful sink write."""
        sink = MockSink()
        result = asyncio.run(framework.test_sink_write(sink, {"test": "data"}))
        assert result is True
        assert len(sink.events) == 1

    def test_sink_write_failure(self, framework):
        """Test failed sink write."""
        sink = MockSink(should_fail=True)
        result = asyncio.run(framework.test_sink_write(sink, {"test": "data"}))
        assert result is False

    def test_clear_state(self, framework):
        """Test clearing framework state."""
        framework.recorded_events.append({"test": "data"})
        framework.errors.append("test error")

        framework.clear_state()

        assert len(framework.recorded_events) == 0
        assert len(framework.errors) == 0

    def test_get_test_summary(self, framework):
        """Test getting test summary."""
        framework.recorded_events.append({"test": "data"})
        framework.errors.append("test error")

        summary = framework.get_test_summary()

        assert summary["total_events"] == 1
        assert summary["total_errors"] == 1
        assert len(summary["errors"]) == 1
        assert len(summary["last_events"]) == 1

    def test_validate_sink_name_for_uri_valid(self, framework):
        """Test validating valid sink names for URI usage."""
        assert framework.validate_sink_name_for_uri("postgres") is True
        assert framework.validate_sink_name_for_uri("my-sink") is True
        assert framework.validate_sink_name_for_uri("sink.v2") is True
        assert framework.validate_sink_name_for_uri("s3+secure") is True

    def test_validate_sink_name_for_uri_invalid(self, framework):
        """Test validating invalid sink names for URI usage."""
        # Underscore not allowed
        assert framework.validate_sink_name_for_uri("my_sink") is False
        # Can't start with digit
        assert framework.validate_sink_name_for_uri("2sink") is False
        # Special characters not allowed
        assert framework.validate_sink_name_for_uri("sink@host") is False
        assert len(framework.errors) == 3

    def test_uri_parsing_with_invalid_scheme(self, framework):
        """Test URI parsing fails gracefully with invalid schemes."""
        expected = {"host": "localhost"}
        # Use a scheme with underscore which is actually invalid
        result = framework.test_uri_parsing("my_sink://localhost", expected)
        assert result is False
        assert len(framework.errors) > 0
        error_msg = str(framework.errors[-1])
        assert "underscores (_) are not allowed" in error_msg


class TestMockSinks:
    """Test the mock sink implementations."""

    @pytest.mark.asyncio
    async def test_recording_sink(self):
        """Test RecordingSink functionality."""
        sink = RecordingSink()

        event = {"level": "info", "message": "test"}
        await sink.write(event)

        assert len(sink.events) == 1
        assert sink.events[0]["message"] == "test"
        assert "_recorded_at" in sink.events[0]
        assert "_write_count" in sink.events[0]

        # Test filtering
        await sink.write({"level": "error", "message": "error test"})
        info_events = sink.get_events("info")
        assert len(info_events) == 1

        # Test last event
        last_event = sink.get_last_event()
        assert last_event["level"] == "error"

        # Test clear
        sink.clear()
        assert len(sink.events) == 0

    @pytest.mark.asyncio
    async def test_failing_sink(self):
        """Test FailingSink functionality."""
        sink = FailingSink(failure_rate=1.0)  # Always fail

        with pytest.raises(Exception):  # noqa: B017
            await sink.write({"test": "data"})

        stats = sink.get_stats()
        assert stats["attempts"] == 1
        assert stats["failures"] == 1
        assert stats["successes"] == 0

        # Test partial failure
        sink = FailingSink(failure_rate=0.0)  # Never fail
        await sink.write({"test": "data"})

        stats = sink.get_stats()
        assert stats["successes"] == 1

    @pytest.mark.asyncio
    async def test_slow_sink(self):
        """Test SlowSink functionality."""
        sink = SlowSink(delay=0.001)  # 1ms delay

        import time

        start = time.time()
        await sink.write({"test": "data"})
        duration = time.time() - start

        assert duration >= 0.001

        stats = sink.get_performance_stats()
        assert stats["write_count"] == 1
        assert stats["configured_delay"] == 0.001


class TestURITesting:
    """Test URI testing functionality."""

    def test_parse_sink_uri_basic(self):
        """Test basic URI parsing."""

        result = parse_sink_uri("postgres://localhost/logs")
        assert "host" in result
        assert result["host"] == "localhost"

    def test_parse_sink_uri_complex(self):
        """Test complex URI parsing."""

        uri = "postgres://user:pass@localhost:5432/logs?ssl=true&timeout=30"
        result = parse_sink_uri(uri)

        assert result["host"] == "localhost"
        assert result["port"] == 5432
        assert result["user"] == "user"
        assert result["password"] == "pass"
        assert result["database"] == "logs"
        assert result["ssl"] is True
        assert result["timeout"] == 30

    def test_parse_sink_uri_invalid(self):
        """Test invalid URI parsing."""

        with pytest.raises(ValueError):
            parse_sink_uri("invalid-uri")

    def test_validate_scheme_valid(self):
        """Test valid URI scheme validation."""
        from fapilog.testing import validate_uri_scheme

        assert validate_uri_scheme("postgres") is True
        assert validate_uri_scheme("my-sink") is True
        assert validate_uri_scheme("s3.backup") is True
        assert validate_uri_scheme("redis+cluster") is True

    def test_validate_scheme_invalid(self):
        """Test invalid URI scheme validation."""
        from fapilog.testing import validate_uri_scheme

        assert validate_uri_scheme("my_sink") is False  # underscore
        assert validate_uri_scheme("2sink") is False  # starts with digit
        assert validate_uri_scheme("sink@host") is False  # special char
        assert validate_uri_scheme("") is False  # empty

    def test_validate_sink_uri_comprehensive(self):
        """Test comprehensive URI validation."""
        from fapilog.testing import validate_sink_uri

        # Valid URI
        result = validate_sink_uri("postgres://localhost/db")
        assert result["valid"] is True
        assert len(result["issues"]) == 0

        # Invalid scheme
        result = validate_sink_uri("my_sink://localhost")
        assert result["valid"] is False
        assert any("underscores" in issue for issue in result["issues"])

        # No scheme
        result = validate_sink_uri("localhost/db")
        assert result["valid"] is False
        assert any("must have a scheme" in issue for issue in result["issues"])


class TestPerformanceTesting:
    """Test performance testing functionality."""

    @pytest.fixture
    def performance_tester(self):
        """Create a performance tester instance."""
        from fapilog.testing import SinkPerformanceTester

        return SinkPerformanceTester()

    @pytest.mark.asyncio
    async def test_throughput_testing(self, performance_tester):
        """Test throughput measurement."""
        from fapilog.testing import RecordingSink

        sink = RecordingSink()
        throughput = await performance_tester.test_throughput(sink, num_events=10)

        assert throughput > 0
        assert len(sink.events) == 10

    @pytest.mark.asyncio
    async def test_latency_testing(self, performance_tester):
        """Test latency measurement."""
        from fapilog.testing import RecordingSink

        sink = RecordingSink()
        latency = await performance_tester.test_latency(sink, num_samples=5)

        assert "mean_ms" in latency
        assert "median_ms" in latency
        assert latency["mean_ms"] >= 0

    @pytest.mark.asyncio
    async def test_memory_testing(self, performance_tester):
        """Test memory usage measurement."""
        from fapilog.testing import RecordingSink

        sink = RecordingSink()
        memory = await performance_tester.test_memory_usage(sink, num_events=10)

        assert "memory_delta_bytes" in memory
        assert "num_events" in memory


class TestDebugging:
    """Test debugging functionality."""

    def test_list_registered_sinks(self):
        """Test listing registered sinks."""
        from fapilog.core.registries.sink_registry import SinkRegistry

        initial_count = len(SinkDebugger.list_registered_sinks())

        # Register a test sink
        SinkRegistry.register("debug-test", MockSink)

        sinks = SinkDebugger.list_registered_sinks()
        assert len(sinks) == initial_count + 1
        assert "debug-test" in sinks
        assert sinks["debug-test"] == MockSink

    def test_get_sink_info_registered(self):
        """Test getting info for registered sink."""
        from fapilog.core.registries.sink_registry import SinkRegistry

        SinkRegistry.register("info-test", MockSink)

        info = SinkDebugger.get_sink_info("info-test")

        assert info["registered"] is True
        assert info["class_name"] == "MockSink"
        assert "constructor_signature" in info
        assert "methods" in info

    def test_get_sink_info_not_registered(self):
        """Test getting info for non-registered sink."""

        info = SinkDebugger.get_sink_info("nonexistent-sink")

        assert info["registered"] is False

    def test_validate_sink_class_valid(self):
        """Test validating a valid sink class."""

        issues = SinkDebugger.validate_sink_class(MockSink)
        assert len(issues) == 0

    def test_validate_sink_class_invalid(self):
        """Test validating an invalid sink class."""

        class InvalidSink:
            pass

        issues = SinkDebugger.validate_sink_class(InvalidSink)
        assert len(issues) > 0

    def test_test_sink_instantiation_success(self):
        """Test successful sink instantiation."""

        result = SinkDebugger.test_sink_instantiation(MockSink)

        assert result["success"] is True
        assert result["instance_created"] is True

    def test_test_sink_instantiation_failure(self):
        """Test failed sink instantiation."""

        result = SinkDebugger.test_sink_instantiation(
            FailingConstructorSink, valid_param=False
        )

        assert result["success"] is False
        assert "error" in result

    def test_diagnose_sink_registration_issues_valid(self):
        """Test diagnosing valid sink registration."""

        diagnosis = SinkDebugger.diagnose_sink_registration_issues(
            "test-diag", MockSink
        )

        assert diagnosis["can_register"] is True
        assert len(diagnosis["issues"]) == 0

    def test_diagnose_sink_registration_issues_invalid(self):
        """Test diagnosing invalid sink registration."""

        class InvalidSink:
            pass

        diagnosis = SinkDebugger.diagnose_sink_registration_issues(
            "invalid-name", InvalidSink
        )

        assert diagnosis["can_register"] is False
        assert len(diagnosis["issues"]) > 0


class TestIntegrationTesting:
    """Test integration testing utilities."""

    @pytest.mark.asyncio
    async def test_container_integration(self, integration_tester):
        """Test container integration testing."""
        result = await integration_tester.test_container_integration(
            MockSink, "container_test"
        )

        assert "success" in result
        assert "sink_name" in result
        assert "sink_class" in result

    @pytest.mark.asyncio
    async def test_queue_integration(self, integration_tester):
        """Test queue integration testing."""
        # Use valid URI scheme (hyphen, not underscore)
        result = await integration_tester.test_queue_integration(MockSink, "queue-test")

        assert "success" in result
        assert "messages_sent" in result

    @pytest.mark.asyncio
    async def test_error_handling_integration(self, integration_tester):
        """Test error handling integration."""
        # Use valid URI scheme (hyphen, not underscore)
        result = await integration_tester.test_error_handling(MockSink, "error-test")

        assert "success" in result
        assert "error_occurred" in result

    def test_environment_configuration(self, integration_tester):
        """Test environment configuration testing."""
        env_vars = {"FAPILOG_SINKS": "test://localhost"}

        result = integration_tester.test_environment_configuration(
            MockSink, env_vars, "env_test"
        )

        assert "success" in result
        assert "env_vars_set" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
