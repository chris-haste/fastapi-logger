import json
import logging
from io import StringIO

import pytest
import structlog

from fapilog.pipeline import build_processor_chain
from fapilog.settings import LoggingSettings


def test_json_pipeline_keys(capsys):
    settings = LoggingSettings(json_console="json", queue_enabled=False)
    processors = build_processor_chain(settings, pretty=False)
    structlog.configure(
        processors=processors,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logger = structlog.get_logger()
    logger.info("test_event", foo="bar")
    captured = capsys.readouterr()
    log_line = captured.out.strip()
    log_data = json.loads(log_line)
    assert "event" in log_data
    assert "timestamp" in log_data
    assert "level" in log_data
    assert "foo" in log_data
    assert log_data["event"] == "test_event"
    assert log_data["foo"] == "bar"


def test_pretty_pipeline_format(monkeypatch, capsys):
    settings = LoggingSettings(json_console="pretty", queue_enabled=False)
    processors = build_processor_chain(settings, pretty=True)
    structlog.configure(
        processors=processors,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logger = structlog.get_logger()
    logger.info("pretty_event", foo="bar")
    captured = capsys.readouterr()
    log_line = captured.out.strip()
    # Should not be valid JSON
    with pytest.raises(json.JSONDecodeError):
        json.loads(log_line)
    # Should contain ANSI color codes (\x1b)
    assert "\x1b[" in log_line


def test_sampling_processor():
    settings = LoggingSettings(sampling_rate=0.1, queue_enabled=False)
    processors = build_processor_chain(settings, pretty=False)
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setFormatter(logging.Formatter("%(message)s"))
    root_logger = logging.getLogger("sampling_test")
    root_logger.handlers = [handler]
    root_logger.setLevel(logging.INFO)
    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logger = structlog.get_logger("sampling_test")
    total = 1000
    for _ in range(total):
        logger.info("sampled_event")
    handler.flush()
    lines = [
        line
        for line in log_stream.getvalue().splitlines()
        if line.strip() and line.strip() != "null"
    ]
    kept = len(lines)
    # Should keep roughly 5-15% (statistical tolerance)
    assert 50 <= kept <= 150

    def test_processor_order():
        settings = LoggingSettings(queue_enabled=False)
        processors = build_processor_chain(settings, pretty=False)
        print([type(p) for p in processors])  # Debug print
        # Order: add_log_level, TimeStamper, format_exc_info, StackInfoRenderer,
        # EventRenamer, host_process_enricher, redact, request_response_enricher,
        # sampling, filter_none, JSONRenderer
        assert callable(processors[0])
        assert isinstance(processors[1], structlog.processors.TimeStamper)
        assert processors[2] == structlog.processors.format_exc_info
        assert isinstance(processors[3], structlog.processors.StackInfoRenderer)
        assert isinstance(processors[4], structlog.processors.EventRenamer)
        # host_process_enricher, redact, request_response_enricher, sampling, filter_none are callables (functions)
        assert callable(processors[5])
        assert callable(processors[6])
        assert callable(processors[7])
        assert callable(processors[8])
        assert callable(processors[9])
        assert isinstance(processors[10], structlog.processors.JSONRenderer)


def test_redaction_processor_no_patterns():
    """Test redaction processor with no patterns (identity function)."""
    from fapilog._internal.processors import RedactionProcessor

    # Test with empty patterns
    processor_obj = RedactionProcessor(patterns=[])

    # Should return the event_dict unchanged
    event_dict = {"key": "value", "password": "secret123"}
    result = processor_obj.process(None, "info", event_dict)
    assert result == event_dict


@pytest.mark.asyncio
async def test_redaction_processor_with_patterns():
    """Test redaction processor with patterns."""
    from fapilog._internal.processors import RedactionProcessor

    # Test with patterns
    processor_obj = RedactionProcessor(patterns=["password", "secret"])
    await processor_obj.start()  # Initialize pattern engine

    # Test redaction of string values
    event_dict = {
        "user": "john",
        "password": "secret123",
        "token": "abc123",
        "message": "contains secret info",
    }
    result = processor_obj.process(None, "info", event_dict)

    # Check that sensitive values are redacted
    assert result["user"] == "john"  # Should not be redacted
    assert result["password"] == "[REDACTED]"  # Should be redacted
    assert result["token"] == "abc123"  # No pattern match
    # Contains "secret"
    assert result["message"] == "[REDACTED]"


@pytest.mark.asyncio
async def test_redaction_processor_nested_dict():
    """Test redaction processor with nested dictionaries."""
    from fapilog._internal.processors import RedactionProcessor

    processor_obj = RedactionProcessor(patterns=["password", "secret"])
    await processor_obj.start()  # Initialize pattern engine

    event_dict = {
        "user": "john",
        "credentials": {"password": "secret123", "username": "john"},
        "message": "contains secret info",
    }
    result = processor_obj.process(None, "info", event_dict)

    # Check that nested sensitive values are redacted
    assert result["user"] == "john"
    assert result["credentials"]["password"] == "[REDACTED]"
    assert result["credentials"]["username"] == "john"
    assert result["message"] == "[REDACTED]"


def test_sampling_processor_full_rate():
    """Test sampling processor with 100% rate (identity function)."""
    from fapilog._internal.processors import SamplingProcessor

    processor_obj = SamplingProcessor(rate=1.0)

    event_dict = {"key": "value"}
    result = processor_obj.process(None, "info", event_dict)
    assert result == event_dict


def test_filter_none_processor():
    """Test filter none processor."""
    from fapilog._internal.processors import FilterNoneProcessor

    processor_obj = FilterNoneProcessor()

    # Test with None event (should be filtered out)
    result = processor_obj.process(None, "info", None)
    assert result is None

    # Test with valid event (should pass through)
    event_dict = {"key": "value", "null_field": None, "empty": ""}
    result = processor_obj.process(None, "info", event_dict)

    # Should pass through unchanged
    assert result == event_dict
    assert result["key"] == "value"
    assert result["null_field"] is None
    assert result["empty"] == ""
