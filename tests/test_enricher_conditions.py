"""Tests for enricher conditions functionality."""

import os

from fapilog._internal.enricher_conditions import EnricherConditions
from fapilog._internal.enricher_registry import EnricherRegistry


class TestEnricherConditions:
    """Test enricher conditions."""

    def setup_method(self):
        """Clear registry before each test."""
        EnricherRegistry.clear_registry()

    def test_no_conditions_always_enabled(self):
        """Test that enrichers with no conditions are always enabled."""

        class TestEnricher:
            pass

        # Register enricher without conditions
        EnricherRegistry.register("test", TestEnricher, "Test")
        metadata = EnricherRegistry.get_metadata("test")

        context = {"level": "INFO", "environment": "development"}
        assert EnricherConditions.should_enable_enricher(metadata, context) is True

    def test_environment_condition(self):
        """Test environment-based conditions."""

        class TestEnricher:
            pass

        # Register enricher with environment condition
        EnricherRegistry.register(
            "test",
            TestEnricher,
            "Test",
            conditions={"environment": ["production", "staging"]},
        )
        metadata = EnricherRegistry.get_metadata("test")

        # Should be enabled in production
        context = {"environment": "production"}
        assert EnricherConditions.should_enable_enricher(metadata, context) is True

        # Should be enabled in staging
        context = {"environment": "staging"}
        assert EnricherConditions.should_enable_enricher(metadata, context) is True

        # Should NOT be enabled in development
        context = {"environment": "development"}
        assert EnricherConditions.should_enable_enricher(metadata, context) is False

    def test_log_level_condition(self):
        """Test log level conditions."""

        class TestEnricher:
            pass

        # Register enricher that only runs on WARNING and above
        EnricherRegistry.register(
            "test", TestEnricher, "Test", conditions={"min_level": "WARNING"}
        )
        metadata = EnricherRegistry.get_metadata("test")

        # Should be enabled for WARNING and above
        assert (
            EnricherConditions.should_enable_enricher(metadata, {"level": "WARNING"})
            is True
        )
        assert (
            EnricherConditions.should_enable_enricher(metadata, {"level": "ERROR"})
            is True
        )

        # Should NOT be enabled for INFO and below
        assert (
            EnricherConditions.should_enable_enricher(metadata, {"level": "INFO"})
            is False
        )
        assert (
            EnricherConditions.should_enable_enricher(metadata, {"level": "DEBUG"})
            is False
        )

    def test_runtime_condition_function(self):
        """Test runtime condition functions."""

        class TestEnricher:
            pass

        # Condition function that checks if user_id is present
        def has_user_id(context):
            return "user_id" in context and context["user_id"] is not None

        # Register enricher with runtime condition
        EnricherRegistry.register(
            "test", TestEnricher, "Test", conditions={"condition_func": has_user_id}
        )
        metadata = EnricherRegistry.get_metadata("test")

        # Should be enabled when user_id is present
        context = {"user_id": "123"}
        assert EnricherConditions.should_enable_enricher(metadata, context) is True

        # Should NOT be enabled when user_id is missing
        context = {}
        assert EnricherConditions.should_enable_enricher(metadata, context) is False

    def test_multiple_conditions_all_must_pass(self):
        """Test that all conditions must pass for enricher to be enabled."""

        class TestEnricher:
            pass

        # Register enricher with multiple conditions
        EnricherRegistry.register(
            "test",
            TestEnricher,
            "Test",
            conditions={"environment": ["production"], "min_level": "ERROR"},
        )
        metadata = EnricherRegistry.get_metadata("test")

        # Both conditions met - should be enabled
        context = {"environment": "production", "level": "ERROR"}
        assert EnricherConditions.should_enable_enricher(metadata, context) is True

        # Only environment condition met - should NOT be enabled
        context = {"environment": "production", "level": "INFO"}
        assert EnricherConditions.should_enable_enricher(metadata, context) is False

        # Only level condition met - should NOT be enabled
        context = {"environment": "development", "level": "ERROR"}
        assert EnricherConditions.should_enable_enricher(metadata, context) is False

    def test_feature_flag_condition(self):
        """Test feature flag conditions."""

        class TestEnricher:
            pass

        # Register enricher with feature flag condition
        EnricherRegistry.register(
            "test",
            TestEnricher,
            "Test",
            conditions={"feature_flags": ["advanced_logging"]},
        )
        metadata = EnricherRegistry.get_metadata("test")

        # Should be enabled when feature flag is true
        context = {"feature_advanced_logging": True}
        assert EnricherConditions.should_enable_enricher(metadata, context) is True

        # Should NOT be enabled when feature flag is false
        context = {"feature_advanced_logging": False}
        assert EnricherConditions.should_enable_enricher(metadata, context) is False

        # Should NOT be enabled when feature flag is missing
        context = {}
        assert EnricherConditions.should_enable_enricher(metadata, context) is False

    def test_environment_fallback_to_env_var(self):
        """Test that environment condition falls back to environment variable."""

        class TestEnricher:
            pass

        # Register enricher with environment condition
        EnricherRegistry.register(
            "test", TestEnricher, "Test", conditions={"environment": ["production"]}
        )
        metadata = EnricherRegistry.get_metadata("test")

        # Set environment variable
        original_env = os.environ.get("ENVIRONMENT")
        try:
            os.environ["ENVIRONMENT"] = "production"

            # Should be enabled when environment variable matches
            context = {}  # No environment in context
            assert EnricherConditions.should_enable_enricher(metadata, context) is True

        finally:
            # Restore original environment
            if original_env is not None:
                os.environ["ENVIRONMENT"] = original_env
            elif "ENVIRONMENT" in os.environ:
                del os.environ["ENVIRONMENT"]
