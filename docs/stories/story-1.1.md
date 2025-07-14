# Story 1.1 – Initial Project Scaffold

**Epic:** 1 – Core Library Foundation  
Sprint Target: Sprint #⟪next⟫  
Story Points: 8

**As a library maintainer**  
I want a fully boot-strapped, installable project skeleton (packaging + build tooling)  
So that every contributor can clone, run the test-suite, and install `fapilog` with one command.

───────────────────────────────────  
Acceptance Criteria

- `pip install -e .` from the repo root succeeds **and** `python -c "import fapilog"` runs without errors.
- `pytest` executes (even when no tests) and returns exit-code 0.
- `hatch run lint`, `hatch run typecheck`, and `hatch run test` all pass locally.
- `tox -q` succeeds for default envs (py311).
- `python -m build` produces a valid wheel **and** sdist in `dist/`.
- `pyproject.toml` contains project metadata (name, version, license, author, classifiers) and two optional-dependency groups:  
  • `dev` → lint, type, test deps  
  • `loki` → HTTP deps for the Loki sink
- Repo includes an **MIT** or **Apache-2.0** LICENSE file matching metadata.
- README “Development Setup” section accurately reflects the workflow above.

───────────────────────────────────  
Tasks / Technical Checklist

1.  **Repo layout**

        fastapi-logger/
        ├── src/fapilog/          # code under src/ for import isolation
        ├── tests/
        ├── pyproject.toml
        └── LICENSE

2.  **`pyproject.toml`**

    - Build backend: `hatchling`
    - Core deps: `structlog`, `pydantic>=2`, `anyio`
    - Optional deps (`[project.optional-dependencies]`)  
      • `dev = ["pytest", "ruff", "mypy", "pytest-cov"]`  
      • `loki = ["httpx>=0.27"]`

3.  **Hatch config** – set up `[tool.hatch.envs]` for `lint`, `typecheck`, and `test`.

4.  **tox** – add `tox.ini` (or `[tool.tox]` in `pyproject.toml`) mirroring Hatch commands.

5.  **`__init__.py`** stub

        __all__ = ["configure_logging", "log"]

        # Temporary placeholder until full implementation
        from ._internal.utils import get_logger as log
        from .settings import configure_logging

6.  **Pre-commit** (optional) – `.pre-commit-config.yaml` with Ruff, MyPy, Black.

7.  **Smoke test**

        # tests/test_import.py
        import fapilog

        def test_import():
            assert hasattr(fapilog, "configure_logging")

8 **README update** – add “Development Setup” block:

        git clone <repo>
        cd fastapi-logger
        python -m venv .venv && source .venv/bin/activate
        pip install -e ".[dev]"
        hatch run test

───────────────────────────────────  
Dependencies / Notes

- No external service dependencies; green-field start.
- CI setup (GitHub Actions/Drone) handled later (Epic 9).
- Placing code under `src/` prevents accidental imports from the working directory during tests.

───────────────────────────────────  
Summary of Achievements (Sprint Review)

- Project structure migrated to a modern `src/` layout for import isolation.
- `pyproject.toml` created with full project metadata, core and optional dependencies, and Hatch build configuration.
- Hatch environments for linting, type checking, and testing are set up and working.
- `tox.ini` added to mirror Hatch commands for CI compatibility.
- `src/fapilog/__init__.py` exports `configure_logging` and `log` as placeholders, matching the intended API.
- Placeholder implementations for `get_logger` and `configure_logging` provided.
- Initial smoke test (`tests/test_import.py`) verifies import and API surface.
- MIT LICENSE file added, matching project metadata.
- README updated with a clear "Development Setup" section and development workflow.
- All acceptance criteria verified: editable install, import, lint, typecheck, test, and build all succeed locally.
- Linting and type checking pass with no errors; test suite passes with 100% for the current API surface.

───────────────────────────────────  
Definition of Done  
✓ All acceptance criteria met.  
✓ Story merged to **main** via PR with at least one reviewer approval.  
✓ `CHANGELOG.md` entry added under _Unreleased → Added_.  
✓ CI on **main** branch (if present) remains green.
