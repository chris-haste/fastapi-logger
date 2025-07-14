"""Tests for fapilog bootstrap functionality."""

import json
import logging
import os
import sys
from unittest.mock import patch

import pytest
import structlog

from fapilog.bootstrap import configure_logging, reset_logging
from fapilog.settings import LoggingSettings


class TestConfigureLogging:
    """Test the configure_logging function."""

    def setup_method(self) -> None:
        """Reset logging before each test."""
        reset_logging()

    def teardown_method(self) -> None:
        """Reset logging after each test."""
        reset_logging()

    def test_configure_returns_logger(self) -> None:
        """Test that configure_logging returns a structlog.BoundLogger."""
        logger = configure_logging()
        # structlog returns a lazy proxy initially, but it should be callable
        assert callable(logger.info)
        assert callable(logger.error)

    def test_idempotent(self) -> None:
        """Test that multiple calls don't duplicate handlers."""
        # First call
        logger1 = configure_logging()
        handler_count_1 = len(logging.root.handlers)

        # Second call
        logger2 = configure_logging()
        handler_count_2 = len(logging.root.handlers)

        # Handler count should be the same
        assert handler_count_1 == handler_count_2
        # Both should be callable loggers
        assert callable(logger1.info)
        assert callable(logger2.info)

    def test_json_event_fields(self, capsys: pytest.CaptureFixture) -> None:
        """Test that JSON logs contain expected fields."""
        with patch.dict(os.environ, {"FAPILOG_JSON_CONSOLE": "json"}):
            logger = configure_logging()
            logger.info("test_event")

            # Capture stdout since structlog uses PrintLoggerFactory
            captured = capsys.readouterr()
            log_line = captured.out.strip()

            # Parse the JSON log
            log_data = json.loads(log_line)

            # Check required fields
            assert "timestamp" in log_data
            assert "level" in log_data
            assert "event" in log_data

            # Check values
            assert log_data["level"] == "info"
            assert log_data["event"] == "test_event"

            # Check timestamp format (ISO-8601)
            assert "T" in log_data["timestamp"]
            assert "Z" in log_data["timestamp"] or "+" in log_data["timestamp"]

    def test_pretty_toggle_json(self) -> None:
        """Test that JSON rendering is used when explicitly set."""
        with patch.dict(os.environ, {"FAPILOG_JSON_CONSOLE": "json"}):
            configure_logging()

            # Check that structlog is configured with JSONRenderer
            config = structlog.get_config()
            processors = config.get("processors", [])

            # Find the renderer by checking the last processor
            assert len(processors) > 0
            last_processor = processors[-1]
            assert "JSONRenderer" in str(type(last_processor))

    def test_pretty_toggle_pretty(self) -> None:
        """Test that pretty rendering is used when explicitly set."""
        with patch.dict(os.environ, {"FAPILOG_JSON_CONSOLE": "pretty"}):
            configure_logging()

            # Check that structlog is configured with ConsoleRenderer
            config = structlog.get_config()
            processors = config.get("processors", [])

            # Find the renderer by checking the last processor
            assert len(processors) > 0
            last_processor = processors[-1]
            assert "ConsoleRenderer" in str(type(last_processor))

    def test_tty_detection_pretty(self) -> None:
        """Test that TTY detection defaults to pretty output."""
        with patch.object(sys.stderr, "isatty", return_value=True):
            with patch.dict(os.environ, {}, clear=True):
                configure_logging()

                # Check that structlog is configured with ConsoleRenderer
                config = structlog.get_config()
                processors = config.get("processors", [])

                # Find the renderer by checking the last processor
                assert len(processors) > 0
                last_processor = processors[-1]
                assert "ConsoleRenderer" in str(type(last_processor))

    def test_tty_detection_json(self) -> None:
        """Test that non-TTY defaults to JSON output."""
        with patch.object(sys.stderr, "isatty", return_value=False):
            with patch.dict(os.environ, {}, clear=True):
                configure_logging()

                # Check that structlog is configured with JSONRenderer
                config = structlog.get_config()
                processors = config.get("processors", [])

                # Find the renderer by checking the last processor
                assert len(processors) > 0
                last_processor = processors[-1]
                assert "JSONRenderer" in str(type(last_processor))

    def test_level_override(self) -> None:
        """Test that level override works."""
        configure_logging(level="DEBUG")

        # Check that the root logger has DEBUG level
        assert logging.root.level == logging.DEBUG

    def test_env_level_override(self) -> None:
        """Test that FAPILOG_LEVEL environment variable works."""
        with patch.dict(os.environ, {"FAPILOG_LEVEL": "DEBUG"}):
            configure_logging()

            # Check that the root logger has DEBUG level
            assert logging.root.level == logging.DEBUG

    def test_level_override_takes_precedence(self) -> None:
        """Test that function parameter takes precedence over env var."""
        with patch.dict(os.environ, {"FAPILOG_LEVEL": "DEBUG"}):
            configure_logging(level="WARNING")

            # Check that the root logger has WARNING level
            assert logging.root.level == logging.WARNING

    def test_async_context_safety(self) -> None:
        """Test that logging works in async context."""
        import asyncio

        async def async_log_test() -> None:
            """Test logging in async context."""
            logger = configure_logging()
            logger.info("async_test_event")

        # This should not raise RuntimeError
        asyncio.run(async_log_test())

    def test_reset_logging(self) -> None:
        """Test that reset_logging properly resets the configuration."""
        # Configure logging
        configure_logging()

        # Reset logging
        reset_logging()

        # Check that handlers are removed
        assert len(logging.root.handlers) == 0

        # Check that we can configure again
        configure_logging()
        assert len(logging.root.handlers) > 0

    def test_configure_with_settings_object(self) -> None:
        """Test that configure_logging works with a LoggingSettings object."""
        settings = LoggingSettings(level="DEBUG", json_console="json")
        logger = configure_logging(settings=settings)

        # Check that the logger is callable
        assert callable(logger.info)
        assert callable(logger.error)

        # Check that the root logger has DEBUG level
        assert logging.root.level == logging.DEBUG
