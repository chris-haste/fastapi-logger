"""Metrics collection functionality for fapilog."""

import logging

logger = logging.getLogger(__name__)


def get_metrics_text() -> str:
    """Get the current metrics in Prometheus text format.

    Note: This function uses a per-call MetricsCollector instance and will
    return empty metrics unless used with container-scoped access.
    For container-scoped metrics, use container.get_metrics_collector().get_prometheus_metrics().

    Returns:
        Prometheus formatted metrics string
    """
    # Return message indicating container-scoped access is required
    return "# Metrics collection is disabled (use container-scoped access)\n"


def get_metrics_dict() -> dict:
    """Get the current metrics as a dictionary.

    Note: This function uses a per-call MetricsCollector instance and will
    return empty metrics unless used with container-scoped access.
    For container-scoped metrics, use container.get_metrics_collector().get_all_metrics().

    Returns:
        Dictionary containing all current metrics
    """
    # Create a new instance per call to avoid global state
    # This will return empty metrics since metrics aren't shared
    return {"_note": "Metrics collection disabled - use container-scoped access"}


class MetricsCollector:
    """Placeholder for MetricsCollector class that exists in _internal.metrics."""

    def __init__(self):
        """Initialize metrics collector."""
        logger.warning(
            "MetricsCollector should be accessed via container for proper lifecycle management"
        )

    def get_prometheus_metrics(self) -> str:
        """Get metrics in Prometheus format."""
        return get_metrics_text()

    def get_all_metrics(self) -> dict:
        """Get all metrics as dictionary."""
        return get_metrics_dict()
