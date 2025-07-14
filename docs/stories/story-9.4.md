Story 9.4 – Build Artifacts with `python -m build`  
───────────────────────────────────  
Epic: 9 – Developer Experience & CI  
Sprint Target: Sprint #⟪next⟫  
Story Points: 2

**As a maintainer of the fapilog library**  
I want to ensure that valid wheel and source distributions can be built locally  
So that releases can be packaged and distributed via PyPI or other channels.

───────────────────────────────────  
Acceptance Criteria

- Running `python -m build` from the repo root produces:
  - A `.tar.gz` (sdist)
  - A `.whl` (wheel)
- Output is saved to the `dist/` folder
- Build process completes without warnings or errors
- Generated artifacts are valid (installable via `pip install dist/*.whl`)
- No build artifacts are checked into version control
- Build dependencies are declared in `pyproject.toml`

───────────────────────────────────  
Tasks / Technical Checklist

1. Add `build` to `[project.optional-dependencies.dev]` in `pyproject.toml`

2. Ensure `pyproject.toml` has required metadata:

   - `name`, `version`, `description`, `authors`, `license`, `dependencies`, `readme`, `classifiers`, etc.
   - `build-system` section configured with:
     ```toml
     [build-system]
     requires = ["hatchling"]
     build-backend = "hatchling.build"
     ```

3. Confirm `src/` layout is respected in `packages` config for Hatchling

4. Run `python -m build` locally

   - Confirm creation of `dist/*.tar.gz` and `dist/*.whl`

5. Test built wheel:

   - In clean virtualenv: `pip install dist/*.whl`
   - Ensure `import fapilog` succeeds

6. Add `dist/` to `.gitignore`

7. Optional: Add `hatch build` alias for convenience if using Hatch regularly

───────────────────────────────────  
Dependencies / Notes

- Assumes project uses Hatchling for builds
- No need to publish artifacts (covered in future story)
- Supports downstream release automation

───────────────────────────────────  
Definition of Done  
✓ Valid build artifacts are created with `python -m build`  
✓ Artifacts install and run correctly  
✓ `dist/` is ignored from version control  
✓ PR merged to **main** with reviewer approval  
✓ `CHANGELOG.md` updated under _Unreleased → Added_
