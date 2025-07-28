"""Tests for resource snapshot enricher."""

from unittest.mock import Mock, patch

from fapilog.enrichers import resource_snapshot_enricher


def test_enricher_includes_fields():
    """Test that memory_mb and cpu_percent fields are added when psutil is available."""
    # Mock psutil.Process to return predictable values
    mock_process = Mock()
    mock_process.memory_info.return_value.rss = 1024 * 1024 * 50  # 50MB
    mock_process.cpu_percent.return_value = 25.5

    with patch("fapilog.enrichers._get_process_smart", return_value=mock_process):
        # Clear the cache to ensure fresh values
        from fapilog.enrichers import _get_process_smart

        _get_process_smart.cache_clear()

        event_dict = {"event": "test_message", "level": "info"}
        enriched = resource_snapshot_enricher(None, "info", event_dict)

        # Verify fields are added
        assert "memory_mb" in enriched
        assert "cpu_percent" in enriched

        # Verify values are correct
        assert enriched["memory_mb"] == 50.0
        assert enriched["cpu_percent"] == 25.5

        # Verify original fields are preserved
        assert enriched["event"] == "test_message"
        assert enriched["level"] == "info"


def test_enricher_skipped_when_disabled():
    """Test that enricher is skipped when psutil is not available."""
    with patch("fapilog.enrichers._get_process_smart", return_value=None):
        # Clear the cache to ensure fresh values
        from fapilog.enrichers import _get_process_smart

        _get_process_smart.cache_clear()

        event_dict = {"event": "test_message", "level": "info"}
        enriched = resource_snapshot_enricher(None, "info", event_dict)

        # Verify no fields are added
        assert "memory_mb" not in enriched
        assert "cpu_percent" not in enriched

        # Verify original fields are preserved
        assert enriched["event"] == "test_message"
        assert enriched["level"] == "info"


def test_fields_within_valid_range():
    """Test that memory and CPU values are within expected bounds."""
    mock_process = Mock()
    mock_process.memory_info.return_value.rss = 1024 * 1024 * 100  # 100MB
    mock_process.cpu_percent.return_value = 75.25

    with patch("fapilog.enrichers._get_process_smart", return_value=mock_process):
        # Clear the cache to ensure fresh values
        from fapilog.enrichers import _get_process_smart

        _get_process_smart.cache_clear()

        event_dict = {"event": "test_message"}
        enriched = resource_snapshot_enricher(None, "info", event_dict)

        # Verify memory_mb is a positive float
        assert isinstance(enriched["memory_mb"], float)
        assert enriched["memory_mb"] > 0
        assert enriched["memory_mb"] == 100.0

        # Verify cpu_percent is a float between 0 and 100
        assert isinstance(enriched["cpu_percent"], float)
        assert 0.0 <= enriched["cpu_percent"] <= 100.0
        assert enriched["cpu_percent"] == 75.25


def test_fields_can_be_overridden():
    """Test that memory_mb and cpu_percent fields can be overridden manually."""
    mock_process = Mock()
    mock_process.memory_info.return_value.rss = 1024 * 1024 * 50  # 50MB
    mock_process.cpu_percent.return_value = 25.5

    with patch("fapilog.enrichers._get_process_smart", return_value=mock_process):
        # Clear the cache to ensure fresh values
        from fapilog.enrichers import _get_process_smart

        _get_process_smart.cache_clear()

        # Create event dict with manual values
        event_dict = {
            "event": "test_message",
            "memory_mb": 999.99,
            "cpu_percent": 88.88,
        }

        enriched = resource_snapshot_enricher(None, "info", event_dict)

        # Verify manual values are preserved
        assert enriched["memory_mb"] == 999.99
        assert enriched["cpu_percent"] == 88.88

        # Verify original event is preserved
        assert enriched["event"] == "test_message"


def test_only_missing_fields_added():
    """Test that only missing fields are added."""
    mock_process = Mock()
    mock_process.memory_info.return_value.rss = 1024 * 1024 * 50  # 50MB
    mock_process.cpu_percent.return_value = 25.5

    with patch("fapilog.enrichers._get_process_smart", return_value=mock_process):
        # Clear the cache to ensure fresh values
        from fapilog.enrichers import _get_process_smart

        _get_process_smart.cache_clear()

        # Create event dict with only memory_mb
        event_dict = {"event": "test_message", "memory_mb": 123.45}

        enriched = resource_snapshot_enricher(None, "info", event_dict)

        # Verify memory_mb is preserved
        assert enriched["memory_mb"] == 123.45

        # Verify cpu_percent is added
        assert "cpu_percent" in enriched
        assert enriched["cpu_percent"] == 25.5

        # Test reverse case - only cpu_percent present
        event_dict = {"event": "test_message", "cpu_percent": 67.89}

        enriched = resource_snapshot_enricher(None, "info", event_dict)

        # Verify cpu_percent is preserved
        assert enriched["cpu_percent"] == 67.89

        # Verify memory_mb is added
        assert "memory_mb" in enriched
        assert enriched["memory_mb"] == 50.0


def test_none_values_handling():
    """Test that None values are handled correctly."""
    mock_process = Mock()
    mock_process.memory_info.return_value.rss = 1024 * 1024 * 75  # 75MB
    mock_process.cpu_percent.return_value = 45.5

    with patch("fapilog.enrichers._get_process_smart", return_value=mock_process):
        # Clear the cache to ensure fresh values
        from fapilog.enrichers import _get_process_smart

        _get_process_smart.cache_clear()

        event_dict = {"event": "test_message", "memory_mb": None, "cpu_percent": None}
        enriched = resource_snapshot_enricher(None, "info", event_dict)

        # None values should be replaced with actual values
        assert enriched["memory_mb"] == 75.0
        assert enriched["cpu_percent"] == 45.5


def test_process_errors_handled():
    """Test that process errors are handled gracefully."""
    mock_process = Mock()
    mock_process.memory_info.side_effect = OSError("Process not found")
    mock_process.cpu_percent.return_value = 25.5

    with patch("fapilog.enrichers._get_process_smart", return_value=mock_process):
        # Clear the cache to ensure fresh values
        from fapilog.enrichers import _get_process_smart

        _get_process_smart.cache_clear()

        event_dict = {"event": "test_message"}
        enriched = resource_snapshot_enricher(None, "info", event_dict)

        # Should not crash, and should not add any fields due to error
        assert "memory_mb" not in enriched
        assert "cpu_percent" not in enriched

        # Test with cpu_percent error
        mock_process.memory_info.return_value.rss = 1024 * 1024 * 50
        mock_process.cpu_percent.side_effect = AttributeError("No CPU info")

        event_dict = {"event": "test_message"}
        enriched = resource_snapshot_enricher(None, "info", event_dict)

        # Should not add any fields due to error
        assert "memory_mb" not in enriched
        assert "cpu_percent" not in enriched


def test_cached_process_object():
    """Test that the process object is cached for performance."""
    mock_process = Mock()
    mock_process.memory_info.return_value.rss = 1024 * 1024 * 50
    mock_process.cpu_percent.return_value = 25.5

    with patch("fapilog.enrichers._get_process_smart", return_value=mock_process):
        # Clear the cache to ensure fresh values
        from fapilog.enrichers import _get_process_smart

        _get_process_smart.cache_clear()

        # Apply enricher multiple times
        event_dict1 = {"event": "test1"}
        event_dict2 = {"event": "test2"}

        enriched1 = resource_snapshot_enricher(None, "info", event_dict1)
        enriched2 = resource_snapshot_enricher(None, "info", event_dict2)

        # Verify values are consistent (cached process object)
        assert enriched1["memory_mb"] == enriched2["memory_mb"]
        assert enriched1["cpu_percent"] == enriched2["cpu_percent"]


def test_logger_and_method_parameters():
    """Test that logger and method_name parameters are accepted but not used."""
    mock_process = Mock()
    mock_process.memory_info.return_value.rss = 1024 * 1024 * 50
    mock_process.cpu_percent.return_value = 25.5

    with patch("fapilog.enrichers._get_process_smart", return_value=mock_process):
        # Clear the cache to ensure fresh values
        from fapilog.enrichers import _get_process_smart

        _get_process_smart.cache_clear()

        # Create a mock logger
        mock_logger = object()

        event_dict = {"event": "test_message"}
        enriched = resource_snapshot_enricher(mock_logger, "debug", event_dict)

        # Verify enricher still works correctly
        assert "memory_mb" in enriched
        assert "cpu_percent" in enriched
        assert enriched["event"] == "test_message"


def test_empty_event_dict():
    """Test behavior with empty event dict."""
    mock_process = Mock()
    mock_process.memory_info.return_value.rss = 1024 * 1024 * 50
    mock_process.cpu_percent.return_value = 25.5

    with patch("fapilog.enrichers._get_process_smart", return_value=mock_process):
        # Clear the cache to ensure fresh values
        from fapilog.enrichers import _get_process_smart

        _get_process_smart.cache_clear()

        event_dict = {}
        enriched = resource_snapshot_enricher(None, "info", event_dict)

        assert "memory_mb" in enriched
        assert "cpu_percent" in enriched
        assert enriched["memory_mb"] == 50.0
        assert enriched["cpu_percent"] == 25.5


def test_psutil_import_error():
    """Test behavior when psutil is not available."""
    # Mock _get_process_smart to return None (simulating psutil import failure)
    with patch("fapilog.enrichers._get_process_smart", return_value=None):
        # Clear the cache to ensure fresh values
        from fapilog.enrichers import _get_process_smart

        _get_process_smart.cache_clear()

        event_dict = {"event": "test_message"}
        enriched = resource_snapshot_enricher(None, "info", event_dict)

        # Should not crash and should not add fields
        assert "memory_mb" not in enriched
        assert "cpu_percent" not in enriched
        assert enriched["event"] == "test_message"
