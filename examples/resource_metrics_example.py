#!/usr/bin/env python3
"""Example demonstrating resource metrics in fapilog."""

import time

from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings


def main():
    """Demonstrate resource metrics logging."""

    # Enable resource metrics
    settings = LoggingSettings(
        enable_resource_metrics=True,
        level="INFO",
        queue_enabled=False,  # Disable queue for simpler example
    )

    # Configure logging
    configure_logging(settings=settings)

    print("Resource Metrics Example")
    print("=" * 50)
    print("This example demonstrates memory and CPU usage in log entries.")
    print("Set FAPILOG_ENABLE_RESOURCE_METRICS=true to enable in production.")
    print()

    # Log some events to see resource metrics
    log.info("Application started")

    # Simulate some work
    log.info("Processing data", step="start")
    time.sleep(0.1)  # Simulate work
    log.info("Processing data", step="complete")

    # Log with custom fields
    log.info(
        "Custom event",
        custom_field="value",
        memory_mb=999.99,  # Manual override
        cpu_percent=88.88,
    )  # Manual override

    # Simulate error
    try:
        raise ValueError("Example error")
    except ValueError as e:
        log.error("Error occurred", error=str(e))

    log.info("Application completed")

    print()
    print("Check the log output above for memory_mb and cpu_percent fields.")
    print("Note: Values may vary based on system load and available resources.")


if __name__ == "__main__":
    main()
