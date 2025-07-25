"""Example demonstrating ThrottleProcessor for rate limiting log events.

This example shows how to use the ThrottleProcessor to prevent log flooding
by rate-limiting events per source/key.
"""

import time

from fapilog import configure_logging, log
from fapilog._internal.processors import ThrottleProcessor
from fapilog.settings import LoggingSettings


def basic_throttling_example():
    """Basic throttling example with drop strategy."""
    print("=== Basic Throttling Example (Drop Strategy) ===")

    # Configure logging with throttling enabled
    settings = LoggingSettings(
        enable_throttling=True,
        throttle_max_rate=5,  # Max 5 events per minute per source
        throttle_window_seconds=60,
        throttle_key_field="service_name",
        throttle_strategy="drop",
        sinks=["stdout"],
        json_console="pretty",
    )

    configure_logging(settings=settings)

    print("Sending 8 events (rate limit is 5 per minute)...")
    print("Expected: First 5 events pass, next 3 are dropped\n")

    # This will be throttled after 5 events per minute
    for i in range(8):
        log.error(
            "Service error occurred",
            service_name="payment-service",
            error_count=i + 1,
            timestamp=time.time(),
        )
        print(f"Sent event {i + 1}")

    print("\n")


def sample_strategy_example():
    """Example using sample strategy for throttling."""
    print("=== Throttling with Sample Strategy ===")

    # Create a throttle processor directly for demonstration
    throttle_processor = ThrottleProcessor(
        max_rate=3,
        window_seconds=60,
        key_field="service",
        strategy="sample",  # Sample instead of drop
    )

    print("Sending 6 events with sample strategy (rate limit 3)...")
    print("Expected: First 3 pass, next 3 are sampled (some may pass)\n")

    for i in range(6):
        event = {
            "level": "ERROR",
            "service": "database-service",
            "message": f"Connection timeout #{i + 1}",
            "timestamp": time.time(),
        }

        result = throttle_processor.process(None, "error", event)

        if result is not None:
            print(f"✅ Event {i + 1}: PASSED")
        else:
            print(f"❌ Event {i + 1}: THROTTLED")

    print("\n")


def multi_service_throttling_example():
    """Example showing per-service rate limiting."""
    print("=== Multi-Service Throttling Example ===")

    throttle_processor = ThrottleProcessor(
        max_rate=2, window_seconds=60, key_field="service", strategy="drop"
    )

    services = ["auth-service", "payment-service", "notification-service"]

    print("Each service has its own rate limit of 2 events per minute...\n")

    for service in services:
        print(f"Testing {service}:")

        for i in range(3):  # Send 3 events per service
            event = {
                "level": "WARN",
                "service": service,
                "message": f"Service warning #{i + 1}",
                "timestamp": time.time(),
            }

            result = throttle_processor.process(None, "warn", event)

            if result is not None:
                print(f"  ✅ Event {i + 1}: PASSED")
            else:
                print(f"  ❌ Event {i + 1}: THROTTLED")

        print()


def time_window_example():
    """Example showing time window expiration."""
    print("=== Time Window Expiration Example ===")

    throttle_processor = ThrottleProcessor(
        max_rate=2,
        window_seconds=2,  # Very short window for demo
        key_field="source",
        strategy="drop",
    )

    print("Rate limit: 2 events per 2 seconds")
    print("Sending 2 events, then waiting, then sending 2 more...\n")

    # First batch - should both pass
    for i in range(2):
        event = {
            "level": "INFO",
            "source": "test-service",
            "message": f"First batch event {i + 1}",
        }

        result = throttle_processor.process(None, "info", event)
        print(f"First batch event {i + 1}: {'PASSED' if result else 'THROTTLED'}")

    # Third event - should be throttled
    event = {
        "level": "INFO",
        "source": "test-service",
        "message": "Third event (should be throttled)",
    }
    result = throttle_processor.process(None, "info", event)
    print(f"Third event: {'PASSED' if result else 'THROTTLED'}")

    print("\nWaiting 2.5 seconds for window to expire...")
    time.sleep(2.5)

    # After window expiration - should pass again
    for i in range(2):
        event = {
            "level": "INFO",
            "source": "test-service",
            "message": f"After expiration event {i + 1}",
        }

        result = throttle_processor.process(None, "info", event)
        print(f"After expiration event {i + 1}: {'PASSED' if result else 'THROTTLED'}")

    print("\n")


def monitoring_example():
    """Example showing how to monitor current rates."""
    print("=== Rate Monitoring Example ===")

    throttle_processor = ThrottleProcessor(
        max_rate=5, window_seconds=60, key_field="service", strategy="drop"
    )

    services = ["service-a", "service-b", "service-c"]

    # Generate different amounts of events per service
    event_counts = [2, 4, 6]

    for service, count in zip(services, event_counts):
        print(f"Generating {count} events for {service}")

        for i in range(count):
            event = {"level": "INFO", "service": service, "message": f"Event {i + 1}"}
            throttle_processor.process(None, "info", event)

    # Check current rates
    print("\nCurrent rates per service:")
    rates = throttle_processor.get_current_rates()

    for service, rate in rates.items():
        status = "OK" if rate < 5 else "THROTTLED"
        print(f"  {service}: {rate}/5 events ({status})")

    print("\n")


def custom_key_field_example():
    """Example using a custom field for throttling."""
    print("=== Custom Key Field Example ===")

    # Throttle by user_id instead of service
    throttle_processor = ThrottleProcessor(
        max_rate=3,
        window_seconds=60,
        key_field="user_id",  # Custom key field
        strategy="drop",
    )

    print("Throttling by user_id (limit: 3 events per user per minute)\n")

    # Different users should have separate limits
    users = ["user123", "user456", "user123"]  # user123 appears twice

    for user in users:
        for attempt in range(2):
            event = {
                "level": "INFO",
                "user_id": user,
                "action": "page_view",
                "page": "/dashboard",
                "attempt": attempt + 1,
            }

            result = throttle_processor.process(None, "info", event)
            status = "PASSED" if result else "THROTTLED"
            print(f"{user} attempt {attempt + 1}: {status}")

    print("\nSending more events for user123 (should hit rate limit):")

    # Send more events for user123 to trigger throttling
    for i in range(3):
        event = {
            "level": "INFO",
            "user_id": "user123",
            "action": "api_call",
            "endpoint": f"/api/data/{i}",
        }

        result = throttle_processor.process(None, "info", event)
        status = "PASSED" if result else "THROTTLED"
        print(f"user123 API call {i + 1}: {status}")

    print("\n")


if __name__ == "__main__":
    """Run all throttling examples."""
    print("🚀 FastAPI Logger - ThrottleProcessor Examples\n")
    print("This demonstrates rate limiting functionality to prevent log flooding.\n")

    try:
        basic_throttling_example()
        sample_strategy_example()
        multi_service_throttling_example()
        time_window_example()
        monitoring_example()
        custom_key_field_example()

        print("✅ All examples completed successfully!")
        print("\nKey takeaways:")
        print("- Use throttling to prevent log flooding from specific sources")
        print("- Different strategies: 'drop' (discard) vs 'sample' (probabilistic)")
        print("- Rate limits are applied per key (configurable field)")
        print("- Time windows automatically expire old events")
        print("- Monitor current rates to understand system behavior")

    except Exception as e:
        print(f"❌ Error running examples: {e}")
        raise
