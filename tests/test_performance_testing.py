"""Tests for the performance testing framework."""

import asyncio
from unittest.mock import Mock, patch

import pytest

from fapilog.sinks import Sink
from fapilog.testing.performance import SinkPerformanceTester


class MockSink(Sink):
    """Mock sink for performance testing."""

    def __init__(self, delay: float = 0.0, should_fail: bool = False):
        super().__init__()
        self.delay = delay
        self.should_fail = should_fail
        self.events = []
        self.write_calls = 0

    async def write(self, event_dict):
        """Write event with optional delay and failure."""
        self.write_calls += 1
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        if self.should_fail:
            raise Exception("Mock sink failure")
        self.events.append(event_dict)

    async def write_batch(self, events):
        """Write a batch of events."""
        for event in events:
            await self.write(event)


class TestSinkPerformanceTester:
    """Test the SinkPerformanceTester class."""

    @pytest.fixture
    def tester(self):
        """Create a performance tester instance."""
        return SinkPerformanceTester()

    @pytest.fixture
    def mock_sink(self):
        """Create a mock sink."""
        return MockSink()

    def test_init(self, tester):
        """Test performance tester initialization."""
        assert isinstance(tester.metrics, dict)
        assert len(tester.metrics) == 0
        assert isinstance(tester._test_events, list)
        assert len(tester._test_events) == 0

    def test_create_test_event(self, tester):
        """Test test event creation."""
        event = tester._create_test_event(42)

        assert event["level"] == "info"
        assert event["message"] == "Performance test event 42"
        assert "timestamp" in event
        assert event["test_index"] == 42
        assert event["test_data"] == "x" * 100

    @pytest.mark.asyncio
    async def test_throughput_basic(self, tester, mock_sink):
        """Test basic throughput measurement."""
        num_events = 10

        result = await tester.test_throughput(mock_sink, num_events)

        assert isinstance(result, float)
        assert result > 0
        assert mock_sink.write_calls == num_events
        assert len(mock_sink.events) == num_events

        # Check metrics were stored
        assert "throughput" in tester.metrics
        metrics = tester.metrics["throughput"]
        assert metrics["events_per_second"] == result
        assert metrics["total_events"] == num_events
        assert metrics["test_type"] == "sequential"

    @pytest.mark.asyncio
    async def test_throughput_with_delay(self, tester):
        """Test throughput with delayed sink."""
        slow_sink = MockSink(delay=0.01)  # 10ms delay

        result = await tester.test_throughput(slow_sink, 5)

        assert result > 0
        assert result < 1000  # Should be much less than 1000 eps due to delay

    @pytest.mark.asyncio
    async def test_concurrent_throughput_basic(self, tester, mock_sink):
        """Test concurrent throughput measurement."""
        num_events = 20
        concurrency = 4

        result = await tester.test_concurrent_throughput(
            mock_sink, num_events, concurrency
        )

        assert isinstance(result, float)
        assert result > 0
        assert mock_sink.write_calls == num_events

        # Check metrics were stored
        assert "concurrent_throughput" in tester.metrics
        metrics = tester.metrics["concurrent_throughput"]
        assert metrics["events_per_second"] == result
        assert metrics["total_events"] == num_events
        assert metrics["concurrency"] == concurrency
        assert metrics["test_type"] == "concurrent"

    @pytest.mark.asyncio
    async def test_concurrent_throughput_uneven_distribution(self, tester, mock_sink):
        """Test concurrent throughput with uneven event distribution."""
        num_events = 17  # Not evenly divisible by concurrency
        concurrency = 5

        result = await tester.test_concurrent_throughput(
            mock_sink, num_events, concurrency
        )

        assert result > 0
        assert mock_sink.write_calls == num_events

    @pytest.mark.asyncio
    async def test_latency_basic(self, tester, mock_sink):
        """Test basic latency measurement."""
        num_samples = 20

        result = await tester.test_latency(mock_sink, num_samples)

        assert isinstance(result, dict)
        assert "mean_ms" in result
        assert "median_ms" in result
        assert "min_ms" in result
        assert "max_ms" in result
        assert "std_dev_ms" in result

        # All latency values should be reasonable (< 1 second)
        assert result["mean_ms"] < 1000
        assert result["median_ms"] < 1000
        assert result["min_ms"] >= 0
        assert result["max_ms"] >= result["min_ms"]

        # Check metrics were stored
        assert "latency" in tester.metrics
        assert tester.metrics["latency"]["num_samples"] == num_samples

    @pytest.mark.asyncio
    async def test_latency_with_percentiles(self, tester, mock_sink):
        """Test latency measurement with enough samples for percentiles."""
        num_samples = 50  # Enough for percentiles

        result = await tester.test_latency(mock_sink, num_samples)

        # Should include percentiles
        assert "p50_ms" in result
        assert "p90_ms" in result
        assert "p95_ms" in result
        assert "p99_ms" in result

        # Percentiles should be in order
        assert result["p50_ms"] <= result["p90_ms"]
        assert result["p90_ms"] <= result["p95_ms"]
        assert result["p95_ms"] <= result["p99_ms"]

    @pytest.mark.asyncio
    async def test_latency_insufficient_samples(self, tester, mock_sink):
        """Test latency measurement with too few samples for percentiles."""
        num_samples = 5  # Not enough for percentiles

        result = await tester.test_latency(mock_sink, num_samples)

        # Should not include percentiles
        assert "p50_ms" not in result
        assert "p90_ms" not in result
        assert "p95_ms" not in result
        assert "p99_ms" not in result

    @pytest.mark.asyncio
    async def test_latency_single_sample(self, tester, mock_sink):
        """Test latency with single sample (edge case for std dev)."""
        result = await tester.test_latency(mock_sink, 1)

        assert result["std_dev_ms"] == 0  # Should be 0 for single sample

    @pytest.mark.asyncio
    async def test_memory_usage_with_psutil(self, tester, mock_sink):
        """Test memory usage measurement when psutil is available."""
        with patch("psutil.Process") as mock_process_class:
            mock_process = Mock()
            mock_process.memory_info.return_value.rss = 1000000  # 1MB
            mock_process_class.return_value = mock_process

            result = await tester.test_memory_usage(mock_sink, 10)

            assert isinstance(result, dict)
            assert "initial_memory_bytes" in result
            assert "final_memory_bytes" in result
            assert "memory_delta_bytes" in result
            assert "memory_per_event_bytes" in result
            assert "num_events" in result
            assert result["num_events"] == 10

    @pytest.mark.asyncio
    async def test_memory_usage_without_psutil(self, tester, mock_sink):
        """Test memory usage measurement when psutil is not available."""
        # Patch the import at the module level
        import sys

        original_modules = sys.modules.copy()

        # Remove psutil if it exists
        if "psutil" in sys.modules:
            del sys.modules["psutil"]

        # Mock the import to raise ImportError
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "psutil":
                raise ImportError("No module named 'psutil'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", mock_import):
            # Force reimport of the performance module to trigger ImportError
            import importlib

            import fapilog.testing.performance

            importlib.reload(fapilog.testing.performance)

            result = await tester.test_memory_usage(mock_sink, 10)

            assert "error" in result
            assert result["error"] == "psutil not available for memory testing"
            assert result["initial_memory_bytes"] == 0
            assert result["final_memory_bytes"] == 0
            assert result["memory_delta_bytes"] == 0

        # Restore original modules
        sys.modules.update(original_modules)

    @pytest.mark.asyncio
    async def test_batch_performance_default_sizes(self, tester, mock_sink):
        """Test batch performance with default batch sizes."""
        result = await tester.test_batch_performance(mock_sink)

        assert isinstance(result, dict)
        default_sizes = [1, 5, 10, 20, 50, 100]

        for size in default_sizes:
            assert size in result
            metrics = result[size]
            assert "throughput_eps" in metrics
            assert "duration_seconds" in metrics
            assert "total_events" in metrics
            assert "num_batches" in metrics
            assert metrics["total_events"] == size * 100  # default events_per_batch

    @pytest.mark.asyncio
    async def test_batch_performance_custom_sizes(self, tester, mock_sink):
        """Test batch performance with custom batch sizes."""
        custom_sizes = [2, 8]
        events_per_batch = 5

        result = await tester.test_batch_performance(
            mock_sink, custom_sizes, events_per_batch
        )

        assert len(result) == 2
        for size in custom_sizes:
            assert size in result
            assert result[size]["total_events"] == size * events_per_batch

    @pytest.mark.asyncio
    async def test_batch_performance_with_batch_sink(self, tester):
        """Test batch performance with a sink that supports batch operations."""
        batch_sink = MockSink()

        result = await tester.test_batch_performance(batch_sink, [2], 3)

        assert 2 in result
        # Should have called write 6 times (2 events * 3 batches)
        assert batch_sink.write_calls == 6

    @pytest.mark.asyncio
    async def test_comprehensive_test_default_config(self, tester, mock_sink):
        """Test comprehensive test with default configuration."""
        with patch("builtins.print"):  # Suppress print statements
            result = await tester.run_comprehensive_test(mock_sink)

        assert isinstance(result, dict)
        assert "test_duration_seconds" in result
        assert "sink_type" in result
        assert "test_config" in result
        assert "throughput" in result
        assert "latency" in result
        assert "memory" in result
        assert "batch_performance" in result
        assert "summary" in result

        # Check throughput section
        throughput = result["throughput"]
        assert "sequential_eps" in throughput
        assert "concurrent_eps" in throughput

        # Check summary section
        summary = result["summary"]
        assert "best_sequential_throughput" in summary
        assert "best_concurrent_throughput" in summary
        assert "average_latency_ms" in summary
        assert "p95_latency_ms" in summary
        assert "memory_delta_mb" in summary

    @pytest.mark.asyncio
    async def test_comprehensive_test_custom_config(self, tester, mock_sink):
        """Test comprehensive test with custom configuration."""
        custom_config = {
            "throughput_events": 50,
            "concurrent_events": 40,
            "concurrent_workers": 4,
            "latency_samples": 20,
            "memory_events": 30,
            "batch_sizes": [1, 5],
            "batch_events_per_size": 10,
        }

        with patch("builtins.print"):  # Suppress print statements
            result = await tester.run_comprehensive_test(mock_sink, custom_config)

        assert result["test_config"] == custom_config
        # Verify the sink received the expected number of events
        # Should be: 50 + 40 + 20 + 30 + (1*10 + 5*10) = 200 total calls
        assert mock_sink.write_calls == 200

    def test_get_metrics(self, tester):
        """Test getting metrics."""
        # Add some test metrics
        tester.metrics["test"] = {"value": 42}

        result = tester.get_metrics()

        assert result == {"test": {"value": 42}}
        # Should be a copy, not the original
        assert result is not tester.metrics

    def test_clear_metrics(self, tester):
        """Test clearing metrics."""
        tester.metrics["test"] = {"value": 42}

        tester.clear_metrics()

        assert len(tester.metrics) == 0

    def test_print_summary_no_metrics(self, tester):
        """Test printing summary with no metrics."""
        with patch("builtins.print") as mock_print:
            tester.print_summary()

            mock_print.assert_called_with("No performance metrics available.")

    def test_print_summary_with_metrics(self, tester):
        """Test printing summary with various metrics."""
        tester.metrics = {
            "throughput": {
                "events_per_second": 1000.5,
                "duration_seconds": 2.345,
            },
            "concurrent_throughput": {
                "events_per_second": 1500.7,
                "concurrency": 5,
                "duration_seconds": 1.234,
            },
            "latency": {
                "mean_ms": 10.123,
                "median_ms": 9.876,
                "p95_ms": 15.456,
            },
            "memory": {
                "memory_delta_bytes": 2048000,  # 2MB
                "memory_per_event_bytes": 1024,
            },
        }

        with patch("builtins.print") as mock_print:
            tester.print_summary()

            # Check that all sections were printed
            calls = [call[0][0] for call in mock_print.call_args_list]
            assert any("Sequential Throughput" in call for call in calls)
            assert any("Concurrent Throughput" in call for call in calls)
            assert any("Latency Statistics" in call for call in calls)
            assert any("Memory Usage" in call for call in calls)
            assert any("Events/sec: 1000.50" in call for call in calls)
            # Check for memory output (format may vary)
            assert any("MB" in call for call in calls)

    def test_print_summary_with_memory_error(self, tester):
        """Test printing summary with memory error."""
        tester.metrics = {"memory": {"error": "psutil not available"}}

        with patch("builtins.print") as mock_print:
            tester.print_summary()

            calls = [call[0][0] for call in mock_print.call_args_list]
            # Should not print memory section when there's an error
            assert not any("Memory Usage" in call for call in calls)
