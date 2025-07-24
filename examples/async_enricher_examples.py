"""Example async enrichers showing database, API, and Redis integration."""

import asyncio
from typing import Any, Dict

import aiohttp

# Note: These imports would require the optional dependencies
# import aioredis
# import asyncpg
from fapilog._internal.async_enricher import AsyncEnricher
from fapilog._internal.circuit_breaker import CircuitBreaker
from fapilog._internal.enricher_cache import EnricherCache


class DatabaseUserEnricher(AsyncEnricher):
    """Enrich with user data from PostgreSQL database."""

    def __init__(self, database_url: str, **kwargs):
        super().__init__("database_user", **kwargs)
        self.database_url = database_url
        self.pool = None
        self.cache = EnricherCache(max_size=1000, ttl=300)
        self.circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)

    async def _startup(self) -> None:
        """Initialize database connection pool."""
        try:
            import asyncpg

            self.pool = await asyncpg.create_pool(
                self.database_url, min_size=2, max_size=10, command_timeout=5
            )
        except ImportError:
            raise ImportError("asyncpg is required for DatabaseUserEnricher")

    async def _shutdown(self) -> None:
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()

    async def _health_check(self) -> bool:
        """Check database connectivity."""
        if not self.pool:
            return False

        try:
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception:
            return False

    async def _fetch_user_data(self, user_id: str) -> dict:
        """Fetch user data with circuit breaker protection."""

        async def fetch():
            if not self.pool:
                return {}
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT name, email, department FROM users WHERE id = $1", user_id
                )
                return dict(row) if row else {}

        return await self.circuit_breaker.call(fetch)

    async def enrich_async(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enrich with user data from database."""
        user_id = event_dict.get("user_id")
        if not user_id:
            return event_dict

        try:
            # Use cache key from user_id
            cache_key = f"user:{user_id}"
            cached_data = await self.cache.get(cache_key)

            if cached_data is not None:
                event_dict.update(cached_data)
            else:
                user_data = await self._fetch_user_data(user_id)
                if user_data:
                    await self.cache.set(cache_key, user_data)
                    event_dict.update(user_data)
        except Exception as e:
            event_dict["user_enrichment_error"] = str(e)

        return event_dict


class APIServiceEnricher(AsyncEnricher):
    """Enrich with data from external API service."""

    def __init__(self, api_base_url: str, api_key: str, **kwargs):
        super().__init__("api_service", **kwargs)
        self.api_base_url = api_base_url
        self.api_key = api_key
        self.session = None
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

    async def _startup(self) -> None:
        """Initialize HTTP session."""
        timeout = aiohttp.ClientTimeout(total=10, connect=5)
        self.session = aiohttp.ClientSession(
            timeout=timeout, headers={"Authorization": f"Bearer {self.api_key}"}
        )

    async def _shutdown(self) -> None:
        """Close HTTP session."""
        if self.session:
            await self.session.close()

    async def _health_check(self) -> bool:
        """Check API service health."""
        if not self.session:
            return False
        try:
            async with self.session.get(f"{self.api_base_url}/health") as response:
                return response.status == 200
        except Exception:
            return False

    async def enrich_async(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enrich with data from API service."""
        request_id = event_dict.get("request_id")
        if not request_id or not self.session:
            return event_dict

        async def fetch_request_data():
            async with self.session.get(
                f"{self.api_base_url}/requests/{request_id}"
            ) as response:
                if response.status == 200:
                    return await response.json()
                return {}

        try:
            data = await self.circuit_breaker.call(fetch_request_data)
            if data:
                event_dict["request_context"] = data
        except Exception as e:
            event_dict["api_enrichment_error"] = str(e)

        return event_dict


class RedisEnricher(AsyncEnricher):
    """Enrich with data from Redis cache."""

    def __init__(self, redis_url: str, **kwargs):
        super().__init__("redis_enricher", **kwargs)
        self.redis_url = redis_url
        self.redis = None
        self.circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)

    async def _startup(self) -> None:
        """Initialize Redis connection."""
        try:
            import aioredis

            self.redis = await aioredis.from_url(self.redis_url)
        except ImportError:
            raise ImportError("aioredis is required for RedisEnricher")

    async def _shutdown(self) -> None:
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()

    async def _health_check(self) -> bool:
        """Check Redis connectivity."""
        if not self.redis:
            return False
        try:
            await self.redis.ping()
            return True
        except Exception:
            return False

    async def enrich_async(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enrich with data from Redis."""
        session_id = event_dict.get("session_id")
        if not session_id or not self.redis:
            return event_dict

        async def fetch_session_data():
            session_data = await self.redis.get(f"session:{session_id}")
            if session_data:
                import json

                return json.loads(session_data)
            return {}

        try:
            data = await self.circuit_breaker.call(fetch_session_data)
            if data:
                event_dict["session_data"] = data
        except Exception as e:
            event_dict["redis_enrichment_error"] = str(e)

        return event_dict


class SlowOperationEnricher(AsyncEnricher):
    """Example enricher that simulates slow operations with caching."""

    def __init__(self, operation_delay: float = 2.0, **kwargs):
        super().__init__("slow_operation", **kwargs)
        self.operation_delay = operation_delay
        self.cache = EnricherCache(max_size=500, ttl=120)

    async def _startup(self) -> None:
        """No startup needed for this example."""
        pass

    async def _shutdown(self) -> None:
        """No shutdown needed for this example."""
        pass

    async def _health_check(self) -> bool:
        """Always healthy for this example."""
        return True

    async def enrich_async(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enrich with simulated slow operation."""
        operation_key = event_dict.get("operation_key")
        if not operation_key:
            return event_dict

        # Check cache first
        cache_key = f"slow_op:{operation_key}"
        cached_result = await self.cache.get(cache_key)

        if cached_result is not None:
            event_dict["slow_operation_result"] = cached_result
            event_dict["from_cache"] = True
        else:
            # Simulate slow operation
            await asyncio.sleep(self.operation_delay)
            result = f"processed_{operation_key}_{int(asyncio.get_event_loop().time())}"

            # Cache the result
            await self.cache.set(cache_key, result)
            event_dict["slow_operation_result"] = result
            event_dict["from_cache"] = False

        return event_dict


# Usage examples
def create_example_enrichers():
    """Create example async enrichers for demonstration."""

    # Database enricher (requires asyncpg)
    database_enricher = DatabaseUserEnricher(
        database_url="postgresql://user:pass@localhost/db"
    )

    # API enricher
    api_enricher = APIServiceEnricher(
        api_base_url="https://api.company.com", api_key="your-api-key"
    )

    # Redis enricher (requires aioredis)
    redis_enricher = RedisEnricher(redis_url="redis://localhost:6379")

    # Slow operation enricher with caching
    slow_enricher = SlowOperationEnricher(operation_delay=1.0)

    return [database_enricher, api_enricher, redis_enricher, slow_enricher]


async def example_usage():
    """Example of how to use async enrichers."""
    enrichers = create_example_enrichers()

    # Example with lifecycle management
    for enricher in enrichers:
        try:
            await enricher.startup()
            print(f"Started {enricher.name}")

            # Health check
            is_healthy = await enricher.health_check()
            print(f"{enricher.name} health: {is_healthy}")

        except Exception as e:
            print(f"Failed to start {enricher.name}: {e}")

    # Clean shutdown
    for enricher in enrichers:
        try:
            await enricher.shutdown()
            print(f"Shutdown {enricher.name}")
        except Exception as e:
            print(f"Error shutting down {enricher.name}: {e}")


if __name__ == "__main__":
    asyncio.run(example_usage())
