"""Unit tests for ConfigurationManager.

This module tests the configuration validation and format determination
functionality extracted from LoggingContainer for better separation of concerns.
"""

import sys
from unittest.mock import patch

import pytest

from fapilog.core.managers.configuration_manager import ConfigurationManager
from fapilog.exceptions import ConfigurationError
from fapilog.settings import LoggingSettings


class TestConfigurationManager:
    """Test suite for ConfigurationManager functionality."""

    def test_validate_settings_with_none(self):
        """Test validate_settings with None input."""
        result = ConfigurationManager.validate_settings(None)
        assert isinstance(result, LoggingSettings)
        assert result.level == "INFO"  # default value

    def test_validate_settings_with_existing_instance(self):
        """Test validate_settings with existing LoggingSettings instance."""
        original = LoggingSettings(level="DEBUG", json_console="json")
        result = ConfigurationManager.validate_settings(original)

        # Should return the same instance (fast path)
        assert result is original
        assert result.level == "DEBUG"
        assert result.json_console == "json"

    def test_validate_settings_with_dict(self):
        """Test validate_settings with dictionary input."""
        settings_dict = {"level": "WARNING", "json_console": "pretty"}
        result = ConfigurationManager.validate_settings(settings_dict)

        assert isinstance(result, LoggingSettings)
        assert result.level == "WARNING"
        assert result.json_console == "pretty"

    def test_validate_settings_with_invalid_data(self):
        """Test validate_settings with invalid input."""
        with pytest.raises(ConfigurationError):
            ConfigurationManager.validate_settings({"level": "INVALID_LEVEL"})

    def test_determine_console_format_pretty(self):
        """Test determine_console_format with pretty format."""
        result = ConfigurationManager.determine_console_format("pretty")
        assert result == "pretty"

    def test_determine_console_format_json(self):
        """Test determine_console_format with json format."""
        result = ConfigurationManager.determine_console_format("json")
        assert result == "json"

    def test_determine_console_format_auto_with_tty(self):
        """Test determine_console_format with auto when TTY is available."""
        with patch.object(sys.stderr, "isatty", return_value=True):
            result = ConfigurationManager.determine_console_format("auto")
            assert result == "pretty"

    def test_determine_console_format_auto_without_tty(self):
        """Test determine_console_format with auto when TTY is not available."""
        with patch.object(sys.stderr, "isatty", return_value=False):
            result = ConfigurationManager.determine_console_format("auto")
            assert result == "json"

    def test_determine_console_format_invalid(self):
        """Test determine_console_format with invalid format."""
        with pytest.raises(ConfigurationError):
            ConfigurationManager.determine_console_format("invalid_format")

    def test_performance_fast_paths(self):
        """Test that fast paths are used for performance."""
        # Test settings validation fast path
        settings = LoggingSettings(level="DEBUG")
        result = ConfigurationManager.validate_settings(settings)
        assert result is settings  # Same instance returned

        # Test console format fast paths
        assert ConfigurationManager.determine_console_format("pretty") == "pretty"
        assert ConfigurationManager.determine_console_format("json") == "json"

    def test_stateless_design(self):
        """Test that ConfigurationManager is stateless."""
        # Multiple calls should be independent
        result1 = ConfigurationManager.validate_settings(None)
        result2 = ConfigurationManager.validate_settings(None)

        # Different instances should be created
        assert result1 is not result2
        assert result1.level == result2.level  # But same default values

    def test_thread_safety_design(self):
        """Test that ConfigurationManager operations are thread-safe by design."""
        # Since all methods are static and stateless, they should be thread-safe
        import threading
        import time

        results = []
        errors = []

        def worker():
            try:
                for _ in range(10):
                    # Mix of different operations
                    settings = ConfigurationManager.validate_settings({"level": "INFO"})
                    format_result = ConfigurationManager.determine_console_format(
                        "auto"
                    )
                    results.append((settings.level, format_result))
                    time.sleep(0.001)  # Small delay to encourage race conditions
            except Exception as e:
                errors.append(e)

        # Run multiple threads
        threads = [threading.Thread(target=worker) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Verify no errors and consistent results
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        assert len(results) == 50  # 5 threads * 10 operations each

        # All level results should be "INFO"
        for level, _ in results:
            assert level == "INFO"
