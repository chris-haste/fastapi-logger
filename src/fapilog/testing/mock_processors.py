"""Mock processor implementations for testing custom processors."""

import random
import time
from typing import Any, Callable, Dict, List, Optional

from ..exceptions import ProcessorExecutionError
from ..processors.base import Processor


class RecordingProcessor(Processor):
    """Processor that records all processed events for testing."""

    def __init__(self, **config: Any) -> None:
        """Initialize recording processor.

        Args:
            **config: Configuration parameters
        """
        super().__init__(**config)
        self.recorded_events: List[Dict[str, Any]] = []
        self._process_count = 0

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Record the event and pass it through.

        Args:
            logger: Logger instance
            method_name: Logging method name
            event_dict: Event dictionary to process

        Returns:
            The processed event dictionary
        """
        # Add recording metadata
        enriched_event = event_dict.copy()
        enriched_event["_recorded_at"] = time.time()
        enriched_event["_process_count"] = self._process_count
        enriched_event["_method_name"] = method_name

        self.recorded_events.append(enriched_event)
        self._process_count += 1

        return event_dict

    def clear(self) -> None:
        """Clear all recorded events."""
        self.recorded_events.clear()
        self._process_count = 0

    def get_events(self, level: str = None) -> List[Dict[str, Any]]:
        """Get recorded events, optionally filtered by level.

        Args:
            level: Optional log level to filter by

        Returns:
            List of recorded events
        """
        if level is None:
            return self.recorded_events.copy()

        return [event for event in self.recorded_events if event.get("level") == level]

    def get_last_event(self) -> Dict[str, Any]:
        """Get the most recently recorded event.

        Returns:
            The last recorded event, or empty dict if none
        """
        return self.recorded_events[-1] if self.recorded_events else {}

    def get_stats(self) -> Dict[str, int]:
        """Get processing statistics.

        Returns:
            Dictionary with processing statistics
        """
        level_counts: Dict[str, int] = {}
        for event in self.recorded_events:
            level = event.get("level", "unknown")
            level_counts[level] = level_counts.get(level, 0) + 1

        return {
            "total_events": len(self.recorded_events),
            "process_count": self._process_count,
            "level_counts": level_counts,  # type: ignore[dict-item]
        }


class FailingProcessor(Processor):
    """Processor that fails predictably for error handling tests."""

    def __init__(
        self,
        failure_rate: float = 1.0,
        failure_message: str = None,
        fail_on_start: bool = False,
        fail_on_stop: bool = False,
        **config: Any,
    ) -> None:
        """Initialize failing processor.

        Args:
            failure_rate: Probability of failure (0.0 to 1.0)
            failure_message: Custom failure message
            fail_on_start: Whether to fail on start()
            fail_on_stop: Whether to fail on stop()
            **config: Configuration parameters
        """
        super().__init__(**config)
        self.failure_rate = failure_rate
        self.failure_message = failure_message or "Mock processor failure"
        self.fail_on_start = fail_on_start
        self.fail_on_stop = fail_on_stop
        self._attempt_count = 0
        self._failure_count = 0

    async def _start_impl(self) -> None:
        """Start implementation that can fail."""
        if self.fail_on_start:
            raise ProcessorExecutionError("Processor start failure")

    async def _stop_impl(self) -> None:
        """Stop implementation that can fail."""
        if self.fail_on_stop:
            raise ProcessorExecutionError("Processor stop failure")

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process event with potential failure.

        Args:
            logger: Logger instance
            method_name: Logging method name
            event_dict: Event dictionary to process

        Returns:
            The processed event dictionary

        Raises:
            ProcessorExecutionError: Based on failure_rate probability
        """
        self._attempt_count += 1

        if random.random() < self.failure_rate:
            self._failure_count += 1
            raise ProcessorExecutionError(
                f"{self.failure_message} (attempt {self._attempt_count})"
            )

        return event_dict

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


class SlowProcessor(Processor):
    """Processor that introduces delays for performance testing."""

    def __init__(self, delay_ms: int = 100, **config: Any) -> None:
        """Initialize slow processor.

        Args:
            delay_ms: Delay in milliseconds for each process call
            **config: Configuration parameters
        """
        super().__init__(**config)
        self.delay_ms = delay_ms
        self._total_delay = 0.0
        self._call_count = 0

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process event with artificial delay.

        Args:
            logger: Logger instance
            method_name: Logging method name
            event_dict: Event dictionary to process

        Returns:
            The processed event dictionary
        """
        delay_seconds = self.delay_ms / 1000.0
        time.sleep(delay_seconds)

        self._total_delay += delay_seconds
        self._call_count += 1

        # Add timing information to the event
        result = event_dict.copy()
        result["_processing_delay_ms"] = self.delay_ms
        result["_call_count"] = self._call_count

        return result

    def get_timing_stats(self) -> Dict[str, float]:
        """Get timing statistics.

        Returns:
            Dictionary with timing statistics
        """
        avg_delay = self._total_delay / self._call_count if self._call_count > 0 else 0

        return {
            "total_delay_seconds": self._total_delay,
            "call_count": self._call_count,
            "average_delay_seconds": avg_delay,
            "configured_delay_ms": self.delay_ms,
        }


class TransformProcessor(Processor):
    """Processor that transforms events using a custom function."""

    def __init__(
        self,
        transform_func: Callable[[Dict[str, Any]], Dict[str, Any]] = None,
        **config: Any,
    ) -> None:
        """Initialize transform processor.

        Args:
            transform_func: Function to transform events
            **config: Configuration parameters
        """
        super().__init__(**config)
        self.transform_func = (
            transform_func if transform_func is not None else (lambda x: x)  # type: ignore[truthy-function]
        )
        self._transformation_count = 0

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transform event using the configured function.

        Args:
            logger: Logger instance
            method_name: Logging method name
            event_dict: Event dictionary to process

        Returns:
            The transformed event dictionary
        """
        try:
            result = self.transform_func(event_dict)
            self._transformation_count += 1

            # Ensure result is a dict
            if not isinstance(result, dict):
                raise ProcessorExecutionError(
                    f"Transform function must return dict, got {type(result)}"
                )

            return result

        except Exception as e:
            if isinstance(e, ProcessorExecutionError):
                raise
            raise ProcessorExecutionError(f"Transform function failed: {e}") from e

    def get_transformation_count(self) -> int:
        """Get number of successful transformations.

        Returns:
            Count of transformations
        """
        return self._transformation_count


class ConditionalFailingProcessor(Processor):
    """Processor that fails based on event content."""

    def __init__(
        self,
        fail_on_level: str = None,
        fail_on_field: str = None,
        fail_on_value: Any = None,
        **config: Any,
    ) -> None:
        """Initialize conditional failing processor.

        Args:
            fail_on_level: Fail when event has this log level
            fail_on_field: Fail when event contains this field
            fail_on_value: Fail when event contains this value (in any field)
            **config: Configuration parameters
        """
        super().__init__(**config)
        self.fail_on_level = fail_on_level
        self.fail_on_field = fail_on_field
        self.fail_on_value = fail_on_value
        self._failure_conditions_met = 0

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process event and fail if conditions are met.

        Args:
            logger: Logger instance
            method_name: Logging method name
            event_dict: Event dictionary to process

        Returns:
            The processed event dictionary

        Raises:
            ProcessorExecutionError: If failure conditions are met
        """
        should_fail = False
        failure_reasons = []

        # Check level condition
        if self.fail_on_level and event_dict.get("level") == self.fail_on_level:
            should_fail = True
            failure_reasons.append(f"level={self.fail_on_level}")

        # Check field condition
        if self.fail_on_field and self.fail_on_field in event_dict:
            should_fail = True
            failure_reasons.append(f"field={self.fail_on_field}")

        # Check value condition
        if self.fail_on_value is not None:
            for _key, value in event_dict.items():
                if value == self.fail_on_value:
                    should_fail = True
                    failure_reasons.append(f"value={self.fail_on_value}")
                    break

        if should_fail:
            self._failure_conditions_met += 1
            reason_str = ", ".join(failure_reasons)
            raise ProcessorExecutionError(f"Conditional failure: {reason_str}")

        return event_dict

    def get_failure_count(self) -> int:
        """Get number of times failure conditions were met.

        Returns:
            Count of conditional failures
        """
        return self._failure_conditions_met


class BatchingProcessor(Processor):
    """Processor that batches events before processing."""

    def __init__(
        self, batch_size: int = 5, auto_process: bool = True, **config: Any
    ) -> None:
        """Initialize batching processor.

        Args:
            batch_size: Number of events to batch together
            auto_process: Whether to automatically process full batches
            **config: Configuration parameters
        """
        super().__init__(**config)
        self.batch_size = batch_size
        self.auto_process = auto_process
        self._current_batch: List[Dict[str, Any]] = []
        self._processed_batches: List[List[Dict[str, Any]]] = []

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add event to batch and process if full.

        Args:
            logger: Logger instance
            method_name: Logging method name
            event_dict: Event dictionary to process

        Returns:
            The processed event dictionary with batch metadata
        """
        # Add to current batch
        self._current_batch.append(event_dict.copy())

        # Calculate batch metadata BEFORE potential flush
        batch_position = len(self._current_batch) - 1
        current_batch_size = len(self._current_batch)
        batch_id = len(self._processed_batches)

        # Process batch if full and auto-processing is enabled
        if len(self._current_batch) >= self.batch_size and self.auto_process:
            self.flush_batch()

        # Return event with batch metadata
        result = event_dict.copy()
        result["_batch_position"] = batch_position
        result["_current_batch_size"] = current_batch_size
        result["_batch_id"] = batch_id

        return result

    def flush_batch(self) -> List[Dict[str, Any]]:
        """Process the current batch.

        Returns:
            The processed batch
        """
        if self._current_batch:
            batch_copy = self._current_batch.copy()
            self._processed_batches.append(batch_copy)
            self._current_batch.clear()
            return batch_copy
        return []

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
        return self._current_batch.copy()

    def get_stats(self) -> Dict[str, int]:
        """Get batching statistics.

        Returns:
            Dictionary with batch statistics
        """
        total_events = sum(len(batch) for batch in self._processed_batches)
        total_events += len(self._current_batch)

        return {
            "processed_batches": len(self._processed_batches),
            "current_batch_size": len(self._current_batch),
            "total_events": total_events,
            "configured_batch_size": self.batch_size,
        }


class FilteringProcessor(Processor):
    """Processor that filters events based on criteria."""

    def __init__(
        self,
        filter_level: str = None,
        filter_field: str = None,
        filter_value: Any = None,
        invert_filter: bool = False,
        **config: Any,
    ) -> None:
        """Initialize filtering processor.

        Args:
            filter_level: Only allow events with this log level
            filter_field: Only allow events containing this field
            filter_value: Only allow events containing this value
            invert_filter: Invert the filter logic (exclude instead of include)
            **config: Configuration parameters
        """
        super().__init__(**config)
        self.filter_level = filter_level
        self.filter_field = filter_field
        self.filter_value = filter_value
        self.invert_filter = invert_filter
        self._filtered_count = 0
        self._passed_count = 0

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Filter event based on configured criteria.

        Args:
            logger: Logger instance
            method_name: Logging method name
            event_dict: Event dictionary to process

        Returns:
            The event dictionary if it passes the filter, None if filtered out
        """
        should_pass = True

        # Check level filter
        if self.filter_level:
            should_pass = should_pass and (event_dict.get("level") == self.filter_level)

        # Check field filter
        if self.filter_field:
            should_pass = should_pass and (self.filter_field in event_dict)

        # Check value filter
        if self.filter_value is not None:
            value_found = any(
                value == self.filter_value for value in event_dict.values()
            )
            should_pass = should_pass and value_found

        # Apply inversion if configured
        if self.invert_filter:
            should_pass = not should_pass

        if should_pass:
            self._passed_count += 1
            return event_dict
        else:
            self._filtered_count += 1
            return None

    def get_filter_stats(self) -> Dict[str, int]:
        """Get filtering statistics.

        Returns:
            Dictionary with filtering statistics
        """
        total = self._filtered_count + self._passed_count
        pass_rate = (self._passed_count / total * 100) if total > 0 else 0

        return {
            "total_processed": total,
            "passed": self._passed_count,
            "filtered": self._filtered_count,
            "pass_rate_percent": float(pass_rate),  # type: ignore[dict-item]
        }
