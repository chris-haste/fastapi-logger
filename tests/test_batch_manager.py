"""Unit tests for BatchManager component."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from fapilog.async_components.queue.batch_manager import BatchManager


class TestBatchManager:
    """Test cases for BatchManager."""

    @pytest.mark.asyncio
    async def test_batch_size_trigger(self) -> None:
        """Test that flush is triggered when batch size is reached."""
        flush_callback = AsyncMock()
        manager = BatchManager(
            batch_size=2, batch_interval=1.0, flush_callback=flush_callback
        )

        # Add events
        await manager.add_event({"msg": "event1"})
        flush_callback.assert_not_called()

        await manager.add_event({"msg": "event2"})
        flush_callback.assert_called_once()

        # Verify the batched events
        call_args = flush_callback.call_args[0][0]
        assert len(call_args) == 2
        assert call_args[0] == {"msg": "event1"}
        assert call_args[1] == {"msg": "event2"}

    @pytest.mark.asyncio
    async def test_interval_trigger(self) -> None:
        """Test that flush is triggered by interval."""
        flush_callback = AsyncMock()
        manager = BatchManager(
            batch_size=5, batch_interval=0.1, flush_callback=flush_callback
        )

        # Add one event
        await manager.add_event({"msg": "event1"})
        flush_callback.assert_not_called()

        # Wait for interval
        await asyncio.sleep(0.2)
        flush_callback.assert_called_once()

        # Verify the event was flushed
        call_args = flush_callback.call_args[0][0]
        assert len(call_args) == 1
        assert call_args[0] == {"msg": "event1"}

    @pytest.mark.asyncio
    async def test_manual_flush(self) -> None:
        """Test manual flush functionality."""
        flush_callback = AsyncMock()
        manager = BatchManager(
            batch_size=5, batch_interval=1.0, flush_callback=flush_callback
        )

        # Add events
        await manager.add_event({"msg": "event1"})
        await manager.add_event({"msg": "event2"})
        flush_callback.assert_not_called()

        # Manual flush
        await manager.flush_batch()
        flush_callback.assert_called_once()

        # Verify events were flushed
        call_args = flush_callback.call_args[0][0]
        assert len(call_args) == 2

    @pytest.mark.asyncio
    async def test_close_flushes_remaining(self) -> None:
        """Test that close flushes any remaining events."""
        flush_callback = AsyncMock()
        manager = BatchManager(
            batch_size=5, batch_interval=1.0, flush_callback=flush_callback
        )

        # Add events
        await manager.add_event({"msg": "event1"})
        flush_callback.assert_not_called()

        # Close should flush
        await manager.close()
        flush_callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_properties(self) -> None:
        """Test BatchManager properties."""
        flush_callback = AsyncMock()
        manager = BatchManager(
            batch_size=3, batch_interval=1.0, flush_callback=flush_callback
        )

        # Initially empty
        assert manager.current_batch_size == 0

        # Add events
        await manager.add_event({"msg": "event1"})
        assert manager.current_batch_size == 1

        await manager.add_event({"msg": "event2"})
        assert manager.current_batch_size == 2

        # Time since last flush should be small
        assert manager.time_since_last_flush < 1.0
