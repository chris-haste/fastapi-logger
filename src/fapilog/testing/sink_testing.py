"""Framework for testing custom sinks."""

import asyncio
import inspect
from typing import Any, Dict, List, Optional, Type

from .._internal.queue import Sink
from .._internal.sink_registry import SinkRegistry


class SinkTestFramework:
    """Framework for testing custom sinks."""

    def __init__(self):
        self.recorded_events: List[Dict[str, Any]] = []
        self.errors: List[Exception] = []

    def create_test_sink(self, sink_class: Type[Sink], **kwargs) -> Sink:
        """Create a test instance of a sink.

        Args:
            sink_class: The sink class to instantiate
            **kwargs: Keyword arguments to pass to the sink constructor

        Returns:
            Configured sink instance

        Raises:
            ValueError: If sink_class is not a valid Sink subclass
            Exception: If sink instantiation fails
        """
        if not issubclass(sink_class, Sink):
            msg = f"{sink_class.__name__} must inherit from Sink"
            raise ValueError(msg)

        try:
            return sink_class(**kwargs)
        except Exception as e:
            self.errors.append(e)
            raise

    def validate_sink_interface(self, sink_class: Type[Sink]) -> bool:
        """Validate that a sink class implements the required interface.

        Args:
            sink_class: The sink class to validate

        Returns:
            True if the sink implements the required interface correctly
        """
        issues = []

        # Check if it's a Sink subclass
        if not issubclass(sink_class, Sink):
            issues.append("Must inherit from Sink base class")

        # Check required methods
        if not hasattr(sink_class, "write"):
            issues.append("Missing required 'write' method")
        elif not asyncio.iscoroutinefunction(sink_class.write):
            issues.append("'write' method must be async")

        # Check constructor
        if not hasattr(sink_class, "__init__"):
            issues.append("Missing __init__ method")
        else:
            # Check constructor signature is callable
            try:
                sig = inspect.signature(sink_class.__init__)
                # Ensure it accepts at least self
                params = list(sig.parameters.keys())
                if not params or params[0] != "self":
                    issues.append("__init__ method has invalid signature")
            except Exception:
                issues.append("__init__ method signature cannot be inspected")

        if issues:
            for issue in issues:
                err_msg = f"Interface validation failed: {issue}"
                self.errors.append(ValueError(err_msg))
            return False

        return True

    def test_sink_registration(self, name: str, sink_class: Type[Sink]) -> bool:
        """Test sink registration and retrieval.

        Args:
            name: Name to register the sink under
            sink_class: Sink class to register

        Returns:
            True if registration and retrieval work correctly
        """
        try:
            # Clear any existing registration
            original_sinks = SinkRegistry._sinks.copy()

            # Test registration
            registered_class = SinkRegistry.register(name, sink_class)

            # Verify registration worked
            if registered_class != sink_class:
                err_msg = "Registration did not return the same class"
                self.errors.append(ValueError(err_msg))
                return False

            # Test retrieval
            retrieved_class = SinkRegistry.get(name)
            if retrieved_class != sink_class:
                err_msg = "Retrieved class does not match registered class"
                self.errors.append(ValueError(err_msg))
                return False

            # Test listing includes the sink
            all_sinks = SinkRegistry.list()
            if name not in all_sinks or all_sinks[name] != sink_class:
                err_msg = "Sink not found in registry listing"
                self.errors.append(ValueError(err_msg))
                return False

            return True

        except Exception as e:
            self.errors.append(e)
            return False
        finally:
            # Restore original state
            SinkRegistry._sinks = original_sinks

    def test_uri_parsing(self, uri: str, expected_params: Dict) -> bool:
        """Test URI parsing for custom sinks.

        Args:
            uri: The URI to parse and test
            expected_params: Expected parameters from parsing

        Returns:
            True if URI parsing matches expectations
        """
        from .uri_testing import parse_sink_uri, validate_sink_uri

        try:
            # First validate the URI format
            validation = validate_sink_uri(uri)
            if not validation["valid"]:
                error_msg = f"Invalid URI: {'; '.join(validation['issues'])}"
                self.errors.append(ValueError(error_msg))
                return False

            # Then test parameter parsing
            result = parse_sink_uri(uri)
            success = result == expected_params

            if not success:
                error_msg = (
                    f"URI parsing mismatch. Expected: {expected_params}, Got: {result}"
                )
                self.errors.append(ValueError(error_msg))

            return success
        except Exception as e:
            self.errors.append(e)
            return False

    def validate_sink_name_for_uri(self, sink_name: str) -> bool:
        """Validate that a sink name can be used in URIs.

        Args:
            sink_name: The sink name to validate

        Returns:
            True if valid for URI usage
        """
        from .._internal.uri_validation import validate_uri_scheme

        if not validate_uri_scheme(sink_name):
            error_msg = (
                f"Invalid sink name '{sink_name}' for URI usage. "
                "Sink names used in URIs can only contain letters, digits, +, -, . "
                "and must start with a letter. Note: underscores (_) are not allowed."
            )
            self.errors.append(ValueError(error_msg))
            return False

        return True

    async def test_sink_write(
        self, sink: Sink, test_events: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """Test basic sink write functionality.

        Args:
            sink: Sink instance to test
            test_events: Optional list of test events. If None, uses default
                test events.

        Returns:
            True if all writes succeed without exceptions
        """
        if test_events is None:
            test_events = [
                {
                    "level": "info",
                    "message": "Test message 1",
                    "timestamp": "2023-01-01T12:00:00Z",
                },
                {"level": "error", "message": "Test error", "error": "Test exception"},
                {"level": "debug", "message": "Debug message", "extra_field": "value"},
            ]

        try:
            for event in test_events:
                await sink.write(event)
                self.recorded_events.append(event)
            return True

        except Exception as e:
            self.errors.append(e)
            return False

    def clear_state(self) -> None:
        """Clear recorded events and errors."""
        self.recorded_events.clear()
        self.errors.clear()

    def get_test_summary(self) -> Dict[str, Any]:
        """Get a summary of test results.

        Returns:
            Dictionary containing test statistics and errors
        """
        last_events = self.recorded_events[-5:] if self.recorded_events else []
        return {
            "total_events": len(self.recorded_events),
            "total_errors": len(self.errors),
            "errors": [str(e) for e in self.errors],
            "last_events": last_events,
        }
