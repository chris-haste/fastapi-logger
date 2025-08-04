"""System enrichers for fapilog (hostname, PID, resource monitoring)."""

import asyncio
import os
import socket
from typing import Any, Callable, Dict, Optional, cast


async def _get_hostname_smart() -> str:
    """Get hostname using async SmartCache with fallback error handling.

    Note: This function uses a per-call AsyncSmartCache instance and will not
    cache across calls unless used with container-scoped access.
    For container-scoped caching, use container.get_async_smart_cache().
    """
    try:
        # Import here to avoid circular imports
        from .cache import AsyncSmartCache

        # Create a new instance per call to avoid global state
        # This will not cache across calls since cache isn't shared
        cache = AsyncSmartCache()
        return cast(
            str, await cache.get_or_compute("hostname", lambda: socket.gethostname())
        )
    except Exception:
        return "unknown"


async def _get_pid_smart() -> int:
    """Get process ID using async SmartCache with fallback error handling.

    Note: This function uses a per-call AsyncSmartCache instance and will not
    cache across calls unless used with container-scoped access.
    For container-scoped caching, use container.get_async_smart_cache().
    """
    try:
        # Import here to avoid circular imports
        from .cache import AsyncSmartCache

        # Create a new instance per call to avoid global state
        # This will not cache across calls since cache isn't shared
        cache = AsyncSmartCache()
        return cast(int, await cache.get_or_compute("pid", lambda: os.getpid()))
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

    # Import here to avoid circular imports
    from .cache import AsyncSmartCache

    # Create a new instance per call to avoid global state
    # This will not cache across calls since cache isn't shared
    cache = AsyncSmartCache()
    return await cache.get_or_compute("psutil_process", _create_process)


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


def host_process_enricher_sync(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Sync wrapper for structlog pipeline compatibility.

    This wrapper allows the async host_process_enricher to work with
    structlog's sync processor model by running the async version.

    Note: For direct usage, prefer the async version for better performance.
    """
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
