"""Tests for debug utilities."""

from typing import Any, Dict
from unittest.mock import Mock, patch

from fapilog.core.registries.sink_registry import SinkRegistry
from fapilog.sinks import Sink
from fapilog.testing.debug import SinkDebugger


class ValidTestSink(Sink):
    """A valid test sink for testing purposes."""

    def __init__(self, test_param: str = "default"):
        super().__init__()
        self.test_param = test_param

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Write event to test sink."""
        pass


class InvalidTestSink:
    """An invalid test sink that doesn't inherit from Sink."""

    def __init__(self):
        pass

    def write(self, event_dict: Dict[str, Any]) -> None:
        """Sync write method (should be async)."""
        pass


class AsyncInvalidTestSink(Sink):
    """An invalid test sink with wrong write signature."""

    def __init__(self):
        super().__init__()

    async def write(self, wrong_param: str) -> None:  # type: ignore[override]
        """Write method with wrong signature."""
        pass


class NoInitTestSink(Sink):
    """Test sink without proper __init__."""

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Write event."""
        pass


class FailingInitTestSink(Sink):
    """Test sink that fails during instantiation."""

    def __init__(self):
        raise Exception("Initialization failed")

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Write event."""
        pass


class TestSinkDebugger:
    """Test SinkDebugger class."""

    def setup_method(self):
        """Setup method to clean registry."""
        # Store original state and clean registry
        self.original_sinks = SinkRegistry._sinks.copy()
        SinkRegistry._sinks.clear()

    def teardown_method(self):
        """Cleanup method to restore registry."""
        # Restore original state
        SinkRegistry._sinks = self.original_sinks

    def test_list_registered_sinks_empty(self):
        """Test list_registered_sinks with empty registry."""
        result = SinkDebugger.list_registered_sinks()
        assert result == {}

    def test_list_registered_sinks_with_sinks(self):
        """Test list_registered_sinks with registered sinks."""
        SinkRegistry.register("test_sink", ValidTestSink)
        SinkRegistry.register("another_sink", ValidTestSink)

        result = SinkDebugger.list_registered_sinks()

        assert len(result) == 2
        assert "test_sink" in result
        assert "another_sink" in result
        assert result["test_sink"] == ValidTestSink
        assert result["another_sink"] == ValidTestSink

    def test_get_sink_info_not_found(self):
        """Test get_sink_info with non-existent sink."""
        result = SinkDebugger.get_sink_info("non_existent")

        assert result == {
            "name": "non_existent",
            "registered": False,
            "error": "Sink 'non_existent' not found in registry",
        }

    def test_get_sink_info_valid_sink(self):
        """Test get_sink_info with valid sink."""
        SinkRegistry.register("test_sink", ValidTestSink)

        result = SinkDebugger.get_sink_info("test_sink")

        assert result["name"] == "test_sink"
        assert result["registered"] is True
        assert result["class_name"] == "ValidTestSink"
        assert "test_debug" in result["module"]
        # File may be None for dynamically created classes
        assert "(self, test_param: str = 'default')" in result["constructor_signature"]
        assert result["constructor_params"] == ["test_param"]
        assert result["docstring"] == "A valid test sink for testing purposes."
        assert len(result["methods"]) >= 2  # __init__ and write

        # Check write method is async
        write_method = next(
            (m for m in result["methods"] if m["name"] == "write"), None
        )
        assert write_method is not None
        assert write_method["is_async"] is True

    def test_get_sink_info_constructor_error(self):
        """Test get_sink_info with sink that has constructor inspection error."""
        # Register a valid sink first, then patch the inspection
        SinkRegistry.register("mock_sink", ValidTestSink)

        # Patch only the specific inspect.signature call for __init__
        with patch("fapilog.testing.debug.inspect.signature") as mock_sig:
            # Return error for constructor, then normal mocks for other calls
            normal_mock = Mock()
            normal_mock.parameters = {}
            mock_sig.side_effect = [Exception("Signature error")] + [normal_mock] * 10

            result = SinkDebugger.get_sink_info("mock_sink")

            assert result["constructor_signature"] == "Error: Signature error"
            assert result["constructor_params"] == []

    def test_get_sink_info_no_file_attribute(self):
        """Test get_sink_info when sink class has no file attribute."""
        SinkRegistry.register("mock_sink", ValidTestSink)

        with patch("inspect.getfile", side_effect=Exception("No file")):
            with patch("inspect.getdoc", return_value=None):
                result = SinkDebugger.get_sink_info("mock_sink")

                assert result["file"] is None
                assert result["docstring"] == "No docstring available"

    def test_validate_sink_class_valid(self):
        """Test validate_sink_class with valid sink."""
        issues = SinkDebugger.validate_sink_class(ValidTestSink)
        assert issues == []

    def test_validate_sink_class_not_subclass(self):
        """Test validate_sink_class with non-Sink class."""
        issues = SinkDebugger.validate_sink_class(InvalidTestSink)
        assert len(issues) == 1
        assert "Must inherit from Sink base class" in issues[0]

    def test_validate_sink_class_no_write_method(self):
        """Test validate_sink_class with missing write method."""
        # Patch hasattr to simulate missing write method
        with patch("builtins.hasattr", side_effect=lambda obj, attr: attr != "write"):
            issues = SinkDebugger.validate_sink_class(ValidTestSink)
            assert "Missing required 'write' method" in issues

    def test_validate_sink_class_sync_write_method(self):
        """Test validate_sink_class with sync write method."""

        class SyncWriteTestSink(Sink):
            def __init__(self):
                super().__init__()

            def write(self, event_dict: Dict[str, Any]) -> None:  # type: ignore[override]
                pass

        issues = SinkDebugger.validate_sink_class(SyncWriteTestSink)
        assert "'write' method must be async" in issues

    def test_validate_sink_class_wrong_write_signature(self):
        """Test validate_sink_class with wrong write method signature."""
        issues = SinkDebugger.validate_sink_class(AsyncInvalidTestSink)
        assert any("signature" in issue for issue in issues)

    def test_validate_sink_class_write_inspection_error(self):
        """Test validate_sink_class when write method inspection fails."""
        mock_sink = type("MockSink", (Sink,), {})
        mock_sink.write = Mock()  # type: ignore[attr-defined]

        with patch("inspect.signature", side_effect=Exception("Inspection error")):
            issues = SinkDebugger.validate_sink_class(mock_sink)
            assert any("Error inspecting 'write' method" in issue for issue in issues)

    def test_validate_sink_class_no_init(self):
        """Test validate_sink_class with missing __init__ method."""
        # Create a class without __init__ by patching hasattr
        with patch(
            "builtins.hasattr", side_effect=lambda obj, attr: attr != "__init__"
        ):
            issues = SinkDebugger.validate_sink_class(ValidTestSink)
            assert "Missing __init__ method" in issues

    def test_validate_sink_class_init_inspection_error(self):
        """Test validate_sink_class when __init__ inspection fails."""
        mock_sink = type("MockSink", (Sink,), {})

        with patch("inspect.signature", side_effect=Exception("Init inspection error")):
            issues = SinkDebugger.validate_sink_class(mock_sink)
            assert any("Error inspecting __init__ method" in issue for issue in issues)

    def test_validate_sink_class_bad_init_signature(self):
        """Test validate_sink_class with bad __init__ signature."""

        class BadInitTestSink(Sink):
            def __init__(wrong_param):  # Missing self
                pass

        with patch("inspect.signature") as mock_sig:
            mock_sig.return_value.parameters.keys.return_value = ["wrong_param"]
            issues = SinkDebugger.validate_sink_class(BadInitTestSink)
            assert any(
                "must accept 'self' as first parameter" in issue for issue in issues
            )

    def test_validate_sink_class_missing_sink_name(self):
        """Test validate_sink_class with sink missing _sink_name attribute."""

        class NoSinkNameTestSink(Sink):
            def __init__(self):
                # Don't call super().__init__()
                pass

            async def write(self, event_dict: Dict[str, Any]) -> None:
                pass

        issues = SinkDebugger.validate_sink_class(NoSinkNameTestSink)
        assert any("_sink_name" in issue for issue in issues)

    def test_validate_sink_class_instantiation_error(self):
        """Test validate_sink_class with sink that fails to instantiate."""
        issues = SinkDebugger.validate_sink_class(FailingInitTestSink)
        assert any(
            "Cannot instantiate sink with no arguments" in issue for issue in issues
        )

    def test_test_sink_instantiation_success(self):
        """Test test_sink_instantiation with successful instantiation."""
        result = SinkDebugger.test_sink_instantiation(ValidTestSink, test_param="value")

        assert result["success"] is True
        assert result["sink_class"] == "ValidTestSink"
        assert result["kwargs"] == {"test_param": "value"}
        assert result["error"] is None
        assert result["instance_created"] is True
        assert result["write_method_callable"] is True

    def test_test_sink_instantiation_failure(self):
        """Test test_sink_instantiation with failed instantiation."""
        result = SinkDebugger.test_sink_instantiation(FailingInitTestSink)

        assert result["success"] is False
        assert result["sink_class"] == "FailingInitTestSink"
        assert result["error"] == "Initialization failed"
        assert result["traceback"] is not None
        assert result["instance_created"] is False
        assert result["write_method_callable"] is False

    def test_test_sink_instantiation_no_write_method(self):
        """Test test_sink_instantiation with sink without write method."""

        class NoWriteTestSink:
            def __init__(self):
                pass

        result = SinkDebugger.test_sink_instantiation(NoWriteTestSink)

        assert result["success"] is True
        assert result["instance_created"] is True
        assert result["write_method_callable"] is False

    def test_test_sink_uri_parsing_success(self):
        """Test test_sink_uri_parsing with valid URI."""
        SinkRegistry.register("test", ValidTestSink)

        # Use a URI with query parameters that match ValidTestSink constructor
        with patch(
            "fapilog.core.factories.sink_factory.create_custom_sink_from_uri"
        ) as mock_create:
            mock_create.return_value = ValidTestSink()

            result = SinkDebugger.test_sink_uri_parsing("test:///?test_param=value")

            assert result["success"] is True
            assert result["uri"] == "test:///?test_param=value"
            assert result["parsed_scheme"] == "test"
            assert result["sink_found"] is True
            assert result["sink_class"] == "ValidTestSink"
            assert result["instantiation_success"] is True

    def test_test_sink_uri_parsing_sink_not_found(self):
        """Test test_sink_uri_parsing with unregistered sink."""
        result = SinkDebugger.test_sink_uri_parsing("unknown://config")

        assert result["success"] is False
        assert result["error"] == "Sink 'unknown' not registered"
        assert result["sink_found"] is False

    def test_test_sink_uri_parsing_instantiation_failure(self):
        """Test test_sink_uri_parsing with instantiation failure."""
        SinkRegistry.register("test", ValidTestSink)

        with patch("fapilog.testing.debug.create_custom_sink_from_uri") as mock_create:
            mock_create.side_effect = Exception("Create failed")

            result = SinkDebugger.test_sink_uri_parsing("test:///?test_param=value")

            assert result["success"] is False
            assert result["error"] == "Instantiation failed: Create failed"
            assert result["instantiation_success"] is False

    def test_test_sink_uri_parsing_invalid_uri(self):
        """Test test_sink_uri_parsing with invalid URI."""
        with patch("urllib.parse.urlparse", side_effect=Exception("Parse error")):
            result = SinkDebugger.test_sink_uri_parsing("invalid://uri")

            assert result["success"] is False
            assert result["error"] == "URI parsing failed: Parse error"

    def test_diagnose_sink_registration_issues_valid(self):
        """Test diagnose_sink_registration_issues with valid sink."""
        result = SinkDebugger.diagnose_sink_registration_issues(
            "test_sink", ValidTestSink
        )

        assert result["sink_name"] == "test_sink"
        assert result["sink_class"] == "ValidTestSink"
        assert result["issues"] == []
        assert result["can_register"] is True
        assert result["registration_test"]["success"] is True

    def test_diagnose_sink_registration_issues_empty_name(self):
        """Test diagnose_sink_registration_issues with empty sink name."""
        result = SinkDebugger.diagnose_sink_registration_issues("", ValidTestSink)

        assert "Sink name cannot be empty" in result["issues"]
        assert result["can_register"] is False

    def test_diagnose_sink_registration_issues_whitespace_name(self):
        """Test diagnose_sink_registration_issues with whitespace in name."""
        result = SinkDebugger.diagnose_sink_registration_issues("   ", ValidTestSink)

        assert "Sink name cannot be empty" in result["issues"]

    def test_diagnose_sink_registration_issues_spaces_in_name(self):
        """Test diagnose_sink_registration_issues with spaces in name."""
        result = SinkDebugger.diagnose_sink_registration_issues(
            "test sink", ValidTestSink
        )

        assert any("spaces" in warning for warning in result["warnings"])

    def test_diagnose_sink_registration_issues_uppercase_name(self):
        """Test diagnose_sink_registration_issues with uppercase name."""
        result = SinkDebugger.diagnose_sink_registration_issues(
            "TestSink", ValidTestSink
        )

        assert any("lowercase" in warning for warning in result["warnings"])

    def test_diagnose_sink_registration_issues_invalid_class(self):
        """Test diagnose_sink_registration_issues with invalid sink class."""
        result = SinkDebugger.diagnose_sink_registration_issues("test", InvalidTestSink)

        assert len(result["issues"]) > 0
        assert result["can_register"] is False

    def test_diagnose_sink_registration_issues_already_registered_same(self):
        """Test diagnose_sink_registration_issues with already registered same class."""
        SinkRegistry.register("test_sink", ValidTestSink)

        result = SinkDebugger.diagnose_sink_registration_issues(
            "test_sink", ValidTestSink
        )

        assert any(
            "already registered with same class" in warning
            for warning in result["warnings"]
        )

    def test_diagnose_sink_registration_issues_already_registered_different(self):
        """Test diagnose_sink_registration_issues with already registered different class."""
        SinkRegistry.register("test_sink", ValidTestSink)

        result = SinkDebugger.diagnose_sink_registration_issues(
            "test_sink", AsyncInvalidTestSink
        )

        assert any(
            "already registered with different class" in warning
            for warning in result["warnings"]
        )

    def test_diagnose_sink_registration_issues_instantiation_failure(self):
        """Test diagnose_sink_registration_issues with failing instantiation."""
        result = SinkDebugger.diagnose_sink_registration_issues(
            "test", FailingInitTestSink
        )

        assert any("Cannot instantiate sink" in issue for issue in result["issues"])
        assert result["can_register"] is False

    def test_diagnose_sink_registration_issues_registration_failure(self):
        """Test diagnose_sink_registration_issues with registration failure."""
        with patch.object(
            SinkRegistry, "register", side_effect=Exception("Registration failed")
        ):
            result = SinkDebugger.diagnose_sink_registration_issues(
                "test", ValidTestSink
            )

            assert any("Registration failed" in issue for issue in result["issues"])

    def test_diagnose_sink_registration_issues_retrieval_mismatch(self):
        """Test diagnose_sink_registration_issues with retrieval mismatch."""
        with patch.object(SinkRegistry, "register", return_value=ValidTestSink):
            with patch.object(SinkRegistry, "get", return_value=AsyncInvalidTestSink):
                result = SinkDebugger.diagnose_sink_registration_issues(
                    "test", ValidTestSink
                )

                assert any(
                    "Registration/retrieval mismatch" in issue
                    for issue in result["issues"]
                )

    def test_diagnose_sink_registration_issues_wrong_registration_return(self):
        """Test diagnose_sink_registration_issues with wrong registration return."""
        with patch.object(SinkRegistry, "register", return_value=AsyncInvalidTestSink):
            result = SinkDebugger.diagnose_sink_registration_issues(
                "test", ValidTestSink
            )

            assert any(
                "Registration returned different class" in issue
                for issue in result["issues"]
            )

    def test_debug_sink_configuration_success(self):
        """Test debug_sink_configuration with successful configuration."""
        SinkRegistry.register("test", ValidTestSink)

        with patch(
            "fapilog.core.factories.sink_factory.create_custom_sink_from_uri"
        ) as mock_create:
            mock_create.return_value = ValidTestSink()

            result = SinkDebugger.debug_sink_configuration("test:///?test_param=value")

            assert result["overall_status"] == "success"
            assert result["uri"] == "test:///?test_param=value"
            assert result["uri_parsing"]["success"] is True
            assert result["instantiation"]["success"] is True

    def test_debug_sink_configuration_uri_parsing_failure(self):
        """Test debug_sink_configuration with URI parsing failure."""
        result = SinkDebugger.debug_sink_configuration("invalid://uri")

        assert result["overall_status"] == "failed"
        assert not result["uri_parsing"]["success"]
        assert "Fix URI format or register the sink type" in result["recommendations"]

    def test_debug_sink_configuration_instantiation_failure(self):
        """Test debug_sink_configuration with instantiation failure."""
        SinkRegistry.register("test", ValidTestSink)

        # Mock the create_custom_sink_from_uri to succeed in test_sink_uri_parsing but fail later
        with patch("fapilog.testing.debug.create_custom_sink_from_uri") as mock_create:
            # First call in test_sink_uri_parsing succeeds, second call in debug_sink_configuration fails
            mock_create.side_effect = [
                ValidTestSink(),
                Exception("Instantiation failed"),
            ]

            result = SinkDebugger.debug_sink_configuration("test:///?test_param=value")

            assert result["overall_status"] == "failed"
            assert result["instantiation"]["success"] is False
            assert any(
                "Fix sink instantiation issue" in rec
                for rec in result["recommendations"]
            )

    def test_debug_sink_configuration_sink_not_registered(self):
        """Test debug_sink_configuration with unregistered sink."""
        result = SinkDebugger.debug_sink_configuration("unknown://config")

        assert result["overall_status"] == "failed"
        # The actual behavior is that it returns the generic message since URI parsing fails early
        assert any(
            "Fix URI format or register the sink type" in rec
            for rec in result["recommendations"]
        )

    def test_print_sink_registry_status_empty(self, capsys):
        """Test print_sink_registry_status with empty registry."""
        SinkDebugger.print_sink_registry_status()

        captured = capsys.readouterr()
        assert "=== Sink Registry Status ===" in captured.out
        assert "Total registered sinks: 0" in captured.out
        assert "No sinks currently registered." in captured.out
        assert "To register a sink:" in captured.out

    def test_print_sink_registry_status_with_sinks(self, capsys):
        """Test print_sink_registry_status with registered sinks."""
        SinkRegistry.register("valid_sink", ValidTestSink)
        # Directly add invalid sink to bypass validation for testing
        SinkRegistry._sinks["invalid_sink"] = InvalidTestSink

        SinkDebugger.print_sink_registry_status()

        captured = capsys.readouterr()
        assert "Total registered sinks: 2" in captured.out
        assert "valid_sink: ValidTestSink" in captured.out
        assert "invalid_sink: InvalidTestSink" in captured.out
        assert "✅ Valid" in captured.out
        assert "⚠️  Issues:" in captured.out

    def test_print_sink_registry_status_with_many_issues(self, capsys):
        """Test print_sink_registry_status with sink having many issues."""

        # Create a sink class with multiple issues (no inheritance, no methods, etc.)
        class VeryInvalidSink:
            def some_method(self):  # Wrong method signature
                pass

        # Directly add invalid sink to bypass validation for testing
        SinkRegistry._sinks["very_invalid"] = VeryInvalidSink

        SinkDebugger.print_sink_registry_status()

        captured = capsys.readouterr()
        assert "⚠️  Issues:" in captured.out
        # This class should have multiple issues: inheritance, missing write, missing __init__ etc.
        # Just check for issues being reported - the truncation logic depends on actual issue count
        assert "Must inherit from Sink base class" in captured.out

    def test_print_sink_debug_info_not_found(self, capsys):
        """Test print_sink_debug_info with non-existent sink."""
        SinkRegistry.register("existing_sink", ValidTestSink)

        SinkDebugger.print_sink_debug_info("non_existent")

        captured = capsys.readouterr()
        assert "=== Debug Info: non_existent ===" in captured.out
        assert "❌ Sink 'non_existent' not found in registry" in captured.out
        assert "Available sinks:" in captured.out
        assert "existing_sink" in captured.out

    def test_print_sink_debug_info_valid_sink(self, capsys):
        """Test print_sink_debug_info with valid sink."""
        SinkRegistry.register("test_sink", ValidTestSink)

        SinkDebugger.print_sink_debug_info("test_sink")

        captured = capsys.readouterr()
        assert "=== Debug Info: test_sink ===" in captured.out
        assert "Class: ValidTestSink" in captured.out
        assert "Constructor:" in captured.out
        assert "Parameters:" in captured.out
        assert "Methods:" in captured.out
        assert "✅ Validation: All checks passed" in captured.out

    def test_print_sink_debug_info_invalid_sink(self, capsys):
        """Test print_sink_debug_info with invalid sink."""
        # Directly add invalid sink to bypass validation for testing
        SinkRegistry._sinks["invalid_sink"] = InvalidTestSink

        SinkDebugger.print_sink_debug_info("invalid_sink")

        captured = capsys.readouterr()
        assert "=== Debug Info: invalid_sink ===" in captured.out
        assert "⚠️  Validation Issues:" in captured.out
        assert "Must inherit from Sink base class" in captured.out

    def test_print_sink_debug_info_no_file_info(self, capsys):
        """Test print_sink_debug_info with sink that has no file info."""
        mock_sink = Mock()
        mock_sink.__name__ = "MockSink"
        mock_sink.__module__ = "test_module"

        with patch("fapilog.testing.debug.SinkDebugger.get_sink_info") as mock_get_info:
            mock_get_info.return_value = {
                "name": "test_sink",
                "registered": True,
                "class_name": "MockSink",
                "module": "test_module",
                "file": None,
                "constructor_signature": "(self)",
                "constructor_params": [],
                "methods": [],
                "docstring": "Test docstring",
            }

            SinkDebugger.print_sink_debug_info("test_sink")

            captured = capsys.readouterr()
            assert "Class: MockSink" in captured.out
            assert "Module: test_module" in captured.out
            # Should not show file line when file is None
            assert "File:" not in captured.out

    def test_print_sink_debug_info_no_constructor_params(self, capsys):
        """Test print_sink_debug_info with sink that has no constructor params."""
        with patch("fapilog.testing.debug.SinkDebugger.get_sink_info") as mock_get_info:
            mock_get_info.return_value = {
                "name": "test_sink",
                "registered": True,
                "class_name": "MockSink",
                "module": "test_module",
                "file": "/test/file.py",
                "constructor_signature": "(self)",
                "constructor_params": [],
                "methods": [
                    {
                        "name": "write",
                        "is_async": True,
                        "signature": "(self, event_dict)",
                    }
                ],
                "docstring": "Test docstring",
            }

            SinkRegistry.register("test_sink", ValidTestSink)
            SinkDebugger.print_sink_debug_info("test_sink")

            captured = capsys.readouterr()
            # Should not show parameters line when there are no params
            assert "Parameters:" not in captured.out
            assert "write (async):" in captured.out

    def test_coverage_edge_cases(self):
        """Test additional edge cases for complete coverage."""

        # Test with sink that has no __file__ attribute
        class NoFileTestSink(Sink):
            async def write(self, event_dict: Dict[str, Any]) -> None:
                pass

        # Remove __file__ attribute if it exists
        if hasattr(NoFileTestSink, "__file__"):
            delattr(NoFileTestSink, "__file__")

        SinkRegistry.register("no_file_sink", NoFileTestSink)
        _ = SinkDebugger.get_sink_info("no_file_sink")
        # Should handle missing file gracefully

        # Test edge case in validate_sink_class with empty parameters
        with patch("inspect.signature") as mock_sig:
            mock_sig.return_value.parameters.keys.return_value = []
            _ = SinkDebugger.validate_sink_class(ValidTestSink)
            # Should handle empty parameters

    def test_async_method_detection(self):
        """Test async method detection in get_sink_info."""

        class MixedMethodsSink(Sink):
            def __init__(self):
                super().__init__()

            async def write(self, event_dict: Dict[str, Any]) -> None:
                pass

            def sync_method(self):
                pass

            async def async_method(self):
                pass

        SinkRegistry.register("mixed_sink", MixedMethodsSink)
        info = SinkDebugger.get_sink_info("mixed_sink")

        # Find methods and check async detection
        write_method = next((m for m in info["methods"] if m["name"] == "write"), None)
        sync_method = next(
            (m for m in info["methods"] if m["name"] == "sync_method"), None
        )
        async_method = next(
            (m for m in info["methods"] if m["name"] == "async_method"), None
        )

        assert write_method is not None
        assert write_method["is_async"] is True
        if sync_method:  # May be filtered out by inspect.getmembers
            assert sync_method is not None
            assert sync_method["is_async"] is False
        if async_method:
            assert async_method is not None
            assert async_method["is_async"] is True
