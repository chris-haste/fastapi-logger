"""Prometheus metrics export for fapilog."""

import asyncio
import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..container import LoggingContainer

try:
    import uvicorn
    from fastapi import FastAPI, Response
    from fastapi.responses import PlainTextResponse
except ImportError:
    FastAPI = None
    Response = None
    PlainTextResponse = None
    uvicorn = None


logger = logging.getLogger(__name__)


class PrometheusExporter:
    """Prometheus metrics exporter with HTTP endpoint."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8000,
        path: str = "/metrics",
        enabled: bool = True,
        container: Optional["LoggingContainer"] = None,
    ):
        """Initialize the Prometheus exporter.

        Args:
            host: Host to bind the HTTP server to
            port: Port to bind the HTTP server to
            path: HTTP path for metrics endpoint
            enabled: Whether the exporter is enabled
            container: Optional LoggingContainer for metrics collection
        """
        self.host = host
        self.port = port
        self.path = path
        self.enabled = enabled
        self._container = container
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
            return self._get_metrics_text()

        @self._app.get("/health")
        async def health_endpoint():
            """Health check endpoint."""
            return {"status": "healthy", "service": "fapilog-metrics"}

    def _get_metrics_text(self) -> str:
        """Get metrics text from container or return default."""
        if self._container:
            try:
                metrics_collector = self._container.get_metrics_collector()
                if metrics_collector:
                    return metrics_collector.get_prometheus_metrics()
            except Exception as e:
                logger.warning(f"Failed to get metrics from container: {e}")

        return "# No metrics available\n"

    async def start(self) -> None:
        """Start the metrics server."""
        if not self.enabled or self._app is None or uvicorn is None:
            return

        if self._server_task is not None:
            logger.warning("Prometheus exporter already running")
            return

        try:
            config = uvicorn.Config(
                app=self._app,
                host=self.host,
                port=self.port,
                log_level="warning",
                access_log=False,
            )
            server = uvicorn.Server(config)

            self._server_task = asyncio.create_task(server.serve())
            logger.info(
                f"Prometheus metrics server started at http://{self.host}:{self.port}{self.path}"
            )

        except Exception as e:
            logger.error(f"Failed to start Prometheus exporter: {e}")
            self.enabled = False

    async def stop(self) -> None:
        """Stop the metrics server."""
        if self._server_task is None:
            return

        try:
            self._server_task.cancel()
            try:
                await self._server_task
            except asyncio.CancelledError:
                pass
            self._server_task = None
            logger.info("Prometheus metrics server stopped")

        except Exception as e:
            logger.error(f"Error stopping Prometheus exporter: {e}")

    def is_running(self) -> bool:
        """Check if the exporter is running."""
        return self._server_task is not None and not self._server_task.done()

    def get_metrics_url(self) -> Optional[str]:
        """Get the metrics URL if the exporter is enabled and running.

        Returns:
            The metrics URL or None if not available
        """
        if self.enabled and self.is_running():
            return f"http://{self.host}:{self.port}{self.path}"
        return None


def create_prometheus_exporter(
    host: str = "0.0.0.0",
    port: int = 8000,
    path: str = "/metrics",
    enabled: bool = True,
) -> PrometheusExporter:
    """Create a Prometheus exporter instance.

    Note: This function creates a standalone exporter instance.
    For container-managed exporters with proper lifecycle management,
    use LoggingContainer.get_prometheus_exporter() instead.

    Args:
        host: Host to bind to
        port: Port to bind to
        path: Path for metrics endpoint
        enabled: Whether the exporter is enabled

    Returns:
        PrometheusExporter instance
    """
    return PrometheusExporter(
        host=host,
        port=port,
        path=path,
        enabled=enabled,
    )


def get_prometheus_exporter(
    host: str = "0.0.0.0",
    port: int = 8000,
    path: str = "/metrics",
    enabled: bool = True,
) -> PrometheusExporter:
    """Get a Prometheus exporter instance.

    This is an alias for create_prometheus_exporter for backward compatibility.

    Args:
        host: Host to bind to
        port: Port to bind to
        path: Path for metrics endpoint
        enabled: Whether the exporter is enabled

    Returns:
        PrometheusExporter instance
    """
    return create_prometheus_exporter(host=host, port=port, path=path, enabled=enabled)


async def start_metrics_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    path: str = "/metrics",
) -> Optional[PrometheusExporter]:
    """Start a standalone Prometheus metrics server.

    Note: This function creates a standalone exporter instance.
    For container-managed metrics servers with proper lifecycle management,
    use LoggingContainer.get_prometheus_exporter() and manage lifecycle
    through the container.

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


async def stop_metrics_server(exporter: PrometheusExporter) -> None:
    """Stop a Prometheus metrics server.

    Args:
        exporter: The PrometheusExporter instance to stop
    """
    if exporter:
        await exporter.stop()
