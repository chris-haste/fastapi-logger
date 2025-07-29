"""Default processor pipeline for fapilog structured logging."""

from typing import Any, List

import structlog

from fapilog.enrichers import (
    body_size_enricher,
    host_process_enricher_sync,
    request_response_enricher,
    resource_snapshot_enricher_sync,
    run_registered_enrichers,
    user_context_enricher,
)

from ._internal.pii_patterns import DEFAULT_PII_PATTERNS, auto_redact_pii_processor
from ._internal.processor import Processor
from ._internal.processor_error_handling import (
    create_simple_processor_wrapper,
)
from ._internal.processors import (
    DeduplicationProcessor,
    FilterNoneProcessor,
    RedactionProcessor,
    SamplingProcessor,
    ThrottleProcessor,
)
from .redactors import field_redactor
from .settings import LoggingSettings


def _create_safe_processor(
    processor: Processor,
) -> Any:
    """Create a simple processor wrapper with fail-fast error handling.

    Args:
        processor: The processor instance to wrap

    Returns:
        A wrapped processor function with simplified error handling that can be used in structlog chain
    """
    return create_simple_processor_wrapper(processor)


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
    processors.append(host_process_enricher_sync)

    # 7. Custom redaction processor (regex patterns) - class-based with error handling
    redaction_processor = RedactionProcessor(
        patterns=settings.redact_patterns, redact_level=settings.redact_level
    )
    processors.append(_create_safe_processor(redaction_processor))

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
        processors.append(resource_snapshot_enricher_sync)

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
        processors.append(_create_safe_processor(throttle_processor))

    # 15. Deduplication processor - class-based with error handling (if enabled)
    if settings.enable_deduplication:
        dedupe_processor = DeduplicationProcessor(
            window_seconds=settings.dedupe_window_seconds,
            dedupe_fields=settings.dedupe_fields,
            max_cache_size=settings.dedupe_max_cache_size,
            hash_algorithm=settings.dedupe_hash_algorithm,
        )
        processors.append(_create_safe_processor(dedupe_processor))

    # 16. Sampling processor - class-based with error handling
    sampling_processor = SamplingProcessor(rate=settings.sampling_rate)
    processors.append(_create_safe_processor(sampling_processor))

    # 17. Filter None processor - class-based with error handling
    filter_processor = FilterNoneProcessor()
    processors.append(_create_safe_processor(filter_processor))

    # 16. Queue sink or renderer
    if settings.queue_enabled:
        # Import here to avoid circular imports
        from ._internal.queue_integration import queue_sink

        processors.append(queue_sink)
    else:
        # Renderer (JSON or Console) - always last
        if pretty:
            renderer = structlog.dev.ConsoleRenderer(colors=True)
        else:
            renderer = structlog.processors.JSONRenderer()
        processors.append(renderer)

    return processors
