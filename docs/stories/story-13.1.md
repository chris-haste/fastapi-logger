# Story 13.1 – Eliminate Global State and Implement Dependency Injection

**Epic:** 13 – Architecture Improvements  
Sprint Target: Sprint #⟪next⟫  
Story Points: 13

**As a library maintainer**  
I want to eliminate global state and implement proper dependency injection  
So that the library is more testable, thread-safe, and follows clean architecture principles.

───────────────────────────────────  
Acceptance Criteria

- Global variables `_configured` and `_queue_worker` in `bootstrap.py` are eliminated
- A `LoggingContainer` class manages all logging dependencies and lifecycle
- `configure_logging()` becomes idempotent without global state
- Multiple logging configurations can coexist in the same process (for testing)
- All existing functionality is preserved (queue workers, sinks, middleware registration)
- Thread-safety is improved with proper state management
- Unit tests can create isolated logging instances without interference
- Memory leaks are prevented with proper cleanup mechanisms
- The public API remains unchanged for backward compatibility

───────────────────────────────────  
Tasks / Technical Checklist

1. **Create `LoggingContainer` class in `src/fapilog/container.py`**:

   - Manage settings, queue worker, sinks, and configuration state
   - Implement singleton pattern with proper lifecycle management
   - Add methods for configuration, cleanup, and state access

2. **Refactor `bootstrap.py`**:

   - Remove global variables `_configured` and `_queue_worker`
   - Use `LoggingContainer` for state management
   - Maintain idempotent behavior through container state
   - Add proper cleanup methods

3. **Update `_internal/queue.py`**:

   - Remove global queue worker state
   - Use container-based worker management
   - Improve thread-safety in worker lifecycle

4. **Enhance middleware integration**:

   - Allow multiple middleware instances with different configurations
   - Improve context isolation between different logging setups

5. **Add comprehensive tests**:

   - Test multiple concurrent logging configurations
   - Verify thread-safety in multi-threaded scenarios
   - Test memory leak prevention
   - Verify backward compatibility

6. **Update documentation**:
   - Document the new container-based architecture
   - Add examples of advanced usage patterns
   - Update troubleshooting guide

───────────────────────────────────  
Dependencies / Notes

- This is a breaking change internally but maintains public API compatibility
- Requires careful testing of all existing functionality
- May impact performance slightly due to additional abstraction layer
- Should be implemented alongside Story 13.2 for maximum benefit

───────────────────────────────────  
Definition of Done  
✓ Global state eliminated from all modules  
✓ LoggingContainer manages all dependencies  
✓ Multiple configurations can coexist safely  
✓ All existing tests pass with new architecture  
✓ Thread-safety verified with concurrent tests  
✓ Memory leak tests pass  
✓ Public API remains unchanged  
✓ Documentation updated with new architecture  
✓ PR merged to **main** with reviewer approval and green CI  
✓ `CHANGELOG.md` updated under _Unreleased → Changed_

───────────────────────────────────  
**CURRENT STATUS: PARTIALLY COMPLETED**

**Completed Tasks:**

- ✅ Eliminated global state in `httpx_patch.py` by creating `HttpxTracePropagation` class
- ✅ Improved state management with class-based approach
- ✅ Better testability through encapsulation

**Remaining Tasks:**

- ❌ Global variables `_configured` and `_queue_worker` in `bootstrap.py` still exist
- ❌ Need to create `LoggingContainer` class
- ❌ Need to implement proper dependency injection pattern
- ❌ Update `_internal/queue.py` to remove global state
- ❌ Add comprehensive tests for multiple configurations
- ❌ Update documentation
