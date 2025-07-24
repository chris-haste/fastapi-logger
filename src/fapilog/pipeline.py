"""Default processor pipeline for fapilog structured logging."""

import random
import re
from typing import Any, Dict, List, Optional

import structlog

from ._internal.pii_patterns import DEFAULT_PII_PATTERNS, auto_redact_pii_processor
from .enrichers import (
    body_size_enricher,
    host_process_enricher,
    request_response_enricher,
    resource_snapshot_enricher,
    user_context_enricher,
)
from .redactors import _should_redact_at_level, field_redactor
from .settings import LoggingSettings


def _redact_processor(patterns: List[str], redact_level: str = "INFO") -> Any:
    """Create a redaction processor that masks values matching patterns.

    Args:
        patterns: List of regex patterns to match for redaction
        redact_level: Minimum log level for redaction to be applied

    Returns:
        A processor function that redacts matching values
    """
    if not patterns:
        return lambda logger, method_name, event_dict: event_dict

    compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]

    def redact_processor(
        logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Redact sensitive information from log entries."""
        # Check if redaction should be applied based on log level
        event_level = event_dict.get("level", "INFO")
        if not _should_redact_at_level(event_level, redact_level):
            return event_dict

        redacted_dict = event_dict.copy()

        for key, value in event_dict.items():
            if isinstance(value, str):
                for pattern in compiled_patterns:
                    if pattern.search(key) or pattern.search(value):
                        redacted_dict[key] = "[REDACTED]"
                        break
            elif isinstance(value, dict):
                # Recursively redact nested dictionaries
                redacted_dict[key] = redact_processor(logger, method_name, value)

        return redacted_dict

    return redact_processor


def _sampling_processor(rate: float) -> Any:
    """Create a sampling processor that drops events probabilistically.

    Args:
        rate: Sampling rate between 0.0 and 1.0

    Returns:
        A processor function that returns None for dropped events
    """
    if rate >= 1.0:
        return lambda logger, method_name, event_dict: event_dict

    def sampling_processor(
        logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Sample log events based on the configured rate."""
        if random.random() >= rate:
            return None  # Drop this event
        return event_dict

    return sampling_processor


def _filter_none_processor(
    logger: Any, method_name: str, event_dict: Optional[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    if event_dict is None:
        return None
    return event_dict


def build_processor_chain(
    settings: LoggingSettings, pretty: bool = False, enricher_lifecycle=None
) -> List[Any]:
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

    # 7. Custom redaction processor (regex patterns)
    processors.append(
        _redact_processor(settings.redact_patterns, settings.redact_level)
    )

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

    # 13. Enhanced enricher processor (advanced registry)
    processors.append(create_enricher_processor(settings, enricher_lifecycle))

    # 14. Sampling processor (must be just before renderer)
    sampling = _sampling_processor(settings.sampling_rate)

    # 15. Filter None processor (skips rendering if None)
    processors.append(sampling)
    processors.append(_filter_none_processor)

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


def create_enricher_processor(settings: LoggingSettings, enricher_lifecycle=None):
    """Create processor that runs enrichers in dependency order."""

    def enricher_processor(logger, method_name, event_dict):
        """Enhanced enricher processor with dependency resolution."""
        import os

        from ._internal.async_enricher import AsyncEnricher
        from ._internal.enricher_conditions import EnricherConditions
        from ._internal.enricher_registry import EnricherRegistry

        # Initialize enrichers from URIs if configured
        if hasattr(settings, "enrichers") and settings.enrichers:
            for enricher_config in settings.enrichers:
                if isinstance(enricher_config, str) and "://" in enricher_config:
                    try:
                        # Create enricher from URI if not already instantiated
                        # Register it if needed (URI scheme as name)
                        from urllib.parse import urlparse

                        scheme = urlparse(enricher_config).scheme
                        if not EnricherRegistry.get_metadata(scheme):
                            # Register the instance wrapper
                            class URIEnricherWrapper:
                                def __init__(self, instance):
                                    self.instance = instance

                                def __call__(self, logger, method_name, event_dict):
                                    return self.instance(
                                        logger, method_name, event_dict
                                    )

                            EnricherRegistry.register(
                                name=scheme,
                                enricher_class=URIEnricherWrapper,
                                description=f"URI enricher: {enricher_config}",
                                priority=150,  # Between built-in and custom
                            )
                    except Exception as e:
                        # Log error but don't break the pipeline
                        import logging

                        logger_err = logging.getLogger(__name__)
                        logger_err.debug(
                            f"Failed to initialize enricher {enricher_config}: {e}"
                        )

        # Get enabled enrichers based on conditions
        context = {
            "environment": os.getenv("ENVIRONMENT", "development"),
            "level": event_dict.get("level", "INFO"),
            "method": method_name,
            **event_dict,
        }

        # Apply global enricher conditions from settings
        if hasattr(settings, "enricher_conditions") and settings.enricher_conditions:
            context.update(settings.enricher_conditions)

        # Resolve enricher order and dependencies
        enabled_enrichers = []
        for name, metadata in EnricherRegistry.list_enrichers().items():
            if EnricherConditions.should_enable_enricher(metadata, context):
                enabled_enrichers.append(name)

        if not enabled_enrichers:
            return event_dict

        # Sort by priority and dependencies
        try:
            ordered_enrichers = EnricherRegistry.resolve_dependencies(enabled_enrichers)
        except Exception as e:
            # Log dependency resolution error but continue
            import logging

            logger_err = logging.getLogger(__name__)
            logger_err.debug(f"Enricher dependency resolution failed: {e}")
            # Fall back to priority-based ordering
            ordered_enrichers = sorted(
                enabled_enrichers,
                key=lambda x: EnricherRegistry.get_metadata(x).priority,
            )

        # Apply enrichers in order
        result = event_dict
        for enricher_name in ordered_enrichers:
            metadata = EnricherRegistry.get_metadata(enricher_name)
            if not metadata:
                continue

            try:
                # Get or create enricher instance
                enricher = EnricherRegistry.get_instance(enricher_name)

                # Register async enrichers with lifecycle manager if provided
                if (
                    enricher_lifecycle
                    and metadata.async_capable
                    and hasattr(enricher, "enrichers")
                ):
                    # enricher is an AsyncEnricherProcessor wrapper
                    for async_enricher in enricher.enrichers:
                        if isinstance(async_enricher, AsyncEnricher):
                            enricher_lifecycle.register_enricher(async_enricher)

                result = enricher(logger, method_name, result)
            except Exception as e:
                # Log enricher failure but continue pipeline
                import logging

                enricher_logger = logging.getLogger(__name__)
                enricher_logger.debug(
                    f"Enhanced enricher {enricher_name} failed: {e}", exc_info=True
                )

        return result

    return enricher_processor
