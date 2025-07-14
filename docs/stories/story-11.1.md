Story 11.1 – Public Package Metadata  
───────────────────────────────────  
Epic: 11 – Packaging & Distribution  
Sprint Target: Sprint #⟪next⟫  
Story Points: 3

**As a potential user of the fapilog library**  
I want to see rich and accurate metadata on PyPI or other registries  
So that I can quickly evaluate the library’s purpose, compatibility, and usage.

───────────────────────────────────  
Acceptance Criteria

- `pyproject.toml` includes full metadata for packaging and discovery
- Project metadata is validated and appears correctly when built with `python -m build`
- Fields include: name, version, description, license, authors, dependencies, readme, keywords, classifiers, etc.
- Classifiers match Python version and status
- Extras are documented (e.g., `loki`, `dev`)
- README is used as the long description
- Metadata renders correctly in `twine check dist/*` output
- Badge links (e.g., license, CI) are visible in the README

───────────────────────────────────  
Tasks / Technical Checklist

1. Update `[project]` section of `pyproject.toml` with:

   - `name = "fapilog"`
   - `version = "0.1.0"`
   - `description = "Structured, enriched logging for FastAPI and ASGI apps"`
   - `readme = "README.md"`
   - `license = {text = "MIT"}`
   - `authors = [{ name = "Your Name", email = "you@example.com" }]`
   - `keywords = ["fastapi", "logging", "structured", "asyncio", "middleware"]`
   - `dependencies = [...]`
   - `classifiers = [...]` (Python versions, development status, audience, license)

2. Confirm long description renders properly on PyPI with:  
    python -m build  
    twine check dist/\*

3. Add visible metadata badges to the top of `README.md`:

   - License (e.g., MIT)
   - Python version support (e.g., `3.11`)
   - CI status
   - Coverage (if available)

4. Optional: add `project.urls` block to `pyproject.toml` for source, docs, issues  
    [project.urls]  
    Homepage = "https://github.com/your-org/fastapi-logger"  
    Source = "https://github.com/your-org/fastapi-logger"  
    Issues = "https://github.com/your-org/fastapi-logger/issues"

───────────────────────────────────  
Dependencies / Notes

- Assumes project already builds cleanly (see Story 9.4)
- Actual publish step is covered in Story 11.2
- PyPI-specific formatting for long descriptions uses CommonMark/Markdown

───────────────────────────────────  
Definition of Done  
✓ `pyproject.toml` metadata complete  
✓ `python -m build && twine check dist/*` passes  
✓ Badges present in README  
✓ PR merged to **main** with reviewer approval  
✓ `CHANGELOG.md` updated under _Unreleased → Added_
