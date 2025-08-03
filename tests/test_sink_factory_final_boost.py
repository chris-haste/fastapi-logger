"""Final boost for sink_factory.py coverage - targeting lines 41-42."""

from unittest.mock import patch

import pytest

from fapilog.core.factories.sink_factory import (
    SinkConfigurationError,
    create_custom_sink_from_uri,
)


class TestSinkFactoryFinalBoost:
    """Tests to cover the remaining lines in sink_factory.py."""

    def test_create_custom_sink_urlparse_exception(self):
        """Test exception handling when urlparse fails.

        This covers lines 41-42 in sink_factory.py where urlparse
        raises an exception.
        """
        # Mock urlparse to raise an exception
        with patch(
            "fapilog._internal.sink_factory.urllib.parse.urlparse"
        ) as mock_urlparse:
            mock_urlparse.side_effect = ValueError("Parsing failed")

            with pytest.raises(
                SinkConfigurationError, match="Invalid URI format: Parsing failed"
            ):
                create_custom_sink_from_uri("invalid-uri")
