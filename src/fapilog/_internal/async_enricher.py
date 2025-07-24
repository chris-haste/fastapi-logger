import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict


class AsyncEnricher(ABC):
    """Base class for async enrichers with lifecycle management."""

    def __init__(self, name: str, **kwargs):
        self.name = name
        self.is_started = False
        self.is_healthy = True
        self._lock = asyncio.Lock()
        self._session = None
        self._connection_pool = None

    async def startup(self) -> None:
        """Initialize enricher resources (connections, pools, etc.)."""
        if self.is_started:
            return

        async with self._lock:
            if not self.is_started:
                await self._startup()
                self.is_started = True

    async def shutdown(self) -> None:
        """Clean up enricher resources."""
        if not self.is_started:
            return

        async with self._lock:
            if self.is_started:
                await self._shutdown()
                self.is_started = False

    async def health_check(self) -> bool:
        """Check if enricher is healthy and responsive."""
        try:
            result = await self._health_check()
            self.is_healthy = result
            return result
        except Exception:
            self.is_healthy = False
            return False

    @abstractmethod
    async def _startup(self) -> None:
        """Override to implement startup logic."""
        pass

    @abstractmethod
    async def _shutdown(self) -> None:
        """Override to implement shutdown logic."""
        pass

    @abstractmethod
    async def _health_check(self) -> bool:
        """Override to implement health check logic."""
        pass

    @abstractmethod
    async def enrich_async(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Override to implement enrichment logic."""
        pass

    async def __call__(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Main enricher entry point with error handling."""
        if not self.is_started:
            await self.startup()

        if not self.is_healthy:
            # Skip enrichment if unhealthy
            return event_dict

        try:
            return await self.enrich_async(logger, method_name, event_dict)
        except Exception as e:
            # Log error but don't break pipeline
            import logging

            enricher_logger = logging.getLogger(__name__)
            enricher_logger.debug(
                f"Async enricher {self.name} failed: {e}", exc_info=True
            )
            self.is_healthy = False
            return event_dict
