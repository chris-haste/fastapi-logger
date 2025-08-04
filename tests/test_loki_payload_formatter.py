"""Tests for LokiPayloadFormatter."""

import datetime
from unittest.mock import patch

import pytest

from fapilog.exceptions import SinkWriteError
from fapilog.integrations.loki.formatter import LokiPayloadFormatter


class TestLokiPayloadFormatter:
    """Test LokiPayloadFormatter class."""

    def test_init_with_labels(self):
        """Test initialization with labels."""
        labels = {"service": "test", "env": "dev"}
        formatter = LokiPayloadFormatter(labels)
        assert formatter.labels == labels

    def test_init_with_none_labels(self):
        """Test initialization with None labels (line 20)."""
        formatter = LokiPayloadFormatter(None)
        assert formatter.labels == {}

    def test_init_with_empty_labels(self):
        """Test initialization with empty labels."""
        formatter = LokiPayloadFormatter({})
        assert formatter.labels == {}

    def test_format_batch_simple(self):
        """Test format_batch with simple events."""
        formatter = LokiPayloadFormatter({"service": "test"})
        events = [
            {"message": "test1", "timestamp": 1234567890.123},
            {"message": "test2", "timestamp": 1234567891.456},
        ]

        result = formatter.format_batch(events)

        assert "streams" in result
        assert len(result["streams"]) == 1
        stream = result["streams"][0]
        assert stream["stream"] == {"service": "test"}
        assert len(stream["values"]) == 2
        assert (
            stream["values"][0][1] == '{"message":"test1","timestamp":1234567890.123}'
        )
        assert (
            stream["values"][1][1] == '{"message":"test2","timestamp":1234567891.456}'
        )

    def test_format_batch_no_timestamp(self):
        """Test format_batch with events without timestamp."""
        formatter = LokiPayloadFormatter()
        events = [{"message": "test"}]

        with patch("time.time", return_value=1234567890.123):
            result = formatter.format_batch(events)

        assert len(result["streams"][0]["values"]) == 1
        # Should use current time when timestamp is missing
        timestamp_ns = int(1234567890.123 * 1_000_000_000)
        assert result["streams"][0]["values"][0][0] == str(timestamp_ns)

    def test_format_batch_event_formatting_error(self):
        """Test format_batch with individual event formatting error."""
        formatter = LokiPayloadFormatter({"service": "test"})

        # Mock safe_json_serialize to always raise an exception
        with patch(
            "fapilog.integrations.loki.formatter.safe_json_serialize"
        ) as mock_serialize:
            mock_serialize.side_effect = Exception("Serialization failed")
            events = [{"message": "test", "timestamp": 1234567890.123}]

            with pytest.raises(SinkWriteError) as exc_info:
                formatter.format_batch(events)

            assert "loki" in str(exc_info.value)
            assert exc_info.value.sink_name == "loki"

    def test_format_batch_overall_error(self):
        """Test format_batch with overall formatting error."""
        formatter = LokiPayloadFormatter({"service": "test"})

        # Mock safe_json_serialize to raise an exception
        with patch(
            "fapilog.integrations.loki.formatter.safe_json_serialize"
        ) as mock_serialize:
            mock_serialize.side_effect = Exception("Serialization failed")
            events = [{"message": "test", "timestamp": 1234567890.123}]

            with pytest.raises(SinkWriteError) as exc_info:
                formatter.format_batch(events)

            assert "loki" in str(exc_info.value)
            assert exc_info.value.sink_name == "loki"

    def test_convert_timestamp_to_nanoseconds_string_iso(self):
        """Test _convert_timestamp_to_nanoseconds with ISO string."""
        formatter = LokiPayloadFormatter()

        # Test ISO timestamp string
        timestamp_str = "2023-01-01T12:00:00Z"
        result = formatter._convert_timestamp_to_nanoseconds(timestamp_str)

        # Verify it's a nanosecond timestamp
        assert isinstance(result, int)
        assert result > 1000000000000000000  # Should be in nanoseconds

    def test_convert_timestamp_to_nanoseconds_string_iso_with_offset(self):
        """Test _convert_timestamp_to_nanoseconds with ISO string with offset."""
        formatter = LokiPayloadFormatter()

        # Test ISO timestamp string with timezone offset
        timestamp_str = "2023-01-01T12:00:00+05:00"
        result = formatter._convert_timestamp_to_nanoseconds(timestamp_str)

        assert isinstance(result, int)
        assert result > 1000000000000000000

    def test_convert_timestamp_to_nanoseconds_datetime(self):
        """Test _convert_timestamp_to_nanoseconds with datetime object."""
        formatter = LokiPayloadFormatter()

        # Test datetime object
        dt = datetime.datetime(2023, 1, 1, 12, 0, 0)
        result = formatter._convert_timestamp_to_nanoseconds(dt)

        assert isinstance(result, int)
        expected = int(dt.timestamp() * 1_000_000_000)
        assert result == expected

    def test_convert_timestamp_to_nanoseconds_float(self):
        """Test _convert_timestamp_to_nanoseconds with float timestamp."""
        formatter = LokiPayloadFormatter()

        # Test float timestamp
        timestamp = 1234567890.123
        result = formatter._convert_timestamp_to_nanoseconds(timestamp)

        assert isinstance(result, int)
        expected = int(timestamp * 1_000_000_000)
        assert result == expected

    def test_convert_timestamp_to_nanoseconds_int(self):
        """Test _convert_timestamp_to_nanoseconds with int timestamp."""
        formatter = LokiPayloadFormatter()

        # Test int timestamp
        timestamp = 1234567890
        result = formatter._convert_timestamp_to_nanoseconds(timestamp)

        assert isinstance(result, int)
        expected = int(timestamp * 1_000_000_000)
        assert result == expected

    def test_convert_timestamp_to_nanoseconds_invalid_string(self):
        """Test _convert_timestamp_to_nanoseconds with invalid string."""
        formatter = LokiPayloadFormatter()

        with pytest.raises(ValueError) as exc_info:
            formatter._convert_timestamp_to_nanoseconds("invalid-timestamp")

        assert "Unsupported timestamp format" in str(exc_info.value)

    def test_convert_timestamp_to_nanoseconds_invalid_type(self):
        """Test _convert_timestamp_to_nanoseconds with invalid type."""
        formatter = LokiPayloadFormatter()

        with pytest.raises(ValueError) as exc_info:
            formatter._convert_timestamp_to_nanoseconds(["invalid", "type"])

        assert "Unsupported timestamp format" in str(exc_info.value)

    def test_update_labels(self):
        """Test update_labels method (line 107)."""
        formatter = LokiPayloadFormatter({"old": "value"})

        new_labels = {"service": "test", "env": "prod"}
        formatter.update_labels(new_labels)

        assert formatter.labels == new_labels

    def test_update_labels_with_none(self):
        """Test update_labels with None."""
        formatter = LokiPayloadFormatter({"old": "value"})

        formatter.update_labels(None)

        assert formatter.labels == {}

    def test_add_label(self):
        """Test add_label method (line 116)."""
        formatter = LokiPayloadFormatter({"existing": "value"})

        formatter.add_label("new", "label")

        assert formatter.labels["new"] == "label"
        assert formatter.labels["existing"] == "value"

    def test_add_label_overwrite(self):
        """Test add_label method overwrites existing label."""
        formatter = LokiPayloadFormatter({"existing": "old_value"})

        formatter.add_label("existing", "new_value")

        assert formatter.labels["existing"] == "new_value"

    def test_remove_label_existing(self):
        """Test remove_label method with existing label (line 124)."""
        formatter = LokiPayloadFormatter({"remove_me": "value", "keep_me": "value"})

        formatter.remove_label("remove_me")

        assert "remove_me" not in formatter.labels
        assert formatter.labels["keep_me"] == "value"

    def test_remove_label_nonexistent(self):
        """Test remove_label method with non-existent label."""
        formatter = LokiPayloadFormatter({"keep_me": "value"})

        # Should not raise an exception
        formatter.remove_label("non_existent")

        assert formatter.labels == {"keep_me": "value"}

    def test_format_batch_with_complex_events(self):
        """Test format_batch with complex nested event data."""
        formatter = LokiPayloadFormatter({"service": "test"})
        events = [
            {
                "message": "Complex event",
                "timestamp": 1234567890.123,
                "metadata": {
                    "user_id": 123,
                    "request_id": "abc-123",
                    "nested": {"data": [1, 2, 3]},
                },
                "level": "INFO",
            }
        ]

        result = formatter.format_batch(events)

        assert len(result["streams"][0]["values"]) == 1
        log_line = result["streams"][0]["values"][0][1]
        # Verify the JSON contains all the nested data (compact format)
        assert '"user_id":123' in log_line
        assert '"request_id":"abc-123"' in log_line
        assert '"data":[1,2,3]' in log_line
