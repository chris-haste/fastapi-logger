"""Tests for resource snapshot enricher integration in pipeline."""

from unittest.mock import Mock, patch

from fapilog.pipeline import build_processor_chain
from fapilog.settings import LoggingSettings


def test_resource_enricher_included_when_enabled():
    """Test that resource enricher is included in pipeline when enabled."""
    settings = LoggingSettings(enable_resource_metrics=True)

    with patch("fapilog.enrichers._get_process") as mock_get_process:
        mock_process = Mock()
        mock_process.memory_info.return_value.rss = 1024 * 1024 * 50  # 50MB
        mock_process.cpu_percent.return_value = 25.5
        mock_get_process.return_value = mock_process

        processors = build_processor_chain(settings)

        # Find the resource snapshot enricher in the chain
        from fapilog.enrichers import resource_snapshot_enricher

        assert resource_snapshot_enricher in processors


def test_resource_enricher_excluded_when_disabled():
    """Test that resource enricher is excluded from pipeline when disabled."""
    settings = LoggingSettings(enable_resource_metrics=False)

    processors = build_processor_chain(settings)

    # Verify the resource snapshot enricher is not in the chain
    from fapilog.enrichers import resource_snapshot_enricher

    assert resource_snapshot_enricher not in processors


def test_resource_enricher_position_in_chain():
    """Test that resource enricher is positioned correctly in the pipeline."""
    settings = LoggingSettings(enable_resource_metrics=True)

    with patch("fapilog.enrichers._get_process") as mock_get_process:
        mock_process = Mock()
        mock_process.memory_info.return_value.rss = 1024 * 1024 * 50
        mock_process.cpu_percent.return_value = 25.5
        mock_get_process.return_value = mock_process

        processors = build_processor_chain(settings)

        # Find the resource snapshot enricher in the chain
        from fapilog.enrichers import (
            request_response_enricher,
            resource_snapshot_enricher,
        )

        # Resource enricher should come after request_response_enricher
        request_response_index = processors.index(request_response_enricher)
        resource_index = processors.index(resource_snapshot_enricher)

        assert resource_index > request_response_index


def test_pipeline_with_resource_metrics():
    """Test that pipeline works correctly with resource metrics enabled."""
    settings = LoggingSettings(
        enable_resource_metrics=True,
        level="INFO",
        sinks=["stdout"],
        queue_enabled=False,
    )

    with patch("fapilog.enrichers._get_process") as mock_get_process:
        mock_process = Mock()
        mock_process.memory_info.return_value.rss = 1024 * 1024 * 75  # 75MB
        mock_process.cpu_percent.return_value = 45.5
        mock_get_process.return_value = mock_process

        processors = build_processor_chain(settings)

        # Test that we can create a logger with the processors
        import structlog

        # Create a test logger with our processors
        structlog.configure(processors=processors)
        logger = structlog.get_logger()

        # Test that the logger works
        logger.info("test message")

        # The logger should work without errors
        assert True  # If we get here, no exceptions were raised
