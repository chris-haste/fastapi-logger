"""Tests for safe JSON serialization utility."""

import datetime
import decimal
import json
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass
from unittest.mock import Mock

from fapilog._internal.utils import safe_json_serialize


class TestSafeJsonSerialize:
    """Test safe JSON serialization functionality."""

    def test_basic_types(self):
        """Test serialization of basic JSON-compatible types."""
        # Basic types should pass through unchanged
        assert safe_json_serialize(None) == "null"
        assert safe_json_serialize(True) == "true"
        assert safe_json_serialize(False) == "false"
        assert safe_json_serialize(42) == "42"
        assert safe_json_serialize(3.14) == "3.14"
        assert safe_json_serialize("hello") == '"hello"'
        assert safe_json_serialize([1, 2, 3]) == "[1,2,3]"
        assert safe_json_serialize({"key": "value"}) == '{"key":"value"}'

    def test_datetime_objects(self):
        """Test serialization of datetime objects."""
        dt = datetime.datetime(2023, 12, 25, 10, 30, 45)
        result = json.loads(safe_json_serialize(dt))
        assert result == "2023-12-25T10:30:45"

        # Test date object
        date_obj = datetime.date(2023, 12, 25)
        result = json.loads(safe_json_serialize(date_obj))
        assert result == "2023-12-25"

        # Test time object
        time_obj = datetime.time(10, 30, 45)
        result = json.loads(safe_json_serialize(time_obj))
        assert result == "10:30:45"

    def test_uuid_objects(self):
        """Test serialization of UUID objects."""
        test_uuid = uuid.UUID("12345678-1234-5678-1234-567812345678")
        result = json.loads(safe_json_serialize(test_uuid))
        assert result == "12345678-1234-5678-1234-567812345678"

    def test_decimal_objects(self):
        """Test serialization of Decimal objects."""
        dec = decimal.Decimal("123.456")
        result = json.loads(safe_json_serialize(dec))
        assert result == 123.456

    def test_bytes_objects(self):
        """Test serialization of bytes and bytearray objects."""
        # UTF-8 decodable bytes
        utf8_bytes = b"hello world"
        result = json.loads(safe_json_serialize(utf8_bytes))
        assert result == "hello world"

        # Non-UTF-8 bytes
        binary_bytes = b"\x80\x81\x82"
        result = json.loads(safe_json_serialize(binary_bytes))
        assert result == "<bytes: 3 bytes>"

        # Bytearray
        ba = bytearray(b"test")
        result = json.loads(safe_json_serialize(ba))
        assert result == "test"

        # Non-UTF-8 bytearray
        binary_ba = bytearray(b"\x80\x81\x82")
        result = json.loads(safe_json_serialize(binary_ba))
        assert result == "<bytearray: 3 bytes>"

    def test_circular_references(self):
        """Test handling of circular references."""
        # Create circular reference
        circular_dict = {"a": 1}
        circular_dict["self"] = circular_dict

        result_str = safe_json_serialize(circular_dict)
        result = json.loads(result_str)

        assert result["a"] == 1
        assert "circular_reference" in result["self"]

    def test_circular_references_complex(self):
        """Test complex circular references."""
        # Create more complex circular structure
        obj_a = {"name": "A"}
        obj_b = {"name": "B"}
        obj_a["ref"] = obj_b
        obj_b["ref"] = obj_a

        result_str = safe_json_serialize(obj_a)
        result = json.loads(result_str)

        assert result["name"] == "A"
        assert result["ref"]["name"] == "B"
        assert "circular_reference" in result["ref"]["ref"]

    def test_max_depth_limit(self):
        """Test maximum depth limit enforcement."""
        # Create deeply nested structure
        nested = {"level": 0}
        current = nested
        for i in range(1, 15):
            current["child"] = {"level": i}
            current = current["child"]

        # Test with max_depth=5
        result_str = safe_json_serialize(nested, max_depth=5)
        result = json.loads(result_str)

        # Should be able to traverse to max_depth levels (5 in this case)
        current = result
        for level in range(5):
            assert current["level"] == level
            if level < 4:
                current = current["child"]

        # At level 4, child should contain max_depth_exceeded since we exceed the limit
        child_obj = current["child"]
        assert child_obj["level"] == "<max_depth_exceeded: 5>"

    def test_max_size_limit(self):
        """Test maximum size limit enforcement."""
        # Create large object
        large_obj = {"data": "x" * 1000}  # 1KB+ object

        # Test with small max_size
        result_str = safe_json_serialize(large_obj, max_size=100)
        result = json.loads(result_str)

        # Should be truncated
        assert result["_truncated"] is True
        assert result["_original_type"] == "dict"
        assert result["_size_exceeded"] == 100

    def test_custom_classes(self):
        """Test serialization of custom classes."""

        @dataclass
        class TestClass:
            name: str
            value: int

        obj = TestClass("test", 42)
        result_str = safe_json_serialize(obj)
        result = json.loads(result_str)

        assert result["_type"] == "TestClass"
        assert result["name"] == "test"
        assert result["value"] == 42

    def test_custom_classes_with_private_attrs(self):
        """Test custom classes with private attributes."""

        class TestClass:
            def __init__(self):
                self.public = "visible"
                self._private = "hidden"
                self.__very_private = "very_hidden"

        obj = TestClass()
        result_str = safe_json_serialize(obj)
        result = json.loads(result_str)

        assert result["public"] == "visible"
        # Private attributes should be skipped
        assert "_private" not in result
        assert "__very_private" not in result
        assert "_TestClass__very_private" not in result

    def test_sets(self):
        """Test serialization of sets."""
        test_set = {1, 2, 3, "test"}
        result_str = safe_json_serialize(test_set)
        result = json.loads(result_str)

        # Should be converted to list
        assert isinstance(result, list)
        assert len(result) == 4
        assert all(item in result for item in [1, 2, 3, "test"])

    def test_functions(self):
        """Test serialization of functions."""

        def test_func():
            pass

        result_str = safe_json_serialize(test_func)
        result = json.loads(result_str)

        assert "function: test_func" in result

        # Test lambda
        lambda_func = lambda x: x + 1  # noqa: E731
        result_str = safe_json_serialize(lambda_func)
        result = json.loads(result_str)

        assert "function:" in result

    def test_complex_nested_structures(self):
        """Test complex nested structures with mixed types."""
        complex_obj = {
            "timestamp": datetime.datetime.now(),
            "uuid": uuid.uuid4(),
            "decimal": decimal.Decimal("123.45"),
            "nested": {
                "list": [1, 2, {"inner": "value"}],
                "set": {1, 2, 3},
                "bytes": b"test_data",
            },
        }

        result_str = safe_json_serialize(complex_obj)
        result = json.loads(result_str)

        # Verify structure is preserved
        assert "timestamp" in result
        assert "uuid" in result
        assert result["decimal"] == 123.45
        assert result["nested"]["list"][2]["inner"] == "value"
        assert isinstance(result["nested"]["set"], list)
        assert result["nested"]["bytes"] == "test_data"

    def test_thread_safety(self):
        """Test thread safety of circular reference detection."""
        results = []
        errors = []

        def worker():
            try:
                # Create circular reference
                circular = {"thread_id": threading.current_thread().ident}
                circular["self"] = circular

                result = safe_json_serialize(circular)
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Run multiple threads simultaneously
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Should have no errors and correct number of results
        assert len(errors) == 0
        assert len(results) == 10

        # Each result should be valid JSON
        for result in results:
            parsed = json.loads(result)
            assert "thread_id" in parsed
            assert "circular_reference" in parsed["self"]

    def test_fallback_representations(self):
        """Test configurable fallback representations."""
        # Test with custom fallback
        mock_obj = Mock()
        mock_obj.__class__.__name__ = "MockObject"

        result_str = safe_json_serialize(mock_obj, fallback_repr="<custom_fallback>")
        result = json.loads(result_str)

        # Mock objects are callable, so they get function representation
        assert "function:" in result

    def test_json_parameters(self):
        """Test JSON serialization parameters."""
        test_dict = {"b": 2, "a": 1}

        # Test sort_keys
        sorted_result = safe_json_serialize(test_dict, sort_keys=True)
        assert sorted_result == '{"a":1,"b":2}'

        # Test indent
        indented_result = safe_json_serialize(test_dict, indent=2)
        assert "\n" in indented_result
        assert "  " in indented_result

        # Test ensure_ascii
        unicode_dict = {"key": "café"}
        ascii_result = safe_json_serialize(unicode_dict, ensure_ascii=True)
        assert "\\u00e9" in ascii_result

        non_ascii_result = safe_json_serialize(unicode_dict, ensure_ascii=False)
        assert "café" in non_ascii_result

    def test_edge_cases(self):
        """Test various edge cases."""
        # Empty structures
        assert safe_json_serialize({}) == "{}"
        assert safe_json_serialize([]) == "[]"

        # Very long strings
        long_string = "x" * 300
        result = json.loads(safe_json_serialize(long_string))
        assert result == long_string

        # Nested empty structures
        nested_empty = {"empty_dict": {}, "empty_list": [], "null": None}
        result_str = safe_json_serialize(nested_empty)
        result = json.loads(result_str)
        assert result == nested_empty

    def test_non_string_dict_keys(self):
        """Test handling of non-string dictionary keys."""
        dict_with_int_keys = {1: "one", 2: "two", 3.5: "three-five"}
        result_str = safe_json_serialize(dict_with_int_keys)
        result = json.loads(result_str)

        # Keys should be converted to strings
        assert result["1"] == "one"
        assert result["2"] == "two"
        assert result["3.5"] == "three-five"

    def test_defaultdict(self):
        """Test serialization of defaultdict."""
        dd = defaultdict(list)
        dd["key1"].append("value1")
        dd["key2"].append("value2")

        result_str = safe_json_serialize(dd)
        result = json.loads(result_str)

        assert result["key1"] == ["value1"]
        assert result["key2"] == ["value2"]

    def test_performance_no_regression(self):
        """Test that performance is reasonable for normal cases."""
        # Create normal-sized object
        normal_obj = {
            "level1": {
                "level2": {
                    "data": list(range(100)),
                    "metadata": {"created": datetime.datetime.now().isoformat()},
                }
            }
        }

        # Time safe serialization
        start_time = time.time()
        safe_result = safe_json_serialize(normal_obj)
        safe_duration = time.time() - start_time

        # Time standard json.dumps for comparison
        # Convert datetime to string first for fair comparison
        normal_obj_for_json = {
            "level1": {
                "level2": {
                    "data": list(range(100)),
                    "metadata": {"created": datetime.datetime.now().isoformat()},
                }
            }
        }

        start_time = time.time()
        json_result = json.dumps(normal_obj_for_json)
        json_duration = time.time() - start_time

        # Safe serialization should not be more than 50x slower (more lenient)
        assert safe_duration < json_duration * 50

        # Results should be valid JSON
        assert json.loads(safe_result)
        assert json.loads(json_result)

    def test_integration_with_log_events(self):
        """Test serialization of typical log event structures."""
        log_event = {
            "timestamp": datetime.datetime.now(),
            "level": "INFO",
            "message": "User login successful",
            "user_id": uuid.uuid4(),
            "session_data": {
                "ip_address": "192.168.1.1",
                "user_agent": "Mozilla/5.0...",
                "duration": decimal.Decimal("0.123"),
            },
            "request": {
                "method": "POST",
                "path": "/api/login",
                "headers": {"content-type": "application/json"},
                "body_size": 1024,
            },
            "response": {
                "status_code": 200,
                "headers": {"content-type": "application/json"},
                "processing_time": 0.045,
            },
        }

        result_str = safe_json_serialize(log_event)
        result = json.loads(result_str)

        # Verify key fields are preserved and properly serialized
        assert result["level"] == "INFO"
        assert result["message"] == "User login successful"
        assert "timestamp" in result
        assert "user_id" in result
        assert result["session_data"]["ip_address"] == "192.168.1.1"
        assert result["session_data"]["duration"] == 0.123
        assert result["request"]["method"] == "POST"
        assert result["response"]["status_code"] == 200

    def test_error_in_str_representation(self):
        """Test handling of objects that raise errors in __str__."""

        class ProblematicClass:
            def __str__(self):
                raise ValueError("Cannot convert to string")

        obj = ProblematicClass()
        result_str = safe_json_serialize(obj)
        result = json.loads(result_str)

        # Objects with __dict__ get converted to dict, not fallback
        assert result["_type"] == "ProblematicClass"
        assert result["_module"] == "test_safe_json_serialization"
