"""Default processor pipeline for fapilog structured logging."""

from typing import Any, List

import structlog

from ._internal.pii_patterns import DEFAULT_PII_PATTERNS, auto_redact_pii_processor
from ._internal.processor import Processor
from ._internal.processors import (
    FilterNoneProcessor,
    RedactionProcessor,
    SamplingProcessor,
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

    # 7. Custom redaction processor (regex patterns) - class-based
    redaction_processor = RedactionProcessor(
        patterns=settings.redact_patterns, redact_level=settings.redact_level
    )
    processors.append(_processor_to_function(redaction_processor))

    # 8. Field redaction processor (field names)
    processors.append(
        field_redactor(
            settings.redact_fields, settings.redact_replacement, settings.redact_level
        )
    )

    # 9. PII auto-detection processor (after manual field redaction)
    if settings.enable_auto_redact_pii:
        # Combine default patterns with custom patterns
        all_pii_patterns = DEFAULT_PII_PATTERNS + settings.custom_pii_patterns
        processors.append(
            auto_redact_pii_processor(
                all_pii_patterns, settings.redact_replacement, settings.redact_level
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

    # 14. Sampling processor (must be just before renderer) - class-based
    sampling_processor = SamplingProcessor(rate=settings.sampling_rate)
    processors.append(_processor_to_function(sampling_processor))

    # 15. Filter None processor (skips rendering if None) - class-based
    filter_processor = FilterNoneProcessor()
    processors.append(_processor_to_function(filter_processor))

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
