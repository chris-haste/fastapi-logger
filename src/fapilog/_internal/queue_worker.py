"""Queue worker implementation for async log processing.

This module provides the QueueWorker class that handles background processing
of log events from an async queue, with batching, retry logic, and overflow
strategies.
"""

import asyncio
import logging
import random as rnd
import time
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional

from ..sinks import Sink
from .error_handling import (
    handle_queue_error,
    log_error_with_context,
    retry_with_backoff_async,
)

if TYPE_CHECKING:
    from ..container import LoggingContainer

logger = logging.getLogger(__name__)


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
        container: Optional["LoggingContainer"] = None,
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
            container: Optional LoggingContainer for metrics collection
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
        self._container = container
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
        try:
            logger.debug("QueueWorker started")
        except Exception:
            pass  # Ignore logging errors

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

        try:
            logger.debug("QueueWorker stopped")
        except Exception:
            pass  # Ignore logging errors

    async def shutdown(self) -> None:
        """Shutdown the worker gracefully."""
        try:
            logger.debug("QueueWorker shutdown initiated")
        except Exception:
            pass  # Ignore logging errors during shutdown
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
                    try:
                        logger.debug("Different loop, allowing natural cancel")
                    except Exception:
                        # Ignore logging errors during shutdown
                        pass
            except asyncio.TimeoutError:
                try:
                    logger.warning("Worker task shutdown timed out")
                except Exception:
                    pass  # Ignore logging errors during shutdown
            except asyncio.CancelledError:
                pass
            except Exception as e:
                try:
                    logger.warning(f"Error during worker task shutdown: {e}")
                except Exception:
                    pass  # Ignore logging errors during shutdown

        # Drain any remaining events in the queue
        await self._drain_queue()

        try:
            logger.debug("QueueWorker shutdown completed")
        except Exception:
            pass  # Ignore logging errors during shutdown

    def shutdown_sync(self, timeout: float = 5.0) -> None:
        """Shutdown the worker from a sync context.

        This method attempts to properly shutdown the worker, including
        waiting for background tasks to complete when possible.
        """
        if self._stopping:
            return  # Already shutting down

        try:
            logger.debug("QueueWorker sync shutdown initiated")
        except Exception:
            pass  # Ignore logging errors during shutdown
        self._stopping = True
        self._running = False

        # Disable asyncio logger to prevent "I/O operation on closed file" errors
        # during shutdown when tasks are being cleaned up
        try:
            asyncio_logger = logging.getLogger("asyncio")
            asyncio_logger.disabled = True
            # Also disable the main logger to prevent I/O errors during shutdown
            logger.disabled = True
        except Exception:
            pass  # Ignore any errors during logger disabling

        # Try to cancel the task if it exists
        if self._task is not None and not self._task.done():
            try:
                # Cancel the task
                self._task.cancel()
                try:
                    logger.debug("QueueWorker task cancelled")
                except Exception:
                    pass  # Ignore logging errors during shutdown

                # Try to wait for the task to complete using a temporary event loop
                # This helps prevent the "Task was destroyed but it is pending!" error
                try:
                    import asyncio

                    # Check if we're already in an async context
                    try:
                        asyncio.get_running_loop()
                        # We're in an async context, can't create a new loop
                        # The task will be cleaned up naturally
                    except RuntimeError:
                        # No running loop, we can create a temporary one
                        # Create a new event loop to wait for the task
                        temp_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(temp_loop)
                        try:
                            # Only try to wait if the task belongs to our temporary loop
                            if (
                                hasattr(self._task, "get_loop")
                                and self._task.get_loop() == temp_loop
                            ):
                                # Wait for the task to complete with timeout
                                temp_loop.run_until_complete(
                                    asyncio.wait_for(
                                        asyncio.shield(self._task),
                                        timeout=min(timeout, 2.0),
                                    )
                                )
                            # If task belongs to different loop, skip waiting
                            # The task will be cleaned up by its own loop
                        except (asyncio.TimeoutError, asyncio.CancelledError):
                            # Task didn't complete in time or was cancelled, that's OK
                            pass
                        except Exception:
                            # Any other error during cleanup is also OK
                            pass
                        finally:
                            temp_loop.close()
                            asyncio.set_event_loop(None)
                except Exception:
                    # If anything goes wrong with the event loop, just continue
                    pass

            except Exception as e:
                try:
                    logger.debug(f"Could not cancel queue worker task: {e}")
                except Exception:
                    pass  # Ignore logging errors during shutdown

        try:
            logger.debug("QueueWorker marked for shutdown")
        except Exception:
            pass  # Ignore logging errors during shutdown

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
            try:
                logger.debug(f"Draining {len(drained_events)} remaining events")
            except Exception:
                pass  # Ignore logging errors during shutdown
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
                try:
                    logger.error(f"Error in queue worker: {e}")
                except Exception:
                    pass  # Ignore logging errors during shutdown
                if not self._stopping:
                    await asyncio.sleep(self.retry_delay)

        # Ensure we drain the queue on shutdown
        if self._stopping:
            await self._drain_queue()

    async def _collect_batch(self) -> List[Dict[str, Any]]:
        """Collect a batch of events from the queue."""
        start_time = time.time()
        metrics = self._container.get_metrics_collector() if self._container else None
        batch = []

        # Get the first event (blocking)
        try:
            first_event = await asyncio.wait_for(
                self.queue.get(), timeout=self.batch_timeout
            )
            batch.append(first_event)
            if metrics:
                dequeue_latency_ms = (time.time() - start_time) * 1000
                metrics.record_dequeue(dequeue_latency_ms)
        except asyncio.TimeoutError:
            return batch

        # Try to get more events (non-blocking)
        while len(batch) < self.batch_size:
            try:
                dequeue_start = time.time()
                event = self.queue.get_nowait()
                batch.append(event)
                if metrics:
                    dequeue_latency_ms = (time.time() - dequeue_start) * 1000
                    metrics.record_dequeue(dequeue_latency_ms)
            except asyncio.QueueEmpty:
                break

        return batch

    async def _process_batch(self, batch: List[Dict[str, Any]]) -> None:
        """Process a batch of events."""
        start_time = time.time()
        metrics = self._container.get_metrics_collector() if self._container else None

        for event in batch:
            await self._process_event(event)

        if metrics:
            processing_time_ms = (time.time() - start_time) * 1000
            metrics.record_batch_processing(processing_time_ms)

    async def _process_event(self, event: Dict[str, Any]) -> None:
        """Process a single event with retry logic."""
        start_time = time.time()
        metrics = self._container.get_metrics_collector() if self._container else None

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
            # Record successful event processing
            if metrics:
                processing_time_ms = (time.time() - start_time) * 1000
                metrics.record_log_event(processing_time_ms)
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
        start_time = time.time()
        metrics = self._container.get_metrics_collector() if self._container else None

        if self._stopping:
            return False

        # Apply sampling if enabled
        if self.sampling_rate < 1.0 and rnd.random() > self.sampling_rate:
            if metrics:
                metrics.record_sampled_event()
            return False

        try:
            if self.overflow_strategy == "drop":
                # Drop strategy: try to enqueue, drop if full
                try:
                    self.queue.put_nowait(event_dict)
                    if metrics:
                        latency_ms = (time.time() - start_time) * 1000
                        metrics.record_enqueue(latency_ms)
                        metrics.record_queue_size(self.queue.qsize())
                    return True
                except asyncio.QueueFull:
                    if metrics:
                        metrics.record_dropped_event()
                    return False
            elif self.overflow_strategy == "block":
                # Block strategy: wait until space is available
                try:
                    await self.queue.put(event_dict)
                    if metrics:
                        latency_ms = (time.time() - start_time) * 1000
                        metrics.record_enqueue(latency_ms)
                        metrics.record_queue_size(self.queue.qsize())
                    return True
                except asyncio.CancelledError:
                    return False
            else:  # "sample"
                # Sample strategy: use sampling rate for overflow
                try:
                    self.queue.put_nowait(event_dict)
                    if metrics:
                        latency_ms = (time.time() - start_time) * 1000
                        metrics.record_enqueue(latency_ms)
                        metrics.record_queue_size(self.queue.qsize())
                    return True
                except asyncio.QueueFull:
                    if metrics:
                        metrics.record_dropped_event()
                    return False
        except Exception as e:
            # Unexpected error during enqueue
            queue_state = {
                "queue_size": self.queue.qsize(),
                "overflow_strategy": self.overflow_strategy,
                "sampling_rate": self.sampling_rate,
            }
            raise handle_queue_error(e, "enqueue", queue_state) from e
