"""Error handling utilities for processors in fapilog."""

import logging
from typing import Any, Callable, Dict, Optional, Union

from .._internal.error_handling import log_error_with_context
from ..exceptions import (
    ProcessorConfigurationError,
    ProcessorExecutionError,
    ProcessorRegistrationError,
)
from .base import Processor

logger = logging.getLogger(__name__)


def handle_processor_error(
    error: Exception,
    processor_name: str,
    context: Optional[Dict[str, Any]] = None,
    operation: str = "execution",
) -> Union[
    ProcessorExecutionError,
    ProcessorConfigurationError,
    ProcessorRegistrationError,
]:
    """
    Create appropriate processor error with structured context.

    Args:
        error: The original exception that was raised
        processor_name: Name of the processor that failed
        context: Additional context about the failure
        operation: Type of operation that failed

    Returns:
        Appropriate ProcessorError subclass instance
    """
    error_context: Dict[str, Any] = {"operation": operation}

    if context:
        # Filter out sensitive information from context
        sensitive_keys = [
            "password",
            "token",
            "secret",
            "key",
            "api_key",
            "credential",
        ]
        safe_context = {k: v for k, v in context.items() if k not in sensitive_keys}
        error_context.update(safe_context)

    message = f"Processor {operation} failed for {processor_name}: {error}"

    log_error_with_context(error, {"processor_name": processor_name, **error_context})

    # Return appropriate processor error type based on operation
    if operation in ["configuration", "validate_config"]:
        return ProcessorConfigurationError(message, processor_name=processor_name)
    elif operation in ["register", "registration"]:
        return ProcessorRegistrationError(message, processor_name=processor_name)
    else:
        return ProcessorExecutionError(
            message, processor_name=processor_name, operation=operation
        )


def simple_processor_execution(
    processor: Processor,
    logger_instance: Any,
    method_name: str,
    event_dict: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Execute processor with fail-fast error handling.

    Args:
        processor: The processor instance to execute
        logger_instance: Logger instance for capturing errors
        method_name: Name of the method being called
        event_dict: The event dictionary to process

    Returns:
        - Processed event dictionary or None if processor drops the event
        - Original event is returned on failure for graceful degradation
    """
    processor_name = processor.__class__.__name__

    try:
        # Allow processors to return None (SamplingProcessor drops events)
        return processor.process(logger_instance, method_name, event_dict)
    except Exception as e:
        # Log warning and return original event for graceful degradation
        logger.warning(
            f"Processor {processor_name} failed during {method_name}, "
            f"continuing with original event. Error: {e}"
        )
        return event_dict


def create_simple_processor_wrapper(
    processor: Processor,
) -> Callable[[Any, str, Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Create a simple wrapper for processor execution with fail-fast error handling.

    Args:
        processor: The processor to wrap

    Returns:
        A wrapped processor function with simplified error handling
    """

    def wrapped_processor(
        logger_instance: Any,
        method_name: str,
        event_dict: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Wrapped processor with fail-fast error handling."""
        return simple_processor_execution(
            processor, logger_instance, method_name, event_dict
        )

    return wrapped_processor


def log_processor_error_with_context(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    level: int = logging.WARNING,
) -> None:
    """Log processor errors with full context.

    Args:
        error: The exception that occurred
        context: Additional context information
        level: Logging level to use (default: WARNING for processor failures)
    """
    # Use the established error logging pattern
    log_error_with_context(error, context, level)


def validate_processor_configuration(
    processor: Processor, processor_name: Optional[str] = None
) -> None:
    """Validate processor configuration with comprehensive error handling.

    Args:
        processor: The processor to validate
        processor_name: Optional name for error context

    Raises:
        ProcessorConfigurationError: If configuration is invalid
    """
    if processor_name is None:
        processor_name = processor.__class__.__name__

    try:
        processor.validate_config()
    except Exception as e:
        raise handle_processor_error(
            e, processor_name, operation="configuration"
        ) from e


async def safe_processor_lifecycle_operation(
    processor: Processor,
    operation: str,
    processor_name: Optional[str] = None,
) -> bool:
    """Safely execute processor lifecycle operations (start/stop).

    Args:
        processor: The processor instance
        operation: The operation to perform ("start" or "stop")
        processor_name: Optional name for error context

    Returns:
        True if operation succeeded, False if it failed

    Raises:
        ProcessorExecutionError: If the operation fails critically
    """
    if processor_name is None:
        processor_name = processor.__class__.__name__

    try:
        if operation == "start":
            await processor.start()
        elif operation == "stop":
            await processor.stop()
        else:
            raise ValueError(f"Invalid operation: {operation}")

        return True
    except Exception as e:
        handle_processor_error(e, processor_name, operation=operation)

        # For lifecycle operations, we typically want to log but not
        # prevent the system from continuing
        logger.error(f"Processor {operation} failed for {processor_name}: {e}")

        # Return False to indicate failure but allow graceful handling
        return False
