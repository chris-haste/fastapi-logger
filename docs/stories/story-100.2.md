# Story 100.2 – Event Loop Optimization for Async Enrichers

**Epic:** 100 – Processing Performance Optimization  
Sprint Target: Sprint #⟪next⟫  
Story Points: 5

**As a performance-conscious developer**  
I want async enrichers to use efficient event loop management  
So that async processing latency is reduced and resource usage is optimized.

───────────────────────────────────  
Acceptance Criteria

- [ ] Eliminate creation of new event loops for each async enricher call
- [ ] Implement shared event loop context for async enricher processing
- [ ] Reduce ThreadPoolExecutor overhead through connection pooling
- [ ] Async enricher startup/shutdown lifecycle managed efficiently
- [ ] Event loop context preserved across enricher chains
- [ ] Memory usage reduced through better async resource management
- [ ] Latency improved for async enricher execution
- [ ] Thread safety maintained with optimized async patterns
- [ ] Graceful degradation when event loop is unavailable

───────────────────────────────────  
Tasks / Technical Checklist

1. **Refactor async pipeline in `src/fapilog/_internal/async_pipeline.py`**:

   - Replace `asyncio.run()` with event loop detection and reuse
   - Implement `get_or_create_event_loop()` utility
   - Cache event loop context for enricher execution
   - Add proper cleanup for shared event loop resources

2. **Optimize ThreadPoolExecutor usage**:

   - Implement singleton thread pool for async enricher execution
   - Add configurable thread pool size based on enricher count
   - Reuse executor instances across enricher calls
   - Implement proper shutdown handling for thread pools

3. **Enhance async enricher lifecycle in `src/fapilog/_internal/async_enricher.py`**:

   - Optimize startup/shutdown to work with shared event loops
   - Add connection pool management for async enrichers
   - Implement lazy initialization for async resources
   - Cache async sessions and connection pools

4. **Update enricher lifecycle manager in `src/fapilog/_internal/enricher_lifecycle.py`**:

   - Coordinate async enricher lifecycle with shared event loops
   - Batch startup/shutdown operations for efficiency
   - Add health check optimization for async enrichers
   - Implement graceful degradation patterns

5. **Add async context management**:

   - Create `AsyncEnricherContext` for managing async resources
   - Implement context variables for enricher execution state
   - Add async-aware error handling and recovery
   - Optimize timeout handling across enricher chains

6. **Performance monitoring and metrics**:

   - Track event loop creation/reuse statistics
   - Monitor thread pool utilization and efficiency
   - Measure latency improvements from optimization
   - Add async resource usage metrics

───────────────────────────────────  
Dev Notes

**Current Inefficiency:**
```python
# Creates new event loop for each call
def _run_async_enrichers_in_thread(self, ...):
    return asyncio.run(
        self._process_async_enrichers(logger, method_name, event_dict)
    )
```

**Target Architecture:**
```python
# Reuse event loop and thread pool
class AsyncEnricherContext:
    _event_loop = None
    _thread_pool = None
    
    @classmethod
    async def execute_enrichers(cls, enrichers, ...):
        if cls._event_loop is None:
            cls._event_loop = asyncio.get_running_loop()
        # Process with shared context
```

**Dependencies:**
- Async pipeline implementation
- Enricher lifecycle management
- Container architecture
- Metrics collection

**Performance Impact:**
- 30-50% reduction in async enricher latency
- Reduced memory overhead from event loop creation
- Better thread pool utilization
- Improved resource cleanup and lifecycle management

───────────────────────────────────  
Testing

**Unit Tests:**
- Event loop reuse across multiple enricher calls
- Thread pool lifecycle and resource management
- Async context preservation during enricher execution
- Error handling with shared async resources

**Integration Tests:**
- Full pipeline performance with optimized async processing
- Concurrent enricher execution with shared event loops
- Memory usage under sustained async enricher load
- Compatibility with existing async enricher implementations

**Performance Tests:**
- Latency comparison: before vs after optimization
- Memory usage profiling for async resource management
- Thread pool utilization and efficiency metrics
- Event loop creation frequency analysis

───────────────────────────────────  
Status: **Not Started**

**Dev Agent Record**

- **Agent Model Used:** N/A
- **Debug Log References:** N/A  
- **Completion Notes:** N/A
- **File List:** N/A
- **Change Log:** N/A 