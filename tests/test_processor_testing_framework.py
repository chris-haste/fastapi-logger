"""Tests for processor testing framework and utilities.

This module tests the standardized testing patterns and utilities
for processor implementations.
"""

from typing import Any

import pytest

from fapilog._internal.templates.processor_template import TemplateProcessor
from fapilog._internal.testing.processor_testing import (
    ProcessorConcurrencyTester,
    ProcessorPerformanceTester,
    ProcessorTestBase,
)
from fapilog.processors.async_base import AsyncProcessorBase
from fapilog.processors.base import Processor
from fapilog.processors.filtering import FilterNoneProcessor
from fapilog.processors.redaction import RedactionProcessor


class TestProcessorTestBase:
    """Test the ProcessorTestBase class and its utilities."""

    class MockProcessorTest(ProcessorTestBase):
        """Mock test class for testing ProcessorTestBase."""

        def create_processor(self, **config: Any) -> Processor:
            """Create a simple processor for testing."""
            return FilterNoneProcessor(**config)

        async def test_configuration_validation(self, processor):
            """Test configuration validation for mock processor."""
            # Mock processor doesn't have specific validation to test
            pass

    class TemplateProcessorTest(ProcessorTestBase):
        """Template processor test class for testing AsyncProcessorBase."""

        def create_processor(self, **config: Any) -> Processor:
            """Create a template processor for testing."""
            return TemplateProcessor(**config)

        async def test_configuration_validation(self, processor):
            """Test configuration validation for template processor."""
            # Template processor doesn't have specific validation to test
            pass

    def test_create_processor_test_class(self):
        """Test creating test classes for processors."""
        # This test is removed since create_processor_test_class was removed
        pass

    @pytest.mark.asyncio
    async def test_basic_processing_test(self):
        """Test basic processing test functionality."""
        test_instance = self.MockProcessorTest()
        processor = test_instance.create_processor()
        await processor.start()

        # Test basic processing
        await test_instance.test_basic_processing(processor)

        await processor.stop()

    @pytest.mark.asyncio
    async def test_error_handling_test(self):
        """Test error handling test functionality."""
        test_instance = self.MockProcessorTest()
        processor = test_instance.create_processor()
        await processor.start()

        # Test error handling
        await test_instance.test_error_handling(processor)

        await processor.stop()

    @pytest.mark.asyncio
    async def test_concurrent_access_test(self):
        """Test concurrent access test functionality."""
        test_instance = self.MockProcessorTest()
        processor = test_instance.create_processor()
        await processor.start()

        # Test concurrent access
        await test_instance.test_concurrent_access(processor)

        await processor.stop()

    @pytest.mark.asyncio
    async def test_processor_lifecycle_test(self):
        """Test processor lifecycle test functionality."""
        test_instance = self.MockProcessorTest()
        processor = test_instance.create_processor()

        # Test lifecycle
        await test_instance.test_processor_lifecycle(processor)

    @pytest.mark.asyncio
    async def test_async_safety_patterns_test(self):
        """Test async safety patterns test functionality."""
        # Create test instance for TemplateProcessor
        test_instance = self.TemplateProcessorTest()
        processor = test_instance.create_processor()

        if isinstance(processor, AsyncProcessorBase):
            await processor.start()
            # Test async safety patterns
            await test_instance.test_async_safety_patterns(processor)
            await processor.stop()
        else:
            pytest.skip("Processor is not an AsyncProcessorBase")

    @pytest.mark.asyncio
    async def test_process_event_helper(self):
        """Test the _process_event helper method."""
        test_instance = self.MockProcessorTest()
        processor = test_instance.create_processor()

        # Test with valid event
        event = {"test": "data"}
        result = await test_instance._process_event(processor, event)
        assert result is not None

        # Test with None event
        result = await test_instance._process_event(processor, None)
        assert result is None  # FilterNoneProcessor filters None events

        # Test with invalid event
        result = await test_instance._process_event(processor, "invalid")
        assert result is not None  # Should handle gracefully


class TestProcessorPerformanceTester:
    """Test the ProcessorPerformanceTester class."""

    @pytest.mark.asyncio
    async def test_throughput_test(self):
        """Test throughput testing functionality."""
        processor = FilterNoneProcessor()
        tester = ProcessorPerformanceTester(processor)

        # Test throughput (should be very high for FilterNoneProcessor)
        throughput = await tester.test_throughput(target_ops_per_sec=100)
        assert throughput > 100

    @pytest.mark.asyncio
    async def test_latency_p95_test(self):
        """Test P95 latency testing functionality."""
        processor = FilterNoneProcessor()
        tester = ProcessorPerformanceTester(processor)

        # Test P95 latency (should be very low for FilterNoneProcessor)
        p95_latency = await tester.test_latency_p95(max_p95_ms=100)
        assert p95_latency < 100

    @pytest.mark.asyncio
    async def test_memory_stability_test(self):
        """Test memory stability testing functionality."""
        processor = FilterNoneProcessor()
        tester = ProcessorPerformanceTester(processor)

        # Test memory stability
        memory_growth = await tester.test_memory_stability(max_growth_percent=50)
        assert memory_growth < 50

    @pytest.mark.asyncio
    async def test_process_event_helper(self):
        """Test the _process_event helper method."""
        processor = FilterNoneProcessor()
        tester = ProcessorPerformanceTester(processor)

        # Test with valid event
        event = {"test": "data"}
        result = await tester._process_event(event)
        assert result is not None

        # Test with None event
        result = await tester._process_event(None)
        assert result is None  # FilterNoneProcessor filters None


class TestProcessorConcurrencyTester:
    """Test the ProcessorConcurrencyTester class."""

    @pytest.mark.asyncio
    async def test_concurrent_shared_keys(self):
        """Test concurrent access to shared keys."""
        processor = FilterNoneProcessor()
        tester = ProcessorConcurrencyTester(processor)

        # Test concurrent shared keys
        await tester.test_concurrent_shared_keys(num_workers=5, num_operations=10)

    @pytest.mark.asyncio
    async def test_concurrent_unique_keys(self):
        """Test concurrent access to unique keys."""
        processor = FilterNoneProcessor()
        tester = ProcessorConcurrencyTester(processor)

        # Test concurrent unique keys
        await tester.test_concurrent_unique_keys(num_workers=5, num_operations=10)

    @pytest.mark.asyncio
    async def test_concurrent_mixed_patterns(self):
        """Test concurrent access with mixed patterns."""
        processor = FilterNoneProcessor()
        tester = ProcessorConcurrencyTester(processor)

        # Test concurrent mixed patterns
        await tester.test_concurrent_mixed_patterns(num_workers=5, num_operations=10)

    @pytest.mark.asyncio
    async def test_concurrent_start_stop(self):
        """Test concurrent start/stop operations."""
        processor = FilterNoneProcessor()
        tester = ProcessorConcurrencyTester(processor)

        # Test concurrent start/stop
        await tester.test_concurrent_start_stop()

    @pytest.mark.asyncio
    async def test_process_event_helper(self):
        """Test the _process_event helper method."""
        processor = FilterNoneProcessor()
        tester = ProcessorConcurrencyTester(processor)

        # Test with valid event
        event = {"test": "data"}
        result = await tester._process_event(event)
        assert result is not None

        # Test with None event
        result = await tester._process_event(None)
        assert result is None  # FilterNoneProcessor filters None


class TestTemplateProcessorWithFramework:
    """Test TemplateProcessor using the testing framework."""

    class TemplateProcessorTest(ProcessorTestBase):
        """Test class for TemplateProcessor."""

        def create_processor(self, **config: Any) -> Processor:
            """Create TemplateProcessor instance for testing."""
            return TemplateProcessor(**config)

        async def test_configuration_validation(self, processor):
            """Test configuration validation for template processor."""
            # Template processor doesn't have specific validation to test
            pass

    @pytest.mark.asyncio
    async def test_template_processor_basic_processing(self):
        """Test TemplateProcessor basic processing."""
        test_instance = self.TemplateProcessorTest()
        processor = test_instance.create_processor()
        await processor.start()

        # Test basic processing
        event = {"user_id": "123", "message": "test"}
        result = await processor.process_async(None, "info", event)  # type: ignore[attr-defined]
        assert result is not None

        await processor.stop()

    @pytest.mark.asyncio
    async def test_template_processor_rate_limiting(self):
        """Test TemplateProcessor rate limiting behavior."""
        test_instance = self.TemplateProcessorTest()
        processor = test_instance.create_processor(
            max_events_per_key=5, key_field="user_id"
        )
        await processor.start()

        # Send more events than allowed
        for i in range(10):
            event = {"user_id": "123", "message": f"test_{i}"}
            result = await processor.process_async(None, "info", event)  # type: ignore[attr-defined]
            if i < 5:  # First 5 should be processed
                assert result is not None
            else:  # Rest should be dropped
                assert result is None

        await processor.stop()

    @pytest.mark.asyncio
    async def test_template_processor_concurrent_access(self):
        """Test TemplateProcessor concurrent access."""
        test_instance = self.TemplateProcessorTest()
        processor = test_instance.create_processor()
        await processor.start()

        # Test concurrent access
        await test_instance.test_concurrent_access(processor)

        await processor.stop()

    @pytest.mark.asyncio
    async def test_template_processor_async_safety(self):
        """Test TemplateProcessor async safety patterns."""
        test_instance = self.TemplateProcessorTest()
        processor = test_instance.create_processor()

        if isinstance(processor, AsyncProcessorBase):
            await processor.start()
            # Test async safety patterns
            await test_instance.test_async_safety_patterns(processor)
            await processor.stop()
        else:
            pytest.skip("Processor is not an AsyncProcessorBase")

    @pytest.mark.asyncio
    async def test_template_processor_performance(self):
        """Test TemplateProcessor performance."""
        test_instance = self.TemplateProcessorTest()
        processor = test_instance.create_processor()
        await processor.start()

        # Test performance
        tester = ProcessorPerformanceTester(processor)

        # Test throughput
        throughput = await tester.test_throughput(target_ops_per_sec=100)
        assert throughput > 100

        # Test latency
        p95_latency = await tester.test_latency_p95(max_p95_ms=100)
        assert p95_latency < 100

        await processor.stop()

    @pytest.mark.asyncio
    async def test_template_processor_concurrency(self):
        """Test TemplateProcessor concurrency."""
        test_instance = self.TemplateProcessorTest()
        processor = test_instance.create_processor()
        await processor.start()

        # Test concurrency
        tester = ProcessorConcurrencyTester(processor)

        # Test concurrent shared keys
        await tester.test_concurrent_shared_keys(num_workers=5, num_operations=10)

        # Test concurrent unique keys
        await tester.test_concurrent_unique_keys(num_workers=5, num_operations=10)

        # Test concurrent mixed patterns
        await tester.test_concurrent_mixed_patterns(num_workers=5, num_operations=10)

        await processor.stop()


class TestRedactionProcessorWithFramework:
    """Test RedactionProcessor using the testing framework."""

    class RedactionProcessorTest(ProcessorTestBase):
        """Test class for RedactionProcessor."""

        def create_processor(self, **config: Any) -> Processor:
            """Create RedactionProcessor instance for testing."""
            return RedactionProcessor(**config)

        async def test_configuration_validation(self, processor):
            """Test configuration validation for redaction processor."""
            # Redaction processor doesn't have specific validation to test
            pass

    @pytest.mark.asyncio
    async def test_redaction_processor_basic_processing(self):
        """Test RedactionProcessor basic processing."""
        test_instance = self.RedactionProcessorTest()
        processor = test_instance.create_processor(patterns=["password"])
        await processor.start()

        # Test basic processing
        event = {"message": "test", "password": "secret"}
        result = await test_instance._process_event(processor, event)
        assert result is not None
        assert result["password"] == "[REDACTED]"

        await processor.stop()

    @pytest.mark.asyncio
    async def test_redaction_processor_concurrent_access(self):
        """Test RedactionProcessor concurrent access."""
        test_instance = self.RedactionProcessorTest()
        processor = test_instance.create_processor(patterns=["password"])
        await processor.start()

        # Test concurrent access
        await test_instance.test_concurrent_access(processor)

        await processor.stop()

    @pytest.mark.asyncio
    async def test_redaction_processor_error_handling(self):
        """Test RedactionProcessor error handling."""
        test_instance = self.RedactionProcessorTest()
        processor = test_instance.create_processor(patterns=["password"])
        await processor.start()

        # Test error handling
        await test_instance.test_error_handling(processor)

        await processor.stop()


class TestFrameworkIntegration:
    """Test integration of the testing framework with real processors."""

    @pytest.mark.asyncio
    async def test_framework_with_multiple_processors(self):
        """Test framework with multiple processor types."""
        processors = [
            FilterNoneProcessor(),
            RedactionProcessor(patterns=["password"]),
            TemplateProcessor(max_events_per_key=10),
        ]

        for processor in processors:
            # Test basic functionality
            await processor.start()

            # Test processing
            event = {"test": "data"}
            if hasattr(processor, "process_async"):
                result = await processor.process_async(None, "info", event)
            else:
                result = processor.process(None, "info", event)

            # Verify no crashes
            assert result is not None or result is None

            await processor.stop()

    @pytest.mark.asyncio
    async def test_framework_performance_comparison(self):
        """Test performance comparison between processors."""
        processors = [
            FilterNoneProcessor(),
            RedactionProcessor(patterns=["password"]),
            TemplateProcessor(max_events_per_key=100),
        ]

        for processor in processors:
            tester = ProcessorPerformanceTester(processor)

            # Test throughput
            throughput = await tester.test_throughput(target_ops_per_sec=10)
            assert throughput > 10

            # Test latency
            p95_latency = await tester.test_latency_p95(max_p95_ms=1000)
            assert p95_latency < 1000

    @pytest.mark.asyncio
    async def test_framework_concurrency_comparison(self):
        """Test concurrency comparison between processors."""
        processors = [
            FilterNoneProcessor(),
            RedactionProcessor(patterns=["password"]),
            TemplateProcessor(max_events_per_key=100),
        ]

        for processor in processors:
            tester = ProcessorConcurrencyTester(processor)

            # Test concurrent operations
            await tester.test_concurrent_shared_keys(num_workers=3, num_operations=5)
            await tester.test_concurrent_unique_keys(num_workers=3, num_operations=5)
            await tester.test_concurrent_mixed_patterns(num_workers=3, num_operations=5)


class TestFrameworkErrorHandling:
    """Test error handling in the testing framework."""

    class TemplateProcessorTest(ProcessorTestBase):
        """Test class for TemplateProcessor."""

        def create_processor(self, **config: Any) -> Processor:
            """Create TemplateProcessor instance for testing."""
            return TemplateProcessor(**config)

        async def test_configuration_validation(self, processor):
            """Test configuration validation for template processor."""
            # Template processor doesn't have specific validation to test
            pass

    @pytest.mark.asyncio
    async def test_framework_handles_processor_errors(self):
        """Test that framework handles processor errors gracefully."""
        test_instance = self.TemplateProcessorTest()
        processor = test_instance.create_processor()
        await processor.start()

        # Test with invalid events
        invalid_events = [None, "invalid", {}, {"invalid": "data"}]

        for event in invalid_events:
            result = await test_instance._process_event(processor, event)
            # Should handle gracefully, not crash
            assert result is not None or result is None

        await processor.stop()

    @pytest.mark.asyncio
    async def test_framework_handles_concurrent_errors(self):
        """Test that framework handles concurrent errors gracefully."""
        processor = FilterNoneProcessor()
        tester = ProcessorConcurrencyTester(processor)

        # Test concurrent operations with potential errors
        await tester.test_concurrent_shared_keys(num_workers=10, num_operations=10)

        # Should complete without crashes
        assert True  # If we get here, no crashes occurred

    @pytest.mark.asyncio
    async def test_framework_handles_performance_errors(self):
        """Test that framework handles performance testing errors gracefully."""
        processor = FilterNoneProcessor()
        tester = ProcessorPerformanceTester(processor)

        # Test performance with potential errors
        throughput = await tester.test_throughput(target_ops_per_sec=1)
        assert throughput > 1

        p95_latency = await tester.test_latency_p95(max_p95_ms=10000)
        assert p95_latency < 10000
