Story 4.4 – Custom Enricher Registry and Hook Support  
───────────────────────────────────  
Epic: 4 – Field Enrichers  
Sprint Target: Sprint #⟪next⟫  
Story Points: 5

**As an advanced user or integrator**  
I want to register custom enrichers into the logging pipeline  
So that I can inject application-specific metadata into log events without modifying the core library.

───────────────────────────────────  
Acceptance Criteria

- A global registry for custom enrichers is implemented in **`fapilog/enrichers.py`**
- Developers can register enrichers at runtime via `register_enricher(fn)`
- Custom enrichers are included at the end of the processor chain by default
- Enricher functions follow the structlog processor signature: `(logger, method_name, event_dict) → event_dict`
- Multiple enrichers can be registered; they are called in registration order
- Duplicate registrations are prevented (same function ref or name)
- Enrichers can be cleared via `clear_enrichers()` (for test isolation)
- Unit tests verify:  
  • Enrichers are registered and executed  
  • Multiple enrichers run in order  
  • Redundant registrations are ignored  
  • Registered enrichers affect log output
- README includes an example of custom enrichment and registry usage

───────────────────────────────────  
Tasks / Technical Checklist

1. In `fapilog/enrichers.py`, define:

   - `registered_enrichers: list[Callable] = []`
   - `register_enricher(fn: Callable) → None`  
     • Adds `fn` to list if not already present
   - `clear_enrichers()` – clears the registry (used in tests)
   - `run_registered_enrichers(logger, method_name, event_dict)` – applies all registered enrichers

2. Modify `build_processor_chain()` in `pipeline.py`:

   - Append `run_registered_enrichers` to processor list (last before rendering)

3. Unit tests in `tests/test_enricher_registry.py`:

   - `test_register_and_run_enricher()`
   - `test_multiple_enrichers_in_order()`
   - `test_duplicate_enrichers_are_ignored()`
   - `test_clear_enrichers()`

4. Update README:
   - New section: “Custom Enrichers”
   - Show how to inject an enricher (e.g., adding `tenant_id`, `session_id`)

───────────────────────────────────  
Dependencies / Notes

- Builds on structlog-style processor chain
- Enables downstream services to customize logs without modifying `fapilog` core

───────────────────────────────────  
Definition of Done  
✓ Registry implemented and exposed via public API  
✓ Custom enrichers run automatically in processor chain  
✓ Tests confirm functionality and resilience  
✓ PR merged to **main** with reviewer approval and green CI  
✓ `CHANGELOG.md` and README updated under _Unreleased → Added_
