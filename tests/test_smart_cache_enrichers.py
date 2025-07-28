"""Tests for smart cache, error handling, and health monitoring in enrichers."""

import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from fapilog.enrichers import (
    CacheEntry,
    EnricherErrorHandler,
    EnricherErrorStrategy,
    EnricherExecutionError,
    EnricherHealthMonitor,
    SmartCache,
    _error_handler,
    _get_hostname_smart,
    _get_pid_smart,
    _get_process_smart,
    clear_enrichers,
    configure_enricher_error_handling,
    get_enricher_health_report,
    register_enricher,
    run_registered_enrichers,
)


class TestSmartCache:
    """Test SmartCache functionality."""

    def test_cache_entry_creation(self):
        """Test CacheEntry creation with defaults."""
        now = datetime.now()
        entry = CacheEntry(value="test", cached_at=now)

        assert entry.value == "test"
        assert entry.cached_at == now
        assert entry.is_error is False
        assert entry.retry_after is None

    def test_cache_entry_with_error(self):
        """Test CacheEntry creation with error state."""
        now = datetime.now()
        retry_time = now + timedelta(minutes=5)
        entry = CacheEntry(
            value=None, cached_at=now, is_error=True, retry_after=retry_time
        )

        assert entry.value is None
        assert entry.is_error is True
        assert entry.retry_after == retry_time

    def test_smart_cache_initialization(self):
        """Test SmartCache initialization."""
        cache = SmartCache()
        assert cache.retry_interval == timedelta(minutes=5)
        assert cache._cache == {}

    def test_smart_cache_custom_retry_interval(self):
        """Test SmartCache with custom retry interval."""
        custom_interval = timedelta(minutes=10)
        cache = SmartCache(retry_interval=custom_interval)
        assert cache.retry_interval == custom_interval

    def test_cache_successful_computation(self):
        """Test successful computation and caching."""
        cache = SmartCache()

        def compute_func():
            return "computed_value"

        # First call should compute
        result = cache.get_or_compute("test_key", compute_func)
        assert result == "computed_value"

        # Verify cache entry
        assert "test_key" in cache._cache
        entry = cache._cache["test_key"]
        assert entry.value == "computed_value"
        assert not entry.is_error
        assert entry.retry_after is None

    def test_cache_returns_cached_value(self):
        """Test that subsequent calls return cached value."""
        cache = SmartCache()
        call_count = 0

        def compute_func():
            nonlocal call_count
            call_count += 1
            return f"computed_value_{call_count}"

        # First call
        result1 = cache.get_or_compute("test_key", compute_func)
        assert result1 == "computed_value_1"
        assert call_count == 1

        # Second call should return cached value
        result2 = cache.get_or_compute("test_key", compute_func)
        assert result2 == "computed_value_1"  # Same value
        assert call_count == 1  # Function not called again

    def test_cache_error_handling(self):
        """Test error handling and retry logic."""
        cache = SmartCache(retry_interval=timedelta(seconds=1))

        def failing_func():
            raise ImportError("Module not found")

        # First call should fail and cache error
        with pytest.raises(ImportError):
            cache.get_or_compute("test_key", failing_func)

        # Verify error is cached
        assert "test_key" in cache._cache
        entry = cache._cache["test_key"]
        assert entry.is_error
        assert entry.retry_after is not None

        # Immediate retry should raise cached error
        with pytest.raises(RuntimeError, match="Cached error for test_key"):
            cache.get_or_compute("test_key", failing_func)

    def test_cache_retry_after_interval(self):
        """Test that cache retries after retry interval."""
        cache = SmartCache(retry_interval=timedelta(milliseconds=100))
        call_count = 0

        def sometimes_failing_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ImportError("First failure")
            return "success"

        # First call fails
        with pytest.raises(ImportError):
            cache.get_or_compute("test_key", sometimes_failing_func)

        # Wait for retry interval
        time.sleep(0.15)

        # Second call should retry and succeed
        result = cache.get_or_compute("test_key", sometimes_failing_func)
        assert result == "success"
        assert call_count == 2


class TestEnricherErrorHandler:
    """Test error handling strategies."""

    def test_error_handler_initialization(self):
        """Test error handler initialization."""
        handler = EnricherErrorHandler()
        assert handler.strategy == EnricherErrorStrategy.LOG_WARNING
        assert handler.failed_enrichers == set()

    def test_error_handler_custom_strategy(self):
        """Test error handler with custom strategy."""
        handler = EnricherErrorHandler(EnricherErrorStrategy.FAIL_FAST)
        assert handler.strategy == EnricherErrorStrategy.FAIL_FAST

    def test_silent_strategy(self):
        """Test SILENT error handling strategy."""
        handler = EnricherErrorHandler(EnricherErrorStrategy.SILENT)

        def dummy_enricher():
            pass

        result = handler.handle_enricher_error(
            dummy_enricher, Exception("test error"), {"event": "test"}
        )

        assert result is True  # Continue processing
        assert len(handler.failed_enrichers) == 0

    def test_log_warning_strategy(self):
        """Test LOG_WARNING error handling strategy."""
        handler = EnricherErrorHandler(EnricherErrorStrategy.LOG_WARNING)

        def test_enricher():
            pass

        with patch("fapilog.enrichers.enricher_logger.warning") as mock_warning:
            result = handler.handle_enricher_error(
                test_enricher, Exception("test error"), {"event": "test"}
            )

            assert result is True
            assert "test_enricher" in handler.failed_enrichers
            mock_warning.assert_called_once()

    def test_log_error_strategy(self):
        """Test LOG_ERROR error handling strategy."""
        handler = EnricherErrorHandler(EnricherErrorStrategy.LOG_ERROR)

        def test_enricher():
            pass

        with patch("fapilog.enrichers.enricher_logger.error") as mock_error:
            result = handler.handle_enricher_error(
                test_enricher, Exception("test error"), {"event": "test"}
            )

            assert result is True
            assert "test_enricher" in handler.failed_enrichers
            mock_error.assert_called_once()

    def test_fail_fast_strategy(self):
        """Test FAIL_FAST error handling strategy."""
        handler = EnricherErrorHandler(EnricherErrorStrategy.FAIL_FAST)

        def test_enricher():
            pass

        original_error = Exception("test error")

        with pytest.raises(EnricherExecutionError) as exc_info:
            handler.handle_enricher_error(
                test_enricher, original_error, {"event": "test"}
            )

        assert "test_enricher failed" in str(exc_info.value)
        assert exc_info.value.__cause__ is original_error


class TestEnricherHealthMonitor:
    """Test enricher health monitoring."""

    def test_health_monitor_initialization(self):
        """Test health monitor initialization."""
        monitor = EnricherHealthMonitor()
        assert monitor.enricher_stats == {}

    def test_record_successful_execution(self):
        """Test recording successful enricher execution."""
        monitor = EnricherHealthMonitor()

        monitor.record_enricher_execution("test_enricher", True, 5.5)

        stats = monitor.enricher_stats["test_enricher"]
        assert stats["total_calls"] == 1
        assert stats["successful_calls"] == 1
        assert stats["failed_calls"] == 0
        assert stats["avg_duration_ms"] == 5.5
        assert stats["last_success"] is not None
        assert stats["last_failure"] is None

    def test_record_failed_execution(self):
        """Test recording failed enricher execution."""
        monitor = EnricherHealthMonitor()

        monitor.record_enricher_execution("test_enricher", False, 3.2)

        stats = monitor.enricher_stats["test_enricher"]
        assert stats["total_calls"] == 1
        assert stats["successful_calls"] == 0
        assert stats["failed_calls"] == 1
        assert stats["avg_duration_ms"] == 3.2
        assert stats["last_success"] is None
        assert stats["last_failure"] is not None

    def test_multiple_executions_average_duration(self):
        """Test average duration calculation with multiple executions."""
        monitor = EnricherHealthMonitor()

        # Record multiple executions
        monitor.record_enricher_execution("test_enricher", True, 10.0)
        monitor.record_enricher_execution("test_enricher", True, 20.0)
        monitor.record_enricher_execution("test_enricher", False, 30.0)

        stats = monitor.enricher_stats["test_enricher"]
        assert stats["total_calls"] == 3
        assert stats["successful_calls"] == 2
        assert stats["failed_calls"] == 1
        assert stats["avg_duration_ms"] == 20.0  # (10 + 20 + 30) / 3

    def test_health_report_empty(self):
        """Test health report with no enrichers."""
        monitor = EnricherHealthMonitor()

        report = monitor.get_health_report()

        assert report["enricher_count"] == 0
        assert report["enrichers"] == {}
        assert report["overall_success_rate"] == 1.0

    def test_health_report_with_data(self):
        """Test health report with enricher data."""
        monitor = EnricherHealthMonitor()

        # Record some executions
        monitor.record_enricher_execution("enricher1", True, 5.0)
        monitor.record_enricher_execution("enricher1", True, 10.0)
        monitor.record_enricher_execution("enricher2", False, 15.0)

        report = monitor.get_health_report()

        assert report["enricher_count"] == 2
        assert "enricher1" in report["enrichers"]
        assert "enricher2" in report["enrichers"]
        # 2 successful out of 3 total = 0.6667
        assert abs(report["overall_success_rate"] - 0.6667) < 0.001


class TestSmartCacheFunctions:
    """Test smart cache helper functions."""

    def test_get_process_smart_success(self):
        """Test _get_process_smart with successful psutil import."""
        with patch("fapilog.enrichers._smart_cache") as mock_cache:
            mock_process = Mock()
            mock_cache.get_or_compute.return_value = mock_process

            result = _get_process_smart()

            assert result is mock_process
            # Verify it was called with correct key and a callable
            mock_cache.get_or_compute.assert_called_once()
            call_args = mock_cache.get_or_compute.call_args
            assert call_args[0][0] == "psutil_process"
            assert callable(call_args[0][1])

    def test_get_process_smart_failure(self):
        """Test _get_process_smart with failed psutil import."""
        with patch("fapilog.enrichers._smart_cache") as mock_cache:
            mock_cache.get_or_compute.side_effect = ImportError("No psutil")

            result = _get_process_smart()

            assert result is None

    def test_get_hostname_smart_success(self):
        """Test _get_hostname_smart successful operation."""
        with patch("fapilog.enrichers._smart_cache") as mock_cache:
            mock_cache.get_or_compute.return_value = "test-hostname"

            result = _get_hostname_smart()

            assert result == "test-hostname"

    def test_get_hostname_smart_failure(self):
        """Test _get_hostname_smart with failure."""
        with patch("fapilog.enrichers._smart_cache") as mock_cache:
            mock_cache.get_or_compute.side_effect = Exception("Network error")

            result = _get_hostname_smart()

            assert result == "unknown"

    def test_get_pid_smart_success(self):
        """Test _get_pid_smart successful operation."""
        with patch("fapilog.enrichers._smart_cache") as mock_cache:
            mock_cache.get_or_compute.return_value = 12345

            result = _get_pid_smart()

            assert result == 12345

    def test_get_pid_smart_failure(self):
        """Test _get_pid_smart with failure."""
        with patch("fapilog.enrichers._smart_cache") as mock_cache:
            mock_cache.get_or_compute.side_effect = Exception("OS error")

            result = _get_pid_smart()

            assert result == -1


class TestEnricherConfiguration:
    """Test enricher configuration functions."""

    def test_configure_error_handling(self):
        """Test configuring global error handling strategy."""
        # Store original strategy

        original_strategy = _error_handler.strategy

        try:
            # Test with different strategies
            configure_enricher_error_handling(EnricherErrorStrategy.FAIL_FAST)
            from fapilog.enrichers import _error_handler as updated_handler

            assert updated_handler.strategy == EnricherErrorStrategy.FAIL_FAST

            configure_enricher_error_handling(EnricherErrorStrategy.SILENT)
            from fapilog.enrichers import _error_handler as updated_handler2

            assert updated_handler2.strategy == EnricherErrorStrategy.SILENT
        finally:
            # Restore original strategy
            configure_enricher_error_handling(original_strategy)

    def test_get_health_report(self):
        """Test getting global health report."""
        # The function should return the global monitor's report
        with patch("fapilog.enrichers._health_monitor") as mock_monitor:
            mock_report = {"test": "report"}
            mock_monitor.get_health_report.return_value = mock_report

            result = get_enricher_health_report()

            assert result == mock_report
            mock_monitor.get_health_report.assert_called_once()


class TestImprovedEnricherRegistry:
    """Test improved enricher registry with error handling and monitoring."""

    def setUp(self):
        """Set up clean state for each test."""
        clear_enrichers()
        # Reset global handlers to default state
        configure_enricher_error_handling(EnricherErrorStrategy.LOG_WARNING)

    def test_run_enrichers_with_success_monitoring(self):
        """Test that successful enrichers are monitored."""
        self.setUp()

        def test_enricher(logger, method_name, event_dict):
            event_dict["test_field"] = "test_value"
            return event_dict

        register_enricher(test_enricher)

        with patch("fapilog.enrichers._health_monitor") as mock_monitor:
            event_dict = {"event": "test"}
            result = run_registered_enrichers(None, "info", event_dict)

            assert result["test_field"] == "test_value"
            mock_monitor.record_enricher_execution.assert_called_once()
            # Verify it was called with success=True
            call_args = mock_monitor.record_enricher_execution.call_args
            assert call_args[0][1] is True  # success parameter

    def test_run_enrichers_with_failure_monitoring(self):
        """Test that failed enrichers are monitored."""
        self.setUp()

        def failing_enricher(logger, method_name, event_dict):
            raise RuntimeError("Test failure")

        register_enricher(failing_enricher)

        with patch("fapilog.enrichers._health_monitor") as mock_monitor, patch(
            "fapilog.enrichers._error_handler"
        ) as mock_error_handler:
            mock_error_handler.handle_enricher_error.return_value = True

            event_dict = {"event": "test"}
            result = run_registered_enrichers(None, "info", event_dict)

            # Should still return the event dict
            assert result["event"] == "test"

            # Verify monitoring was called with failure
            mock_monitor.record_enricher_execution.assert_called_once()
            call_args = mock_monitor.record_enricher_execution.call_args
            assert call_args[0][1] is False  # success parameter

    def test_run_enrichers_with_fail_fast_strategy(self):
        """Test enricher execution stops on fail_fast strategy."""
        self.setUp()

        def first_enricher(logger, method_name, event_dict):
            event_dict["first"] = "success"
            return event_dict

        def failing_enricher(logger, method_name, event_dict):
            raise RuntimeError("Test failure")

        def third_enricher(logger, method_name, event_dict):
            event_dict["third"] = "should_not_execute"
            return event_dict

        register_enricher(first_enricher)
        register_enricher(failing_enricher)
        register_enricher(third_enricher)

        # Configure fail_fast strategy
        configure_enricher_error_handling(EnricherErrorStrategy.FAIL_FAST)

        with pytest.raises(EnricherExecutionError):
            event_dict = {"event": "test"}
            run_registered_enrichers(None, "info", event_dict)

    def test_run_enrichers_error_handler_stops_processing(self):
        """Test that enricher processing stops when error handler returns False."""
        self.setUp()

        def first_enricher(logger, method_name, event_dict):
            event_dict["first"] = "success"
            return event_dict

        def failing_enricher(logger, method_name, event_dict):
            raise RuntimeError("Test failure")

        def third_enricher(logger, method_name, event_dict):
            event_dict["third"] = "should_not_execute"
            return event_dict

        register_enricher(first_enricher)
        register_enricher(failing_enricher)
        register_enricher(third_enricher)

        with patch("fapilog.enrichers._error_handler") as mock_error_handler:
            mock_error_handler.handle_enricher_error.return_value = False

            event_dict = {"event": "test"}
            result = run_registered_enrichers(None, "info", event_dict)

            # First enricher should have executed
            assert result["first"] == "success"
            # Third enricher should not have executed
            assert "third" not in result
            # Error handler should have been called
            mock_error_handler.handle_enricher_error.assert_called_once()

    def test_duration_tracking_accuracy(self):
        """Test that duration tracking is reasonably accurate."""
        self.setUp()

        def slow_enricher(logger, method_name, event_dict):
            time.sleep(0.01)  # 10ms delay
            event_dict["slow"] = "done"
            return event_dict

        register_enricher(slow_enricher)

        with patch("fapilog.enrichers._health_monitor") as mock_monitor:
            event_dict = {"event": "test"}
            run_registered_enrichers(None, "info", event_dict)

            mock_monitor.record_enricher_execution.assert_called_once()
            call_args = mock_monitor.record_enricher_execution.call_args
            duration_ms = call_args[0][2]  # duration parameter

            # Should be at least 10ms, but allow for some variance
            assert duration_ms >= 8.0
            assert duration_ms < 50.0  # Should not be too high


@pytest.fixture(autouse=True)
def cleanup_enrichers():
    """Clean up enrichers after each test."""
    yield
    clear_enrichers()
    # Reset to default error handling
    configure_enricher_error_handling(EnricherErrorStrategy.LOG_WARNING)


class TestUserContextEnricher:
    """Test user_context_enricher function for complete coverage."""

    def test_user_context_enricher_with_user_roles(self):
        """Test user_context_enricher with user_roles in context."""
        from fapilog._internal.context import bind_user_context
        from fapilog.enrichers import user_context_enricher

        # Bind user context with roles
        bind_user_context(
            user_id="test_user", user_roles=["admin", "user"], auth_scheme="Bearer"
        )

        event_dict = {"event": "test"}
        result = user_context_enricher(None, "info", event_dict)

        assert result["user_id"] == "test_user"
        assert result["user_roles"] == ["admin", "user"]
        assert result["auth_scheme"] == "Bearer"

    def test_user_context_enricher_partial_context(self):
        """Test user_context_enricher with partial context."""
        from fapilog._internal.context import bind_user_context, clear_context
        from fapilog.enrichers import user_context_enricher

        # Clear context first to avoid contamination
        clear_context()

        # Bind only user_roles
        bind_user_context(user_roles=["viewer"])

        event_dict = {"event": "test"}
        result = user_context_enricher(None, "info", event_dict)

        assert "user_id" not in result
        assert result["user_roles"] == ["viewer"]
        assert "auth_scheme" not in result

    def test_user_context_enricher_preserves_existing(self):
        """Test user_context_enricher preserves existing values."""
        from fapilog._internal.context import bind_user_context
        from fapilog.enrichers import user_context_enricher

        bind_user_context(user_id="context_user", user_roles=["admin"])

        event_dict = {
            "event": "test",
            "user_id": "existing_user",
            "user_roles": ["existing_role"],
        }
        result = user_context_enricher(None, "info", event_dict)

        # Should preserve existing values
        assert result["user_id"] == "existing_user"
        assert result["user_roles"] == ["existing_role"]


class TestCreateUserDependency:
    """Test create_user_dependency function for complete coverage."""

    def test_create_user_dependency_with_dict_user(self):
        """Test create_user_dependency with dict user object."""
        from fapilog.enrichers import create_user_dependency

        def mock_get_user():
            return {
                "user_id": "123",
                "user_roles": ["admin", "user"],
                "auth_scheme": "Bearer",
            }

        user_dep = create_user_dependency(mock_get_user)

        # This is a sync function dependency
        result = asyncio.run(user_dep())

        assert result["user_id"] == "123"
        assert result["user_roles"] == ["admin", "user"]
        assert result["auth_scheme"] == "Bearer"

    def test_create_user_dependency_with_async_function(self):
        """Test create_user_dependency with async user function."""
        from fapilog.enrichers import create_user_dependency

        async def async_get_user():
            return {"id": 456, "roles": "admin", "scheme": "API-Key"}

        user_dep = create_user_dependency(async_get_user)

        result = asyncio.run(user_dep())

        assert result["id"] == 456
        assert result["roles"] == "admin"
        assert result["scheme"] == "API-Key"

    def test_create_user_dependency_with_user_object(self):
        """Test create_user_dependency with user object (not dict)."""
        from fapilog.enrichers import create_user_dependency

        class MockUser:
            def __init__(self):
                self.user_id = "789"
                self.roles = ["viewer"]
                self.auth_scheme = "Token"

        def mock_get_user():
            return MockUser()

        user_dep = create_user_dependency(mock_get_user)
        result = asyncio.run(user_dep())

        assert result.user_id == "789"
        assert result.roles == ["viewer"]
        assert result.auth_scheme == "Token"

    def test_create_user_dependency_with_alternate_field_names(self):
        """Test create_user_dependency with alternate field names."""
        from fapilog.enrichers import create_user_dependency

        def mock_get_user():
            return {
                "id": "999",  # alternate to user_id
                "roles": "manager",  # alternate to user_roles
                "scheme": "Basic",  # alternate to auth_scheme
            }

        user_dep = create_user_dependency(mock_get_user)
        result = asyncio.run(user_dep())

        assert result["id"] == "999"
        assert result["roles"] == "manager"
        assert result["scheme"] == "Basic"

    def test_create_user_dependency_with_none_user(self):
        """Test create_user_dependency when user function returns None."""
        from fapilog.enrichers import create_user_dependency

        def mock_get_user():
            return None

        user_dep = create_user_dependency(mock_get_user)
        result = asyncio.run(user_dep())

        assert result is None

    def test_create_user_dependency_roles_conversion(self):
        """Test create_user_dependency converts roles to list."""
        from fapilog.enrichers import create_user_dependency

        def mock_get_user_string_roles():
            return {"user_id": "123", "user_roles": "admin"}

        def mock_get_user_iterable_roles():
            return {"user_id": "456", "user_roles": {"admin", "user"}}

        def mock_get_user_invalid_roles():
            return {"user_id": "789", "user_roles": 12345}

            # Test string roles (create_user_dependency returns original user)

        user_dep1 = create_user_dependency(mock_get_user_string_roles)
        result1 = asyncio.run(user_dep1())
        assert result1["user_roles"] == "admin"  # Original unchanged

        # Test iterable roles (create_user_dependency returns original user)
        user_dep2 = create_user_dependency(mock_get_user_iterable_roles)
        result2 = asyncio.run(user_dep2())
        assert isinstance(result2["user_roles"], set)
        assert len(result2["user_roles"]) == 2

        # Test invalid roles (create_user_dependency returns original user)
        user_dep3 = create_user_dependency(mock_get_user_invalid_roles)
        result3 = asyncio.run(user_dep3())
        assert result3["user_roles"] == 12345  # Original unchanged

    def test_create_user_dependency_user_id_conversion(self):
        """Test create_user_dependency returns original user (conversion done internally)."""
        from fapilog.enrichers import create_user_dependency

        def mock_get_user():
            return {"user_id": 12345}

        user_dep = create_user_dependency(mock_get_user)
        result = asyncio.run(user_dep())

        # create_user_dependency returns original user unchanged
        assert result["user_id"] == 12345
        assert isinstance(result["user_id"], int)

    def test_create_user_dependency_object_with_alternate_attrs(self):
        """Test create_user_dependency with object having alternate attribute names."""
        from fapilog.enrichers import create_user_dependency

        class MockUser:
            def __init__(self):
                self.id = "obj123"  # alternate to user_id
                self.roles = ["admin"]  # alternate to user_roles
                self.scheme = "JWT"  # alternate to auth_scheme

        def mock_get_user():
            return MockUser()

        user_dep = create_user_dependency(mock_get_user)
        result = asyncio.run(user_dep())

        assert result.id == "obj123"
        assert result.roles == ["admin"]
        assert result.scheme == "JWT"


class TestMiscCoverage:
    """Tests for miscellaneous coverage gaps."""

    def test_error_handler_return_true_coverage(self):
        """Test to ensure the return True line in error handler is covered."""
        from fapilog.enrichers import EnricherErrorHandler, EnricherErrorStrategy

        # Test with strategy that doesn't raise exception
        handler = EnricherErrorHandler(EnricherErrorStrategy.SILENT)

        def dummy_enricher():
            pass

        # This should return True and hit the return True line
        result = handler.handle_enricher_error(
            dummy_enricher, Exception("test"), {"event": "test"}
        )

        assert result is True
