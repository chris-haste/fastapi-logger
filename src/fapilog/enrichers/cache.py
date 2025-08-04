"""Cache functionality for fapilog enrichers."""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional


@dataclass
class CacheEntry:
    """Cache entry that tracks value, timestamp, and error state."""

    value: Any
    cached_at: datetime
    is_error: bool = False
    retry_after: Optional[datetime] = None


class CacheEntryManager:
    """Manages cache entry lifecycle with optimized operations."""

    def __init__(self, retry_interval: timedelta = timedelta(minutes=5)):
        self.retry_interval = retry_interval

    def should_retry_failed_entry(
        self, entry: CacheEntry, current_time: datetime
    ) -> bool:
        """Check if a failed cache entry should be retried."""
        return (
            entry.is_error
            and entry.retry_after is not None
            and current_time >= entry.retry_after
        )

    def create_success_entry(self, value: Any, current_time: datetime) -> CacheEntry:
        """Create a successful cache entry."""
        return CacheEntry(
            value=value, cached_at=current_time, is_error=False, retry_after=None
        )

    def create_error_entry(self, current_time: datetime) -> CacheEntry:
        """Create an error cache entry with retry timestamp."""
        return CacheEntry(
            value=None,
            cached_at=current_time,
            is_error=True,
            retry_after=current_time + self.retry_interval,
        )


class AsyncSmartCache:
    """Async-first cache that eliminates race conditions with proper locking."""

    def __init__(self, retry_interval: timedelta = timedelta(minutes=5)):
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()
        self._entry_manager = CacheEntryManager(retry_interval)

    async def get_or_compute(self, key: str, compute_func: Callable) -> Any:
        """Get cached value or compute new one with async-safe retry logic."""
        async with self._lock:  # Atomic operation ensures thread safety
            entry = self._cache.get(key)
            now = datetime.now()

            # Check if we should retry a failed computation
            if entry and self._entry_manager.should_retry_failed_entry(entry, now):
                entry = None

            # Need to compute if no entry or failed entry ready for retry
            if entry is None or (
                entry.is_error and entry.retry_after and now >= entry.retry_after
            ):
                try:
                    # Handle both sync and async compute functions
                    if asyncio.iscoroutinefunction(compute_func):
                        value = await compute_func()
                    else:
                        value = compute_func()

                    # Create and store successful entry
                    self._cache[key] = self._entry_manager.create_success_entry(
                        value, now
                    )
                    return value
                except Exception:
                    # Create and store error entry
                    self._cache[key] = self._entry_manager.create_error_entry(now)
                    raise

            # Handle cached error
            if entry.is_error:
                raise RuntimeError(f"Cached error for {key}")

            return entry.value

    async def clear(self) -> None:
        """Clear all cache entries atomically."""
        async with self._lock:
            self._cache.clear()

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics atomically."""
        async with self._lock:
            total_entries = len(self._cache)
            error_entries = sum(1 for entry in self._cache.values() if entry.is_error)
            success_entries = total_entries - error_entries

            return {
                "total_entries": total_entries,
                "success_entries": success_entries,
                "error_entries": error_entries,
                "cache_hit_rate": success_entries / total_entries
                if total_entries > 0
                else 0.0,
            }


def clear_smart_cache() -> None:
    """Clear async smart cache for testing purposes.

    Note: This function has no effect since global async smart cache was removed in Issue 165.
    For container-scoped cache clearing, use:
    container.get_async_smart_cache()._cache.clear()
    """
    # This function is kept for backward compatibility but has no effect
    # since global async smart cache was removed in Issue 165
    pass
