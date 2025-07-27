"""Final boost for performance.py coverage - targeting lines 260-261."""

from typing import Any, Dict

import pytest

from fapilog.sinks import Sink
from fapilog.testing.performance import SinkPerformanceTester


class SimpleSink(Sink):
    """Simple sink without write_batch method for testing."""

    def __init__(self):
        super().__init__()
        self.events = []

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Write single event."""
        self.events.append(event_dict)
        # Note: This sink intentionally does NOT have write_batch method


class TestPerformanceFinalBoost:
    """Tests to cover the remaining lines in performance.py."""

    @pytest.mark.asyncio
    async def test_batch_performance_without_write_batch_method(self):
        """Test batch performance with sink that doesn't have write_batch method.

        This should cover lines 260-261 in performance.py where events are
        written individually when sink lacks write_batch method.
        """
        tester = SinkPerformanceTester()
        sink = SimpleSink()

        # Call test_batch_performance which will hit the individual write path
        # since SimpleSink doesn't have write_batch method
        results = await tester.test_batch_performance(
            sink=sink,
            batch_sizes=[2, 4],  # Small batch sizes for quick test
            events_per_batch=2,  # Small number for quick test
        )

        # Verify results
        assert len(results) == 2
        assert 2 in results
        assert 4 in results

        # Verify events were written individually (lines 260-261)
        assert len(sink.events) > 0  # Events were written, covering the target lines
