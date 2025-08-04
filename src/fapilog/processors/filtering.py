"""Log filtering processors."""

from typing import Any, Dict, Optional

from .base import Processor


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
