"""Tests for enhanced enricher registry functionality."""

import pytest

from fapilog._internal.enricher_registry import EnricherRegistry
from fapilog.exceptions import EnricherConfigurationError, EnricherDependencyError


class TestEnricherRegistry:
    """Test enhanced enricher registry."""

    def setup_method(self):
        """Clear registry before each test."""
        EnricherRegistry.clear_registry()

    def test_register_enricher_with_metadata(self):
        """Test registering enricher with full metadata."""

        class TestEnricher:
            def __call__(self, logger, method_name, event_dict):
                return event_dict

        # Register enricher with metadata
        EnricherRegistry.register(
            name="test_enricher",
            enricher_class=TestEnricher,
            description="Test enricher for unit testing",
            priority=50,
            dependencies=["dep1", "dep2"],
            conditions={"environment": ["production"]},
            async_capable=True,
        )

        # Verify registration
        metadata = EnricherRegistry.get_metadata("test_enricher")
        assert metadata is not None
        assert metadata.name == "test_enricher"
        assert metadata.enricher_class == TestEnricher
        assert metadata.description == "Test enricher for unit testing"
        assert metadata.priority == 50
        assert metadata.dependencies == ["dep1", "dep2"]
        assert metadata.conditions == {"environment": ["production"]}
        assert metadata.async_capable is True

    def test_list_enrichers(self):
        """Test listing all registered enrichers."""

        class EnricherA:
            pass

        class EnricherB:
            pass

        # Register multiple enrichers
        EnricherRegistry.register("enricher_a", EnricherA, "Enricher A")
        EnricherRegistry.register("enricher_b", EnricherB, "Enricher B")

        # List enrichers
        enrichers = EnricherRegistry.list_enrichers()
        assert len(enrichers) == 2
        assert "enricher_a" in enrichers
        assert "enricher_b" in enrichers
        assert enrichers["enricher_a"].enricher_class == EnricherA
        assert enrichers["enricher_b"].enricher_class == EnricherB

    def test_get_metadata_not_found(self):
        """Test getting metadata for non-existent enricher."""
        metadata = EnricherRegistry.get_metadata("non_existent")
        assert metadata is None

    def test_resolve_dependencies_simple(self):
        """Test dependency resolution with simple linear dependencies."""

        class EnricherA:
            pass

        class EnricherB:
            pass

        class EnricherC:
            pass

        # Register enrichers with dependencies: C -> B -> A
        EnricherRegistry.register("enricher_a", EnricherA, "A", priority=100)
        EnricherRegistry.register(
            "enricher_b", EnricherB, "B", priority=100, dependencies=["enricher_a"]
        )
        EnricherRegistry.register(
            "enricher_c", EnricherC, "C", priority=100, dependencies=["enricher_b"]
        )

        # Resolve dependencies
        order = EnricherRegistry.resolve_dependencies(
            ["enricher_c", "enricher_b", "enricher_a"]
        )
        assert order == ["enricher_a", "enricher_b", "enricher_c"]

    def test_resolve_dependencies_with_priority(self):
        """Test dependency resolution with priority ordering."""

        class EnricherA:
            pass

        class EnricherB:
            pass

        class EnricherC:
            pass

        # Register enrichers with different priorities (lower = higher priority)
        EnricherRegistry.register("enricher_a", EnricherA, "A", priority=200)
        EnricherRegistry.register("enricher_b", EnricherB, "B", priority=50)
        EnricherRegistry.register("enricher_c", EnricherC, "C", priority=100)

        # Resolve - should order by priority when no dependencies
        order = EnricherRegistry.resolve_dependencies(
            ["enricher_a", "enricher_b", "enricher_c"]
        )
        assert order == ["enricher_b", "enricher_c", "enricher_a"]

    def test_resolve_dependencies_circular(self):
        """Test circular dependency detection."""

        class EnricherA:
            pass

        class EnricherB:
            pass

        # Register enrichers with circular dependencies: A -> B, B -> A
        EnricherRegistry.register(
            "enricher_a", EnricherA, "A", dependencies=["enricher_b"]
        )
        EnricherRegistry.register(
            "enricher_b", EnricherB, "B", dependencies=["enricher_a"]
        )

        # Should raise dependency error
        with pytest.raises(EnricherDependencyError) as exc_info:
            EnricherRegistry.resolve_dependencies(["enricher_a", "enricher_b"])

        assert "Circular dependency detected" in str(exc_info.value)

    def test_resolve_dependencies_empty_list(self):
        """Test dependency resolution with empty list."""
        order = EnricherRegistry.resolve_dependencies([])
        assert order == []

    def test_get_instance_success(self):
        """Test creating enricher instance successfully."""

        class TestEnricher:
            def __init__(self, param1="default", param2=42):
                self.param1 = param1
                self.param2 = param2

        # Register enricher
        EnricherRegistry.register("test_enricher", TestEnricher, "Test")

        # Create instance with parameters
        instance = EnricherRegistry.get_instance(
            "test_enricher", param1="custom", param2=100
        )
        assert isinstance(instance, TestEnricher)
        assert instance.param1 == "custom"
        assert instance.param2 == 100

    def test_get_instance_caching(self):
        """Test that instances are cached based on parameters."""

        class TestEnricher:
            def __init__(self, param="default"):
                self.param = param

        # Register enricher
        EnricherRegistry.register("test_enricher", TestEnricher, "Test")

        # Create instances with same parameters
        instance1 = EnricherRegistry.get_instance("test_enricher", param="value")
        instance2 = EnricherRegistry.get_instance("test_enricher", param="value")

        # Should be the same instance (cached)
        assert instance1 is instance2

        # Create instance with different parameters
        instance3 = EnricherRegistry.get_instance("test_enricher", param="different")

        # Should be different instance
        assert instance1 is not instance3

    def test_get_instance_not_registered(self):
        """Test getting instance for non-registered enricher."""
        with pytest.raises(EnricherConfigurationError) as exc_info:
            EnricherRegistry.get_instance("non_existent")

        assert "not registered" in str(exc_info.value)

    def test_get_instance_instantiation_error(self):
        """Test handling of enricher instantiation errors."""

        class FailingEnricher:
            def __init__(self, required_param):
                if required_param is None:
                    raise ValueError("required_param cannot be None")
                self.required_param = required_param

        # Register enricher
        EnricherRegistry.register("failing_enricher", FailingEnricher, "Failing")

        # Try to create instance without required parameter
        with pytest.raises(EnricherConfigurationError) as exc_info:
            EnricherRegistry.get_instance("failing_enricher")

        assert "Failed to instantiate enricher" in str(exc_info.value)

    def test_clear_registry(self):
        """Test clearing the registry."""

        class TestEnricher:
            pass

        # Register enricher
        EnricherRegistry.register("test_enricher", TestEnricher, "Test")
        assert len(EnricherRegistry.list_enrichers()) == 1

        # Clear registry
        EnricherRegistry.clear_registry()
        assert len(EnricherRegistry.list_enrichers()) == 0

    def test_clear_instances(self):
        """Test clearing cached instances."""

        class TestEnricher:
            def __init__(self, param="default"):
                self.param = param

        # Register enricher and create instance
        EnricherRegistry.register("test_enricher", TestEnricher, "Test")
        instance1 = EnricherRegistry.get_instance("test_enricher", param="value")

        # Clear instances
        EnricherRegistry.clear_instances()

        # Create same instance again - should be new object
        instance2 = EnricherRegistry.get_instance("test_enricher", param="value")
        assert instance1 is not instance2
        assert instance1.param == instance2.param  # Same parameters though

    def test_complex_dependency_resolution(self):
        """Test complex dependency resolution scenario."""

        class EnricherA:
            pass

        class EnricherB:
            pass

        class EnricherC:
            pass

        class EnricherD:
            pass

        class EnricherE:
            pass

        # Register enrichers with complex dependencies:
        # E -> [C, D], C -> [A, B], D -> [B], B -> [A]
        # Expected order: A, B, C, D, E
        EnricherRegistry.register("enricher_a", EnricherA, "A", priority=100)
        EnricherRegistry.register(
            "enricher_b", EnricherB, "B", priority=100, dependencies=["enricher_a"]
        )
        EnricherRegistry.register(
            "enricher_c",
            EnricherC,
            "C",
            priority=100,
            dependencies=["enricher_a", "enricher_b"],
        )
        EnricherRegistry.register(
            "enricher_d", EnricherD, "D", priority=100, dependencies=["enricher_b"]
        )
        EnricherRegistry.register(
            "enricher_e",
            EnricherE,
            "E",
            priority=100,
            dependencies=["enricher_c", "enricher_d"],
        )

        # Resolve dependencies
        order = EnricherRegistry.resolve_dependencies(
            ["enricher_e", "enricher_d", "enricher_c", "enricher_b", "enricher_a"]
        )

        # Verify correct dependency constraints are satisfied
        # (multiple valid topological orderings are possible)
        a_pos = order.index("enricher_a")
        b_pos = order.index("enricher_b")
        c_pos = order.index("enricher_c")
        d_pos = order.index("enricher_d")
        e_pos = order.index("enricher_e")

        # Verify dependency constraints:
        # B depends on A
        assert a_pos < b_pos
        # C depends on A and B
        assert a_pos < c_pos and b_pos < c_pos
        # D depends on B
        assert b_pos < d_pos
        # E depends on C and D
        assert c_pos < e_pos and d_pos < e_pos

    def test_new_pipeline_integration(self):
        """Test that the new pipeline integration works with the enhanced enricher registry."""

        class EnricherA:
            pass

        class EnricherB:
            pass

        class EnricherC:
            pass

        class EnricherD:
            pass

        # Register enrichers
        EnricherRegistry.register("a", EnricherA, "A")
        EnricherRegistry.register("b", EnricherB, "B")
        EnricherRegistry.register("c", EnricherC, "C")
        EnricherRegistry.register("d", EnricherD, "D", dependencies=["a", "b"])

        # Get metadata for "d"
        result = EnricherRegistry.get_metadata("d")
        assert result is not None
        assert result.name == "d"
        assert result.dependencies == ["a", "b"]

    def test_pipeline_integration_with_enhanced_registry(self):
        """Test that enhanced enricher registry integrates with pipeline."""
        from fapilog.pipeline import create_enricher_processor
        from fapilog.settings import LoggingSettings

        # Create a test enricher class
        class TestPipelineEnricher:
            def __init__(self, prefix="test"):
                self.prefix = prefix

            def __call__(self, logger, method_name, event_dict):
                event_dict[f"{self.prefix}_enhanced"] = True
                event_dict[f"{self.prefix}_method"] = method_name
                return event_dict

        # Register enricher with conditions
        EnricherRegistry.register(
            name="pipeline_test",
            enricher_class=TestPipelineEnricher,
            description="Test enricher for pipeline integration",
            priority=50,
            conditions={"environment": ["test", "development"]},
        )

        # Create settings and processor
        settings = LoggingSettings()
        processor = create_enricher_processor(settings)

        # Test processor execution
        event_dict = {"event": "test message", "level": "INFO"}
        result = processor(None, "info", event_dict)

        # Verify enricher was applied
        assert result["test_enhanced"] is True
        assert result["test_method"] == "info"
        assert result["event"] == "test message"
