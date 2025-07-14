"""Default processor pipeline for fapilog structured logging."""

import random
import re
from typing import Any, Dict, List, Optional

import structlog

from .settings import LoggingSettings


def _redact_processor(patterns: List[str]) -> Any:
    """Create a redaction processor that masks values matching patterns.

    Args:
        patterns: List of regex patterns to match for redaction

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

    # 6. Custom redaction processor
    processors.append(_redact_processor(settings.redact_patterns))

    # 7. Sampling processor (must be just before renderer)
    sampling = _sampling_processor(settings.sampling_rate)

    # 8. Filter None processor (skips rendering if None)
    processors.append(sampling)
    processors.append(_filter_none_processor)

    # 9. Renderer (JSON or Console) - always last
    if pretty:
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    else:
        renderer = structlog.processors.JSONRenderer()
    processors.append(renderer)

    return processors
