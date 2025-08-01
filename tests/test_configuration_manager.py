"""Tests for ConfigurationManager class."""

import sys
from unittest.mock import patch

import pytest

from fapilog._internal.configuration_manager import ConfigurationManager
from fapilog.exceptions import ConfigurationError
from fapilog.settings import LoggingSettings


class TestConfigurationManager:
    """Test suite for ConfigurationManager class."""

    def test_validate_settings_with_none(self):
        """Test that None settings returns default LoggingSettings."""
        result = ConfigurationManager.validate_settings(None)
        assert isinstance(result, LoggingSettings)
        assert result.level == "INFO"  # Default value

    def test_validate_settings_with_existing_instance(self):
        """Test that existing LoggingSettings instance is returned directly."""
        original_settings = LoggingSettings(level="DEBUG")
        result = ConfigurationManager.validate_settings(original_settings)
        assert result is original_settings
        assert result.level == "DEBUG"

    def test_validate_settings_with_dict(self):
        """Test validation with dictionary input."""
        settings_dict = {"level": "WARNING", "json_console": "json"}
        result = ConfigurationManager.validate_settings(settings_dict)
        assert isinstance(result, LoggingSettings)
        assert result.level == "WARNING"
        assert result.json_console == "json"

    def test_validate_settings_with_invalid_data(self):
        """Test that invalid settings data raises ConfigurationError."""
        invalid_settings = {"level": "INVALID_LEVEL"}
        with pytest.raises(ConfigurationError):
            ConfigurationManager.validate_settings(invalid_settings)

    def test_validate_settings_thread_safety(self):
        """Test that validate_settings is thread-safe (stateless)."""
        import threading

        results = []
        errors = []

        def worker(level):
            try:
                settings = {"level": level}
                result = ConfigurationManager.validate_settings(settings)
                results.append((level, result.level))
            except Exception as e:
                errors.append(e)

        threads = []
        levels = ["DEBUG", "INFO", "WARNING", "ERROR"]

        for level in levels:
            thread = threading.Thread(target=worker, args=(level,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        assert not errors, f"Thread safety test failed with errors: {errors}"
        assert len(results) == 4
        for level, result_level in results:
            assert level == result_level

    def test_determine_console_format_auto_with_tty(self):
        """Test auto format determination when stderr is a TTY."""
        with patch.object(sys.stderr, "isatty", return_value=True):
            result = ConfigurationManager.determine_console_format("auto")
            assert result == "pretty"

    def test_determine_console_format_auto_without_tty(self):
        """Test auto format determination when stderr is not a TTY."""
        with patch.object(sys.stderr, "isatty", return_value=False):
            result = ConfigurationManager.determine_console_format("auto")
            assert result == "json"

    def test_determine_console_format_explicit_pretty(self):
        """Test explicit pretty format specification."""
        result = ConfigurationManager.determine_console_format("pretty")
        assert result == "pretty"

    def test_determine_console_format_explicit_json(self):
        """Test explicit json format specification."""
        result = ConfigurationManager.determine_console_format("json")
        assert result == "json"

    def test_determine_console_format_invalid_format(self):
        """Test that invalid console format raises ConfigurationError."""
        with pytest.raises(ConfigurationError):
            ConfigurationManager.determine_console_format("invalid")

    def test_determine_console_format_case_sensitivity(self):
        """Test that console format is case sensitive."""
        with pytest.raises(ConfigurationError):
            ConfigurationManager.determine_console_format("JSON")

        with pytest.raises(ConfigurationError):
            ConfigurationManager.determine_console_format("Pretty")

    def test_determine_console_format_thread_safety(self):
        """Test that determine_console_format is thread-safe."""
        import threading

        results = []
        errors = []

        def worker(format_type):
            try:
                result = ConfigurationManager.determine_console_format(format_type)
                results.append((format_type, result))
            except Exception as e:
                errors.append(e)

        threads = []
        formats = ["pretty", "json", "pretty", "json"]

        for format_type in formats:
            thread = threading.Thread(target=worker, args=(format_type,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        assert not errors, f"Thread safety test failed with errors: {errors}"
        assert len(results) == 4
        for format_type, result in results:
            assert format_type == result

    def test_configuration_manager_stateless(self):
        """Test that ConfigurationManager is truly stateless."""
        # Create multiple "instances" (though it's all static methods)
        manager1 = ConfigurationManager()
        manager2 = ConfigurationManager()

        # Verify they have no state
        assert not hasattr(manager1, "__dict__") or not manager1.__dict__
        assert not hasattr(manager2, "__dict__") or not manager2.__dict__

        # Verify static methods work the same way
        settings1 = LoggingSettings(level="DEBUG")
        settings2 = LoggingSettings(level="INFO")

        result1 = manager1.validate_settings(settings1)
        result2 = manager2.validate_settings(settings2)

        assert result1.level == "DEBUG"
        assert result2.level == "INFO"

    def test_error_handling_preserves_context(self):
        """Test that error handling preserves original exception context."""
        with pytest.raises(ConfigurationError) as exc_info:
            ConfigurationManager.validate_settings({"level": 123})  # Invalid type

        # Check that the error has proper context
        error = exc_info.value
        assert "settings" in str(error)
        assert hasattr(error, "__cause__")

    def test_integration_with_logging_settings_validation(self):
        """Test integration with LoggingSettings validation rules."""
        # Test various LoggingSettings validation scenarios
        test_cases = [
            {"level": "DEBUG", "json_console": "auto"},
            {"level": "INFO", "json_console": "pretty"},
            {"level": "WARNING", "json_console": "json"},
            {"level": "ERROR", "sampling_rate": 0.5},
            {"level": "CRITICAL", "enable_resource_metrics": True},
        ]

        for case in test_cases:
            result = ConfigurationManager.validate_settings(case)
            assert isinstance(result, LoggingSettings)
            # Type hint for mypy - case is a dict
            case_dict: dict = case
            for key, value in case_dict.items():
                assert getattr(result, key) == value

    def test_console_format_edge_cases(self):
        """Test console format determination edge cases."""
        # Test empty string
        with pytest.raises(ConfigurationError):
            ConfigurationManager.determine_console_format("")

        # Test whitespace
        with pytest.raises(ConfigurationError):
            ConfigurationManager.determine_console_format(" ")

        # Test None (this should fail at runtime due to type hints)
        with pytest.raises((ConfigurationError, TypeError)):
            ConfigurationManager.determine_console_format(None)

    def test_memory_efficiency(self):
        """Test that ConfigurationManager operations are memory efficient."""
        import gc

        # Force garbage collection before test
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Perform multiple operations
        for _ in range(100):
            ConfigurationManager.validate_settings({"level": "INFO"})
            ConfigurationManager.determine_console_format("auto")

        # Force garbage collection after operations
        gc.collect()
        final_objects = len(gc.get_objects())

        # Should not have significant memory growth (allow some tolerance)
        object_growth = final_objects - initial_objects
        assert object_growth < 50, f"Memory growth too high: {object_growth} objects"
