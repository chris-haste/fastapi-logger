"""Efficient LRU Cache implementation for high-performance processors.

This module provides an O(1) LRU cache implementation to replace the O(n log n)
operations in ThrottleProcessor, achieving the 5x throughput improvement target.
"""

import asyncio
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional


class LRUCache:
    """Efficient LRU cache with O(1) operations for throttle rate tracking.

    Uses OrderedDict for O(1) get/put operations and automatic LRU eviction.
    Designed specifically for ThrottleProcessor's rate tracking needs.
    """

    def __init__(self, maxsize: int):
        """Initialize LRU cache with maximum size.

        Args:
            maxsize: Maximum number of keys to store in cache
        """
        self.maxsize = maxsize
        self.cache: OrderedDict[str, List[float]] = OrderedDict()
        self._lock = asyncio.Lock()

        # Statistics tracking
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    async def get(self, key: str) -> Optional[List[float]]:
        """Get value with O(1) complexity.

        Args:
            key: Cache key to retrieve

        Returns:
            List of timestamps for the key, or None if not found
        """
        async with self._lock:
            if key in self.cache:
                # Move to end (most recently used) - O(1) operation
                self.cache.move_to_end(key)
                self._hits += 1
                return self.cache[
                    key
                ].copy()  # Return copy to prevent external mutation

            self._misses += 1
            return None

    async def put(self, key: str, value: List[float]) -> None:
        """Put value with O(1) complexity.

        Args:
            key: Cache key
            value: List of timestamps to store
        """
        async with self._lock:
            if key in self.cache:
                # Update existing key and move to end
                self.cache.move_to_end(key)
            else:
                # Check if we need to evict
                if len(self.cache) >= self.maxsize:
                    # Remove oldest (least recently used) - O(1) operation
                    self.cache.popitem(last=False)
                    self._evictions += 1

            self.cache[key] = value.copy()  # Store copy to prevent external mutation

    async def remove(self, key: str) -> bool:
        """Remove key from cache.

        Args:
            key: Cache key to remove

        Returns:
            True if key was removed, False if key didn't exist
        """
        async with self._lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False

    async def cleanup_expired(self, window_seconds: int) -> int:
        """Clean up expired entries from all cached values.

        Args:
            window_seconds: Time window in seconds

        Returns:
            Number of entries cleaned up
        """
        current_time = time.time()
        cutoff_time = current_time - window_seconds
        cleaned_count = 0

        async with self._lock:
            keys_to_remove = []

            for key, timestamps in self.cache.items():
                # Filter out expired timestamps
                valid_timestamps = [ts for ts in timestamps if ts >= cutoff_time]

                if not valid_timestamps:
                    # No valid timestamps, mark key for removal
                    keys_to_remove.append(key)
                    cleaned_count += len(timestamps)
                elif len(valid_timestamps) < len(timestamps):
                    # Some timestamps expired, update the list
                    self.cache[key] = valid_timestamps
                    cleaned_count += len(timestamps) - len(valid_timestamps)

            # Remove empty keys
            for key in keys_to_remove:
                del self.cache[key]

        return cleaned_count

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring.

        Returns:
            Dictionary with cache performance metrics
        """
        total_requests = self._hits + self._misses
        hit_ratio = self._hits / total_requests if total_requests > 0 else 0.0

        return {
            "size": len(self.cache),
            "max_size": self.maxsize,
            "utilization": len(self.cache) / self.maxsize if self.maxsize > 0 else 0.0,
            "hits": self._hits,
            "misses": self._misses,
            "hit_ratio": hit_ratio,
            "evictions": self._evictions,
        }

    async def get_all_keys(self) -> List[str]:
        """Get all cache keys for monitoring purposes.

        Returns:
            List of all cache keys
        """
        async with self._lock:
            return list(self.cache.keys())

    def size(self) -> int:
        """Get current cache size (non-async for simple checks).

        Returns:
            Current number of keys in cache
        """
        return len(self.cache)

    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self.cache.clear()
            self._hits = 0
            self._misses = 0
            self._evictions = 0
