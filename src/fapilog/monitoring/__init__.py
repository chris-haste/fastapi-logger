"""Monitoring package for fapilog."""

# Export Prometheus functionality
# Export Health monitoring functionality
from .health import (
    get_health_status,
    get_processor_health_status,
    get_processor_performance_stats,
    get_processor_summary,
    reset_processor_metrics,
)

# Export Metrics collection functionality
from .metrics.collector import MetricsCollector, get_metrics_dict, get_metrics_text

# Re-export FastAPI and related imports for backward compatibility with tests
from .prometheus import (
    FastAPI,
    PlainTextResponse,
    PrometheusExporter,
    Response,
    create_prometheus_exporter,
    get_prometheus_exporter,
    start_metrics_server,
    stop_metrics_server,
    uvicorn,
)

__all__ = [
    # Prometheus exports
    "PrometheusExporter",
    "create_prometheus_exporter",
    "get_prometheus_exporter",
    "start_metrics_server",
    "stop_metrics_server",
    # Health monitoring exports
    "get_health_status",
    "get_processor_health_status",
    "get_processor_performance_stats",
    "get_processor_summary",
    "reset_processor_metrics",
    # Metrics collection exports
    "MetricsCollector",
    "get_metrics_dict",
    "get_metrics_text",
    # FastAPI re-exports for backward compatibility
    "FastAPI",
    "Response",
    "PlainTextResponse",
    "uvicorn",
]
