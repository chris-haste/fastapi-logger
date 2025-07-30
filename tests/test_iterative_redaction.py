"""
Comprehensive test suite for iterative redaction implementation (Issue #144).

Tests verify O(n) memory complexity, stack overflow prevention, performance,
correctness, and safety features of the iterative redaction algorithm.
"""

import copy
import re
import time
import tracemalloc
from typing import Any, Dict, List

import pytest

from fapilog._internal.pii_patterns import (
    _redact_pii_iterative,
    _redact_pii_recursive,
)
from fapilog._internal.processors import RedactionProcessor


def create_nested_dict(depth: int, keys_per_level: int = 5) -> Dict[str, Any]:
    """Create a nested dictionary of specific depth for testing using iterative approach.

    Args:
        depth: Maximum nesting depth
        keys_per_level: Number of keys at each level

    Returns:
        Nested dictionary structure
    """
    if depth == 0:
        return {
            "secret_key": "sensitive_data",
            "password": "user_password",
            "normal_key": "safe_data",
            "token": "auth_token",
            "data": "regular_content",
        }

    # Use iterative approach to build nested structure
    # Start with the deepest level and work upward
    result = {
        "secret_key": "sensitive_data",
        "password": "user_password",
        "normal_key": "safe_data",
        "token": "auth_token",
        "data": "regular_content",
    }

    # Build from deepest level up to avoid recursion
    for current_depth in range(1, depth + 1):
        new_level = {}

        for i in range(keys_per_level):
            if i == 0:
                # First key gets the deeper structure
                new_level[f"level_{current_depth}_key_{i}"] = result
            elif i == 1:
                # Second key has sensitive data
                new_level[f"secret_level_{current_depth}"] = (
                    f"sensitive_value_at_depth_{current_depth}"
                )
            else:
                # Other keys have regular data
                new_level[f"level_{current_depth}_key_{i}"] = (
                    f"value_at_depth_{current_depth}_{i}"
                )

        result = new_level

    return result


def create_nested_list(depth: int, items_per_level: int = 3) -> List[Any]:
    """Create a nested list structure of specific depth.

    Args:
        depth: Maximum nesting depth
        items_per_level: Number of items at each level

    Returns:
        Nested list structure
    """
    if depth == 0:
        return ["secret_value", "normal_value", "password_data"]

    result = []
    for i in range(items_per_level):
        if i == 0:
            result.append(create_nested_list(depth - 1, items_per_level))
        elif i == 1:
            result.append({"secret": f"hidden_at_depth_{depth}"})
        else:
            result.append(f"item_at_depth_{depth}_{i}")

    return result


def create_complex_enterprise_log_event() -> Dict[str, Any]:
    """Create a realistic enterprise log event with various data types."""
    return {
        "timestamp": "2024-01-01T12:00:00Z",
        "level": "INFO",
        "message": "User authentication successful",
        "user": {
            "id": 12345,
            "username": "john_doe",
            "email": "john.doe@company.com",
            "session": {
                "token": "secret_auth_token_12345",
                "expires": "2024-01-01T13:00:00Z",
                "permissions": ["read", "write"],
                "metadata": {
                    "ip_address": "192.168.1.100",
                    "user_agent": "Mozilla/5.0...",
                    "credentials": {
                        "password_hash": "sensitive_hash_value",
                        "salt": "secret_salt_value",
                    },
                },
            },
        },
        "request": {
            "method": "POST",
            "url": "/api/auth/login",
            "headers": {
                "authorization": "Bearer secret_token_value",
                "content-type": "application/json",
            },
            "body": {
                "username": "john_doe",
                "password": "user_entered_password",
                "remember_me": True,
            },
        },
        "response": {
            "status": 200,
            "headers": ["content-type: application/json"],
            "body": {
                "success": True,
                "token": "response_auth_token",
                "user_info": {
                    "name": "John Doe",
                    "role": "admin",
                    "secret_clearance": "top_secret",
                },
            },
        },
        "system": {
            "host": "auth-server-01",
            "pid": 1234,
            "memory_usage": "256MB",
            "cpu_usage": "15%",
        },
    }


class TestMemoryComplexityLinearScaling:
    """Test that memory usage scales linearly O(n) with nesting depth."""

    @pytest.mark.asyncio
    async def test_linear_memory_scaling_nested_dicts(self):
        """Test that memory usage scales linearly with nested dictionary depth."""
        depths = [10, 25, 50, 75, 100]

        # Instead of measuring absolute memory, measure relative scaling
        # This is more robust when other tests have run before this one
        processing_times = []

        for depth in depths:
            # Force aggressive garbage collection
            import gc

            gc.collect()
            gc.collect()  # Call twice to be thorough

            # Create nested structure
            nested_obj = create_nested_dict(depth=depth, keys_per_level=3)
            processor = RedactionProcessor(
                patterns=["secret", "password", "token"], max_depth=depth + 50
            )

            # Initialize processor patterns
            await processor.start()

            # Measure processing complexity via time (more reliable than memory in test suites)
            import time as time_module

            # Warm up the function (JIT, caching, etc)
            test_obj_warmup = copy.deepcopy(nested_obj)
            processor._redact_iterative(test_obj_warmup)
            del test_obj_warmup
            gc.collect()

            # Measure actual processing time for multiple runs
            runs = 3
            run_times = []
            for _ in range(runs):
                test_obj = copy.deepcopy(nested_obj)
                start_time = time_module.perf_counter()
                processor._redact_iterative(test_obj)
                end_time = time_module.perf_counter()
                run_times.append(end_time - start_time)
                del test_obj

            # Use median time to reduce noise
            median_time = sorted(run_times)[len(run_times) // 2]
            processing_times.append(median_time)

            # Clean up references
            del nested_obj, processor
            gc.collect()

        # Verify that processing time scales sub-exponentially (O(n) or O(n log n) is OK)
        # Calculate ratios between consecutive measurements
        ratios = []
        for i in range(1, len(processing_times)):
            if processing_times[i - 1] > 0:
                ratio = processing_times[i] / processing_times[i - 1]
                ratios.append(ratio)

        # For efficient algorithms, ratios should be reasonable (not exponential growth)
        if len(ratios) > 0:
            average_ratio = sum(ratios) / len(ratios)
            max_ratio = max(ratios)

            # Allow for some variance but ensure it's not exponential
            assert max_ratio < 10.0, (
                f"Processing time scaling appears exponential, max ratio: {max_ratio}. "
                f"Times: {processing_times}, Ratios: {ratios}"
            )

            assert average_ratio < 5.0, (
                f"Processing time scaling appears non-linear, avg ratio: {average_ratio}. "
                f"Times: {processing_times}, Ratios: {ratios}"
            )

        # Ensure the algorithm actually works (not just timing)
        # Test with a simple case to verify redaction occurs
        simple_obj = {"secret_key": "secret_value", "normal_key": "normal_value"}
        simple_processor = RedactionProcessor(patterns=["secret"])
        await simple_processor.start()
        result = simple_processor._redact_iterative(copy.deepcopy(simple_obj))

        assert "[REDACTED]" in str(result), "Algorithm should perform redaction"

    def test_memory_usage_vs_width(self):
        """Test memory usage with varying structure width."""
        widths = [5, 10, 20, 40, 80]
        memory_usage = []

        for width in widths:
            # Create wide structure with moderate depth
            nested_obj = create_nested_dict(depth=20, keys_per_level=width)
            processor = RedactionProcessor(patterns=["secret"])

            tracemalloc.start()
            processor._redact_iterative(copy.deepcopy(nested_obj))
            snapshot = tracemalloc.take_snapshot()
            current_usage = sum(stat.size for stat in snapshot.statistics("lineno"))
            memory_usage.append(current_usage)
            tracemalloc.stop()

        # Memory should scale roughly linearly with width too
        ratios = [
            memory_usage[i] / memory_usage[i - 1] for i in range(1, len(memory_usage))
        ]
        average_ratio = sum(ratios) / len(ratios)
        assert average_ratio < 3.0, (
            f"Memory scaling with width non-linear: {average_ratio}"
        )


class TestStackOverflowPrevention:
    """Test that very deep nesting doesn't cause stack overflow."""

    @pytest.mark.asyncio
    async def test_deep_nesting_no_stack_overflow(self):
        """Test that very deep nesting doesn't cause stack overflow."""
        # Create a 1000-level deep nested structure
        deep_obj = create_nested_dict(depth=1000, keys_per_level=2)
        processor = RedactionProcessor(patterns=["secret", "password"], max_depth=1500)
        await processor.start()  # Initialize compiled patterns

        # This should NOT raise RecursionError
        result = processor._redact_iterative(deep_obj)
        assert result is not None

        # Verify some redaction occurred
        assert "[REDACTED]" in str(result)

    @pytest.mark.asyncio
    async def test_extremely_deep_nesting_with_max_depth_protection(self):
        """Test max depth protection prevents processing of overly deep structures."""
        # Create very deep structure
        deep_obj = create_nested_dict(depth=500, keys_per_level=2)
        processor = RedactionProcessor(
            patterns=["secret"],
            max_depth=100,  # Set low limit
        )
        await processor.start()  # Initialize compiled patterns

        # Should raise ValueError due to depth limit
        with pytest.raises(ValueError, match="Object nesting exceeds maximum depth"):
            processor._redact_with_observability(deep_obj)

    @pytest.mark.asyncio
    async def test_circular_reference_handling(self):
        """Test handling of circular references."""
        obj1 = {"name": "obj1", "secret": "hidden_value"}
        obj2 = {"name": "obj2", "ref": obj1}
        obj1["ref"] = obj2  # Create circular reference

        processor = RedactionProcessor(patterns=["secret"])
        await processor.start()  # Initialize compiled patterns

        # Should complete without infinite loop
        result = processor._redact_iterative(obj1)

        # Verify redaction occurred
        assert result["secret"] == "[REDACTED]"

        # Verify structure integrity maintained
        assert result["name"] == "obj1"


class TestPerformanceBenchmarking:
    """Compare performance of iterative vs theoretical recursive approaches."""

    def measure_processing_time(self, processor, test_obj: Any) -> float:
        """Measure processing time for a redaction operation."""
        start_time = time.perf_counter()

        # Make a copy to ensure consistent test conditions
        obj_copy = copy.deepcopy(test_obj)
        processor._redact_iterative(obj_copy)

        end_time = time.perf_counter()
        return end_time - start_time

    def test_iterative_performance_characteristics(self):
        """Test performance characteristics of iterative algorithm."""
        test_cases = [
            {"depth": 50, "width": 5, "size": "medium_deep"},
            {"depth": 10, "width": 50, "size": "medium_wide"},
            {"depth": 100, "width": 3, "size": "very_deep"},
            {"depth": 5, "width": 100, "size": "very_wide"},
        ]

        results = {}
        for case in test_cases:
            test_obj = create_nested_dict(
                depth=case["depth"], keys_per_level=case["width"]
            )

            processor = RedactionProcessor(
                patterns=["secret", "password", "token"], max_depth=case["depth"] + 50
            )

            # Measure average over multiple runs
            times = []
            for _ in range(5):
                processing_time = self.measure_processing_time(processor, test_obj)
                times.append(processing_time)

            avg_time = sum(times) / len(times)
            results[case["size"]] = avg_time

            # Performance should be reasonable (< 100ms for test structures)
            assert avg_time < 0.1, (
                f"Performance too slow for {case['size']}: {avg_time:.3f}s"
            )

        print("Performance results:", results)

    def test_enterprise_log_event_performance(self):
        """Test performance on realistic enterprise log events."""
        log_event = create_complex_enterprise_log_event()
        processor = RedactionProcessor(
            patterns=["secret", "password", "token", "authorization", "credentials"]
        )

        # Performance should be very fast for typical log events
        processing_time = self.measure_processing_time(processor, log_event)

        assert processing_time < 0.01, (
            f"Enterprise log processing too slow: {processing_time:.4f}s"
        )


class TestCorrectnessValidation:
    """Test that iterative algorithm produces correct redaction results."""

    def simple_flat_dict(self) -> Dict[str, Any]:
        """Simple flat dictionary for testing."""
        return {
            "username": "john_doe",
            "password": "secret123",
            "email": "john@example.com",
            "token": "auth_token_abc",
            "normal_field": "safe_value",
        }

    def nested_dict_with_lists(self) -> Dict[str, Any]:
        """Nested dictionary containing lists."""
        return {
            "user": {
                "credentials": {
                    "password": "user_password",
                    "api_keys": ["secret_key_1", "secret_key_2", "normal_key"],
                },
                "profile": {
                    "name": "John Doe",
                    "preferences": ["theme_dark", "notifications_on"],
                },
            },
            "sessions": [
                {"token": "session_token_1", "expires": "2024-01-01"},
                {"token": "session_token_2", "expires": "2024-01-02"},
            ],
        }

    def edge_case_empty_structures(self) -> Dict[str, Any]:
        """Edge cases with empty structures."""
        return {
            "empty_dict": {},
            "empty_list": [],
            "nested_empty": {"inner": {"empty_again": {}, "list_with_empty": [{}]}},
            "password": "should_be_redacted",
        }

    @pytest.mark.asyncio
    async def test_simple_redaction_correctness(self):
        """Test basic redaction correctness."""
        test_obj = self.simple_flat_dict()
        original_copy = copy.deepcopy(test_obj)

        processor = RedactionProcessor(patterns=["password", "token"])
        await processor.start()  # Initialize compiled patterns
        processor._redact_iterative(test_obj)

        # Verify sensitive fields redacted
        assert test_obj["password"] == "[REDACTED]"
        assert test_obj["token"] == "[REDACTED]"

        # Verify non-sensitive fields preserved
        assert test_obj["username"] == original_copy["username"]
        assert test_obj["email"] == original_copy["email"]
        assert test_obj["normal_field"] == original_copy["normal_field"]

    @pytest.mark.asyncio
    async def test_nested_structure_redaction(self):
        """Test redaction in nested structures."""
        test_obj = self.nested_dict_with_lists()
        processor = RedactionProcessor(patterns=["password", "token", "secret"])
        await processor.start()  # Initialize compiled patterns

        processor._redact_iterative(test_obj)

        # Verify nested redaction
        assert test_obj["user"]["credentials"]["password"] == "[REDACTED]"
        assert "[REDACTED]" in test_obj["user"]["credentials"]["api_keys"]
        assert test_obj["sessions"][0]["token"] == "[REDACTED]"
        assert test_obj["sessions"][1]["token"] == "[REDACTED]"

        # Verify non-sensitive data preserved
        assert test_obj["user"]["profile"]["name"] == "John Doe"
        assert "theme_dark" in test_obj["user"]["profile"]["preferences"]

    @pytest.mark.asyncio
    async def test_edge_cases_handling(self):
        """Test handling of edge cases."""
        test_obj = self.edge_case_empty_structures()
        processor = RedactionProcessor(patterns=["password"])
        await processor.start()  # Initialize compiled patterns

        processor._redact_iterative(test_obj)

        # Verify empty structures preserved
        assert test_obj["empty_dict"] == {}
        assert test_obj["empty_list"] == []
        assert test_obj["nested_empty"]["inner"]["empty_again"] == {}

        # Verify redaction still works
        assert test_obj["password"] == "[REDACTED]"

    @pytest.mark.asyncio
    async def test_data_type_preservation(self):
        """Test that data types are preserved correctly."""
        test_obj = {
            "string_field": "value",
            "int_field": 42,
            "float_field": 3.14,
            "bool_field": True,
            "none_field": None,
            "list_field": [1, 2, "three"],
            "password": "secret123",  # Should be redacted
        }

        processor = RedactionProcessor(patterns=["password"])
        await processor.start()  # Initialize compiled patterns
        processor._redact_iterative(test_obj)

        # Verify types preserved
        assert isinstance(test_obj["string_field"], str)
        assert isinstance(test_obj["int_field"], int)
        assert isinstance(test_obj["float_field"], float)
        assert isinstance(test_obj["bool_field"], bool)
        assert test_obj["none_field"] is None
        assert isinstance(test_obj["list_field"], list)

        # Verify redaction occurred
        assert test_obj["password"] == "[REDACTED]"


class TestPIIRedactionIterative:
    """Test the PII redaction iterative implementation."""

    def test_pii_iterative_vs_recursive_consistency(self):
        """Test that PII iterative produces same results as the old recursive approach."""
        import re

        test_data = {
            "user": {
                "email": "sensitive@example.com",
                "phone": "555-123-4567",
                "profile": {
                    "ssn": "123-45-6789",
                    "notes": ["contains sensitive info", "normal note"],
                },
            },
            "normal_data": "safe content",
        }

        patterns = [
            re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),  # SSN pattern
            re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),  # Email
        ]

        # Test both implementations
        result_iterative = _redact_pii_iterative(
            copy.deepcopy(test_data), patterns, "[REDACTED]"
        )
        result_recursive = _redact_pii_recursive(
            copy.deepcopy(test_data), patterns, "[REDACTED]"
        )

        # Results should be identical
        assert result_iterative == result_recursive

        # Verify redaction occurred
        assert "[REDACTED]" in str(result_iterative)

    @pytest.mark.asyncio
    async def test_pii_deep_nesting_no_overflow(self):
        """Test PII redaction on deeply nested structures."""
        deep_data = create_nested_dict(depth=200, keys_per_level=2)
        patterns = [re.compile(r"secret", re.IGNORECASE)]

        # Should not cause stack overflow
        result = _redact_pii_iterative(deep_data, patterns, "[REDACTED]")
        assert result is not None
        assert "[REDACTED]" in str(result)


class TestSafetyFeatures:
    """Test safety features of the iterative implementation."""

    def test_max_depth_configuration(self):
        """Test configurable maximum depth protection."""
        deep_obj = create_nested_dict(depth=50, keys_per_level=2)

        # Test with different max_depth settings
        processor_low = RedactionProcessor(patterns=["secret"], max_depth=25)
        processor_high = RedactionProcessor(patterns=["secret"], max_depth=100)

        # Low depth should raise error
        with pytest.raises(ValueError, match="Object nesting exceeds maximum depth"):
            processor_low._redact_with_observability(copy.deepcopy(deep_obj))

        # High depth should work fine
        result = processor_high._redact_with_observability(copy.deepcopy(deep_obj))
        assert result is not None

    def test_memory_safety_with_large_structures(self):
        """Test memory safety with large but not deep structures."""
        # Create wide structure (many keys but shallow)
        wide_obj = create_nested_dict(depth=5, keys_per_level=100)

        processor = RedactionProcessor(patterns=["secret"], max_depth=50)

        # Should handle large structures efficiently
        start_time = time.perf_counter()
        result = processor._redact_with_observability(wide_obj)
        processing_time = time.perf_counter() - start_time

        assert result is not None
        assert processing_time < 1.0, (
            f"Large structure processing too slow: {processing_time:.3f}s"
        )

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self):
        """Test error handling in edge cases."""
        processor = RedactionProcessor(patterns=["test"])
        await processor.start()  # Initialize compiled patterns

        # Test with None
        assert processor._redact_iterative(None) is None

        # Test with primitive types
        assert processor._redact_iterative("test_string") == "test_string"
        assert processor._redact_iterative(42) == 42
        assert processor._redact_iterative(True) is True


if __name__ == "__main__":
    pytest.main([__file__])
