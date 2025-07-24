"""
Example demonstrating async enricher integration with fapilog main pipeline.

This example shows how to:
1. Create custom async enrichers
2. Register them with the enricher registry
3. Use them alongside sync enrichers in the main logging pipeline
4. Configure them via settings and URIs
"""

import asyncio
import time

from fapilog._internal.async_enricher import AsyncEnricher
from fapilog.container import LoggingContainer
from fapilog.enrichers import register_enricher_advanced
from fapilog.settings import LoggingSettings


# Example 1: Custom Async Enricher
@register_enricher_advanced(
    name="api-user-enricher",
    description="Enriches logs with user context from API",
    priority=50,
    async_capable=True,
)
class APIUserEnricher(AsyncEnricher):
    """Example async enricher that fetches user context from an API."""

    def __init__(self, api_url="http://localhost:8000", timeout=3.0):
        super().__init__("api-user-enricher")
        self.api_url = api_url
        self.timeout = timeout
        self.cache = {}

    async def _startup(self):
        """Initialize connections, caches, etc."""
        print(f"🚀 Starting APIUserEnricher with API: {self.api_url}")
        # Simulate connection setup
        await asyncio.sleep(0.1)

    async def _shutdown(self):
        """Clean up resources."""
        print("🛑 Shutting down APIUserEnricher")
        self.cache.clear()

    async def _health_check(self):
        """Check if the enricher is healthy."""
        return True  # Simulate healthy state

    async def enrich_async(self, logger, method_name, event_dict):
        """Enrich log with user context from API."""
        user_id = event_dict.get("user_id")
        if not user_id:
            return event_dict

        # Check cache first
        if user_id in self.cache:
            user_data = self.cache[user_id]
        else:
            # Simulate API call
            await asyncio.sleep(0.05)  # Simulate network latency
            user_data = {
                "username": f"user_{user_id}",
                "role": "admin" if int(user_id) % 2 == 0 else "user",
                "department": "engineering",
            }
            self.cache[user_id] = user_data

        return {**event_dict, "user": user_data, "enriched_by_async": True}


# Example 2: Async Database Enricher
@register_enricher_advanced(
    name="db-metadata-enricher",
    description="Enriches logs with database metadata",
    priority=75,
    dependencies=["api-user-enricher"],  # Run after user enricher
    async_capable=True,
)
class DatabaseMetadataEnricher(AsyncEnricher):
    """Example async enricher that adds database metadata."""

    def __init__(self, db_url="postgresql://localhost:5432/app", timeout=2.0):
        super().__init__("db-metadata-enricher")
        self.db_url = db_url
        self.timeout = timeout

    async def _startup(self):
        """Initialize database connection."""
        print(f"🗄️ Connecting to database: {self.db_url}")
        await asyncio.sleep(0.1)

    async def _shutdown(self):
        """Close database connection."""
        print("🗄️ Closing database connection")

    async def _health_check(self):
        """Check database connection health."""
        return True

    async def enrich_async(self, logger, method_name, event_dict):
        """Add database metadata to logs."""
        # Simulate database query
        await asyncio.sleep(0.02)

        return {
            **event_dict,
            "db_metadata": {
                "connection_pool_size": 10,
                "active_connections": 3,
                "last_query_time": time.time(),
            },
            "db_enriched": True,
        }


# Example 3: Sync Enricher for comparison
@register_enricher_advanced(
    name="request-id-enricher",
    description="Adds request ID to logs",
    priority=25,  # Higher priority (runs first)
    async_capable=False,
)
class RequestIDEnricher:
    """Example sync enricher for comparison."""

    def __init__(self):
        self.request_counter = 0

    def __call__(self, logger, method_name, event_dict):
        """Add request ID to log."""
        if "request_id" not in event_dict:
            self.request_counter += 1
            event_dict["request_id"] = f"req_{self.request_counter:06d}"

        return {**event_dict, "sync_enriched": True}


async def main():
    """Demonstrate async enricher integration."""

    print("=== Async Enricher Integration Example ===\n")

    # Example 1: Basic Usage
    print("1. Basic async enricher integration:")

    settings = LoggingSettings(
        level="INFO",
        json_console=True,
        # Mix of sync and async enrichers
        enrichers=[
            "request-id-enricher://",
            "api-user-enricher://localhost:8000?timeout=3.0",
            "db-metadata-enricher://postgres:5432/myapp?timeout=2.0",
        ],
    )

    container = LoggingContainer(settings)
    logger = container.configure()

    # Test logging with enrichers
    logger.info("User login", user_id="123", action="login")
    logger.warning("Database slow query", user_id="456", query_time=1.5)
    logger.error("API error", user_id="789", error_code="AUTH_FAILED")

    print()

    # Example 2: Manual Enricher Registration
    print("2. Manual enricher registration:")

    # Create a simple async enricher inline
    @register_enricher_advanced(
        name="timestamp-enricher",
        description="Adds high precision timestamp",
        priority=10,
        async_capable=True,
    )
    class TimestampEnricher(AsyncEnricher):
        def __init__(self):
            super().__init__("timestamp-enricher")

        async def _startup(self):
            pass

        async def _shutdown(self):
            pass

        async def _health_check(self):
            return True

        async def enrich_async(self, logger, method_name, event_dict):
            await asyncio.sleep(0.001)  # Simulate precision timing
            return {
                **event_dict,
                "precise_timestamp": time.time_ns(),
                "timestamp_enriched": True,
            }

    # Use it in a new container
    settings2 = LoggingSettings(
        level="DEBUG", json_console=True, enrichers=["timestamp-enricher://"]
    )

    container2 = LoggingContainer(settings2)
    logger2 = container2.configure()

    logger2.debug("High precision event", event_type="measurement")

    print()

    # Example 3: Error Handling
    print("3. Error handling with async enrichers:")

    @register_enricher_advanced(
        name="failing-enricher",
        description="Enricher that sometimes fails",
        priority=60,
        async_capable=True,
    )
    class FailingEnricher(AsyncEnricher):
        def __init__(self):
            super().__init__("failing-enricher")
            self.call_count = 0

        async def _startup(self):
            pass

        async def _shutdown(self):
            pass

        async def _health_check(self):
            return True

        async def enrich_async(self, logger, method_name, event_dict):
            self.call_count += 1
            if self.call_count % 3 == 0:
                raise Exception("Simulated enricher failure")

            return {**event_dict, "failure_test": True, "call_count": self.call_count}

    settings3 = LoggingSettings(
        level="INFO", json_console=True, enrichers=["failing-enricher://"]
    )

    container3 = LoggingContainer(settings3)
    logger3 = container3.configure()

    # Test error resilience
    for i in range(5):
        logger3.info(f"Test message {i + 1}", test_id=i + 1)

    print()

    # Cleanup - graceful shutdown
    print("4. Graceful shutdown:")
    await container.shutdown()
    await container2.shutdown()
    await container3.shutdown()

    print("✅ All containers shut down gracefully")
    print("\n=== Example Complete ===")


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())
