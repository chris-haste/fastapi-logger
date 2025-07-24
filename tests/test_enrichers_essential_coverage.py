"""Essential tests to cover missing lines in src/fapilog/enrichers.py."""

import sys
from unittest.mock import patch

import pytest

from fapilog.enrichers import _get_process, register_enricher


class TestEssentialEnricherCoverage:
    """Simple tests to cover the essential missing lines."""

    def test_get_process_import_error(self):
        """Test _get_process() when psutil import fails."""
        # Clear cache first
        _get_process.cache_clear()

        # Mock psutil module to not exist
        with patch.dict(sys.modules, {"psutil": None}):
            with patch("builtins.__import__", side_effect=ImportError()):
                result = _get_process()
                assert result is None

    def test_register_enricher_legacy_error(self):
        """Test legacy register_enricher function raises helpful error."""
        with pytest.raises(AttributeError) as exc_info:
            register_enricher(lambda x: x)

        error_msg = str(exc_info.value)
        assert "register_enricher() has been removed" in error_msg
        assert "use @register_enricher_advanced() decorator instead" in error_msg
        assert "Example migration:" in error_msg
