"""Health monitoring and error handling for fapilog enrichers."""

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Set

# Logger for enricher-related issues
enricher_logger = logging.getLogger(__name__)


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
    ) -> None:
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
