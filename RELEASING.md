# Releasing fapilog

This document outlines the manual release process for fapilog following [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Prerequisites

- Ensure you have write access to the repository
- Verify all tests pass: `hatch run test:test`
- Ensure linting passes: `hatch run lint:lint`
- Verify type checking passes: `hatch run typecheck:typecheck`

## Release Process

### 1. Prepare the Release

1. **Bump version in `pyproject.toml`**

   ```bash
   # Edit pyproject.toml and update the version field
   # Example: version = "0.1.0" → version = "0.2.0"
   ```

2. **Update CHANGELOG.md**

   - Move entries from `## [Unreleased]` to a new version section
   - Format: `## [X.Y.Z] - YYYY-MM-DD`
   - Example:

     ```markdown
     ## [0.2.0] - 2024-01-15

     ### Added

     - New feature X
     - Enhanced feature Y

     ### Changed

     - Improved performance of Z

     ### Fixed

     - Bug fix in A
     ```

3. **Commit the changes**
   ```bash
   git add pyproject.toml CHANGELOG.md
   git commit -m "chore(release): vX.Y.Z"
   ```

### 2. Create and Push the Tag

1. **Create a signed tag**

   ```bash
   git tag -a vX.Y.Z -m "Release vX.Y.Z"
   ```

   For a more detailed tag message linking to the changelog:

   ```bash
   git tag -a vX.Y.Z -m "Release vX.Y.Z

   See CHANGELOG.md for detailed changes.

   https://github.com/fapilog/fapilog/blob/vX.Y.Z/CHANGELOG.md#xyz---yyyy-mm-dd"
   ```

2. **Push the tag to GitHub**
   ```bash
   git push origin main --tags
   ```

### 3. Build Release Artifacts

1. **Build the package**

   ```bash
   python -m build
   ```

   This creates both wheel (`.whl`) and source distribution (`.tar.gz`) files in the `dist/` directory.

2. **Verify the build artifacts**

   ```bash
   # List the created artifacts
   ls -la dist/

   # Test installation (optional)
   pip install dist/fapilog-X.Y.Z-py3-none-any.whl
   python -c "import fapilog; print('Installation successful')"
   ```

### 4. (Optional) Manual PyPI Upload

For now, PyPI uploads are manual. Future automation will be added.

```bash
# Upload to PyPI (requires PyPI credentials)
python -m twine upload dist/*

# Or upload to TestPyPI first
python -m twine upload --repository testpypi dist/*
```

## Version Numbering

Follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html):

- **MAJOR** version for incompatible API changes
- **MINOR** version for backwards-compatible functionality additions
- **PATCH** version for backwards-compatible bug fixes

### Examples

- `v0.1.0` → `v0.1.1` (patch: bug fix)
- `v0.1.0` → `v0.2.0` (minor: new feature)
- `v0.1.0` → `v1.0.0` (major: breaking change)

## Pre-release Testing

Before creating a release tag, perform a dry-run:

1. **Create a test tag**

   ```bash
   git tag -a vX.Y.Z-test -m "Test release vX.Y.Z"
   ```

2. **Test the build process**

   ```bash
   python -m build
   ```

3. **Delete the test tag**
   ```bash
   git tag -d vX.Y.Z-test
   git push origin :refs/tags/vX.Y.Z-test  # Delete remote tag if pushed
   ```

## Release Checklist

- [ ] All tests pass
- [ ] Linting passes
- [ ] Type checking passes
- [ ] Version bumped in `pyproject.toml`
- [ ] CHANGELOG.md updated with new version section
- [ ] Changes committed with proper message
- [ ] Tag created and pushed
- [ ] Build artifacts created successfully
- [ ] Build artifacts verified (optional installation test)

## Future Automation

This manual process will be enhanced with:

- GitHub Releases integration
- Automated PyPI uploads
- Automated version bumping (e.g., with `bump2version` or `hatch`)
- Automated changelog generation
- Release notes generation from PRs

## Troubleshooting

### Tag already exists

```bash
# Delete local tag
git tag -d vX.Y.Z

# Delete remote tag
git push origin :refs/tags/vX.Y.Z

# Recreate tag
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin main --tags
```

### Build fails

- Ensure all dependencies are installed: `pip install -e ".[dev]"`
- Check for syntax errors: `python -c "import fapilog"`
- Verify `pyproject.toml` is valid

### Push fails

- Ensure you have write access to the repository
- Check if the tag already exists remotely
- Verify your git credentials are configured
