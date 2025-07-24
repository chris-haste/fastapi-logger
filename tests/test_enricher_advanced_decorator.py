"""Tests for advanced enricher decorator functionality."""

from fapilog._internal.enricher_registry import EnricherRegistry
from fapilog.enrichers import register_enricher, register_enricher_advanced


class TestAdvancedEnricherDecorator:
    """Test advanced enricher decorator."""

    def setup_method(self):
        """Clear registry before each test."""
        EnricherRegistry.clear_registry()

    def test_register_enricher_advanced_decorator(self):
        """Test the advanced enricher decorator."""

        @register_enricher_advanced(
            name="test_enricher",
            description="Test enricher",
            priority=50,
            dependencies=["auth"],
            conditions={"environment": ["production"]},
            async_capable=True,
        )
        class TestEnricher:
            def __init__(self, param="default"):
                self.param = param

            def __call__(self, logger, method_name, event_dict):
                event_dict["test_field"] = f"test_value_{self.param}"
                return event_dict

        # Verify registration in advanced registry
        metadata = EnricherRegistry.get_metadata("test_enricher")
        assert metadata is not None
        assert metadata.name == "test_enricher"
        assert metadata.enricher_class == TestEnricher
        assert metadata.description == "Test enricher"
        assert metadata.priority == 50
        assert metadata.dependencies == ["auth"]
        assert metadata.conditions == {"environment": ["production"]}
        assert metadata.async_capable is True

        # Test creating instance
        instance = EnricherRegistry.get_instance("test_enricher", param="custom")
        assert isinstance(instance, TestEnricher)
        assert instance.param == "custom"

    def test_backward_compatible_register_enricher(self):
        """Test legacy register_enricher raises helpful error."""

        def test_function_enricher(logger, method_name, event_dict):
            event_dict["function_field"] = "function_value"
            return event_dict

        # Test that legacy function raises helpful error
        import pytest

        with pytest.raises(AttributeError) as exc_info:
            register_enricher(test_function_enricher)

        error_msg = str(exc_info.value)
        assert "register_enricher() has been removed" in error_msg
        assert "register_enricher_advanced" in error_msg

    def test_enricher_with_no_metadata(self):
        """Test enricher registration with minimal metadata."""

        @register_enricher_advanced(name="minimal_enricher")
        class MinimalEnricher:
            def __call__(self, logger, method_name, event_dict):
                return event_dict

        metadata = EnricherRegistry.get_metadata("minimal_enricher")
        assert metadata is not None
        assert metadata.name == "minimal_enricher"
        assert metadata.description == ""
        assert metadata.priority == 100
        assert metadata.dependencies == []
        assert metadata.conditions == {}
        assert metadata.async_capable is False
