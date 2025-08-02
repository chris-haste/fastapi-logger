"""Final win tests for bootstrap.py to reach 90% coverage."""

from unittest.mock import patch

import pytest

from fapilog._internal.configuration_manager import ConfigurationManager


class TestBootstrapFinalWin:
    """Test the final 3 missing lines in bootstrap.py."""

    def test_determine_console_format_auto_with_tty(self):
        """Test _determine_console_format with auto when stderr is a tty."""
        # Mock sys.stderr.isatty() to return True (lines 92-93)
        with patch("sys.stderr.isatty", return_value=True):
            result = ConfigurationManager.determine_console_format("auto")
            assert result == "pretty"

    def test_determine_console_format_auto_without_tty(self):
        """Test _determine_console_format with auto when stderr is not a tty."""
        # Mock sys.stderr.isatty() to return False (lines 92-93)
        with patch("sys.stderr.isatty", return_value=False):
            result = ConfigurationManager.determine_console_format("auto")
            assert result == "json"

    def test_determine_console_format_explicit_format(self):
        """Test _determine_console_format with explicit format (line 94)."""
        # Should return the format as-is without checking isatty
        result = ConfigurationManager.determine_console_format("pretty")
        assert result == "pretty"

        result = ConfigurationManager.determine_console_format("json")
        assert result == "json"


if __name__ == "__main__":
    pytest.main([__file__])
