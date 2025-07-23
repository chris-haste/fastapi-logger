"""Final boost for stdout.py coverage - targeting lines 72-74."""

from unittest.mock import patch

import pytest

from fapilog.sinks.stdout import StdoutSink


class TestStdoutFinalBoost:
    """Tests to cover the remaining lines in stdout.py."""

    @pytest.mark.asyncio
    async def test_stdout_write_exception_handling(self):
        """Test exception handling when stdout writing fails.

        This covers lines 72-74 in stdout.py where an exception occurs
        during stdout writing.
        """
        sink = StdoutSink(mode="json")

        # Mock print to raise an exception
        with patch("builtins.print", side_effect=OSError("Write failed")):
            # This should trigger the exception path in write method
            with pytest.raises(OSError, match="Write failed"):
                await sink.write({"level": "info", "message": "test"})
