"""Simple tests for httpx functionality - easy coverage wins."""

from unittest.mock import MagicMock, patch

import pytest

from fapilog.exceptions import ConfigurationError
from fapilog.httpx_patch import (
    HttpxTracePropagation,
    configure_httpx_trace_propagation,
    disable_httpx_trace_propagation,
    enable_httpx_trace_propagation,
    is_httpx_trace_propagation_enabled,
)
from fapilog.settings import LoggingSettings


class TestHttpxTracePropagationBasics:
    """Test basic HttpxTracePropagation functionality."""

    def test_initialization(self):
        """Test HttpxTracePropagation initialization."""
        propagation = HttpxTracePropagation()

        assert not propagation.is_enabled()
        assert propagation._patching_enabled is False
        assert propagation._original_request_method is None
        assert propagation._trace_header_name == "X-Request-ID"

    def test_is_enabled_when_disabled(self):
        """Test is_enabled() returns False when disabled."""
        propagation = HttpxTracePropagation()
        assert not propagation.is_enabled()

    def test_cleanup_when_not_enabled(self):
        """Test cleanup() when not enabled - should not error."""
        propagation = HttpxTracePropagation()

        # Should not raise exception
        propagation.cleanup()

    def test_configure_with_disabled_setting(self):
        """Test configure() with disabled trace propagation."""
        propagation = HttpxTracePropagation()
        settings = LoggingSettings(enable_httpx_trace_propagation=False)

        # Should not enable propagation
        propagation.configure(settings)
        assert not propagation.is_enabled()

    def test_configure_calls_enable_when_requested(self):
        """Test configure() calls enable when propagation is requested."""
        with patch("fapilog.httpx_patch.httpx") as mock_httpx:
            # Mock httpx as available
            mock_httpx.AsyncClient = MagicMock()

            propagation = HttpxTracePropagation()
            settings = LoggingSettings(
                enable_httpx_trace_propagation=True,
                trace_id_header="X-Custom-Trace",
            )

            # Mock the enable method to avoid actual patching
            with patch.object(propagation, "enable") as mock_enable:
                propagation.configure(settings)

                mock_enable.assert_called_once_with("X-Custom-Trace")


class TestGlobalFunctions:
    """Test global wrapper functions."""

    def test_global_enable_calls_instance_method(self):
        """Test global enable_httpx_trace_propagation function."""
        with patch("fapilog.httpx_patch._global_propagation") as mock_global:
            enable_httpx_trace_propagation("X-Test-Header")
            mock_global.enable.assert_called_once_with("X-Test-Header")

    def test_global_disable_calls_instance_method(self):
        """Test global disable_httpx_trace_propagation function."""
        with patch("fapilog.httpx_patch._global_propagation") as mock_global:
            disable_httpx_trace_propagation()
            mock_global.disable.assert_called_once()

    def test_global_is_enabled_calls_instance_method(self):
        """Test global is_httpx_trace_propagation_enabled function."""
        with patch("fapilog.httpx_patch._global_propagation") as mock_global:
            mock_global.is_enabled.return_value = True

            result = is_httpx_trace_propagation_enabled()

            assert result is True
            mock_global.is_enabled.assert_called_once()

    def test_global_configure_calls_instance_method(self):
        """Test global configure_httpx_trace_propagation function."""
        settings = LoggingSettings()

        with patch("fapilog.httpx_patch._global_propagation") as mock_global:
            configure_httpx_trace_propagation(settings)
            mock_global.configure.assert_called_once_with(settings)


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_enable_without_httpx_raises_configuration_error(self):
        """Test enable() raises ConfigurationError when httpx not available."""
        with patch("fapilog.httpx_patch.httpx", None):
            propagation = HttpxTracePropagation()

            with pytest.raises(ConfigurationError) as exc_info:
                propagation.enable()

            assert "httpx is required for trace propagation" in str(exc_info.value)

    def test_disable_when_not_enabled_raises_error(self):
        """Test disable() raises error when not enabled."""
        propagation = HttpxTracePropagation()

        with pytest.raises(ConfigurationError) as exc_info:
            propagation.disable()

        assert "httpx trace propagation is not currently enabled" in str(exc_info.value)


class TestHttpxAvailableScenarios:
    """Test scenarios when httpx is available."""

    @pytest.fixture
    def mock_httpx(self):
        """Mock httpx as available."""
        with patch("fapilog.httpx_patch.httpx") as mock_httpx:
            mock_httpx.AsyncClient = MagicMock()
            mock_httpx.AsyncClient.request = MagicMock()
            yield mock_httpx

    def test_enable_with_custom_header_name(self, mock_httpx):
        """Test enable() with custom header name."""
        propagation = HttpxTracePropagation()

        propagation.enable("X-Custom-Trace-ID")

        assert propagation.is_enabled()
        assert propagation._trace_header_name == "X-Custom-Trace-ID"

        # Clean up
        propagation.disable()

    def test_enable_already_enabled_raises_error(self, mock_httpx):
        """Test enable() when already enabled raises error."""
        propagation = HttpxTracePropagation()
        propagation.enable()

        with pytest.raises(ConfigurationError) as exc_info:
            propagation.enable()

        assert "httpx trace propagation is already enabled" in str(exc_info.value)

        # Clean up
        propagation.disable()

    def test_cleanup_calls_disable(self, mock_httpx):
        """Test cleanup() calls disable() when enabled."""
        propagation = HttpxTracePropagation()
        propagation.enable()

        assert propagation.is_enabled()

        propagation.cleanup()

        assert not propagation.is_enabled()

    def test_disable_restores_original_method(self, mock_httpx):
        """Test disable() restores original request method."""
        propagation = HttpxTracePropagation()
        original_method = mock_httpx.AsyncClient.request

        propagation.enable()
        assert propagation._original_request_method is not None

        propagation.disable()

        # Should restore original method
        assert mock_httpx.AsyncClient.request == original_method
        assert propagation._original_request_method is None


if __name__ == "__main__":
    pytest.main([__file__])
