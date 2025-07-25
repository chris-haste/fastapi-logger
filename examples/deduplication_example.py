"""Example demonstrating DeduplicationProcessor for removing duplicate log events.

This example shows how to use the DeduplicationProcessor to eliminate duplicate
log events within a configurable time window, preventing log flooding.
"""

import time

from fapilog import configure_logging, log
from fapilog._internal.processors import DeduplicationProcessor
from fapilog.settings import LoggingSettings


def basic_deduplication_example():
    """Basic deduplication example showing duplicate removal."""
    print("=== Basic Deduplication Example ===")

    # Configure logging with deduplication enabled
    settings = LoggingSettings(
        enable_deduplication=True,
        dedupe_window_seconds=60,  # 1 minute window
        dedupe_fields=["event", "error_code", "service"],
        dedupe_max_cache_size=5000,
        dedupe_hash_algorithm="md5",
        sinks=["stdout"],
        json_console="pretty",
    )

    configure_logging(settings=settings)

    print("Sending identical events (should be deduplicated)...")
    print("Expected: First event passes, subsequent identical events are dropped\n")

    # These events are identical in the dedupe_fields
    for i in range(5):
        log.error(
            "Database connection failed",
            error_code="DB001",
            service="payment-service",
            request_id=f"req-{i}",  # Different request_id but same dedupe signature
            timestamp=time.time(),
        )
        print(f"Sent event {i + 1}")

    print("\n")


def different_signatures_example():
    """Example showing events with different signatures are not deduplicated."""
    print("=== Different Signatures Example ===")

    # Create a deduplication processor directly for demonstration
    dedupe_processor = DeduplicationProcessor(
        window_seconds=60,
        dedupe_fields=["event", "error_code"],
        hash_algorithm="sha256",
    )

    print("Sending events with different error codes (different signatures)...")
    print("Expected: All events pass (different error codes)\n")

    events = [
        {"event": "Database error", "error_code": "DB001", "service": "api"},
        {"event": "Database error", "error_code": "DB002", "service": "api"},
        {"event": "Database error", "error_code": "DB003", "service": "api"},
    ]

    for i, event in enumerate(events):
        result = dedupe_processor.process(None, "error", event)

        if result is not None:
            print(f"✅ Event {i + 1} (error_code: {event['error_code']}): PASSED")
        else:
            print(f"❌ Event {i + 1} (error_code: {event['error_code']}): DEDUPLICATED")

    print("\nNow sending duplicates...")
    for i, event in enumerate(events):
        result = dedupe_processor.process(None, "error", event)

        if result is not None:
            print(f"✅ Duplicate {i + 1}: PASSED")
        else:
            print(f"❌ Duplicate {i + 1}: DEDUPLICATED")

    print("\n")


def time_window_expiration_example():
    """Example showing time window expiration."""
    print("=== Time Window Expiration Example ===")

    dedupe_processor = DeduplicationProcessor(
        window_seconds=2,  # Very short window for demo
        dedupe_fields=["event"],
        hash_algorithm="md5",
    )

    print("Deduplication window: 2 seconds")
    print("Sending identical events with time delays...\n")

    event = {"event": "Service health check failed", "service": "monitoring"}

    # First event - should pass
    result1 = dedupe_processor.process(None, "warn", event)
    print(f"First event: {'PASSED' if result1 else 'DEDUPLICATED'}")

    # Immediate duplicate - should be deduplicated
    result2 = dedupe_processor.process(None, "warn", event)
    print(f"Immediate duplicate: {'PASSED' if result2 else 'DEDUPLICATED'}")

    print("Waiting 2.5 seconds for window to expire...")
    time.sleep(2.5)

    # After window expiration - should pass again
    result3 = dedupe_processor.process(None, "warn", event)
    print(f"After window expiration: {'PASSED' if result3 else 'DEDUPLICATED'}")

    print("\n")


def hash_algorithm_comparison_example():
    """Example comparing different hash algorithms."""
    print("=== Hash Algorithm Comparison Example ===")

    processors = {
        "MD5": DeduplicationProcessor(hash_algorithm="md5"),
        "SHA1": DeduplicationProcessor(hash_algorithm="sha1"),
        "SHA256": DeduplicationProcessor(hash_algorithm="sha256"),
    }

    event = {"event": "Configuration updated", "component": "auth-service"}

    print("Generating signatures with different algorithms:")
    for algo, processor in processors.items():
        signature = processor._generate_signature(event)
        print(f"  {algo}: {signature} (length: {len(signature)})")

    print("\n")


def cache_monitoring_example():
    """Example showing cache statistics monitoring."""
    print("=== Cache Monitoring Example ===")

    dedupe_processor = DeduplicationProcessor(
        window_seconds=300,
        dedupe_fields=["event", "service"],
        max_cache_size=100,
        hash_algorithm="md5",
    )

    print("Adding various events and monitoring cache...")

    # Add unique events
    services = ["api", "auth", "payment", "notification", "analytics"]
    events_per_service = 3

    for service in services:
        for i in range(events_per_service):
            event = {
                "event": f"Service operation {i}",
                "service": service,
                "timestamp": time.time(),
            }
            dedupe_processor.process(None, "info", event)

    print(
        f"Added {len(services)} services × {events_per_service} events = {len(services) * events_per_service} unique events"
    )

    # Add some duplicates
    duplicate_count = 0
    for service in services[:2]:  # Only first 2 services
        for i in range(2):  # 2 duplicates each
            event = {
                "event": f"Service operation {i}",
                "service": service,
                "timestamp": time.time(),
            }
            result = dedupe_processor.process(None, "info", event)
            if result is None:
                duplicate_count += 1

    print(f"Attempted to add duplicates, {duplicate_count} were deduplicated")

    # Show cache statistics
    stats = dedupe_processor.cache_stats
    print("\nCache Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\n")


def complex_nested_data_example():
    """Example with complex nested event data."""
    print("=== Complex Nested Data Example ===")

    dedupe_processor = DeduplicationProcessor(
        window_seconds=60,
        dedupe_fields=["event", "error_details"],
        hash_algorithm="sha256",
    )

    print("Testing deduplication with complex nested structures...")

    event1 = {
        "event": "API request failed",
        "error_details": {
            "status_code": 500,
            "error_type": "InternalServerError",
            "endpoint": "/api/v1/users",
            "method": "POST",
        },
        "request_metadata": {
            "user_id": "user123",
            "session_id": "sess-abc",
            "ip_address": "192.168.1.100",
        },
        "timestamp": "2023-01-01T10:00:00Z",
    }

    event2 = {
        "event": "API request failed",
        "error_details": {
            "status_code": 500,
            "error_type": "InternalServerError",
            "endpoint": "/api/v1/users",
            "method": "POST",
        },
        "request_metadata": {
            "user_id": "user456",  # Different user
            "session_id": "sess-def",  # Different session
            "ip_address": "192.168.1.101",  # Different IP
        },
        "timestamp": "2023-01-01T10:00:01Z",  # Different timestamp
    }

    # Both events have same signature (event + error_details)
    result1 = dedupe_processor.process(None, "error", event1)
    result2 = dedupe_processor.process(None, "error", event2)

    print(f"First complex event: {'PASSED' if result1 else 'DEDUPLICATED'}")
    print(
        f"Second complex event (same error_details): {'PASSED' if result2 else 'DEDUPLICATED'}"
    )

    # Different error details should pass
    event3 = event1.copy()
    event3["error_details"] = {
        "status_code": 404,
        "error_type": "NotFoundError",
        "endpoint": "/api/v1/users",
        "method": "GET",
    }

    result3 = dedupe_processor.process(None, "error", event3)
    print(
        f"Third event (different error_details): {'PASSED' if result3 else 'DEDUPLICATED'}"
    )

    print("\n")


def memory_efficiency_example():
    """Example demonstrating memory efficiency with cache limits."""
    print("=== Memory Efficiency Example ===")

    dedupe_processor = DeduplicationProcessor(
        window_seconds=3600,  # Long window
        max_cache_size=50,  # Small cache for demo
        dedupe_fields=["event", "id"],
        hash_algorithm="md5",
    )

    print("Testing cache size limiting with max_cache_size=50...")

    # Generate more events than cache can hold
    total_events = 75
    passed_events = 0

    for i in range(total_events):
        event = {
            "event": "Bulk processing",
            "id": i,
            "data": f"payload-{i}",
            "timestamp": time.time(),
        }
        result = dedupe_processor.process(None, "info", event)
        if result is not None:
            passed_events += 1

    stats = dedupe_processor.cache_stats

    print(f"Generated {total_events} unique events")
    print(f"Events that passed: {passed_events}")
    print(f"Cache size: {stats['cache_size']} (limit: {stats['max_cache_size']})")
    print(f"Unique signatures: {stats['unique_signatures']}")
    print(f"Total events seen: {stats['total_events_seen']}")

    print("Cache automatically evicted oldest entries to stay within limit!")
    print("\n")


if __name__ == "__main__":
    """Run all deduplication examples."""
    print("🚀 FastAPI Logger - DeduplicationProcessor Examples\n")
    print("This demonstrates duplicate event removal to prevent log flooding.\n")

    try:
        basic_deduplication_example()
        different_signatures_example()
        time_window_expiration_example()
        hash_algorithm_comparison_example()
        cache_monitoring_example()
        complex_nested_data_example()
        memory_efficiency_example()

        print("✅ All examples completed successfully!")
        print("\nKey takeaways:")
        print("- Use deduplication to eliminate redundant log events")
        print("- Configure dedupe_fields to control what makes events 'identical'")
        print("- Time windows automatically expire old signatures")
        print("- Cache size limits prevent memory growth")
        print(
            "- Different hash algorithms offer different performance/security trade-offs"
        )
        print("- Monitor cache statistics to understand deduplication effectiveness")

    except Exception as e:
        print(f"❌ Error running examples: {e}")
        raise
