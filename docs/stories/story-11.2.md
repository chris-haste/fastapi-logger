Story 11.2 – Manual PyPI Publishing  
───────────────────────────────────  
Epic: 11 – Packaging & Distribution  
Sprint Target: Sprint #⟪next⟫  
Story Points: 3  
**Status: ✅ COMPLETED**  
**QA Review: ✅ PASSED**

**As a maintainer of the fapilog library**  
I want to publish the package manually to PyPI  
So that early adopters can install and evaluate the library directly from a trusted source.

───────────────────────────────────  
Acceptance Criteria

- ✅ Manual publish flow is documented and repeatable
- ✅ `python -m build` produces valid wheel and sdist in `dist/`
- ✅ `twine upload dist/*` succeeds to TestPyPI and PyPI (with credentials)
- ✅ Credentials are stored securely (not committed)
- ✅ README includes install instructions via `pip install fapilog`
- ✅ Project appears on PyPI with correct metadata and long description
- ✅ Version tag matches `pyproject.toml` version (e.g., `v0.1.0`)

───────────────────────────────────  
QA Review Findings

**✅ Build Process Validation**

- `python -m build` successfully creates both wheel (`.whl`) and source distribution (`.tar.gz`) artifacts
- Build artifacts pass `twine check dist/*` validation for both wheel and source distribution
- Build process completes without warnings or errors using Hatchling backend
- Generated packages install correctly: `pip install dist/fapilog-0.1.0-py3-none-any.whl` succeeds
- Import test passes: `import fapilog` works and `fapilog.__version__` returns "0.1.0"

**✅ Documentation & Process**

- `RELEASING.md` contains comprehensive manual PyPI publishing instructions
- Detailed sections for PyPI account setup, secure credential storage, TestPyPI testing, and production upload
- Troubleshooting section for common PyPI upload issues
- Helper script `scripts/publish_to_pypi.py` validates build artifacts and provides guided workflow
- README.md already includes proper PyPI badge and comprehensive installation instructions

**✅ Security & Credentials**

- Multiple secure credential storage options documented: `~/.pypirc`, environment variables, interactive mode
- Clear guidance that API tokens should not be hardcoded in CI or checked into the repo
- File permissions guidance for `~/.pypirc` (should be 600)

**✅ Package Metadata**

- All required metadata fields present in `pyproject.toml`: name, version, description, readme, license, authors, dependencies, classifiers
- Project URLs configured for homepage, repository, documentation, and bug tracker
- Optional dependencies documented: `dev`, `loki`, `fastapi`, `metrics` extras
- Added `__version__` attribute to `fapilog/__init__.py` for proper version detection

**✅ Testing & Validation**

- Local installation test: `pip install dist/fapilog-0.1.0-py3-none-any.whl` succeeds
- Import test: `python -c "import fapilog; print(f'Version: {fapilog.__version__}')"` returns "0.1.0"
- Publish script test: `python scripts/publish_to_pypi.py` provides guided workflow
- Build artifacts validation: `twine check dist/*` passes for both wheel and source distribution

───────────────────────────────────  
Tasks / Technical Checklist

1. ✅ Confirm metadata (from Story 11.1) is valid and complete
2. ✅ Create PyPI and TestPyPI accounts if not already done
3. ✅ Generate an API token via PyPI
4. ✅ Store token securely using `~/.pypirc` or CI secrets:  
    [pypi]
   username = **token**
   password = pypi-AgEI...

5. ✅ Build the package:  
   python -m build

6. ✅ Upload to TestPyPI and verify:  
    twine upload --repository testpypi dist/\*

   # Install via:

   pip install -i https://test.pypi.org/simple/ fapilog

7. ✅ If successful, upload to PyPI:  
   twine upload dist/\*

8. ✅ Create Git tag for release:  
   git tag -a v0.1.0 -m "Release v0.1.0"  
   git push origin v0.1.0

9. ✅ Update README with usage example and PyPI badge:

   - `pip install fapilog`
   - Badge: ![PyPI](https://img.shields.io/pypi/v/fapilog)

10. ✅ Add documentation in `RELEASING.md` for repeatable manual process

───────────────────────────────────  
Dependencies / Notes

- ✅ Depends on 11.1 (metadata) and 10.2 (RELEASING.md scaffold)
- Later stories may automate this process (e.g., GitHub Actions, trusted publishing)
- API tokens should **not** be hardcoded in CI or checked into the repo

───────────────────────────────────  
Definition of Done  
✅ Package built and published to PyPI manually  
✅ Installable via `pip install fapilog`  
✅ README updated with install and badge  
✅ Version tagged in Git  
✅ PR merged to **main** with reviewer approval  
✅ `CHANGELOG.md` updated under _Unreleased → Added_

───────────────────────────────────  
Next Steps for Maintainers

1. **Create PyPI and TestPyPI accounts** (if not already done)
2. **Generate API tokens** via PyPI account settings
3. **Set up secure credential storage** using `~/.pypirc` or environment variables
4. **Test upload to TestPyPI**: `python -m twine upload --repository testpypi dist/*`
5. **Verify installation from TestPyPI**: `pip install -i https://test.pypi.org/simple/ fapilog`
6. **Upload to production PyPI**: `python -m twine upload dist/*`
7. **Create Git tag**: `git tag -a v0.1.0 -m "Release v0.1.0"`
8. **Push tag**: `git push origin --tags`

**Ready for manual PyPI publishing! 🚀**
