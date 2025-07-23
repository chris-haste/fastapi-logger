"""Testing utilities for fapilog custom sinks.

This package provides comprehensive testing tools for sink developers including:
- SinkTestFramework for testing sink implementations
- Mock sinks for testing (RecordingSink, FailingSink, SlowSink)
- Performance testing helpers
- Integration testing tools
- Debugging utilities
- URI validation for sink names

Example:
    from fapilog.testing import SinkTestFramework, SinkPerformanceTester

    framework = SinkTestFramework()
    tester = SinkPerformanceTester()

    # Test sink registration and performance
    assert framework.test_sink_registration("my_sink", MySink)
    throughput = await tester.test_throughput(MySink())
"""

from .debug import SinkDebugger
from .mock_sinks import FailingSink, RecordingSink, SlowSink
from .performance import SinkPerformanceTester
from .sink_testing import SinkTestFramework
from .uri_testing import validate_sink_uri, validate_uri_scheme

__all__ = [
    "SinkTestFramework",
    "RecordingSink",
    "FailingSink",
    "SlowSink",
    "SinkPerformanceTester",
    "SinkDebugger",
    "validate_uri_scheme",
    "validate_sink_uri",
]
