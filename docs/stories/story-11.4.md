Story 11.4 – Trusted Publishing with GitHub Actions  
───────────────────────────────────  
Epic: 11 – Packaging & Distribution  
Sprint Target: Sprint #⟪next⟫  
Story Points: 5

**As a library maintainer**  
I want to automate package publishing to PyPI using GitHub Actions  
So that I can safely release new versions with tags and avoid manual upload steps.

───────────────────────────────────  
Acceptance Criteria

- GitHub Actions workflow exists to publish tagged versions to PyPI
- Uses Trusted Publishing (no API token) or secure OIDC-based upload
- Only runs on `push` to `main` with a valid version tag (e.g., `v0.1.2`)
- Workflow builds both sdist and wheel
- Publish only occurs if build passes and tag version matches `pyproject.toml`
- Manual release is no longer required after setup
- README and RELEASING.md updated to reflect new automated process

───────────────────────────────────  
Tasks / Technical Checklist

1.  Enable Trusted Publishing in PyPI project settings

    - Link GitHub repo under PyPI project settings → “Trusted Publishers”
    - Select `workflow` and verify org/repo access

2.  Create `.github/workflows/publish.yml`:  
     name: Publish to PyPI

    on:
    push:
    tags: - 'v\*'

    permissions:
    id-token: write
    contents: read

    jobs:
    publish:
    runs-on: ubuntu-latest
    steps: - uses: actions/checkout@v4 - uses: actions/setup-python@v5
    with:
    python-version: '3.11'

             - name: Install build tools
               run: pip install build

             - name: Build package
               run: python -m build

             - name: Publish to PyPI
               uses: pypa/gh-action-pypi-publish@release/v1

3.  Verify that workflow:

    - Runs only on semver tags
    - Publishes successfully to PyPI
    - Fails cleanly if version mismatch occurs

4.  Update `RELEASING.md`:

    - Remove manual `twine upload` steps
    - Describe how to tag and push to trigger publish

5.  Tag a patch version (e.g., `v0.1.1`) and confirm end-to-end automation

───────────────────────────────────  
Dependencies / Notes

- Depends on Story 11.2 (manual PyPI publish)
- PyPI’s Trusted Publishing must be enabled manually through the UI
- Avoids token leakage risks by using GitHub’s OIDC integration

───────────────────────────────────  
Definition of Done  
✓ Workflow file committed and merged  
✓ PyPI publishing works via GitHub Actions  
✓ Tagging and pushing a new version triggers release  
✓ README and RELEASING.md updated accordingly  
✓ `CHANGELOG.md` updated under _Unreleased → Added_
