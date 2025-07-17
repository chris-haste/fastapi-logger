#!/usr/bin/env python3
"""
Example 9: Queue Configuration

This example demonstrates how to configure and use the async logging queue in fapilog.
It shows how queue settings affect logging behavior and performance.
"""

import time

from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings


def main():
    print("=== Queue Configuration Example ===\n")

    # Configure logging with queue enabled
    settings = LoggingSettings(
        level="INFO",
        json_console="pretty",
        queue_enabled=True,  # Enable async queue
        queue_maxsize=5,  # Small queue for demonstration
        queue_batch_size=2,  # Process 2 events per batch
        queue_batch_timeout=0.5,  # 0.5s max wait for batch
        queue_overflow="drop",  # Drop logs if queue is full
    )
    configure_logging(settings=settings)

    print("Queue settings:")
    print(f"  queue_enabled: {settings.queue_enabled}")
    print(f"  queue_maxsize: {settings.queue_maxsize}")
    print(f"  queue_batch_size: {settings.queue_batch_size}")
    print(f"  queue_batch_timeout: {settings.queue_batch_timeout}")
    print(f"  queue_overflow: {settings.queue_overflow}")
    print()

    print("Logging 10 events rapidly to demonstrate queue behavior...")
    for i in range(10):
        log.info("Queue test event", event_number=i)
        time.sleep(0.05)  # Rapid fire

    print("\nAll events enqueued. Waiting for queue to flush...")
    time.sleep(2)  # Wait for queue to process

    print("\nKey takeaways:")
    print("✅ Async queue decouples logging from main thread")
    print("✅ Small queue size can drop logs if overwhelmed")
    print("✅ Batch size and timeout control flush behavior")
    print("✅ Overflow strategy determines what happens when full")
    print("✅ Use larger queue and batch size for production")


if __name__ == "__main__":
    main()
