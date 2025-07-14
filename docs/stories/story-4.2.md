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

1. Add `psutil` to optional dependencies in `pyproject.toml`:

   - Under `[project.optional-dependencies]`, add:  
     `metrics = ["psutil>=5.9"]`

2. Implement `resource_snapshot_enricher()` in `fapilog/enrichers.py`:

   - Use `psutil.Process().memory_info().rss / (1024 * 1024)` for MB
   - Use `Process().cpu_percent(interval=None)` for CPU
   - Cache `psutil.Process()` instance for reuse

3. Extend `LoggingSettings` (fapilog/settings.py):

   - Add field: `enable_resource_metrics: bool = False`
   - Map to env var: `FAPILOG_ENABLE_RESOURCE_METRICS`

4. Update `build_processor_chain()` (pipeline.py):

   - If `settings.enable_resource_metrics` is `True`, insert the enricher before the renderer

5. Unit tests in `tests/test_enricher_resource.py`:

   - `test_enricher_includes_fields()`
   - `test_enricher_skipped_when_disabled()`
   - `test_fields_within_valid_range()`

6. Update README:
   - Add explanation and field descriptions under “Log Fields”
   - Note that `psutil` must be installed and enrichment must be enabled

───────────────────────────────────  
Dependencies / Notes

- Builds on enrichment and settings infrastructure from earlier epics
- Adds `psutil` only if metrics are enabled; safe for containerized and CLI apps

───────────────────────────────────  
Definition of Done  
✓ Enricher implemented and conditionally included based on settings  
✓ Unit tests verify field presence, correctness, and opt-out logic  
✓ PR merged to **main** with reviewer approval and green CI  
✓ `CHANGELOG.md` and README updated under _Unreleased → Added_
