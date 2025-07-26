"""Tests for processor testing framework."""

from typing import Any, Dict
from unittest.mock import patch

import pytest

from fapilog._internal.processor import Processor
from fapilog.exceptions import ProcessorExecutionError
from fapilog.testing import (
    BatchingProcessor,
    ConditionalFailingProcessor,
    FailingProcessor,
    FilteringProcessor,
    ProcessorPerformanceTester,
    ProcessorTestFramework,
    RecordingProcessor,
    SlowProcessor,
    TransformProcessor,
)


class SimpleTestProcessor(Processor):
    """Simple processor for testing."""

    def __init__(self, **config: Any) -> None:
        super().__init__(**config)

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        result = event_dict.copy()
        result["processed"] = True
        return result


class FailingInitProcessor(Processor):
    """Processor that fails during initialization."""

    def __init__(self, **config: Any) -> None:
        if config.get("should_fail", False):
            raise ValueError("Initialization failed")
        super().__init__(**config)

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        return event_dict


# Additional processors for testing edge cases
class InvalidProcessor:
    """Not a Processor subclass."""

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        return event_dict


class InvalidSignatureProcessor(Processor):
    """Processor with invalid process signature."""

    def __init__(self, **config: Any) -> None:
        super().__init__(**config)

    def process(self, wrong_params: str) -> Dict[str, Any]:  # type: ignore[override]
        return {}


class NonAsyncMethodsProcessor(Processor):
    """Processor with non-async lifecycle methods."""

    def __init__(self, **config: Any) -> None:
        super().__init__(**config)

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        return event_dict

    def start(self) -> None:  # type: ignore[override]  # Should be async
        pass

    def stop(self) -> None:  # type: ignore[override]  # Should be async
        pass


class NoInitProcessor(Processor):
    """Processor without __init__ method for testing."""

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        return event_dict


class BrokenInspectionProcessor(Processor):
    """Processor that breaks inspect.signature."""

    def __init__(self, **config: Any) -> None:
        super().__init__(**config)

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        return event_dict


class LifecycleFailingProcessor(Processor):
    """Processor that fails during lifecycle operations."""

    def __init__(
        self,
        fail_start: bool = False,
        fail_stop: bool = False,
        start_not_started: bool = False,
        **config: Any,
    ) -> None:
        super().__init__(**config)
        self.fail_start = fail_start
        self.fail_stop = fail_stop
        self.start_not_started = start_not_started
        self._started = False

    @property
    def is_started(self) -> bool:
        if self.start_not_started and hasattr(self, "_start_called"):
            return False  # Simulate not starting properly
        return self._started

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        return event_dict

    async def start(self) -> None:
        self._start_called = True
        if self.fail_start:
            raise RuntimeError("Start failed")
        if not self.start_not_started:
            self._started = True

    async def stop(self) -> None:
        if self.fail_stop:
            raise RuntimeError("Stop failed")
        self._started = False


class AlreadyStartedProcessor(Processor):
    """Processor that claims to be already started."""

    def __init__(self, **config: Any) -> None:
        super().__init__(**config)
        self._started = True  # Start as already started

    @property
    def is_started(self) -> bool:
        return self._started

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        return event_dict

    async def start(self) -> None:
        self._started = True

    async def stop(self) -> None:
        self._started = False


class ExecutionFailingProcessor(Processor):
    """Processor that fails during execution."""

    def __init__(self, **config: Any) -> None:
        super().__init__(**config)

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        raise RuntimeError("Execution failed")


class ConfigValidationFailingProcessor(Processor):
    """Processor that fails config validation."""

    def __init__(self, should_fail_validation: bool = False, **config: Any) -> None:
        super().__init__(**config)
        self.should_fail_validation = should_fail_validation

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        return event_dict

    def validate_config(self) -> None:
        if self.should_fail_validation:
            raise ValueError("Config validation failed")


class PerformanceFailingProcessor(Processor):
    """Processor that starts but fails during performance testing."""

    def __init__(self, **config: Any) -> None:
        super().__init__(**config)

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        raise RuntimeError("Performance test execution failed")


class TestProcessorTestFramework:
    """Test the ProcessorTestFramework class."""

    def test_init(self):
        """Test framework initialization."""
        framework = ProcessorTestFramework()
        assert framework.recorded_events == []
        assert framework.errors == []
        assert framework.test_results == []

    def test_create_test_processor_success(self):
        """Test successful processor creation."""
        framework = ProcessorTestFramework()
        processor = framework.create_test_processor(SimpleTestProcessor)
        assert isinstance(processor, SimpleTestProcessor)

    def test_create_test_processor_invalid_class(self):
        """Test processor creation with invalid class."""
        framework = ProcessorTestFramework()
        with pytest.raises(ValueError, match="must inherit from Processor"):
            framework.create_test_processor(InvalidProcessor)

    def test_create_test_processor_init_failure(self):
        """Test processor creation when initialization fails."""
        framework = ProcessorTestFramework()
        with pytest.raises(ValueError):
            framework.create_test_processor(FailingInitProcessor, should_fail=True)

        # Check that error was recorded
        assert len(framework.errors) == 1
        assert isinstance(framework.errors[0], ValueError)

    def test_validate_processor_interface_valid(self):
        """Test interface validation for valid processor."""
        framework = ProcessorTestFramework()
        result = framework.validate_processor_interface(SimpleTestProcessor)
        assert result is True
        assert len(framework.errors) == 0

    def test_validate_processor_interface_invalid_class(self):
        """Test interface validation for invalid class."""
        framework = ProcessorTestFramework()
        result = framework.validate_processor_interface(InvalidProcessor)
        assert result is False
        assert len(framework.errors) > 0

    def test_validate_processor_interface_invalid_signature(self):
        """Test interface validation for processor with invalid signature."""
        framework = ProcessorTestFramework()
        result = framework.validate_processor_interface(InvalidSignatureProcessor)
        assert result is False
        # Should have error about process method signature
        error_messages = [str(e) for e in framework.errors]
        assert any("process method signature" in msg for msg in error_messages)

    def test_validate_processor_interface_non_async_methods(self):
        """Test interface validation for processor with non-async lifecycle methods."""
        framework = ProcessorTestFramework()
        result = framework.validate_processor_interface(NonAsyncMethodsProcessor)
        assert result is False
        # Should have errors about async methods
        error_messages = [str(e) for e in framework.errors]
        assert any("method must be async" in msg for msg in error_messages)

    def test_validate_processor_interface_broken_inspection(self):
        """Test interface validation when inspect.signature fails."""
        framework = ProcessorTestFramework()

        # Mock inspect.signature to raise an exception for the process method
        with patch("inspect.signature") as mock_signature:

            def side_effect(method):
                if hasattr(method, "__name__") and method.__name__ == "process":
                    raise TypeError("Cannot inspect signature")
                # For other methods, call the real inspect.signature
                import inspect

                return inspect.signature(method)

            mock_signature.side_effect = side_effect

            result = framework.validate_processor_interface(BrokenInspectionProcessor)
            assert result is False
            # Should have error about signature inspection
            error_messages = [str(e) for e in framework.errors]
            assert any("signature cannot be inspected" in msg for msg in error_messages)

    def test_validate_processor_interface_broken_init_inspection(self):
        """Test interface validation when inspect.signature fails for __init__."""
        framework = ProcessorTestFramework()

        # Mock inspect.signature to raise an exception for the __init__ method
        with patch("inspect.signature") as mock_signature:

            def side_effect(method):
                if hasattr(method, "__name__") and method.__name__ == "__init__":
                    raise TypeError("Cannot inspect __init__ signature")
                # For other methods, call the real inspect.signature
                import inspect

                return inspect.signature(method)

            mock_signature.side_effect = side_effect

            result = framework.validate_processor_interface(BrokenInspectionProcessor)
            assert result is False
            # Should have error about __init__ signature inspection
            error_messages = [str(e) for e in framework.errors]
            assert any(
                "__init__ method signature cannot be inspected" in msg
                for msg in error_messages
            )

    def test_test_processor_registration_with_registry(self):
        """Test processor registration with the processor registry."""
        framework = ProcessorTestFramework()

        # Now that the registry exists, this should work properly
        result = framework.test_processor_registration("test", SimpleTestProcessor)
        assert result is True  # Should return True when registration succeeds

    @pytest.mark.asyncio
    async def test_test_processor_lifecycle_success(self):
        """Test successful processor lifecycle."""
        framework = ProcessorTestFramework()
        processor = SimpleTestProcessor()

        result = await framework.test_processor_lifecycle(processor)
        assert result is True
        assert len(framework.errors) == 0

    @pytest.mark.asyncio
    async def test_test_processor_lifecycle_initial_started_error(self):
        """Test lifecycle when processor is already started initially."""
        framework = ProcessorTestFramework()
        processor = AlreadyStartedProcessor()

        result = await framework.test_processor_lifecycle(processor)
        assert result is False

        # Should have error about initial state
        error_messages = [str(e) for e in framework.errors]
        assert any("should not be started initially" in msg for msg in error_messages)

    @pytest.mark.asyncio
    async def test_test_processor_lifecycle_start_failure(self):
        """Test lifecycle when start operation fails."""
        framework = ProcessorTestFramework()
        processor = LifecycleFailingProcessor(fail_start=True)

        result = await framework.test_processor_lifecycle(processor)
        assert result is False

        # Should have error about start operation
        error_messages = [str(e) for e in framework.errors]
        assert any("start operation failed" in msg for msg in error_messages)

    @pytest.mark.asyncio
    async def test_test_processor_lifecycle_not_started_after_start(self):
        """Test lifecycle when processor is not started after start()."""
        framework = ProcessorTestFramework()
        processor = LifecycleFailingProcessor(start_not_started=True)

        result = await framework.test_processor_lifecycle(processor)
        assert result is False

        # Should have error about started state
        error_messages = [str(e) for e in framework.errors]
        assert any("should be started after start()" in msg for msg in error_messages)

    @pytest.mark.asyncio
    async def test_test_processor_lifecycle_still_started_after_stop(self):
        """Test lifecycle when processor is still started after stop()."""
        framework = ProcessorTestFramework()

        class StubbyStoppedProcessor(Processor):
            def __init__(self, **config: Any) -> None:
                super().__init__(**config)
                self._started = False
                self._stop_called = False

            @property
            def is_started(self) -> bool:
                # Return True even after stop() is called to trigger the error
                if self._stop_called:
                    return True  # Simulate processor not actually stopping
                return self._started

            def process(
                self, logger: Any, method_name: str, event_dict: Dict[str, Any]
            ) -> Dict[str, Any]:
                return event_dict

            async def start(self) -> None:
                self._started = True

            async def stop(self) -> None:
                self._stop_called = True
                # Don't actually stop (keep is_started returning True)

        processor = StubbyStoppedProcessor()

        result = await framework.test_processor_lifecycle(processor)
        assert result is False

        # Should have error about stopped state
        error_messages = [str(e) for e in framework.errors]
        assert any("should be stopped after stop()" in msg for msg in error_messages)

    @pytest.mark.asyncio
    async def test_test_processor_lifecycle_general_exception(self):
        """Test lifecycle when general exception occurs."""
        framework = ProcessorTestFramework()

        # Create a processor that raises an exception during lifecycle test
        class ExceptionProcessor(Processor):
            def __init__(self, **config: Any) -> None:
                super().__init__(**config)

            @property
            def is_started(self) -> bool:
                raise RuntimeError("Property access failed")

            def process(
                self, logger: Any, method_name: str, event_dict: Dict[str, Any]
            ) -> Dict[str, Any]:
                return event_dict

            async def start(self) -> None:
                pass

            async def stop(self) -> None:
                pass

        processor = ExceptionProcessor()

        result = await framework.test_processor_lifecycle(processor)
        assert result is False

        # Should have recorded the exception
        assert len(framework.errors) == 1
        assert isinstance(framework.errors[0], RuntimeError)

    def test_test_processor_execution_success(self):
        """Test successful processor execution."""
        framework = ProcessorTestFramework()
        processor = SimpleTestProcessor()

        result = framework.test_processor_execution(processor)
        assert result is True
        assert len(framework.recorded_events) > 0

    def test_test_processor_execution_with_custom_events(self):
        """Test processor execution with custom events."""
        framework = ProcessorTestFramework()
        processor = SimpleTestProcessor()

        custom_events = [
            {"level": "info", "message": "Custom test 1"},
            {"level": "error", "message": "Custom test 2"},
        ]

        result = framework.test_processor_execution(processor, custom_events)
        assert result is True
        assert len(framework.recorded_events) == 2

    def test_test_processor_execution_exception(self):
        """Test processor execution when exception occurs."""
        framework = ProcessorTestFramework()

        # Mock safe_processor_execution to raise an exception
        with patch(
            "fapilog.testing.processor_testing.safe_processor_execution",
            side_effect=RuntimeError("Execution error"),
        ):
            processor = SimpleTestProcessor()
            result = framework.test_processor_execution(processor)
            assert result is False

            # Should have recorded the exception
            assert len(framework.errors) == 1
            assert isinstance(framework.errors[0], RuntimeError)

    def test_test_processor_error_handling_success(self):
        """Test successful processor error handling."""
        framework = ProcessorTestFramework()
        processor = SimpleTestProcessor()

        result = framework.test_processor_error_handling(processor)
        assert result is True

    def test_test_processor_error_handling_valid_event_returns_none(self):
        """Test error handling when valid event processing returns None."""
        framework = ProcessorTestFramework()
        processor = SimpleTestProcessor()

        # Mock safe_processor_execution to return None for valid event
        with patch(
            "fapilog.testing.processor_testing.safe_processor_execution",
            return_value=None,
        ):
            result = framework.test_processor_error_handling(processor)
            assert result is False

            # Should have error about None result
            error_messages = [str(e) for e in framework.errors]
            assert any(
                "Valid event should not be None" in msg for msg in error_messages
            )

    def test_test_processor_error_handling_invalid_event_returns_none(self):
        """Test error handling when invalid event processing returns None."""
        framework = ProcessorTestFramework()
        processor = SimpleTestProcessor()

        # Mock safe_processor_execution to return good result for valid event, None for invalid
        def mock_execution(proc, logger, method, event, strategy=None):
            if event == {}:  # Invalid event
                return None
            return event  # Valid event

        with patch(
            "fapilog.testing.processor_testing.safe_processor_execution",
            side_effect=mock_execution,
        ):
            result = framework.test_processor_error_handling(processor)
            assert result is False

            # Should have error about pass_through strategy
            error_messages = [str(e) for e in framework.errors]
            assert any(
                "Error handling should use pass_through strategy" in msg
                for msg in error_messages
            )

    def test_test_processor_error_handling_exception(self):
        """Test error handling when exception occurs."""
        framework = ProcessorTestFramework()
        processor = SimpleTestProcessor()

        # Mock safe_processor_execution to raise an exception
        with patch(
            "fapilog.testing.processor_testing.safe_processor_execution",
            side_effect=RuntimeError("Error handling test failed"),
        ):
            result = framework.test_processor_error_handling(processor)
            assert result is False

            # Should have recorded the exception
            assert len(framework.errors) == 1
            assert isinstance(framework.errors[0], RuntimeError)

    def test_test_processor_configuration_success(self):
        """Test successful processor configuration."""
        framework = ProcessorTestFramework()

        configs = [{}, {"param1": "value1"}, {"param2": 42}]

        result = framework.test_processor_configuration(SimpleTestProcessor, configs)
        assert result is True
        assert len(framework.test_results) == 3

    def test_test_processor_configuration_exception(self):
        """Test processor configuration when exception occurs."""
        framework = ProcessorTestFramework()

        # Mock the processor class to raise an exception during instantiation
        with patch.object(
            SimpleTestProcessor,
            "__init__",
            side_effect=RuntimeError("Config test failed"),
        ):
            result = framework.test_processor_configuration(SimpleTestProcessor, [{}])
            assert result is True  # Method completes but records the failure

            # Should have recorded the failed result
            assert len(framework.test_results) == 1
            assert framework.test_results[0]["success"] is False

    @pytest.mark.asyncio
    async def test_test_processor_performance_basic_success(self):
        """Test successful processor performance testing."""
        framework = ProcessorTestFramework()
        processor = SimpleTestProcessor()
        await processor.start()

        metrics = await framework.test_processor_performance_basic(processor, 10)
        assert "throughput_eps" in metrics
        assert "avg_latency_ms" in metrics
        assert metrics["event_count"] == 10

    @pytest.mark.asyncio
    async def test_test_processor_performance_basic_not_started(self):
        """Test performance testing when processor is not started."""
        framework = ProcessorTestFramework()
        processor = SimpleTestProcessor()
        # Don't start the processor

        metrics = await framework.test_processor_performance_basic(processor, 10)
        assert "throughput_eps" in metrics
        assert metrics["event_count"] == 10

    @pytest.mark.asyncio
    async def test_test_processor_performance_basic_exception(self):
        """Test performance testing when exception occurs."""
        framework = ProcessorTestFramework()
        processor = SimpleTestProcessor()
        await processor.start()

        # Mock safe_processor_execution to raise an exception
        with patch(
            "fapilog.testing.processor_testing.safe_processor_execution",
            side_effect=RuntimeError("Performance test execution failed"),
        ):
            metrics = await framework.test_processor_performance_basic(processor, 5)
            assert "error" in metrics
            assert metrics["throughput_eps"] == 0
            assert metrics["event_count"] == 0

            # Should have recorded the exception
            assert len(framework.errors) == 1

    def test_clear_state(self):
        """Test clearing framework state."""
        framework = ProcessorTestFramework()

        # Add some data
        framework.recorded_events.append({"test": "data"})
        framework.errors.append(ValueError("test error"))
        framework.test_results.append({"test": "result"})

        framework.clear_state()

        assert len(framework.recorded_events) == 0
        assert len(framework.errors) == 0
        assert len(framework.test_results) == 0

    def test_get_test_summary_with_data(self):
        """Test getting test summary with data."""
        framework = ProcessorTestFramework()

        # Add some data
        framework.recorded_events = [{"event": f"test_{i}"} for i in range(10)]
        framework.errors = [ValueError("error1"), RuntimeError("error2")]
        framework.test_results = [
            {"success": True, "config": {}},
            {"success": False, "config": {"param": "value"}},
        ]

        summary = framework.get_test_summary()

        assert summary["total_events"] == 10
        assert summary["total_errors"] == 2
        assert summary["total_config_tests"] == 2
        assert summary["successful_config_tests"] == 1
        assert len(summary["last_events"]) == 5  # Last 5 events
        assert len(summary["errors"]) == 2

    def test_get_test_summary_empty_state(self):
        """Test getting test summary with empty state."""
        framework = ProcessorTestFramework()

        summary = framework.get_test_summary()

        assert summary["total_events"] == 0
        assert summary["total_errors"] == 0
        assert summary["total_config_tests"] == 0
        assert summary["successful_config_tests"] == 0
        assert summary["last_events"] == []
        assert summary["errors"] == []

    @pytest.mark.asyncio
    async def test_run_comprehensive_test_suite_success(self):
        """Test successful comprehensive test suite."""
        framework = ProcessorTestFramework()

        results = await framework.run_comprehensive_test_suite(SimpleTestProcessor)

        assert results["overall_success"] is True
        assert results["interface_validation"] is True
        assert results["lifecycle_test"] is True
        assert results["execution_test"] is True
        assert results["error_handling_test"] is True
        assert results["configuration_test"] is True
        assert "performance_metrics" in results

    @pytest.mark.asyncio
    async def test_run_comprehensive_test_suite_interface_failure(self):
        """Test comprehensive test suite when interface validation fails."""
        framework = ProcessorTestFramework()

        results = await framework.run_comprehensive_test_suite(InvalidProcessor)

        assert "interface_validation" in results
        assert results["interface_validation"] is False
        assert "error" in results
        assert results["error"] == "Interface validation failed"

    @pytest.mark.asyncio
    async def test_run_comprehensive_test_suite_exception(self):
        """Test comprehensive test suite when exception occurs."""
        framework = ProcessorTestFramework()

        # Mock create_test_processor to raise an exception
        with patch.object(
            framework,
            "create_test_processor",
            side_effect=RuntimeError("Test suite failed"),
        ):
            results = await framework.run_comprehensive_test_suite(SimpleTestProcessor)

            assert results["overall_success"] is False
            assert "error" in results
            assert results["error"] == "Test suite failed"

            # Should have recorded the exception
            assert len(framework.errors) == 1

    def test_export_results(self):
        """Test exporting results to JSON."""
        tester = ProcessorPerformanceTester()
        tester.metrics["test"] = {"value": 123}

        json_str = tester.export_results()

        import json

        parsed = json.loads(json_str)
        assert parsed["test"]["value"] == 123

    def test_compare_processors(self):
        """Test comparing processor performance."""
        tester = ProcessorPerformanceTester()

        # Mock results for comparison
        results = [
            {
                "processor_class": "ProcessorA",
                "throughput": {"sequential_eps": 100},
                "latency": {"avg_latency_ms": 10},
            },
            {
                "processor_class": "ProcessorB",
                "throughput": {"sequential_eps": 200},
                "latency": {"avg_latency_ms": 5},
            },
        ]

        # Compare throughput (higher is better)
        comparison = tester.compare_processors(results, "throughput")
        assert comparison["best_performer"]["processor"] == "ProcessorB"
        assert comparison["worst_performer"]["processor"] == "ProcessorA"

        # Compare latency (lower is better)
        comparison = tester.compare_processors(results, "latency")
        assert comparison["best_performer"]["processor"] == "ProcessorB"
        assert comparison["worst_performer"]["processor"] == "ProcessorA"

    def test_compare_processors_empty(self):
        """Test comparing with empty results."""
        tester = ProcessorPerformanceTester()

        comparison = tester.compare_processors([], "throughput")
        assert "error" in comparison


class TestMockProcessors:
    """Test mock processor implementations."""

    def test_recording_processor(self):
        """Test RecordingProcessor functionality."""
        processor = RecordingProcessor()
        event = {"level": "info", "message": "test"}

        result = processor.process(None, "info", event)

        assert result == event  # Should pass through unchanged
        assert len(processor.recorded_events) == 1

        recorded = processor.recorded_events[0]
        assert recorded["level"] == "info"
        assert recorded["message"] == "test"
        assert "_recorded_at" in recorded
        assert "_process_count" in recorded
        assert "_method_name" in recorded

        # Test statistics
        stats = processor.get_stats()
        assert stats["total_events"] == 1
        assert stats["process_count"] == 1

        # Test clearing
        processor.clear()
        assert len(processor.recorded_events) == 0

    def test_failing_processor(self):
        """Test FailingProcessor functionality."""
        # 100% failure rate
        processor = FailingProcessor(failure_rate=1.0)
        event = {"level": "info", "message": "test"}

        with pytest.raises(ProcessorExecutionError):
            processor.process(None, "info", event)

        # 0% failure rate - use same processor to test statistics
        processor.failure_rate = (
            0.0  # Change failure rate instead of creating new processor
        )
        result = processor.process(None, "info", event)
        assert result == event

        # Test statistics
        stats = processor.get_stats()
        assert stats["attempts"] == 2
        assert stats["failures"] == 1
        assert stats["successes"] == 1

    @pytest.mark.asyncio
    async def test_failing_processor_lifecycle(self):
        """Test FailingProcessor lifecycle failures."""
        # Test start failure
        processor = FailingProcessor(fail_on_start=True)
        with pytest.raises(ProcessorExecutionError):
            await processor.start()

        # Test stop failure
        processor = FailingProcessor(fail_on_stop=True)
        await processor.start()  # Should succeed
        with pytest.raises(ProcessorExecutionError):
            await processor.stop()

    def test_slow_processor(self):
        """Test SlowProcessor functionality."""
        processor = SlowProcessor(delay_ms=10)  # Small delay for testing
        event = {"level": "info", "message": "test"}

        import time

        start_time = time.time()
        result = processor.process(None, "info", event)
        end_time = time.time()

        duration = (end_time - start_time) * 1000  # Convert to ms
        assert duration >= 8  # Should take at least close to 10ms

        assert result["_processing_delay_ms"] == 10
        assert result["_call_count"] == 1

        # Test timing stats
        stats = processor.get_timing_stats()
        assert stats["call_count"] == 1
        assert stats["configured_delay_ms"] == 10

    def test_transform_processor(self):
        """Test TransformProcessor functionality."""
        # Test with identity transform
        processor = TransformProcessor()
        event = {"level": "info", "message": "test"}

        result = processor.process(None, "info", event)
        assert result == event

        # Test with custom transform
        def uppercase_transform(event_dict):
            result = event_dict.copy()
            result["message"] = result["message"].upper()
            return result

        processor = TransformProcessor(transform_func=uppercase_transform)
        result = processor.process(None, "info", event)

        assert result["message"] == "TEST"
        assert processor.get_transformation_count() == 1

    def test_transform_processor_invalid_return(self):
        """Test TransformProcessor with invalid return type."""

        def invalid_transform(event_dict):
            return "not a dict"

        processor = TransformProcessor(transform_func=invalid_transform)
        event = {"level": "info", "message": "test"}

        with pytest.raises(ProcessorExecutionError, match="must return dict"):
            processor.process(None, "info", event)

    def test_conditional_failing_processor(self):
        """Test ConditionalFailingProcessor functionality."""
        # Test level-based failure
        processor = ConditionalFailingProcessor(fail_on_level="error")

        # Should pass with info level
        info_event = {"level": "info", "message": "test"}
        result = processor.process(None, "info", info_event)
        assert result == info_event

        # Should fail with error level
        error_event = {"level": "error", "message": "test"}
        with pytest.raises(ProcessorExecutionError, match="level=error"):
            processor.process(None, "error", error_event)

        assert processor.get_failure_count() == 1

    def test_batching_processor(self):
        """Test BatchingProcessor functionality."""
        processor = BatchingProcessor(batch_size=3, auto_process=True)

        events = [{"level": "info", "message": f"test {i}"} for i in range(5)]

        results = []
        for event in events:
            result = processor.process(None, "info", event)
            results.append(result)

        # Check batch metadata - remember that batch gets flushed after 3 items
        # So positions are: 0, 1, 2 (flush), 0, 1
        assert results[0]["_batch_position"] == 0
        assert results[1]["_batch_position"] == 1
        assert results[2]["_batch_position"] == 2
        assert results[3]["_batch_position"] == 0  # New batch starts
        assert results[4]["_batch_position"] == 1

        # Should have processed one complete batch
        batches = processor.get_batches()
        assert len(batches) >= 1

        stats = processor.get_stats()
        assert stats["total_events"] == 5
        assert stats["configured_batch_size"] == 3

    def test_filtering_processor(self):
        """Test FilteringProcessor functionality."""
        # Test level filtering
        processor = FilteringProcessor(filter_level="info")

        info_event = {"level": "info", "message": "test"}
        debug_event = {"level": "debug", "message": "test"}

        info_result = processor.process(None, "info", info_event)
        debug_result = processor.process(None, "debug", debug_event)

        assert info_result == info_event  # Should pass
        assert debug_result is None  # Should be filtered

        stats = processor.get_filter_stats()
        assert stats["passed"] == 1
        assert stats["filtered"] == 1


class TestProcessorPerformanceTester:
    """Test ProcessorPerformanceTester functionality."""

    @pytest.mark.asyncio
    async def test_throughput_testing(self):
        """Test throughput measurement."""
        tester = ProcessorPerformanceTester()
        processor = SimpleTestProcessor()

        throughput = await tester.test_throughput(processor, 50)

        assert throughput > 0
        assert "throughput" in tester.metrics

        metrics = tester.metrics["throughput"]
        assert metrics["total_events"] == 50
        assert metrics["test_type"] == "sequential"

    @pytest.mark.asyncio
    async def test_concurrent_throughput_testing(self):
        """Test concurrent throughput measurement."""
        tester = ProcessorPerformanceTester()
        processor = SimpleTestProcessor()

        throughput = await tester.test_concurrent_throughput(processor, 100, 5)

        assert throughput > 0
        assert "concurrent_throughput" in tester.metrics

        metrics = tester.metrics["concurrent_throughput"]
        assert metrics["num_workers"] == 5
        assert metrics["test_type"] == "concurrent"

    @pytest.mark.asyncio
    async def test_latency_testing(self):
        """Test latency measurement."""
        tester = ProcessorPerformanceTester()
        processor = SimpleTestProcessor()

        latency_stats = await tester.test_latency(processor, 20)

        assert "avg_latency_ms" in latency_stats
        assert "median_latency_ms" in latency_stats
        assert "p95_latency_ms" in latency_stats
        assert "p99_latency_ms" in latency_stats
        assert latency_stats["num_samples"] == 20

    @pytest.mark.asyncio
    async def test_memory_testing(self):
        """Test memory usage measurement."""
        tester = ProcessorPerformanceTester()
        processor = SimpleTestProcessor()

        memory_stats = await tester.test_memory_usage(processor, 100)

        # Should have memory stats (or error if psutil not available)
        assert "memory_growth_mb" in memory_stats or "error" in memory_stats

    @pytest.mark.asyncio
    async def test_cpu_testing(self):
        """Test CPU usage measurement."""
        tester = ProcessorPerformanceTester()
        processor = SimpleTestProcessor()

        cpu_stats = await tester.test_cpu_usage(processor, 2)  # Short duration

        # Should have CPU stats (or error if psutil not available)
        assert "avg_cpu_percent" in cpu_stats or "error" in cpu_stats

    @pytest.mark.asyncio
    async def test_batch_performance_testing(self):
        """Test batch performance measurement."""
        tester = ProcessorPerformanceTester()
        processor = SimpleTestProcessor()

        batch_results = await tester.test_batch_performance(processor, [1, 5, 10], 10)

        assert len(batch_results) == 3
        for _batch_size, metrics in batch_results.items():
            assert "throughput_eps" in metrics
            assert metrics["num_batches"] == 10

    @pytest.mark.asyncio
    async def test_comprehensive_performance_test(self):
        """Test comprehensive performance testing."""
        tester = ProcessorPerformanceTester()
        processor = SimpleTestProcessor()

        # Use smaller test configuration for speed
        test_config = {
            "throughput_events": 50,
            "concurrent_events": 50,
            "concurrent_workers": 3,
            "latency_samples": 10,
            "memory_events": 50,
            "cpu_duration": 2,
            "batch_sizes": [1, 5],
            "batch_events_per_size": 5,
        }

        results = await tester.run_comprehensive_test(processor, test_config)

        assert results["processor_class"] == "SimpleTestProcessor"
        assert "throughput" in results
        assert "latency" in results
        assert "memory" in results
        assert "cpu" in results
        assert "batch_performance" in results

    def test_metrics_management(self):
        """Test metrics storage and clearing."""
        tester = ProcessorPerformanceTester()

        # Add some metrics
        tester.metrics["test"] = {"value": 123}

        metrics = tester.get_metrics()
        assert metrics["test"]["value"] == 123

        tester.clear_metrics()
        assert len(tester.metrics) == 0

    def test_export_results(self):
        """Test exporting results to JSON."""
        tester = ProcessorPerformanceTester()
        tester.metrics["test"] = {"value": 123}

        json_str = tester.export_results()

        import json

        parsed = json.loads(json_str)
        assert parsed["test"]["value"] == 123

    def test_compare_processors(self):
        """Test comparing processor performance."""
        tester = ProcessorPerformanceTester()

        # Mock results for comparison
        results = [
            {
                "processor_class": "ProcessorA",
                "throughput": {"sequential_eps": 100},
                "latency": {"avg_latency_ms": 10},
            },
            {
                "processor_class": "ProcessorB",
                "throughput": {"sequential_eps": 200},
                "latency": {"avg_latency_ms": 5},
            },
        ]

        # Compare throughput (higher is better)
        comparison = tester.compare_processors(results, "throughput")
        assert comparison["best_performer"]["processor"] == "ProcessorB"
        assert comparison["worst_performer"]["processor"] == "ProcessorA"

        # Compare latency (lower is better)
        comparison = tester.compare_processors(results, "latency")
        assert comparison["best_performer"]["processor"] == "ProcessorB"
        assert comparison["worst_performer"]["processor"] == "ProcessorA"

    def test_compare_processors_empty(self):
        """Test comparing with empty results."""
        tester = ProcessorPerformanceTester()

        comparison = tester.compare_processors([], "throughput")
        assert "error" in comparison


class TestIntegration:
    """Test integration scenarios."""

    @pytest.mark.asyncio
    async def test_end_to_end_testing(self):
        """Test complete end-to-end processor testing."""
        # Create framework and performance tester
        framework = ProcessorTestFramework()
        performance_tester = ProcessorPerformanceTester()

        # Test interface validation
        assert framework.validate_processor_interface(SimpleTestProcessor) is True

        # Test processor creation
        processor = framework.create_test_processor(SimpleTestProcessor)

        # Test lifecycle
        lifecycle_result = await framework.test_processor_lifecycle(processor)
        assert lifecycle_result is True

        # Test execution
        execution_result = framework.test_processor_execution(processor)
        assert execution_result is True

        # Test performance
        throughput = await performance_tester.test_throughput(processor, 25)
        assert throughput > 0

        # Test comprehensive suite
        results = await framework.run_comprehensive_test_suite(SimpleTestProcessor)
        assert results["overall_success"] is True

    def test_mock_processor_interactions(self):
        """Test interactions between different mock processors."""
        # Create a chain of processors
        recording = RecordingProcessor()
        transform = TransformProcessor(lambda x: {**x, "transformed": True})

        event = {"level": "info", "message": "test"}

        # Process through recording first
        result1 = recording.process(None, "info", event)

        # Then through transform
        result2 = transform.process(None, "info", result1)

        # Check recording processor captured the event
        assert len(recording.recorded_events) == 1

        # Check transform processor added the field
        assert result2["transformed"] is True
        assert transform.get_transformation_count() == 1
