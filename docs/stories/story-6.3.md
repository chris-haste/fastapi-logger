Story 6.3 – Context Enricher: User and Auth Context  
───────────────────────────────────  
Epic: 6 – Contextual Enrichers  
Sprint Target: Sprint #⟪next⟫  
Story Points: 5

**As a FastAPI developer**  
I want logs to include authenticated user information (e.g., user ID, roles)  
So that I can attribute actions and errors to specific users.

───────────────────────────────────  
Acceptance Criteria

- A `UserContextEnricher` is implemented and hooks into FastAPI dependency injection
- Captures user ID and optional roles/scopes from request context
- Adds fields like `user_id`, `user_roles`, `auth_scheme` to the log context
- Works with custom or standard auth backends
- User info is included in all log events during the request lifecycle
- Fallbacks gracefully when no user is authenticated (e.g., `user_id = null`)
- Unit tests confirm enrichment, null behavior, and isolation between requests
- README documents integration and field names

───────────────────────────────────  
Tasks / Technical Checklist

1. Implement `UserContextEnricher` using FastAPI dependencies:

   - Create a `get_current_user()` dependency wrapper
   - Extract user info (ID, roles/scopes, auth scheme)
   - Inject into `contextvars`

2. Middleware augments existing log context with user info if available

   - Add `user_id`, `user_roles`, and `auth_scheme` to structured logs

3. Update settings (`fapilog/settings.py`):

   - Optional field for `USER_CONTEXT_ENABLED` (default: True)
   - Optional user model path override for advanced use

4. Unit tests in `tests/test_user_context.py`:

   - `test_authenticated_user_fields_present()`
   - `test_unauthenticated_request_yields_null_user()`
   - `test_roles_and_scheme_extraction()`

5. Update README:
   - Show how to use the provided dependency in FastAPI routes
   - List user fields injected into logs
   - Mention null-safe behavior for unauthenticated requests

───────────────────────────────────  
Dependencies / Notes

- Designed to work with any FastAPI-compatible authentication mechanism
- Should be decoupled from specific auth providers (OAuth2, JWT, etc.)

───────────────────────────────────  
Definition of Done  
✓ User context injected into per-request log context  
✓ Works with or without authentication  
✓ Fully tested and documented  
✓ PR merged to **main** with reviewer approval  
✓ `CHANGELOG.md` and README updated under _Unreleased → Added_
