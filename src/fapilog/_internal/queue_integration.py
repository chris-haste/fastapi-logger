"""Queue pipeline integration for structlog processors.

This module provides integration functions that connect structlog processors
with the async queue system for non-blocking log processing.
"""

import asyncio
import logging
import random as rnd
from typing import Any, Dict, Optional

import structlog

logger = logging.getLogger(__name__)


def queue_sink(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Queue sink processor for structlog.

    This processor enqueues log events into the async queue instead of
    writing them directly to sinks. It only works with container-provided
    queue workers.

    Args:
        logger: The structlog logger instance
        method_name: The log method name (info, error, etc.)
        event_dict: The structured log event dictionary

    Returns:
        None to prevent further processing, or the event_dict if queuing failed
    """
    # Import here to avoid circular import
    from ..container import get_current_container

    container = get_current_container()
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
