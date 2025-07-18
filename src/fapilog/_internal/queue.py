"""Async log queue implementation for non-blocking logging."""

import asyncio
import logging
import random as rnd
from typing import Any, Dict, List, Literal, Optional

import structlog

from .error_handling import (
    handle_queue_error,
    log_error_with_context,
    retry_with_backoff_async,
)

logger = logging.getLogger(__name__)


class Sink:
    """Base class for log sinks."""

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Write a log event to the sink.

        Args:
            event_dict: The structured log event dictionary
        """
        raise NotImplementedError


class QueueWorker:
    """Background worker that processes log events from the queue."""

    def __init__(
        self,
        sinks: List[Sink],
        queue_max_size: int = 1000,
        batch_size: int = 10,
        batch_timeout: float = 1.0,
        retry_delay: float = 1.0,
        max_retries: int = 3,
        overflow_strategy: Literal["drop", "block", "sample"] = "drop",
        sampling_rate: float = 1.0,
    ) -> None:
        """Initialize the queue worker.

        Args:
            sinks: List of sink instances to write to
            queue_max_size: Maximum size of the internal queue
            batch_size: Number of events to process in a batch
            batch_timeout: Maximum time to wait for batch completion
            retry_delay: Delay between retries on sink failures
            max_retries: Maximum number of retries per event
            overflow_strategy: Strategy for handling queue overflow
            sampling_rate: Sampling rate for log messages (0.0 to 1.0)
        """
        self.sinks = sinks
        self.queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(
            maxsize=queue_max_size
        )
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.retry_delay = retry_delay
        self.max_retries = max_retries
        self.overflow_strategy = overflow_strategy
        self.sampling_rate = sampling_rate
        self._task: Optional[asyncio.Task[None]] = None
        self._running = False
        self._stopping = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    async def start(self) -> None:
        """Start the queue worker."""
        if self._task is not None and not self._task.done():
            return  # Already running

        self._running = True
        self._stopping = False
        self._loop = asyncio.get_running_loop()
        self._task = asyncio.create_task(self._run())
        logger.debug("QueueWorker started")

    async def stop(self) -> None:
        """Stop the queue worker gracefully."""
        if self._task is None:
            return

        self._running = False

        # Wait for the task to complete
        if not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.debug("QueueWorker stopped")

    async def shutdown(self) -> None:
        """Shutdown the worker gracefully."""
        logger.debug("QueueWorker shutdown initiated")
        self._stopping = True
        self._running = False

        # Wait for the worker task to complete
        if self._task is not None and not self._task.done():
            try:
                # Cancel the task if it's still running
                self._task.cancel()

                # Only wait if we're on the same event loop
                if self._loop and self._loop == asyncio.get_running_loop():
                    await asyncio.wait_for(self._task, timeout=5.0)
                else:
                    # Different loop, just let it cancel naturally
                    logger.debug("Different loop, allowing natural cancellation")
            except asyncio.TimeoutError:
                logger.warning("Worker task shutdown timed out")
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.warning(f"Error during worker task shutdown: {e}")

        # Drain any remaining events in the queue
        await self._drain_queue()

        logger.debug("QueueWorker shutdown completed")

    def shutdown_sync(self, timeout: float = 5.0) -> None:
        """Shutdown the worker from a sync context.

        This method marks the worker as stopping and returns immediately.
        The worker will shut down naturally when it next checks the stopping
        flag.
        """
        if self._stopping:
            return  # Already shutting down

        logger.debug("QueueWorker sync shutdown initiated")
        self._stopping = True
        self._running = False

        # Don't wait for completion - let it shut down naturally
        # This avoids event loop conflicts entirely
        logger.debug("QueueWorker marked for shutdown")

    async def _drain_queue(self) -> None:
        """Drain all remaining events from the queue and process them."""
        drained_events = []

        # Collect all remaining events from the queue
        while not self.queue.empty():
            try:
                event = self.queue.get_nowait()
                drained_events.append(event)
            except asyncio.QueueEmpty:
                break

        # Process all drained events
        if drained_events:
            logger.debug(f"Draining {len(drained_events)} remaining events")
            for event in drained_events:
                await self._process_event(event)

    async def _run(self) -> None:
        """Main worker loop."""
        while self._running and not self._stopping:
            try:
                # Process events in batches
                batch = await self._collect_batch()
                if batch:
                    await self._process_batch(batch)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in queue worker: {e}")
                if not self._stopping:
                    await asyncio.sleep(self.retry_delay)

        # Ensure we drain the queue on shutdown
        if self._stopping:
            await self._drain_queue()

    async def _collect_batch(self) -> List[Dict[str, Any]]:
        """Collect a batch of events from the queue."""
        batch = []

        # Get the first event (blocking)
        try:
            first_event = await asyncio.wait_for(
                self.queue.get(), timeout=self.batch_timeout
            )
            batch.append(first_event)
        except asyncio.TimeoutError:
            return batch

        # Try to get more events (non-blocking)
        while len(batch) < self.batch_size:
            try:
                event = self.queue.get_nowait()
                batch.append(event)
            except asyncio.QueueEmpty:
                break

        return batch

    async def _process_batch(self, batch: List[Dict[str, Any]]) -> None:
        """Process a batch of events."""
        for event in batch:
            await self._process_event(event)

    async def _process_event(self, event: Dict[str, Any]) -> None:
        """Process a single event with retry logic."""

        async def process_event_with_sinks() -> None:
            """Process event by writing to all sinks."""
            # Write to all sinks
            results = await asyncio.gather(
                *[sink.write(event) for sink in self.sinks],
                return_exceptions=True,
            )

            # Check if any sink failed
            exceptions = [r for r in results if isinstance(r, Exception)]
            if exceptions:
                # Log individual sink failures for debugging
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        sink_config = {
                            "sink_index": i,
                            "sink_type": type(self.sinks[i]).__name__,
                        }
                        log_error_with_context(result, sink_config, logging.WARNING)

                # Raise the first exception with context about all failures
                first_exception = exceptions[0]
                raise handle_queue_error(
                    first_exception,
                    "process_event",
                    {
                        "event_keys": list(event.keys()),
                        "total_sinks": len(self.sinks),
                        "failed_sinks": len(exceptions),
                    },
                )

        try:
            await retry_with_backoff_async(
                process_event_with_sinks,
                max_retries=self.max_retries,
                base_delay=self.retry_delay,
                error_handler=lambda e: handle_queue_error(
                    e, "process_event", {"event_keys": list(event.keys())}
                ),
            )
        except Exception as e:
            # Final failure after all retries
            queue_state = {
                "queue_size": self.queue.qsize(),
                "max_retries": self.max_retries,
                "retry_delay": self.retry_delay,
                "total_sinks": len(self.sinks),
            }
            raise handle_queue_error(e, "process_event", queue_state) from e

    async def enqueue(self, event_dict: Dict[str, Any]) -> bool:
        """Enqueue a log event.

        Args:
            event_dict: The structured log event dictionary

        Returns:
            True if the event was enqueued, False if the queue was full or
            shutting down

        Raises:
            QueueError: If enqueue operation fails unexpectedly
        """
        if self._stopping:
            return False

        # Apply sampling if enabled
        if self.sampling_rate < 1.0 and rnd.random() > self.sampling_rate:
            return False

        try:
            if self.overflow_strategy == "drop":
                # Drop strategy: try to enqueue, drop if full
                try:
                    self.queue.put_nowait(event_dict)
                    return True
                except asyncio.QueueFull:
                    return False
            elif self.overflow_strategy == "block":
                # Block strategy: wait until space is available
                try:
                    await self.queue.put(event_dict)
                    return True
                except asyncio.CancelledError:
                    return False
            else:  # "sample"
                # Sample strategy: use sampling rate for overflow
                try:
                    self.queue.put_nowait(event_dict)
                    return True
                except asyncio.QueueFull:
                    return False
        except Exception as e:
            # Unexpected error during enqueue
            queue_state = {
                "queue_size": self.queue.qsize(),
                "overflow_strategy": self.overflow_strategy,
                "sampling_rate": self.sampling_rate,
            }
            raise handle_queue_error(e, "enqueue", queue_state) from e


# Global queue worker instance
_queue_worker: Optional[QueueWorker] = None


def get_queue_worker() -> Optional[QueueWorker]:
    """Get the global queue worker instance."""
    return _queue_worker


def set_queue_worker(worker: QueueWorker) -> None:
    """Set the global queue worker instance."""
    global _queue_worker
    _queue_worker = worker


def queue_sink(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Queue sink processor for structlog.

    This processor enqueues log events into the async queue instead of
    writing them directly to sinks.

    Args:
        logger: The structlog logger instance
        method_name: The log method name (info, error, etc.)
        event_dict: The structured log event dictionary

    Returns:
        None to prevent further processing, or the event_dict if queuing failed
    """
    worker = get_queue_worker()
    if worker is None:
        # Fall back to synchronous processing if no queue worker
        return event_dict

    # Start the worker if it's not running
    if not worker._running and not worker._stopping:
        try:
            # Try to start the worker in the current context
            try:
                loop = asyncio.get_running_loop()
                task = loop.create_task(worker.start())
                # Store task reference to prevent garbage collection
                worker._task = task  # type: ignore[attr-defined]
                # Task is stored in the event loop, no need to keep reference
            except RuntimeError:
                # No running loop, start it in a new thread
                import threading

                def start_worker() -> None:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(worker.start())
                    finally:
                        loop.close()

                thread = threading.Thread(target=start_worker, daemon=True)
                thread.start()
        except Exception:
            # If we can't start the worker, fall back to sync processing
            return event_dict

    # Handle different overflow strategies
    if worker._stopping:
        # Don't enqueue if shutting down
        raise structlog.DropEvent

    if worker.overflow_strategy == "drop":
        # Drop strategy: try to enqueue, drop if full
        try:
            worker.queue.put_nowait(event_dict)
            raise structlog.DropEvent
        except asyncio.QueueFull:
            raise structlog.DropEvent from None
    elif worker.overflow_strategy == "block":
        # Block strategy: not supported in sync context, fall back to drop
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


async def queue_sink_async(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Async version of queue_sink for use in async contexts."""
    worker = get_queue_worker()
    if worker is None:
        return event_dict

    # Try to enqueue the event
    enqueued = await worker.enqueue(event_dict)
    if not enqueued:
        # Queue is full or shutting down, drop the event silently
        return None

    return None  # Prevent further processing
