"""Tests for enricher factory URI functionality."""

import pytest

from fapilog._internal.enricher_factory import EnricherFactory
from fapilog._internal.enricher_registry import EnricherRegistry
from fapilog.exceptions import EnricherConfigurationError


class TestEnricherFactory:
    """Test enricher factory functionality."""

    def setup_method(self):
        """Clear registry before each test."""
        EnricherRegistry.clear_registry()

    def test_create_enricher_from_uri_basic(self):
        """Test creating enricher from basic URI."""

        class TestEnricher:
            def __init__(self, host="localhost", port=8080, timeout=5):
                self.host = host
                self.port = port
                self.timeout = timeout

            def __call__(self, logger, method_name, event_dict):
                return event_dict

        # Register enricher
        EnricherRegistry.register("testscheme", TestEnricher, "Test")

        # Create from URI
        uri = "testscheme://api.example.com:9000?timeout=10"
        enricher = EnricherFactory.create_enricher_from_uri(uri)

        assert isinstance(enricher, TestEnricher)
        assert enricher.host == "api.example.com"
        assert enricher.port == 9000
        assert enricher.timeout == 10

    def test_create_enricher_with_path_and_credentials(self):
        """Test URI with path and credentials."""

        class DatabaseEnricher:
            def __init__(
                self,
                host="localhost",
                port=5432,
                path="",
                username=None,
                password=None,
                **kwargs,
            ):
                self.host = host
                self.port = port
                self.path = path
                self.username = username
                self.password = password
                self.kwargs = kwargs

        # Register enricher
        EnricherRegistry.register("database", DatabaseEnricher, "Database")

        # Create from URI with credentials and path
        uri = "database://user:pass@db.example.com:5432/mydb?ssl=true"
        enricher = EnricherFactory.create_enricher_from_uri(uri)

        assert enricher.host == "db.example.com"
        assert enricher.port == 5432
        assert enricher.path == "mydb"
        assert enricher.username == "user"
        assert enricher.password == "pass"
        assert enricher.kwargs["ssl"] is True

    def test_parameter_type_conversion(self):
        """Test automatic parameter type conversion."""

        class TypeTestEnricher:
            def __init__(
                self,
                str_param="",
                int_param=0,
                float_param=0.0,
                bool_param=False,
                **kwargs,
            ):
                self.str_param = str_param
                self.int_param = int_param
                self.float_param = float_param
                self.bool_param = bool_param
                self.kwargs = kwargs

        # Register enricher
        EnricherRegistry.register("typetest", TypeTestEnricher, "Type Test")

        # Create with different parameter types
        uri = (
            "typetest://localhost?str_param=hello&int_param=42"
            "&float_param=3.14&bool_param=true"
        )
        enricher = EnricherFactory.create_enricher_from_uri(uri)

        assert enricher.str_param == "hello"
        assert enricher.int_param == 42
        assert enricher.float_param == 3.14
        assert enricher.bool_param is True

    def test_uri_validation_errors(self):
        """Test URI validation error cases."""

        # Empty or None URI
        with pytest.raises(EnricherConfigurationError) as exc:
            EnricherFactory.create_enricher_from_uri("")
        assert "non-empty string" in str(exc.value)

        # No scheme
        with pytest.raises(EnricherConfigurationError) as exc:
            EnricherFactory.create_enricher_from_uri("no-scheme-here")
        assert "must include a scheme" in str(exc.value)

        # Unknown scheme
        with pytest.raises(EnricherConfigurationError) as exc:
            EnricherFactory.create_enricher_from_uri("unknown://localhost")
        assert "Unknown enricher scheme" in str(exc.value)

    def test_enricher_instantiation_error(self):
        """Test handling of enricher instantiation errors."""

        class FailingEnricher:
            def __init__(self, required_param):
                if not required_param:
                    raise ValueError("required_param is required")
                self.required_param = required_param

        # Register enricher
        EnricherRegistry.register("failing", FailingEnricher, "Failing")

        # Try to create without required parameter
        with pytest.raises(EnricherConfigurationError) as exc:
            EnricherFactory.create_enricher_from_uri("failing://localhost")
        assert "Failed to instantiate enricher" in str(exc.value)

    def test_create_enrichers_from_uris(self):
        """Test creating multiple enrichers from URI list."""

        class EnricherA:
            def __init__(self, param="default", **kwargs):
                self.param = param

        class EnricherB:
            def __init__(self, value=100, **kwargs):
                self.value = value

        # Register enrichers
        EnricherRegistry.register("enrichera", EnricherA, "A")
        EnricherRegistry.register("enricherb", EnricherB, "B")

        # Create multiple enrichers
        uris = ["enrichera://localhost?param=custom", "enricherb://localhost?value=200"]
        enrichers = EnricherFactory.create_enrichers_from_uris(uris)

        assert len(enrichers) == 2
        assert "enrichera" in enrichers
        assert "enricherb" in enrichers
        assert enrichers["enrichera"].param == "custom"
        assert enrichers["enricherb"].value == 200

    def test_create_enrichers_from_uris_error(self):
        """Test error handling in multiple URI creation."""

        uris = [
            "valid://localhost",  # Will fail - not registered
            "invalid",  # Will fail - no scheme
        ]

        with pytest.raises(EnricherConfigurationError) as exc:
            EnricherFactory.create_enrichers_from_uris(uris)
        assert "Failed to create enricher from URI" in str(exc.value)

    def test_validate_uri(self):
        """Test URI validation function."""

        class ValidEnricher:
            def __init__(self, **kwargs):
                pass

        # Register enricher
        EnricherRegistry.register("valid", ValidEnricher, "Valid")

        # Valid URI
        assert EnricherFactory.validate_enricher_uri("valid://localhost") is True

        # Invalid URIs
        assert EnricherFactory.validate_enricher_uri("invalid://localhost") is False
        assert EnricherFactory.validate_enricher_uri("no-scheme") is False
        assert EnricherFactory.validate_enricher_uri("") is False

    def test_minimal_uri(self):
        """Test minimal URI with just scheme."""

        class MinimalEnricher:
            def __init__(self):
                pass

        # Register enricher
        EnricherRegistry.register("minimal", MinimalEnricher, "Minimal")

        # Minimal URI
        enricher = EnricherFactory.create_enricher_from_uri("minimal://")
        assert isinstance(enricher, MinimalEnricher)

    def test_complex_uri_example(self):
        """Test complex real-world URI example."""

        class UserContextEnricher:
            def __init__(
                self,
                host="localhost",
                port=8080,
                path="",
                timeout=5,
                api_key="",
                cache_ttl=300,
                **kwargs,
            ):
                self.host = host
                self.port = port
                self.path = path
                self.timeout = timeout
                self.api_key = api_key
                self.cache_ttl = cache_ttl
                self.kwargs = kwargs

        # Register enricher
        EnricherRegistry.register("usercontext", UserContextEnricher, "User Context")

        # Complex URI
        uri = (
            "usercontext://auth-api.company.com:8443/v1/users"
            "?timeout=10&api_key=secret123&cache_ttl=600&ssl=true"
        )
        enricher = EnricherFactory.create_enricher_from_uri(uri)

        assert enricher.host == "auth-api.company.com"
        assert enricher.port == 8443
        assert enricher.path == "v1/users"
        assert enricher.timeout == 10
        assert enricher.api_key == "secret123"
        assert enricher.cache_ttl == 600
        assert enricher.kwargs["ssl"] is True
