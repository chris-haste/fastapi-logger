"""Integration tests for async enricher integration with main pipeline."""

import asyncio

import pytest

from fapilog._internal.async_enricher import AsyncEnricher
from fapilog._internal.enricher_lifecycle import EnricherLifecycleManager
from fapilog._internal.enricher_registry import EnricherRegistry
from fapilog.container import LoggingContainer
from fapilog.enrichers import register_enricher_advanced
from fapilog.pipeline import create_enricher_processor
from fapilog.settings import LoggingSettings


# Test async enricher classes
@register_enricher_advanced(
    name="test-async-enricher",
    description="Test async enricher for integration testing",
    priority=50,
    async_capable=True,
)
class AsyncEnricherForTesting(AsyncEnricher):
    """Test async enricher for integration testing."""

    def __init__(self, prefix="async", timeout=5.0, **kwargs):
        super().__init__("test-async-enricher")
        self.prefix = prefix
        self.timeout = timeout
        self.enrichment_count = 0
        # Accept any additional kwargs for URI factory compatibility
        for key, value in kwargs.items():
            setattr(self, key, value)

    async def _startup(self):
        """Initialize enricher."""
        await asyncio.sleep(0.01)  # Simulate startup

    async def _shutdown(self):
        """Cleanup enricher."""
        await asyncio.sleep(0.01)  # Simulate cleanup

    async def _health_check(self):
        """Health check."""
        return True

    async def enrich_async(self, logger, method_name, event_dict):
        """Add async enrichment."""
        await asyncio.sleep(0.01)  # Simulate async work
        self.enrichment_count += 1
        return {
            **event_dict,
            f"{self.prefix}_enriched": True,
            f"{self.prefix}_count": self.enrichment_count,
        }


@register_enricher_advanced(
    name="test-sync-enricher",
    description="Test sync enricher for integration testing",
    priority=100,
    async_capable=False,
)
class SyncEnricherForTesting:
    """Test sync enricher for integration testing."""

    def __init__(self, prefix="sync", **kwargs):
        self.prefix = prefix
        self.enrichment_count = 0
        # Accept any additional kwargs for URI factory compatibility
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __call__(self, logger, method_name, event_dict):
        """Add sync enrichment."""
        self.enrichment_count += 1
        return {
            **event_dict,
            f"{self.prefix}_enriched": True,
            f"{self.prefix}_count": self.enrichment_count,
        }


class TestAsyncEnricherIntegration:
    """Integration tests for async enricher pipeline integration."""

    def setup_method(self):
        """Setup for each test."""
        # Clear any existing instances
        EnricherRegistry.clear_instances()

    def teardown_method(self):
        """Cleanup after each test."""
        EnricherRegistry.clear_instances()

    def test_async_enricher_registry_integration(self):
        """Test that async enrichers are properly wrapped by registry."""
        # Get instance from registry
        async_enricher = EnricherRegistry.get_instance("test-async-enricher")

        # Should be wrapped in AsyncEnricherProcessor
        from fapilog._internal.async_pipeline import AsyncEnricherProcessor

        assert isinstance(async_enricher, AsyncEnricherProcessor)

        # Should contain the actual async enricher
        assert len(async_enricher.enrichers) == 1
        assert isinstance(async_enricher.enrichers[0], AsyncEnricherForTesting)

    def test_sync_enricher_registry_integration(self):
        """Test that sync enrichers work normally."""
        # Get instance from registry
        sync_enricher = EnricherRegistry.get_instance("test-sync-enricher")

        # Should be the actual enricher, not wrapped
        assert isinstance(sync_enricher, SyncEnricherForTesting)

    def test_mixed_enricher_processor_execution(self):
        """Test that enricher processor handles mixed sync/async enrichers."""
        settings = LoggingSettings()
        lifecycle_manager = EnricherLifecycleManager()

        # Create processor with lifecycle manager
        processor = create_enricher_processor(settings, lifecycle_manager)

        # Mock event dict
        event_dict = {"event": "test_log", "level": "INFO"}

        # Process event
        result = processor(None, "info", event_dict)

        # Should contain enrichments from both sync and async enrichers
        assert "sync_enriched" in result
        assert "async_enriched" in result
        assert result["sync_count"] == 1
        assert result["async_count"] == 1

    def test_enricher_lifecycle_registration(self):
        """Test that async enrichers are registered with lifecycle manager."""
        lifecycle_manager = EnricherLifecycleManager()
        settings = LoggingSettings()

        # Create processor - this should register async enrichers
        processor = create_enricher_processor(settings, lifecycle_manager)

        # Process an event to trigger registration
        event_dict = {"event": "test_log", "level": "INFO"}
        processor(None, "info", event_dict)

        # Check that async enricher was registered
        assert len(lifecycle_manager.enrichers) >= 1
        async_enricher_names = [e.name for e in lifecycle_manager.enrichers]
        assert "test-async-enricher" in async_enricher_names

    @pytest.mark.asyncio
    async def test_lifecycle_manager_startup_shutdown(self):
        """Test enricher lifecycle management."""
        lifecycle_manager = EnricherLifecycleManager()

        # Create and register an async enricher
        enricher = AsyncEnricherForTesting()
        lifecycle_manager.register_enricher(enricher)

        # Test startup
        await lifecycle_manager.startup_all()
        assert lifecycle_manager.is_started
        assert enricher.is_started

        # Test health check
        health = await lifecycle_manager.health_check_all()
        assert health["test-async-enricher"] is True

        # Test shutdown
        await lifecycle_manager.shutdown_all()
        assert not lifecycle_manager.is_started
        assert not enricher.is_started

    def test_container_integration(self):
        """Test full container integration with async enrichers."""
        settings = LoggingSettings()
        container = LoggingContainer(settings)

        # Configure container
        logger = container.configure(settings)

        # Container should have lifecycle manager
        assert hasattr(container, "_enricher_lifecycle")
        assert container._enricher_lifecycle is not None

        # Test logging with enrichers
        logger.info("test message", extra_field="test")

    def test_uri_factory_async_enricher_creation(self):
        """Test creating async enrichers via URI factory."""
        from fapilog._internal.enricher_factory import EnricherFactory

        # Test URI creation for async enricher
        uri = "test-async-enricher://localhost?prefix=uri_async&timeout=3.0"
        enricher = EnricherFactory.create_enricher_from_uri(uri)

        # Should be wrapped AsyncEnricherProcessor
        from fapilog._internal.async_pipeline import AsyncEnricherProcessor

        assert isinstance(enricher, AsyncEnricherProcessor)

        # Check timeout was applied
        assert enricher.timeout == 3.0

    def test_settings_enricher_configuration(self):
        """Test configuring async enrichers via settings."""
        settings = LoggingSettings(
            enrichers=[
                ("test-async-enricher://localhost?prefix=settings_async&timeout=2.0"),
                "test-sync-enricher://localhost?prefix=settings_sync",
            ]
        )

        # Create processor
        lifecycle_manager = EnricherLifecycleManager()
        processor = create_enricher_processor(settings, lifecycle_manager)

        # Process event
        event_dict = {"event": "test_settings", "level": "INFO"}
        result = processor(None, "info", event_dict)

        # Should have enrichments from both async and sync enrichers
        # Note: Currently uses default prefixes rather than URI-specified ones
        assert "async_enriched" in result
        assert "sync_enriched" in result
        assert result["async_count"] == 1
        assert result["sync_count"] == 1

    def test_async_enricher_error_handling(self):
        """Test error handling for async enrichers."""

        @register_enricher_advanced(
            name="failing-async-enricher",
            description="Async enricher that fails",
            priority=75,
            async_capable=True,
        )
        class FailingAsyncEnricher(AsyncEnricher):
            def __init__(self):
                super().__init__("failing-async-enricher")

            async def _startup(self):
                pass

            async def _shutdown(self):
                pass

            async def _health_check(self):
                return True

            async def enrich_async(self, logger, method_name, event_dict):
                raise Exception("Intentional async enricher failure")

        try:
            settings = LoggingSettings()
            lifecycle_manager = EnricherLifecycleManager()
            processor = create_enricher_processor(settings, lifecycle_manager)

            # Process event - should not crash despite enricher failure
            event_dict = {"event": "test_error", "level": "INFO"}
            result = processor(None, "info", event_dict)

            # Should still contain original event
            assert "event" in result
            assert result["event"] == "test_error"

        finally:
            # Cleanup
            EnricherRegistry.clear_instances()

    def test_async_enricher_timeout_handling(self):
        """Test timeout handling for slow async enrichers."""

        @register_enricher_advanced(
            name="slow-async-enricher",
            description="Slow async enricher for timeout testing",
            priority=60,
            async_capable=True,
        )
        class SlowAsyncEnricher(AsyncEnricher):
            def __init__(self, timeout=0.1):  # Very short timeout
                super().__init__("slow-async-enricher")
                self.timeout = timeout

            async def _startup(self):
                pass

            async def _shutdown(self):
                pass

            async def _health_check(self):
                return True

            async def enrich_async(self, logger, method_name, event_dict):
                await asyncio.sleep(1.0)  # Sleep longer than timeout
                return {**event_dict, "slow_enriched": True}

        try:
            # Create enricher with short timeout
            enricher = EnricherRegistry.get_instance("slow-async-enricher", timeout=0.1)

            # Process event - should timeout gracefully
            event_dict = {"event": "test_timeout", "level": "INFO"}
            result = enricher(None, "info", event_dict)

            # Should return original event (timeout should not add enrichment)
            assert "event" in result
            assert result["event"] == "test_timeout"
            assert "slow_enriched" not in result

        finally:
            # Cleanup
            EnricherRegistry.clear_instances()

    def test_enricher_dependency_ordering_with_async(self):
        """Test that dependency ordering works with mixed sync/async enrichers."""

        @register_enricher_advanced(
            name="dependent-async-enricher",
            description="Async enricher with dependencies",
            priority=200,
            dependencies=["test-sync-enricher"],
            async_capable=True,
        )
        class DependentAsyncEnricher(AsyncEnricher):
            def __init__(self):
                super().__init__("dependent-async-enricher")

            async def _startup(self):
                pass

            async def _shutdown(self):
                pass

            async def _health_check(self):
                return True

            async def enrich_async(self, logger, method_name, event_dict):
                # Should run after sync enricher
                assert "sync_enriched" in event_dict
                return {**event_dict, "dependent_async_enriched": True}

        try:
            settings = LoggingSettings()
            lifecycle_manager = EnricherLifecycleManager()
            processor = create_enricher_processor(settings, lifecycle_manager)

            # Process event
            event_dict = {"event": "test_dependency", "level": "INFO"}
            result = processor(None, "info", event_dict)

            # Should have both enrichments with correct order
            assert "sync_enriched" in result
            assert "dependent_async_enriched" in result

        finally:
            # Cleanup
            EnricherRegistry.clear_instances()


if __name__ == "__main__":
    pytest.main([__file__])
