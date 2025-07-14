Story 11.2 – Manual PyPI Publishing  
───────────────────────────────────  
Epic: 11 – Packaging & Distribution  
Sprint Target: Sprint #⟪next⟫  
Story Points: 3

**As a maintainer of the fapilog library**  
I want to publish the package manually to PyPI  
So that early adopters can install and evaluate the library directly from a trusted source.

───────────────────────────────────  
Acceptance Criteria

- Manual publish flow is documented and repeatable
- `python -m build` produces valid wheel and sdist in `dist/`
- `twine upload dist/*` succeeds to TestPyPI and PyPI (with credentials)
- Credentials are stored securely (not committed)
- README includes install instructions via `pip install fapilog`
- Project appears on PyPI with correct metadata and long description
- Version tag matches `pyproject.toml` version (e.g., `v0.1.0`)

───────────────────────────────────  
Tasks / Technical Checklist

1. Confirm metadata (from Story 11.1) is valid and complete
2. Create PyPI and TestPyPI accounts if not already done
3. Generate an API token via PyPI
4. Store token securely using `~/.pypirc` or CI secrets:  
    [pypi]
   username = **token**
   password = pypi-AgEI...

5. Build the package:  
    python -m build

6. Upload to TestPyPI and verify:  
    twine upload --repository testpypi dist/\*

   # Install via:

   pip install -i https://test.pypi.org/simple/ fapilog

7. If successful, upload to PyPI:  
    twine upload dist/\*

8. Create Git tag for release:  
    git tag -a v0.1.0 -m "Release v0.1.0"  
    git push origin v0.1.0

9. Update README with usage example and PyPI badge:

   - `pip install fapilog`
   - Badge: ![PyPI](https://img.shields.io/pypi/v/fapilog)

10. Add documentation in `RELEASING.md` for repeatable manual process

───────────────────────────────────  
Dependencies / Notes

- Depends on 11.1 (metadata) and 10.2 (RELEASING.md scaffold)
- Later stories may automate this process (e.g., GitHub Actions, trusted publishing)
- API tokens should **not** be hardcoded in CI or checked into the repo

───────────────────────────────────  
Definition of Done  
✓ Package built and published to PyPI manually  
✓ Installable via `pip install fapilog`  
✓ README updated with install and badge  
✓ Version tagged in Git  
✓ PR merged to **main** with reviewer approval  
✓ `CHANGELOG.md` updated under _Unreleased → Added_
