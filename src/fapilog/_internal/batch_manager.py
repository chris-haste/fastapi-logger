"""Batch manager for handling log event batching with configurable strategies."""

import asyncio
import time
from typing import Any, Awaitable, Callable, Dict, List, Optional


class BatchManager:
    """Handles batching logic with configurable strategies."""

    def __init__(
        self,
        batch_size: int,
        batch_interval: float,
        flush_callback: Callable[[List[Dict[str, Any]]], Awaitable[None]],
    ) -> None:
        """Initialize the batch manager.

        Args:
            batch_size: Number of events to batch before triggering flush
            batch_interval: Maximum time to wait before flushing batch (seconds)
            flush_callback: Async function to call when batch should be flushed
        """
        self.batch_size = batch_size
        self.batch_interval = batch_interval
        self._flush_callback = flush_callback

        # Batch state
        self._batch: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()
        self._timer_task: Optional[asyncio.Task[None]] = None
        self._last_flush = time.time()

    async def add_event(self, event: Dict[str, Any]) -> None:
        """Add event to batch, triggering flush if batch is full.

        Args:
            event: The log event to add to the batch
        """
        async with self._lock:
            self._batch.append(event)
            batch_was_empty = len(self._batch) == 1

            should_flush = len(self._batch) >= self.batch_size

            if should_flush:
                await self._flush_batch()
            elif batch_was_empty:
                # Start interval flush timer if this is the first event in batch
                self._start_flush_timer()

    async def flush_batch(self) -> None:
        """Force flush current batch regardless of size or time."""
        async with self._lock:
            if self._batch:
                await self._flush_batch()

    async def _flush_batch(self) -> None:
        """Internal flush implementation (assumes lock is held)."""
        if not self._batch:
            return

        # Cancel interval flush timer
        if self._timer_task and not self._timer_task.done():
            self._timer_task.cancel()
            self._timer_task = None

        # Get current batch and reset
        batch_to_send = self._batch.copy()
        self._batch.clear()
        self._last_flush = time.time()

        # Send batch via callback
        await self._flush_callback(batch_to_send)

    def _start_flush_timer(self) -> None:
        """Start or restart the interval flush timer."""
        if self._timer_task and not self._timer_task.done():
            self._timer_task.cancel()

        loop = asyncio.get_running_loop()
        self._timer_task = loop.create_task(self._interval_flush())

    async def _interval_flush(self) -> None:
        """Handle interval-based flushing."""
        try:
            await asyncio.sleep(self.batch_interval)
            async with self._lock:
                if self._batch:
                    await self._flush_batch()
        except asyncio.CancelledError:
            pass

    async def close(self) -> None:
        """Close the batch manager and flush any remaining events."""
        # Cancel interval flush timer
        if self._timer_task and not self._timer_task.done():
            self._timer_task.cancel()
            try:
                await self._timer_task
            except asyncio.CancelledError:
                pass
            self._timer_task = None

        # Flush any remaining events
        async with self._lock:
            if self._batch:
                await self._flush_batch()

    @property
    def current_batch_size(self) -> int:
        """Get the current number of events in the batch."""
        return len(self._batch)

    @property
    def time_since_last_flush(self) -> float:
        """Get time in seconds since last flush."""
        return time.time() - self._last_flush
