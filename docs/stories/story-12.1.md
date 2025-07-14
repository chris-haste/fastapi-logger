Story 12.1 – Documentation Site Bootstrap  
───────────────────────────────────  
Epic: 12 – Documentation  
Sprint Target: Sprint #⟪next⟫  
Story Points: 5

**As a user or contributor of fapilog**  
I want a browsable documentation site  
So that I can explore usage, examples, and API references without digging into source code.

───────────────────────────────────  
Acceptance Criteria

- Docs scaffolded with MkDocs and Material theme
- `mkdocs serve` runs locally and renders homepage
- Site includes at minimum:
  - Home page with project description and badges
  - Getting Started page with install, quick start, and usage
  - Configuration reference for settings and sinks
- `mkdocs.yml` contains metadata, site name, theme, navigation
- Docs are installable via `pip install ".[docs]"`
- Commands `mkdocs build` and `mkdocs serve` both succeed

───────────────────────────────────  
Tasks / Technical Checklist

1. Add `[project.optional-dependencies]` in `pyproject.toml`:  
    docs = ["mkdocs", "mkdocs-material", "mkdocstrings[python]", "markdown-include"]

2. Create `docs/` folder with these initial files:

   - `index.md` – high-level overview
   - `getting-started.md` – install, quick-start, basic usage
   - `config.md` – `settings.py`, environment variables, extras

3. Create `mkdocs.yml` in project root:  
    site_name: fapilog
   theme:
   name: material
   nav: - Home: index.md - Getting Started: getting-started.md - Configuration: config.md

4. Add Python API auto-doc generation later (Story 12.2)

5. Update README.md to link to future hosted site (placeholder for now)

6. Test locally:  
    pip install ".[docs]"
   mkdocs serve

───────────────────────────────────  
Dependencies / Notes

- Lays foundation for full API docs and GitHub Pages deploy (Story 12.3)
- Does not require all content to be finalized—just scaffold and basic sections
- Assumes optional dependencies defined and tested in tox/hatch (optional)

───────────────────────────────────  
Definition of Done  
✓ Docs structure exists and renders locally  
✓ Minimum required sections created  
✓ Installable via extras  
✓ PR merged to **main** with reviewer approval  
✓ `CHANGELOG.md` updated under _Unreleased → Added_
