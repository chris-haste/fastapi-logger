"""Comprehensive tests for enrichers.py to achieve >90% coverage."""

from unittest.mock import Mock, patch

import pytest

from fapilog.enrichers import (
    AsyncSmartCache,
    EnricherErrorHandler,
    EnricherErrorStrategy,
    EnricherExecutionError,
    EnricherHealthMonitor,
    body_size_enricher,
    clear_enrichers,
    clear_smart_cache,
    configure_enricher_error_handling,
    create_user_dependency,
    get_enricher_health_report,
    host_process_enricher,
    register_enricher,
    request_response_enricher,
    resource_snapshot_enricher,
    run_registered_enrichers,
    user_context_enricher,
)


class TestEnricherErrorHandler:
    """Test EnricherErrorHandler functionality."""

    def test_enricher_error_handler_initialization(self):
        """Test EnricherErrorHandler initialization."""
        handler = EnricherErrorHandler()
        assert handler.strategy == EnricherErrorStrategy.LOG_WARNING
        assert handler.failed_enrichers == set()

        custom_handler = EnricherErrorHandler(EnricherErrorStrategy.SILENT)
        assert custom_handler.strategy == EnricherErrorStrategy.SILENT

    def test_handle_enricher_error_silent_strategy(self):
        """Test silent error handling strategy."""
        handler = EnricherErrorHandler(EnricherErrorStrategy.SILENT)
        error = Exception("Test error")
        event_dict = {"test": "data"}

        result = handler.handle_enricher_error(Mock(), error, event_dict)
        assert result is True
        assert len(handler.failed_enrichers) == 0

    def test_handle_enricher_error_log_warning_strategy(self):
        """Test log warning error handling strategy."""
        handler = EnricherErrorHandler(EnricherErrorStrategy.LOG_WARNING)
        error = Exception("Test error")
        event_dict = {"test": "data"}
        mock_enricher = Mock(__name__="test_enricher")

        with patch("fapilog.enrichers.enricher_logger") as mock_logger:
            result = handler.handle_enricher_error(mock_enricher, error, event_dict)
            assert result is True
            assert "test_enricher" in handler.failed_enrichers
            mock_logger.warning.assert_called_once()

    def test_handle_enricher_error_log_error_strategy(self):
        """Test log error error handling strategy."""
        handler = EnricherErrorHandler(EnricherErrorStrategy.LOG_ERROR)
        error = Exception("Test error")
        event_dict = {"test": "data"}
        mock_enricher = Mock(__name__="test_enricher")

        with patch("fapilog.enrichers.enricher_logger") as mock_logger:
            result = handler.handle_enricher_error(mock_enricher, error, event_dict)
            assert result is True
            assert "test_enricher" in handler.failed_enrichers
            mock_logger.error.assert_called_once()

    def test_handle_enricher_error_fail_fast_strategy(self):
        """Test fail fast error handling strategy."""
        handler = EnricherErrorHandler(EnricherErrorStrategy.FAIL_FAST)
        error = Exception("Test error")
        event_dict = {"test": "data"}
        mock_enricher = Mock(__name__="test_enricher")

        with pytest.raises(EnricherExecutionError):
            handler.handle_enricher_error(mock_enricher, error, event_dict)

    def test_handle_enricher_error_without_name(self):
        """Test error handling with enricher without __name__."""
        handler = EnricherErrorHandler(EnricherErrorStrategy.LOG_WARNING)
        error = Exception("Test error")
        event_dict = {"test": "data"}
        mock_enricher = Mock()
        del mock_enricher.__name__

        with patch("fapilog.enrichers.enricher_logger") as mock_logger:
            result = handler.handle_enricher_error(mock_enricher, error, event_dict)
            assert result is True
            mock_logger.warning.assert_called_once()


class TestEnricherHealthMonitor:
    """Test EnricherHealthMonitor functionality."""

    def test_enricher_health_monitor_initialization(self):
        """Test EnricherHealthMonitor initialization."""
        monitor = EnricherHealthMonitor()
        assert monitor.enricher_stats == {}

    def test_record_enricher_execution_success(self):
        """Test recording successful enricher execution."""
        monitor = EnricherHealthMonitor()
        enricher_name = "test_enricher"
        duration_ms = 100.0

        monitor.record_enricher_execution(enricher_name, True, duration_ms)

        assert enricher_name in monitor.enricher_stats
        stats = monitor.enricher_stats[enricher_name]
        assert stats["total_calls"] == 1
        assert stats["successful_calls"] == 1
        assert stats["failed_calls"] == 0
        assert stats["avg_duration_ms"] == duration_ms
        assert stats["last_success"] is not None
        assert stats["last_failure"] is None

    def test_record_enricher_execution_failure(self):
        """Test recording failed enricher execution."""
        monitor = EnricherHealthMonitor()
        enricher_name = "test_enricher"
        duration_ms = 50.0

        monitor.record_enricher_execution(enricher_name, False, duration_ms)

        assert enricher_name in monitor.enricher_stats
        stats = monitor.enricher_stats[enricher_name]
        assert stats["total_calls"] == 1
        assert stats["successful_calls"] == 0
        assert stats["failed_calls"] == 1
        assert stats["avg_duration_ms"] == duration_ms
        assert stats["last_success"] is None
        assert stats["last_failure"] is not None

    def test_record_enricher_execution_multiple_calls(self):
        """Test recording multiple enricher executions."""
        monitor = EnricherHealthMonitor()
        enricher_name = "test_enricher"

        # Record multiple executions
        monitor.record_enricher_execution(enricher_name, True, 100.0)
        monitor.record_enricher_execution(enricher_name, False, 200.0)
        monitor.record_enricher_execution(enricher_name, True, 150.0)

        stats = monitor.enricher_stats[enricher_name]
        assert stats["total_calls"] == 3
        assert stats["successful_calls"] == 2
        assert stats["failed_calls"] == 1
        assert stats["avg_duration_ms"] == 150.0  # (100 + 200 + 150) / 3

    def test_get_health_report(self):
        """Test getting health report."""
        monitor = EnricherHealthMonitor()
        monitor.record_enricher_execution("enricher1", True, 100.0)
        monitor.record_enricher_execution("enricher2", False, 200.0)

        report = monitor.get_health_report()
        assert report["enricher_count"] == 2
        assert "enrichers" in report
        assert "overall_success_rate" in report
        assert report["overall_success_rate"] == 0.5  # 1 success / 2 total

    def test_calculate_overall_success_rate_empty(self):
        """Test calculating success rate with no enrichers."""
        monitor = EnricherHealthMonitor()
        success_rate = monitor._calculate_overall_success_rate()
        assert success_rate == 1.0

    def test_calculate_overall_success_rate_all_success(self):
        """Test calculating success rate with all successful enrichers."""
        monitor = EnricherHealthMonitor()
        monitor.record_enricher_execution("enricher1", True, 100.0)
        monitor.record_enricher_execution("enricher2", True, 200.0)

        success_rate = monitor._calculate_overall_success_rate()
        assert success_rate == 1.0

    def test_calculate_overall_success_rate_mixed(self):
        """Test calculating success rate with mixed results."""
        monitor = EnricherHealthMonitor()
        monitor.record_enricher_execution("enricher1", True, 100.0)
        monitor.record_enricher_execution("enricher2", False, 200.0)
        monitor.record_enricher_execution("enricher3", True, 150.0)

        success_rate = monitor._calculate_overall_success_rate()
        assert success_rate == 2 / 3  # 2 success / 3 total


class TestGlobalFunctions:
    """Test global functions in enrichers.py."""

    def test_configure_enricher_error_handling(self):
        """Test configuring enricher error handling."""
        # Test that the function doesn't raise any exceptions
        configure_enricher_error_handling(EnricherErrorStrategy.SILENT)
        configure_enricher_error_handling(EnricherErrorStrategy.LOG_WARNING)
        configure_enricher_error_handling(EnricherErrorStrategy.LOG_ERROR)
        configure_enricher_error_handling(EnricherErrorStrategy.FAIL_FAST)

    def test_get_enricher_health_report(self):
        """Test getting enricher health report."""
        report = get_enricher_health_report()
        assert isinstance(report, dict)
        assert "enricher_count" in report
        assert "enrichers" in report
        assert "overall_success_rate" in report

    def test_clear_smart_cache(self):
        """Test clearing smart cache."""
        # This should not raise any exceptions
        clear_smart_cache()


class TestHostProcessEnricher:
    """Test host_process_enricher functionality."""

    @pytest.mark.asyncio
    async def test_host_process_enricher_basic(self):
        """Test basic host process enrichment."""
        event_dict = {}
        result = await host_process_enricher(Mock(), "info", event_dict)

        assert "hostname" in result
        assert "pid" in result
        assert result["hostname"] is not None
        assert result["pid"] is not None

    @pytest.mark.asyncio
    async def test_host_process_enricher_with_existing_values(self):
        """Test host process enrichment with existing values."""
        event_dict = {"hostname": "existing_host", "pid": 12345}
        result = await host_process_enricher(Mock(), "info", event_dict)

        assert result["hostname"] == "existing_host"
        assert result["pid"] == 12345

    @pytest.mark.asyncio
    async def test_host_process_enricher_with_none_values(self):
        """Test host process enrichment with None values."""
        event_dict = {"hostname": None, "pid": None}
        result = await host_process_enricher(Mock(), "info", event_dict)

        assert result["hostname"] is not None
        assert result["pid"] is not None

    @pytest.mark.asyncio
    @patch("fapilog.enrichers.socket.gethostname")
    async def test_host_process_enricher_socket_error(self, mock_gethostname):
        """Test host process enrichment with socket error."""
        clear_smart_cache()  # Clear cache to test error condition
        mock_gethostname.side_effect = Exception("Socket error")
        event_dict = {}
        result = await host_process_enricher(Mock(), "info", event_dict)

        assert result["hostname"] == "unknown"
        assert "pid" in result

    @pytest.mark.asyncio
    @patch("fapilog.enrichers.os.getpid")
    async def test_host_process_enricher_pid_error(self, mock_getpid):
        """Test host process enrichment with PID error."""
        clear_smart_cache()  # Clear cache to test error condition
        mock_getpid.side_effect = Exception("PID error")
        event_dict = {}
        result = await host_process_enricher(Mock(), "info", event_dict)

        assert result["pid"] == -1
        assert "hostname" in result


class TestResourceSnapshotEnricher:
    """Test resource_snapshot_enricher functionality."""

    @pytest.mark.asyncio
    async def test_resource_snapshot_enricher_basic(self):
        """Test basic resource snapshot enrichment."""
        event_dict = {}
        result = await resource_snapshot_enricher(Mock(), "info", event_dict)

        # Should not crash and should return the event_dict
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_resource_snapshot_enricher_with_existing_values(self):
        """Test resource snapshot enrichment with existing values."""
        event_dict = {"memory_mb": 100.0, "cpu_percent": 50.0}
        result = await resource_snapshot_enricher(Mock(), "info", event_dict)

        assert result["memory_mb"] == 100.0
        assert result["cpu_percent"] == 50.0

    @pytest.mark.asyncio
    async def test_resource_snapshot_enricher_with_none_values(self):
        """Test resource snapshot enrichment with None values."""
        event_dict = {"memory_mb": None, "cpu_percent": None}
        result = await resource_snapshot_enricher(Mock(), "info", event_dict)

        # Should not crash
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    @patch("fapilog.enrichers._get_process_smart")
    async def test_resource_snapshot_enricher_psutil_import_error(
        self, mock_get_process
    ):
        """Test resource snapshot enrichment with psutil import error."""
        mock_get_process.return_value = None  # Simulate import failure
        event_dict = {}
        result = await resource_snapshot_enricher(Mock(), "info", event_dict)

        assert result == event_dict

    @pytest.mark.asyncio
    @patch("fapilog.enrichers._get_process_smart")
    async def test_resource_snapshot_enricher_process_error(self, mock_get_process):
        """Test resource snapshot enrichment with process error."""
        # Mock process that fails on memory_info
        mock_instance = Mock()
        mock_instance.memory_info.side_effect = OSError("Process not found")
        mock_get_process.return_value = mock_instance

        event_dict = {}
        result = await resource_snapshot_enricher(Mock(), "info", event_dict)

        # Should handle error gracefully and return event_dict without fields
        assert isinstance(result, dict)
        assert "memory_mb" not in result
        assert "cpu_percent" not in result


class TestBodySizeEnricher:
    """Test body_size_enricher functionality."""

    def test_body_size_enricher_basic(self):
        """Test basic body size enrichment."""
        event_dict = {}
        result = body_size_enricher(Mock(), "info", event_dict)

        # Should not crash and should return the event_dict
        assert isinstance(result, dict)

    def test_body_size_enricher_with_existing_values(self):
        """Test body size enrichment with existing values."""
        event_dict = {"req_bytes": 1000, "res_bytes": 2000}
        result = body_size_enricher(Mock(), "info", event_dict)

        assert result["req_bytes"] == 1000
        assert result["res_bytes"] == 2000

    def test_body_size_enricher_with_none_values(self):
        """Test body size enrichment with None values."""
        event_dict = {"req_bytes": None, "res_bytes": None}
        result = body_size_enricher(Mock(), "info", event_dict)

        # Should not crash
        assert isinstance(result, dict)


class TestRequestResponseEnricher:
    """Test request_response_enricher functionality."""

    def test_request_response_enricher_basic(self):
        """Test basic request response enrichment."""
        event_dict = {}
        result = request_response_enricher(Mock(), "info", event_dict)

        # Should not crash and should return the event_dict
        assert isinstance(result, dict)

    def test_request_response_enricher_with_existing_values(self):
        """Test request response enrichment with existing values."""
        event_dict = {"method": "GET", "status_code": 200}
        result = request_response_enricher(Mock(), "info", event_dict)

        assert result["method"] == "GET"
        assert result["status_code"] == 200

    def test_request_response_enricher_with_none_values(self):
        """Test request response enrichment with None values."""
        event_dict = {"method": None, "status_code": None}
        result = request_response_enricher(Mock(), "info", event_dict)

        # Should not crash
        assert isinstance(result, dict)


class TestUserContextEnricher:
    """Test user_context_enricher functionality."""

    def test_user_context_enricher_basic(self):
        """Test basic user context enrichment."""
        event_dict = {}
        result = user_context_enricher(Mock(), "info", event_dict)

        # Should not crash and should return the event_dict
        assert isinstance(result, dict)

    def test_user_context_enricher_with_existing_values(self):
        """Test user context enrichment with existing values."""
        event_dict = {"user_id": "123", "username": "test_user"}
        result = user_context_enricher(Mock(), "info", event_dict)

        assert result["user_id"] == "123"
        assert result["username"] == "test_user"

    def test_user_context_enricher_with_none_values(self):
        """Test user context enrichment with None values."""
        event_dict = {"user_id": None, "username": None}
        result = user_context_enricher(Mock(), "info", event_dict)

        # Should not crash
        assert isinstance(result, dict)


class TestCreateUserDependency:
    """Test create_user_dependency functionality."""

    def test_create_user_dependency_basic(self):
        """Test basic user dependency creation."""

        def mock_get_user_func():
            return {"user_id": "123", "username": "test_user"}

        user_dependency = create_user_dependency(mock_get_user_func)
        assert callable(user_dependency)

    @pytest.mark.asyncio
    async def test_user_dependency_async_execution(self):
        """Test async user dependency execution."""

        def mock_get_user_func(*args, **kwargs):
            return {"user_id": "123", "username": "test_user"}

        user_dependency = create_user_dependency(mock_get_user_func)
        result = await user_dependency("arg1", kwarg1="value1")

        assert result == {"user_id": "123", "username": "test_user"}

    @pytest.mark.asyncio
    async def test_user_dependency_with_async_get_user_func(self):
        """Test user dependency with async get_user_func."""

        async def mock_async_get_user_func():
            return {"user_id": "456", "username": "async_user"}

        user_dependency = create_user_dependency(mock_async_get_user_func)
        result = await user_dependency()

        assert result == {"user_id": "456", "username": "async_user"}

    @pytest.mark.asyncio
    async def test_user_dependency_exception_handling(self):
        """Test user dependency exception handling."""

        def mock_get_user_func():
            raise Exception("User not found")

        user_dependency = create_user_dependency(mock_get_user_func)

        with pytest.raises(Exception, match="User not found"):
            await user_dependency()


class TestRunRegisteredEnrichers:
    """Test run_registered_enrichers functionality."""

    def test_run_registered_enrichers_empty(self):
        """Test running registered enrichers with none registered."""
        event_dict = {"test": "data"}
        result = run_registered_enrichers(Mock(), "info", event_dict)

        assert result == event_dict

    def test_run_registered_enrichers_with_enrichers(self):
        """Test running registered enrichers."""

        # Register a test enricher
        def test_enricher(logger, method_name, event_dict):
            event_dict["enriched"] = True
            return event_dict

        register_enricher(test_enricher)

        event_dict = {"test": "data"}
        result = run_registered_enrichers(Mock(), "info", event_dict)

        assert result["enriched"] is True
        assert result["test"] == "data"

        # Clean up

        clear_enrichers()

    def test_run_registered_enrichers_with_failing_enricher(self):
        """Test running registered enrichers with failing enricher."""

        def failing_enricher(logger, method_name, event_dict):
            raise Exception("Enricher failed")

        register_enricher(failing_enricher)

        # Configure error handling to be silent
        from fapilog.enrichers import (
            EnricherErrorStrategy,
            configure_enricher_error_handling,
        )

        configure_enricher_error_handling(EnricherErrorStrategy.SILENT)

        event_dict = {"test": "data"}
        result = run_registered_enrichers(Mock(), "info", event_dict)

        # Should handle the error gracefully and return the original event_dict
        assert result == event_dict

        # Clean up

        clear_enrichers()


class TestAsyncSmartCacheIntegration:
    """Test AsyncSmartCache integration with enrichers."""

    @pytest.mark.asyncio
    async def test_async_smart_cache_container_scoped_instance(self):
        """Test container-scoped AsyncSmartCache instance."""
        from fapilog.container import LoggingContainer

        # Test container-scoped instance
        container = LoggingContainer()
        cache = container.get_async_smart_cache()
        assert isinstance(cache, AsyncSmartCache)

        # Test basic functionality
        result = await cache.get_or_compute("test_key", lambda: "test_value")
        assert result == "test_value"

        # Test caching
        result2 = await cache.get_or_compute("test_key", lambda: "different_value")
        assert result2 == "test_value"  # Should return cached value

        # Test isolation - different containers have different caches
        container2 = LoggingContainer()
        cache2 = container2.get_async_smart_cache()
        assert cache is not cache2  # Different instances

        # Same container returns same cache instance
        cache_same = container.get_async_smart_cache()
        assert cache is cache_same

    @pytest.mark.asyncio
    async def test_async_smart_cache_clear_function(self):
        """Test container-scoped cache clearing."""
        from fapilog.container import LoggingContainer
        from fapilog.enrichers import clear_smart_cache

        # Test container-scoped cache clearing
        container = LoggingContainer()
        cache = container.get_async_smart_cache()

        # Add some data to cache
        await cache.get_or_compute("test_key", lambda: "test_value")

        # Test that global clear_smart_cache function does nothing (backward compatibility)
        clear_smart_cache()  # Should have no effect

        # Verify cache is not cleared by global function
        stats = await cache.get_cache_stats()
        assert stats["total_entries"] == 1  # Should still have the entry

        # Test direct cache clearing
        cache._cache.clear()
        stats = await cache.get_cache_stats()
        assert stats["total_entries"] == 0
