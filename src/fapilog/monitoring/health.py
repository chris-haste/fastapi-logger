"""Health monitoring for fapilog processors and system components."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_processor_health_status() -> dict:
    """Get health status for all processors.

    Returns:
        Dictionary mapping processor names to health status strings
    """
    try:
        stats = get_processor_performance_stats()
        if "error" in stats:
            return stats

        health = {}

        for processor_name, processor_stats in stats.items():
            if processor_stats.get("total_executions", 0) == 0:
                health[processor_name] = "unknown"
            elif processor_stats.get("failure_rate", 0) > 10:  # >10% failure rate
                health[processor_name] = "unhealthy"
            elif processor_stats.get("average_latency_ms", 0) > 100:  # >100ms avg
                health[processor_name] = "slow"
            else:
                health[processor_name] = "healthy"

        return health
    except Exception as e:
        logger.error(f"Error getting processor health status: {e}")
        return {"error": str(e)}


def get_processor_performance_stats() -> dict:
    """Get processor performance statistics.

    Note: This function uses a per-call ProcessorMetrics instance and will
    return empty stats unless processors have been wrapped with metrics collection.
    For container-scoped metrics, use container.get_processor_metrics().get_all_stats().

    Returns:
        Dictionary containing performance stats for all processors
    """
    try:
        from .._internal.processor_metrics import ProcessorMetrics

        # Create a new instance per call to avoid global state
        # This will return empty stats since metrics aren't shared
        metrics = ProcessorMetrics()
        return metrics.get_all_stats()
    except ImportError:
        logger.warning("ProcessorMetrics not available")
        return {"error": "ProcessorMetrics not available"}
    except Exception as e:
        logger.error(f"Error getting processor performance stats: {e}")
        return {"error": str(e)}


def reset_processor_metrics(processor_name: Optional[str] = None) -> None:
    """Reset processor metrics.

    Note: This function uses a per-call ProcessorMetrics instance and will have
    no effect unless processors have been wrapped with the same metrics instance.
    For container-scoped metrics, use container.get_processor_metrics().reset_stats().

    Args:
        processor_name: Name of specific processor to reset, or None for all
    """
    try:
        from .._internal.processor_metrics import ProcessorMetrics

        # Create a new instance per call to avoid global state
        # This will have no effect since metrics aren't shared
        metrics = ProcessorMetrics()
        metrics.reset_stats(processor_name)
        logger.info(
            f"Reset processor metrics for: {processor_name or 'all processors'}"
        )
    except Exception as e:
        logger.error(f"Error resetting processor metrics: {e}")


def get_processor_summary() -> dict:
    """Get a summary of processor performance across the system.

    Returns:
        Dictionary containing aggregated processor performance summary
    """
    try:
        stats = get_processor_performance_stats()
        if "error" in stats:
            return stats

        if not stats:
            return {"total_processors": 0, "summary": "No processors tracked"}

        summary = {
            "total_processors": len(stats),
            "healthy_processors": 0,
            "unhealthy_processors": 0,
            "slow_processors": 0,
            "unknown_processors": 0,
            "total_executions": 0,
            "total_successful": 0,
            "total_failed": 0,
            "average_latency_ms": 0.0,
            "total_bytes_processed": 0,
        }

        health_status = get_processor_health_status()
        if "error" in health_status:
            return health_status

        total_latency = 0.0
        processors_with_latency = 0

        for processor_name, processor_stats in stats.items():
            # Count health status
            status = health_status.get(processor_name, "unknown")
            if status == "healthy":
                summary["healthy_processors"] += 1
            elif status == "unhealthy":
                summary["unhealthy_processors"] += 1
            elif status == "slow":
                summary["slow_processors"] += 1
            else:
                summary["unknown_processors"] += 1

            # Aggregate metrics
            summary["total_executions"] += processor_stats.get("total_executions", 0)
            summary["total_successful"] += processor_stats.get(
                "successful_executions", 0
            )
            summary["total_failed"] += processor_stats.get("failed_executions", 0)
            summary["total_bytes_processed"] += processor_stats.get(
                "total_bytes_processed", 0
            )

            # Average latency calculation
            avg_latency = processor_stats.get("average_latency_ms", 0)
            if avg_latency > 0:
                total_latency += avg_latency
                processors_with_latency += 1

        if processors_with_latency > 0:
            summary["average_latency_ms"] = total_latency / processors_with_latency

        # Calculate overall success rate
        if summary["total_executions"] > 0:
            summary["overall_success_rate"] = (
                summary["total_successful"] / summary["total_executions"]
            ) * 100
        else:
            summary["overall_success_rate"] = 0.0

        return summary
    except Exception as e:
        logger.error(f"Error getting processor summary: {e}")
        return {"error": str(e)}


def get_health_status() -> dict:
    """Get overall system health status.

    Returns:
        Dictionary containing overall health information
    """
    try:
        processor_health = get_processor_health_status()
        processor_summary = get_processor_summary()

        # Determine overall health
        overall_health = "healthy"
        if "error" in processor_health or "error" in processor_summary:
            overall_health = "error"
        elif processor_summary.get("unhealthy_processors", 0) > 0:
            overall_health = "unhealthy"
        elif processor_summary.get("slow_processors", 0) > 0:
            overall_health = "degraded"

        return {
            "overall_health": overall_health,
            "timestamp": None,  # Would be set by caller
            "processor_health": processor_health,
            "processor_summary": processor_summary,
        }
    except Exception as e:
        logger.error(f"Error getting health status: {e}")
        return {"overall_health": "error", "error": str(e)}
