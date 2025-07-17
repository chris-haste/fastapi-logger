#!/usr/bin/env python3
"""
Test script for corrected sink examples.

This script tests the corrected examples to ensure they work
with the actual fapilog API.
"""

import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fapilog import configure_logging
from fapilog.settings import LoggingSettings


def test_environment_config():
    """Test environment variable configuration."""
    print("Testing environment variable configuration...")

    try:
        # Configure using environment variables (defaults)
        logger = configure_logging()

        logger.info(
            "Environment configuration test",
            extra={"test": True, "method": "environment"},
        )

        print("✅ Environment configuration works")
        return True

    except Exception as e:
        print(f"✗ Environment configuration failed: {e}")
        return False


def test_programmatic_config():
    """Test programmatic configuration."""
    print("Testing programmatic configuration...")

    try:
        # Configure via settings object
        settings = LoggingSettings(
            level="INFO",
            sinks=["stdout"],  # List of sink names
            queue_enabled=True,
            queue_maxsize=100,
            queue_batch_size=5,
        )

        logger = configure_logging(settings=settings)

        logger.info(
            "Programmatic configuration test",
            extra={"test": True, "method": "programmatic"},
        )

        print("✅ Programmatic configuration works")
        return True

    except Exception as e:
        print(f"✗ Programmatic configuration failed: {e}")
        return False


def test_mixed_config():
    """Test mixed configuration."""
    print("Testing mixed configuration...")

    try:
        # Start with environment settings, override specific values
        settings = LoggingSettings(
            level="DEBUG",  # Override environment level
            sinks=["stdout"],  # Override to just stdout
            queue_enabled=True,
        )

        logger = configure_logging(settings=settings)

        logger.debug("Debug message with mixed configuration")
        logger.info("Mixed configuration test", extra={"test": True, "method": "mixed"})

        print("✅ Mixed configuration works")
        return True

    except Exception as e:
        print(f"✗ Mixed configuration failed: {e}")
        return False


def test_multiple_sinks_config():
    """Test multiple sinks configuration."""
    print("Testing multiple sinks configuration...")

    try:
        # Configure multiple sinks
        settings = LoggingSettings(
            level="INFO",
            sinks=["stdout", "file"],  # Multiple sink names
            queue_enabled=True,
            queue_maxsize=100,
            queue_batch_size=5,
        )

        logger = configure_logging(settings=settings)

        logger.info(
            "Multiple sinks test", extra={"test": True, "sinks": ["stdout", "file"]}
        )

        print("✅ Multiple sinks configuration works")
        return True

    except Exception as e:
        print(f"✗ Multiple sinks configuration failed: {e}")
        return False


def test_logging_levels():
    """Test different logging levels."""
    print("Testing logging levels...")

    try:
        settings = LoggingSettings(level="DEBUG", sinks=["stdout"], queue_enabled=True)

        logger = configure_logging(settings=settings)

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        print("✅ Logging levels work")
        return True

    except Exception as e:
        print(f"✗ Logging levels failed: {e}")
        return False


def main():
    """Run all tests."""
    print("Testing corrected sink examples...\n")

    tests = [
        test_environment_config,
        test_programmatic_config,
        test_mixed_config,
        test_multiple_sinks_config,
        test_logging_levels,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("✅ All corrected examples are working correctly!")
        print("\nKey improvements:")
        print("✅ Uses correct LoggingSettings class")
        print("✅ Uses configure_logging() function")
        print("✅ Sinks configured as string names, not objects")
        print("✅ Environment variable configuration works")
        print("✅ Programmatic configuration works")
        print("✅ Multiple sinks configuration works")
        return 0
    else:
        print("✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
