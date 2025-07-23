"""Debug utilities for sink registration and configuration."""

import asyncio
import inspect
import time
import traceback
from typing import Any, Dict, List, Type

from .._internal.queue import Sink
from .._internal.sink_factory import create_custom_sink_from_uri
from .._internal.sink_registry import SinkRegistry


class SinkDebugger:
    """Debug utilities for sink registration and configuration."""

    @staticmethod
    def list_registered_sinks() -> Dict[str, Type[Sink]]:
        """List all registered sinks with metadata.

        Returns:
            Dictionary mapping sink names to sink classes
        """
        return SinkRegistry.list()

    @staticmethod
    def get_sink_info(sink_name: str) -> Dict[str, Any]:
        """Get detailed information about a registered sink.

        Args:
            sink_name: Name of the registered sink

        Returns:
            Dictionary with sink information
        """
        sink_class = SinkRegistry.get(sink_name)

        if sink_class is None:
            return {
                "name": sink_name,
                "registered": False,
                "error": f"Sink '{sink_name}' not found in registry",
            }

        # Get class information
        info = {
            "name": sink_name,
            "registered": True,
            "class_name": sink_class.__name__,
            "module": sink_class.__module__,
            "file": inspect.getfile(sink_class)
            if hasattr(sink_class, "__file__")
            else None,
        }

        # Get constructor signature
        try:
            sig = inspect.signature(sink_class.__init__)
            info["constructor_signature"] = str(sig)
            info["constructor_params"] = list(sig.parameters.keys())[1:]  # Skip 'self'
        except Exception as e:
            info["constructor_signature"] = f"Error: {e}"
            info["constructor_params"] = []

        # Get docstring
        info["docstring"] = inspect.getdoc(sink_class) or "No docstring available"

        # Get methods
        methods = []
        for name, method in inspect.getmembers(
            sink_class, predicate=inspect.isfunction
        ):
            if not name.startswith("_") or name in ["__init__"]:
                methods.append(
                    {
                        "name": name,
                        "signature": str(inspect.signature(method)),
                        "is_async": asyncio.iscoroutinefunction(method),
                    }
                )
        info["methods"] = methods

        return info

    @staticmethod
    def validate_sink_class(sink_class: Type[Sink]) -> List[str]:
        """Validate a sink class and return any issues.

        Args:
            sink_class: Sink class to validate

        Returns:
            List of validation issues (empty if valid)
        """
        issues = []

        # Check inheritance
        if not issubclass(sink_class, Sink):
            issues.append("Must inherit from Sink base class")
            return issues  # Can't continue without proper inheritance

        # Check required methods
        if not hasattr(sink_class, "write"):
            issues.append("Missing required 'write' method")
        else:
            # Check write method signature
            try:
                write_method = sink_class.write
                if not asyncio.iscoroutinefunction(write_method):
                    issues.append("'write' method must be async")

                sig = inspect.signature(write_method)
                params = list(sig.parameters.keys())
                if len(params) != 2 or params[0] != "self" or params[1] != "event_dict":
                    issues.append(
                        "'write' method must have signature "
                        "(self, event_dict: Dict[str, Any]) -> None"
                    )
            except Exception as e:
                issues.append(f"Error inspecting 'write' method: {e}")

        # Check constructor
        if not hasattr(sink_class, "__init__"):
            issues.append("Missing __init__ method")
        else:
            try:
                sig = inspect.signature(sink_class.__init__)
                params = list(sig.parameters.keys())
                if not params or params[0] != "self":
                    issues.append(
                        "__init__ method must accept 'self' as first parameter"
                    )
            except Exception as e:
                issues.append(f"Error inspecting __init__ method: {e}")

        # Check for common issues
        if hasattr(sink_class, "write") and hasattr(sink_class, "__init__"):
            try:
                # Try to create an instance to check for obvious issues
                instance = sink_class()
                if not hasattr(instance, "_sink_name"):
                    issues.append(
                        "Instance missing '_sink_name' attribute (call super().__init__())"
                    )
            except Exception as e:
                issues.append(f"Cannot instantiate sink with no arguments: {e}")

        return issues

    @staticmethod
    def test_sink_instantiation(sink_class: Type[Sink], **kwargs) -> Dict[str, Any]:
        """Test that a sink can be instantiated with given parameters.

        Args:
            sink_class: Sink class to test
            **kwargs: Constructor arguments

        Returns:
            Test results dictionary
        """
        result = {
            "success": False,
            "sink_class": sink_class.__name__,
            "kwargs": kwargs,
            "error": None,
            "instance_created": False,
            "write_method_callable": False,
        }

        try:
            # Try to instantiate
            instance = sink_class(**kwargs)
            result["instance_created"] = True

            # Check if write method exists and is callable
            if hasattr(instance, "write") and callable(instance.write):
                result["write_method_callable"] = True

            result["success"] = True

        except Exception as e:
            result["error"] = str(e)
            result["traceback"] = traceback.format_exc()

        return result

    @staticmethod
    def test_sink_uri_parsing(uri: str) -> Dict[str, Any]:
        """Test URI parsing for sink configuration.

        Args:
            uri: URI to test

        Returns:
            Parsing test results
        """
        result = {
            "uri": uri,
            "success": False,
            "error": None,
            "parsed_scheme": None,
            "sink_found": False,
            "sink_class": None,
            "parameters": {},
            "instantiation_success": False,
        }

        try:
            from urllib.parse import urlparse

            parsed = urlparse(uri)
            result["parsed_scheme"] = parsed.scheme

            # Check if sink is registered
            sink_class = SinkRegistry.get(parsed.scheme)
            if sink_class:
                result["sink_found"] = True
                result["sink_class"] = sink_class.__name__
            else:
                result["error"] = f"Sink '{parsed.scheme}' not registered"
                return result

            # Try to create sink from URI
            try:
                create_custom_sink_from_uri(uri)
                result["instantiation_success"] = True
                result["success"] = True
            except Exception as e:
                result["error"] = f"Instantiation failed: {e}"

        except Exception as e:
            result["error"] = f"URI parsing failed: {e}"

        return result

    @staticmethod
    def diagnose_sink_registration_issues(
        sink_name: str, sink_class: Type[Sink]
    ) -> Dict[str, Any]:
        """Diagnose potential issues with sink registration.

        Args:
            sink_name: Name to register the sink under
            sink_class: Sink class to diagnose

        Returns:
            Dictionary with diagnosis results and recommendations
        """
        diagnosis: Dict[str, Any] = {
            "sink_name": sink_name,
            "sink_class": sink_class.__name__,
            "issues": [],
            "warnings": [],
            "can_register": False,
            "registration_test": None,
        }

        # Validate sink name
        if not sink_name or not sink_name.strip():
            diagnosis["issues"].append("Sink name cannot be empty")
        elif " " in sink_name:
            diagnosis["warnings"].append(
                "Sink name contains spaces - use underscores or hyphens"
            )
        elif sink_name != sink_name.lower():
            diagnosis["warnings"].append(
                "Sink name should be lowercase for URI compatibility"
            )

        # Validate sink class
        class_issues = SinkDebugger.validate_sink_class(sink_class)
        diagnosis["issues"].extend(class_issues)

        # Check if name is already registered
        existing_sink = SinkRegistry.get(sink_name)
        if existing_sink:
            if existing_sink == sink_class:
                diagnosis["warnings"].append("Sink already registered with same class")
            else:
                diagnosis["warnings"].append(
                    f"Sink name '{sink_name}' already registered "
                    f"with different class: {existing_sink.__name__}"
                )

        # Test instantiation
        instantiation_test = SinkDebugger.test_sink_instantiation(sink_class)
        if not instantiation_test["success"]:
            diagnosis["issues"].append(
                f"Cannot instantiate sink: {instantiation_test['error']}"
            )

        # Test registration if no blocking issues
        if not diagnosis["issues"]:
            diagnosis["can_register"] = True

            # Try actual registration test
            try:
                original_sinks = SinkRegistry._sinks.copy()
                registered_class = SinkRegistry.register(sink_name, sink_class)

                if registered_class == sink_class:
                    diagnosis["registration_test"] = {"success": True}

                    # Test retrieval
                    retrieved = SinkRegistry.get(sink_name)
                    if retrieved != sink_class:
                        diagnosis["issues"].append("Registration/retrieval mismatch")
                else:
                    diagnosis["issues"].append("Registration returned different class")

            except Exception as e:
                diagnosis["issues"].append(f"Registration failed: {e}")
            finally:
                # Restore original state
                SinkRegistry._sinks = original_sinks

        return diagnosis

    @staticmethod
    def debug_sink_configuration(uri: str) -> Dict[str, Any]:
        """Debug a complete sink configuration from URI.

        Args:
            uri: Sink URI to debug

        Returns:
            Comprehensive debug information
        """
        debug_info: Dict[str, Any] = {
            "uri": uri,
            "overall_status": "success",
            "recommendations": [],
            "uri_parsing": {},
            "sink_registration": {},
            "instantiation": {},
        }

        # Test URI parsing
        debug_info["uri_parsing"] = SinkDebugger.test_sink_uri_parsing(uri)

        if not debug_info["uri_parsing"]["success"]:
            debug_info["overall_status"] = "failed"
            debug_info["recommendations"].append(
                "Fix URI format or register the sink type"
            )
            return debug_info

        # Get sink information
        scheme = debug_info["uri_parsing"]["parsed_scheme"]
        sink_class = SinkRegistry.get(scheme)

        if sink_class:
            # Diagnose registration
            debug_info["sink_registration"] = (
                SinkDebugger.diagnose_sink_registration_issues(scheme, sink_class)
            )

            # Test instantiation from URI
            try:
                sink_instance = create_custom_sink_from_uri(uri)
                debug_info["instantiation"] = {
                    "success": True,
                    "sink_type": type(sink_instance).__name__,
                }
                debug_info["overall_status"] = "success"
            except Exception as e:
                debug_info["instantiation"] = {
                    "success": False,
                    "error": str(e),
                }
                debug_info["overall_status"] = "failed"
                debug_info["recommendations"].append(
                    f"Fix sink instantiation issue: {e}"
                )
        else:
            debug_info["overall_status"] = "failed"
            debug_info["recommendations"].append(f"Register sink type '{scheme}' first")

        return debug_info

    @staticmethod
    def print_sink_registry_status() -> None:
        """Print a human-readable status of the sink registry."""
        sinks = SinkDebugger.list_registered_sinks()

        print("\n=== Sink Registry Status ===")
        print(f"Total registered sinks: {len(sinks)}")

        if not sinks:
            print("No sinks currently registered.")
            print("\nTo register a sink:")
            print("  from fapilog import register_sink")
            print("  @register_sink('my_sink')")
            print("  class MySink(Sink): ...")
            print("=" * 29)
            return

        print("\nRegistered sinks:")
        for name, sink_class in sinks.items():
            print(f"  {name}: {sink_class.__name__}")

            # Quick validation
            issues = SinkDebugger.validate_sink_class(sink_class)
            if issues:
                print(f"    ⚠️  Issues: {', '.join(issues[:2])}")
                if len(issues) > 2:
                    print(f"    ⚠️  ... and {len(issues) - 2} more")
            else:
                print("    ✅ Valid")

        print("=" * 29)

    @staticmethod
    def print_sink_debug_info(sink_name: str) -> None:
        """Print detailed debug information for a specific sink.

        Args:
            sink_name: Name of the sink to debug
        """
        info = SinkDebugger.get_sink_info(sink_name)

        print(f"\n=== Debug Info: {sink_name} ===")

        if not info["registered"]:
            print(f"❌ {info['error']}")
            print("\nAvailable sinks:")
            for name in SinkDebugger.list_registered_sinks():
                print(f"  - {name}")
            print("=" * (len(sink_name) + 16))
            return

        print(f"Class: {info['class_name']}")
        print(f"Module: {info['module']}")

        if info.get("file"):
            print(f"File: {info['file']}")

        print(f"\nConstructor: {info['constructor_signature']}")

        if info["constructor_params"]:
            print(f"Parameters: {', '.join(info['constructor_params'])}")

        print("\nMethods:")
        for method in info["methods"]:
            async_marker = " (async)" if method["is_async"] else ""
            print(f"  {method['name']}{async_marker}: {method['signature']}")

        # Validation
        sink_class = SinkRegistry.get(sink_name)
        if sink_class:
            issues = SinkDebugger.validate_sink_class(sink_class)
            if issues:
                print("\n⚠️  Validation Issues:")
                for issue in issues:
                    print(f"  - {issue}")
            else:
                print("\n✅ Validation: All checks passed")

        print("=" * (len(sink_name) + 16))
