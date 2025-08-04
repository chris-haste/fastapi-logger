"""Log sampling processor."""

from typing import Any, Dict, Optional

from .base import Processor


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
        import random

        if self.rate >= 1.0:
            return event_dict

        if random.random() >= self.rate:
            return None  # Drop this event
        return event_dict
