import asyncio
import hashlib
import json
import time
from functools import wraps
from typing import Any, Callable, Dict, Hashable, Optional


class EnricherCache:
    """Cache for expensive enricher operations."""

    def __init__(self, max_size: int = 1000, ttl: float = 300.0):
        self.max_size = max_size
        self.ttl = ttl
        self._cache: Dict[Hashable, tuple] = {}
        self._access_times: Dict[Hashable, float] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: Hashable) -> Optional[Any]:
        """Get cached value if not expired."""
        async with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                if time.time() - timestamp < self.ttl:
                    self._access_times[key] = time.time()
                    return value
                else:
                    # Expired
                    del self._cache[key]
                    del self._access_times[key]
            return None

    async def set(self, key: Hashable, value: Any) -> None:
        """Set cached value with eviction if needed."""
        async with self._lock:
            current_time = time.time()

            # Evict expired entries
            expired_keys = [
                k for k, (_, ts) in self._cache.items() if current_time - ts >= self.ttl
            ]
            for k in expired_keys:
                del self._cache[k]
                del self._access_times[k]

            # Evict LRU if at capacity
            if len(self._cache) >= self.max_size:
                lru_key = min(self._access_times.keys(), key=self._access_times.get)
                del self._cache[lru_key]
                del self._access_times[lru_key]

            self._cache[key] = (value, current_time)
            self._access_times[key] = current_time

    def cache_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        # Create deterministic key from arguments
        key_data = {"args": args, "kwargs": sorted(kwargs.items())}
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()


def cached_enricher(cache: EnricherCache, key_func: Optional[Callable] = None):
    """Decorator for caching enricher results."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = cache.cache_key(*args, **kwargs)

            # Try to get from cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result)
            return result

        return wrapper

    return decorator
