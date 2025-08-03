"""Base enricher functionality and registry for fapilog."""

import inspect
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List

from ..exceptions import ConfigurationError

# Logger for enricher-related issues
enricher_logger = logging.getLogger(__name__)

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
    # Import here to avoid circular imports
    from .health import EnricherErrorHandler, EnricherHealthMonitor

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
