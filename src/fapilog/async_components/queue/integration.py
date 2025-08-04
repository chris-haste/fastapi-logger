"""Queue pipeline integration for structlog processors.

This module provides integration functions that connect structlog processors
with the async queue system for non-blocking log processing using pure
dependency injection patterns.
"""

import asyncio
import logging
import random as rnd
from typing import TYPE_CHECKING, Any, Dict, Optional

import structlog

if TYPE_CHECKING:
    from ..container import LoggingContainer

logger = logging.getLogger(__name__)


def create_queue_sink(container: "LoggingContainer") -> Any:
    """Create a queue sink processor for structlog with explicit container.

    This function creates a queue sink processor that uses the provided
    container instead of relying on global state access.

    Args:
        container: The LoggingContainer instance to use for queue operations

    Returns:
        A queue sink processor function that can be used in structlog chain
    """

    def queue_sink(
        logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Queue sink processor for structlog with explicit container.

        This processor enqueues log events into the async queue instead of
        writing them directly to sinks. It uses the provided container
        for queue worker access.

        Args:
            logger: The structlog logger instance
            method_name: The log method name (info, error, etc.)
            event_dict: The structured log event dictionary

        Returns:
            None to prevent further processing, or the event_dict if queuing failed
        """
        # Use the explicitly provided container
        if container is None:
            # No container available - return event_dict for further processing
            return event_dict

        worker = getattr(container, "queue_worker", None)
        if worker is None:
            # No queue worker available - return event_dict for further processing
            return event_dict

        # When we have a queue worker, we should ALWAYS either queue or drop
        # Never let structured data reach the logger when queues are intended

        # Check if we're shutting down first
        if worker._stopping:
            # Drop events during shutdown
            raise structlog.DropEvent

        # Start the worker if it's not running (but be more careful)
        if not worker._running and not worker._stopping:
            try:
                # Try to start the worker in the current context
                try:
                    loop = asyncio.get_running_loop()
                    # Only create task if we're in an async context
                    if not loop.is_closed():
                        loop.create_task(worker.start())
                    else:
                        # Event loop is closed, drop the event
                        raise structlog.DropEvent
                except RuntimeError:
                    # No running loop - drop the event rather than fall back
                    # This prevents structured data from reaching the logger
                    raise structlog.DropEvent from None
            except Exception:
                # Any other exception during startup - drop the event
                raise structlog.DropEvent from None

        # Handle different overflow strategies
        if worker.overflow_strategy == "drop":
            # Drop strategy: try to enqueue, drop if full
            try:
                worker.queue.put_nowait(event_dict)
                raise structlog.DropEvent
            except asyncio.QueueFull:
                raise structlog.DropEvent from None
        elif worker.overflow_strategy == "block":
            # Block strategy: not supported in sync context, drop instead
            try:
                worker.queue.put_nowait(event_dict)
                raise structlog.DropEvent
            except asyncio.QueueFull:
                raise structlog.DropEvent from None
        else:  # "sample"
            # Sample strategy: apply sampling and try to enqueue
            rate = worker.sampling_rate
            if rate < 1.0 and rnd.random() > rate:
                raise structlog.DropEvent
            try:
                worker.queue.put_nowait(event_dict)
                raise structlog.DropEvent
            except asyncio.QueueFull:
                raise structlog.DropEvent from None

    return queue_sink


# Legacy function for backward compatibility during transition
def queue_sink(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Legacy queue sink processor for backward compatibility.

    This function provides backward compatibility during the transition
    to pure dependency injection. It should not be used in new code.

    Args:
        logger: The structlog logger instance
        method_name: The log method name (info, error, etc.)
        event_dict: The structured log event dictionary

    Returns:
        The event_dict for further processing (queue functionality disabled)
    """
    # During transition, return event_dict to allow processing to continue
    # This ensures the system doesn't break while components are being updated
    logger.warning(
        "Legacy queue_sink function called - queue functionality disabled during transition",
        event_dict=event_dict,
    )
    return event_dict
