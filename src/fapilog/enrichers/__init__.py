"""Enrichers package for fapilog."""

# Export base enricher functionality
from .base import clear_enrichers, register_enricher, run_registered_enrichers

# Export cache functionality
from .cache import AsyncSmartCache, CacheEntry, CacheEntryManager, clear_smart_cache

# Export health and error handling
from .health import (
    EnricherErrorHandler,
    EnricherErrorStrategy,
    EnricherExecutionError,
    EnricherHealthMonitor,
    configure_enricher_error_handling,
    get_enricher_health_report,
)

# Export request enrichers
from .request import body_size_enricher, request_response_enricher

# Export system enrichers
# Export cache helper functions from system for backward compatibility
from .system import (
    RetryCoordinator,
    _get_hostname_smart,
    _get_pid_smart,
    _get_process_smart,
    host_process_enricher,
    host_process_enricher_sync,
    resource_snapshot_enricher,
    resource_snapshot_enricher_sync,
)

# Export user enrichers
from .user import create_user_dependency, user_context_enricher

__all__ = [
    # Base functionality
    "register_enricher",
    "clear_enrichers",
    "run_registered_enrichers",
    # Cache classes and functions
    "AsyncSmartCache",
    "CacheEntry",
    "CacheEntryManager",
    "clear_smart_cache",
    # Health and error handling
    "EnricherErrorStrategy",
    "EnricherErrorHandler",
    "EnricherHealthMonitor",
    "EnricherExecutionError",
    "configure_enricher_error_handling",
    "get_enricher_health_report",
    # Request enrichers
    "body_size_enricher",
    "request_response_enricher",
    # System enrichers
    "host_process_enricher",
    "resource_snapshot_enricher",
    "RetryCoordinator",
    # Sync wrappers
    "host_process_enricher_sync",
    "resource_snapshot_enricher_sync",
    # User enrichers
    "user_context_enricher",
    "create_user_dependency",
    # Cache helpers for backward compatibility
    "_get_hostname_smart",
    "_get_pid_smart",
    "_get_process_smart",
]
