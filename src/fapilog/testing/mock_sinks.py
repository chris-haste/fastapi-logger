"""Mock sink implementations for testing custom sinks."""

import asyncio
import random
import time
from typing import Any, Dict, List

from .._internal.queue import Sink


class RecordingSink(Sink):
    """Sink that records all events for testing."""

    def __init__(self):
        super().__init__()
        self.events: List[Dict[str, Any]] = []
        self._write_count = 0

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Record the event for later inspection.

        Args:
            event_dict: The log event dictionary to record
        """
        # Add timestamp and write count for testing
        enriched_event = event_dict.copy()
        enriched_event["_recorded_at"] = time.time()
        enriched_event["_write_count"] = self._write_count

        self.events.append(enriched_event)
        self._write_count += 1

    def clear(self) -> None:
        """Clear all recorded events."""
        self.events.clear()
        self._write_count = 0

    def get_events(self, level: str = None) -> List[Dict[str, Any]]:
        """Get recorded events, optionally filtered by level.

        Args:
            level: Optional log level to filter by

        Returns:
            List of recorded events
        """
        if level is None:
            return self.events.copy()

        return [event for event in self.events if event.get("level") == level]

    def get_last_event(self) -> Dict[str, Any]:
        """Get the most recently recorded event.

        Returns:
            The last recorded event, or empty dict if none
        """
        return self.events[-1] if self.events else {}


class FailingSink(Sink):
    """Sink that fails for error testing."""

    def __init__(self, failure_rate: float = 1.0, failure_message: str = None):
        super().__init__()
        self.failure_rate = failure_rate
        self.failure_message = failure_message or "Mock sink failure"
        self._attempt_count = 0
        self._failure_count = 0

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Fail based on failure rate.

        Args:
            event_dict: The log event dictionary

        Raises:
            Exception: Based on failure_rate probability
        """
        self._attempt_count += 1

        if random.random() < self.failure_rate:
            self._failure_count += 1
            raise Exception(f"{self.failure_message} (attempt {self._attempt_count})")

    def get_stats(self) -> Dict[str, int]:
        """Get failure statistics.

        Returns:
            Dictionary with attempt and failure counts
        """
        return {
            "attempts": self._attempt_count,
            "failures": self._failure_count,
            "successes": self._attempt_count - self._failure_count,
        }

    def reset_stats(self) -> None:
        """Reset failure statistics."""
        self._attempt_count = 0
        self._failure_count = 0


class SlowSink(Sink):
    """Sink that simulates slow operations."""

    def __init__(self, delay: float = 0.1, jitter: float = 0.0):
        super().__init__()
        self.delay = delay
        self.jitter = jitter
        self._total_delay = 0.0
        self._write_count = 0

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Write with artificial delay.

        Args:
            event_dict: The log event dictionary
        """
        # Calculate delay with optional jitter
        actual_delay = self.delay
        if self.jitter > 0:
            jitter_amount = random.uniform(-self.jitter, self.jitter)
            actual_delay = max(0, self.delay + jitter_amount)

        # Apply delay
        await asyncio.sleep(actual_delay)

        # Track statistics
        self._total_delay += actual_delay
        self._write_count += 1

    def get_performance_stats(self) -> Dict[str, float]:
        """Get performance statistics.

        Returns:
            Dictionary with timing statistics
        """
        avg_delay = (
            self._total_delay / self._write_count if self._write_count > 0 else 0.0
        )

        return {
            "total_delay": self._total_delay,
            "write_count": self._write_count,
            "average_delay": avg_delay,
            "configured_delay": self.delay,
            "configured_jitter": self.jitter,
        }

    def reset_stats(self) -> None:
        """Reset performance statistics."""
        self._total_delay = 0.0
        self._write_count = 0


class ConditionalFailingSink(Sink):
    """Sink that fails based on event content."""

    def __init__(self, fail_on_level: str = "error", fail_on_field: str = None):
        super().__init__()
        self.fail_on_level = fail_on_level
        self.fail_on_field = fail_on_field
        self._failure_conditions_met = 0

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Fail if event meets configured conditions.

        Args:
            event_dict: The log event dictionary

        Raises:
            Exception: If failure conditions are met
        """
        should_fail = False
        failure_reason = []

        # Check level condition
        if self.fail_on_level and event_dict.get("level") == self.fail_on_level:
            should_fail = True
            failure_reason.append(f"level={self.fail_on_level}")

        # Check field condition
        if self.fail_on_field and self.fail_on_field in event_dict:
            should_fail = True
            failure_reason.append(f"field={self.fail_on_field}")

        if should_fail:
            self._failure_conditions_met += 1
            reason_str = ", ".join(failure_reason)
            raise Exception(f"Conditional failure: {reason_str}")

    def get_failure_count(self) -> int:
        """Get number of times failure conditions were met.

        Returns:
            Count of conditional failures
        """
        return self._failure_conditions_met


class BatchingSink(Sink):
    """Sink that batches events before processing."""

    def __init__(self, batch_size: int = 5, auto_flush: bool = True):
        super().__init__()
        self.batch_size = batch_size
        self.auto_flush = auto_flush
        self._batch: List[Dict[str, Any]] = []
        self._processed_batches: List[List[Dict[str, Any]]] = []

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Add event to batch and process if full.

        Args:
            event_dict: The log event dictionary
        """
        self._batch.append(event_dict.copy())

        if len(self._batch) >= self.batch_size and self.auto_flush:
            await self.flush()

    async def flush(self) -> None:
        """Process the current batch."""
        if self._batch:
            self._processed_batches.append(self._batch.copy())
            self._batch.clear()

    def get_batches(self) -> List[List[Dict[str, Any]]]:
        """Get all processed batches.

        Returns:
            List of processed batches
        """
        return self._processed_batches.copy()

    def get_current_batch(self) -> List[Dict[str, Any]]:
        """Get the current unflushed batch.

        Returns:
            Current batch of events
        """
        return self._batch.copy()

    def get_stats(self) -> Dict[str, int]:
        """Get batching statistics.

        Returns:
            Dictionary with batch statistics
        """
        total_events = sum(len(batch) for batch in self._processed_batches)
        total_events += len(self._batch)

        return {
            "processed_batches": len(self._processed_batches),
            "current_batch_size": len(self._batch),
            "total_events": total_events,
            "configured_batch_size": self.batch_size,
        }
