#!/usr/bin/env python3
"""
Example demonstrating custom enrichers in fapilog.

This example shows how to register custom enrichers to inject
application-specific metadata into log events.
"""

from fapilog import configure_logging, log
from fapilog._internal.context import get_context
from fapilog.enrichers import register_enricher_advanced


@register_enricher_advanced(
    name="tenant_enricher",
    description="Add tenant ID to all log events",
    priority=100,
    async_capable=False,
)
class TenantEnricher:
    """Add tenant ID to all log events."""

    def __call__(self, logger, method_name, event_dict):
        # In a real application, you might get this from request headers,
        # JWT tokens, or database context
        event_dict["tenant_id"] = "tenant_123"
        return event_dict


@register_enricher_advanced(
    name="session_enricher",
    description="Add session ID to all log events",
    priority=110,
    async_capable=False,
)
class SessionEnricher:
    """Add session ID to all log events."""

    def __call__(self, logger, method_name, event_dict):
        # In a real application, you might get this from session cookies
        # or authentication context
        event_dict["session_id"] = "session_456"
        return event_dict


@register_enricher_advanced(
    name="user_context_enricher",
    description="Add user context from request headers",
    priority=120,
    async_capable=False,
)
class UserContextEnricher:
    """Add user context from request headers."""

    def __call__(self, logger, method_name, event_dict):
        context = get_context()
        user_id = context.get("user_id")
        if user_id:
            event_dict["user_id"] = user_id
        return event_dict


@register_enricher_advanced(
    name="environment_enricher",
    description="Add environment information to all log events",
    priority=130,
    async_capable=False,
)
class EnvironmentEnricher:
    """Add environment information to all log events."""

    def __call__(self, logger, method_name, event_dict):
        import os

        event_dict["environment"] = os.getenv("ENVIRONMENT", "development")
        event_dict["service_name"] = "my-fastapi-app"
        return event_dict


def main():
    """Demonstrate custom enrichers."""
    print("=== Custom Enricher Example ===\n")

    # Configure logging (enrichers are auto-registered via decorators)
    configure_logging()

    print("Registered enrichers (via @register_enricher_advanced decorators):")
    print("- TenantEnricher: Adds tenant_id (priority 100)")
    print("- SessionEnricher: Adds session_id (priority 110)")
    print("- UserContextEnricher: Adds user_id from context (priority 120)")
    print("- EnvironmentEnricher: Adds environment and service_name (priority 130)")
    print()

    # Log some events to see the custom fields
    print("Logging events with custom enrichers:")
    print("-" * 50)

    log.info("user_login", user_id="user_789")
    log.warning("rate_limit_exceeded", endpoint="/api/users")
    log.error("database_connection_failed", retry_count=3)

    print("\n" + "=" * 50)
    print("Notice how each log event now includes:")
    print("- tenant_id: tenant_123")
    print("- session_id: session_456")
    print("- environment: development")
    print("- service_name: my-fastapi-app")
    print("- user_id: user_789 (from context)")
    print()
    print("Custom enrichers are executed in priority order (100-130)")
    print("and integrated with built-ins (hostname, pid, trace_id, etc.).")
    print("\nNew features in @register_enricher_advanced:")
    print("- Automatic registration via decorators")
    print("- Priority-based execution order")
    print("- Metadata and descriptions")
    print("- Better error handling and lifecycle management")


if __name__ == "__main__":
    main()
