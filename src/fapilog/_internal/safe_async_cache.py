"""Thread-safe async cache with atomic operations.

This module provides atomic cache operations to eliminate race conditions
in cache access patterns. It replaces dangerous lock-free optimizations
with proper async-safe operations.
"""

import asyncio
import logging
import time
from collections import OrderedDict
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    TypeVar,
)

logger = logging.getLogger(__name__)

K = TypeVar("K")
V = TypeVar("V")


class SafeAsyncCache(Generic[K, V]):
    """Thread-safe async cache with atomic operations.

    Provides atomic get-or-create operations and size limit enforcement
    to replace race condition-prone cache patterns in processors.
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: Optional[float] = None):
        """Initialize cache with size limits and optional TTL.

        Args:
            max_size: Maximum number of cache entries
            ttl_seconds: Time-to-live for cache entries (None = no expiration)
        """
        self._cache: OrderedDict[K, tuple[V, float]] = OrderedDict()
        self._lock = asyncio.Lock()
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._access_times: Dict[K, float] = {}

    async def get_or_create(self, key: K, factory: Callable[[], Awaitable[V]]) -> V:
        """Atomic get-or-create operation with proper locking.

        Args:
            key: Cache key
            factory: Async function to create value if not exists

        Returns:
            V: The cached or newly created value
        """
        current_time = time.time()

        async with self._lock:
            # Check if key exists and is not expired
            if key in self._cache:
                value, created_time = self._cache[key]

                # Check TTL expiration
                if (
                    self._ttl_seconds is None
                    or (current_time - created_time) <= self._ttl_seconds
                ):
                    # Update access time for LRU
                    self._access_times[key] = current_time
                    # Move to end for OrderedDict LRU
                    self._cache.move_to_end(key)
                    logger.debug(f"Cache hit for key: {key}")
                    return value
                else:
                    # Entry expired, remove it
                    del self._cache[key]
                    self._access_times.pop(key, None)
                    logger.debug(f"Cache entry expired for key: {key}")

            # Create new value
            logger.debug(f"Cache miss for key: {key}, creating new value")
            value = await factory()

            # Store with creation timestamp
            self._cache[key] = (value, current_time)
            self._access_times[key] = current_time

            # Enforce size limit with LRU eviction
            await self._enforce_size_limit()

            return value

    async def get(self, key: K) -> Optional[V]:
        """Get value from cache if exists and not expired.

        Args:
            key: Cache key

        Returns:
            Optional[V]: The cached value or None if not found/expired
        """
        current_time = time.time()

        async with self._lock:
            if key not in self._cache:
                return None

            value, created_time = self._cache[key]

            # Check TTL expiration
            if (
                self._ttl_seconds is not None
                and (current_time - created_time) > self._ttl_seconds
            ):
                # Entry expired, remove it
                del self._cache[key]
                self._access_times.pop(key, None)
                logger.debug(f"Cache entry expired for key: {key}")
                return None

            # Update access time and move to end
            self._access_times[key] = current_time
            self._cache.move_to_end(key)
            logger.debug(f"Cache hit for key: {key}")
            return value

    async def set(self, key: K, value: V) -> None:
        """Set value in cache with atomic operation.

        Args:
            key: Cache key
            value: Value to cache
        """
        current_time = time.time()

        async with self._lock:
            self._cache[key] = (value, current_time)
            self._access_times[key] = current_time

            # Enforce size limit
            await self._enforce_size_limit()
            logger.debug(f"Cache set for key: {key}")

    async def delete(self, key: K) -> bool:
        """Delete key from cache.

        Args:
            key: Cache key to delete

        Returns:
            bool: True if key was deleted, False if not found
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._access_times.pop(key, None)
                logger.debug(f"Cache deleted key: {key}")
                return True
            return False

    async def clear(self) -> None:
        """Clear all cache entries atomically."""
        async with self._lock:
            self._cache.clear()
            self._access_times.clear()
            logger.debug("Cache cleared")

    async def _enforce_size_limit(self) -> None:
        """Enforce maximum cache size with LRU eviction."""
        if len(self._cache) <= self._max_size:
            return

        # Remove oldest entries (LRU) until we're under the limit
        entries_to_remove = len(self._cache) - self._max_size

        for _ in range(entries_to_remove):
            if self._cache:
                # Remove the oldest entry (first in OrderedDict)
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self._access_times.pop(oldest_key, None)
                logger.debug(f"Evicted LRU cache entry: {oldest_key}")

    async def cleanup_expired(self) -> int:
        """Remove all expired entries from cache.

        Returns:
            int: Number of entries removed
        """
        if self._ttl_seconds is None:
            return 0

        current_time = time.time()
        removed_count = 0

        async with self._lock:
            expired_keys = []

            for key, (_, created_time) in self._cache.items():
                if (current_time - created_time) > self._ttl_seconds:
                    expired_keys.append(key)

            for key in expired_keys:
                del self._cache[key]
                self._access_times.pop(key, None)
                removed_count += 1
                logger.debug(f"Cleaned up expired cache entry: {key}")

        return removed_count

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with cache statistics
        """
        current_time = time.time()
        expired_count = 0

        if self._ttl_seconds is not None:
            for _, created_time in self._cache.values():
                if (current_time - created_time) > self._ttl_seconds:
                    expired_count += 1

        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "utilization": len(self._cache) / self._max_size
            if self._max_size > 0
            else 0.0,
            "expired_entries": expired_count,
            "ttl_seconds": self._ttl_seconds,
        }

    async def get_all_keys(self) -> List[K]:
        """Get all cache keys atomically.

        Returns:
            List of all cache keys
        """
        async with self._lock:
            return list(self._cache.keys())

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, _exc_type, _exc_val, _exc_tb):
        """Async context manager exit with cleanup."""
        if self._ttl_seconds is not None:
            await self.cleanup_expired()
