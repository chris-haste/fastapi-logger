"""Async log queue implementation for non-blocking logging."""

import asyncio
import logging
from typing import Any, Dict, List, Optional
import structlog

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
        queue_size: int = 1000,
        batch_size: int = 10,
        batch_timeout: float = 1.0,
        retry_delay: float = 1.0,
        max_retries: int = 3,
    ) -> None:
        """Initialize the queue worker.

        Args:
            sinks: List of sink instances to write to
            queue_size: Maximum size of the internal queue
            batch_size: Number of events to process in a batch
            batch_timeout: Maximum time to wait for batch completion
            retry_delay: Delay between retries on sink failures
            max_retries: Maximum number of retries per event
        """
        self.sinks = sinks
        self.queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(maxsize=queue_size)
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.retry_delay = retry_delay
        self.max_retries = max_retries
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
        """Shutdown the queue worker gracefully, ensuring all logs are flushed.

        This method:
        1. Marks the queue as stopping to prevent new events from being
           processed
        2. Waits for the queue to drain
        3. Ensures all log events are flushed to all registered sinks
        4. Can be called safely more than once
        """
        if self._stopping:
            # Already shutting down, just wait for completion
            if self._task is not None and not self._task.done():
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            return

        logger.debug("QueueWorker shutdown initiated")
        self._stopping = True
        self._running = False

        # Wait for the worker task to complete
        if self._task is not None and not self._task.done():
            try:
                # Cancel the task if it's still running
                self._task.cancel()
                # Use a timeout to avoid hanging and event loop issues
                await asyncio.wait_for(self._task, timeout=5.0)
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
        """Shutdown the worker from a sync context, using the correct event loop."""
        if self._loop and self._loop.is_running():
            # Schedule shutdown on the worker's loop
            fut = asyncio.run_coroutine_threadsafe(self.shutdown(), self._loop)
            try:
                fut.result(timeout=timeout)
            except Exception as e:
                logger.warning(f"Error during sync shutdown: {e}")
        else:
            # Fallback: run in current thread/loop
            try:
                asyncio.run(self.shutdown())
            except Exception as e:
                logger.warning(f"Error during sync shutdown fallback: {e}")

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
        for attempt in range(self.max_retries + 1):
            try:
                # Write to all sinks
                results = await asyncio.gather(
                    *[sink.write(event) for sink in self.sinks],
                    return_exceptions=True,
                )

                # Check if any sink failed
                exceptions = [r for r in results if isinstance(r, Exception)]
                if exceptions:
                    raise exceptions[0]  # Raise the first exception

                break  # Success, exit retry loop
            except Exception as e:
                if attempt == self.max_retries:
                    logger.error(
                        f"Failed to process event after {self.max_retries} retries: {e}"
                    )
                else:
                    logger.warning(
                        f"Retrying event processing (attempt {attempt + 1}): {e}"
                    )
                    await asyncio.sleep(self.retry_delay * (2**attempt))

    async def enqueue(self, event_dict: Dict[str, Any]) -> bool:
        """Enqueue a log event.

        Args:
            event_dict: The structured log event dictionary

        Returns:
            True if the event was enqueued, False if the queue was full or
            shutting down
        """
        if self._stopping:
            return False

        try:
            self.queue.put_nowait(event_dict)
            return True
        except asyncio.QueueFull:
            return False


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
                loop.create_task(worker.start())
            except RuntimeError:
                # No running loop, start it in a new thread
                import threading

                def start_worker():
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

    # Try to enqueue the event (sync context, so we can't await)
    try:
        if worker._stopping:
            # Don't enqueue if shutting down
            raise structlog.DropEvent
        worker.queue.put_nowait(event_dict)
        # If put_nowait succeeds, drop the event from further processing
        raise structlog.DropEvent
    except asyncio.QueueFull:
        # Drop the event silently if the queue is full
        raise structlog.DropEvent


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
