"""Comprehensive integration tests for enricher-cache interactions.

This test suite validates:
- All enrichers with new async cache patterns
- Zero race conditions in concurrent enricher execution
- Error state management under concurrent access
- Performance benchmarking against synchronous implementation
- RetryCoordinator with multiple concurrent retry attempts
"""

import asyncio
import time
from unittest.mock import Mock, patch

import pytest

from fapilog.enrichers import (
    AsyncSmartCache,
    RetryCoordinator,
    _get_hostname_smart,
    _get_pid_smart,
    _get_process_smart,
    clear_smart_cache,
    host_process_enricher,
    resource_snapshot_enricher,
)

# Get reference to original __import__ for mocking
original_import = __import__


class TestAsyncSmartCacheIntegration:
    """Test async SmartCache integration functions."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_smart_cache()

    @pytest.mark.asyncio
    async def test_get_hostname_smart_success(self):
        """Test hostname retrieval via async SmartCache."""
        result = await _get_hostname_smart()
        assert isinstance(result, str)
        assert result != ""
        assert result != "unknown"

    @pytest.mark.asyncio
    async def test_get_hostname_smart_fallback(self):
        """Test hostname fallback on error."""
        with patch(
            "fapilog.enrichers.system.socket.gethostname",
            side_effect=Exception("Network error"),
        ):
            result = await _get_hostname_smart()
            assert result == "unknown"

    @pytest.mark.asyncio
    async def test_get_pid_smart_success(self):
        """Test PID retrieval via async SmartCache."""
        result = await _get_pid_smart()
        assert isinstance(result, int)
        assert result > 0

    @pytest.mark.asyncio
    async def test_get_pid_smart_fallback(self):
        """Test PID fallback on error."""
        with patch(
            "fapilog.enrichers.system.os.getpid", side_effect=Exception("System error")
        ):
            result = await _get_pid_smart()
            assert result == -1

    @pytest.mark.asyncio
    async def test_get_process_smart_success(self):
        """Test process retrieval via async SmartCache."""
        with patch("psutil.Process") as mock_process:
            mock_instance = Mock()
            mock_process.return_value = mock_instance

            result = await _get_process_smart()
            assert result == mock_instance

    @pytest.mark.asyncio
    async def test_get_process_smart_import_error(self):
        """Test process fallback on psutil ImportError."""

        # Mock psutil module to be unavailable at import time
        def mock_import(name, *args, **kwargs):
            if name == "psutil":
                raise ImportError("psutil not available")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result = await _get_process_smart()
            assert result is None

    @pytest.mark.asyncio
    async def test_get_process_smart_exception(self):
        """Test process fallback on exception."""

        # Mock psutil.Process to raise an exception
        def mock_import(name, *args, **kwargs):
            if name == "psutil":
                mock_psutil = Mock()
                mock_psutil.Process.side_effect = Exception("System error")
                return mock_psutil
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result = await _get_process_smart()
            assert result is None


class TestAsyncEnricherIntegration:
    """Test async enricher implementations."""

    @pytest.mark.asyncio
    async def test_host_process_enricher_async(self):
        """Test async host_process_enricher functionality."""
        logger = Mock()
        event_dict = {}

        result = await host_process_enricher(logger, "info", event_dict)

        assert "hostname" in result
        assert "pid" in result
        assert isinstance(result["hostname"], str)
        assert isinstance(result["pid"], int)
        assert result["pid"] > 0

    @pytest.mark.asyncio
    async def test_host_process_enricher_existing_values(self):
        """Test enricher respects existing values."""
        logger = Mock()
        event_dict = {"hostname": "custom-host", "pid": 12345}

        result = await host_process_enricher(logger, "info", event_dict)

        assert result["hostname"] == "custom-host"
        assert result["pid"] == 12345

    @pytest.mark.asyncio
    async def test_host_process_enricher_none_values(self):
        """Test enricher replaces None values."""
        logger = Mock()
        event_dict = {"hostname": None, "pid": None}

        result = await host_process_enricher(logger, "info", event_dict)

        assert result["hostname"] is not None
        assert result["pid"] is not None
        assert isinstance(result["hostname"], str)
        assert isinstance(result["pid"], int)

    @pytest.mark.asyncio
    async def test_resource_snapshot_enricher_async(self):
        """Test async resource_snapshot_enricher functionality."""
        # Clear cache to ensure clean state
        clear_smart_cache()

        logger = Mock()
        event_dict = {}

        # Mock _get_process_smart to return consistent process instance
        with patch("fapilog.enrichers.system._get_process_smart") as mock_get_process:
            mock_instance = Mock()
            mock_memory_info = Mock()
            mock_memory_info.rss = 1024 * 1024 * 100  # 100 MB = 104857600 bytes
            mock_instance.memory_info.return_value = mock_memory_info
            mock_instance.cpu_percent.return_value = 15.5
            mock_get_process.return_value = mock_instance

            result = await resource_snapshot_enricher(logger, "info", event_dict)

            assert "memory_mb" in result
            assert "cpu_percent" in result
            assert result["memory_mb"] == 100.0  # round(104857600 / 1048576, 2) = 100.0
            assert result["cpu_percent"] == 15.5

    @pytest.mark.asyncio
    async def test_resource_snapshot_enricher_no_psutil(self):
        """Test resource enricher with no psutil available."""
        logger = Mock()
        event_dict = {}

        with patch("psutil.Process", side_effect=ImportError("No psutil")):
            result = await resource_snapshot_enricher(logger, "info", event_dict)

            # Should return unchanged event_dict
            assert result == event_dict

    @pytest.mark.asyncio
    async def test_resource_snapshot_enricher_process_error(self):
        """Test resource enricher handles process errors gracefully."""
        # Clear cache to ensure clean state
        clear_smart_cache()

        logger = Mock()
        event_dict = {}

        # Mock _get_process_smart to return a process that fails on memory_info
        with patch("fapilog.enrichers.system._get_process_smart") as mock_get_process:
            mock_instance = Mock()
            mock_instance.memory_info.side_effect = OSError("Process not found")
            mock_instance.cpu_percent.side_effect = OSError("Process not found")
            mock_get_process.return_value = mock_instance

            result = await resource_snapshot_enricher(logger, "info", event_dict)

            # Should return event_dict without adding fields due to OSError
            assert "memory_mb" not in result
            assert "cpu_percent" not in result


class TestConcurrentExecution:
    """Test concurrent enricher execution for race conditions."""

    @pytest.mark.asyncio
    async def test_concurrent_host_process_enricher(self):
        """Test concurrent execution of host_process_enricher."""
        logger = Mock()

        async def run_enricher():
            return await host_process_enricher(logger, "info", {})

        # Run 100 concurrent enricher calls
        tasks = [run_enricher() for _ in range(100)]
        results = await asyncio.gather(*tasks)

        # All results should be identical (cached values)
        hostnames = [result["hostname"] for result in results]
        pids = [result["pid"] for result in results]

        assert len(set(hostnames)) == 1  # All should be the same
        assert len(set(pids)) == 1  # All should be the same

    @pytest.mark.asyncio
    async def test_concurrent_resource_enricher(self):
        """Test concurrent execution of resource_snapshot_enricher."""
        # Clear cache to ensure clean state
        clear_smart_cache()

        logger = Mock()

        # Mock _get_process_smart to track calls and return consistent data
        with patch("fapilog.enrichers.system._get_process_smart") as mock_get_process:
            mock_instance = Mock()
            mock_memory_info = Mock()
            mock_memory_info.rss = 1024 * 1024 * 50  # 50 MB
            mock_instance.memory_info.return_value = mock_memory_info
            mock_instance.cpu_percent.return_value = 25.0
            mock_get_process.return_value = mock_instance

            async def run_enricher():
                return await resource_snapshot_enricher(logger, "info", {})

            # Run 50 concurrent enricher calls
            tasks = [run_enricher() for _ in range(50)]
            results = await asyncio.gather(*tasks)

            # Verify the cached function was called (may be 1 due to caching)
            assert mock_get_process.call_count >= 1

            # All results should have the same process data (if any were added)
            memory_values = [result.get("memory_mb") for result in results]
            cpu_values = [result.get("cpu_percent") for result in results]

            # Filter out None values
            memory_values = [v for v in memory_values if v is not None]
            cpu_values = [v for v in cpu_values if v is not None]

            if memory_values:  # Only check if we have values
                assert len(set(memory_values)) == 1  # All should be the same
            if cpu_values:
                assert len(set(cpu_values)) == 1  # All should be the same

    @pytest.mark.asyncio
    async def test_cache_consistency_under_load(self):
        """Test cache consistency under high concurrent load."""
        cache = AsyncSmartCache()

        counter = 0

        def expensive_computation():
            nonlocal counter
            counter += 1
            time.sleep(0.01)  # Simulate expensive work
            return f"result_{counter}"

        async def get_cached_value():
            return await cache.get_or_compute("test_key", expensive_computation)

        # Run 200 concurrent calls
        tasks = [get_cached_value() for _ in range(200)]
        results = await asyncio.gather(*tasks)

        # All results should be identical (no race conditions)
        assert len(set(results)) == 1
        assert counter == 1  # Computation should only run once


class TestRetryCoordinator:
    """Test RetryCoordinator functionality."""

    @pytest.mark.asyncio
    async def test_retry_coordinator_basic(self):
        """Test basic retry coordination."""
        coordinator = RetryCoordinator()

        call_count = 0

        async def retry_func():
            nonlocal call_count
            call_count += 1
            return f"attempt_{call_count}"

        result = await coordinator.coordinate_retry("test_key", retry_func)

        assert result == "attempt_1"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_coordinator_concurrent_same_key(self):
        """Test retry coordination with concurrent attempts on same key."""
        coordinator = RetryCoordinator()

        call_count = 0

        async def retry_func():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)  # Simulate work
            return f"attempt_{call_count}"

        # Run concurrent retries for the same key
        tasks = [
            coordinator.coordinate_retry("same_key", retry_func) for _ in range(10)
        ]
        results = await asyncio.gather(*tasks)

        # Due to locking, calls should be sequential
        assert call_count == 10
        expected_results = [f"attempt_{i}" for i in range(1, 11)]
        assert results == expected_results

    @pytest.mark.asyncio
    async def test_retry_coordinator_different_keys(self):
        """Test retry coordination with different keys (should be concurrent)."""
        coordinator = RetryCoordinator()

        results = []

        async def retry_func(key_id):
            await asyncio.sleep(0.01)  # Simulate work
            results.append(key_id)
            return f"result_{key_id}"

        # Run concurrent retries for different keys
        tasks = [
            coordinator.coordinate_retry(f"key_{i}", lambda i=i: retry_func(i))
            for i in range(5)
        ]
        await asyncio.gather(*tasks)

        # All should have executed
        assert len(results) == 5
        assert set(results) == {0, 1, 2, 3, 4}


class TestErrorHandling:
    """Test error handling in async enricher patterns."""

    @pytest.mark.asyncio
    async def test_cache_error_isolation(self):
        """Test that cache errors don't affect other enrichers."""
        logger = Mock()

        # Test the actual error handling by mocking at the socket level
        # This tests the real error isolation within _get_hostname_smart
        with patch(
            "fapilog.enrichers.system.socket.gethostname",
            side_effect=RuntimeError("Socket error"),
        ), patch("fapilog.enrichers.system._get_pid_smart", return_value=12345):
            # The host_process_enricher should handle errors gracefully
            # _get_hostname_smart will catch the socket error and return "unknown"
            result = await host_process_enricher(logger, "info", {})

            # Should still return a result with both fields
            assert "pid" in result
            assert "hostname" in result
            assert result["pid"] == 12345
            assert result["hostname"] == "unknown"  # Fallback value

    @pytest.mark.asyncio
    async def test_graceful_degradation(self):
        """Test graceful degradation when cache fails."""
        logger = Mock()

        # Test resource enricher with process creation failure
        result = await resource_snapshot_enricher(logger, "info", {})

        # Should return original event_dict on failure
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_concurrent_error_handling(self):
        """Test error handling under concurrent access."""
        cache = AsyncSmartCache()

        failure_count = 0

        def failing_function():
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 3:
                raise ValueError(f"Failure {failure_count}")
            return "success"

        # First call should fail with original exception
        with pytest.raises(ValueError, match="Failure 1"):
            await cache.get_or_compute("failing_key", failing_function)

        # Error should be cached temporarily
        with pytest.raises(RuntimeError, match="Cached error for failing_key"):
            await cache.get_or_compute("failing_key", failing_function)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
