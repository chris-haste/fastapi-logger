"""Enrichers for adding metadata to log events."""

import asyncio
import logging
import os
import socket
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Set

from ._internal.context import get_context
from .exceptions import ConfigurationError

if TYPE_CHECKING:
    import psutil

# Logger for enricher-related issues
enricher_logger = logging.getLogger(__name__)

# Public API
__all__ = [
    # Core classes
    "SmartCache",
    "CacheEntry",
    "EnricherErrorStrategy",
    "EnricherErrorHandler",
    "EnricherHealthMonitor",
    "EnricherExecutionError",
    # Configuration functions
    "configure_enricher_error_handling",
    "get_enricher_health_report",
    "clear_smart_cache",
    # Enricher functions
    "host_process_enricher",
    "resource_snapshot_enricher",
    "body_size_enricher",
    "request_response_enricher",
    "user_context_enricher",
    "create_user_dependency",
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


class SmartCache:
    """Cache that handles failures gracefully with retry logic."""

    def __init__(self, retry_interval: timedelta = timedelta(minutes=5)):
        self._cache: Dict[str, CacheEntry] = {}
        self.retry_interval = retry_interval

    def get_or_compute(self, key: str, compute_func: Callable) -> Any:
        """Get cached value or compute new one with retry logic."""
        entry = self._cache.get(key)
        now = datetime.now()

        # Check if we should retry a failed computation
        if entry and entry.is_error and entry.retry_after and now >= entry.retry_after:
            # Retry the computation
            entry = None

        if entry is None or (
            entry.is_error and entry.retry_after and now >= entry.retry_after
        ):
            try:
                value = compute_func()
                self._cache[key] = CacheEntry(
                    value=value, cached_at=now, is_error=False
                )
                return value
            except Exception:
                retry_after = now + self.retry_interval
                self._cache[key] = CacheEntry(
                    value=None, cached_at=now, is_error=True, retry_after=retry_after
                )
                raise

        if entry.is_error:
            raise RuntimeError(f"Cached error for {key}")

        return entry.value


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


# Global smart cache instance
_smart_cache = SmartCache()

# Global error handler and health monitor
_error_handler = EnricherErrorHandler()
_health_monitor = EnricherHealthMonitor()


def configure_enricher_error_handling(strategy: EnricherErrorStrategy) -> None:
    """Configure global enricher error handling strategy."""
    global _error_handler
    _error_handler = EnricherErrorHandler(strategy)


def get_enricher_health_report() -> Dict[str, Any]:
    """Get current enricher health report."""
    return _health_monitor.get_health_report()


def _create_process() -> "psutil.Process":
    """Create psutil process - may raise ImportError."""
    import psutil

    return psutil.Process()


def _get_process_smart() -> Optional["psutil.Process"]:
    """Get process with smart caching and retry logic."""
    try:
        return _smart_cache.get_or_compute("psutil_process", _create_process)
    except Exception:
        return None  # Graceful degradation


def _create_hostname() -> str:
    """Create hostname - cached computation."""
    return socket.gethostname()


def _get_hostname_smart() -> str:
    """Get hostname with smart caching."""
    try:
        return _smart_cache.get_or_compute("hostname", _create_hostname)
    except Exception:
        return "unknown"  # Fallback value


def _create_pid() -> int:
    """Create process ID - cached computation."""
    return os.getpid()


def _get_pid_smart() -> int:
    """Get process ID with smart caching."""
    try:
        return _smart_cache.get_or_compute("pid", _create_pid)
    except Exception:
        return -1  # Fallback value


def host_process_enricher(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Enrich log events with hostname and process ID.

    This processor adds system metadata to every log event:
    - hostname: System hostname (via socket.gethostname())
    - pid: Process ID (via os.getpid())

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
        event_dict["hostname"] = _get_hostname_smart()

    # Add pid if not already present or if it's None
    if "pid" not in event_dict or event_dict["pid"] is None:
        event_dict["pid"] = _get_pid_smart()

    return event_dict


def resource_snapshot_enricher(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Enrich log events with memory and CPU usage metrics.

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
    process = _get_process_smart()
    if process is None:
        # psutil not available, skip enrichment
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

    Args:
        logger: The logger instance
        method_name: The logging method name
        event_dict: The event dictionary to enrich

    Returns:
        The enriched event dictionary
    """
    result = event_dict
    for enricher in _registered_enrichers:
        enricher_name = getattr(enricher, "__name__", str(enricher))
        start_time = datetime.now()

        try:
            result = enricher(logger, method_name, result)
            # Record successful execution
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            _health_monitor.record_enricher_execution(enricher_name, True, duration_ms)

        except Exception as e:
            # Record failed execution
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            _health_monitor.record_enricher_execution(enricher_name, False, duration_ms)

            # Handle error according to strategy
            should_continue = _error_handler.handle_enricher_error(enricher, e, result)
            if not should_continue:
                break

    return result


def clear_smart_cache() -> None:
    """Clear the global smart cache for testing purposes."""
    global _smart_cache
    _smart_cache._cache.clear()
