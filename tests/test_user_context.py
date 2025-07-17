"""Tests for user context enrichment functionality."""

import pytest

from fapilog._internal.context import (
    bind_user_context,
    clear_context,
    get_auth_scheme,
    get_context,
    get_user_id,
    get_user_roles,
)
from fapilog.enrichers import create_user_dependency, user_context_enricher


def test_authenticated_user_fields_present():
    """Test that user fields are present in logs when user is authenticated."""
    # Clear any existing context
    clear_context()

    # Set up user context
    bind_user_context(
        user_id="user123",
        user_roles=["admin", "user"],
        auth_scheme="Bearer",
    )

    # Create a mock event dict
    event_dict = {"event": "test_message", "level": "info"}

    # Apply the user context enricher
    enriched = user_context_enricher(None, "info", event_dict)

    # Verify user fields are added
    assert "user_id" in enriched
    assert "user_roles" in enriched
    assert "auth_scheme" in enriched

    # Verify values are correct
    assert enriched["user_id"] == "user123"
    assert enriched["user_roles"] == ["admin", "user"]
    assert enriched["auth_scheme"] == "Bearer"

    # Verify original fields are preserved
    assert enriched["event"] == "test_message"
    assert enriched["level"] == "info"


def test_unauthenticated_request_yields_null_user():
    """Test that user fields are null when no user is authenticated."""
    # Clear any existing context
    clear_context()

    # Create a mock event dict
    event_dict = {"event": "test_message", "level": "info"}

    # Apply the user context enricher
    enriched = user_context_enricher(None, "info", event_dict)

    # Verify user fields are not added when context is empty
    assert "user_id" not in enriched
    assert "user_roles" not in enriched
    assert "auth_scheme" not in enriched

    # Verify original fields are preserved
    assert enriched["event"] == "test_message"
    assert enriched["level"] == "info"


def test_roles_and_scheme_extraction():
    """Test extraction of roles and authentication scheme."""
    # Clear any existing context
    clear_context()

    # Test with different role combinations
    test_cases = [
        {
            "user_id": "user1",
            "user_roles": ["admin"],
            "auth_scheme": "Bearer",
        },
        {
            "user_id": "user2",
            "user_roles": ["user", "moderator", "admin"],
            "auth_scheme": "Basic",
        },
        {
            "user_id": "user3",
            "user_roles": [],
            "auth_scheme": "JWT",
        },
    ]

    for case in test_cases:
        # Clear context for each test
        clear_context()

        # Set up user context
        bind_user_context(**case)

        # Create event dict
        event_dict = {"event": "test_action"}

        # Apply enricher
        enriched = user_context_enricher(None, "info", event_dict)

        # Verify all fields are correctly extracted
        assert enriched["user_id"] == case["user_id"]
        assert enriched["user_roles"] == case["user_roles"]
        assert enriched["auth_scheme"] == case["auth_scheme"]


def test_user_fields_can_be_overridden():
    """Test that user fields can be overridden manually in logs."""
    # Clear any existing context
    clear_context()

    # Set up user context
    bind_user_context(
        user_id="user123",
        user_roles=["admin"],
        auth_scheme="Bearer",
    )

    # Create event dict with manual user values
    event_dict = {
        "event": "test_message",
        "user_id": "manual_user",
        "user_roles": ["manual_role"],
        "auth_scheme": "Manual",
    }

    # Apply the enricher
    enriched = user_context_enricher(None, "info", event_dict)

    # Verify manual values are preserved (not overridden)
    assert enriched["user_id"] == "manual_user"
    assert enriched["user_roles"] == ["manual_role"]
    assert enriched["auth_scheme"] == "Manual"


def test_partial_user_context():
    """Test enricher with partial user context (some fields missing)."""
    # Clear any existing context
    clear_context()

    # Set up partial user context (only user_id)
    bind_user_context(user_id="user123")

    # Create event dict
    event_dict = {"event": "test_message"}

    # Apply enricher
    enriched = user_context_enricher(None, "info", event_dict)

    # Verify only user_id is added
    assert enriched["user_id"] == "user123"
    assert "user_roles" not in enriched
    assert "auth_scheme" not in enriched


def test_context_helper_functions():
    """Test context helper functions for user data."""
    # Clear any existing context
    clear_context()

    # Initially no user context
    assert get_user_id() is None
    assert get_user_roles() is None
    assert get_auth_scheme() is None

    # Set user context
    bind_user_context(
        user_id="test_user",
        user_roles=["role1", "role2"],
        auth_scheme="Bearer",
    )

    # Verify helper functions return correct values
    assert get_user_id() == "test_user"
    assert get_user_roles() == ["role1", "role2"]
    assert get_auth_scheme() == "Bearer"

    # Clear context
    clear_context()

    # Verify helper functions return None after clearing
    assert get_user_id() is None
    assert get_user_roles() is None
    assert get_auth_scheme() is None


@pytest.mark.asyncio
async def test_create_user_dependency_with_dict_user():
    """Test create_user_dependency with dict-based user object."""

    def mock_get_user():
        return {
            "user_id": "dict_user_123",
            "roles": ["admin", "user"],
            "auth_scheme": "Bearer",
        }

    # Create the dependency
    user_dependency = create_user_dependency(mock_get_user)

    # Clear context
    clear_context()

    # Call the dependency
    user = await user_dependency()

    # Verify user is returned
    assert user["user_id"] == "dict_user_123"
    assert user["roles"] == ["admin", "user"]
    assert user["auth_scheme"] == "Bearer"

    # Verify context is set
    context = get_context()
    assert context["user_id"] == "dict_user_123"
    assert context["user_roles"] == ["admin", "user"]
    assert context["auth_scheme"] == "Bearer"


@pytest.mark.asyncio
async def test_create_user_dependency_with_object_user():
    """Test create_user_dependency with object-based user."""

    class MockUser:
        def __init__(self):
            self.id = "obj_user_456"
            self.roles = ["moderator"]
            self.scheme = "JWT"

    def mock_get_user():
        return MockUser()

    # Create the dependency
    user_dependency = create_user_dependency(mock_get_user)

    # Clear context
    clear_context()

    # Call the dependency
    user = await user_dependency()

    # Verify user is returned
    assert user.id == "obj_user_456"
    assert user.roles == ["moderator"]
    assert user.scheme == "JWT"

    # Verify context is set
    context = get_context()
    assert context["user_id"] == "obj_user_456"
    assert context["user_roles"] == ["moderator"]
    assert context["auth_scheme"] == "JWT"


@pytest.mark.asyncio
async def test_create_user_dependency_with_none_user():
    """Test create_user_dependency when user is None (unauthenticated)."""

    def mock_get_user():
        return None

    # Create the dependency
    user_dependency = create_user_dependency(mock_get_user)

    # Clear context
    clear_context()

    # Call the dependency
    user = await user_dependency()

    # Verify None is returned
    assert user is None

    # Verify context remains empty
    context = get_context()
    assert context["user_id"] is None
    assert context["user_roles"] is None
    assert context["auth_scheme"] is None


@pytest.mark.asyncio
async def test_create_user_dependency_with_async_function():
    """Test create_user_dependency with async user function."""

    async def mock_get_user_async():
        return {
            "user_id": "async_user_789",
            "roles": ["user"],
            "auth_scheme": "Bearer",
        }

    # Create the dependency
    user_dependency = create_user_dependency(mock_get_user_async)

    # Clear context
    clear_context()

    # Call the dependency
    user = await user_dependency()

    # Verify user is returned
    assert user["user_id"] == "async_user_789"
    assert user["roles"] == ["user"]
    assert user["auth_scheme"] == "Bearer"

    # Verify context is set
    context = get_context()
    assert context["user_id"] == "async_user_789"
    assert context["user_roles"] == ["user"]
    assert context["auth_scheme"] == "Bearer"


@pytest.mark.asyncio
async def test_create_user_dependency_string_role_conversion():
    """Test create_user_dependency converts string roles to list."""

    def mock_get_user():
        return {
            "user_id": "string_role_user",
            "roles": "admin",  # Single string role
            "auth_scheme": "Bearer",
        }

    # Create the dependency
    user_dependency = create_user_dependency(mock_get_user)

    # Clear context
    clear_context()

    # Call the dependency
    await user_dependency()

    # Verify context roles are converted to list
    context = get_context()
    assert context["user_id"] == "string_role_user"
    assert context["user_roles"] == ["admin"]  # Should be converted to list
    assert context["auth_scheme"] == "Bearer"


@pytest.mark.asyncio
async def test_create_user_dependency_numeric_user_id():
    """Test create_user_dependency converts numeric user_id to string."""

    def mock_get_user():
        return {
            "user_id": 12345,  # Numeric user ID
            "roles": ["user"],
            "auth_scheme": "Bearer",
        }

    # Create the dependency
    user_dependency = create_user_dependency(mock_get_user)

    # Clear context
    clear_context()

    # Call the dependency
    await user_dependency()

    # Verify context user_id is converted to string
    context = get_context()
    assert context["user_id"] == "12345"  # Should be converted to string
    assert context["user_roles"] == ["user"]
    assert context["auth_scheme"] == "Bearer"


def test_bind_user_context_function():
    """Test the bind_user_context helper function."""
    # Clear context
    clear_context()

    # Test binding individual fields
    bind_user_context(user_id="test123")
    assert get_user_id() == "test123"
    assert get_user_roles() is None
    assert get_auth_scheme() is None

    # Test binding all fields
    bind_user_context(
        user_id="full_user",
        user_roles=["admin", "user"],
        auth_scheme="Bearer",
    )
    assert get_user_id() == "full_user"
    assert get_user_roles() == ["admin", "user"]
    assert get_auth_scheme() == "Bearer"

    # Test binding with None values (should not change existing values)
    bind_user_context(user_id=None, user_roles=None, auth_scheme=None)
    assert get_user_id() == "full_user"  # Should remain unchanged
    assert get_user_roles() == ["admin", "user"]  # Should remain unchanged
    assert get_auth_scheme() == "Bearer"  # Should remain unchanged


def test_user_context_integration_in_get_context():
    """Test that user context is included in get_context() output."""
    # Clear context
    clear_context()

    # Set user context
    bind_user_context(
        user_id="integration_user",
        user_roles=["tester"],
        auth_scheme="Test",
    )

    # Get full context
    context = get_context()

    # Verify user fields are in context
    assert context["user_id"] == "integration_user"
    assert context["user_roles"] == ["tester"]
    assert context["auth_scheme"] == "Test"

    # Verify other context fields exist (even if None)
    assert "trace_id" in context
    assert "span_id" in context
    assert "method" in context
    assert "path" in context
