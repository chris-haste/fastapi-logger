import asyncio
import concurrent.futures
from typing import Any, Callable, Dict, List, Union

from .async_enricher import AsyncEnricher


class AsyncEnricherProcessor:
    """Processor that handles both sync and async enrichers."""

    def __init__(
        self, enrichers: List[Union[Callable, AsyncEnricher]], timeout: float = 5.0
    ):
        self.enrichers = enrichers
        self.timeout = timeout
        self._async_enrichers = [e for e in enrichers if isinstance(e, AsyncEnricher)]
        self._sync_enrichers = [
            e for e in enrichers if not isinstance(e, AsyncEnricher)
        ]

    async def startup(self) -> None:
        """Start all async enrichers."""
        startup_tasks = [enricher.startup() for enricher in self._async_enrichers]
        if startup_tasks:
            await asyncio.gather(*startup_tasks, return_exceptions=True)

    async def shutdown(self) -> None:
        """Shutdown all async enrichers."""
        shutdown_tasks = [enricher.shutdown() for enricher in self._async_enrichers]
        if shutdown_tasks:
            await asyncio.gather(*shutdown_tasks, return_exceptions=True)

    def __call__(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process event through both sync and async enrichers."""

        # Process sync enrichers first
        result = event_dict
        for enricher in self._sync_enrichers:
            try:
                result = enricher(logger, method_name, result)
            except Exception as e:
                import logging

                enricher_logger = logging.getLogger(__name__)
                enricher_logger.debug(f"Sync enricher failed: {e}", exc_info=True)

        # Process async enrichers if any
        if self._async_enrichers:
            try:
                # Use ThreadPoolExecutor to run async code from sync context
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        self._run_async_enrichers_in_thread, logger, method_name, result
                    )
                    result = future.result(timeout=self.timeout)
            except concurrent.futures.TimeoutError:
                import logging

                enricher_logger = logging.getLogger(__name__)
                enricher_logger.warning(
                    f"Async enrichers timed out after {self.timeout}s"
                )
            except Exception as e:
                import logging

                enricher_logger = logging.getLogger(__name__)
                enricher_logger.debug(
                    f"Async enricher processing failed: {e}", exc_info=True
                )

        return result

    def _run_async_enrichers_in_thread(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run async enrichers in a new event loop in thread."""
        return asyncio.run(
            self._process_async_enrichers(logger, method_name, event_dict)
        )

    async def _process_async_enrichers(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process async enrichers sequentially to maintain order."""
        result = event_dict

        # Process async enrichers sequentially to maintain order
        for enricher in self._async_enrichers:
            try:
                result = await enricher(logger, method_name, result)
            except Exception as e:
                import logging

                enricher_logger = logging.getLogger(__name__)
                enricher_logger.debug(
                    f"Async enricher {enricher.name} failed: {e}", exc_info=True
                )

        return result
