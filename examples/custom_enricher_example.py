#!/usr/bin/env python3
"""
Example demonstrating custom enrichers in fapilog.

This example shows how to register custom enrichers to inject
application-specific metadata into log events.
"""

from fapilog import configure_logging, log
from fapilog.enrichers import clear_enrichers, register_enricher
from fapilog.utils.context import get_context


def tenant_enricher(logger, method_name, event_dict):
    """Add tenant ID to all log events."""
    # In a real application, you might get this from request headers,
    # JWT tokens, or database context
    event_dict["tenant_id"] = "tenant_123"
    return event_dict


def session_enricher(logger, method_name, event_dict):
    """Add session ID to all log events."""
    # In a real application, you might get this from session cookies
    # or authentication context
    event_dict["session_id"] = "session_456"
    return event_dict


def user_context_enricher(logger, method_name, event_dict):
    """Add user context from request headers."""
    context = get_context()
    user_id = context.get("user_id")
    if user_id:
        event_dict["user_id"] = user_id
    return event_dict


def environment_enricher(logger, method_name, event_dict):
    """Add environment information to all log events."""
    import os

    event_dict["environment"] = os.getenv("ENVIRONMENT", "development")
    event_dict["service_name"] = "my-fastapi-app"
    return event_dict


def main():
    """Demonstrate custom enrichers."""
    print("=== Custom Enricher Example ===\n")

    # Clear any existing enrichers for clean state
    clear_enrichers()

    # Register custom enrichers
    register_enricher(tenant_enricher)
    register_enricher(session_enricher)
    register_enricher(user_context_enricher)
    register_enricher(environment_enricher)

    # Configure logging
    configure_logging()

    print("Registered enrichers:")
    print("- tenant_enricher: Adds tenant_id")
    print("- session_enricher: Adds session_id")
    print("- user_context_enricher: Adds user_id from context")
    print("- environment_enricher: Adds environment and service_name")
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
    print("Custom enrichers are called at the end of the processor chain,")
    print("after all built-in enrichers (hostname, pid, trace_id, etc.).")


if __name__ == "__main__":
    main()
