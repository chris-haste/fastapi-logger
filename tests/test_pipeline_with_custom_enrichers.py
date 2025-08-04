"""Tests for custom enrichers integration with the pipeline."""

import structlog
from structlog.testing import CapturingLogger

from fapilog.bootstrap import configure_logging
from fapilog.config import LoggingSettings
from fapilog.enrichers import (
    clear_enrichers,
    register_enricher,
)
from fapilog.pipeline import build_processor_chain


def test_custom_enrichers_in_pipeline():
    """Test that custom enrichers are called in the pipeline."""
    # Clear any existing enrichers
    clear_enrichers()

    # Track if enricher was called
    enricher_called = False

    def test_enricher(logger, method_name, event_dict):
        nonlocal enricher_called
        enricher_called = True
        event_dict["custom_field"] = "custom_value"
        return event_dict

    # Register the enricher
    register_enricher(test_enricher)

    # Configure logging
    logger = configure_logging()

    # Log a message
    logger.info("test_message")

    # Verify the enricher was called
    assert enricher_called


def test_custom_enrichers_order_in_pipeline():
    """Test that custom enrichers run after built-in enrichers."""
    # Clear any existing enrichers
    clear_enrichers()

    # Track execution order
    execution_order = []

    def built_in_tracker(logger, method_name, event_dict):
        """Simulate a built-in enricher."""
        execution_order.append("built_in")
        return event_dict

    def custom_enricher(logger, method_name, event_dict):
        """Custom enricher that should run after built-in ones."""
        execution_order.append("custom")
        event_dict["custom_field"] = "custom_value"
        return event_dict

    # Register the custom enricher
    register_enricher(custom_enricher)

    # Configure logging with a custom processor to track built-in enrichers
    # We'll add our tracker to the pipeline manually
    settings = LoggingSettings()
    processors = build_processor_chain(settings)

    # Find where custom enrichers should be in the chain
    # They should be after host_process_enricher but before sampling
    custom_enricher_index = None
    for i, processor in enumerate(processors):
        if (
            hasattr(processor, "__name__")
            and processor.__name__ == "run_registered_enrichers"
        ):
            custom_enricher_index = i
            break

    # Verify custom enrichers are in the right position
    assert custom_enricher_index is not None

    # Verify they come after host_process_enricher
    host_process_found = False
    for i in range(custom_enricher_index):
        if (
            hasattr(processors[i], "__name__")
            and processors[i].__name__ == "host_process_enricher_sync"
        ):
            host_process_found = True
            break

    assert host_process_found, "Custom enrichers should come after built-in enrichers"


def test_custom_enrichers_with_actual_logging():
    """Test that custom enrichers affect actual log output."""
    clear_enrichers()

    # Clear context to avoid contamination from other tests
    from fapilog.utils.context import clear_context

    clear_context()

    def tenant_enricher(logger, method_name, event_dict):
        event_dict["tenant_id"] = "tenant_123"
        return event_dict

    def session_enricher(logger, method_name, event_dict):
        event_dict["session_id"] = "session_456"
        return event_dict

    register_enricher(tenant_enricher)
    register_enricher(session_enricher)

    # Create a minimal processor chain without queue
    settings = LoggingSettings()
    settings.queue.enabled = False
    processors = build_processor_chain(settings)

    # Use CapturingLogger to capture output
    cap_logger = CapturingLogger()

    # Configure structlog with our processor chain
    structlog.configure(
        processors=processors,
        logger_factory=lambda *a, **k: cap_logger,
        cache_logger_on_first_use=False,
    )
    logger = structlog.get_logger()

    logger.info("test_message", user_id="user_789")

    assert len(cap_logger.calls) > 0
    # CapturedCall structure: (method_name, args, kwargs)
    captured_call = cap_logger.calls[-1]
    import json

    event_dict = json.loads(captured_call.args[0])
    assert event_dict["tenant_id"] == "tenant_123"
    assert event_dict["session_id"] == "session_456"
    assert event_dict["user_id"] == "user_789"
    assert event_dict["event"] == "test_message"


def test_custom_enrichers_exception_handling():
    """Test that custom enricher exceptions don't break the pipeline."""
    clear_enrichers()

    def failing_enricher(logger, method_name, event_dict):
        raise RuntimeError("This enricher fails")

    def working_enricher(logger, method_name, event_dict):
        event_dict["working_field"] = "working_value"
        return event_dict

    register_enricher(failing_enricher)
    register_enricher(working_enricher)

    # Create a minimal processor chain without queue
    settings = LoggingSettings()
    settings.queue.enabled = False
    processors = build_processor_chain(settings)

    cap_logger = CapturingLogger()
    structlog.configure(
        processors=processors,
        logger_factory=lambda *a, **k: cap_logger,
        cache_logger_on_first_use=False,
    )
    logger = structlog.get_logger()

    logger.info("test_message")
    # The working enricher should still have been applied
    captured_call = cap_logger.calls[-1]
    import json

    event_dict = json.loads(captured_call.args[0])
    assert event_dict["working_field"] == "working_value"
    assert event_dict["event"] == "test_message"


def test_custom_enrichers_clear_functionality():
    """Test that clear_enrichers removes enrichers from the pipeline."""
    clear_enrichers()

    def test_enricher(logger, method_name, event_dict):
        event_dict["test_field"] = "test_value"
        return event_dict

    register_enricher(test_enricher)

    # Create a minimal processor chain without queue
    settings = LoggingSettings()
    settings.queue.enabled = False
    processors = build_processor_chain(settings)

    cap_logger = CapturingLogger()
    structlog.configure(
        processors=processors,
        logger_factory=lambda *a, **k: cap_logger,
        cache_logger_on_first_use=False,
    )
    logger = structlog.get_logger()

    clear_enrichers()
    logger.info("test_message")
    captured_call = cap_logger.calls[-1]
    import json

    event_dict = json.loads(captured_call.args[0])
    assert "test_field" not in event_dict
    assert event_dict["event"] == "test_message"
