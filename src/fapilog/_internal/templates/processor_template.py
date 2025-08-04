"""
Template for new processor implementations.

This template demonstrates standardized async-safe patterns for processor development.
Follow these patterns for consistent behavior and to avoid race conditions.

Features:
- Async-safe resource management
- Consistent error handling
- Performance-optimized operations
- Proper metrics collection
- Comprehensive testing support
"""

import asyncio
import logging
import time
from typing import Any, Callable, Dict, Optional, cast

from ...exceptions import ProcessorConfigurationError
from ...processors.async_base import AsyncProcessorBase

logger = logging.getLogger(__name__)


class TemplateProcessor(AsyncProcessorBase):
    """
    Template processor demonstrating standard patterns.

    This template shows how to implement a processor that:
    - Inherits from AsyncProcessorBase for async-safe operations
    - Uses standardized error handling patterns
    - Implements performance-optimized operations
    - Provides proper metrics collection
    - Follows consistent async patterns

    Usage:
        processor = TemplateProcessor(
            max_events_per_key=100,
            window_seconds=60,
            key_field="source"
        )
        await processor.start()
        result = await processor.process_async(logger, "info", event_dict)
        await processor.stop()
    """

    def __init__(
        self,
        max_events_per_key: int = 100,
        window_seconds: int = 60,
        key_field: str = "source",
        **config: Any,
    ) -> None:
        """Initialize template processor with standardized patterns.

        Args:
            max_events_per_key: Maximum events to process per key in window
            window_seconds: Time window in seconds for rate limiting
            key_field: Field to use as processing key
            **config: Additional configuration parameters
        """
        # Set attributes before super().__init__() for validate_config()
        self.max_events_per_key = max_events_per_key
        self.window_seconds = window_seconds
        self.key_field = key_field

        # Configure cache settings for AsyncProcessorBase
        config.update(
            {
                "cache_max_size": 1000,
                "cache_ttl_seconds": window_seconds,
                "processor_id": "TemplateProcessor",
            }
        )

        super().__init__(**config)

        # Processor-specific state
        self._processed_count = 0
        self._dropped_count = 0
        self._error_count = 0

        logger.info(
            f"Initialized TemplateProcessor: max_events={max_events_per_key}, "
            f"window={window_seconds}s, key_field={key_field}"
        )

    def validate_config(self) -> None:
        """Validate processor configuration with standardized patterns.

        Raises:
            ProcessorConfigurationError: If configuration is invalid
        """
        if not isinstance(self.max_events_per_key, int) or self.max_events_per_key <= 0:
            raise ProcessorConfigurationError(
                "max_events_per_key must be a positive integer"
            )

        if not isinstance(self.window_seconds, int) or self.window_seconds <= 0:
            raise ProcessorConfigurationError(
                "window_seconds must be a positive integer"
            )

        if not isinstance(self.key_field, str) or not self.key_field.strip():
            raise ProcessorConfigurationError("key_field must be a non-empty string")

    def process(
        self, logger_obj: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Process event with standardized sync interface.

        This is the sync entry point that delegates to async processing.
        Maintains backward compatibility with existing processor interfaces.

        Args:
            logger_obj: The logger instance
            method_name: The logging method name
            event_dict: The event dictionary to process

        Returns:
            The processed event dictionary, or None to drop the event
        """
        try:
            # Try to get current event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in an async context, run async version
                asyncio.create_task(
                    self.process_async(logger_obj, method_name, event_dict)
                )
                # For sync compatibility, return the event and let async
                # processing happen. This maintains non-blocking behavior.
                return event_dict
            else:
                # Not in async context, run sync version
                return asyncio.run(
                    self.process_async(logger_obj, method_name, event_dict)
                )
        except RuntimeError:
            # No event loop, run sync version
            return asyncio.run(self.process_async(logger_obj, method_name, event_dict))

    async def process_async(
        self, logger_obj: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Process event with standardized async patterns.

        This method demonstrates the standard async-safe patterns that
        all processors should follow to avoid race conditions.

        Args:
            logger_obj: The logger instance
            method_name: The logging method name
            event_dict: The event dictionary to process

        Returns:
            The processed event dictionary, or None to drop the event
        """
        try:
            # Step 1: Validate input with standardized patterns
            if not self._validate_event(event_dict):
                return event_dict

            # Step 2: Extract processing key with error handling
            key = await self._safe_operation(self._extract_key, event_dict)
            if key is None:
                return event_dict

            # Step 3: Process with async-safe patterns
            result = await self._safe_operation(self._process_event, key, event_dict)

            # Step 4: Update metrics atomically
            await self._atomic_update("metrics", self._update_metrics)

            # Return the result directly - None means drop the event
            return cast(Optional[Dict[str, Any]], result)

        except Exception as e:
            # Step 5: Handle errors with standardized patterns
            await self._handle_processor_error(
                e,
                {
                    "event_dict": event_dict,
                    "method_name": method_name,
                    "operation": "processing",
                },
            )
            return event_dict

    def _validate_event(self, event_dict: Dict[str, Any]) -> bool:
        """Validate event data with standardized patterns.

        Args:
            event_dict: Event dictionary to validate

        Returns:
            True if event is valid, False otherwise
        """
        return event_dict is not None and isinstance(event_dict, dict)

    async def _extract_key(self, event_dict: Dict[str, Any]) -> Optional[str]:
        """Extract processing key from event with error handling.

        Args:
            event_dict: Event dictionary

        Returns:
            Processing key string, or None if extraction fails
        """
        try:
            return str(event_dict.get(self.key_field, "default"))
        except Exception as e:
            logger.warning(f"Failed to extract key from event: {e}")
            return None

    async def _process_event(
        self, key: str, event_dict: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Process event with O(1) operations and async-safe patterns.

        This method demonstrates how to implement efficient processing
        that avoids race conditions and performance bottlenecks.

        Args:
            key: Processing key
            event_dict: Event dictionary to process

        Returns:
            Processed event or None if filtered
        """
        current_time = time.time()

        # Use async-safe cache operations
        cache_key = f"events_{key}"

        # Create a proper async factory function
        async def create_empty_list():
            return []

        events = await self._get_or_create_cached_value(cache_key, create_empty_list)

        # Clean up expired events (O(n) but bounded by max_events_per_key)
        cutoff_time = current_time - self.window_seconds
        valid_events = [ts for ts in events if ts >= cutoff_time]

        # Check if we should process this event
        if len(valid_events) >= self.max_events_per_key:
            # Event should be dropped
            self._dropped_count += 1
            return None

        # Add current event timestamp
        valid_events.append(current_time)

        # Update cache atomically
        await self._update_cache_atomic(cache_key, valid_events)

        # Event should be processed
        self._processed_count += 1
        return event_dict

    async def _update_metrics(self) -> None:
        """Update processor metrics atomically.

        This method demonstrates how to update metrics safely
        in concurrent environments.
        """
        # Metrics are already updated in _process_event
        # This method can be used for periodic metric updates
        pass

    async def _safe_operation(
        self, operation: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        """Execute operation with standardized error handling.

        Args:
            operation: Operation to execute
            *args: Positional arguments for operation
            **kwargs: Keyword arguments for operation

        Returns:
            Result of operation, or None on error
        """
        try:
            if asyncio.iscoroutinefunction(operation):
                return await operation(*args, **kwargs)
            else:
                return operation(*args, **kwargs)
        except Exception as e:
            self._error_count += 1
            logger.error(f"TemplateProcessor operation failed: {e}")
            return None

    async def _start_impl(self) -> None:
        """Async processor startup with standardized patterns.

        Override this method to implement custom async initialization logic.
        Always call super()._start_impl() to ensure proper initialization.
        """
        await super()._start_impl()
        logger.info("TemplateProcessor started")

    async def _stop_impl(self) -> None:
        """Async processor cleanup with standardized patterns.

        Override this method to implement custom async cleanup logic.
        Always call super()._stop_impl() to ensure proper cleanup.
        """
        await super()._stop_impl()
        logger.info("TemplateProcessor stopped")

    def get_metrics(self) -> Dict[str, Any]:
        """Get processor metrics with standardized format.

        Returns:
            Dictionary with processor performance metrics
        """
        base_metrics = super().get_metrics() if hasattr(super(), "get_metrics") else {}
        return {
            **base_metrics,
            "processed_count": self._processed_count,
            "dropped_count": self._dropped_count,
            "error_count": self._error_count,
            "max_events_per_key": self.max_events_per_key,
            "window_seconds": self.window_seconds,
            "key_field": self.key_field,
        }


# Testing patterns
class TestTemplateProcessor:
    """Example test class for TemplateProcessor.

    This demonstrates how to test processors using the standardized
    testing framework.
    """

    def create_processor(self, **config):
        """Create processor instance for testing."""
        return TemplateProcessor(**config)

    async def example_basic_processing(self, processor):
        """Example: Test basic event processing."""
        event = {"user_id": "123", "message": "test"}
        result = await processor.process_async(None, "info", event)
        assert result is not None

    async def example_rate_limiting(self, processor):
        """Example: Test rate limiting behavior."""
        # Send more events than allowed
        for i in range(60):  # More than max_events_per_key
            event = {"user_id": "123", "message": f"test_{i}"}
            result = await processor.process_async(None, "info", event)
            if i < 50:  # First 50 should be processed
                assert result is not None
            else:  # Rest should be dropped
                assert result is None

    async def example_concurrent_access(self, processor):
        """Example: Test concurrent access patterns."""

        async def worker(worker_id):
            for i in range(10):
                event = {"user_id": f"user_{worker_id}", "message": f"test_{i}"}
                await processor.process_async(None, "info", event)

        # Run concurrent workers
        tasks = [worker(i) for i in range(5)]
        await asyncio.gather(*tasks)

        # Verify no crashes
        metrics = processor.get_metrics()
        assert metrics is not None
