"""Concrete processor implementations for fapilog structured logging."""

import random
import re
from typing import Any, Dict, List, Optional

from ..redactors import _should_redact_at_level
from .processor import Processor
from .processor_registry import ProcessorRegistry


class RedactionProcessor(Processor):
    """Processor that redacts values matching regex patterns."""

    def __init__(
        self,
        patterns: Optional[List[str]] = None,
        redact_level: str = "INFO",
        **config: Any,
    ) -> None:
        """Initialize redaction processor.

        Args:
            patterns: List of regex patterns to match for redaction
            redact_level: Minimum log level for redaction to be applied
            **config: Additional configuration parameters
        """
        self.patterns = patterns or []
        self.redact_level = redact_level
        self.compiled_patterns: List[re.Pattern[str]] = []
        super().__init__(patterns=patterns, redact_level=redact_level, **config)

    async def _start_impl(self) -> None:
        """Initialize compiled regex patterns."""
        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.patterns
        ]

    def validate_config(self) -> None:
        """Validate configuration parameters."""
        if not isinstance(self.patterns, list):
            raise ValueError("patterns must be a list of strings")

        for pattern in self.patterns:
            if not isinstance(pattern, str):
                raise ValueError("All patterns must be strings")
            try:
                re.compile(pattern)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern '{pattern}': {e}") from e

        if not isinstance(self.redact_level, str):
            raise ValueError("redact_level must be a string")

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Redact sensitive information from log entries."""
        # Check if redaction should be applied based on log level
        event_level = event_dict.get("level", "INFO")
        if not _should_redact_at_level(event_level, self.redact_level):
            return event_dict

        if not self.compiled_patterns:
            return event_dict

        return self._redact_recursive(event_dict)

    def _redact_recursive(self, data: Any) -> Any:
        """Recursively redact values in nested structures."""
        if isinstance(data, dict):
            redacted_dict = data.copy()
            for key, value in data.items():
                if isinstance(value, str):
                    for pattern in self.compiled_patterns:
                        if pattern.search(key) or pattern.search(value):
                            redacted_dict[key] = "[REDACTED]"
                            break
                elif isinstance(value, dict):
                    redacted_dict[key] = self._redact_recursive(value)
            return redacted_dict
        return data


class SamplingProcessor(Processor):
    """Processor that drops events probabilistically for sampling."""

    def __init__(self, rate: float = 1.0, **config: Any) -> None:
        """Initialize sampling processor.

        Args:
            rate: Sampling rate between 0.0 and 1.0
            **config: Additional configuration parameters
        """
        self.rate = rate
        super().__init__(rate=rate, **config)

    def validate_config(self) -> None:
        """Validate configuration parameters."""
        if not isinstance(self.rate, (int, float)):
            raise ValueError("rate must be a number")

        if not 0.0 <= self.rate <= 1.0:
            raise ValueError("rate must be between 0.0 and 1.0")

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Sample log events based on the configured rate."""
        if self.rate >= 1.0:
            return event_dict

        if random.random() >= self.rate:
            return None  # Drop this event
        return event_dict


class FilterNoneProcessor(Processor):
    """Processor that filters out None events."""

    def __init__(self, **config: Any) -> None:
        """Initialize filter processor.

        Args:
            **config: Configuration parameters (not used by this processor)
        """
        super().__init__(**config)

    def process(
        self, logger: Any, method_name: str, event_dict: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Filter out None events."""
        if event_dict is None:
            return None
        return event_dict


# Register built-in processors in the ProcessorRegistry
ProcessorRegistry.register("redaction", RedactionProcessor)
ProcessorRegistry.register("sampling", SamplingProcessor)
ProcessorRegistry.register("filter_none", FilterNoneProcessor)
