#!/usr/bin/env python3
"""
Example 12: Batch Processing Configuration

This example demonstrates how batch size and batch timeout affect the logging queue's
behavior in fapilog. It shows how logs are flushed in batches and how tuning these
settings can optimize performance.
"""

import time

from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings


def log_with_batch(batch_size, batch_timeout, num_events=10):
    print(f"\n--- Batch Size: {batch_size}, Batch Timeout: {batch_timeout}s ---")
    settings = LoggingSettings(
        level="INFO",
        json_console="pretty",
        queue_enabled=True,
        queue_maxsize=20,
        queue_batch_size=batch_size,
        queue_batch_timeout=batch_timeout,
        queue_overflow="drop",
    )
    configure_logging(settings=settings)

    print(f"Logging {num_events} events...")
    for i in range(num_events):
        log.info("Batch processing test event", event_number=i)
        time.sleep(0.1)
    print("Waiting for queue to flush...")
    time.sleep(2)


def main():
    print("=== Batch Processing Configuration Example ===\n")
    print("This example demonstrates:")
    print("- How batch size controls the number of events flushed at once")
    print("- How batch timeout controls the maximum wait before flushing")
    print("- How tuning these settings can optimize performance")

    log_with_batch(batch_size=2, batch_timeout=1.0)
    log_with_batch(batch_size=5, batch_timeout=0.5)
    log_with_batch(batch_size=10, batch_timeout=0.2)

    print("\nKey takeaways:")
    print("✅ Small batch size = more frequent flushes, lower latency")
    print("✅ Large batch size = higher throughput, but more delay")
    print("✅ Batch timeout ensures logs are not delayed indefinitely")
    print("✅ Tune for your workload and sink performance")


if __name__ == "__main__":
    main()
