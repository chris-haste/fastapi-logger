Story 9.2 – Pre-commit Hooks for Linting and Type-checking  
───────────────────────────────────  
Epic: 9 – Developer Experience & CI  
Sprint Target: Sprint #⟪next⟫  
Story Points: 3

**As a contributor to the fapilog library**  
I want automated pre-commit checks for linting, type-checking, and formatting  
So that common issues are caught before code is committed.

───────────────────────────────────  
Acceptance Criteria

- `.pre-commit-config.yaml` is present in the repo root
- Hooks include:
  - `ruff` for linting
  - `mypy` for type-checking
  - `black` (optional, not enforced if not project standard)
- `pre-commit install` sets up local git hooks
- Hooks run successfully on staged files
- `README.md` includes setup instructions for pre-commit
- Running `pre-commit run --all-files` reports no errors on a clean repo

───────────────────────────────────  
Tasks / Technical Checklist

1. Create `.pre-commit-config.yaml` with these hooks:

   - `repo: https://github.com/charliermarsh/ruff-pre-commit`
     - `rev: stable`
     - `hooks: [ruff]`
   - `repo: https://github.com/pre-commit/mirrors-mypy`
     - `rev: v1.10.0`
     - `hooks: [mypy]`
   - `repo: https://github.com/psf/black` (optional)
     - `rev: 24.4.2`
     - `hooks: [black]`

2. Add `[tool.ruff]` and `[tool.mypy]` config in `pyproject.toml` if not already present
3. Add `pre-commit` to the `dev` extra in `pyproject.toml`
4. Add a section in the README:

   - Installation: `pip install -e .[dev]`
   - Setup: `pre-commit install`
   - Manual run: `pre-commit run --all-files`

5. Run hooks on existing files and clean up any errors
6. Ensure pre-commit doesn't conflict with CI behavior

───────────────────────────────────  
Dependencies / Notes

- This is a local developer QoL improvement; not enforced in CI (covered separately)
- Formatting hook (black) is optional and should align with project formatting decision
- Developers can override locally, but hook success must be reproducible

───────────────────────────────────  
Definition of Done  
✓ Pre-commit hooks are installed and functioning  
✓ Instructions provided in README  
✓ CI and local lint/type behavior remain consistent  
✓ PR merged to **main** with reviewer approval  
✓ `CHANGELOG.md` updated under _Unreleased → Added_
