import asyncio
import atexit
from contextlib import asynccontextmanager
from typing import Dict, List

from .async_enricher import AsyncEnricher


class EnricherLifecycleManager:
    """Manages lifecycle of async enrichers."""

    def __init__(self):
        self.enrichers: List[AsyncEnricher] = []
        self.is_started = False
        self._shutdown_registered = False

    def register_enricher(self, enricher: AsyncEnricher) -> None:
        """Register an async enricher for lifecycle management."""
        self.enrichers.append(enricher)
        if not self._shutdown_registered:
            atexit.register(self._sync_shutdown)
            self._shutdown_registered = True

    async def startup_all(self) -> None:
        """Start all registered enrichers."""
        if self.is_started:
            return

        startup_tasks = []
        for enricher in self.enrichers:
            startup_tasks.append(enricher.startup())

        if startup_tasks:
            results = await asyncio.gather(*startup_tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.error(
                        f"Failed to start enricher {self.enrichers[i].name}: {result}"
                    )

        self.is_started = True

    async def shutdown_all(self) -> None:
        """Shutdown all registered enrichers."""
        if not self.is_started:
            return

        shutdown_tasks = []
        for enricher in self.enrichers:
            shutdown_tasks.append(enricher.shutdown())

        if shutdown_tasks:
            await asyncio.gather(*shutdown_tasks, return_exceptions=True)

        self.is_started = False

    async def health_check_all(self) -> Dict[str, bool]:
        """Health check all enrichers."""
        health_tasks = []
        for enricher in self.enrichers:
            health_tasks.append(enricher.health_check())

        if not health_tasks:
            return {}

        results = await asyncio.gather(*health_tasks, return_exceptions=True)
        return {
            enricher.name: result if isinstance(result, bool) else False
            for enricher, result in zip(self.enrichers, results)
        }

    def _sync_shutdown(self) -> None:
        """Synchronous shutdown for atexit."""
        if self.is_started:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Create a task for shutdown
                    asyncio.create_task(self.shutdown_all())
                else:
                    asyncio.run(self.shutdown_all())
            except Exception:
                pass  # Best effort shutdown

    @asynccontextmanager
    async def managed_enrichers(self):
        """Context manager for enricher lifecycle."""
        try:
            await self.startup_all()
            yield self
        finally:
            await self.shutdown_all()


# Global lifecycle manager
lifecycle_manager = EnricherLifecycleManager()
