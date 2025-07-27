"""Comprehensive tests to boost sink_testing module coverage."""

from typing import Any, Dict
from unittest.mock import patch

import pytest

from fapilog._internal.sink_registry import SinkRegistry
from fapilog.sinks import Sink
from fapilog.testing.sink_testing import SinkTestFramework


class ValidSink(Sink):
    """Valid sink for testing."""

    def __init__(self, **kwargs):
        super().__init__()
        self.kwargs = kwargs
        self.events = []

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Write event."""
        self.events.append(event_dict)


class InvalidSink:
    """Invalid sink that doesn't inherit from Sink."""

    async def write(self, event_dict: Dict[str, Any]) -> None:
        pass


class SinkWithoutWrite(Sink):
    """Sink missing write method."""

    def __init__(self):
        super().__init__()


class SinkWithSyncWrite(Sink):
    """Sink with non-async write method."""

    def __init__(self):
        super().__init__()

    def write(self, event_dict: Dict[str, Any]) -> None:  # type: ignore[override]
        """Intentionally synchronous write method for testing validation."""
        pass


class SinkWithBadInit(Sink):
    """Sink with problematic init."""

    def __init__(self, bad_param):  # Missing self
        pass

    async def write(self, event_dict: Dict[str, Any]) -> None:
        pass


class FailingConstructorSink(Sink):
    """Sink that fails during construction."""

    def __init__(self, **kwargs):
        if kwargs.get("should_fail"):
            raise RuntimeError("Construction failed")
        super().__init__()

    async def write(self, event_dict: Dict[str, Any]) -> None:
        pass


class FailingWriteSink(Sink):
    """Sink that fails during write."""

    def __init__(self):
        super().__init__()

    async def write(self, event_dict: Dict[str, Any]) -> None:
        raise RuntimeError("Write failed")


class TestSinkTestFrameworkCoverage:
    """Comprehensive tests for SinkTestFramework."""

    def setup_method(self):
        """Setup before each test."""
        self.framework = SinkTestFramework()
        # Clear registry
        SinkRegistry._sinks.clear()

    def teardown_method(self):
        """Cleanup after each test."""
        # Clear registry
        SinkRegistry._sinks.clear()

    def test_initialization(self):
        """Test SinkTestFramework initialization."""
        framework = SinkTestFramework()

        assert framework.recorded_events == []
        assert framework.errors == []

    def test_create_test_sink_success(self):
        """Test successful sink creation."""
        sink = self.framework.create_test_sink(ValidSink, param1="value1")

        assert isinstance(sink, ValidSink)
        assert sink.kwargs == {"param1": "value1"}
        assert len(self.framework.errors) == 0

    def test_create_test_sink_invalid_class(self):
        """Test sink creation with invalid class."""
        with pytest.raises(ValueError, match="must inherit from Sink"):
            self.framework.create_test_sink(InvalidSink)

    def test_create_test_sink_construction_failure(self):
        """Test sink creation when constructor fails."""
        with pytest.raises(RuntimeError, match="Construction failed"):
            self.framework.create_test_sink(FailingConstructorSink, should_fail=True)

        # Should have recorded the error
        assert len(self.framework.errors) == 1
        assert "Construction failed" in str(self.framework.errors[0])

    def test_validate_sink_interface_valid(self):
        """Test interface validation with valid sink."""
        result = self.framework.validate_sink_interface(ValidSink)

        assert result is True
        assert len(self.framework.errors) == 0

    def test_validate_sink_interface_not_sink_subclass(self):
        """Test interface validation with non-Sink class."""
        result = self.framework.validate_sink_interface(InvalidSink)

        assert result is False
        assert len(self.framework.errors) > 0
        assert "Must inherit from Sink base class" in str(self.framework.errors[0])

    def test_validate_sink_interface_sync_write(self):
        """Test interface validation with non-async write method."""
        result = self.framework.validate_sink_interface(SinkWithSyncWrite)

        assert result is False
        assert len(self.framework.errors) > 0
        assert "'write' method must be async" in str(self.framework.errors[0])

    def test_validate_sink_interface_bad_init_signature(self):
        """Test interface validation with bad init signature."""
        # Mock inspect.signature to simulate signature inspection failure
        with patch("fapilog.testing.sink_testing.inspect.signature") as mock_sig:
            mock_sig.side_effect = Exception("Signature error")

            result = self.framework.validate_sink_interface(ValidSink)

            assert result is False
            assert len(self.framework.errors) > 0
            assert "signature cannot be inspected" in str(self.framework.errors[0])

    def test_test_sink_registration_success(self):
        """Test successful sink registration."""
        result = self.framework.test_sink_registration("test", ValidSink)

        assert result is True
        assert len(self.framework.errors) == 0

    def test_test_sink_registration_failure(self):
        """Test sink registration with mocked failure."""
        # Mock SinkRegistry.register to return different class
        with patch("fapilog.testing.sink_testing.SinkRegistry.register") as mock_reg:
            mock_reg.return_value = InvalidSink  # Different class

            result = self.framework.test_sink_registration("test", ValidSink)

            assert result is False
            assert len(self.framework.errors) > 0
            assert "did not return the same class" in str(self.framework.errors[0])

    def test_test_sink_registration_retrieval_failure(self):
        """Test sink registration with retrieval failure."""
        # Mock SinkRegistry.get to return None
        with patch("fapilog.testing.sink_testing.SinkRegistry.get") as mock_get:
            mock_get.return_value = None

            result = self.framework.test_sink_registration("test", ValidSink)

            assert result is False
            assert len(self.framework.errors) > 0
            assert "does not match registered class" in str(self.framework.errors[0])

    def test_test_sink_registration_listing_failure(self):
        """Test sink registration with listing failure."""
        # Mock SinkRegistry.list to return empty dict
        with patch("fapilog.testing.sink_testing.SinkRegistry.list") as mock_list:
            mock_list.return_value = {}

            result = self.framework.test_sink_registration("test", ValidSink)

            assert result is False
            assert len(self.framework.errors) > 0
            assert "not found in registry listing" in str(self.framework.errors[0])

    def test_test_sink_registration_exception(self):
        """Test sink registration with exception."""
        # Mock SinkRegistry.register to raise exception
        with patch("fapilog.testing.sink_testing.SinkRegistry.register") as mock_reg:
            mock_reg.side_effect = RuntimeError("Registration error")

            result = self.framework.test_sink_registration("test", ValidSink)

            assert result is False
            assert len(self.framework.errors) > 0
            assert "Registration error" in str(self.framework.errors[0])

    def test_test_uri_parsing_success(self):
        """Test successful URI parsing."""
        with patch("fapilog.testing.uri_testing.validate_sink_uri") as mock_validate:
            with patch("fapilog.testing.uri_testing.parse_sink_uri") as mock_parse:
                mock_validate.return_value = {"valid": True}
                mock_parse.return_value = {"host": "localhost", "port": 8080}

                expected = {"host": "localhost", "port": 8080}
                result = self.framework.test_uri_parsing(
                    "test://localhost:8080", expected
                )

                assert result is True
                assert len(self.framework.errors) == 0

    def test_test_uri_parsing_invalid_uri(self):
        """Test URI parsing with invalid URI."""
        with patch("fapilog.testing.uri_testing.validate_sink_uri") as mock_validate:
            mock_validate.return_value = {
                "valid": False,
                "issues": ["Invalid scheme", "Missing host"],
            }

            result = self.framework.test_uri_parsing("invalid://", {"host": "test"})

            assert result is False
            assert len(self.framework.errors) > 0
            assert "Invalid URI" in str(self.framework.errors[0])

    def test_test_uri_parsing_mismatch(self):
        """Test URI parsing with parameter mismatch."""
        with patch("fapilog.testing.uri_testing.validate_sink_uri") as mock_validate:
            with patch("fapilog.testing.uri_testing.parse_sink_uri") as mock_parse:
                mock_validate.return_value = {"valid": True}
                mock_parse.return_value = {"host": "different"}

                expected = {"host": "localhost"}
                result = self.framework.test_uri_parsing("test://different", expected)

                assert result is False
                assert len(self.framework.errors) > 0
                assert "URI parsing mismatch" in str(self.framework.errors[0])

    def test_test_uri_parsing_exception(self):
        """Test URI parsing with exception."""
        with patch("fapilog.testing.uri_testing.validate_sink_uri") as mock_validate:
            mock_validate.side_effect = RuntimeError("Validation error")

            result = self.framework.test_uri_parsing(
                "test://localhost", {"host": "localhost"}
            )

            assert result is False
            assert len(self.framework.errors) > 0
            assert "Validation error" in str(self.framework.errors[0])

    def test_validate_sink_name_for_uri_valid(self):
        """Test valid sink name for URI."""
        with patch("fapilog.testing.uri_testing.validate_uri_scheme") as mock_validate:
            mock_validate.return_value = True

            result = self.framework.validate_sink_name_for_uri("valid-sink.name")

            assert result is True
            assert len(self.framework.errors) == 0

    def test_validate_sink_name_for_uri_invalid(self):
        """Test invalid sink name for URI."""
        with patch("fapilog.testing.uri_testing.validate_uri_scheme") as mock_validate:
            mock_validate.return_value = False

            result = self.framework.validate_sink_name_for_uri("invalid_sink_name")

            assert result is False
            assert len(self.framework.errors) > 0
            assert "Invalid sink name" in str(self.framework.errors[0])
            assert "underscores (_) are not allowed" in str(self.framework.errors[0])

    @pytest.mark.asyncio
    async def test_test_sink_write_success(self):
        """Test successful sink write."""
        sink = ValidSink()
        test_events = [
            {"level": "info", "message": "test1"},
            {"level": "error", "message": "test2"},
        ]

        result = await self.framework.test_sink_write(sink, test_events)

        assert result is True
        assert len(self.framework.recorded_events) == 2
        assert self.framework.recorded_events == test_events
        assert len(sink.events) == 2

    @pytest.mark.asyncio
    async def test_test_sink_write_default_events(self):
        """Test sink write with default test events."""
        sink = ValidSink()

        result = await self.framework.test_sink_write(sink)

        assert result is True
        assert len(self.framework.recorded_events) == 3  # Default has 3 events
        assert len(sink.events) == 3

    @pytest.mark.asyncio
    async def test_test_sink_write_failure(self):
        """Test sink write with failing sink."""
        sink = FailingWriteSink()

        result = await self.framework.test_sink_write(sink)

        assert result is False
        assert len(self.framework.errors) > 0
        assert "Write failed" in str(self.framework.errors[0])

    def test_clear_state(self):
        """Test clearing framework state."""
        # Add some events and errors
        self.framework.recorded_events = [{"test": "event"}]
        self.framework.errors = [RuntimeError("test error")]

        assert len(self.framework.recorded_events) == 1
        assert len(self.framework.errors) == 1

        self.framework.clear_state()

        assert len(self.framework.recorded_events) == 0
        assert len(self.framework.errors) == 0

    def test_get_test_summary_empty(self):
        """Test getting summary with no events or errors."""
        summary = self.framework.get_test_summary()

        assert summary["total_events"] == 0
        assert summary["total_errors"] == 0
        assert summary["errors"] == []
        assert summary["last_events"] == []

    def test_get_test_summary_with_data(self):
        """Test getting summary with events and errors."""
        # Add events and errors
        events = [{"event": i} for i in range(10)]
        self.framework.recorded_events = events
        self.framework.errors = [RuntimeError("error1"), ValueError("error2")]

        summary = self.framework.get_test_summary()

        assert summary["total_events"] == 10
        assert summary["total_errors"] == 2
        assert len(summary["errors"]) == 2
        assert "error1" in summary["errors"][0]
        assert "error2" in summary["errors"][1]

        # Should only show last 5 events
        assert len(summary["last_events"]) == 5
        assert summary["last_events"][-1] == {"event": 9}  # Last event
