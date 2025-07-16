#!/usr/bin/env python3
"""Example demonstrating the StdoutSink functionality with different modes."""

import os

from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings


def demonstrate_json_mode() -> None:
    """Demonstrate JSON output mode."""
    print("\n=== JSON Mode ===")
    settings = LoggingSettings(json_console="json")
    configure_logging(settings=settings)

    log.info("user_login", user_id="12345", ip_address="192.168.1.1")
    log.warning("rate_limit_exceeded", user_id="12345", attempts=5)
    log.error("database_connection_failed", retry_count=3)


def demonstrate_pretty_mode() -> None:
    """Demonstrate pretty output mode."""
    print("\n=== Pretty Mode ===")
    settings = LoggingSettings(json_console="pretty")
    configure_logging(settings=settings)

    log.info("user_login", user_id="12345", ip_address="192.168.1.1")
    log.warning("rate_limit_exceeded", user_id="12345", attempts=5)
    log.error("database_connection_failed", retry_count=3)


def demonstrate_auto_mode() -> None:
    """Demonstrate auto mode (detects TTY)."""
    print("\n=== Auto Mode ===")
    settings = LoggingSettings(json_console="auto")
    configure_logging(settings=settings)

    log.info("user_login", user_id="12345", ip_address="192.168.1.1")
    log.warning("rate_limit_exceeded", user_id="12345", attempts=5)
    log.error("database_connection_failed", retry_count=3)


def demonstrate_environment_variables() -> None:
    """Demonstrate using environment variables."""
    print("\n=== Environment Variable Configuration ===")

    # Set environment variable
    os.environ["FAPILOG_JSON_CONSOLE"] = "pretty"
    os.environ["FAPILOG_LEVEL"] = "DEBUG"

    # Configure logging (will use environment variables)
    configure_logging()

    log.debug("debug_message", detail="This is a debug message")
    log.info("info_message", detail="This is an info message")
    log.warning("warning_message", detail="This is a warning message")
    log.error("error_message", detail="This is an error message")


def main() -> None:
    """Run the demonstration."""
    print("StdoutSink Mode Demonstration")
    print("=" * 40)

    # Demonstrate different modes
    demonstrate_json_mode()
    demonstrate_pretty_mode()
    demonstrate_auto_mode()
    demonstrate_environment_variables()

    print("\n" + "=" * 40)
    print("Demonstration complete!")
    print("\nTo run with different modes:")
    print("  FAPILOG_JSON_CONSOLE=json python examples/stdout_sink_example.py")
    print("  FAPILOG_JSON_CONSOLE=pretty python examples/stdout_sink_example.py")
    print("  FAPILOG_JSON_CONSOLE=auto python examples/stdout_sink_example.py")


if __name__ == "__main__":
    main()
