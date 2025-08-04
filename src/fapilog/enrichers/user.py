"""User context enrichers for fapilog."""

import asyncio
from typing import Any, Callable, Dict

from ..utils.context import get_context


def user_context_enricher(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Enrich log events with user authentication context.

    This processor reads user context variables and adds user authentication
    metadata to every event:
    - user_id: Authenticated user identifier
    - user_roles: List of user roles/scopes
    - auth_scheme: Authentication scheme (e.g., 'Bearer', 'Basic')

    Fields are only added if not already present in the event_dict,
    allowing manual override of these values. If no user is authenticated,
    the fields will be null.

    Args:
        logger: The logger instance
        method_name: The logging method name
        event_dict: The event dictionary to enrich

    Returns:
        The enriched event dictionary
    """
    context = get_context()

    # Add user_id if not already present and available in context
    if "user_id" not in event_dict:
        user_id = context.get("user_id")
        if user_id is not None:
            event_dict["user_id"] = user_id

    # Add user_roles if not already present and available in context
    if "user_roles" not in event_dict:
        user_roles = context.get("user_roles")
        if user_roles is not None:
            event_dict["user_roles"] = user_roles

    # Add auth_scheme if not already present and available in context
    if "auth_scheme" not in event_dict:
        auth_scheme = context.get("auth_scheme")
        if auth_scheme is not None:
            event_dict["auth_scheme"] = auth_scheme

    return event_dict


def create_user_dependency(get_user_func: Callable[..., Any]) -> Callable[..., Any]:
    """Create a FastAPI dependency that extracts user context and binds it.

    This factory function creates a FastAPI dependency that wraps your existing
    user authentication logic and automatically binds user context variables
    for logging enrichment.

    Args:
        get_user_func: Your existing FastAPI dependency function that returns
                      user information. This should be a callable that returns
                      a user object or dict with user information.

    Returns:
        A FastAPI dependency function that binds user context and returns
        the user object.

    Example:
        ```python
        from fastapi import Depends, HTTPException
        from fastapi.security import HTTPBearer
        from fapilog.enrichers import create_user_dependency

        security = HTTPBearer()

        def get_current_user_base(token: str = Depends(security)):
            # Your authentication logic here
            if not validate_token(token):
                raise HTTPException(401, "Invalid token")
            return {
                "user_id": "123",
                "roles": ["admin", "user"],
                "auth_scheme": "Bearer"
            }

        # Create the logging-aware dependency
        get_current_user = create_user_dependency(get_current_user_base)

        @app.get("/protected")
        async def protected_route(user = Depends(get_current_user)):
            # All logs in this request will automatically include user context
            log.info("Protected action", action="view_profile")
            return {"user": user}
        ```
    """
    from ..utils.context import bind_user_context

    async def user_dependency(*args: Any, **kwargs: Any) -> Any:
        """FastAPI dependency that extracts and binds user context."""
        # Call the original user function
        if asyncio.iscoroutinefunction(get_user_func):
            user = await get_user_func(*args, **kwargs)
        else:
            user = get_user_func(*args, **kwargs)

        # Extract user context from user object
        if user is not None:
            user_id = None
            user_roles = None
            auth_scheme = None

            # Handle different user object types
            if isinstance(user, dict):
                user_id = user.get("user_id") or user.get("id")
                user_roles = user.get("user_roles") or user.get("roles")
                auth_scheme = user.get("auth_scheme") or user.get("scheme")
            else:
                # Handle user objects with attributes
                user_id = getattr(user, "user_id", None) or getattr(user, "id", None)
                user_roles = getattr(user, "user_roles", None) or getattr(
                    user, "roles", None
                )
                auth_scheme = getattr(user, "auth_scheme", None) or getattr(
                    user, "scheme", None
                )

            # Convert user_id to string if it's not None
            if user_id is not None:
                user_id = str(user_id)

            # Ensure user_roles is a list if present
            if user_roles is not None and not isinstance(user_roles, list):
                if isinstance(user_roles, str):
                    user_roles = [user_roles]
                else:
                    # Try to convert iterable to list
                    try:
                        user_roles = list(user_roles)
                    except (TypeError, ValueError):
                        user_roles = [str(user_roles)]

            # Bind user context for logging enrichment
            bind_user_context(
                user_id=user_id,
                user_roles=user_roles,
                auth_scheme=auth_scheme,
            )

        return user

    return user_dependency
