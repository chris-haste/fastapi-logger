"""Enrichers for adding metadata to log events."""

import asyncio
import logging
import os
import socket
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from ._internal.context import get_context
from .exceptions import ConfigurationError

# Logger for enricher-related issues
enricher_logger = logging.getLogger(__name__)

# Public API
__all__ = [
    # Core classes
    "AsyncSmartCache",
    "CacheEntry",
    "CacheEntryManager",
    "EnricherErrorStrategy",
    "EnricherErrorHandler",
    "EnricherHealthMonitor",
    "EnricherExecutionError",
    "RetryCoordinator",
    # Configuration functions
    "configure_enricher_error_handling",
    "get_enricher_health_report",
    "clear_smart_cache",
    # Async SmartCache integration functions
    "_get_hostname_smart",
    "_get_pid_smart",
    "_get_process_smart",
    # Enricher functions (now async - BREAKING CHANGE)
    "host_process_enricher",
    "resource_snapshot_enricher",
    "body_size_enricher",
    "request_response_enricher",
    "user_context_enricher",
    "create_user_dependency",
    # Sync wrapper functions for pipeline compatibility
    "host_process_enricher_sync",
    "resource_snapshot_enricher_sync",
    # Registry functions
    "register_enricher",
    "clear_enrichers",
    "run_registered_enrichers",
]


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


class EnricherErrorStrategy(Enum):
    """Error handling strategies for enricher failures."""

    SILENT = "silent"  # Current behavior - continue silently
    LOG_WARNING = "log_warning"  # Log warning but continue
    LOG_ERROR = "log_error"  # Log error but continue
    FAIL_FAST = "fail_fast"  # Raise exception immediately


class EnricherExecutionError(Exception):
    """Exception raised when enricher execution fails and fail_fast is enabled."""

    pass


class EnricherErrorHandler:
    """Handles enricher errors according to configured strategy."""

    def __init__(
        self, strategy: EnricherErrorStrategy = EnricherErrorStrategy.LOG_WARNING
    ):
        self.strategy = strategy
        self.failed_enrichers: Set[str] = set()

    def handle_enricher_error(
        self, enricher: Callable, error: Exception, event_dict: Dict[str, Any]
    ) -> bool:
        """Handle enricher error according to strategy.

        Returns:
            bool: True to continue processing, False to stop
        """
        enricher_name = getattr(enricher, "__name__", str(enricher))

        if self.strategy == EnricherErrorStrategy.SILENT:
            return True  # Continue processing
        elif self.strategy == EnricherErrorStrategy.LOG_WARNING:
            enricher_logger.warning(
                f"Enricher {enricher_name} failed: {error}", exc_info=True
            )
            self.failed_enrichers.add(enricher_name)
            return True
        elif self.strategy == EnricherErrorStrategy.LOG_ERROR:
            enricher_logger.error(
                f"Enricher {enricher_name} failed: {error}", exc_info=True
            )
            self.failed_enrichers.add(enricher_name)
            return True
        elif self.strategy == EnricherErrorStrategy.FAIL_FAST:
            raise EnricherExecutionError(f"Enricher {enricher_name} failed") from error

        return True


class EnricherHealthMonitor:
    """Monitor enricher health and availability."""

    def __init__(self):
        self.enricher_stats: Dict[str, Dict[str, Any]] = {}

    def record_enricher_execution(
        self, enricher_name: str, success: bool, duration_ms: float
    ):
        """Record enricher execution statistics."""
        if enricher_name not in self.enricher_stats:
            self.enricher_stats[enricher_name] = {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "avg_duration_ms": 0.0,
                "last_success": None,
                "last_failure": None,
            }

        stats = self.enricher_stats[enricher_name]
        stats["total_calls"] += 1

        if success:
            stats["successful_calls"] += 1
            stats["last_success"] = datetime.now()
        else:
            stats["failed_calls"] += 1
            stats["last_failure"] = datetime.now()

        # Update average duration
        current_avg = stats["avg_duration_ms"]
        total_calls = stats["total_calls"]
        stats["avg_duration_ms"] = (
            (current_avg * (total_calls - 1)) + duration_ms
        ) / total_calls

    def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report for all enrichers."""
        return {
            "enricher_count": len(self.enricher_stats),
            "enrichers": self.enricher_stats.copy(),
            "overall_success_rate": self._calculate_overall_success_rate(),
        }

    def _calculate_overall_success_rate(self) -> float:
        """Calculate overall success rate across all enrichers."""
        if not self.enricher_stats:
            return 1.0

        total_calls = sum(
            stats["total_calls"] for stats in self.enricher_stats.values()
        )
        total_successful = sum(
            stats["successful_calls"] for stats in self.enricher_stats.values()
        )

        return total_successful / total_calls if total_calls > 0 else 1.0


# Note: Global instances removed in Issue 165 - use container-scoped access


# ============================================================================
# Async SmartCache Integration Functions
# ============================================================================


async def _get_hostname_smart() -> str:
    """Get hostname using async SmartCache with fallback error handling.

    Note: This function uses a per-call AsyncSmartCache instance and will not
    cache across calls unless used with container-scoped access.
    For container-scoped caching, use container.get_async_smart_cache().
    """
    try:
        # Create a new instance per call to avoid global state
        # This will not cache across calls since cache isn't shared
        cache = AsyncSmartCache()
        return await cache.get_or_compute("hostname", lambda: socket.gethostname())
    except Exception:
        return "unknown"


async def _get_pid_smart() -> int:
    """Get process ID using async SmartCache with fallback error handling.

    Note: This function uses a per-call AsyncSmartCache instance and will not
    cache across calls unless used with container-scoped access.
    For container-scoped caching, use container.get_async_smart_cache().
    """
    try:
        # Create a new instance per call to avoid global state
        # This will not cache across calls since cache isn't shared
        cache = AsyncSmartCache()
        return await cache.get_or_compute("pid", lambda: os.getpid())
    except Exception:
        return -1


async def _get_process_smart() -> Optional[Any]:
    """Get psutil Process instance using async SmartCache with error handling.

    Note: This function uses a per-call AsyncSmartCache instance and will not
    cache across calls unless used with container-scoped access.
    For container-scoped caching, use container.get_async_smart_cache().
    """

    def _create_process():
        try:
            import psutil

            return psutil.Process()
        except ImportError:
            return None
        except Exception:
            return None

    # Create a new instance per call to avoid global state
    # This will not cache across calls since cache isn't shared
    cache = AsyncSmartCache()
    return await cache.get_or_compute("psutil_process", _create_process)


# ============================================================================
# RetryCoordinator for Clean Retry Mechanism
# ============================================================================


class RetryCoordinator:
    """Coordinates retry attempts across multiple enrichers to prevent conflicts."""

    def __init__(self):
        self._retry_locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    async def get_retry_lock(self, key: str) -> asyncio.Lock:
        """Get or create a retry lock for a specific cache key."""
        async with self._global_lock:
            if key not in self._retry_locks:
                self._retry_locks[key] = asyncio.Lock()
            return self._retry_locks[key]

    async def coordinate_retry(self, key: str, retry_func: Callable) -> Any:
        """Coordinate a retry attempt for a specific cache key."""
        retry_lock = await self.get_retry_lock(key)
        async with retry_lock:
            return await retry_func()


# Note: Global retry coordinator removed in Issue 165 - use container-scoped access


# ============================================================================
# Configuration Functions
# ============================================================================


def configure_enricher_error_handling(strategy: EnricherErrorStrategy) -> None:
    """Configure enricher error handling strategy.

    Note: This function has no effect since global enricher state was removed in Issue 165.
    For container-scoped error handling, use:
    container.get_enricher_error_handler().strategy = strategy
    """
    # This function is kept for backward compatibility but has no effect
    # since global enricher state was removed in Issue 165
    pass


def get_enricher_health_report() -> Dict[str, Any]:
    """Get current enricher health report.

    Note: This function uses a per-call EnricherHealthMonitor instance and will
    return empty health report unless enrichers have been used with the same monitor.
    For container-scoped health monitoring, use container.get_enricher_health_monitor().
    """
    # Create a new instance per call to avoid global state
    # This will return empty health report since monitors aren't shared
    monitor = EnricherHealthMonitor()
    return monitor.get_health_report()


# ============================================================================
# Async Enricher Implementations (Breaking Changes)
# ============================================================================


async def host_process_enricher(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Enrich log events with hostname and process ID using async SmartCache.

    This processor adds system metadata to every log event:
    - hostname: System hostname (cached via async SmartCache)
    - pid: Process ID (cached via async SmartCache)

    These fields are only added if not already present in the event_dict,
    allowing manual override of these values.

    Args:
        logger: The logger instance
        method_name: The logging method name
        event_dict: The event dictionary to enrich

    Returns:
        The enriched event dictionary
    """
    # Add hostname if not already present or if it's None
    if "hostname" not in event_dict or event_dict["hostname"] is None:
        event_dict["hostname"] = await _get_hostname_smart()

    # Add pid if not already present or if it's None
    if "pid" not in event_dict or event_dict["pid"] is None:
        event_dict["pid"] = await _get_pid_smart()

    return event_dict


async def resource_snapshot_enricher(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Enrich log events with memory and CPU usage metrics using async SmartCache.

    This processor adds system resource metrics to every log event:
    - memory_mb: Resident memory usage of the current process in megabytes (rounded float)
    - cpu_percent: Process CPU usage percentage (float, 0.0-100.0)

    These fields are only added if not already present in the event_dict,
    allowing manual override of these values.

    Args:
        logger: The logger instance
        method_name: The logging method name
        event_dict: The event dictionary to enrich

    Returns:
        The enriched event dictionary
    """
    # Get cached process instance via async SmartCache
    process = await _get_process_smart()
    if process is None:
        # psutil not available or process creation failed, skip enrichment
        return event_dict

    try:
        # Add memory_mb if not already present or if it's None
        if "memory_mb" not in event_dict or event_dict["memory_mb"] is None:
            memory_info = process.memory_info()
            memory_mb = round(memory_info.rss / (1024 * 1024), 2)
            event_dict["memory_mb"] = memory_mb

        # Add cpu_percent if not already present or if it's None
        if "cpu_percent" not in event_dict or event_dict["cpu_percent"] is None:
            cpu_percent = process.cpu_percent(interval=None)
            event_dict["cpu_percent"] = round(cpu_percent, 2)

    except (OSError, AttributeError):
        # Handle cases where process info cannot be retrieved
        # (e.g., process terminated, permission issues)
        pass

    return event_dict


def body_size_enricher(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Enrich log events with request and response body sizes.

    This processor reads from context variables populated by TraceIDMiddleware
    and adds request/response body size metadata to every event:
    - req_bytes: Size of request body in bytes (0 if no body or streaming)
    - res_bytes: Size of response body in bytes (0 if streaming)

    These values are extracted by TraceIDMiddleware and stored in contextvars.
    Works for standard JSON, form, and plain requests; req_bytes falls back to
    Content-Length header if body not read. res_bytes is set based on
    len(response.body) (when available).

    Args:
        logger: The logger instance
        method_name: The logging method name
        event_dict: The event dictionary to enrich

    Returns:
        The enriched event dictionary
    """
    # Get context metadata
    context = get_context()

    # Add req_bytes if available in context
    req_bytes = context.get("req_bytes")
    if req_bytes is not None:
        event_dict["req_bytes"] = req_bytes

    # Add res_bytes if available in context
    res_bytes = context.get("res_bytes")
    if res_bytes is not None:
        event_dict["res_bytes"] = res_bytes

    return event_dict


def request_response_enricher(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Enrich log events with request and response metadata.

    This processor reads from context variables populated by TraceIDMiddleware
    and adds request/response metadata to every event:
    - status_code: HTTP status integer
    - latency_ms: Request latency in milliseconds
    - req_bytes: Size of request body in bytes (0 if no body or streaming)
    - res_bytes: Size of response body in bytes (0 if streaming)
    - user_agent: Value of User-Agent header or "-"

    Args:
        logger: The logger instance
        method_name: The logging method name
        event_dict: The event dictionary to enrich

    Returns:
        The enriched event dictionary
    """
    # Get all context metadata
    context = get_context()

    # Add non-None values to event_dict
    for key, value in context.items():
        if value is not None:
            event_dict[key] = value

    return event_dict


def user_context_enricher(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Enrich log events with user authentication context.

    This processor reads user context variables and adds user authentication
    metadata to every event:
    - user_id: Authenticated user identifier
    - user_roles: List of user roles/scopes
    - auth_scheme: Authentication scheme (e.g., 'Bearer', 'Basic')

    Fields are only added if not already present in the event_dict,
    allowing manual override of these values. If no user is authenticated,
    the fields will be null.

    Args:
        logger: The logger instance
        method_name: The logging method name
        event_dict: The event dictionary to enrich

    Returns:
        The enriched event dictionary
    """
    context = get_context()

    # Add user_id if not already present and available in context
    if "user_id" not in event_dict:
        user_id = context.get("user_id")
        if user_id is not None:
            event_dict["user_id"] = user_id

    # Add user_roles if not already present and available in context
    if "user_roles" not in event_dict:
        user_roles = context.get("user_roles")
        if user_roles is not None:
            event_dict["user_roles"] = user_roles

    # Add auth_scheme if not already present and available in context
    if "auth_scheme" not in event_dict:
        auth_scheme = context.get("auth_scheme")
        if auth_scheme is not None:
            event_dict["auth_scheme"] = auth_scheme

    return event_dict


def create_user_dependency(get_user_func: Callable[..., Any]) -> Callable[..., Any]:
    """Create a FastAPI dependency that extracts user context and binds it.

    This factory function creates a FastAPI dependency that wraps your existing
    user authentication logic and automatically binds user context variables
    for logging enrichment.

    Args:
        get_user_func: Your existing FastAPI dependency function that returns
                      user information. This should be a callable that returns
                      a user object or dict with user information.

    Returns:
        A FastAPI dependency function that binds user context and returns
        the user object.

    Example:
        ```python
        from fastapi import Depends, HTTPException
        from fastapi.security import HTTPBearer
        from fapilog.enrichers import create_user_dependency

        security = HTTPBearer()

        def get_current_user_base(token: str = Depends(security)):
            # Your authentication logic here
            if not validate_token(token):
                raise HTTPException(401, "Invalid token")
            return {
                "user_id": "123",
                "roles": ["admin", "user"],
                "auth_scheme": "Bearer"
            }

        # Create the logging-aware dependency
        get_current_user = create_user_dependency(get_current_user_base)

        @app.get("/protected")
        async def protected_route(user = Depends(get_current_user)):
            # All logs in this request will automatically include user context
            log.info("Protected action", action="view_profile")
            return {"user": user}
        ```
    """
    from ._internal.context import bind_user_context

    async def user_dependency(*args: Any, **kwargs: Any) -> Any:
        """FastAPI dependency that extracts and binds user context."""
        # Call the original user function
        if asyncio.iscoroutinefunction(get_user_func):
            user = await get_user_func(*args, **kwargs)
        else:
            user = get_user_func(*args, **kwargs)

        # Extract user context from user object
        if user is not None:
            user_id = None
            user_roles = None
            auth_scheme = None

            # Handle different user object types
            if isinstance(user, dict):
                user_id = user.get("user_id") or user.get("id")
                user_roles = user.get("user_roles") or user.get("roles")
                auth_scheme = user.get("auth_scheme") or user.get("scheme")
            else:
                # Handle user objects with attributes
                user_id = getattr(user, "user_id", None) or getattr(user, "id", None)
                user_roles = getattr(user, "user_roles", None) or getattr(
                    user, "roles", None
                )
                auth_scheme = getattr(user, "auth_scheme", None) or getattr(
                    user, "scheme", None
                )

            # Convert user_id to string if it's not None
            if user_id is not None:
                user_id = str(user_id)

            # Ensure user_roles is a list if present
            if user_roles is not None and not isinstance(user_roles, list):
                if isinstance(user_roles, str):
                    user_roles = [user_roles]
                else:
                    # Try to convert iterable to list
                    try:
                        user_roles = list(user_roles)
                    except (TypeError, ValueError):
                        user_roles = [str(user_roles)]

            # Bind user context for logging enrichment
            bind_user_context(
                user_id=user_id,
                user_roles=user_roles,
                auth_scheme=auth_scheme,
            )

        return user

    return user_dependency


# Custom enricher registry
_registered_enrichers: List[Callable[..., Any]] = []


def register_enricher(fn: Callable[..., Any]) -> None:
    """Register a custom enricher function.

    Custom enrichers are called at the end of the processor chain, after all
    built-in enrichers. They follow the structlog processor signature:
    `(logger, method_name, event_dict) -> event_dict`

    Args:
        fn: The enricher function to register

    Raises:
        ValueError: If the function doesn't have the correct signature
    """
    # Validate function signature
    import inspect

    sig = inspect.signature(fn)
    params = list(sig.parameters.keys())

    if len(params) != 3 or params != ["logger", "method_name", "event_dict"]:
        raise ConfigurationError(
            f"Enricher function must have signature "
            f"(logger, method_name, event_dict), got {params}",
            "enricher_signature",
            params,
            "(logger, method_name, event_dict)",
        )

    # Check if function is already registered (by reference)
    if fn not in _registered_enrichers:
        _registered_enrichers.append(fn)


def clear_enrichers() -> None:
    """Clear all registered custom enrichers.

    This is primarily used for test isolation.
    """
    _registered_enrichers.clear()


def run_registered_enrichers(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Run all registered custom enrichers in registration order.

    Note: This function uses per-call EnricherHealthMonitor and EnricherErrorHandler
    instances and will not share state across calls. For container-scoped enricher
    management, use container.get_enricher_*() methods.

    Args:
        logger: The logger instance
        method_name: The logging method name
        event_dict: The event dictionary to enrich

    Returns:
        The enriched event dictionary
    """
    # Create per-call instances to avoid global state
    # This will not share state across calls since instances aren't shared
    health_monitor = EnricherHealthMonitor()
    error_handler = EnricherErrorHandler()

    result = event_dict
    for enricher in _registered_enrichers:
        enricher_name = getattr(enricher, "__name__", str(enricher))
        start_time = datetime.now()

        try:
            result = enricher(logger, method_name, result)
            # Record successful execution
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            health_monitor.record_enricher_execution(enricher_name, True, duration_ms)

        except Exception as e:
            # Record failed execution
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            health_monitor.record_enricher_execution(enricher_name, False, duration_ms)

            # Handle error according to strategy
            should_continue = error_handler.handle_enricher_error(enricher, e, result)
            if not should_continue:
                break

    return result


def clear_smart_cache() -> None:
    """Clear async smart cache for testing purposes.

    Note: This function has no effect since global async smart cache was removed in Issue 165.
    For container-scoped cache clearing, use:
    container.get_async_smart_cache()._cache.clear()
    """
    # This function is kept for backward compatibility but has no effect
    # since global async smart cache was removed in Issue 165
    pass


# ============================================================================
# Sync Wrappers for Pipeline/Structlog Compatibility
# ============================================================================


def host_process_enricher_sync(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Sync wrapper for structlog pipeline compatibility.

    This wrapper allows the async host_process_enricher to work with
    structlog's sync processor model by running the async version.

    Note: For direct usage, prefer the async version for better performance.
    """
    import asyncio

    try:
        # Try to run in existing event loop
        asyncio.get_running_loop()
        # If we're in an async context, we can't use asyncio.run()
        # Fall back to direct system calls for sync compatibility
        if "hostname" not in event_dict or event_dict["hostname"] is None:
            try:
                event_dict["hostname"] = socket.gethostname()
            except Exception:
                event_dict["hostname"] = "unknown"

        if "pid" not in event_dict or event_dict["pid"] is None:
            try:
                event_dict["pid"] = os.getpid()
            except Exception:
                event_dict["pid"] = -1

        return event_dict
    except RuntimeError:
        # No event loop running, safe to use asyncio.run()
        return asyncio.run(host_process_enricher(logger, method_name, event_dict))


def resource_snapshot_enricher_sync(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Sync wrapper for structlog pipeline compatibility.

    This wrapper allows the async resource_snapshot_enricher to work with
    structlog's sync processor model by running the async version.

    Note: For direct usage, prefer the async version for better performance.
    """
    import asyncio

    try:
        # Try to run in existing event loop
        asyncio.get_running_loop()
        # If we're in an async context, we can't use asyncio.run()
        # Fall back to direct system calls for sync compatibility
        try:
            import psutil

            process = psutil.Process()
        except ImportError:
            return event_dict

        try:
            if "memory_mb" not in event_dict or event_dict["memory_mb"] is None:
                memory_info = process.memory_info()
                memory_mb = round(memory_info.rss / (1024 * 1024), 2)
                event_dict["memory_mb"] = memory_mb

            if "cpu_percent" not in event_dict or event_dict["cpu_percent"] is None:
                cpu_percent = process.cpu_percent(interval=None)
                event_dict["cpu_percent"] = round(cpu_percent, 2)
        except (OSError, AttributeError):
            pass

        return event_dict
    except RuntimeError:
        # No event loop running, safe to use asyncio.run()
        return asyncio.run(resource_snapshot_enricher(logger, method_name, event_dict))
