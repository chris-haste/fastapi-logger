"""Test that fapilog can be imported correctly."""

import fapilog


def test_import() -> None:
    """Test that fapilog can be imported and has expected attributes."""
    assert hasattr(fapilog, "configure_logging")
    assert hasattr(fapilog, "log")
    assert callable(fapilog.configure_logging)
    # Check that the logger has the expected methods
    assert hasattr(fapilog.log, "info")
    assert hasattr(fapilog.log, "error")
    assert hasattr(fapilog.log, "warning")
    assert hasattr(fapilog.log, "debug")


def test_log_info_call() -> None:
    """Test that log.info can be called without errors."""
    # This should not raise any exceptions
    fapilog.log.info("test_message")
    fapilog.log.info("test_with_data", key="value", number=42)
