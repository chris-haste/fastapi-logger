Story 12.2 – Auto-Generated API Reference  
───────────────────────────────────  
Epic: 12 – Documentation  
Sprint Target: Sprint #⟪next⟫  
Story Points: 5

**As a developer using fapilog**  
I want a complete API reference generated from docstrings  
So that I can understand all available classes, functions, and settings without reading source files.

───────────────────────────────────  
Acceptance Criteria

- API documentation is auto-generated using `mkdocstrings`
- Each documented module appears in the navigation under "API Reference"
- Docstrings are rendered with type hints, signatures, and summaries
- Modules documented include:
  - `fapilog.middleware`
  - `fapilog.settings`
  - `fapilog.enrichers`
  - `fapilog.sinks.*`
- Each function/class has at least a minimal docstring in source
- `mkdocs serve` renders the API reference without warnings
- `mkdocs build` completes successfully

───────────────────────────────────  
Tasks / Technical Checklist

1. Ensure `mkdocstrings[python]` is in the `docs` extra (Story 12.1)
2. Add `api.md` to `docs/` with content:

   # API Reference

   ::: fapilog.middleware  
    ::: fapilog.settings  
    ::: fapilog.enrichers  
    ::: fapilog.sinks.stdout  
    ::: fapilog.sinks.loki

3. Update `mkdocs.yml` to include API section:  
    nav: - Home: index.md  
    - Getting Started: getting-started.md  
    - Configuration: config.md  
    - API Reference: api.md

4. Ensure each target module has basic docstrings (may stub for now)
5. Run and validate locally:  
    mkdocs serve  
    mkdocs build

6. Optionally configure `mkdocstrings` formatting in `mkdocs.yml`:
   plugins: - mkdocstrings:
   default_handler: python

───────────────────────────────────  
Dependencies / Notes

- Builds on top of 12.1 (site bootstrap)
- Later refinement (e.g., detailed docstrings or examples) is out of scope
- Site deployment is handled separately (12.3)

───────────────────────────────────  
Definition of Done  
✓ API doc page renders with all core modules  
✓ No rendering errors or broken anchors  
✓ PR merged to **main** with reviewer approval  
✓ `CHANGELOG.md` updated under _Unreleased → Added_
