#!/usr/bin/env python3
"""
Example 10: Queue Overflow Strategies

This example demonstrates the different queue overflow strategies in fapilog:
- drop: Silently drops logs when the queue is full
- block: Waits for space in the queue (may slow down logging)
- sample: Probabilistically keeps a fraction of logs when full
"""

import time
from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings


def log_events(strategy: str, sampling_rate: float = 1.0):
    print(
        f"\n--- Overflow Strategy: {strategy.upper()} (sampling_rate={sampling_rate}) ---"
    )
    settings = LoggingSettings(
        level="INFO",
        json_console="pretty",
        queue_enabled=True,
        queue_maxsize=5,  # Small queue for demonstration
        queue_batch_size=2,
        queue_batch_timeout=0.5,
        queue_overflow=strategy,
        sampling_rate=sampling_rate,
    )
    configure_logging(settings=settings)

    print(f"Logging 15 events rapidly with overflow strategy '{strategy}'...")
    for i in range(15):
        log.info("Overflow strategy test event", event_number=i)
        time.sleep(0.02)
    print("Waiting for queue to flush...")
    time.sleep(2)


def main():
    print("=== Queue Overflow Strategies Example ===\n")
    print("This example demonstrates:")
    print("- drop: Drops logs when full (default)")
    print("- block: Waits for space in the queue")
    print("- sample: Keeps a fraction of logs when full (sampling_rate)")

    log_events("drop")
    log_events("block")
    log_events("sample", sampling_rate=0.3)

    print("\nKey takeaways:")
    print("✅ drop: Fastest, but may lose logs under load")
    print("✅ block: No log loss, but may slow down app")
    print("✅ sample: Adaptive, keeps a sample under load")
    print("✅ Choose based on your reliability/performance needs")


if __name__ == "__main__":
    main()
