#!/usr/bin/env python3
"""
Test script for sink-related examples.

This script tests the sink examples without requiring external services
like Loki or custom APIs.
"""

import asyncio
import json
import sys
import tempfile
import os
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fapilog import configure_logging
from fapilog.settings import LoggingSettings
from fapilog.sinks.stdout import StdoutSink


def test_loki_sink_example():
    """Test the Loki sink example configuration."""
    print("Testing Loki sink example...")

    try:
        # Import the example
        from examples import loki_sink_example

        # Test that the settings can be created
        settings = loki_sink_example.loki_settings
        assert settings.level == "INFO"
        assert settings.format == "json"
        assert len(settings.sinks) == 1
        assert settings.sinks[0].__class__.__name__ == "LokiSink"

        print("✓ Loki sink example configuration is valid")
        return True

    except Exception as e:
        print(f"✗ Loki sink example failed: {e}")
        return False


def test_multiple_sinks_example():
    """Test the multiple sinks example."""
    print("Testing multiple sinks example...")

    try:
        # Create a test version with stdout only
        test_settings = LoggingSettings(
            level="DEBUG",
            format="json",
            sinks=[
                StdoutSink(),
                StdoutSink(),
            ],
        )

        logger = configure_logging(test_settings)

        # Test logging
        logger.info("Test multiple sinks", extra={"test": True})
        logger.debug("Debug message", extra={"level": "debug"})
        logger.warning("Warning message", extra={"level": "warning"})

        print("✓ Multiple sinks example works")
        return True

    except Exception as e:
        print(f"✗ Multiple sinks example failed: {e}")
        return False


def test_custom_sink_example():
    """Test the custom sink example."""
    print("Testing custom sink example...")

    try:
        # Test with stdout sink instead of custom API
        test_settings = LoggingSettings(
            level="INFO",
            format="json",
            sinks=[
                StdoutSink(),
            ],
        )

        logger = configure_logging(test_settings)

        # Test audit logging
        logger.info(
            "User action audit",
            extra={
                "log_type": "audit",
                "user_id": "test-user",
                "action": "test-action",
                "resource": "test-resource",
                "details": {"test": True},
                "ip_address": "127.0.0.1",
                "session_id": "test-session",
            },
        )

        # Test regular logging
        logger.info(
            "Regular application log",
            extra={
                "user_id": "test-user",
                "action": "test-action",
                "resource": "test-resource",
            },
        )

        print("✓ Custom sink example works")
        return True

    except Exception as e:
        print(f"✗ Custom sink example failed: {e}")
        return False


def test_security_logging_example():
    """Test the security logging example."""
    print("Testing security logging example...")

    try:
        # Test security utilities
        from examples.security_logging_example import (
            mask_sensitive_data,
            hash_sensitive_data,
            sanitize_log_data,
        )

        # Test masking
        masked_email = mask_sensitive_data("user@example.com")
        assert masked_email == "us********@example.com"

        # Test hashing
        hashed_data = hash_sensitive_data("sensitive-data")
        assert len(hashed_data) == 16

        # Test sanitization
        test_data = {
            "email": "user@example.com",
            "password": "secret123",
            "credit_card": "1234567890123456",
            "normal_field": "normal-value",
        }
        sanitized = sanitize_log_data(test_data)
        assert sanitized["email"] == "us********@example.com"
        assert sanitized["password"] == "se******23"
        assert sanitized["credit_card"] == "12************56"
        assert sanitized["normal_field"] == "normal-value"

        # Test logging
        test_settings = LoggingSettings(
            level="INFO", format="json", sinks=[StdoutSink()]
        )

        logger = configure_logging(test_settings)

        # Test security event logging
        logger.info(
            "Security event",
            extra={
                "log_type": "security",
                "event_type": "login_attempt",
                "email": masked_email,
                "ip_address": "192.168.1.100",
                "timestamp": "2024-01-15T10:30:00Z",
            },
        )

        print("✓ Security logging example works")
        return True

    except Exception as e:
        print(f"✗ Security logging example failed: {e}")
        return False


async def test_async_logging():
    """Test async logging functionality."""
    print("Testing async logging...")

    try:
        settings = LoggingSettings(level="INFO", format="json", sinks=[StdoutSink()])

        logger = configure_logging(settings)

        # Test async logging
        async def async_function():
            logger.info("Async function started")
            await asyncio.sleep(0.1)
            logger.info("Async function completed")

        await async_function()

        print("✓ Async logging works")
        return True

    except Exception as e:
        print(f"✗ Async logging failed: {e}")
        return False


def test_file_logging():
    """Test file logging functionality."""
    print("Testing file logging...")

    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".log") as f:
            log_file_path = f.name

        try:
            settings = LoggingSettings(
                level="DEBUG",
                format="json",
                sinks=[StdoutSink(file_path=log_file_path)],
            )

            logger = configure_logging(settings)

            # Test logging to file
            logger.info("Test file logging", extra={"test": True})
            logger.debug("Debug message", extra={"level": "debug"})

            # Check if file was created and contains logs
            with open(log_file_path, "r") as f:
                content = f.read()
                assert "Test file logging" in content
                assert "Debug message" in content

            print("✓ File logging works")
            return True

        finally:
            # Clean up
            try:
                os.unlink(log_file_path)
            except OSError:
                pass

    except Exception as e:
        print(f"✗ File logging failed: {e}")
        return False


def main():
    """Run all sink example tests."""
    print("Testing sink-related examples...\n")

    tests = [
        test_loki_sink_example,
        test_multiple_sinks_example,
        test_custom_sink_example,
        test_security_logging_example,
        test_file_logging,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")

    # Test async logging separately
    try:
        if asyncio.run(test_async_logging()):
            passed += 1
        total += 1
    except Exception as e:
        print(f"✗ Async logging test failed: {e}")

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("✓ All sink examples are working correctly!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
