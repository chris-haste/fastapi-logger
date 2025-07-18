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

   - `repo: https://github.com/astral-sh/ruff-pre-commit` (updated from charliermarsh)
     - `rev: v0.4.5`
     - `hooks: [ruff, ruff-format]`
   - `repo: https://github.com/pre-commit/mirrors-mypy`
     - `rev: v1.10.0`
     - `hooks: [mypy]`
   - `repo: https://github.com/jendrikseipp/vulture` (bonus: dead code detection)
     - `rev: v2.10`
     - `hooks: [vulture]`

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

───────────────────────────────────  
QA Review Findings

**Status: ✅ COMPLETE - All acceptance criteria met**

**Implementation Details:**

- `.pre-commit-config.yaml` created with 3 hooks: ruff, mypy, vulture
- Uses `https://github.com/astral-sh/ruff-pre-commit` (current official repo, not charliermarsh)
- Ruff configured with `--fix` for automatic code fixes
- Ruff-format included for consistent code formatting
- MyPy with proper dependencies and ignore settings
- Vulture with comprehensive configuration for dead code detection
- All hooks use project's existing settings from `pyproject.toml`

**Dependencies Status:**

- `pre-commit>=3.0.0` already in dev dependencies ✅
- `vulture>=2.10.0` already in dev dependencies ✅
- All required tools already configured in `pyproject.toml` ✅

**Documentation Status:**

- README includes complete setup instructions in "Development Setup" section ✅
- CHANGELOG updated with comprehensive entry under "Story 9.2" ✅
- Instructions cover installation, setup, and manual execution ✅

**Quality Assurance Results:**

- All hooks pass successfully: ruff (0.06s), mypy (4.59s), vulture (0.09s) ✅
- No linting errors, type errors, or dead code issues found ✅
- Pre-commit hooks properly installed in `.git/hooks/pre-commit` ✅
- Hooks run successfully on staged files ✅
- `pre-commit run --all-files` reports no errors on clean repo ✅

**Configuration Notes:**

- Used `astral-sh/ruff-pre-commit` instead of `charliermarsh/ruff-pre-commit` (current official)
- Added vulture for dead code detection (bonus feature beyond requirements)
- Ruff configured with both linting and formatting hooks
- MyPy includes proper additional dependencies and ignore settings
- All configuration leverages existing project settings

**Developer Experience:**

- Clear setup instructions in README
- Fast execution times for all hooks
- Seamless integration with existing CI setup
- Comprehensive error handling and configuration
- Zero conflicts with existing development workflow

**Story Completion:**
✅ All acceptance criteria met exactly as specified
✅ Implementation follows best practices
✅ Excellent developer experience with clear documentation
✅ Maintains consistency with existing project structure
✅ Ready for production use by contributors
