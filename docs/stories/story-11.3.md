Story 11.3 – Install Instructions & Version Pinning  
───────────────────────────────────  
Epic: 11 – Packaging & Distribution  
Sprint Target: Sprint #⟪next⟫  
Story Points: 2

**As a new user of fapilog**  
I want clear and reliable installation instructions  
So that I can integrate the library easily into my project with correct optional extras.

───────────────────────────────────  
Acceptance Criteria

- README includes a clear **Installation** section
- Standard install command: `pip install fapilog`
- Extras install commands:
  - `pip install fapilog[loki]`
  - `pip install fapilog[dev]` (for contributors)
- Version pinning guidance is provided (e.g., `~=0.1.0` or `==0.1.1`)
- Installation block is copy-paste friendly and tested
- README displays the current version badge from PyPI
- Section clarifies Python version compatibility and optional extras

───────────────────────────────────  
Tasks / Technical Checklist

1. Add **Installation** section to README.md:

   - Include standard and extras install examples
   - Mention compatible Python versions (e.g., 3.11+)
   - Recommend pinning format:
     - Production: `fapilog~=0.1.0`
     - Strict reproducibility: `fapilog==0.1.1`

2. Add PyPI version badge:  
    ![PyPI](https://img.shields.io/pypi/v/fapilog)

3. Add a minimal “Getting Started” usage snippet below install:

   ```python
   from fapilog import configure_logging, log

   configure_logging()
   log.info("Hello from fapilog!")
   ```

4. Test all install commands locally in a clean virtualenv

5. Optional: create a `requirements-example.txt` file for quick-start projects

───────────────────────────────────  
Dependencies / Notes

- Requires Story 11.2 to be completed (PyPI publish)
- Assumes optional extras (`loki`, `dev`) are already defined in `pyproject.toml`

───────────────────────────────────  
Definition of Done  
✓ Installation section added to README  
✓ Extras and pinning options clearly documented  
✓ Snippets tested in a clean environment  
✓ PR merged to **main** with reviewer approval  
✓ `CHANGELOG.md` updated under _Unreleased → Added_
