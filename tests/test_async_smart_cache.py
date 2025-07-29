"""Comprehensive test suite for AsyncSmartCache implementation."""

import asyncio
from datetime import datetime, timedelta

import pytest

from fapilog.enrichers import AsyncSmartCache, CacheEntry, CacheEntryManager


class TestCacheEntryManager:
    """Test CacheEntryManager functionality."""

    def test_cache_entry_manager_initialization(self):
        """Test CacheEntryManager initialization."""
        manager = CacheEntryManager()
        assert manager.retry_interval == timedelta(minutes=5)

        custom_interval = timedelta(minutes=10)
        manager = CacheEntryManager(retry_interval=custom_interval)
        assert manager.retry_interval == custom_interval

    def test_should_retry_failed_entry_false_cases(self):
        """Test should_retry_failed_entry returns False for various cases."""
        manager = CacheEntryManager()
        now = datetime.now()

        # Success entry should not retry
        success_entry = CacheEntry(value="test", cached_at=now, is_error=False)
        assert not manager.should_retry_failed_entry(success_entry, now)

        # Error entry without retry_after should not retry
        error_entry_no_retry = CacheEntry(
            value=None, cached_at=now, is_error=True, retry_after=None
        )
        assert not manager.should_retry_failed_entry(error_entry_no_retry, now)

        # Error entry with future retry_after should not retry
        future_retry = now + timedelta(minutes=1)
        error_entry_future = CacheEntry(
            value=None, cached_at=now, is_error=True, retry_after=future_retry
        )
        assert not manager.should_retry_failed_entry(error_entry_future, now)

    def test_should_retry_failed_entry_true_case(self):
        """Test should_retry_failed_entry returns True when ready to retry."""
        manager = CacheEntryManager()
        now = datetime.now()
        past_retry = now - timedelta(minutes=1)

        error_entry_ready = CacheEntry(
            value=None, cached_at=now, is_error=True, retry_after=past_retry
        )
        assert manager.should_retry_failed_entry(error_entry_ready, now)

    def test_create_success_entry(self):
        """Test successful cache entry creation."""
        manager = CacheEntryManager()
        now = datetime.now()
        value = "test_value"

        entry = manager.create_success_entry(value, now)
        assert entry.value == value
        assert entry.cached_at == now
        assert entry.is_error is False
        assert entry.retry_after is None

    def test_create_error_entry(self):
        """Test error cache entry creation."""
        manager = CacheEntryManager(retry_interval=timedelta(minutes=3))
        now = datetime.now()

        entry = manager.create_error_entry(now)
        assert entry.value is None
        assert entry.cached_at == now
        assert entry.is_error is True
        assert entry.retry_after == now + timedelta(minutes=3)


class TestAsyncSmartCache:
    """Test AsyncSmartCache functionality."""

    def test_async_smart_cache_initialization(self):
        """Test AsyncSmartCache initialization."""
        cache = AsyncSmartCache()
        # Check that _lock has the required lock interface
        assert hasattr(cache._lock, "acquire")
        assert hasattr(cache._lock, "release")
        assert cache._cache == {}
        assert isinstance(cache._entry_manager, CacheEntryManager)

    def test_async_smart_cache_custom_retry_interval(self):
        """Test AsyncSmartCache with custom retry interval."""
        custom_interval = timedelta(minutes=10)
        cache = AsyncSmartCache(retry_interval=custom_interval)
        assert cache._entry_manager.retry_interval == custom_interval

    @pytest.mark.asyncio
    async def test_cache_successful_computation_sync(self):
        """Test successful computation and caching with sync function."""
        cache = AsyncSmartCache()

        def compute_func():
            return "computed_value"

        # First call should compute
        result = await cache.get_or_compute("test_key", compute_func)
        assert result == "computed_value"

        # Verify cache entry
        assert "test_key" in cache._cache
        entry = cache._cache["test_key"]
        assert entry.value == "computed_value"
        assert not entry.is_error
        assert entry.retry_after is None

    @pytest.mark.asyncio
    async def test_cache_successful_computation_async(self):
        """Test successful computation and caching with async function."""
        cache = AsyncSmartCache()

        async def async_compute_func():
            return "async_computed_value"

        # First call should compute
        result = await cache.get_or_compute("test_key", async_compute_func)
        assert result == "async_computed_value"

        # Verify cache entry
        assert "test_key" in cache._cache
        entry = cache._cache["test_key"]
        assert entry.value == "async_computed_value"
        assert not entry.is_error

    @pytest.mark.asyncio
    async def test_cache_returns_cached_value(self):
        """Test that subsequent calls return cached value."""
        cache = AsyncSmartCache()
        call_count = 0

        def compute_func():
            nonlocal call_count
            call_count += 1
            return f"computed_value_{call_count}"

        # First call
        result1 = await cache.get_or_compute("test_key", compute_func)
        assert result1 == "computed_value_1"
        assert call_count == 1

        # Second call should return cached value
        result2 = await cache.get_or_compute("test_key", compute_func)
        assert result2 == "computed_value_1"  # Same value
        assert call_count == 1  # Function not called again

    @pytest.mark.asyncio
    async def test_cache_error_handling(self):
        """Test error handling and retry logic."""
        cache = AsyncSmartCache(retry_interval=timedelta(seconds=1))

        def failing_func():
            raise ImportError("Module not found")

        # First call should fail and cache error
        with pytest.raises(ImportError):
            await cache.get_or_compute("test_key", failing_func)

        # Verify error is cached
        assert "test_key" in cache._cache
        entry = cache._cache["test_key"]
        assert entry.is_error
        assert entry.retry_after is not None

        # Immediate retry should raise cached error
        with pytest.raises(RuntimeError, match="Cached error for test_key"):
            await cache.get_or_compute("test_key", failing_func)

    @pytest.mark.asyncio
    async def test_cache_retry_after_interval(self):
        """Test that cache retries after retry interval."""
        cache = AsyncSmartCache(retry_interval=timedelta(milliseconds=100))
        call_count = 0

        def sometimes_failing_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ImportError("First failure")
            return "success"

        # First call fails
        with pytest.raises(ImportError):
            await cache.get_or_compute("test_key", sometimes_failing_func)

        # Wait for retry interval
        await asyncio.sleep(0.15)

        # Second call should retry and succeed
        result = await cache.get_or_compute("test_key", sometimes_failing_func)
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_cache_clear(self):
        """Test cache clearing functionality."""
        cache = AsyncSmartCache()

        def compute_func():
            return "test_value"

        # Add some entries
        await cache.get_or_compute("key1", compute_func)
        await cache.get_or_compute("key2", compute_func)
        assert len(cache._cache) == 2

        # Clear cache
        await cache.clear()
        assert len(cache._cache) == 0

    @pytest.mark.asyncio
    async def test_cache_stats(self):
        """Test cache statistics functionality."""
        cache = AsyncSmartCache()

        def success_func():
            return "success"

        def error_func():
            raise ValueError("Error")

        # Add successful entries
        await cache.get_or_compute("key1", success_func)
        await cache.get_or_compute("key2", success_func)

        # Add error entry
        with pytest.raises(ValueError):
            await cache.get_or_compute("key3", error_func)

        stats = await cache.get_cache_stats()
        assert stats["total_entries"] == 3
        assert stats["success_entries"] == 2
        assert stats["error_entries"] == 1
        assert stats["cache_hit_rate"] == 2.0 / 3.0

    @pytest.mark.asyncio
    async def test_concurrent_access_no_race_conditions(self):
        """Test concurrent access with no race conditions."""
        cache = AsyncSmartCache()
        call_count = 0

        def compute_func():
            nonlocal call_count
            call_count += 1
            return f"computed_value_{call_count}"

        # Launch 1000 concurrent operations on same key
        tasks = [cache.get_or_compute("test_key", compute_func) for _ in range(1000)]
        results = await asyncio.gather(*tasks)

        # All results should be the same (no race condition)
        unique_results = set(results)
        assert len(unique_results) == 1
        assert call_count == 1  # Function called only once

    @pytest.mark.asyncio
    async def test_concurrent_different_keys(self):
        """Test concurrent access with different keys."""
        cache = AsyncSmartCache()

        def compute_func_factory(key_name):
            def compute_func():
                return f"value_for_{key_name}"

            return compute_func

        # Launch concurrent operations on different keys
        tasks = [
            cache.get_or_compute(f"key_{i}", compute_func_factory(f"key_{i}"))
            for i in range(100)
        ]
        results = await asyncio.gather(*tasks)

        # Each result should be unique
        assert len(set(results)) == 100
        assert len(cache._cache) == 100

    @pytest.mark.asyncio
    async def test_stress_test_1000_operations(self):
        """Stress test with 1000+ concurrent cache operations."""
        cache = AsyncSmartCache()
        operation_count = 0

        def compute_func():
            nonlocal operation_count
            operation_count += 1
            return f"computed_{operation_count}"

        # Mix of same and different keys to test various scenarios
        tasks = []
        for i in range(1000):
            key = f"key_{i % 10}"  # 10 different keys, 100 operations each
            tasks.append(cache.get_or_compute(key, compute_func))

        results = await asyncio.gather(*tasks)

        # Should have 10 different keys
        assert len(cache._cache) == 10
        # Each key should have been computed only once
        assert operation_count == 10
        # All operations should have completed successfully
        assert len(results) == 1000

    @pytest.mark.asyncio
    async def test_async_error_propagation(self):
        """Test that async errors are properly propagated."""
        cache = AsyncSmartCache()

        async def async_failing_func():
            raise RuntimeError("Async error")

        with pytest.raises(RuntimeError, match="Async error"):
            await cache.get_or_compute("test_key", async_failing_func)

        # Verify error is cached
        entry = cache._cache["test_key"]
        assert entry.is_error

    @pytest.mark.asyncio
    async def test_lock_contention_scenarios(self):
        """Test lock contention scenarios for thread safety validation."""
        cache = AsyncSmartCache()
        computation_delay = 0.01  # 10ms delay

        async def slow_compute_func():
            await asyncio.sleep(computation_delay)
            return "slow_result"

        # Start many concurrent operations that will contend for the lock
        start_time = asyncio.get_event_loop().time()
        tasks = [cache.get_or_compute("slow_key", slow_compute_func) for _ in range(50)]
        results = await asyncio.gather(*tasks)
        end_time = asyncio.get_event_loop().time()

        # All results should be the same (no race condition)
        assert all(result == "slow_result" for result in results)

        # Total time should be close to single computation time (plus overhead)
        # since all operations should wait for the first one to complete
        total_time = end_time - start_time
        assert total_time < computation_delay * 5  # Allow for overhead
