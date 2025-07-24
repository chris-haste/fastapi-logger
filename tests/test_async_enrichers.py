"""Tests for async enricher support."""

import asyncio
from unittest.mock import patch

import pytest

from fapilog._internal.async_enricher import AsyncEnricher
from fapilog._internal.async_pipeline import AsyncEnricherProcessor
from fapilog._internal.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
)
from fapilog._internal.enricher_cache import EnricherCache, cached_enricher
from fapilog._internal.enricher_lifecycle import EnricherLifecycleManager


class TestAsyncEnricher:
    """Test the AsyncEnricher base class."""

    class MockAsyncEnricher(AsyncEnricher):
        def __init__(
            self, name: str, startup_success: bool = True, health_success: bool = True
        ):
            super().__init__(name)
            self.startup_success = startup_success
            self.health_success = health_success
            self.startup_called = False
            self.shutdown_called = False
            self.health_check_called = False

        async def _startup(self) -> None:
            self.startup_called = True
            if not self.startup_success:
                raise Exception("Startup failed")

        async def _shutdown(self) -> None:
            self.shutdown_called = True

        async def _health_check(self) -> bool:
            self.health_check_called = True
            return self.health_success

        async def enrich_async(self, logger, method_name, event_dict):
            return {**event_dict, "enriched_by": self.name}

    @pytest.mark.asyncio
    async def test_startup_lifecycle(self):
        """Test enricher startup lifecycle."""
        enricher = self.MockAsyncEnricher("test")

        assert not enricher.is_started
        await enricher.startup()
        assert enricher.is_started
        assert enricher.startup_called

        # Second startup should be no-op
        enricher.startup_called = False
        await enricher.startup()
        assert not enricher.startup_called

    @pytest.mark.asyncio
    async def test_shutdown_lifecycle(self):
        """Test enricher shutdown lifecycle."""
        enricher = self.MockAsyncEnricher("test")
        await enricher.startup()

        assert enricher.is_started
        await enricher.shutdown()
        assert not enricher.is_started
        assert enricher.shutdown_called

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test enricher health checking."""
        enricher = self.MockAsyncEnricher("test", health_success=True)
        result = await enricher.health_check()
        assert result is True
        assert enricher.health_check_called

        enricher = self.MockAsyncEnricher("test", health_success=False)
        result = await enricher.health_check()
        assert result is False
        assert not enricher.is_healthy

    @pytest.mark.asyncio
    async def test_enrichment_with_auto_startup(self):
        """Test enrichment automatically starts enricher."""
        enricher = self.MockAsyncEnricher("test")

        event_dict = {"key": "value"}
        result = await enricher(None, "info", event_dict)

        assert enricher.is_started
        assert result == {"key": "value", "enriched_by": "test"}

    @pytest.mark.asyncio
    async def test_enrichment_skips_when_unhealthy(self):
        """Test enrichment is skipped when enricher is unhealthy."""
        enricher = self.MockAsyncEnricher("test")
        enricher.is_healthy = False

        event_dict = {"key": "value"}
        result = await enricher(None, "info", event_dict)

        assert result == {"key": "value"}  # Unchanged

    @pytest.mark.asyncio
    async def test_enrichment_error_handling(self):
        """Test enrichment error handling makes enricher unhealthy."""

        class FailingEnricher(AsyncEnricher):
            async def _startup(self) -> None:
                pass

            async def _shutdown(self) -> None:
                pass

            async def _health_check(self) -> bool:
                return True

            async def enrich_async(self, logger, method_name, event_dict):
                raise Exception("Enrichment failed")

        enricher = FailingEnricher("failing")
        event_dict = {"key": "value"}

        result = await enricher(None, "info", event_dict)

        assert result == {"key": "value"}  # Unchanged
        assert not enricher.is_healthy


class TestAsyncEnricherProcessor:
    """Test the AsyncEnricherProcessor."""

    def sync_enricher(self, logger, method_name, event_dict):
        return {**event_dict, "sync": True}

    class MockAsyncEnricher(AsyncEnricher):
        def __init__(self, name: str, delay: float = 0.0):
            super().__init__(name)
            self.delay = delay

        async def _startup(self) -> None:
            pass

        async def _shutdown(self) -> None:
            pass

        async def _health_check(self) -> bool:
            return True

        async def enrich_async(self, logger, method_name, event_dict):
            if self.delay:
                await asyncio.sleep(self.delay)
            return {**event_dict, "async": self.name}

    @pytest.mark.asyncio
    async def test_mixed_sync_async_processing(self):
        """Test processor handles both sync and async enrichers."""
        async_enricher = self.MockAsyncEnricher("async_test")
        processor = AsyncEnricherProcessor([self.sync_enricher, async_enricher])

        await processor.startup()

        event_dict = {"key": "value"}
        result = processor(None, "info", event_dict)

        assert result == {"key": "value", "sync": True, "async": "async_test"}

        await processor.shutdown()

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test processor handles async enricher timeouts."""
        slow_enricher = self.MockAsyncEnricher("slow", delay=2.0)
        processor = AsyncEnricherProcessor([slow_enricher], timeout=0.1)

        event_dict = {"key": "value"}

        with patch("logging.getLogger") as mock_logger:
            result = processor(None, "info", event_dict)

        # Should return original event dict due to timeout
        assert result == {"key": "value"}

        # Should log timeout warning
        mock_logger().warning.assert_called()

    @pytest.mark.asyncio
    async def test_async_enricher_error_handling(self):
        """Test processor handles async enricher errors gracefully."""

        class FailingAsyncEnricher(AsyncEnricher):
            def __init__(self):
                super().__init__("failing")

            async def _startup(self) -> None:
                pass

            async def _shutdown(self) -> None:
                pass

            async def _health_check(self) -> bool:
                return True

            async def enrich_async(self, logger, method_name, event_dict):
                raise Exception("Async enricher failed")

        failing_enricher = FailingAsyncEnricher()
        processor = AsyncEnricherProcessor([failing_enricher])

        event_dict = {"key": "value"}

        with patch("logging.getLogger"):
            result = processor(None, "info", event_dict)

        # Should return original event dict despite error
        assert result == {"key": "value"}


class TestEnricherCache:
    """Test the EnricherCache."""

    @pytest.mark.asyncio
    async def test_cache_get_set(self):
        """Test basic cache get/set operations."""
        cache = EnricherCache(max_size=10, ttl=1.0)

        # Cache miss
        result = await cache.get("key1")
        assert result is None

        # Cache set and hit
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_cache_ttl_expiration(self):
        """Test cache TTL expiration."""
        cache = EnricherCache(max_size=10, ttl=0.1)

        await cache.set("key1", "value1")
        result = await cache.get("key1")
        assert result == "value1"

        # Wait for expiration
        await asyncio.sleep(0.2)
        result = await cache.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_lru_eviction(self):
        """Test cache LRU eviction when at capacity."""
        cache = EnricherCache(max_size=2, ttl=10.0)

        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        # Access key1 to make it more recently used
        await cache.get("key1")

        # Add key3, should evict key2 (least recently used)
        await cache.set("key3", "value3")

        assert await cache.get("key1") == "value1"
        assert await cache.get("key2") is None
        assert await cache.get("key3") == "value3"

    @pytest.mark.asyncio
    async def test_cached_enricher_decorator(self):
        """Test the cached_enricher decorator."""
        cache = EnricherCache(max_size=10, ttl=1.0)
        call_count = 0

        @cached_enricher(cache)
        async def slow_function(arg1, arg2):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return f"result_{arg1}_{arg2}"

        # First call should execute function
        result1 = await slow_function("a", "b")
        assert result1 == "result_a_b"
        assert call_count == 1

        # Second call should use cache
        result2 = await slow_function("a", "b")
        assert result2 == "result_a_b"
        assert call_count == 1  # No additional call

        # Different args should execute function again
        result3 = await slow_function("c", "d")
        assert result3 == "result_c_d"
        assert call_count == 2


class TestCircuitBreaker:
    """Test the CircuitBreaker."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_success(self):
        """Test circuit breaker with successful calls."""
        circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)

        async def success_func():
            return "success"

        result = await circuit_breaker.call(success_func)
        assert result == "success"
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_failure_threshold(self):
        """Test circuit breaker opens after failure threshold."""
        circuit_breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1.0)

        async def failing_func():
            raise ValueError("Function failed")

        # First failure
        with pytest.raises(ValueError):
            await circuit_breaker.call(failing_func)
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 1

        # Second failure - should open circuit
        with pytest.raises(ValueError):
            await circuit_breaker.call(failing_func)
        assert circuit_breaker.state == CircuitState.OPEN
        assert circuit_breaker.failure_count == 2

        # Third call should raise CircuitBreakerOpenError
        with pytest.raises(CircuitBreakerOpenError):
            await circuit_breaker.call(failing_func)

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery after timeout."""
        circuit_breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)

        async def failing_func():
            raise ValueError("Function failed")

        async def success_func():
            return "success"

        # Trigger circuit open
        with pytest.raises(ValueError):
            await circuit_breaker.call(failing_func)
        assert circuit_breaker.state == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.2)

        # Should transition to half-open and allow one call
        result = await circuit_breaker.call(success_func)
        assert result == "success"
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0


class TestEnricherLifecycleManager:
    """Test the EnricherLifecycleManager."""

    class MockAsyncEnricher(AsyncEnricher):
        def __init__(
            self, name: str, startup_fail: bool = False, health_result: bool = True
        ):
            super().__init__(name)
            self.startup_fail = startup_fail
            self.health_result = health_result
            self.startup_called = False
            self.shutdown_called = False

        async def _startup(self) -> None:
            self.startup_called = True
            if self.startup_fail:
                raise Exception(f"Startup failed for {self.name}")

        async def _shutdown(self) -> None:
            self.shutdown_called = True

        async def _health_check(self) -> bool:
            return self.health_result

        async def enrich_async(self, logger, method_name, event_dict):
            return event_dict

    @pytest.mark.asyncio
    async def test_lifecycle_manager_startup_shutdown(self):
        """Test lifecycle manager startup and shutdown."""
        manager = EnricherLifecycleManager()
        enricher1 = self.MockAsyncEnricher("enricher1")
        enricher2 = self.MockAsyncEnricher("enricher2")

        manager.register_enricher(enricher1)
        manager.register_enricher(enricher2)

        # Startup all
        await manager.startup_all()
        assert manager.is_started
        assert enricher1.startup_called
        assert enricher2.startup_called

        # Shutdown all
        await manager.shutdown_all()
        assert not manager.is_started
        assert enricher1.shutdown_called
        assert enricher2.shutdown_called

    @pytest.mark.asyncio
    async def test_lifecycle_manager_startup_error_handling(self):
        """Test lifecycle manager handles startup errors."""
        manager = EnricherLifecycleManager()
        enricher1 = self.MockAsyncEnricher("good_enricher")
        enricher2 = self.MockAsyncEnricher("bad_enricher", startup_fail=True)

        manager.register_enricher(enricher1)
        manager.register_enricher(enricher2)

        with patch("logging.getLogger"):
            await manager.startup_all()

        # Should still be started despite one failure
        assert manager.is_started
        assert enricher1.startup_called
        assert enricher2.startup_called

    @pytest.mark.asyncio
    async def test_lifecycle_manager_health_checks(self):
        """Test lifecycle manager health checks."""
        manager = EnricherLifecycleManager()
        enricher1 = self.MockAsyncEnricher("healthy", health_result=True)
        enricher2 = self.MockAsyncEnricher("unhealthy", health_result=False)

        manager.register_enricher(enricher1)
        manager.register_enricher(enricher2)

        health_results = await manager.health_check_all()

        assert health_results == {"healthy": True, "unhealthy": False}

    @pytest.mark.asyncio
    async def test_lifecycle_manager_context_manager(self):
        """Test lifecycle manager as context manager."""
        manager = EnricherLifecycleManager()
        enricher = self.MockAsyncEnricher("test")
        manager.register_enricher(enricher)

        async with manager.managed_enrichers():
            assert enricher.startup_called
            assert manager.is_started

        assert enricher.shutdown_called
        assert not manager.is_started

    @pytest.mark.asyncio
    async def test_lifecycle_manager_idempotent_operations(self):
        """Test lifecycle manager operations are idempotent."""
        manager = EnricherLifecycleManager()
        enricher = self.MockAsyncEnricher("test")
        manager.register_enricher(enricher)

        # Multiple startups should be no-op
        await manager.startup_all()
        enricher.startup_called = False
        await manager.startup_all()
        assert not enricher.startup_called

        # Multiple shutdowns should be no-op
        await manager.shutdown_all()
        enricher.shutdown_called = False
        await manager.shutdown_all()
        assert not enricher.shutdown_called


@pytest.mark.asyncio
async def test_integration_async_enrichers_with_pipeline():
    """Integration test for async enrichers with pipeline processor."""

    class TestAsyncEnricher(AsyncEnricher):
        def __init__(self, name: str, delay: float = 0.01):
            super().__init__(name)
            self.delay = delay

        async def _startup(self) -> None:
            pass

        async def _shutdown(self) -> None:
            pass

        async def _health_check(self) -> bool:
            return True

        async def enrich_async(self, logger, method_name, event_dict):
            await asyncio.sleep(self.delay)
            return {**event_dict, f"{self.name}_processed": True}

    # Create enrichers
    enricher1 = TestAsyncEnricher("enricher1")
    enricher2 = TestAsyncEnricher("enricher2")

    # Create processor
    processor = AsyncEnricherProcessor([enricher1, enricher2], timeout=1.0)

    # Start enrichers
    await processor.startup()

    try:
        # Process event
        event_dict = {"initial": "data"}
        result = processor(None, "info", event_dict)

        expected = {
            "initial": "data",
            "enricher1_processed": True,
            "enricher2_processed": True,
        }
        assert result == expected

    finally:
        # Cleanup
        await processor.shutdown()
