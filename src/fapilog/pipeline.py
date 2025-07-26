"""Default processor pipeline for fapilog structured logging."""

from typing import Any, Dict, List

import structlog

from ._internal.pii_patterns import DEFAULT_PII_PATTERNS, auto_redact_pii_processor
from ._internal.processor import Processor
from ._internal.processor_error_handling import (
    create_safe_processor_wrapper,
)
from ._internal.processors import (
    FilterNoneProcessor,
    RedactionProcessor,
    SamplingProcessor,
    ThrottleProcessor,
)
from .enrichers import (
    body_size_enricher,
    host_process_enricher,
    request_response_enricher,
    resource_snapshot_enricher,
    run_registered_enrichers,
    user_context_enricher,
)
from .redactors import field_redactor
from .settings import LoggingSettings


def _processor_to_function(processor: Processor) -> Any:
    """Convert a processor instance to a function for structlog chain.

    Args:
        processor: The processor instance to convert

    Returns:
        A function that can be used in the structlog processor chain
    """

    def processor_function(logger: Any, method_name: str, event_dict: Any) -> Any:
        return processor.process(logger, method_name, event_dict)

    return processor_function


def _wrap_processor_with_error_handling(
    processor: Processor,
    fallback_strategy: str = "pass_through",
    retry_count: int = 0,
) -> Any:
    """Wrap processor with error handling and graceful degradation.

    Args:
        processor: The processor instance to wrap
        fallback_strategy: Strategy for handling failures
            - "pass_through": Return original event_dict on failure
            - "drop": Return None to drop the event
            - "fallback_value": Return a safe default event structure
        retry_count: Number of retries on failure (0 = no retries)

    Returns:
        A wrapped processor function with error handling
    """
    return create_safe_processor_wrapper(processor, fallback_strategy, retry_count)


def _handle_processor_chain_error(
    processor_name: str,
    error: Exception,
    event_dict: Dict[str, Any],
) -> Dict[str, Any]:
    """Handle errors in processor chain with fallback behavior.

    Args:
        processor_name: Name of the processor that failed
        error: The exception that occurred
        event_dict: The original event dictionary

    Returns:
        Fallback event dictionary
    """
    from ._internal.processor_error_handling import handle_processor_error

    # Handle the error with context
    handle_processor_error(
        error,
        processor_name,
        context={
            "event_keys": list(event_dict.keys()) if event_dict else [],
            "chain_position": "unknown",
        },
        operation="chain_processing",
    )

    # Return a safe fallback event
    return {
        "level": event_dict.get("level", "ERROR"),
        "message": "Processor chain error occurred",
        "processor_error": True,
        "failed_processor": processor_name,
        "original_message": event_dict.get("message", "unknown"),
    }


# Legacy function-based processors have been replaced with class-based processors
# Located in src/fapilog/_internal/processors.py


def build_processor_chain(settings: LoggingSettings, pretty: bool = False) -> List[Any]:
    """Build the default processor chain for structlog.

    Args:
        settings: LoggingSettings instance containing configuration
        pretty: Whether to use pretty console output

    Returns:
        List of processor functions in the correct order
    """
    processors = []

    # 1. Add log level
    processors.append(structlog.processors.add_log_level)

    # 2. Add timestamp (ISO-8601, UTC)
    processors.append(structlog.processors.TimeStamper(fmt="iso", utc=True))

    # 3. Format exception info
    processors.append(structlog.processors.format_exc_info)

    # 4. Stack info renderer
    processors.append(structlog.processors.StackInfoRenderer())

    # 5. Event renamer
    processors.append(structlog.processors.EventRenamer("event"))

    # 6. Host and process info enricher (early in chain)
    processors.append(host_process_enricher)

    # 7. Custom redaction processor (regex patterns) - class-based with error handling
    redaction_processor = RedactionProcessor(
        patterns=settings.redact_patterns, redact_level=settings.redact_level
    )
    processors.append(
        _wrap_processor_with_error_handling(
            redaction_processor, fallback_strategy="pass_through"
        )
    )

    # 8. Field redaction processor (field names)
    processors.append(
        field_redactor(
            settings.redact_fields,
            settings.redact_replacement,
            settings.redact_level,
        )
    )

    # 9. PII auto-detection processor (after manual field redaction)
    if settings.enable_auto_redact_pii:
        # Combine default patterns with custom patterns
        all_pii_patterns = DEFAULT_PII_PATTERNS + settings.custom_pii_patterns
        processors.append(
            auto_redact_pii_processor(
                all_pii_patterns,
                settings.redact_replacement,
                settings.redact_level,
            )
        )

    # 10. Request/Response metadata enricher
    processors.append(request_response_enricher)

    # 11. Body size enricher (after context, before final rendering)
    processors.append(body_size_enricher)

    # 12. Resource metrics enricher (if enabled)
    if settings.enable_resource_metrics:
        processors.append(resource_snapshot_enricher)

    # 12. User context enricher (if enabled)
    if settings.user_context_enabled:
        processors.append(user_context_enricher)

    # 13. Custom registered enrichers (after all built-in enrichers)
    processors.append(run_registered_enrichers)

    # 14. Throttling processor - class-based with error handling (if enabled)
    if settings.enable_throttling:
        throttle_processor = ThrottleProcessor(
            max_rate=settings.throttle_max_rate,
            window_seconds=settings.throttle_window_seconds,
            key_field=settings.throttle_key_field,
            strategy=settings.throttle_strategy,
        )
        processors.append(
            _wrap_processor_with_error_handling(
                throttle_processor, fallback_strategy="pass_through"
            )
        )

    # 15. Sampling processor - class-based with error handling
    sampling_processor = SamplingProcessor(rate=settings.sampling_rate)
    processors.append(
        _wrap_processor_with_error_handling(
            sampling_processor, fallback_strategy="pass_through"
        )
    )

    # 16. Filter None processor - class-based with error handling
    filter_processor = FilterNoneProcessor()
    processors.append(
        _wrap_processor_with_error_handling(
            filter_processor, fallback_strategy="pass_through"
        )
    )

    # 16. Queue sink or renderer
    if settings.queue_enabled:
        # Import here to avoid circular imports
        from ._internal.queue import queue_sink

        processors.append(queue_sink)
    else:
        # Renderer (JSON or Console) - always last
        if pretty:
            renderer = structlog.dev.ConsoleRenderer(colors=True)
        else:
            renderer = structlog.processors.JSONRenderer()
        processors.append(renderer)

    return processors
