"""Error handling utilities for processors in fapilog."""

import logging
from typing import Any, Callable, Dict, Optional

from ..exceptions import (
    ProcessorConfigurationError,
    ProcessorError,
    ProcessorExecutionError,
    ProcessorRegistrationError,
)
from .error_handling import log_error_with_context
from .processor import Processor

logger = logging.getLogger(__name__)


def handle_processor_error(
    error: Exception,
    processor_name: str,
    context: Optional[Dict[str, Any]] = None,
    operation: str = "execution",
) -> ProcessorError:
    """Handle processor errors with context.

    Args:
        error: The original exception
        processor_name: Name of the processor that failed
        context: Additional context information
        operation: Operation that failed

    Returns:
        ProcessorError with proper context
    """
    error_context = {
        "operation": operation,
        "original_error": str(error),
    }

    if context:
        # Filter out sensitive information from context
        safe_context = {
            k: v
            for k, v in context.items()
            if k not in ["password", "token", "secret", "key", "api_key", "credential"]
        }
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


def safe_processor_execution(
    processor: Processor,
    logger_instance: Any,
    method_name: str,
    event_dict: Dict[str, Any],
    fallback_strategy: str = "pass_through",
) -> Optional[Dict[str, Any]]:
    """Execute processor with comprehensive error handling.

    Args:
        processor: The processor instance to execute
        logger_instance: Logger instance for the event
        method_name: Logging method name
        event_dict: Event dictionary to process
        fallback_strategy: Strategy for handling failures
            - "pass_through": Return original event_dict on failure
            - "drop": Return None to drop the event
            - "fallback_value": Return a safe default event structure

    Returns:
        Processed event dict, original event dict, None, or fallback structure
    """
    processor_name = processor.__class__.__name__

    try:
        return processor.process(logger_instance, method_name, event_dict)
    except Exception as e:
        # Create context about the event being processed
        event_context = {
            "event_keys": list(event_dict.keys()) if event_dict else [],
            "method_name": method_name,
            "fallback_strategy": fallback_strategy,
        }

        # Handle the error with context
        handle_processor_error(e, processor_name, event_context, "process")

        # Apply fallback strategy
        if fallback_strategy == "pass_through":
            logger.warning(
                f"Processor {processor_name} failed, passing through original event"
            )
            return event_dict
        elif fallback_strategy == "drop":
            logger.warning(f"Processor {processor_name} failed, dropping event")
            return None
        elif fallback_strategy == "fallback_value":
            logger.warning(
                f"Processor {processor_name} failed, using fallback event structure"
            )
            return {
                "level": event_dict.get("level", "ERROR"),
                "message": "Processor execution failed",
                "processor_error": True,
                "original_message": event_dict.get("message", "unknown"),
            }
        else:
            # Invalid fallback strategy, default to pass_through
            logger.error(
                f"Invalid fallback strategy '{fallback_strategy}', using pass_through"
            )
            return event_dict


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


def create_safe_processor_wrapper(
    processor: Processor,
    fallback_strategy: str = "pass_through",
    retry_count: int = 0,
) -> Callable[[Any, str, Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Create a safe wrapper for processor execution.

    Args:
        processor: The processor to wrap
        fallback_strategy: Strategy for handling failures
        retry_count: Number of retries on failure (0 = no retries)

    Returns:
        A wrapped processor function with error handling
    """
    processor_name = processor.__class__.__name__

    def wrapped_processor(
        logger_instance: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Wrapped processor with error handling and retry logic."""
        attempts = retry_count + 1

        for attempt in range(attempts):
            try:
                return processor.process(logger_instance, method_name, event_dict)
            except Exception as e:
                is_last_attempt = attempt == attempts - 1

                # Create context for this attempt
                context = {
                    "attempt": attempt + 1,
                    "max_attempts": attempts,
                    "is_last_attempt": is_last_attempt,
                    "event_keys": list(event_dict.keys()) if event_dict else [],
                    "method_name": method_name,
                }

                if is_last_attempt:
                    # Final failure, apply fallback strategy
                    handle_processor_error(e, processor_name, context, "process")
                    return _apply_fallback_strategy(
                        event_dict, fallback_strategy, processor_name
                    )
                else:
                    # Log the retry attempt
                    logger.debug(
                        f"Processor {processor_name} failed on attempt {attempt + 1}, "
                        f"retrying..."
                    )

        return None  # Should never reach here

    return wrapped_processor


def _apply_fallback_strategy(
    event_dict: Dict[str, Any], strategy: str, processor_name: str
) -> Optional[Dict[str, Any]]:
    """Apply the specified fallback strategy.

    Args:
        event_dict: Original event dictionary
        strategy: Fallback strategy to apply
        processor_name: Name of the failed processor

    Returns:
        Result based on fallback strategy
    """
    if strategy == "pass_through":
        logger.warning(
            f"Processor {processor_name} failed, passing through original event"
        )
        return event_dict
    elif strategy == "drop":
        logger.warning(f"Processor {processor_name} failed, dropping event")
        return None
    elif strategy == "fallback_value":
        logger.warning(
            f"Processor {processor_name} failed, using fallback event structure"
        )
        return {
            "level": event_dict.get("level", "ERROR"),
            "message": "Processor execution failed",
            "processor_error": True,
            "processor_name": processor_name,
            "original_message": event_dict.get("message", "unknown"),
        }
    else:
        # Invalid strategy, default to pass_through
        logger.error(f"Invalid fallback strategy '{strategy}', using pass_through")
        return event_dict


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
