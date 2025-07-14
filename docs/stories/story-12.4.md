Story 12.4 – Configuration Guide & Examples  
───────────────────────────────────  
Epic: 12 – Documentation  
Sprint Target: Sprint #⟪next⟫  
Story Points: 3

**As a developer integrating fapilog**  
I want a clear guide on configuring the logger  
So that I can understand available options, environment variables, and how to customize logging behavior.

───────────────────────────────────  
Acceptance Criteria

- `docs/config.md` contains complete reference for all configuration fields
- Each setting includes:
  - Field name and type
  - Description and default value
  - Example environment variable name (e.g. `FAPILOG_LEVEL`)
- Configuration guide covers:
  - `FapilogSettings` Pydantic model
  - How to override via env vars or `configure_logging()` args
  - Optional Loki-specific fields
- Markdown is well-formatted and renders in the site
- Internal links or anchors provided for navigation (e.g., `#log_level`)

───────────────────────────────────  
Tasks / Technical Checklist

1. Open `fapilog/settings.py` and extract all top-level config fields
2. Document each field in `docs/config.md` with:

   - Name (e.g., `log_level`)
   - Type (e.g., `Literal["info", "debug"]`)
   - Default (e.g., `"info"`)
   - Env var name (e.g., `FAPILOG_LEVEL`)
   - Short description and sample value

3. Organize settings into logical sections:

   - Core Logging
   - Sinks (stdout, Loki)
   - Advanced / Developer options

4. Add “Overriding Configuration” section to show:

   - How env vars are picked up
   - How to override inline via `configure_logging(settings=...)`

5. Update `mkdocs.yml` nav if needed to ensure easy access from sidebar

6. Run `mkdocs serve` and verify rendering

───────────────────────────────────  
Dependencies / Notes

- Builds on 12.1 (site scaffold) and 12.2 (API docs)
- Can later be extended to support search or interactive playgrounds

───────────────────────────────────  
Definition of Done  
✓ Configuration reference added and visible in docs site  
✓ All major fields are documented with usage guidance  
✓ Internal navigation is clear and structured  
✓ PR merged to **main** with reviewer approval  
✓ `CHANGELOG.md` updated under _Unreleased → Added_
