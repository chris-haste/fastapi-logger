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
