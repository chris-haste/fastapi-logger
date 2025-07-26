"""Monitoring and metrics export for fapilog."""

import asyncio
import logging
from typing import Optional

try:
    import uvicorn
    from fastapi import FastAPI, Response
    from fastapi.responses import PlainTextResponse
except ImportError:
    FastAPI = None
    Response = None
    PlainTextResponse = None
    uvicorn = None

from ._internal.metrics import get_metrics_collector

logger = logging.getLogger(__name__)


class PrometheusExporter:
    """Prometheus metrics exporter with HTTP endpoint."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8000,
        path: str = "/metrics",
        enabled: bool = True,
    ):
        """Initialize the Prometheus exporter.

        Args:
            host: Host to bind the HTTP server to
            port: Port to bind the HTTP server to
            path: HTTP path for metrics endpoint
            enabled: Whether the exporter is enabled
        """
        self.host = host
        self.port = port
        self.path = path
        self.enabled = enabled
        self._app: Optional[FastAPI] = None
        self._server_task: Optional[asyncio.Task] = None

        if not enabled:
            return

        if FastAPI is None:
            logger.warning(
                "FastAPI not available. Prometheus exporter disabled. "
                "Install with: pip install 'fapilog[prometheus]'"
            )
            self.enabled = False
            return

        self._setup_app()

    def _setup_app(self) -> None:
        """Setup the FastAPI application."""
        if not self.enabled:
            return

        self._app = FastAPI(
            title="fapilog Metrics",
            description="Prometheus metrics for fapilog",
            version="1.0.0",
            docs_url=None,
            redoc_url=None,
        )

        @self._app.get(self.path, response_class=PlainTextResponse)
        async def metrics_endpoint():
            """Metrics endpoint returning Prometheus format."""
            metrics_collector = get_metrics_collector()
            if not metrics_collector or not metrics_collector.is_enabled():
                return PlainTextResponse(
                    "# Metrics collection is disabled\n", status_code=503
                )

            try:
                prometheus_metrics = metrics_collector.get_prometheus_metrics()
                return PlainTextResponse(prometheus_metrics)
            except Exception as e:
                logger.error(f"Error generating Prometheus metrics: {e}")
                return PlainTextResponse(
                    f"# Error generating metrics: {e}\n", status_code=500
                )

        @self._app.get("/health")
        async def health_endpoint():
            """Health check endpoint."""
            return {"status": "healthy", "metrics_enabled": self.enabled}

        @self._app.get("/")
        async def root_endpoint():
            """Root endpoint with basic info."""
            return {
                "service": "fapilog-metrics",
                "metrics_path": self.path,
                "health_path": "/health",
            }

    async def start(self) -> None:
        """Start the Prometheus metrics server."""
        if not self.enabled or self._app is None:
            logger.debug("Prometheus exporter not enabled or not configured")
            return

        if self._server_task is not None and not self._server_task.done():
            logger.debug("Prometheus exporter already running")
            return

        try:
            # Configure uvicorn to run in the current event loop
            config = uvicorn.Config(
                app=self._app,
                host=self.host,
                port=self.port,
                log_level="error",  # Reduce log noise
                access_log=False,
            )
            server = uvicorn.Server(config)

            # Start the server as a background task
            self._server_task = asyncio.create_task(server.serve())
            logger.info(
                f"Prometheus metrics server started on "
                f"http://{self.host}:{self.port}{self.path}"
            )

        except Exception as e:
            logger.error(f"Failed to start Prometheus metrics server: {e}")
            self.enabled = False

    async def stop(self) -> None:
        """Stop the Prometheus metrics server."""
        if self._server_task is None:
            return

        if not self._server_task.done():
            self._server_task.cancel()
            try:
                await self._server_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error stopping Prometheus metrics server: {e}")

        self._server_task = None
        logger.info("Prometheus metrics server stopped")

    def is_running(self) -> bool:
        """Check if the metrics server is running."""
        return (
            self.enabled
            and self._server_task is not None
            and not self._server_task.done()
        )

    def get_metrics_url(self) -> Optional[str]:
        """Get the full URL for the metrics endpoint."""
        if not self.enabled:
            return None
        return f"http://{self.host}:{self.port}{self.path}"


# Global Prometheus exporter instance
_prometheus_exporter: Optional[PrometheusExporter] = None


def get_prometheus_exporter() -> Optional[PrometheusExporter]:
    """Get the global Prometheus exporter instance."""
    return _prometheus_exporter


def set_prometheus_exporter(exporter: Optional[PrometheusExporter]) -> None:
    """Set the global Prometheus exporter instance."""
    global _prometheus_exporter
    _prometheus_exporter = exporter


def create_prometheus_exporter(
    host: str = "0.0.0.0",
    port: int = 8000,
    path: str = "/metrics",
    enabled: bool = True,
) -> PrometheusExporter:
    """Create and set a new global Prometheus exporter."""
    exporter = PrometheusExporter(
        host=host,
        port=port,
        path=path,
        enabled=enabled,
    )
    set_prometheus_exporter(exporter)
    return exporter


async def start_metrics_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    path: str = "/metrics",
) -> Optional[PrometheusExporter]:
    """Start a Prometheus metrics server.

    Args:
        host: Host to bind to
        port: Port to bind to
        path: Path for metrics endpoint

    Returns:
        The PrometheusExporter instance or None if failed
    """
    try:
        exporter = create_prometheus_exporter(
            host=host,
            port=port,
            path=path,
            enabled=True,
        )
        await exporter.start()
        return exporter
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")
        return None


async def stop_metrics_server() -> None:
    """Stop the global Prometheus metrics server."""
    exporter = get_prometheus_exporter()
    if exporter:
        await exporter.stop()


def get_metrics_text() -> str:
    """Get the current metrics in Prometheus text format.

    Returns:
        Prometheus formatted metrics string
    """
    metrics_collector = get_metrics_collector()
    if not metrics_collector or not metrics_collector.is_enabled():
        return "# Metrics collection is disabled\n"

    try:
        return metrics_collector.get_prometheus_metrics()
    except Exception as e:
        logger.error(f"Error generating Prometheus metrics: {e}")
        return f"# Error generating metrics: {e}\n"


def get_metrics_dict() -> dict:
    """Get the current metrics as a dictionary.

    Returns:
        Dictionary containing all current metrics
    """
    metrics_collector = get_metrics_collector()
    if not metrics_collector or not metrics_collector.is_enabled():
        return {}

    try:
        return metrics_collector.get_all_metrics()
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return {"error": str(e)}


def get_processor_performance_stats() -> dict:
    """Get processor performance statistics.

    Returns:
        Dictionary containing performance stats for all processors
    """
    try:
        from ._internal.processor_metrics import get_processor_metrics

        metrics = get_processor_metrics()
        return metrics.get_all_stats()
    except Exception as e:
        logger.error(f"Error getting processor performance stats: {e}")
        return {"error": str(e)}


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


def reset_processor_metrics(processor_name: Optional[str] = None) -> None:
    """Reset processor metrics.

    Args:
        processor_name: Name of specific processor to reset, or None for all
    """
    try:
        from ._internal.processor_metrics import get_processor_metrics

        metrics = get_processor_metrics()
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
