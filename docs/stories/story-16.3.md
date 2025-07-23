# Story 16.3 – Implement Enricher Testing Framework and Utilities

**Epic:** 16 – Enricher Architecture Improvements  
Sprint Target: Sprint #⟪next⟫  
Story Points: 3

**As a developer**  
I want comprehensive testing utilities for enrichers  
So that I can easily test and validate my custom enricher implementations.

───────────────────────────────────  
Acceptance Criteria

- Testing framework for enricher functionality and performance
- Mock enricher implementations for testing scenarios
- Performance testing helpers for enricher operations
- Debugging utilities for enricher registration and execution
- Async enricher testing support with lifecycle management
- Cache testing utilities for enricher caching behavior
- Integration testing tools for enricher dependencies
- Comprehensive testing documentation and examples

───────────────────────────────────  
Tasks / Technical Checklist

1. **Create Enricher Testing Framework in `src/fapilog/testing/enricher_testing.py`**:

   ```python
   import asyncio
   import time
   from typing import Dict, Any, List, Optional, Callable, Union
   from dataclasses import dataclass, field

   @dataclass
   class EnrichmentTestResult:
       """Result of enrichment testing."""
       input_event: Dict[str, Any]
       output_event: Dict[str, Any]
       enricher_name: str
       duration_ms: float
       success: bool
       error: Optional[str] = None
       added_fields: List[str] = field(default_factory=list)
       modified_fields: List[str] = field(default_factory=list)

   class EnricherTestFramework:
       """Framework for testing enrichers."""

       def __init__(self):
           self.test_results: List[EnrichmentTestResult] = []
           self.performance_data = {}

       def test_enricher_interface(self, enricher_class: type) -> bool:
           """Validate that an enricher class implements the required interface."""
           required_methods = ['__call__']
           required_attributes = []

           issues = []

           # Check required methods
           for method in required_methods:
               if not hasattr(enricher_class, method):
                   issues.append(f"Missing required method: {method}")
               elif not callable(getattr(enricher_class, method)):
                   issues.append(f"Method {method} is not callable")

           # Check if it's an async enricher
           if hasattr(enricher_class, 'enrich_async'):
               if not asyncio.iscoroutinefunction(enricher_class.enrich_async):
                   issues.append("enrich_async method must be async")

           # Check constructor
           if not hasattr(enricher_class, '__init__'):
               issues.append("Missing __init__ method")

           if issues:
               print(f"Enricher interface validation failed:")
               for issue in issues:
                   print(f"  - {issue}")
               return False

           return True

       def test_enricher_execution(self, enricher: Any, test_events: List[Dict[str, Any]], 
                                  logger=None, method_name: str = "info") -> List[EnrichmentTestResult]:
           """Test enricher execution with sample events."""
           results = []
           
           for event in test_events:
               result = self._test_single_enrichment(enricher, event, logger, method_name)
               results.append(result)
               self.test_results.append(result)

           return results

       def _test_single_enrichment(self, enricher: Any, event: Dict[str, Any], 
                                  logger=None, method_name: str = "info") -> EnrichmentTestResult:
           """Test single enrichment operation."""
           import copy
           input_event = copy.deepcopy(event)
           enricher_name = getattr(enricher, 'name', enricher.__class__.__name__)

           start_time = time.perf_counter()
           success = True
           error = None
           output_event = input_event.copy()

           try:
               if hasattr(enricher, 'enrich_async') and asyncio.iscoroutinefunction(enricher.enrich_async):
                   # Async enricher
                   output_event = asyncio.run(enricher(logger, method_name, input_event))
               else:
                   # Sync enricher
                   output_event = enricher(logger, method_name, input_event)
           except Exception as e:
               success = False
               error = str(e)
               output_event = input_event

           duration_ms = (time.perf_counter() - start_time) * 1000

           # Analyze changes
           added_fields = [k for k in output_event.keys() if k not in input_event]
           modified_fields = [
               k for k in input_event.keys() 
               if k in output_event and output_event[k] != input_event[k]
           ]

           return EnrichmentTestResult(
               input_event=input_event,
               output_event=output_event,
               enricher_name=enricher_name,
               duration_ms=duration_ms,
               success=success,
               error=error,
               added_fields=added_fields,
               modified_fields=modified_fields
           )

       def test_enricher_registration(self, name: str, enricher_class: type) -> bool:
           """Test enricher registration and retrieval."""
           try:
               from fapilog._internal.enricher_registry import EnricherRegistry
               
               # Register enricher
               EnricherRegistry.register(name, enricher_class)
               
               # Verify registration
               metadata = EnricherRegistry.get_metadata(name)
               if metadata is None:
                   print(f"Registration test failed: {name} not found in registry")
                   return False
               
               if metadata.enricher_class != enricher_class:
                   print(f"Registration test failed: {name} class mismatch")
                   return False
               
               return True
           except Exception as e:
               print(f"Registration test failed for {name}: {e}")
               return False

       def test_conditional_enrichment(self, enricher_metadata, test_conditions: List[Dict[str, Any]]) -> Dict[str, bool]:
           """Test conditional enricher enablement."""
           from fapilog._internal.enricher_conditions import EnricherConditions
           
           results = {}
           for i, condition in enumerate(test_conditions):
               should_enable = EnricherConditions.should_enable_enricher(enricher_metadata, condition)
               results[f"condition_{i}"] = should_enable
           
           return results

       def generate_test_report(self) -> str:
           """Generate a comprehensive test report."""
           if not self.test_results:
               return "No test results available."

           successful = [r for r in self.test_results if r.success]
           failed = [r for r in self.test_results if not r.success]
           
           avg_duration = sum(r.duration_ms for r in successful) / len(successful) if successful else 0
           
           report = f"""
   Enricher Test Report
   ===================
   
   Total Tests: {len(self.test_results)}
   Successful: {len(successful)}
   Failed: {len(failed)}
   Success Rate: {len(successful) / len(self.test_results) * 100:.1f}%
   
   Performance:
   - Average Duration: {avg_duration:.3f}ms
   - Fastest: {min((r.duration_ms for r in successful), default=0):.3f}ms
   - Slowest: {max((r.duration_ms for r in successful), default=0):.3f}ms
   
   """
           
           if failed:
               report += "\nFailed Tests:\n"
               for result in failed:
                   report += f"- {result.enricher_name}: {result.error}\n"
           
           return report
   ```

2. **Add Mock Enricher Implementations in `src/fapilog/testing/mock_enrichers.py`**:

   ```python
   import asyncio
   import time
   from typing import Dict, Any, List, Optional
   from fapilog._internal.async_enricher import AsyncEnricher

   class RecordingEnricher:
       """Mock enricher that records all enrichment calls."""

       def __init__(self, name: str = "recording"):
           self.name = name
           self.calls: List[Dict[str, Any]] = []
           self.call_count = 0

       def __call__(self, logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
           self.call_count += 1
           call_info = {
               'call_number': self.call_count,
               'method_name': method_name,
               'event_dict': event_dict.copy(),
               'timestamp': time.time()
           }
           self.calls.append(call_info)
           
           # Add recording metadata to event
           result = event_dict.copy()
           result['_recorded_by'] = self.name
           result['_call_number'] = self.call_count
           return result

       def clear_calls(self):
           """Clear recorded calls."""
           self.calls.clear()
           self.call_count = 0

   class FailingEnricher:
       """Mock enricher that fails under specific conditions."""

       def __init__(self, name: str = "failing", 
                   fail_after: int = 0, 
                   fail_probability: float = 0.0,
                   exception_type: type = RuntimeError,
                   error_message: str = "Mock enricher failure"):
           self.name = name
           self.fail_after = fail_after
           self.fail_probability = fail_probability
           self.exception_type = exception_type
           self.error_message = error_message
           self.call_count = 0

       def __call__(self, logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
           self.call_count += 1
           
           # Check if should fail based on call count
           if self.fail_after > 0 and self.call_count > self.fail_after:
               raise self.exception_type(f"{self.error_message} (call {self.call_count})")
           
           # Check if should fail based on probability
           if self.fail_probability > 0:
               import random
               if random.random() < self.fail_probability:
                   raise self.exception_type(f"{self.error_message} (random failure)")
           
           # Check if should fail based on event content
           if event_dict.get('force_enricher_failure'):
               raise self.exception_type(f"{self.error_message} (forced failure)")
           
           result = event_dict.copy()
           result['_processed_by_failing'] = self.name
           return result

   class SlowEnricher:
       """Mock enricher that introduces artificial delays."""

       def __init__(self, name: str = "slow", 
                   delay_ms: float = 100,
                   variable_delay: bool = False):
           self.name = name
           self.delay_ms = delay_ms
           self.variable_delay = variable_delay
           self.call_count = 0

       def __call__(self, logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
           self.call_count += 1
           
           delay = self.delay_ms
           if self.variable_delay:
               import random
               delay = random.uniform(self.delay_ms * 0.5, self.delay_ms * 1.5)
           
           time.sleep(delay / 1000)  # Convert to seconds
           
           result = event_dict.copy()
           result['_processed_by_slow'] = self.name
           result['_artificial_delay_ms'] = delay
           return result

   class AsyncRecordingEnricher(AsyncEnricher):
       """Async mock enricher that records calls."""

       def __init__(self, name: str = "async_recording", **kwargs):
           super().__init__(name, **kwargs)
           self.calls: List[Dict[str, Any]] = []
           self.call_count = 0

       async def _startup(self) -> None:
           pass

       async def _shutdown(self) -> None:
           pass

       async def _health_check(self) -> bool:
           return True

       async def enrich_async(self, logger: Any, method_name: str, 
                             event_dict: Dict[str, Any]) -> Dict[str, Any]:
           self.call_count += 1
           call_info = {
               'call_number': self.call_count,
               'method_name': method_name,
               'event_dict': event_dict.copy(),
               'timestamp': time.time()
           }
           self.calls.append(call_info)
           
           result = event_dict.copy()
           result['_async_recorded_by'] = self.name
           result['_async_call_number'] = self.call_count
           return result

   class AsyncSlowEnricher(AsyncEnricher):
       """Async mock enricher with delays."""

       def __init__(self, name: str = "async_slow", delay_ms: float = 100, **kwargs):
           super().__init__(name, **kwargs)
           self.delay_ms = delay_ms

       async def _startup(self) -> None:
           pass

       async def _shutdown(self) -> None:
           pass

       async def _health_check(self) -> bool:
           return True

       async def enrich_async(self, logger: Any, method_name: str, 
                             event_dict: Dict[str, Any]) -> Dict[str, Any]:
           await asyncio.sleep(self.delay_ms / 1000)
           
           result = event_dict.copy()
           result['_async_slow_processed'] = self.name
           result['_async_delay_ms'] = self.delay_ms
           return result
   ```

3. **Add Performance Testing in `src/fapilog/testing/enricher_performance.py`**:

   ```python
   import asyncio
   import time
   import statistics
   from typing import Dict, Any, List, Optional, Union
   from dataclasses import dataclass

   @dataclass
   class PerformanceMetrics:
       """Performance metrics for enricher testing."""
       enricher_name: str
       total_calls: int
       total_duration_ms: float
       avg_duration_ms: float
       min_duration_ms: float
       max_duration_ms: float
       median_duration_ms: float
       p95_duration_ms: float
       p99_duration_ms: float
       throughput_ops_per_sec: float
       error_count: int
       error_rate: float

   class EnricherPerformanceTester:
       """Performance testing utilities for enrichers."""

       def __init__(self):
           self.results: List[PerformanceMetrics] = []

       def test_enricher_throughput(self, enricher: Any, test_events: List[Dict[str, Any]], 
                                   iterations: int = 1000, logger=None, 
                                   method_name: str = "info") -> PerformanceMetrics:
           """Test enricher throughput with multiple iterations."""
           enricher_name = getattr(enricher, 'name', enricher.__class__.__name__)
           durations = []
           errors = 0

           start_time = time.perf_counter()

           for i in range(iterations):
               event = test_events[i % len(test_events)].copy()
               
               iteration_start = time.perf_counter()
               try:
                   if hasattr(enricher, 'enrich_async') and asyncio.iscoroutinefunction(enricher.enrich_async):
                       asyncio.run(enricher(logger, method_name, event))
                   else:
                       enricher(logger, method_name, event)
               except Exception:
                   errors += 1
               
               iteration_duration = (time.perf_counter() - iteration_start) * 1000
               durations.append(iteration_duration)

           total_duration = (time.perf_counter() - start_time) * 1000

           # Calculate metrics
           metrics = PerformanceMetrics(
               enricher_name=enricher_name,
               total_calls=iterations,
               total_duration_ms=total_duration,
               avg_duration_ms=statistics.mean(durations),
               min_duration_ms=min(durations),
               max_duration_ms=max(durations),
               median_duration_ms=statistics.median(durations),
               p95_duration_ms=self._percentile(durations, 95),
               p99_duration_ms=self._percentile(durations, 99),
               throughput_ops_per_sec=(iterations / total_duration) * 1000,
               error_count=errors,
               error_rate=(errors / iterations) * 100
           )

           self.results.append(metrics)
           return metrics

       async def test_async_enricher_concurrency(self, enricher: Any, test_events: List[Dict[str, Any]], 
                                                concurrency: int = 10, iterations: int = 100,
                                                logger=None, method_name: str = "info") -> PerformanceMetrics:
           """Test async enricher under concurrent load."""
           enricher_name = getattr(enricher, 'name', enricher.__class__.__name__)
           
           async def worker(worker_id: int, events_per_worker: int):
               durations = []
               errors = 0
               
               for i in range(events_per_worker):
                   event = test_events[i % len(test_events)].copy()
                   
                   start_time = time.perf_counter()
                   try:
                       await enricher(logger, method_name, event)
                   except Exception:
                       errors += 1
                   
                   duration = (time.perf_counter() - start_time) * 1000
                   durations.append(duration)
               
               return durations, errors

           events_per_worker = iterations // concurrency
           total_start = time.perf_counter()
           
           # Run concurrent workers
           tasks = [worker(i, events_per_worker) for i in range(concurrency)]
           results = await asyncio.gather(*tasks)
           
           total_duration = (time.perf_counter() - total_start) * 1000

           # Aggregate results
           all_durations = []
           total_errors = 0
           
           for durations, errors in results:
               all_durations.extend(durations)
               total_errors += errors

           total_calls = concurrency * events_per_worker

           metrics = PerformanceMetrics(
               enricher_name=f"{enricher_name}_concurrent",
               total_calls=total_calls,
               total_duration_ms=total_duration,
               avg_duration_ms=statistics.mean(all_durations),
               min_duration_ms=min(all_durations),
               max_duration_ms=max(all_durations),
               median_duration_ms=statistics.median(all_durations),
               p95_duration_ms=self._percentile(all_durations, 95),
               p99_duration_ms=self._percentile(all_durations, 99),
               throughput_ops_per_sec=(total_calls / total_duration) * 1000,
               error_count=total_errors,
               error_rate=(total_errors / total_calls) * 100
           )

           self.results.append(metrics)
           return metrics

       def test_enricher_memory_usage(self, enricher: Any, test_events: List[Dict[str, Any]], 
                                     iterations: int = 1000) -> Dict[str, Any]:
           """Test enricher memory usage patterns."""
           import psutil
           import gc
           
           process = psutil.Process()
           
           # Force garbage collection before test
           gc.collect()
           initial_memory = process.memory_info().rss

           for i in range(iterations):
               event = test_events[i % len(test_events)].copy()
               try:
                   if hasattr(enricher, 'enrich_async') and asyncio.iscoroutinefunction(enricher.enrich_async):
                       asyncio.run(enricher(None, "info", event))
                   else:
                       enricher(None, "info", event)
               except Exception:
                   pass

           # Force garbage collection after test
           gc.collect()
           final_memory = process.memory_info().rss
           
           return {
               'enricher_name': getattr(enricher, 'name', enricher.__class__.__name__),
               'initial_memory_mb': initial_memory / 1024 / 1024,
               'final_memory_mb': final_memory / 1024 / 1024,
               'memory_delta_mb': (final_memory - initial_memory) / 1024 / 1024,
               'memory_per_operation_bytes': (final_memory - initial_memory) / iterations
           }

       def _percentile(self, data: List[float], percentile: float) -> float:
           """Calculate percentile of data."""
           if not data:
               return 0.0
           
           sorted_data = sorted(data)
           k = (len(sorted_data) - 1) * (percentile / 100)
           f = int(k)
           c = k - f
           
           if f + 1 < len(sorted_data):
               return sorted_data[f] + c * (sorted_data[f + 1] - sorted_data[f])
           else:
               return sorted_data[f]

       def generate_performance_report(self) -> str:
           """Generate performance testing report."""
           if not self.results:
               return "No performance test results available."

           report = "Enricher Performance Report\n"
           report += "=" * 50 + "\n\n"
           
           for metrics in self.results:
               report += f"Enricher: {metrics.enricher_name}\n"
               report += f"  Total Calls: {metrics.total_calls}\n"
               report += f"  Average Duration: {metrics.avg_duration_ms:.3f}ms\n"
               report += f"  Median Duration: {metrics.median_duration_ms:.3f}ms\n"
               report += f"  95th Percentile: {metrics.p95_duration_ms:.3f}ms\n"
               report += f"  99th Percentile: {metrics.p99_duration_ms:.3f}ms\n"
               report += f"  Throughput: {metrics.throughput_ops_per_sec:.1f} ops/sec\n"
               report += f"  Error Rate: {metrics.error_rate:.2f}%\n\n"
           
           return report
   ```

4. **Add Debugging Utilities in `src/fapilog/testing/enricher_debug.py`**:

   ```python
   import inspect
   from typing import Dict, Any, List, Optional, Type
   from fapilog._internal.enricher_registry import EnricherRegistry
   from fapilog._internal.async_enricher import AsyncEnricher

   class EnricherDebugger:
       """Debug utilities for enricher development."""

       @staticmethod
       def list_registered_enrichers() -> Dict[str, Dict[str, Any]]:
           """List all registered enrichers with detailed metadata."""
           enrichers = EnricherRegistry.list_enrichers()
           result = {}
           
           for name, metadata in enrichers.items():
               result[name] = {
                   'name': metadata.name,
                   'class': metadata.enricher_class.__name__,
                   'module': metadata.enricher_class.__module__,
                   'description': metadata.description,
                   'priority': metadata.priority,
                   'dependencies': metadata.dependencies,
                   'conditions': metadata.conditions,
                   'async_capable': metadata.async_capable,
                   'methods': [m for m in dir(metadata.enricher_class) if not m.startswith('_')]
               }
           
           return result

       @staticmethod
       def validate_enricher_class(enricher_class: Type) -> List[str]:
           """Validate enricher class implementation."""
           issues = []
           
           # Check required methods
           if not hasattr(enricher_class, '__call__'):
               issues.append("Missing required '__call__' method")
           elif not callable(getattr(enricher_class, '__call__')):
               issues.append("'__call__' attribute is not callable")
           
           # Check signature of __call__ method
           if hasattr(enricher_class, '__call__'):
               try:
                   sig = inspect.signature(enricher_class.__call__)
                   params = list(sig.parameters.keys())
                   
                   # Expected: self, logger, method_name, event_dict
                   expected_params = ['self', 'logger', 'method_name', 'event_dict']
                   if len(params) < 4 or params[:4] != expected_params:
                       issues.append(f"Incorrect __call__ signature. Expected {expected_params}, got {params}")
               except Exception as e:
                   issues.append(f"Cannot inspect __call__ signature: {e}")
           
           # Check if it's an async enricher
           if issubclass(enricher_class, AsyncEnricher):
               # Check required async methods
               if not hasattr(enricher_class, 'enrich_async'):
                   issues.append("AsyncEnricher must implement 'enrich_async' method")
               elif not asyncio.iscoroutinefunction(enricher_class.enrich_async):
                   issues.append("'enrich_async' method must be async")
               
               for method in ['_startup', '_shutdown', '_health_check']:
                   if not hasattr(enricher_class, method):
                       issues.append(f"AsyncEnricher must implement '{method}' method")
                   elif not asyncio.iscoroutinefunction(getattr(enricher_class, method)):
                       issues.append(f"'{method}' method must be async")
           
           # Check constructor
           if hasattr(enricher_class, '__init__'):
               try:
                   sig = inspect.signature(enricher_class.__init__)
                   # Should accept at least self and **kwargs
                   params = list(sig.parameters.keys())
                   if len(params) < 1 or params[0] != 'self':
                       issues.append("Constructor must accept 'self' parameter")
               except Exception as e:
                   issues.append(f"Cannot inspect constructor signature: {e}")
           
           return issues

       @staticmethod
       def test_enricher_instantiation(enricher_class: Type, **kwargs) -> Dict[str, Any]:
           """Test enricher instantiation with given parameters."""
           result = {
               'success': False,
               'instance': None,
               'error': None,
               'warnings': []
           }
           
           try:
               instance = enricher_class(**kwargs)
               result['success'] = True
               result['instance'] = instance
               
               # Additional validation for async enrichers
               if isinstance(instance, AsyncEnricher):
                   if not hasattr(instance, 'name'):
                       result['warnings'].append("AsyncEnricher should have a 'name' attribute")
           
           except Exception as e:
               result['error'] = str(e)
           
           return result

       @staticmethod
       def trace_enricher_execution(enricher: Any, event_dict: Dict[str, Any], 
                                   logger=None, method_name: str = "info") -> Dict[str, Any]:
           """Trace enricher execution with detailed information."""
           import time
           import copy
           
           trace_info = {
               'enricher_name': getattr(enricher, 'name', enricher.__class__.__name__),
               'enricher_class': enricher.__class__.__name__,
               'input_event': copy.deepcopy(event_dict),
               'output_event': None,
               'execution_time_ms': 0,
               'success': False,
               'error': None,
               'changes': {
                   'added_fields': [],
                   'modified_fields': [],
                   'removed_fields': []
               }
           }
           
           start_time = time.perf_counter()
           
           try:
               if hasattr(enricher, 'enrich_async') and asyncio.iscoroutinefunction(enricher.enrich_async):
                   output_event = asyncio.run(enricher(logger, method_name, event_dict))
               else:
                   output_event = enricher(logger, method_name, event_dict)
               
               trace_info['output_event'] = output_event
               trace_info['success'] = True
               
               # Analyze changes
               input_keys = set(event_dict.keys())
               output_keys = set(output_event.keys())
               
               trace_info['changes']['added_fields'] = list(output_keys - input_keys)
               trace_info['changes']['removed_fields'] = list(input_keys - output_keys)
               
               # Check for modified fields
               for key in input_keys & output_keys:
                   if event_dict[key] != output_event[key]:
                       trace_info['changes']['modified_fields'].append(key)
           
           except Exception as e:
               trace_info['error'] = str(e)
           
           trace_info['execution_time_ms'] = (time.perf_counter() - start_time) * 1000
           
           return trace_info

       @staticmethod
       def analyze_enricher_dependencies(enricher_names: List[str]) -> Dict[str, Any]:
           """Analyze enricher dependencies and suggest execution order."""
           enrichers = EnricherRegistry.list_enrichers()
           
           analysis = {
               'enrichers': {},
               'dependency_graph': {},
               'suggested_order': [],
               'circular_dependencies': [],
               'missing_dependencies': []
           }
           
           # Build dependency graph
           for name in enricher_names:
               if name in enrichers:
                   metadata = enrichers[name]
                   analysis['enrichers'][name] = {
                       'dependencies': metadata.dependencies,
                       'priority': metadata.priority
                   }
                   analysis['dependency_graph'][name] = metadata.dependencies
               else:
                   analysis['missing_dependencies'].append(name)
           
           # Try to resolve order (simplified topological sort)
           try:
               resolved_order = EnricherRegistry.resolve_dependencies(enricher_names)
               analysis['suggested_order'] = resolved_order
           except Exception as e:
               analysis['circular_dependencies'] = [str(e)]
           
           return analysis
   ```

5. **Create Testing Examples in `examples/enricher_testing_examples.py`**:

   ```python
   from fapilog.testing import (
       EnricherTestFramework, 
       EnricherPerformanceTester,
       EnricherDebugger,
       RecordingEnricher,
       FailingEnricher,
       SlowEnricher
   )
   from fapilog import register_enricher_advanced

   @register_enricher_advanced(
       name="example_enricher",
       description="Example enricher for testing",
       priority=100
   )
   class ExampleEnricher:
       def __init__(self, prefix: str = "test", **kwargs):
           self.prefix = prefix
       
       def __call__(self, logger, method_name, event_dict):
           result = event_dict.copy()
           result[f'{self.prefix}_field'] = f'{self.prefix}_value'
           result[f'{self.prefix}_timestamp'] = time.time()
           return result

   def test_enricher_examples():
       """Demonstrate enricher testing capabilities."""
       
       # Initialize testing frameworks
       test_framework = EnricherTestFramework()
       perf_tester = EnricherPerformanceTester()
       
       # Test enricher interface
       print("=== Interface Validation ===")
       is_valid = test_framework.test_enricher_interface(ExampleEnricher)
       print(f"ExampleEnricher interface valid: {is_valid}")
       
       # Test enricher registration
       print("\n=== Registration Testing ===")
       registration_success = test_framework.test_enricher_registration(
           "example_enricher", ExampleEnricher
       )
       print(f"Registration successful: {registration_success}")
       
       # Test enricher execution
       print("\n=== Execution Testing ===")
       enricher = ExampleEnricher(prefix="demo")
       test_events = [
           {"user_id": "123", "action": "login"},
           {"user_id": "456", "action": "logout"},
           {"request_id": "req-789", "endpoint": "/api/users"}
       ]
       
       results = test_framework.test_enricher_execution(enricher, test_events)
       for result in results:
           print(f"  Test: {result.success}, Duration: {result.duration_ms:.3f}ms")
           print(f"    Added fields: {result.added_fields}")
       
       # Performance testing
       print("\n=== Performance Testing ===")
       perf_metrics = perf_tester.test_enricher_throughput(
           enricher, test_events, iterations=1000
       )
       print(f"  Throughput: {perf_metrics.throughput_ops_per_sec:.1f} ops/sec")
       print(f"  Average latency: {perf_metrics.avg_duration_ms:.3f}ms")
       
       # Memory testing
       memory_metrics = perf_tester.test_enricher_memory_usage(
           enricher, test_events, iterations=1000
       )
       print(f"  Memory delta: {memory_metrics['memory_delta_mb']:.3f}MB")
       
       # Mock enricher testing
       print("\n=== Mock Enricher Testing ===")
       recording = RecordingEnricher("test_recorder")
       failing = FailingEnricher("test_failer", fail_after=3)
       slow = SlowEnricher("test_slow", delay_ms=50)
       
       mock_results = test_framework.test_enricher_execution(
           recording, test_events
       )
       print(f"Recording enricher calls: {recording.call_count}")
       
       # Test failing enricher
       try:
           test_framework.test_enricher_execution(failing, test_events * 2)
       except Exception as e:
           print(f"Failing enricher behaved as expected: {type(e).__name__}")
       
       # Debug utilities
       print("\n=== Debug Analysis ===")
       enricher_info = EnricherDebugger.list_registered_enrichers()
       print(f"Registered enrichers: {list(enricher_info.keys())}")
       
       validation_issues = EnricherDebugger.validate_enricher_class(ExampleEnricher)
       print(f"Validation issues: {validation_issues or 'None'}")
       
       # Generate reports
       print("\n=== Test Report ===")
       print(test_framework.generate_test_report())
       print(perf_tester.generate_performance_report())

   if __name__ == "__main__":
       test_enricher_examples()
   ```

6. **Add Comprehensive Tests in `tests/test_enricher_testing_framework.py`**:

   - Test enricher testing framework functionality
   - Test mock enricher behaviors
   - Test performance testing accuracy
   - Test debugging utilities
   - Test async enricher testing support
   - Test integration with enricher registry
   - Test error handling in testing scenarios

───────────────────────────────────  
Dependencies / Notes

- Depends on Stories 16.1 and 16.2 for enhanced enricher system
- Should provide easy-to-use testing utilities
- Performance testing should be accurate and reproducible
- Mock enrichers should cover common testing scenarios
- Debug utilities should provide actionable insights
- Should work with both sync and async enrichers

───────────────────────────────────  
Definition of Done  
✓ Enricher testing framework implemented with comprehensive utilities  
✓ Mock enricher implementations added (Recording, Failing, Slow, Async variants)  
✓ Performance testing helpers implemented with detailed metrics  
✓ Debugging utilities created with validation and tracing  
✓ Testing examples created with documentation  
✓ Async enricher testing support implemented  
✓ Integration testing tools added  
✓ Comprehensive tests added with good coverage  
✓ Testing utilities are easy to use and well-documented  
✓ PR merged to **main** with reviewer approval and green CI  
✓ `CHANGELOG.md` updated under _Unreleased → Added_ 