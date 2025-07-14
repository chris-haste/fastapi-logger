Story 9.3 – Test Coverage Reporting  
───────────────────────────────────  
Epic: 9 – Developer Experience & CI  
Sprint Target: Sprint #⟪next⟫  
Story Points: 3

**As a contributor to the fapilog library**  
I want to see test coverage information for every test run  
So that I can track coverage regressions and ensure untested code paths are visible.

───────────────────────────────────  
Acceptance Criteria

- Test coverage report is printed in the console when running `hatch run test`
- Minimum coverage threshold is defined (e.g. 80%) and enforced in CI
- GitHub Actions job fails if coverage drops below threshold
- Coverage is measured using `pytest-cov`
- Coverage can be run locally with `hatch run cov` or `pytest --cov`
- Coverage includes `fapilog` package (not tests or venv)

───────────────────────────────────  
Tasks / Technical Checklist

1. Add `pytest-cov` to `[project.optional-dependencies.dev]` in `pyproject.toml`

2. Add coverage settings to `tool.pytest.ini_options` in `pyproject.toml`

   - Use the following TOML block (escape to keep inline):
     ```toml
     [tool.pytest.ini_options]
     addopts = "--cov=fapilog --cov-report=term-missing --cov-fail-under=80"
     ```

3. Update `[tool.hatch.envs.test.scripts]` to allow:

   - `test = "pytest"`
   - `cov = "pytest --cov"`

4. Update GitHub Actions CI job to also run `hatch run cov`
5. Verify CI job fails if coverage is below threshold
6. Add test file (if missing) to verify at least one function is covered
7. Add README section showing how to run with coverage locally

───────────────────────────────────  
Dependencies / Notes

- Only includes console-based reporting (no coverage uploads to services like Codecov)
- Threshold is static and intentionally conservative for now (raise later)
- Enforces basic test hygiene early in development

───────────────────────────────────  
Definition of Done  
✓ Test coverage reported in local and CI runs  
✓ Threshold is enforced and blocks merge if unmet  
✓ README includes instructions  
✓ PR merged to **main** with reviewer approval  
✓ `CHANGELOG.md` updated under _Unreleased → Added_
