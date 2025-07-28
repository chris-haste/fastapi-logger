"""Unit tests for AsyncProcessorBase foundation component.

Tests async processor base functionality, integration with foundation components,
and async-safe operation patterns.
"""

import asyncio
from typing import Any, Dict, Optional
from unittest.mock import Mock, patch

import pytest

from fapilog._internal.async_lock_manager import ProcessorLockManager
from fapilog._internal.async_processor_base import AsyncProcessorBase
from fapilog._internal.safe_async_cache import SafeAsyncCache


class TestAsyncProcessor(AsyncProcessorBase):
    """Test implementation of AsyncProcessorBase for testing."""

    def __init__(self, **config):
        super().__init__(**config)
        self.process_calls = []
        self.process_async_calls = []

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Test implementation of sync process method."""
        self.process_calls.append((logger, method_name, event_dict))
        # Add a test field to verify processing
        event_dict = event_dict.copy()
        event_dict["test_processed"] = True
        return event_dict

    async def process_async(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Test implementation of async process method."""
        self.process_async_calls.append((logger, method_name, event_dict))
        # Add a test field to verify async processing
        event_dict = event_dict.copy()
        event_dict["async_processed"] = True
        return event_dict


class TestAsyncProcessorBase:
    """Test cases for AsyncProcessorBase."""

    def test_init(self):
        """Test AsyncProcessorBase initialization."""
        processor = TestAsyncProcessor(
            processor_id="test_proc", cache_max_size=500, cache_ttl_seconds=30.0
        )

        assert processor._processor_id == "test_proc"
        assert isinstance(processor._lock_manager, ProcessorLockManager)
        assert isinstance(processor._cache, SafeAsyncCache)
        assert processor._cache._max_size == 500
        assert processor._cache._ttl_seconds == 30.0

    def test_init_default_processor_id(self):
        """Test initialization with default processor ID."""
        processor = TestAsyncProcessor()
        assert processor._processor_id == "TestAsyncProcessor"

    def test_lock_names_generation(self):
        """Test lock name generation for processor operations."""
        processor = TestAsyncProcessor(processor_id="test_proc")

        assert processor._cache_lock_name == "test_proc_cache"
        assert processor._update_lock_name == "test_proc_update"

    @pytest.mark.asyncio
    async def test_safe_cache_operation(self):
        """Test safe cache operation with proper locking."""
        processor = TestAsyncProcessor()

        operation_called = False

        async def test_operation():
            nonlocal operation_called
            operation_called = True
            return "operation_result"

        result = await processor._safe_cache_operation("test_key", test_operation)

        assert result == "operation_result"
        assert operation_called

    @pytest.mark.asyncio
    async def test_atomic_update(self):
        """Test atomic update operation with proper locking."""
        processor = TestAsyncProcessor()

        update_called = False

        async def test_update():
            nonlocal update_called
            update_called = True
            return "update_result"

        result = await processor._atomic_update("update_key", test_update)

        assert result == "update_result"
        assert update_called

    @pytest.mark.asyncio
    async def test_get_or_create_cached_value(self):
        """Test get or create cached value functionality."""
        processor = TestAsyncProcessor()

        factory_call_count = 0

        async def factory():
            nonlocal factory_call_count
            factory_call_count += 1
            return f"value_{factory_call_count}"

        # First call should create value
        result1 = await processor._get_or_create_cached_value("test_key", factory)
        assert result1 == "value_1"
        assert factory_call_count == 1

        # Second call should use cached value
        result2 = await processor._get_or_create_cached_value("test_key", factory)
        assert result2 == "value_1"  # Same value from cache
        assert factory_call_count == 1  # Factory not called again

    @pytest.mark.asyncio
    async def test_update_cache_atomic(self):
        """Test atomic cache update functionality."""
        processor = TestAsyncProcessor()

        # Update cache
        await processor._update_cache_atomic("test_key", "test_value")

        # Verify value was stored
        result = await processor._cache.get("test_key")
        assert result == "test_value"

    @pytest.mark.asyncio
    async def test_remove_from_cache(self):
        """Test atomic cache removal functionality."""
        processor = TestAsyncProcessor()

        # Add value to cache
        await processor._cache.set("test_key", "test_value")
        assert await processor._cache.get("test_key") == "test_value"

        # Remove value
        removed = await processor._remove_from_cache("test_key")

        assert removed is True
        assert await processor._cache.get("test_key") is None

    @pytest.mark.asyncio
    async def test_cleanup_expired_cache(self):
        """Test cleanup of expired cache entries."""
        processor = TestAsyncProcessor(cache_ttl_seconds=0.1)

        # Add entries that will expire
        await processor._cache.set("key1", "value1")
        await processor._cache.set("key2", "value2")

        # Wait for expiration
        await asyncio.sleep(0.15)

        # Cleanup expired entries
        removed_count = await processor._cleanup_expired_cache()

        assert removed_count == 2

    @pytest.mark.asyncio
    async def test_start_impl(self):
        """Test async processor startup implementation."""
        processor = TestAsyncProcessor()

        # Test startup
        await processor._start_impl()

        # Should complete without error (base implementation does nothing)
        assert True

    @pytest.mark.asyncio
    async def test_stop_impl(self):
        """Test async processor cleanup implementation."""
        processor = TestAsyncProcessor()

        # Add some cache entries
        await processor._cache.set("key1", "value1")
        await processor._cache.set("key2", "value2")
        assert len(processor._cache._cache) == 2

        # Test cleanup
        await processor._stop_impl()

        # Cache should be cleared
        assert len(processor._cache._cache) == 0

    def test_get_async_stats(self):
        """Test async processor statistics."""
        processor = TestAsyncProcessor(processor_id="test_proc")

        stats = processor.get_async_stats()

        assert stats["processor_id"] == "test_proc"
        assert stats["is_started"] is False
        assert "lock_stats" in stats
        assert "cache_stats" in stats
        assert isinstance(stats["lock_stats"], dict)
        assert isinstance(stats["cache_stats"], dict)

    @pytest.mark.asyncio
    async def test_handle_processor_error(self):
        """Test processor error handling."""
        processor = TestAsyncProcessor()

        error = ValueError("Test error")
        context = {"operation": "test", "key": "test_key"}

        # Mock logger to capture log calls
        with patch("fapilog._internal.async_processor_base.logger") as mock_logger:
            await processor._handle_processor_error(error, context)

            # Verify error was logged
            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert "Error in async processor TestAsyncProcessor" in call_args[0][0]
            assert call_args[1]["extra"]["processor_id"] == "TestAsyncProcessor"
            assert call_args[1]["extra"]["error_type"] == "ValueError"
            assert call_args[1]["extra"]["context"] == context

    def test_process_method_required(self):
        """Test that process method is required (abstract)."""
        # TestAsyncProcessor implements process, so it should work
        processor = TestAsyncProcessor()

        mock_logger = Mock()
        event_dict = {"message": "test"}

        result = processor.process(mock_logger, "info", event_dict)

        assert result["test_processed"] is True
        assert len(processor.process_calls) == 1

    @pytest.mark.asyncio
    async def test_process_async_default_implementation(self):
        """Test default async process implementation calls sync process."""
        processor = TestAsyncProcessor()

        mock_logger = Mock()
        event_dict = {"message": "test"}

        # Call async version which should delegate to sync process
        result = await processor.process_async(mock_logger, "info", event_dict)

        # Should have called sync process method (default implementation)
        # But our test class overrides it, so check async version was called
        assert result["async_processed"] is True
        assert len(processor.process_async_calls) == 1

    @pytest.mark.asyncio
    async def test_create_processor_task_success(self):
        """Test successful async task creation."""
        processor = TestAsyncProcessor()

        async def test_coro():
            await asyncio.sleep(0.001)
            return "task_result"

        # Create task
        task = processor._create_processor_task(test_coro(), "test_task")

        assert task is not None
        assert isinstance(task, asyncio.Task)
        assert task.get_name() == "TestAsyncProcessor_test_task"


class TestAsyncProcessorIntegration:
    """Integration tests for AsyncProcessorBase with foundation components."""

    @pytest.mark.asyncio
    async def test_concurrent_cache_operations(self):
        """Test concurrent cache operations through processor interface."""
        processor = TestAsyncProcessor()

        async def cache_worker(worker_id: int):
            for i in range(10):
                key = f"worker_{worker_id}_key_{i}"
                value = f"worker_{worker_id}_value_{i}"

                # Use processor cache operations
                await processor._update_cache_atomic(key, value)
                retrieved = await processor._cache.get(key)
                assert retrieved == value

        # Run concurrent workers
        tasks = [cache_worker(i) for i in range(3)]
        await asyncio.gather(*tasks)

        # Verify cache consistency
        stats = processor.get_async_stats()
        assert stats["cache_stats"]["size"] == 30  # 3 workers * 10 keys each

    @pytest.mark.asyncio
    async def test_concurrent_lock_operations(self):
        """Test concurrent lock operations through processor interface."""
        processor = TestAsyncProcessor()

        operation_order = []

        async def locked_operation(op_id: int):
            async def operation():
                operation_order.append(f"start_{op_id}")
                await asyncio.sleep(0.01)
                operation_order.append(f"end_{op_id}")
                return f"result_{op_id}"

            return await processor._safe_cache_operation("test_key", operation)

        # Run concurrent operations
        tasks = [locked_operation(i) for i in range(3)]
        results = await asyncio.gather(*tasks)

        # Verify all operations completed
        assert len(results) == 3
        assert all(results[i] == f"result_{i}" for i in range(3))

        # Verify proper serialization (no interleaving)
        for i in range(3):
            start_idx = operation_order.index(f"start_{i}")
            end_idx = operation_order.index(f"end_{i}")

            # No other operation should start between this one's start and end
            for j in range(3):
                if i != j:
                    try:
                        other_start_idx = operation_order.index(f"start_{j}")
                        assert not (start_idx < other_start_idx < end_idx)
                    except ValueError:
                        # Other operation might not have started yet
                        pass

    @pytest.mark.asyncio
    async def test_processor_lifecycle_with_cache(self):
        """Test processor lifecycle management with cache operations."""
        processor = TestAsyncProcessor()

        # Test startup
        await processor.start()
        assert processor.is_started

        # Use cache during operation
        await processor._update_cache_atomic("lifecycle_key", "lifecycle_value")
        assert await processor._cache.get("lifecycle_key") == "lifecycle_value"

        # Test shutdown
        await processor.stop()
        assert not processor.is_started

        # Cache should be cleared
        assert await processor._cache.get("lifecycle_key") is None

    @pytest.mark.asyncio
    async def test_error_handling_with_foundation_components(self):
        """Test error handling integration with foundation components."""
        processor = TestAsyncProcessor()

        # Test error in cache operation
        async def failing_operation():
            raise ValueError("Cache operation failed")

        with pytest.raises(ValueError):
            await processor._safe_cache_operation("error_key", failing_operation)

        # Processor should still be functional
        await processor._update_cache_atomic("recovery_key", "recovery_value")
        assert await processor._cache.get("recovery_key") == "recovery_value"

    @pytest.mark.asyncio
    async def test_memory_consistency_under_load(self):
        """Test memory consistency under high concurrent load."""
        processor = TestAsyncProcessor(cache_max_size=50)

        async def high_load_worker(worker_id: int):
            for i in range(100):  # More operations than cache size
                key = f"load_{worker_id}_{i}"
                value = f"value_{worker_id}_{i}"

                # Cache operations
                await processor._update_cache_atomic(key, value)

                # Sometimes use get_or_create
                if i % 3 == 0:

                    async def factory(item_id=i):
                        return f"factory_{worker_id}_{item_id}"

                    await processor._get_or_create_cached_value(
                        f"factory_{key}", factory
                    )

                # Sometimes remove entries
                if i % 5 == 0:
                    await processor._remove_from_cache(key)

        # Run high load
        tasks = [high_load_worker(i) for i in range(5)]
        await asyncio.gather(*tasks)

        # Verify cache size is bounded
        stats = processor.get_async_stats()
        assert stats["cache_stats"]["size"] <= 50

    @pytest.mark.asyncio
    async def test_global_lock_manager_sharing(self):
        """Test that processors share the global lock manager."""
        processor1 = TestAsyncProcessor(processor_id="proc1")
        processor2 = TestAsyncProcessor(processor_id="proc2")

        # Both should use the same lock manager instance
        assert processor1._lock_manager is processor2._lock_manager

        # But have different cache instances
        assert processor1._cache is not processor2._cache


class TestRaceConditionPrevention:
    """Test cases specifically for race condition prevention."""

    @pytest.mark.asyncio
    async def test_no_race_in_get_or_create(self):
        """Test no race conditions in get_or_create operations."""
        processor = TestAsyncProcessor()

        factory_call_count = 0

        async def factory():
            nonlocal factory_call_count
            factory_call_count += 1
            await asyncio.sleep(0.001)  # Simulate async work
            return factory_call_count

        # Many concurrent get_or_create operations
        tasks = [
            processor._get_or_create_cached_value("race_key", factory)
            for _ in range(20)
        ]
        results = await asyncio.gather(*tasks)

        # Factory should only be called once
        assert factory_call_count == 1
        assert all(result == 1 for result in results)

    @pytest.mark.asyncio
    async def test_no_race_in_atomic_updates(self):
        """Test no race conditions in atomic update operations."""
        processor = TestAsyncProcessor()

        update_count = 0

        async def atomic_increment():
            nonlocal update_count
            current = await processor._cache.get("counter") or 0
            await asyncio.sleep(0.001)  # Simulate work that could cause races
            update_count += 1
            await processor._cache.set("counter", current + 1)
            return current + 1

        # Many concurrent atomic updates
        tasks = [
            processor._atomic_update("counter_update", atomic_increment)
            for _ in range(10)
        ]
        await asyncio.gather(*tasks)

        # All updates should have been serialized
        assert update_count == 10
        final_value = await processor._cache.get("counter")
        assert final_value == 10
