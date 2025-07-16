"""Tests for hostname and process info enricher."""

import os
import socket
from unittest.mock import patch

from fapilog.enrichers import host_process_enricher


def test_hostname_pid_present():
    """Test that hostname and pid are present in logs."""
    # Create a mock event dict
    event_dict = {"event": "test_message", "level": "info"}

    # Apply the enricher
    enriched = host_process_enricher(None, "info", event_dict)

    # Verify hostname and pid are added
    assert "hostname" in enriched
    assert "pid" in enriched

    # Verify values match system calls
    assert enriched["hostname"] == socket.gethostname()
    assert enriched["pid"] == os.getpid()

    # Verify original fields are preserved
    assert enriched["event"] == "test_message"
    assert enriched["level"] == "info"


def test_fields_can_be_overridden():
    """Test that hostname and pid fields can be overridden manually."""
    # Create event dict with manual values
    event_dict = {"event": "test_message", "hostname": "custom-host", "pid": 99999}

    # Apply the enricher
    enriched = host_process_enricher(None, "info", event_dict)

    # Verify manual values are preserved
    assert enriched["hostname"] == "custom-host"
    assert enriched["pid"] == 99999

    # Verify original event is preserved
    assert enriched["event"] == "test_message"


def test_only_missing_fields_added():
    """Test that only missing fields are added."""
    # Create event dict with only hostname
    event_dict = {"event": "test_message", "hostname": "custom-host"}

    # Apply the enricher
    enriched = host_process_enricher(None, "info", event_dict)

    # Verify hostname is preserved
    assert enriched["hostname"] == "custom-host"

    # Verify pid is added
    assert "pid" in enriched
    assert enriched["pid"] == os.getpid()

    # Test reverse case - only pid present
    event_dict = {"event": "test_message", "pid": 88888}

    enriched = host_process_enricher(None, "info", event_dict)

    # Verify pid is preserved
    assert enriched["pid"] == 88888

    # Verify hostname is added
    assert "hostname" in enriched
    assert enriched["hostname"] == socket.gethostname()


def test_cached_values():
    """Test that values are cached for performance."""
    # Apply enricher multiple times
    event_dict1 = {"event": "test1"}
    event_dict2 = {"event": "test2"}

    enriched1 = host_process_enricher(None, "info", event_dict1)
    enriched2 = host_process_enricher(None, "info", event_dict2)

    # Verify values are consistent (cached)
    assert enriched1["hostname"] == enriched2["hostname"]
    assert enriched1["pid"] == enriched2["pid"]


def test_with_mock_system_calls():
    """Test with mocked system calls to verify behavior."""
    with patch("socket.gethostname", return_value="test-hostname"), patch(
        "os.getpid", return_value=12345
    ):
        # Clear the lru_cache after applying the mock
        from fapilog.enrichers import _get_hostname, _get_pid

        _get_hostname.cache_clear()
        _get_pid.cache_clear()

        event_dict = {"event": "test_message"}
        enriched = host_process_enricher(None, "info", event_dict)

        assert enriched["hostname"] == "test-hostname"
        assert enriched["pid"] == 12345


def test_empty_event_dict():
    """Test behavior with empty event dict."""
    from fapilog.enrichers import _get_hostname, _get_pid

    _get_hostname.cache_clear()
    _get_pid.cache_clear()
    event_dict = {}
    enriched = host_process_enricher(None, "info", event_dict)

    assert "hostname" in enriched
    assert "pid" in enriched
    assert enriched["hostname"] == socket.gethostname()
    assert enriched["pid"] == os.getpid()


def test_logger_and_method_parameters():
    """Test that logger and method_name parameters are accepted but not used."""
    # Create a mock logger
    mock_logger = object()

    event_dict = {"event": "test_message"}
    enriched = host_process_enricher(mock_logger, "debug", event_dict)

    # Verify enricher still works correctly
    assert "hostname" in enriched
    assert "pid" in enriched
    assert enriched["event"] == "test_message"


def test_none_values_handling():
    """Test that None values are handled correctly."""
    from fapilog.enrichers import _get_hostname, _get_pid

    _get_hostname.cache_clear()
    _get_pid.cache_clear()
    event_dict = {"event": "test_message", "hostname": None, "pid": None}
    enriched = host_process_enricher(None, "info", event_dict)
    # None values should be replaced with actual values
    assert enriched["hostname"] == socket.gethostname()
    assert enriched["pid"] == os.getpid()


def test_non_string_hostname():
    """Test behavior when hostname is not a string."""
    event_dict = {
        "event": "test_message",
        "hostname": 123,  # Non-string value
        "pid": 456,
    }

    enriched = host_process_enricher(None, "info", event_dict)

    # Non-string hostname should be preserved
    assert enriched["hostname"] == 123
    # pid should be preserved since it's already present
    assert enriched["pid"] == 456
