# Story 100.3 – Shared Connection Pool Management

**Epic:** 100 – Processing Performance Optimization  
Sprint Target: Sprint #⟪next⟫  
Story Points: 8

**As a resource-conscious developer**  
I want enrichers and sinks to share connection pools efficiently  
So that resource usage is optimized and connection limits are respected across the pipeline.

───────────────────────────────────  
Acceptance Criteria

- [ ] Shared HTTP connection pools for enrichers accessing external APIs
- [ ] Database connection pooling for enrichers that query databases
- [ ] Connection pool lifecycle managed by container architecture
- [ ] Resource limits enforced across all enrichers and sinks
- [ ] Connection health checking and automatic recovery
- [ ] Graceful degradation when connection pools are exhausted
- [ ] Metrics for connection pool utilization and performance
- [ ] Memory usage reduced through efficient connection reuse
- [ ] Configuration options for pool sizing and timeout settings

───────────────────────────────────  
Tasks / Technical Checklist

1. **Create connection pool manager in `src/fapilog/_internal/connection_pools.py`**:

   - Implement `ConnectionPoolManager` with HTTP and database pools
   - Add pool configuration (max connections, timeouts, retry settings)
   - Implement pool lifecycle management (startup, shutdown, health checks)
   - Support multiple pool types (HTTP, PostgreSQL, Redis, etc.)

2. **Integrate with container architecture in `src/fapilog/container.py`**:

   - Add connection pool initialization to `LoggingContainer`
   - Manage pool lifecycle alongside other container resources
   - Provide pool access methods for enrichers and sinks
   - Implement proper cleanup during container shutdown

3. **Update async enrichers in `src/fapilog/_internal/async_enricher.py`**:

   - Replace individual connections with shared pool access
   - Add `get_connection_pool()` method to base enricher class
   - Implement connection borrowing and returning patterns
   - Add fallback handling when pools are unavailable

4. **Enhance HTTP-based sinks (Loki) in `src/fapilog/sinks/loki.py`**:

   - Use shared HTTP connection pools instead of individual clients
   - Implement pool-aware retry logic and error handling
   - Add connection pool metrics for sink operations
   - Optimize batch processing with pooled connections

5. **Add connection pool configuration to settings**:

   - Extend `LoggingSettings` with connection pool options
   - Add environment variable mapping for pool configuration
   - Implement validation for pool size and timeout settings
   - Support per-pool-type configuration (HTTP vs database)

6. **Implement connection pool metrics**:

   - Track pool utilization, queue depth, and connection lifecycle
   - Monitor connection success/failure rates and latency
   - Add health check metrics for pool status
   - Integrate with existing metrics collection system

7. **Create connection pool testing framework**:

   - Mock pools for unit testing enrichers and sinks
   - Load testing tools for connection pool performance
   - Health check simulation and recovery testing
   - Memory leak detection for pooled connections

───────────────────────────────────  
Dev Notes

**Current Resource Usage:**
```python
# Individual connections per enricher/sink
class LokiSink:
    def __init__(self, ...):
        self._client = httpx.AsyncClient(timeout=self.timeout)

class AsyncEnricher:
    async def _startup(self):
        self._session = httpx.AsyncClient()
```

**Target Architecture:**
```python
# Shared connection pools
class ConnectionPoolManager:
    def __init__(self):
        self.http_pool = httpx.AsyncClient(
            limits=httpx.Limits(max_connections=100)
        )
        self.db_pools = {...}
    
    async def get_http_client(self) -> httpx.AsyncClient:
        return self.http_pool
```

**Dependencies:**
- Container architecture for lifecycle management
- Settings system for pool configuration
- Metrics collection for monitoring
- Async enricher and sink implementations

**Performance Impact:**
- 50-70% reduction in connection overhead
- Better handling of connection limits and rate limiting
- Improved resource utilization across pipeline components
- Faster enricher/sink startup through shared resources

**Resource Benefits:**
- Reduced memory footprint from connection reuse
- Better connection limit management for external services
- Improved startup time for enrichers and sinks
- Centralized connection health monitoring

───────────────────────────────────  
Testing

**Unit Tests:**
- Connection pool lifecycle management
- Pool exhaustion and recovery scenarios
- Connection borrowing and returning patterns
- Health check functionality and fallback behavior

**Integration Tests:**
- End-to-end pipeline with shared connection pools
- Multiple enrichers/sinks using same connection pools
- Pool configuration and environment variable handling
- Memory usage validation under sustained load

**Performance Tests:**
- Connection pool utilization under various load patterns
- Latency comparison: individual vs shared connections
- Memory usage profiling for pooled vs individual connections
- Throughput testing with connection pool constraints

**Load Tests:**
- Pool exhaustion scenarios and graceful degradation
- Connection recovery after network failures
- Concurrent access patterns from multiple enrichers
- Resource limit enforcement and backpressure handling

───────────────────────────────────  
Status: **Not Started**

**Dev Agent Record**

- **Agent Model Used:** N/A
- **Debug Log References:** N/A  
- **Completion Notes:** N/A
- **File List:** N/A
- **Change Log:** N/A 