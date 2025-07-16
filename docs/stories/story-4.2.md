Story 4.2 – Memory & CPU Snapshot Enricher  
───────────────────────────────────  
Epic: 4 – Field Enrichers  
Sprint Target: Sprint #⟪next⟫  
Story Points: 5

**As a platform operator**  
I want each log entry to optionally include memory and CPU usage  
So that I can monitor system health, detect leaks, and correlate log spikes with resource load.

───────────────────────────────────  
Acceptance Criteria

- A new processor `resource_snapshot_enricher` is implemented in **fapilog/enrichers.py**
- It enriches each log with:  
  • `memory_mb`: resident memory usage of the current process in megabytes (rounded float)  
  • `cpu_percent`: process CPU usage percentage (float, 0.0–100.0)
- Processor uses the `psutil` library and caches a `Process()` object for performance
- Enricher is **optional**, enabled only when `FAPILOG_ENABLE_RESOURCE_METRICS=true` or `LoggingSettings.enable_resource_metrics = True`
- When enabled, the enricher is added near the end of the pipeline (after context, before rendering)
- Unit tests verify:  
  • Values appear in logs when enabled  
  • Values are floats and within expected bounds  
  • Fields are absent when enrichment is disabled

───────────────────────────────────  
Tasks / Technical Checklist

✅ **1. Add `psutil` to optional dependencies in `pyproject.toml`:**

- Under `[project.optional-dependencies]`, add:  
  `metrics = ["psutil>=5.9"]`

✅ **2. Implement `resource_snapshot_enricher()` in `fapilog/enrichers.py`:**

- Use `psutil.Process().memory_info().rss / (1024 * 1024)` for MB
- Use `Process().cpu_percent(interval=None)` for CPU
- Cache `psutil.Process()` instance for reuse
- Added graceful error handling for OSError and AttributeError
- Implemented manual field override support
- Added TYPE_CHECKING import for proper type annotations

✅ **3. Extend `LoggingSettings` (fapilog/settings.py):**

- Add field: `enable_resource_metrics: bool = False`
- Map to env var: `FAPILOG_ENABLE_RESOURCE_METRICS`

✅ **4. Update `build_processor_chain()` (pipeline.py):**

- If `settings.enable_resource_metrics` is `True`, insert the enricher before the renderer
- Positioned after request/response enricher, before sampling processor

✅ **5. Unit tests in `tests/test_enricher_resource.py`:**

- ✅ `test_enricher_includes_fields()` - Values appear in logs when enabled
- ✅ `test_enricher_skipped_when_disabled()` - Fields absent when disabled
- ✅ `test_fields_within_valid_range()` - Values are floats within expected bounds
- ✅ `test_fields_can_be_overridden()` - Manual override support
- ✅ `test_only_missing_fields_added()` - Partial field addition
- ✅ `test_none_values_handling()` - None value replacement
- ✅ `test_process_errors_handled()` - Graceful error handling
- ✅ `test_cached_process_object()` - Performance caching verification
- ✅ `test_logger_and_method_parameters()` - Interface compatibility
- ✅ `test_empty_event_dict()` - Edge case handling
- ✅ `test_psutil_import_error()` - Import failure handling

✅ **6. Integration tests in `tests/test_pipeline_resource.py`:**

- ✅ `test_resource_enricher_included_when_enabled()` - Pipeline inclusion
- ✅ `test_resource_enricher_excluded_when_disabled()` - Pipeline exclusion
- ✅ `test_resource_enricher_position_in_chain()` - Correct positioning
- ✅ `test_pipeline_with_resource_metrics()` - End-to-end functionality

✅ **7. Update README:**

- Add explanation and field descriptions under "Log Fields"
- Note that `psutil` must be installed and enrichment must be enabled
- Added comprehensive "Resource Metrics" section with configuration examples

✅ **8. Example implementation:**

- Created `examples/resource_metrics_example.py` demonstrating usage
- Shows both environment variable and programmatic configuration
- Demonstrates manual field override capabilities

✅ **9. CHANGELOG updates:**

- Comprehensive documentation of all features and implementation details
- Added under _Unreleased → Added_ section

───────────────────────────────────  
Implementation Review

**✅ COMPLETED - All Acceptance Criteria Met**

The Memory & CPU Snapshot Enricher has been successfully implemented with the following key features:

### **Core Functionality**

- **Resource Metrics Capture**: `memory_mb` (resident memory in MB) and `cpu_percent` (CPU usage 0.0-100.0)
- **Performance Optimized**: Cached `psutil.Process()` object using `@lru_cache`
- **Graceful Degradation**: Silent skip when psutil unavailable, error handling for process info failures
- **Manual Override Support**: Fields only added if not already present, allowing custom values

### **Configuration & Integration**

- **Optional Dependency**: `psutil>=5.9` via `fapilog[metrics]` package
- **Environment Variable**: `FAPILOG_ENABLE_RESOURCE_METRICS=true`
- **Programmatic Config**: `LoggingSettings(enable_resource_metrics=True)`
- **Pipeline Integration**: Conditionally added after request/response enricher, before sampling

### **Testing & Quality**

- **Comprehensive Test Suite**: 15 tests covering all scenarios (11 unit + 4 integration)
- **100% Test Pass Rate**: All tests passing with robust error handling
- **Edge Case Coverage**: Import failures, process errors, manual overrides, None values
- **Code Quality**: Fixed type annotations, proper error handling, performance optimizations

### **Documentation & Examples**

- **README Updates**: Complete "Resource Metrics" section with configuration and performance notes
- **Working Example**: `examples/resource_metrics_example.py` demonstrating real usage
- **CHANGELOG**: Comprehensive feature documentation
- **Log Fields Documentation**: Updated to include `memory_mb` and `cpu_percent`

### **Production Ready Features**

- **Safe for Containers**: Only installs psutil when metrics enabled
- **Non-blocking**: Minimal performance impact when disabled
- **Error Resilient**: Handles process termination, permission issues, import failures
- **Framework Agnostic**: Works with FastAPI, CLI apps, or any structlog pipeline

### **Sample Usage**

```bash
# Environment variable approach
export FAPILOG_ENABLE_RESOURCE_METRICS=true

# Programmatic approach
from fapilog.settings import LoggingSettings
settings = LoggingSettings(enable_resource_metrics=True)

# Installation
pip install fapilog[metrics]
```

**Sample Output:**

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "info",
  "event": "Request processed",
  "memory_mb": 45.2,
  "cpu_percent": 12.5,
  "trace_id": "abc123def456",
  "status_code": 200,
  "latency_ms": 45.2
}
```

───────────────────────────────────  
Dependencies / Notes

- Builds on enrichment and settings infrastructure from earlier epics
- Adds `psutil` only if metrics are enabled; safe for containerized and CLI apps
- **Performance Impact**: Minimal when disabled, cached process object when enabled
- **Error Handling**: Graceful degradation for all failure scenarios
- **Testing**: 15 comprehensive tests with 100% pass rate

───────────────────────────────────  
Definition of Done  
✅ Enricher implemented and conditionally included based on settings  
✅ Unit tests verify field presence, correctness, and opt-out logic  
✅ Integration tests verify pipeline inclusion/exclusion and positioning  
✅ All tests passing (15/15) with comprehensive coverage  
✅ CHANGELOG.md and README updated under _Unreleased → Added_  
✅ Optional dependency on `psutil>=5.9` via `fapilog[metrics]` package  
✅ Environment variable support: `FAPILOG_ENABLE_RESOURCE_METRICS`  
✅ Graceful error handling for process info retrieval failures  
✅ Performance optimization with cached process object  
✅ Manual field override support  
✅ Correct positioning in processor pipeline  
✅ Working example demonstrating real usage  
✅ Production-ready with comprehensive error handling and testing

**🎉 STORY COMPLETE - READY FOR REVIEW AND MERGE**
