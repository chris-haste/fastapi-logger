#!/usr/bin/env python3
"""
Example: Custom Sink Registry and URI Integration

This example demonstrates the new sink registry system that allows
registering custom sinks globally and configuring them via URIs.

Key features:
- Global sink registration with @register_sink decorator
- URI-based sink configuration (e.g., postgres://localhost/logs)
- Environment variable integration
- Backward compatibility with direct instances
- Discovery and listing capabilities
- Comprehensive error handling
"""

import asyncio
import json
from typing import Any, Dict

from fapilog import configure_logging
from fapilog._internal.sink_registry import SinkRegistry, register_sink
from fapilog.sinks.base import Sink


@register_sink("postgres")
class PostgresSink(Sink):
    """Mock PostgreSQL sink for demonstration."""

    def __init__(
        self,
        host="localhost",
        port=5432,
        database="logs",
        username=None,
        password=None,
        pool_size=5,
        ssl=False,
        **kwargs,
    ):
        super().__init__()
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.pool_size = pool_size
        self.ssl = ssl
        self.kwargs = kwargs

        print("PostgresSink initialized:")
        print(f"  Host: {self.host}:{self.port}")
        print(f"  Database: {self.database}")
        print(f"  Username: {self.username}")
        print(f"  SSL: {self.ssl}")
        print(f"  Pool size: {self.pool_size}")
        print(f"  Extra params: {self.kwargs}")

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Write to mock PostgreSQL database."""
        # Mock database write
        print(f"[POSTGRES] {json.dumps(event_dict, default=str)}")


@register_sink("mongodb")
class MongoDBSink(Sink):
    """Mock MongoDB sink for demonstration."""

    def __init__(
        self,
        host="localhost",
        port=27017,
        database="logs",
        collection="app_logs",
        **kwargs,
    ):
        super().__init__()
        self.host = host
        self.port = port
        self.database = database
        self.collection = collection
        self.kwargs = kwargs

        print("MongoDBSink initialized:")
        print(f"  Host: {self.host}:{self.port}")
        print(f"  Database: {self.database}")
        print(f"  Collection: {self.collection}")
        print(f"  Extra params: {self.kwargs}")

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Write to mock MongoDB collection."""
        # Mock MongoDB write
        print(f"[MONGODB] {json.dumps(event_dict, default=str)}")


@register_sink("elasticsearch")
class ElasticsearchSink(Sink):
    """Mock Elasticsearch sink for demonstration."""

    def __init__(
        self,
        host="localhost",
        port=9200,
        index="logs",
        username=None,
        password=None,
        verify_certs=True,
        **kwargs,
    ):
        super().__init__()
        self.host = host
        self.port = port
        self.index = index
        self.username = username
        self.password = password
        self.verify_certs = verify_certs
        self.kwargs = kwargs

        print("ElasticsearchSink initialized:")
        print(f"  Host: {self.host}:{self.port}")
        print(f"  Index: {self.index}")
        print(f"  Username: {self.username}")
        print(f"  Verify certs: {self.verify_certs}")
        print(f"  Extra params: {self.kwargs}")

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Write to mock Elasticsearch index."""
        # Mock Elasticsearch write
        print(f"[ELASTICSEARCH] {json.dumps(event_dict, default=str)}")


def demonstrate_registry_discovery():
    """Demonstrate sink registry discovery capabilities."""
    print("=== Sink Registry Discovery ===")

    # List all registered sinks
    registered_sinks = SinkRegistry.list()
    print(f"Registered custom sinks: {list(registered_sinks.keys())}")

    for name, sink_class in registered_sinks.items():
        print(f"  - {name}: {sink_class.__name__}")

    print()


def demonstrate_uri_configuration():
    """Demonstrate URI-based sink configuration."""
    print("=== URI-Based Configuration ===")

    print("1. Basic PostgreSQL sink:")
    logger1 = configure_logging(sinks=["postgres://localhost/myapp_logs"])
    logger1.info("Basic PostgreSQL configuration test")

    print("\n2. PostgreSQL with credentials and parameters:")
    logger2 = configure_logging(
        sinks=[
            "postgres://admin:secret@db.example.com:5432/prod_logs?pool_size=20&ssl=true"
        ]
    )
    logger2.info("Advanced PostgreSQL configuration test")

    print("\n3. MongoDB configuration:")
    logger3 = configure_logging(sinks=["mongodb://localhost:27017/app_logs"])
    logger3.info("MongoDB configuration test")

    print("\n4. Elasticsearch configuration:")
    logger4 = configure_logging(
        sinks=["elasticsearch://elastic:password@search.example.com:9200/logs-2024"]
    )
    logger4.info("Elasticsearch configuration test")

    print()


def demonstrate_mixed_configuration():
    """Demonstrate mixing built-in and custom sinks."""
    print("=== Mixed Sink Configuration ===")

    # Create a direct sink instance
    direct_postgres = PostgresSink(
        host="direct.example.com", database="direct_logs", pool_size=15
    )

    # Mix different sink types
    logger = configure_logging(
        sinks=[
            "stdout",  # Built-in sink
            direct_postgres,  # Direct instance
            "postgres://localhost/uri_logs",  # Custom URI
        ]
    )

    logger.info("Message sent to all three sink types")

    print()


def demonstrate_environment_integration():
    """Demonstrate environment variable configuration."""
    print("=== Environment Variable Integration ===")

    # Set environment variable
    import os

    os.environ["FAPILOG_SINKS"] = (
        "postgres://localhost/env_logs,mongodb://localhost/env_logs"
    )

    # Configure using environment variables
    logger = configure_logging()  # Will read from FAPILOG_SINKS
    logger.info("Test message from environment-configured sinks")

    # Clean up
    del os.environ["FAPILOG_SINKS"]

    print()


def demonstrate_error_handling():
    """Demonstrate error handling for invalid configurations."""
    print("=== Error Handling Demonstration ===")

    # Try to use an unregistered sink
    try:
        configure_logging(sinks=["redis://localhost/logs"])
    except Exception as e:
        print(f"✓ Caught error for unregistered sink: {e}")

    # Try invalid URI format
    try:
        configure_logging(sinks=["not-a-valid-uri"])
    except Exception as e:
        print(f"✓ Caught error for invalid URI: {e}")

    print()


def demonstrate_dynamic_registration():
    """Demonstrate dynamic sink registration at runtime."""
    print("=== Dynamic Registration ===")

    # Register a sink dynamically
    class CustomSink(Sink):
        def __init__(self, name="dynamic", **kwargs):
            super().__init__()
            self.name = name
            self.kwargs = kwargs
            print(f"Dynamic sink '{name}' created with: {kwargs}")

        async def write(self, event_dict: Dict[str, Any]) -> None:
            print(f"[{self.name.upper()}] {json.dumps(event_dict, default=str)}")

    # Register at runtime
    SinkRegistry.register("custom", CustomSink)

    # Use the dynamically registered sink
    logger = configure_logging(sinks=["custom://example?name=runtime_sink"])
    logger.info("Message from dynamically registered sink")

    print()


async def main():
    """Main demonstration function."""
    print("🔗 Custom Sink Registry and URI Integration Example\n")
    print("This example shows how to register custom sinks and use them via URIs.\n")

    # Show what sinks are available
    demonstrate_registry_discovery()

    # Basic URI configuration
    demonstrate_uri_configuration()

    # Mixed configuration (built-in + custom + direct instances)
    demonstrate_mixed_configuration()

    # Environment variable integration
    demonstrate_environment_integration()

    # Error handling
    demonstrate_error_handling()

    # Dynamic registration
    demonstrate_dynamic_registration()

    print("=== Summary ===")
    print("✅ Custom sinks registered with @register_sink decorator")
    print("✅ URI-based configuration (postgres://host/db?param=value)")
    print("✅ Environment variable support (FAPILOG_SINKS)")
    print("✅ Mixed sink types (built-in + custom + direct instances)")
    print("✅ Comprehensive error handling")
    print("✅ Dynamic registration capabilities")
    print("✅ Backward compatibility maintained")

    print("\n📖 Usage patterns:")
    print("# Environment variable")
    print("export FAPILOG_SINKS=postgres://localhost/logs,stdout")
    print()
    print("# Programmatic configuration")
    print("configure_logging(sinks=['postgres://localhost/logs'])")
    print()
    print("# Mixed types")
    print("configure_logging(sinks=[custom_sink_instance, 'stdout', 'postgres://...'])")


if __name__ == "__main__":
    asyncio.run(main())
