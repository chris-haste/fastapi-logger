"""Testing utilities for fapilog custom sinks and processors.

This package provides comprehensive testing tools for both sink and processor developers including:

Sink Testing:
- SinkTestFramework for testing sink implementations
- Mock sinks for testing (RecordingSink, FailingSink, SlowSink)
- SinkPerformanceTester for performance testing
- Integration testing tools
- Debugging utilities
- URI validation for sink names

Processor Testing:
- ProcessorTestFramework for testing processor implementations
- Mock processors for testing (RecordingProcessor, FailingProcessor, SlowProcessor, etc.)
- ProcessorPerformanceTester for performance testing
- Configuration and lifecycle testing
- Error handling validation

Example:
    from fapilog.testing import (
        SinkTestFramework, SinkPerformanceTester,
        ProcessorTestFramework, ProcessorPerformanceTester
    )

    # Test a custom sink
    sink_framework = SinkTestFramework()
    sink_tester = SinkPerformanceTester()
    assert sink_framework.test_sink_registration("my_sink", MySink)
    throughput = await sink_tester.test_throughput(MySink())

    # Test a custom processor
    processor_framework = ProcessorTestFramework()
    processor_tester = ProcessorPerformanceTester()
    assert processor_framework.validate_processor_interface(MyProcessor)
    results = await processor_framework.run_comprehensive_test_suite(MyProcessor)
"""

# Sink testing utilities
from .debug import SinkDebugger
from .integration import SinkIntegrationTester

# Processor testing utilities
from .mock_processors import (
    BatchingProcessor,
    ConditionalFailingProcessor,
    FailingProcessor,
    FilteringProcessor,
    RecordingProcessor,
    SlowProcessor,
    TransformProcessor,
)
from .mock_sinks import (
    BatchingSink,
    ConditionalFailingSink,
    FailingSink,
    RecordingSink,
    SlowSink,
)
from .performance import SinkPerformanceTester
from .processor_performance import run_processor_performance_suite
from .processor_testing import (
    ProcessorTestResult,
    benchmark_processor_performance,
    run_processor_edge_cases,
    run_processor_with_events,
    stress_test_processor,
    validate_processor_behavior,
)
from .sink_testing import SinkTestFramework
from .uri_testing import validate_sink_uri, validate_uri_scheme

__all__ = [
    # Sink testing
    "SinkTestFramework",
    "RecordingSink",
    "FailingSink",
    "SlowSink",
    "BatchingSink",
    "ConditionalFailingSink",
    "SinkPerformanceTester",
    "SinkIntegrationTester",
    "SinkDebugger",
    "validate_uri_scheme",
    "validate_sink_uri",
    # Processor testing
    "ProcessorTestFramework",
    "RecordingProcessor",
    "FailingProcessor",
    "SlowProcessor",
    "TransformProcessor",
    "ConditionalFailingProcessor",
    "BatchingProcessor",
    "FilteringProcessor",
    "run_processor_performance_suite",
    "ProcessorTestResult",
    "run_processor_with_events",
    "validate_processor_behavior",
    "stress_test_processor",
    "run_processor_edge_cases",
    "benchmark_processor_performance",
]
