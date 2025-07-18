Story 10.2 – Semantic Versioning and Manual Release Process  
───────────────────────────────────  
Epic: 10 – Release & Versioning  
Sprint Target: Sprint #⟪next⟫  
Story Points: 3

**As a maintainer of the fapilog library**  
I want to tag and version releases using semantic versioning  
So that consumers and downstream tools can track compatibility and upgrades.

───────────────────────────────────  
Acceptance Criteria

- The project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
- Release tags are in the format `vMAJOR.MINOR.PATCH`, e.g., `v0.1.0`
- Manual release instructions are documented in `RELEASING.md`
- A release bumps the version in `pyproject.toml`, updates the `CHANGELOG.md`, and creates a git tag
- The release tag includes a message linking to the changelog section
- Build artifacts are created using `python -m build` as in Story 9.4
- Tags are pushed to GitHub (automated PyPI publishing may come later)

───────────────────────────────────  
Tasks / Technical Checklist

1. Add a `RELEASING.md` guide with the following steps:

   - Bump version in `pyproject.toml`
   - Move changelog entries from `Unreleased` to `## [x.y.z] - YYYY-MM-DD`
   - Commit with message: `chore(release): vX.Y.Z`
   - Create a signed tag: `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
   - Push: `git push origin main --tags`
   - Build: `python -m build`
   - (Optional) Upload manually to PyPI (future)

2. Update `pyproject.toml` with initial version `0.1.0` if not already set

3. Add semantic version classifiers in `pyproject.toml`:

   - `"Development Status :: 3 - Alpha"`
   - `"Intended Audience :: Developers"`
   - `"License :: OSI Approved :: MIT License"`
   - `"Programming Language :: Python :: 3.11"`

4. Confirm `CHANGELOG.md` entries align with new release version

5. Perform a dry-run local release:

   - Tag a test version (e.g., `v0.1.0-test`)
   - Confirm tag, changelog, and build are correct

6. Add README link or badge for latest release tag (optional)

───────────────────────────────────  
Dependencies / Notes

- Future automation (e.g., GitHub Releases, PyPI upload) will build on this manual flow
- Version bump should always be associated with a meaningful CHANGELOG update
- Hatch or bump2version automation may be considered later

───────────────────────────────────  
Definition of Done  
✓ RELEASING.md added with clear steps  
✓ Semantic versioning policy in place  
✓ Tagging process confirmed with test release  
✓ PR merged to **main** with reviewer approval  
✓ `CHANGELOG.md`, `pyproject.toml`, and tags aligned

**✅ COMPLETED - All Acceptance Criteria Met**
