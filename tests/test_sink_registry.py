"""Tests for sink registry and custom sink functionality."""

from typing import Any, Dict

import pytest

from fapilog._internal.sink_factory import (
    SinkConfigurationError,
    _convert_parameter_value,
    _parse_uri_parameters,
    create_custom_sink_from_uri,
)
from fapilog._internal.sink_registry import SinkRegistry, register_sink
from fapilog.bootstrap import configure_logging
from fapilog.settings import LoggingSettings
from fapilog.sinks import Sink


# Test sink implementations
class MockSink(Sink):
    """Simple mock sink for registry testing."""

    def __init__(self, **kwargs):
        super().__init__()
        self.kwargs = kwargs

    async def write(self, event_dict: Dict[str, Any]) -> None:
        pass


class PostgresSink(Sink):
    """Mock PostgreSQL sink for testing."""

    def __init__(self, host="localhost", port=5432, database="logs", **kwargs):
        super().__init__()
        self.host = host
        self.port = port
        self.database = database
        self.kwargs = kwargs

    async def write(self, event_dict: Dict[str, Any]) -> None:
        pass


class TestSinkRegistry:
    """Test the SinkRegistry class."""

    def setup_method(self):
        """Clear registry before each test."""
        SinkRegistry.clear()

    def test_register_sink(self):
        """Test basic sink registration."""
        result = SinkRegistry.register("test", MockSink)
        assert result is MockSink
        assert SinkRegistry.get("test") is MockSink

    def test_register_sink_with_whitespace(self):
        """Test registration handles whitespace in names."""
        SinkRegistry.register("  test  ", MockSink)
        assert SinkRegistry.get("test") is MockSink
        assert SinkRegistry.get("  test  ") is MockSink

    def test_register_invalid_name(self):
        """Test registration with invalid names."""
        with pytest.raises(ValueError, match="Sink name cannot be empty"):
            SinkRegistry.register("", MockSink)

        with pytest.raises(ValueError, match="Sink name cannot be empty"):
            SinkRegistry.register("   ", MockSink)

    def test_register_invalid_class(self):
        """Test registration with invalid sink class."""

        class NotASink:
            pass

        with pytest.raises(ValueError, match="must inherit from Sink"):
            SinkRegistry.register("test", NotASink)

    def test_get_nonexistent_sink(self):
        """Test getting non-existent sink returns None."""
        assert SinkRegistry.get("nonexistent") is None
        assert SinkRegistry.get("") is None

    def test_list_sinks(self):
        """Test listing registered sinks."""
        SinkRegistry.register("test1", MockSink)
        SinkRegistry.register("test2", PostgresSink)

        sinks = SinkRegistry.list()
        assert len(sinks) == 2
        assert sinks["test1"] is MockSink
        assert sinks["test2"] is PostgresSink

        # Verify it returns a copy
        sinks["test3"] = MockSink
        assert "test3" not in SinkRegistry.list()

    def test_clear_registry(self):
        """Test clearing the registry."""
        SinkRegistry.register("test", MockSink)
        assert len(SinkRegistry.list()) == 1

        SinkRegistry.clear()
        assert len(SinkRegistry.list()) == 0


class TestRegisterSinkDecorator:
    """Test the @register_sink decorator."""

    def setup_method(self):
        """Clear registry before each test."""
        SinkRegistry.clear()

    def test_decorator_registration(self):
        """Test decorator registers sink correctly."""

        @register_sink("postgres")
        class DecoratedSink(Sink):
            async def write(self, event_dict: Dict[str, Any]) -> None:
                pass

        assert SinkRegistry.get("postgres") is DecoratedSink

    def test_decorator_returns_class(self):
        """Test decorator returns the original class."""

        @register_sink("test")
        class DecoratedSink(Sink):
            async def write(self, event_dict: Dict[str, Any]) -> None:
                pass

        # Should be able to instantiate normally
        instance = DecoratedSink()
        assert isinstance(instance, Sink)


class TestSinkFactory:
    """Test the sink factory functions."""

    def setup_method(self):
        """Set up test sinks in registry."""
        SinkRegistry.clear()
        SinkRegistry.register("postgres", PostgresSink)
        SinkRegistry.register("test", MockSink)

    def test_create_custom_sink_basic(self):
        """Test creating custom sink from basic URI."""
        sink = create_custom_sink_from_uri("postgres://localhost/logs")
        assert isinstance(sink, PostgresSink)
        assert sink.host == "localhost"
        assert sink.database == "logs"

    def test_create_custom_sink_with_credentials(self):
        """Test creating sink with username/password."""
        uri = "postgres://user:pass@localhost:5432/mydb"
        sink = create_custom_sink_from_uri(uri)
        assert isinstance(sink, PostgresSink)

        assert sink.host == "localhost"
        assert sink.port == 5432
        assert sink.database == "mydb"
        assert sink.kwargs["username"] == "user"
        assert sink.kwargs["password"] == "pass"

    def test_create_custom_sink_with_parameters(self):
        """Test creating sink with query parameters."""
        uri = "postgres://localhost/logs?pool_size=10&ssl=true&timeout=30"
        sink = create_custom_sink_from_uri(uri)

        assert sink.kwargs["pool_size"] == 10  # type: ignore[attr-defined]
        assert sink.kwargs["ssl"] is True  # type: ignore[attr-defined]
        assert sink.kwargs["timeout"] == 30  # type: ignore[attr-defined]

    def test_create_sink_invalid_uri(self):
        """Test error handling for invalid URIs."""
        with pytest.raises(SinkConfigurationError) as exc_info:
            create_custom_sink_from_uri("not-a-uri")

        assert "URI must have a scheme" in str(exc_info.value)

    def test_create_sink_unregistered_type(self):
        """Test error for unregistered sink type."""
        with pytest.raises(SinkConfigurationError) as exc_info:
            create_custom_sink_from_uri("mysql://localhost/logs")

        error = exc_info.value
        assert "Unknown sink type 'mysql'" in str(error)
        assert "Available custom sinks:" in str(error)
        assert error.sink_name == "mysql"

    def test_create_sink_constructor_error(self):
        """Test error when sink constructor fails."""

        class FailingSink(Sink):
            def __init__(self, **kwargs):
                raise ValueError("Constructor failed")

            async def write(self, event_dict: Dict[str, Any]) -> None:
                pass

        SinkRegistry.register("failing", FailingSink)

        with pytest.raises(SinkConfigurationError) as exc_info:
            create_custom_sink_from_uri("failing://localhost")

        error = exc_info.value
        assert "Failed to create failing sink" in str(error)
        assert error.sink_name == "failing"


class TestParameterParsing:
    """Test URI parameter parsing functions."""

    def test_parse_basic_parameters(self):
        """Test parsing basic URI components."""
        from urllib.parse import urlparse

        parsed = urlparse("postgres://user:pass@localhost:5432/mydb")
        params = _parse_uri_parameters(parsed)

        assert params["host"] == "localhost"
        assert params["port"] == 5432
        assert params["username"] == "user"
        assert params["password"] == "pass"
        assert params["database"] == "mydb"

    def test_parse_query_parameters(self):
        """Test parsing query parameters."""
        from urllib.parse import urlparse

        parsed = urlparse("scheme://host?param1=value1&param2=value2")
        params = _parse_uri_parameters(parsed)

        assert params["param1"] == "value1"
        assert params["param2"] == "value2"

    def test_convert_parameter_values(self):
        """Test parameter value type conversion."""
        assert _convert_parameter_value("true") is True
        assert _convert_parameter_value("false") is False
        assert _convert_parameter_value("yes") is True
        assert _convert_parameter_value("no") is False
        assert _convert_parameter_value("1") == 1
        assert _convert_parameter_value("10") == 10
        assert _convert_parameter_value("3.14") == 3.14
        assert _convert_parameter_value("string") == "string"


class TestBootstrapIntegration:
    """Test integration with bootstrap configure_logging."""

    def setup_method(self):
        """Set up test environment."""
        SinkRegistry.clear()
        SinkRegistry.register("test", MockSink)

    def test_configure_logging_with_sink_instances(self):
        """Test configure_logging accepts direct sink instances."""
        test_sink = MockSink(test_param="value")

        logger = configure_logging(sinks=[test_sink])
        assert logger is not None

    def test_configure_logging_with_custom_uris(self):
        """Test configure_logging with custom sink URIs."""
        logger = configure_logging(sinks=["test://localhost?param=value"])
        assert logger is not None

    def test_configure_logging_mixed_sinks(self):
        """Test configure_logging with mixed sink types."""
        test_sink = MockSink()
        logger = configure_logging(sinks=[test_sink, "stdout"])
        assert logger is not None


class TestSettingsIntegration:
    """Test integration with LoggingSettings."""

    def setup_method(self):
        """Set up test environment."""
        SinkRegistry.clear()
        SinkRegistry.register("test", MockSink)

    def test_settings_with_sink_instances(self):
        """Test LoggingSettings accepts sink instances."""
        test_sink = MockSink()
        settings = LoggingSettings(sinks=[test_sink, "stdout"])

        assert len(settings.sinks) == 2
        assert settings.sinks[0] is test_sink
        assert settings.sinks[1] == "stdout"

    def test_settings_parse_mixed_types(self):
        """Test settings parser handles mixed types."""
        test_sink = MockSink()
        settings = LoggingSettings(sinks=[test_sink, "stdout", "test://host"])

        assert len(settings.sinks) == 3
        assert isinstance(settings.sinks[0], MockSink)
        assert settings.sinks[1] == "stdout"
        assert settings.sinks[2] == "test://host"


class TestErrorHandling:
    """Test comprehensive error handling."""

    def test_sink_configuration_error_properties(self):
        """Test SinkConfigurationError properties."""
        error = SinkConfigurationError("Test error", uri="test://uri", sink_name="test")

        assert str(error) == "Test error"
        assert error.uri == "test://uri"
        assert error.sink_name == "test"

    def test_thread_safety(self):
        """Test registry is thread-safe (basic test)."""
        import threading

        SinkRegistry.clear()
        results = []

        def register_sink_thread(name):
            try:
                SinkRegistry.register(f"sink_{name}", MockSink)
                results.append(f"success_{name}")
            except Exception as e:
                results.append(f"error_{name}_{e}")

        threads = []
        for i in range(10):
            thread = threading.Thread(target=register_sink_thread, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All registrations should succeed
        assert len(results) == 10
        assert all(r.startswith("success_") for r in results)
        assert len(SinkRegistry.list()) == 10
