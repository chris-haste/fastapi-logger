# Story 16.2 – Implement Async Enricher Support and Lifecycle Management

**Epic:** 16 – Enricher Architecture Improvements  
Sprint Target: Sprint #⟪next⟫  
Story Points: 5

**As a developer**  
I want full async support for enrichers with lifecycle management  
So that I can perform database lookups, API calls, and resource management in enrichers safely.

───────────────────────────────────  
Acceptance Criteria

- Full async/await support for enrichers alongside existing sync enrichers
- Enricher lifecycle management (startup, shutdown, health checks)
- Connection pooling and resource management for enrichers
- Async context propagation and timeout handling
- Caching layer for expensive enricher operations
- Graceful degradation when async enrichers fail
- Performance monitoring for async enricher operations
- Circuit breaker pattern for external service calls

───────────────────────────────────  
Tasks / Technical Checklist

1. **Implement Async Enricher Interface in `src/fapilog/_internal/async_enricher.py`**:

   ```python
   from abc import ABC, abstractmethod
   from typing import Dict, Any, Optional
   import asyncio
   from contextlib import asynccontextmanager

   class AsyncEnricher(ABC):
       """Base class for async enrichers with lifecycle management."""

       def __init__(self, name: str, **kwargs):
           self.name = name
           self.is_started = False
           self.is_healthy = True
           self._lock = asyncio.Lock()
           self._session = None
           self._connection_pool = None

       async def startup(self) -> None:
           """Initialize enricher resources (connections, pools, etc.)."""
           if self.is_started:
               return
           
           async with self._lock:
               if not self.is_started:
                   await self._startup()
                   self.is_started = True

       async def shutdown(self) -> None:
           """Clean up enricher resources."""
           if not self.is_started:
               return
           
           async with self._lock:
               if self.is_started:
                   await self._shutdown()
                   self.is_started = False

       async def health_check(self) -> bool:
           """Check if enricher is healthy and responsive."""
           try:
               return await self._health_check()
           except Exception:
               self.is_healthy = False
               return False

       @abstractmethod
       async def _startup(self) -> None:
           """Override to implement startup logic."""
           pass

       @abstractmethod
       async def _shutdown(self) -> None:
           """Override to implement shutdown logic."""
           pass

       @abstractmethod
       async def _health_check(self) -> bool:
           """Override to implement health check logic."""
           pass

       @abstractmethod
       async def enrich_async(self, logger: Any, method_name: str, 
                             event_dict: Dict[str, Any]) -> Dict[str, Any]:
           """Override to implement enrichment logic."""
           pass

       async def __call__(self, logger: Any, method_name: str, 
                         event_dict: Dict[str, Any]) -> Dict[str, Any]:
           """Main enricher entry point with error handling."""
           if not self.is_started:
               await self.startup()
           
           if not self.is_healthy:
               # Skip enrichment if unhealthy
               return event_dict
           
           try:
               return await self.enrich_async(logger, method_name, event_dict)
           except Exception as e:
               # Log error but don't break pipeline
               import logging
               enricher_logger = logging.getLogger(__name__)
               enricher_logger.debug(
                   f"Async enricher {self.name} failed: {e}",
                   exc_info=True
               )
               self.is_healthy = False
               return event_dict
   ```

2. **Add Async Pipeline Processor in `src/fapilog/_internal/async_pipeline.py`**:

   ```python
   import asyncio
   from typing import Dict, Any, List, Callable, Union

   class AsyncEnricherProcessor:
       """Processor that handles both sync and async enrichers."""

       def __init__(self, enrichers: List[Union[Callable, AsyncEnricher]], 
                   timeout: float = 5.0):
           self.enrichers = enrichers
           self.timeout = timeout
           self._async_enrichers = [e for e in enrichers if isinstance(e, AsyncEnricher)]
           self._sync_enrichers = [e for e in enrichers if not isinstance(e, AsyncEnricher)]

       async def startup(self) -> None:
           """Start all async enrichers."""
           startup_tasks = [enricher.startup() for enricher in self._async_enrichers]
           if startup_tasks:
               await asyncio.gather(*startup_tasks, return_exceptions=True)

       async def shutdown(self) -> None:
           """Shutdown all async enrichers."""
           shutdown_tasks = [enricher.shutdown() for enricher in self._async_enrichers]
           if shutdown_tasks:
               await asyncio.gather(*shutdown_tasks, return_exceptions=True)

       def __call__(self, logger: Any, method_name: str, 
                   event_dict: Dict[str, Any]) -> Dict[str, Any]:
           """Process event through both sync and async enrichers."""
           
           # Process sync enrichers first
           result = event_dict
           for enricher in self._sync_enrichers:
               try:
                   result = enricher(logger, method_name, result)
               except Exception as e:
                   import logging
                   enricher_logger = logging.getLogger(__name__)
                   enricher_logger.debug(f"Sync enricher failed: {e}", exc_info=True)

           # Process async enrichers if any
           if self._async_enrichers:
               try:
                   loop = asyncio.get_event_loop()
                   if loop.is_running():
                       # Create a task and get result with timeout
                       task = asyncio.create_task(
                           self._process_async_enrichers(logger, method_name, result)
                       )
                       # Use asyncio.wait_for with timeout
                       result = asyncio.run_coroutine_threadsafe(
                           asyncio.wait_for(task, timeout=self.timeout), loop
                       ).result()
                   else:
                       # Create new event loop
                       result = asyncio.run(
                           asyncio.wait_for(
                               self._process_async_enrichers(logger, method_name, result),
                               timeout=self.timeout
                           )
                       )
               except asyncio.TimeoutError:
                   import logging
                   enricher_logger = logging.getLogger(__name__)
                   enricher_logger.warning(f"Async enrichers timed out after {self.timeout}s")
               except Exception as e:
                   import logging
                   enricher_logger = logging.getLogger(__name__)
                   enricher_logger.debug(f"Async enricher processing failed: {e}", exc_info=True)

           return result

       async def _process_async_enrichers(self, logger: Any, method_name: str, 
                                         event_dict: Dict[str, Any]) -> Dict[str, Any]:
           """Process async enrichers concurrently."""
           result = event_dict
           
           # Process async enrichers sequentially to maintain order
           for enricher in self._async_enrichers:
               try:
                   result = await enricher(logger, method_name, result)
               except Exception as e:
                   import logging
                   enricher_logger = logging.getLogger(__name__)
                   enricher_logger.debug(f"Async enricher {enricher.name} failed: {e}", exc_info=True)
           
           return result
   ```

3. **Add Caching Support in `src/fapilog/_internal/enricher_cache.py`**:

   ```python
   import asyncio
   import time
   from typing import Dict, Any, Optional, Callable, Hashable
   from functools import wraps

   class EnricherCache:
       """Cache for expensive enricher operations."""

       def __init__(self, max_size: int = 1000, ttl: float = 300.0):
           self.max_size = max_size
           self.ttl = ttl
           self._cache: Dict[Hashable, tuple] = {}
           self._access_times: Dict[Hashable, float] = {}
           self._lock = asyncio.Lock()

       async def get(self, key: Hashable) -> Optional[Any]:
           """Get cached value if not expired."""
           async with self._lock:
               if key in self._cache:
                   value, timestamp = self._cache[key]
                   if time.time() - timestamp < self.ttl:
                       self._access_times[key] = time.time()
                       return value
                   else:
                       # Expired
                       del self._cache[key]
                       del self._access_times[key]
               return None

       async def set(self, key: Hashable, value: Any) -> None:
           """Set cached value with eviction if needed."""
           async with self._lock:
               current_time = time.time()
               
               # Evict expired entries
               expired_keys = [
                   k for k, (_, ts) in self._cache.items()
                   if current_time - ts >= self.ttl
               ]
               for k in expired_keys:
                   del self._cache[k]
                   del self._access_times[k]
               
               # Evict LRU if at capacity
               if len(self._cache) >= self.max_size:
                   lru_key = min(self._access_times.keys(), key=self._access_times.get)
                   del self._cache[lru_key]
                   del self._access_times[lru_key]
               
               self._cache[key] = (value, current_time)
               self._access_times[key] = current_time

       def cache_key(self, *args, **kwargs) -> str:
           """Generate cache key from arguments."""
           import hashlib
           import json
           
           # Create deterministic key from arguments
           key_data = {
               'args': args,
               'kwargs': sorted(kwargs.items())
           }
           key_str = json.dumps(key_data, sort_keys=True, default=str)
           return hashlib.md5(key_str.encode()).hexdigest()

   def cached_enricher(cache: EnricherCache, key_func: Optional[Callable] = None):
       """Decorator for caching enricher results."""
       def decorator(func: Callable) -> Callable:
           @wraps(func)
           async def wrapper(*args, **kwargs):
               # Generate cache key
               if key_func:
                   cache_key = key_func(*args, **kwargs)
               else:
                   cache_key = cache.cache_key(*args, **kwargs)
               
               # Try to get from cache
               cached_result = await cache.get(cache_key)
               if cached_result is not None:
                   return cached_result
               
               # Execute function and cache result
               result = await func(*args, **kwargs)
               await cache.set(cache_key, result)
               return result
           
           return wrapper
       return decorator
   ```

4. **Implement Circuit Breaker in `src/fapilog/_internal/circuit_breaker.py`**:

   ```python
   import asyncio
   import time
   from enum import Enum
   from typing import Callable, Any, Optional

   class CircuitState(Enum):
       CLOSED = "closed"
       OPEN = "open"
       HALF_OPEN = "half_open"

   class CircuitBreaker:
       """Circuit breaker for protecting against failing enrichers."""

       def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0,
                   expected_exception: type = Exception):
           self.failure_threshold = failure_threshold
           self.recovery_timeout = recovery_timeout
           self.expected_exception = expected_exception
           
           self.failure_count = 0
           self.last_failure_time: Optional[float] = None
           self.state = CircuitState.CLOSED
           self._lock = asyncio.Lock()

       async def call(self, func: Callable, *args, **kwargs) -> Any:
           """Execute function with circuit breaker protection."""
           async with self._lock:
               if self.state == CircuitState.OPEN:
                   if self._should_attempt_reset():
                       self.state = CircuitState.HALF_OPEN
                   else:
                       raise CircuitBreakerOpenError(
                           f"Circuit breaker is open. Last failure: {self.last_failure_time}"
                       )

           try:
               result = await func(*args, **kwargs)
               await self._on_success()
               return result
           except self.expected_exception as e:
               await self._on_failure()
               raise

       def _should_attempt_reset(self) -> bool:
           """Check if we should attempt to reset the circuit breaker."""
           return (
               self.last_failure_time is not None and
               time.time() - self.last_failure_time >= self.recovery_timeout
           )

       async def _on_success(self) -> None:
           """Handle successful call."""
           async with self._lock:
               self.failure_count = 0
               self.state = CircuitState.CLOSED

       async def _on_failure(self) -> None:
           """Handle failed call."""
           async with self._lock:
               self.failure_count += 1
               self.last_failure_time = time.time()
               
               if self.failure_count >= self.failure_threshold:
                   self.state = CircuitState.OPEN

   class CircuitBreakerOpenError(Exception):
       """Raised when circuit breaker is open."""
       pass
   ```

5. **Create Example Async Enrichers in `examples/async_enricher_examples.py`**:

   ```python
   import aiohttp
   import aioredis
   import asyncpg
   from fapilog._internal.async_enricher import AsyncEnricher
   from fapilog._internal.enricher_cache import EnricherCache, cached_enricher
   from fapilog._internal.circuit_breaker import CircuitBreaker

   class DatabaseUserEnricher(AsyncEnricher):
       """Enrich with user data from PostgreSQL database."""

       def __init__(self, database_url: str, **kwargs):
           super().__init__("database_user", **kwargs)
           self.database_url = database_url
           self.pool = None
           self.cache = EnricherCache(max_size=1000, ttl=300)
           self.circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)

       async def _startup(self) -> None:
           """Initialize database connection pool."""
           self.pool = await asyncpg.create_pool(
               self.database_url,
               min_size=2,
               max_size=10,
               command_timeout=5
           )

       async def _shutdown(self) -> None:
           """Close database connection pool."""
           if self.pool:
               await self.pool.close()

       async def _health_check(self) -> bool:
           """Check database connectivity."""
           if not self.pool:
               return False
           
           try:
               async with self.pool.acquire() as conn:
                   await conn.fetchval("SELECT 1")
               return True
           except Exception:
               return False

       @cached_enricher(cache=None)  # Will use self.cache
       async def _fetch_user_data(self, user_id: str) -> dict:
           """Fetch user data with caching and circuit breaker."""
           async def fetch():
               async with self.pool.acquire() as conn:
                   row = await conn.fetchrow(
                       "SELECT name, email, department FROM users WHERE id = $1",
                       user_id
                   )
                   return dict(row) if row else {}
           
           return await self.circuit_breaker.call(fetch)

       async def enrich_async(self, logger: Any, method_name: str, 
                             event_dict: Dict[str, Any]) -> Dict[str, Any]:
           """Enrich with user data from database."""
           user_id = event_dict.get('user_id')
           if not user_id:
               return event_dict

           try:
               # Use cache key from user_id
               cache_key = f"user:{user_id}"
               cached_data = await self.cache.get(cache_key)
               
               if cached_data is not None:
                   event_dict.update(cached_data)
               else:
                   user_data = await self._fetch_user_data(user_id)
                   if user_data:
                       await self.cache.set(cache_key, user_data)
                       event_dict.update(user_data)
           except Exception as e:
               event_dict['user_enrichment_error'] = str(e)

           return event_dict

   class APIServiceEnricher(AsyncEnricher):
       """Enrich with data from external API service."""

       def __init__(self, api_base_url: str, api_key: str, **kwargs):
           super().__init__("api_service", **kwargs)
           self.api_base_url = api_base_url
           self.api_key = api_key
           self.session = None
           self.circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

       async def _startup(self) -> None:
           """Initialize HTTP session."""
           timeout = aiohttp.ClientTimeout(total=10, connect=5)
           self.session = aiohttp.ClientSession(
               timeout=timeout,
               headers={"Authorization": f"Bearer {self.api_key}"}
           )

       async def _shutdown(self) -> None:
           """Close HTTP session."""
           if self.session:
               await self.session.close()

       async def _health_check(self) -> bool:
           """Check API service health."""
           try:
               async with self.session.get(f"{self.api_base_url}/health") as response:
                   return response.status == 200
           except Exception:
               return False

       async def enrich_async(self, logger: Any, method_name: str, 
                             event_dict: Dict[str, Any]) -> Dict[str, Any]:
           """Enrich with data from API service."""
           request_id = event_dict.get('request_id')
           if not request_id:
               return event_dict

           async def fetch_request_data():
               async with self.session.get(
                   f"{self.api_base_url}/requests/{request_id}"
               ) as response:
                   if response.status == 200:
                       return await response.json()
                   return {}

           try:
               data = await self.circuit_breaker.call(fetch_request_data)
               if data:
                   event_dict['request_context'] = data
           except Exception as e:
               event_dict['api_enrichment_error'] = str(e)

           return event_dict

   # Usage example
   database_enricher = DatabaseUserEnricher(
       database_url="postgresql://user:pass@localhost/db"
   )

   api_enricher = APIServiceEnricher(
       api_base_url="https://api.company.com",
       api_key="your-api-key"
   )

   # Configure with async enrichers
   configure_logging(async_enrichers=[database_enricher, api_enricher])
   ```

6. **Add Lifecycle Management in `src/fapilog/_internal/enricher_lifecycle.py`**:

   ```python
   import asyncio
   import atexit
   from typing import List, Dict, Any
   from contextlib import asynccontextmanager

   class EnricherLifecycleManager:
       """Manages lifecycle of async enrichers."""

       def __init__(self):
           self.enrichers: List[AsyncEnricher] = []
           self.is_started = False
           self._shutdown_registered = False

       def register_enricher(self, enricher: AsyncEnricher) -> None:
           """Register an async enricher for lifecycle management."""
           self.enrichers.append(enricher)
           if not self._shutdown_registered:
               atexit.register(self._sync_shutdown)
               self._shutdown_registered = True

       async def startup_all(self) -> None:
           """Start all registered enrichers."""
           if self.is_started:
               return

           startup_tasks = []
           for enricher in self.enrichers:
               startup_tasks.append(enricher.startup())

           if startup_tasks:
               results = await asyncio.gather(*startup_tasks, return_exceptions=True)
               for i, result in enumerate(results):
                   if isinstance(result, Exception):
                       import logging
                       logger = logging.getLogger(__name__)
                       logger.error(
                           f"Failed to start enricher {self.enrichers[i].name}: {result}"
                       )

           self.is_started = True

       async def shutdown_all(self) -> None:
           """Shutdown all registered enrichers."""
           if not self.is_started:
               return

           shutdown_tasks = []
           for enricher in self.enrichers:
               shutdown_tasks.append(enricher.shutdown())

           if shutdown_tasks:
               await asyncio.gather(*shutdown_tasks, return_exceptions=True)

           self.is_started = False

       async def health_check_all(self) -> Dict[str, bool]:
           """Health check all enrichers."""
           health_tasks = []
           for enricher in self.enrichers:
               health_tasks.append(enricher.health_check())

           if not health_tasks:
               return {}

           results = await asyncio.gather(*health_tasks, return_exceptions=True)
           return {
               enricher.name: result if isinstance(result, bool) else False
               for enricher, result in zip(self.enrichers, results)
           }

       def _sync_shutdown(self) -> None:
           """Synchronous shutdown for atexit."""
           if self.is_started:
               try:
                   loop = asyncio.get_event_loop()
                   if loop.is_running():
                       # Create a task for shutdown
                       asyncio.create_task(self.shutdown_all())
                   else:
                       asyncio.run(self.shutdown_all())
               except Exception:
                   pass  # Best effort shutdown

       @asynccontextmanager
       async def managed_enrichers(self):
           """Context manager for enricher lifecycle."""
           try:
               await self.startup_all()
               yield self
           finally:
               await self.shutdown_all()

   # Global lifecycle manager
   lifecycle_manager = EnricherLifecycleManager()
   ```

7. **Add Comprehensive Tests in `tests/test_async_enrichers.py`**:

   - Test async enricher startup and shutdown
   - Test async enricher error handling and fallback
   - Test caching functionality with TTL
   - Test circuit breaker behavior
   - Test lifecycle management
   - Test mixed sync/async enricher processing
   - Test timeout handling
   - Test health checks

───────────────────────────────────  
Dependencies / Notes

- Depends on Story 16.1 for enhanced enricher registry
- Should maintain compatibility with existing sync enrichers
- Async operations should have configurable timeouts
- Connection pools should be properly managed and cleaned up
- Circuit breaker should prevent cascading failures
- Caching should be memory-efficient with TTL and LRU eviction
- Health checks should be fast and reliable

───────────────────────────────────  
Definition of Done  
✓ Async enricher interface implemented with lifecycle management  
✓ Async pipeline processor working with timeout handling  
✓ Caching layer implemented with TTL and LRU eviction  
✓ Circuit breaker pattern implemented for external services  
✓ Example async enrichers created (database, API, Redis)  
✓ Lifecycle management implemented with startup/shutdown hooks  
✓ Performance monitoring and health checks working  
✓ Comprehensive tests added with good coverage  
✓ Documentation updated with async patterns  
✓ PR merged to **main** with reviewer approval and green CI  
✓ `CHANGELOG.md` updated under _Unreleased → Added_ 