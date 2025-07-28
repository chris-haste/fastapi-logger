"""Error handling utilities for fapilog."""

import logging
import time
from typing import Any, Awaitable, Callable, Dict, Optional, TypeVar

from ..exceptions import (
    ConfigurationError,
    ContextError,
    FapilogError,
    MiddlewareError,
    QueueError,
    RedactionError,
    SinkConfigurationError,
    SinkConnectionError,
    SinkError,
    SinkErrorContextBuilder,
    SinkTimeoutError,
    SinkWriteError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class StandardSinkErrorHandling:
    """Mixin providing standard error handling for all sinks."""

    def _handle_sink_error(
        self,
        error: Exception,
        operation: str,
        event_dict: Dict[str, Any],
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> SinkError:
        """Convert any exception to standard sink error with context.

        Args:
            error: The original exception that occurred
            operation: The operation that was being performed
            event_dict: The log event being processed
            additional_context: Sink-specific additional context

        Returns:
            Appropriate SinkError subclass with full context
        """
        sink_name = self.__class__.__name__

        # Build standardized context
        context = SinkErrorContextBuilder.build_write_context(
            sink_name=sink_name,
            event_dict=event_dict,
            operation=operation,
            additional_context=additional_context,
        )

        # Map to appropriate error type based on exception
        error_message = str(error)

        # Check for connection-related errors
        if self._is_connection_error(error):
            return SinkConnectionError(error_message, sink_name, context)

        # Check for timeout errors
        elif self._is_timeout_error(error):
            return SinkTimeoutError(error_message, sink_name, context)

        # Check for configuration errors
        elif self._is_configuration_error(error):
            return SinkConfigurationError(error_message, sink_name, context)

        # Default to write error for all other cases
        else:
            return SinkWriteError(error_message, sink_name, context)

    def _is_connection_error(self, error: Exception) -> bool:
        """Check if error is connection-related."""
        try:
            import httpx

            if isinstance(error, (ConnectionError, httpx.NetworkError)):
                return True
        except ImportError:
            pass

        return isinstance(error, ConnectionError)

    def _is_timeout_error(self, error: Exception) -> bool:
        """Check if error is timeout-related."""
        try:
            import httpx

            if isinstance(error, (TimeoutError, httpx.TimeoutException)):
                return True
        except ImportError:
            pass

        return isinstance(error, TimeoutError)

    def _is_configuration_error(self, error: Exception) -> bool:
        """Check if error is configuration-related."""
        return isinstance(error, (ValueError, TypeError, AttributeError))

    def _log_error_with_context(self, standardized_error: SinkError) -> None:
        """Log the standardized error with full context.

        Args:
            standardized_error: The standardized sink error to log
        """
        log_error_with_context(
            error=standardized_error,
            context=standardized_error.context,
            level=logging.ERROR,
        )


def log_error_with_context(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    level: int = logging.ERROR,
) -> None:
    """Log an error with additional context information.

    Args:
        error: The exception that occurred
        context: Additional context information
        level: Logging level to use
    """
    error_context = {}

    # Extract context from fapilog exceptions
    if isinstance(error, FapilogError):
        error_context.update(error.context)

    # Add provided context
    if context:
        error_context.update(context)

    # Build log message
    if error_context:
        context_str = ", ".join(f"{k}={v}" for k, v in error_context.items())
        message = f"{error} (context: {context_str})"
    else:
        message = str(error)

    # Log with appropriate level
    logger.log(level, message, exc_info=True)


def handle_configuration_error(
    error: Exception,
    setting: str,
    value: Any = None,
    expected_type: Optional[str] = None,
) -> ConfigurationError:
    """Handle configuration-related errors with proper context.

    Args:
        error: The original exception
        setting: Name of the problematic setting
        value: Value that caused the error
        expected_type: Expected type or format

    Returns:
        ConfigurationError with proper context
    """
    context = {
        "setting": setting,
        "original_error": str(error),
    }

    if value is not None:
        context["value"] = value

    if expected_type:
        context["expected_type"] = expected_type

    message = f"Configuration error for setting '{setting}': {error}"

    log_error_with_context(error, context)

    return ConfigurationError(message, setting, value, expected_type)


def handle_queue_error(
    error: Exception,
    operation: str,
    queue_state: Optional[Dict[str, Any]] = None,
) -> QueueError:
    """Handle queue-related errors with proper context.

    Args:
        error: The original exception
        operation: Operation that failed (e.g., "enqueue", "process", "shutdown")
        queue_state: Current state of the queue

    Returns:
        QueueError with proper context
    """
    context = {
        "operation": operation,
        "original_error": str(error),
    }

    if queue_state:
        context["queue_state"] = queue_state

    message = f"Queue {operation} failed: {error}"

    log_error_with_context(error, context)

    return QueueError(message, queue_state, operation)


def handle_middleware_error(
    error: Exception,
    request_info: Optional[Dict[str, Any]] = None,
    operation: str = "process",
) -> MiddlewareError:
    """Handle middleware-related errors with proper context.

    Args:
        error: The original exception
        request_info: Information about the request
        operation: Operation that failed

    Returns:
        MiddlewareError with proper context
    """
    context = {
        "operation": operation,
        "original_error": str(error),
    }

    if request_info:
        context["request_info"] = request_info

    message = f"Middleware {operation} failed: {error}"

    log_error_with_context(error, context)

    return MiddlewareError(message, request_info, operation)


def handle_redaction_error(
    error: Exception,
    field: str,
    pattern: Optional[str] = None,
) -> RedactionError:
    """Handle redaction-related errors with proper context.

    Args:
        error: The original exception
        field: Field that failed to redact
        pattern: Pattern that caused the error

    Returns:
        RedactionError with proper context
    """
    context = {
        "field": field,
        "original_error": str(error),
    }

    if pattern:
        context["pattern"] = pattern

    message = f"Redaction failed for field '{field}': {error}"

    log_error_with_context(error, context)

    return RedactionError(message, field, pattern)


def handle_context_error(
    error: Exception,
    context_key: str,
    operation: str = "access",
) -> ContextError:
    """Handle context-related errors with proper context.

    Args:
        error: The original exception
        context_key: Context key that caused the error
        operation: Operation that failed

    Returns:
        ContextError with proper context
    """
    context = {
        "context_key": context_key,
        "operation": operation,
        "original_error": str(error),
    }

    message = f"Context {operation} failed for key '{context_key}': {error}"

    log_error_with_context(error, context)

    return ContextError(message, context_key, operation)


def safe_execute(
    func: Callable[[], T],
    error_handler: Callable[[Exception], FapilogError],
    default: Optional[T] = None,
) -> Optional[T]:
    """Safely execute a function with error handling.

    Args:
        func: Function to execute
        error_handler: Function to handle errors
        default: Default value to return on error

    Returns:
        Result of func() or default value on error
    """
    try:
        return func()
    except Exception as e:
        error_handler(e)
        return default


async def safe_execute_async(
    func: Callable[[], T],
    error_handler: Callable[[Exception], FapilogError],
    default: Optional[T] = None,
) -> Optional[T]:
    """Safely execute an async function with error handling.

    Args:
        func: Async function to execute
        error_handler: Function to handle errors
        default: Default value to return on error

    Returns:
        Result of func() or default value on error
    """
    try:
        return await func()
    except Exception as e:
        error_handler(e)
        return default


def graceful_degradation(
    primary_func: Callable[[], T],
    fallback_func: Callable[[], T],
    error_handler: Callable[[Exception], FapilogError],
) -> T:
    """Execute primary function with graceful degradation to fallback.

    Args:
        primary_func: Primary function to try first
        fallback_func: Fallback function to try if primary fails
        error_handler: Function to handle errors

    Returns:
        Result from primary_func or fallback_func
    """
    try:
        return primary_func()
    except Exception as e:
        error_handler(e)
        logger.warning("Primary operation failed, using fallback")
        try:
            return fallback_func()
        except Exception as fallback_error:
            error_handler(fallback_error)
            raise error_handler(fallback_error) from fallback_error


async def graceful_degradation_async(
    primary_func: Callable[[], T],
    fallback_func: Callable[[], T],
    error_handler: Callable[[Exception], FapilogError],
) -> T:
    """Execute async primary function with graceful degradation to fallback.

    Args:
        primary_func: Primary async function to try first
        fallback_func: Fallback async function to try if primary fails
        error_handler: Function to handle errors

    Returns:
        Result from primary_func or fallback_func
    """
    try:
        return await primary_func()
    except Exception as e:
        error_handler(e)
        logger.warning("Primary operation failed, using fallback")
        try:
            return await fallback_func()
        except Exception as fallback_error:
            error_handler(fallback_error)
            raise error_handler(fallback_error) from fallback_error


def retry_with_backoff(
    func: Callable[[], T],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    error_handler: Optional[Callable[[Exception], FapilogError]] = None,
) -> T:
    """Retry a function with exponential backoff.

    Args:
        func: Function to retry
        max_retries: Maximum number of retries
        base_delay: Base delay between retries
        max_delay: Maximum delay between retries
        error_handler: Optional error handler

    Returns:
        Result of func()

    Raises:
        Last exception if all retries fail
    """

    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            last_exception = e

            if error_handler:
                error_handler(e)

            if attempt < max_retries:
                delay = min(base_delay * (2**attempt), max_delay)
                logger.warning(
                    f"Attempt {attempt + 1} failed, retrying in {delay}s: {e}"
                )
                time.sleep(delay)
            else:
                logger.error(f"All {max_retries + 1} attempts failed")

    raise last_exception


async def retry_with_backoff_async(
    func: Callable[[], Awaitable[T]],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    error_handler: Optional[Callable[[Exception], FapilogError]] = None,
) -> T:
    """Retry an async function with exponential backoff.

    Args:
        func: Async function to retry
        max_retries: Maximum number of retries
        base_delay: Base delay between retries
        max_delay: Maximum delay between retries
        error_handler: Optional error handler

    Returns:
        Result of func()

    Raises:
        Last exception if all retries fail
    """
    import asyncio

    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await func()
        except Exception as e:
            last_exception = e

            if error_handler:
                error_handler(e)

            if attempt < max_retries:
                delay = min(base_delay * (2**attempt), max_delay)
                logger.warning(
                    f"Attempt {attempt + 1} failed, retrying in {delay}s: {e}"
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"All {max_retries + 1} attempts failed")

    raise last_exception
