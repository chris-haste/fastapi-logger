"""Simplified comprehensive tests for debug.py to improve coverage."""

from typing import Any, Dict
from unittest.mock import patch

import pytest

from fapilog._internal.queue import Sink
from fapilog._internal.sink_registry import SinkRegistry
from fapilog.testing.debug import SinkDebugger


class MockSinkForTesting(Sink):
    """Mock sink for comprehensive testing."""

    def __init__(self, host: str = "localhost", port: int = 8080):
        super().__init__()
        self.host = host
        self.port = port

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Write event to test sink."""
        pass


class ProblematicSink(Sink):
    """Sink class with problematic constructor for testing."""

    def __init__(self):
        # Intentionally don't call super().__init__() to test missing _sink_name
        self.name = "problematic"

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Write event."""
        pass


class SinkWithBadWriteSignature(Sink):
    """Sink with wrong write method signature."""

    async def write(self, wrong_arg) -> None:
        """Write method with wrong signature."""
        pass


class SinkThatFailsInstantiation(Sink):
    """Sink that fails during instantiation."""

    def __init__(self):
        raise ValueError("Intentional instantiation failure")

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Write event."""
        pass


class TestSinkDebuggerComprehensiveSimple:
    """Simplified comprehensive tests for SinkDebugger."""

    def setup_method(self):
        """Setup for each test method."""
        # Clear registry before each test
        SinkRegistry._sinks.clear()

    def teardown_method(self):
        """Cleanup after each test method."""
        # Clear registry after each test
        SinkRegistry._sinks.clear()

    def test_get_sink_info_no_file_attribute(self):
        """Test get_sink_info when sink class has no __file__ attribute."""
        SinkRegistry.register("test", MockSinkForTesting)

        with patch("inspect.getfile", side_effect=AttributeError("No __file__")):
            result = SinkDebugger.get_sink_info("test")

        assert result["registered"] is True
        # Should handle the exception gracefully

    def test_get_sink_info_no_docstring(self):
        """Test get_sink_info when sink class has no docstring."""

        class NoDocstringSink(Sink):
            def __init__(self):
                super().__init__()

            async def write(self, event_dict: Dict[str, Any]) -> None:
                pass

        SinkRegistry.register("no_doc", NoDocstringSink)

        with patch("inspect.getdoc", return_value=None):
            result = SinkDebugger.get_sink_info("no_doc")

        assert result["docstring"] == "No docstring available"

    def test_validate_sink_class_non_async_write_method(self):
        """Test validation of sink with non-async write method."""

        class SyncWriteSink(Sink):
            def __init__(self):
                super().__init__()

            def write(self, event_dict: Dict[str, Any]) -> None:  # type: ignore[override]
                # Not async - this should trigger validation error
                pass

        issues = SinkDebugger.validate_sink_class(SyncWriteSink)

        assert any("'write' method must be async" in issue for issue in issues)

    def test_validate_sink_class_wrong_write_signature(self):
        """Test validation of sink with wrong write method signature."""
        issues = SinkDebugger.validate_sink_class(SinkWithBadWriteSignature)

        assert any("'write' method must have signature" in issue for issue in issues)

    def test_validate_sink_class_missing_sink_name(self):
        """Test validation when instance is missing _sink_name attribute."""
        issues = SinkDebugger.validate_sink_class(ProblematicSink)

        assert any(
            "Instance missing '_sink_name' attribute" in issue for issue in issues
        )

    def test_validate_sink_class_instantiation_failure(self):
        """Test validation when sink instantiation fails."""
        issues = SinkDebugger.validate_sink_class(SinkThatFailsInstantiation)

        assert any(
            "Cannot instantiate sink with no arguments" in issue for issue in issues
        )

    def test_test_sink_uri_parsing_uri_parsing_exception(self):
        """Test URI parsing when urlparse raises exception."""
        with patch("urllib.parse.urlparse", side_effect=Exception("Parse error")):
            result = SinkDebugger.test_sink_uri_parsing("invalid_uri")

        assert result["success"] is False
        assert "URI parsing failed: Parse error" in result["error"]

    def test_test_sink_uri_parsing_sink_instantiation_failure(self):
        """Test URI parsing when sink instantiation fails."""
        SinkRegistry.register("failing", SinkThatFailsInstantiation)

        result = SinkDebugger.test_sink_uri_parsing("failing://localhost")

        assert result["sink_found"] is True
        assert result["instantiation_success"] is False
        assert "Instantiation failed:" in result["error"]

    def test_diagnose_sink_registration_issues_name_with_spaces(self):
        """Test diagnosis with sink name containing spaces."""
        diagnosis = SinkDebugger.diagnose_sink_registration_issues(
            "sink with spaces", MockSinkForTesting
        )

        assert any("contains spaces" in warning for warning in diagnosis["warnings"])

    def test_diagnose_sink_registration_issues_uppercase_name(self):
        """Test diagnosis with uppercase sink name."""
        diagnosis = SinkDebugger.diagnose_sink_registration_issues(
            "UPPERCASE", MockSinkForTesting
        )

        assert any("lowercase" in warning for warning in diagnosis["warnings"])

    def test_diagnose_sink_registration_issues_existing_different_class(self):
        """Test diagnosis when sink name exists with different class."""
        SinkRegistry.register("existing", MockSinkForTesting)

        diagnosis = SinkDebugger.diagnose_sink_registration_issues(
            "existing", ProblematicSink
        )

        assert any(
            "already registered with different class" in warning
            for warning in diagnosis["warnings"]
        )

    def test_debug_sink_configuration_uri_parsing_failure(self):
        """Test debug configuration when URI parsing fails."""
        result = SinkDebugger.debug_sink_configuration("unregistered://localhost")

        assert result["overall_status"] == "failed"
        # Check that it handles unregistered sink gracefully

    def test_print_sink_debug_info_with_issues(self, capsys):
        """Test print_sink_debug_info for sink with validation issues."""
        SinkRegistry.register("problematic", SinkThatFailsInstantiation)

        SinkDebugger.print_sink_debug_info("problematic")

        captured = capsys.readouterr()
        assert "Debug Info: problematic" in captured.out
        assert "⚠️  Validation Issues:" in captured.out

    def test_print_sink_debug_info_no_issues(self, capsys):
        """Test print_sink_debug_info for valid sink."""
        SinkRegistry.register("valid", MockSinkForTesting)

        SinkDebugger.print_sink_debug_info("valid")

        captured = capsys.readouterr()
        assert "Debug Info: valid" in captured.out
        assert "✅ Validation: All checks passed" in captured.out

    def test_print_sink_registry_status_with_valid_sinks(self, capsys):
        """Test print_sink_registry_status with valid sinks."""
        SinkRegistry.register("valid1", MockSinkForTesting)

        SinkDebugger.print_sink_registry_status()

        captured = capsys.readouterr()
        assert "Total registered sinks: 1" in captured.out
        assert "✅ Valid" in captured.out

    def test_print_sink_registry_status_with_issues(self, capsys):
        """Test print_sink_registry_status with sinks having issues."""
        SinkRegistry.register("problematic", SinkThatFailsInstantiation)

        SinkDebugger.print_sink_registry_status()

        captured = capsys.readouterr()
        assert "Total registered sinks: 1" in captured.out
        assert "⚠️  Issues:" in captured.out


if __name__ == "__main__":
    pytest.main([__file__])
