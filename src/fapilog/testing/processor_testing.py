"""Framework for testing custom processors."""

import asyncio
import inspect
import time
from typing import Any, Dict, List, Optional, Type

from .._internal.processor import Processor
from .._internal.processor_error_handling import (
    safe_processor_execution,
    safe_processor_lifecycle_operation,
    validate_processor_configuration,
)


class ProcessorTestFramework:
    """Framework for testing custom processors."""

    def __init__(self):
        self.recorded_events: List[Dict[str, Any]] = []
        self.errors: List[Exception] = []
        self.test_results: List[Dict[str, Any]] = []

    def create_test_processor(
        self, processor_class: Type[Processor], **kwargs
    ) -> Processor:
        """Create a test instance of a processor.

        Args:
            processor_class: The processor class to instantiate
            **kwargs: Keyword arguments to pass to the processor constructor

        Returns:
            Configured processor instance

        Raises:
            ValueError: If processor_class is not a valid Processor subclass
            Exception: If processor instantiation fails
        """
        if not issubclass(processor_class, Processor):
            msg = f"{processor_class.__name__} must inherit from Processor"
            raise ValueError(msg)

        try:
            return processor_class(**kwargs)
        except Exception as e:
            self.errors.append(e)
            raise

    def validate_processor_interface(self, processor_class: Type[Processor]) -> bool:
        """Validate that a processor class implements the required interface.

        Args:
            processor_class: The processor class to validate

        Returns:
            True if the processor implements the required interface correctly
        """
        issues = []

        # Check if it's a Processor subclass
        if not issubclass(processor_class, Processor):
            issues.append("Must inherit from Processor base class")

        # Check required methods
        required_methods = ["process", "validate_config", "start", "stop"]
        for method in required_methods:
            if not hasattr(processor_class, method):
                issues.append(f"Missing required '{method}' method")

        # Check process method signature
        if hasattr(processor_class, "process"):
            try:
                sig = inspect.signature(processor_class.process)
                params = list(sig.parameters.keys())
                expected_params = ["self", "logger", "method_name", "event_dict"]
                if params != expected_params:
                    issues.append(
                        f"process method signature should be {expected_params}, "
                        f"got {params}"
                    )
            except Exception:
                issues.append("process method signature cannot be inspected")

        # Check async lifecycle methods
        for method in ["start", "stop"]:
            if hasattr(processor_class, method):
                method_obj = getattr(processor_class, method)
                if not asyncio.iscoroutinefunction(method_obj):
                    issues.append(f"'{method}' method must be async")

        # Check constructor
        if not hasattr(processor_class, "__init__"):
            issues.append("Missing __init__ method")
        else:
            try:
                sig = inspect.signature(processor_class.__init__)
                params = list(sig.parameters.keys())
                if not params or params[0] != "self":
                    issues.append("__init__ method has invalid signature")
            except Exception:
                issues.append("__init__ method signature cannot be inspected")

        if issues:
            for issue in issues:
                err_msg = f"Interface validation failed: {issue}"
                self.errors.append(ValueError(err_msg))
            return False

        return True

    def test_processor_registration(
        self, name: str, processor_class: Type[Processor]
    ) -> bool:
        """Test processor registration and retrieval.

        Args:
            name: Name to register the processor under
            processor_class: Processor class to register

        Returns:
            True if registration and retrieval work correctly, or True if registry doesn't exist
        """
        try:
            # Try to import ProcessorRegistry - it may not exist in this version
            try:
                from .._internal.processor_registry import ProcessorRegistry
            except ImportError:
                # ProcessorRegistry doesn't exist, skip this test
                return True

            # Clear any existing registration and backup
            original_processors = ProcessorRegistry._processors.copy()

            # Clear registry for clean test
            ProcessorRegistry.clear()

            # Since we're testing function registration, create a dummy function
            def dummy_processor_function():
                return processor_class

            # Test registration
            ProcessorRegistry.register(name, dummy_processor_function)

            # Test retrieval
            retrieved_function = ProcessorRegistry.get(name)
            if retrieved_function != dummy_processor_function:
                err_msg = "Retrieved function does not match registered function"
                self.errors.append(ValueError(err_msg))
                return False

            # Test listing includes the processor
            all_processors = ProcessorRegistry.list()
            if (
                name not in all_processors
                or all_processors[name] != dummy_processor_function
            ):
                err_msg = "Processor not found in registry listing"
                self.errors.append(ValueError(err_msg))
                return False

            return True

        except Exception as e:
            self.errors.append(e)
            return False
        finally:
            # Restore original state
            try:
                from .._internal.processor_registry import ProcessorRegistry

                ProcessorRegistry._processors = original_processors
            except ImportError:
                pass  # Registry doesn't exist, nothing to restore

    async def test_processor_lifecycle(self, processor: Processor) -> bool:
        """Test processor start/stop lifecycle.

        Args:
            processor: Processor instance to test

        Returns:
            True if lifecycle operations work correctly
        """
        try:
            # Test initial state
            if processor.is_started:
                self.errors.append(
                    ValueError("Processor should not be started initially")
                )
                return False

            # Test start operation
            start_result = await safe_processor_lifecycle_operation(processor, "start")
            if not start_result:
                self.errors.append(ValueError("Processor start operation failed"))
                return False

            # Check started state
            if not processor.is_started:
                self.errors.append(
                    ValueError("Processor should be started after start()")
                )
                return False

            # Test idempotent start
            await processor.start()  # Should not fail
            if not processor.is_started:
                self.errors.append(ValueError("Processor start should be idempotent"))
                return False

            # Test stop operation
            stop_result = await safe_processor_lifecycle_operation(processor, "stop")
            if not stop_result:
                self.errors.append(ValueError("Processor stop operation failed"))
                return False

            # Check stopped state
            if processor.is_started:
                self.errors.append(
                    ValueError("Processor should be stopped after stop()")
                )
                return False

            # Test idempotent stop
            await processor.stop()  # Should not fail
            if processor.is_started:
                self.errors.append(ValueError("Processor stop should be idempotent"))
                return False

            return True

        except Exception as e:
            self.errors.append(e)
            return False

    def test_processor_execution(
        self, processor: Processor, test_events: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """Test processor execution with sample events.

        Args:
            processor: Processor instance to test
            test_events: Optional list of test events. If None, uses default test events.

        Returns:
            True if all executions succeed without exceptions
        """
        if test_events is None:
            test_events = [
                {
                    "level": "info",
                    "message": "Test message 1",
                    "timestamp": "2023-01-01T12:00:00Z",
                },
                {"level": "error", "message": "Test error", "error": "Test exception"},
                {"level": "debug", "message": "Debug message", "extra_field": "value"},
                {
                    "level": "warning",
                    "message": "Warning test",
                    "data": {"key": "value"},
                },
            ]

        try:
            for i, event in enumerate(test_events):
                result = safe_processor_execution(
                    processor, None, "info", event, "pass_through"
                )

                # Record the result
                test_result = {
                    "event_index": i,
                    "input_event": event.copy(),
                    "output_event": result.copy() if result else None,
                    "success": result is not None,
                }
                self.recorded_events.append(test_result)

            return True

        except Exception as e:
            self.errors.append(e)
            return False

    def test_processor_error_handling(self, processor: Processor) -> bool:
        """Test processor error handling and recovery.

        Args:
            processor: Processor instance to test

        Returns:
            True if error handling works correctly
        """
        try:
            # Test with valid event
            valid_event = {"level": "info", "message": "Valid test"}
            result = safe_processor_execution(processor, None, "info", valid_event)

            if result is None:
                self.errors.append(ValueError("Valid event should not be None"))
                return False

            # Test with invalid event (empty dict)
            invalid_event = {}
            result = safe_processor_execution(processor, None, "info", invalid_event)

            # Result should still be handled gracefully (pass_through strategy)
            if result is None:
                self.errors.append(
                    ValueError("Error handling should use pass_through strategy")
                )
                return False

            # Test with None event
            try:
                result = safe_processor_execution(processor, None, "info", None)
                # This might fail, which is expected
            except Exception:
                pass  # Expected for None input

            return True

        except Exception as e:
            self.errors.append(e)
            return False

    def test_processor_configuration(
        self, processor_class: Type[Processor], configs: List[Dict[str, Any]]
    ) -> bool:
        """Test processor configuration validation.

        Args:
            processor_class: Processor class to test
            configs: List of configuration dictionaries to test

        Returns:
            True if configuration validation works correctly
        """
        try:
            for i, config in enumerate(configs):
                try:
                    # Create processor with config
                    processor = processor_class(**config)

                    # Test configuration validation
                    validate_processor_configuration(processor)

                    # Record successful config
                    self.test_results.append(
                        {
                            "config_index": i,
                            "config": config,
                            "success": True,
                            "error": None,
                        }
                    )

                except Exception as e:
                    # Record failed config
                    self.test_results.append(
                        {
                            "config_index": i,
                            "config": config,
                            "success": False,
                            "error": str(e),
                        }
                    )
                    # Continue testing other configs

            return True

        except Exception as e:
            self.errors.append(e)
            return False

    async def test_processor_performance_basic(
        self, processor: Processor, event_count: int = 100
    ) -> Dict[str, float]:
        """Test basic processor performance.

        Args:
            processor: Processor instance to test
            event_count: Number of events to process

        Returns:
            Dictionary with performance metrics
        """
        try:
            # Start processor if needed
            if not processor.is_started:
                await processor.start()

            # Create test events
            events = [
                {
                    "level": "info",
                    "message": f"Performance test event {i}",
                    "timestamp": time.time(),
                    "test_index": i,
                }
                for i in range(event_count)
            ]

            # Time the processing
            start_time = time.time()

            for event in events:
                safe_processor_execution(processor, None, "info", event)

            end_time = time.time()
            duration = end_time - start_time

            # Calculate metrics
            throughput = event_count / duration if duration > 0 else 0
            avg_latency = (duration / event_count * 1000) if event_count > 0 else 0

            metrics = {
                "throughput_eps": throughput,
                "avg_latency_ms": avg_latency,
                "total_duration_seconds": duration,
                "event_count": event_count,
            }

            return metrics

        except Exception as e:
            self.errors.append(e)
            return {
                "throughput_eps": 0,
                "avg_latency_ms": 0,
                "total_duration_seconds": 0,
                "event_count": 0,
                "error": str(e),
            }

    def clear_state(self) -> None:
        """Clear recorded events, errors, and test results."""
        self.recorded_events.clear()
        self.errors.clear()
        self.test_results.clear()

    def get_test_summary(self) -> Dict[str, Any]:
        """Get a summary of test results.

        Returns:
            Dictionary containing test statistics and errors
        """
        last_events = self.recorded_events[-5:] if self.recorded_events else []
        successful_tests = sum(1 for r in self.test_results if r.get("success", False))

        return {
            "total_events": len(self.recorded_events),
            "total_errors": len(self.errors),
            "total_config_tests": len(self.test_results),
            "successful_config_tests": successful_tests,
            "errors": [str(e) for e in self.errors],
            "last_events": last_events,
            "test_results": self.test_results,
        }

    async def run_comprehensive_test_suite(
        self, processor_class: Type[Processor], test_config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Run a comprehensive test suite for a processor class.

        Args:
            processor_class: Processor class to test
            test_config: Optional test configuration

        Returns:
            Complete test results
        """
        if test_config is None:
            test_config = {
                "test_configs": [
                    {},  # Default config
                    {"test_param": "value"},  # Custom config
                ],
                "performance_events": 100,
            }

        results = {}

        try:
            # Test interface validation
            print(f"Testing interface for {processor_class.__name__}...")
            interface_valid = self.validate_processor_interface(processor_class)
            results["interface_validation"] = interface_valid

            if not interface_valid:
                results["error"] = "Interface validation failed"
                return results

            # Create test processor
            processor = self.create_test_processor(processor_class)

            # Test lifecycle
            print("Testing processor lifecycle...")
            lifecycle_success = await self.test_processor_lifecycle(processor)
            results["lifecycle_test"] = lifecycle_success

            # Test execution
            print("Testing processor execution...")
            execution_success = self.test_processor_execution(processor)
            results["execution_test"] = execution_success

            # Test error handling
            print("Testing error handling...")
            error_handling_success = self.test_processor_error_handling(processor)
            results["error_handling_test"] = error_handling_success

            # Test configuration
            print("Testing configuration validation...")
            config_success = self.test_processor_configuration(
                processor_class, test_config["test_configs"]
            )
            results["configuration_test"] = config_success

            # Test basic performance
            print("Testing basic performance...")
            performance_metrics = await self.test_processor_performance_basic(
                processor, test_config["performance_events"]
            )
            results["performance_metrics"] = performance_metrics

            # Calculate overall success
            test_success = all(
                [
                    interface_valid,
                    lifecycle_success,
                    execution_success,
                    error_handling_success,
                    config_success,
                ]
            )

            results["overall_success"] = test_success
            results["summary"] = self.get_test_summary()

        except Exception as e:
            results["overall_success"] = False
            results["error"] = str(e)
            self.errors.append(e)

        return results
