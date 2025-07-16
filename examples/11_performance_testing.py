#!/usr/bin/env python3
"""
Example 11: Performance Testing

This example demonstrates simple performance/load testing of the fapilog queue.
It logs a large number of events as quickly as possible and measures throughput.
"""

import time
from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings


def main():
    print("=== Performance Testing Example ===\n")
    num_events = 1000
    settings = LoggingSettings(
        level="INFO",
        json_console="json",
        queue_enabled=True,
        queue_maxsize=500,
        queue_batch_size=50,
        queue_batch_timeout=0.5,
        queue_overflow="drop",
    )
    configure_logging(settings=settings)

    print(f"Logging {num_events} events as fast as possible...")
    start = time.perf_counter()
    for i in range(num_events):
        log.info("Performance test event", event_number=i)
    duration = time.perf_counter() - start
    print(f"Enqueued {num_events} events in {duration:.3f} seconds")
    print(f"Throughput: {num_events/duration:.1f} events/sec")

    print("Waiting for queue to flush...")
    time.sleep(2)
    print("Done.")
    print("\nKey takeaways:")
    print("✅ Queue can handle high throughput")
    print("✅ Batch size and queue size affect performance")
    print("✅ Use performance testing to tune your settings")


if __name__ == "__main__":
    main()
