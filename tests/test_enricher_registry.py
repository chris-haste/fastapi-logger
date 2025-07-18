"""Tests for custom enricher registry functionality."""

from unittest.mock import Mock

import pytest

from fapilog.enrichers import (
    clear_enrichers,
    register_enricher,
    run_registered_enrichers,
)


def test_register_and_run_enricher():
    """Test that enrichers are registered and executed."""
    # Clear any existing enrichers
    clear_enrichers()

    # Create a test enricher
    def test_enricher(logger, method_name, event_dict):
        event_dict["custom_field"] = "test_value"
        return event_dict

    # Register the enricher
    register_enricher(test_enricher)

    # Test that it runs correctly
    event_dict = {"event": "test_message"}
    result = run_registered_enrichers(None, "info", event_dict)

    # Verify the enricher was applied
    assert result["custom_field"] == "test_value"
    assert result["event"] == "test_message"


def test_multiple_enrichers_in_order():
    """Test that multiple enrichers run in registration order."""
    # Clear any existing enrichers
    clear_enrichers()

    # Track execution order
    execution_order = []

    def first_enricher(logger, method_name, event_dict):
        execution_order.append("first")
        event_dict["first_field"] = "first_value"
        return event_dict

    def second_enricher(logger, method_name, event_dict):
        execution_order.append("second")
        event_dict["second_field"] = "second_value"
        return event_dict

    def third_enricher(logger, method_name, event_dict):
        execution_order.append("third")
        event_dict["third_field"] = "third_value"
        return event_dict

    # Register enrichers in order
    register_enricher(first_enricher)
    register_enricher(second_enricher)
    register_enricher(third_enricher)

    # Run the enrichers
    event_dict = {"event": "test_message"}
    result = run_registered_enrichers(None, "info", event_dict)

    # Verify execution order
    assert execution_order == ["first", "second", "third"]

    # Verify all fields were added
    assert result["first_field"] == "first_value"
    assert result["second_field"] == "second_value"
    assert result["third_field"] == "third_value"
    assert result["event"] == "test_message"


def test_duplicate_enrichers_are_ignored():
    """Test that duplicate enricher registrations are ignored."""
    # Clear any existing enrichers
    clear_enrichers()

    # Create a test enricher
    def test_enricher(logger, method_name, event_dict):
        if "call_count" not in event_dict:
            event_dict["call_count"] = 0
        event_dict["call_count"] += 1
        return event_dict

    # Register the same enricher multiple times
    register_enricher(test_enricher)
    register_enricher(test_enricher)  # Should be ignored
    register_enricher(test_enricher)  # Should be ignored

    # Run the enrichers
    event_dict = {"event": "test_message"}
    result = run_registered_enrichers(None, "info", event_dict)

    # Verify the enricher was only called once
    assert result["call_count"] == 1
    assert result["event"] == "test_message"


def test_clear_enrichers():
    """Test that clear_enrichers removes all registered enrichers."""
    # Clear any existing enrichers
    clear_enrichers()

    # Create and register a test enricher
    def test_enricher(logger, method_name, event_dict):
        event_dict["cleared_field"] = "should_be_cleared"
        return event_dict

    register_enricher(test_enricher)

    # Verify it was registered
    event_dict = {"event": "test_message"}
    result = run_registered_enrichers(None, "info", event_dict)
    assert "cleared_field" in result

    # Clear enrichers
    clear_enrichers()

    # Verify enrichers are cleared
    event_dict = {"event": "test_message"}
    result = run_registered_enrichers(None, "info", event_dict)
    assert "cleared_field" not in result
    assert result["event"] == "test_message"


def test_enricher_signature_validation():
    """Test that enrichers with incorrect signatures raise ValueError."""
    # Clear any existing enrichers
    clear_enrichers()

    # Test enricher with wrong number of parameters
    def wrong_signature_enricher(logger, method_name):
        return {}

    with pytest.raises(ValueError, match="Enricher function must have signature"):
        register_enricher(wrong_signature_enricher)

    # Test enricher with wrong parameter names
    def wrong_param_names_enricher(logger, method, event):
        return event

    with pytest.raises(ValueError, match="Enricher function must have signature"):
        register_enricher(wrong_param_names_enricher)

    # Test enricher with extra parameters
    def extra_params_enricher(logger, method_name, event_dict, extra_param):
        return event_dict

    with pytest.raises(ValueError, match="Enricher function must have signature"):
        register_enricher(extra_params_enricher)


def test_enricher_exception_handling():
    """Test that enricher exceptions don't break the chain."""
    # Clear any existing enrichers
    clear_enrichers()

    # Create enrichers - one that works, one that fails, one that works
    def working_enricher1(logger, method_name, event_dict):
        event_dict["field1"] = "value1"
        return event_dict

    def failing_enricher(logger, method_name, event_dict):
        raise RuntimeError("This enricher fails")

    def working_enricher2(logger, method_name, event_dict):
        event_dict["field2"] = "value2"
        return event_dict

    # Register all enrichers
    register_enricher(working_enricher1)
    register_enricher(failing_enricher)
    register_enricher(working_enricher2)

    # Run the enrichers
    event_dict = {"event": "test_message"}
    result = run_registered_enrichers(None, "info", event_dict)

    # Verify that working enrichers still executed
    assert result["field1"] == "value1"
    assert result["field2"] == "value2"
    assert result["event"] == "test_message"


def test_enricher_modifies_event_dict():
    """Test that enrichers can modify the event dictionary."""
    # Clear any existing enrichers
    clear_enrichers()

    def modifying_enricher(logger, method_name, event_dict):
        # Modify existing field
        event_dict["existing_field"] = "modified_value"
        # Add new field
        event_dict["new_field"] = "new_value"
        # Remove field
        event_dict.pop("remove_field", None)
        return event_dict

    register_enricher(modifying_enricher)

    # Run with initial event dict
    event_dict = {
        "event": "test_message",
        "existing_field": "original_value",
        "remove_field": "should_be_removed",
    }
    result = run_registered_enrichers(None, "info", event_dict)

    # Verify modifications
    assert result["existing_field"] == "modified_value"
    assert result["new_field"] == "new_value"
    assert "remove_field" not in result
    assert result["event"] == "test_message"


def test_enricher_returns_new_dict():
    """Test that enrichers can return a new dictionary."""
    # Clear any existing enrichers
    clear_enrichers()

    def new_dict_enricher(logger, method_name, event_dict):
        new_dict = event_dict.copy()
        new_dict["new_dict_field"] = "new_dict_value"
        return new_dict

    register_enricher(new_dict_enricher)

    # Run the enricher
    event_dict = {"event": "test_message"}
    result = run_registered_enrichers(None, "info", event_dict)

    # Verify the new field was added
    assert result["new_dict_field"] == "new_dict_value"
    assert result["event"] == "test_message"


def test_enricher_with_logger_and_method_name():
    """Test that enrichers receive logger and method_name parameters."""
    # Clear any existing enrichers
    clear_enrichers()

    received_logger = None
    received_method_name = None

    def test_enricher(logger, method_name, event_dict):
        nonlocal received_logger, received_method_name
        received_logger = logger
        received_method_name = method_name
        event_dict["received_params"] = True
        return event_dict

    register_enricher(test_enricher)

    # Create a mock logger
    mock_logger = Mock()
    method_name = "debug"

    # Run the enricher
    event_dict = {"event": "test_message"}
    result = run_registered_enrichers(mock_logger, method_name, event_dict)

    # Verify parameters were received
    assert received_logger is mock_logger
    assert received_method_name == method_name
    assert result["received_params"] is True
    assert result["event"] == "test_message"


def test_empty_registry():
    """Test that running with no registered enrichers works correctly."""
    # Clear any existing enrichers
    clear_enrichers()

    # Run with empty registry
    event_dict = {"event": "test_message"}
    result = run_registered_enrichers(None, "info", event_dict)

    # Verify event dict is unchanged
    assert result == event_dict


def test_multiple_registrations_same_function():
    """Test that registering the same function multiple times is handled correctly."""
    # Clear any existing enrichers
    clear_enrichers()

    def test_enricher(logger, method_name, event_dict):
        if "call_count" not in event_dict:
            event_dict["call_count"] = 0
        event_dict["call_count"] += 1
        return event_dict

    # Register the same function multiple times
    register_enricher(test_enricher)
    register_enricher(test_enricher)
    register_enricher(test_enricher)

    # Run the enrichers
    event_dict = {"event": "test_message"}
    result = run_registered_enrichers(None, "info", event_dict)

    # Verify the function was only called once
    assert result["call_count"] == 1
    assert result["event"] == "test_message"


def test_enricher_affects_log_output():
    """Test that registered enrichers actually affect log output."""
    # Clear any existing enrichers
    clear_enrichers()

    def tenant_enricher(logger, method_name, event_dict):
        event_dict["tenant_id"] = "tenant_123"
        return event_dict

    def session_enricher(logger, method_name, event_dict):
        event_dict["session_id"] = "session_456"
        return event_dict

    # Register enrichers
    register_enricher(tenant_enricher)
    register_enricher(session_enricher)

    # Run the enrichers
    event_dict = {"event": "user_login", "user_id": "user_789"}
    result = run_registered_enrichers(None, "info", event_dict)

    # Verify all fields are present
    assert result["tenant_id"] == "tenant_123"
    assert result["session_id"] == "session_456"
    assert result["user_id"] == "user_789"
    assert result["event"] == "user_login"
