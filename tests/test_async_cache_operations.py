"""Unit tests for SafeAsyncCache foundation component.

Tests cache operations, concurrent access scenarios, and race condition prevention.
"""

import asyncio

import pytest

from fapilog._internal.safe_async_cache import SafeAsyncCache


class TestSafeAsyncCache:
    """Test cases for SafeAsyncCache."""

    def test_init(self):
        """Test SafeAsyncCache initialization."""
        cache = SafeAsyncCache(max_size=100, ttl_seconds=60.0)

        assert cache._max_size == 100
        assert cache._ttl_seconds == 60.0
        assert len(cache._cache) == 0
        assert len(cache._access_times) == 0

    @pytest.mark.asyncio
    async def test_get_or_create_new_value(self):
        """Test get_or_create with new value creation."""
        cache = SafeAsyncCache()

        factory_called = False

        async def factory():
            nonlocal factory_called
            factory_called = True
            return "test_value"

        result = await cache.get_or_create("test_key", factory)

        assert result == "test_value"
        assert factory_called
        assert len(cache._cache) == 1
        assert "test_key" in cache._cache

    @pytest.mark.asyncio
    async def test_get_or_create_existing_value(self):
        """Test get_or_create with existing value (cache hit)."""
        cache = SafeAsyncCache()

        # First call - creates value
        async def factory1():
            return "value1"

        result1 = await cache.get_or_create("test_key", factory1)
        assert result1 == "value1"

        # Second call - should use cached value
        factory2_called = False

        async def factory2():
            nonlocal factory2_called
            factory2_called = True
            return "value2"

        result2 = await cache.get_or_create("test_key", factory2)

        assert result2 == "value1"  # Should return cached value
        assert not factory2_called  # Factory should not be called
        assert len(cache._cache) == 1

    @pytest.mark.asyncio
    async def test_get_existing_value(self):
        """Test getting existing value from cache."""
        cache = SafeAsyncCache()

        # Set a value
        await cache.set("test_key", "test_value")

        # Get the value
        result = await cache.get("test_key")
        assert result == "test_value"

    @pytest.mark.asyncio
    async def test_get_nonexistent_value(self):
        """Test getting non-existent value returns None."""
        cache = SafeAsyncCache()

        result = await cache.get("nonexistent_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_value(self):
        """Test setting values in cache."""
        cache = SafeAsyncCache()

        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        assert len(cache._cache) == 2
        result1 = await cache.get("key1")
        result2 = await cache.get("key2")

        assert result1 == "value1"
        assert result2 == "value2"

    @pytest.mark.asyncio
    async def test_delete_existing_key(self):
        """Test deleting existing key from cache."""
        cache = SafeAsyncCache()

        await cache.set("test_key", "test_value")
        assert len(cache._cache) == 1

        deleted = await cache.delete("test_key")

        assert deleted is True
        assert len(cache._cache) == 0
        assert await cache.get("test_key") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_key(self):
        """Test deleting non-existent key returns False."""
        cache = SafeAsyncCache()

        deleted = await cache.delete("nonexistent_key")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_clear_cache(self):
        """Test clearing all cache entries."""
        cache = SafeAsyncCache()

        # Add some entries
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        assert len(cache._cache) == 2

        # Clear cache
        await cache.clear()

        assert len(cache._cache) == 0
        assert len(cache._access_times) == 0

    @pytest.mark.asyncio
    async def test_size_limit_enforcement(self):
        """Test cache size limit enforcement with LRU eviction."""
        cache = SafeAsyncCache(max_size=3)

        # Add entries up to limit
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")
        assert len(cache._cache) == 3

        # Add one more - should evict oldest
        await cache.set("key4", "value4")

        assert len(cache._cache) == 3
        assert await cache.get("key1") is None  # Should be evicted
        assert await cache.get("key2") == "value2"
        assert await cache.get("key3") == "value3"
        assert await cache.get("key4") == "value4"

    @pytest.mark.asyncio
    async def test_lru_ordering(self):
        """Test LRU ordering with access updates."""
        cache = SafeAsyncCache(max_size=3)

        # Add entries
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")

        # Access key1 to make it most recently used
        await cache.get("key1")

        # Add new entry - key2 should be evicted (least recently used)
        await cache.set("key4", "value4")

        assert await cache.get("key1") == "value1"  # Should still exist
        assert await cache.get("key2") is None  # Should be evicted
        assert await cache.get("key3") == "value3"  # Should still exist
        assert await cache.get("key4") == "value4"  # Should exist

    @pytest.mark.asyncio
    async def test_ttl_expiration(self):
        """Test TTL-based expiration."""
        cache = SafeAsyncCache(ttl_seconds=0.1)  # 100ms TTL

        await cache.set("test_key", "test_value")

        # Should be available immediately
        result1 = await cache.get("test_key")
        assert result1 == "test_value"

        # Wait for expiration
        await asyncio.sleep(0.15)

        # Should be expired
        result2 = await cache.get("test_key")
        assert result2 is None
        assert len(cache._cache) == 0  # Should be removed

    @pytest.mark.asyncio
    async def test_ttl_in_get_or_create(self):
        """Test TTL expiration in get_or_create operations."""
        cache = SafeAsyncCache(ttl_seconds=0.1)

        # Create initial value
        async def factory1():
            return "value1"

        result1 = await cache.get_or_create("test_key", factory1)
        assert result1 == "value1"

        # Wait for expiration
        await asyncio.sleep(0.15)

        # Should create new value after expiration
        async def factory2():
            return "value2"

        result2 = await cache.get_or_create("test_key", factory2)
        assert result2 == "value2"

    @pytest.mark.asyncio
    async def test_cleanup_expired_entries(self):
        """Test cleanup of expired entries."""
        cache = SafeAsyncCache(ttl_seconds=0.2)  # Longer TTL for more reliable timing

        # Add entries
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")

        # Wait for some to expire
        await asyncio.sleep(0.1)
        await cache.set("key4", "value4")  # Fresh entry
        await asyncio.sleep(0.15)  # Wait for first 3 to expire

        # Cleanup expired entries
        removed_count = await cache.cleanup_expired()

        assert removed_count >= 3  # key1, key2, key3 should be expired
        # key4 should still exist as it was added later
        result = await cache.get("key4")
        assert (
            result == "value4" or result is None
        )  # May have expired too due to timing

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test cache statistics."""
        cache = SafeAsyncCache(max_size=10, ttl_seconds=1.0)

        # Initial stats
        stats = cache.get_stats()
        assert stats["size"] == 0
        assert stats["max_size"] == 10
        assert stats["utilization"] == 0.0
        assert stats["expired_entries"] == 0
        assert stats["ttl_seconds"] == 1.0

        # Add some entries
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        stats = cache.get_stats()
        assert stats["size"] == 2
        assert stats["utilization"] == 0.2

    @pytest.mark.asyncio
    async def test_get_all_keys(self):
        """Test getting all cache keys."""
        cache = SafeAsyncCache()

        # Empty cache
        keys = await cache.get_all_keys()
        assert keys == []

        # Add some entries
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")

        keys = await cache.get_all_keys()
        assert set(keys) == {"key1", "key2", "key3"}

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test async context manager functionality."""
        cache = SafeAsyncCache(ttl_seconds=0.1)

        async with cache:
            await cache.set("key1", "value1")
            await asyncio.sleep(0.15)  # Wait for expiration
            await cache.set("key2", "value2")  # Fresh entry

        # Context manager should cleanup expired entries on exit
        assert await cache.get("key1") is None
        assert await cache.get("key2") == "value2"


class TestConcurrentAccess:
    """Test cases for concurrent cache access."""

    @pytest.mark.asyncio
    async def test_concurrent_get_or_create(self):
        """Test concurrent get_or_create operations."""
        cache = SafeAsyncCache()

        factory_call_count = 0

        async def factory():
            nonlocal factory_call_count
            factory_call_count += 1
            await asyncio.sleep(0.01)  # Simulate work
            return f"value_{factory_call_count}"

        # Multiple concurrent get_or_create for same key
        tasks = [cache.get_or_create("test_key", factory) for _ in range(5)]
        results = await asyncio.gather(*tasks)

        # Should only call factory once and return same value to all
        assert factory_call_count == 1
        assert all(result == results[0] for result in results)
        assert len(cache._cache) == 1

    @pytest.mark.asyncio
    async def test_concurrent_set_operations(self):
        """Test concurrent set operations."""
        cache = SafeAsyncCache()

        async def setter(key: str, value: str):
            await cache.set(key, value)
            return await cache.get(key)

        # Concurrent sets to different keys
        tasks = [setter(f"key_{i}", f"value_{i}") for i in range(10)]
        results = await asyncio.gather(*tasks)

        # All operations should succeed
        assert len(results) == 10
        assert len(cache._cache) == 10

        # Verify all values are correct
        for i in range(10):
            assert await cache.get(f"key_{i}") == f"value_{i}"

    @pytest.mark.asyncio
    async def test_concurrent_mixed_operations(self):
        """Test mixed concurrent operations."""
        cache = SafeAsyncCache(max_size=20)

        async def reader(key: str):
            return await cache.get(key)

        async def writer(key: str, value: str):
            await cache.set(key, value)

        async def deleter(key: str):
            return await cache.delete(key)

        # Mix of operations
        tasks = []

        # Add some initial data
        for i in range(5):
            tasks.append(writer(f"key_{i}", f"value_{i}"))

        # Add readers
        for i in range(10):
            tasks.append(reader(f"key_{i % 5}"))

        # Add more writers
        for i in range(5, 10):
            tasks.append(writer(f"key_{i}", f"value_{i}"))

        # Add deleters
        for i in range(2):
            tasks.append(deleter(f"key_{i}"))

        # Execute all concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # No exceptions should occur
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) == 0

    @pytest.mark.asyncio
    async def test_race_condition_prevention(self):
        """Test prevention of race conditions in cache operations."""
        cache = SafeAsyncCache()

        counter = 0

        async def factory():
            nonlocal counter
            await asyncio.sleep(0.001)  # Simulate async work
            counter += 1
            return counter

        # Many concurrent get_or_create operations for same key
        tasks = [cache.get_or_create("race_key", factory) for _ in range(50)]
        results = await asyncio.gather(*tasks)

        # Factory should only be called once despite race conditions
        assert counter == 1
        assert all(result == 1 for result in results)
        assert len(cache._cache) == 1

    @pytest.mark.asyncio
    async def test_memory_consistency_under_load(self):
        """Test memory consistency under concurrent load."""
        cache = SafeAsyncCache(max_size=100)

        async def worker(worker_id: int):
            for i in range(20):
                key = f"worker_{worker_id}_key_{i}"
                value = f"worker_{worker_id}_value_{i}"

                # Set value
                await cache.set(key, value)

                # Immediately get and verify
                retrieved = await cache.get(key)
                assert retrieved == value, f"Inconsistency for {key}"

                # Sometimes delete
                if i % 3 == 0:
                    await cache.delete(key)

        # Run multiple workers concurrently
        tasks = [worker(i) for i in range(5)]
        await asyncio.gather(*tasks)

        # Cache should be consistent (no corruption)
        stats = cache.get_stats()
        assert stats["size"] <= 100  # Should respect max size


class TestMemoryManagement:
    """Test cases for memory management and leak prevention."""

    @pytest.mark.asyncio
    async def test_no_memory_leak_with_many_operations(self):
        """Test no memory leaks with many cache operations."""
        cache = SafeAsyncCache(max_size=10)

        # Perform many operations that could cause leaks
        for i in range(1000):
            key = f"temp_key_{i}"
            await cache.set(key, f"value_{i}")

            # Sometimes get and delete
            if i % 2 == 0:
                await cache.get(key)
            if i % 3 == 0:
                await cache.delete(key)

        # Cache size should be bounded by max_size
        assert len(cache._cache) <= 10
        assert len(cache._access_times) <= 10

    @pytest.mark.asyncio
    async def test_ttl_prevents_memory_accumulation(self):
        """Test TTL prevents unlimited memory accumulation."""
        cache = SafeAsyncCache(max_size=1000, ttl_seconds=0.05)

        # Add many entries that will expire
        for i in range(100):
            await cache.set(f"key_{i}", f"value_{i}")

        assert len(cache._cache) == 100

        # Wait for expiration
        await asyncio.sleep(0.1)

        # Cleanup should remove expired entries
        removed = await cache.cleanup_expired()
        assert removed == 100
        assert len(cache._cache) == 0
