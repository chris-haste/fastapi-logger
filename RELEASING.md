# Releasing fapilog

This document outlines the manual release process for fapilog following [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Prerequisites

- Ensure you have write access to the repository
- Verify all tests pass: `hatch run test:test`
- Ensure linting passes: `hatch run lint:lint`
- Verify type checking passes: `hatch run typecheck:typecheck`
- Install build tools: `pip install build twine`

## Helper Script

For guided PyPI publishing, use the helper script:

```bash
python scripts/publish_to_pypi.py
```

This script will:

- Check prerequisites (build, twine)
- Build the package
- Validate build artifacts
- Check credentials
- Provide step-by-step guidance

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

   https://github.com/chris-haste/fastapi-logger/blob/vX.Y.Z/CHANGELOG.md#xyz---yyyy-mm-dd"
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

### 4. Manual PyPI Publishing

This section covers the complete manual PyPI publishing process for fapilog.

#### 4.1 PyPI Account Setup

1. **Create PyPI Account**

   - Visit [PyPI](https://pypi.org/account/register/) and create an account
   - Verify your email address

2. **Create TestPyPI Account**

   - Visit [TestPyPI](https://test.pypi.org/account/register/) and create an account
   - This is for testing releases before publishing to production PyPI

3. **Generate API Token**
   - Go to [PyPI Account Settings](https://pypi.org/manage/account/)
   - Click "Add API token"
   - Give it a name like "fapilog-upload-token"
   - Copy the token (format: `pypi-AgEI...`)

#### 4.2 Secure Credential Storage

**Option A: Using ~/.pypirc (Recommended)**

Create `~/.pypirc` file:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-AgEI...your-token-here...

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-AgEI...your-test-token-here...
```

**Option B: Environment Variables**

```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-AgEI...your-token-here...
```

**Option C: Interactive (Less Secure)**

```bash
# Twine will prompt for credentials
python -m twine upload dist/*
```

#### 4.3 TestPyPI Upload and Verification

1. **Upload to TestPyPI**

   ```bash
   python -m twine upload --repository testpypi dist/*
   ```

2. **Install from TestPyPI**

   ```bash
   pip install -i https://test.pypi.org/simple/ fapilog
   python -c "import fapilog; print('TestPyPI installation successful')"
   ```

3. **Verify Package Metadata**
   - Visit [TestPyPI fapilog page](https://test.pypi.org/project/fapilog/)
   - Check that description, classifiers, and URLs are correct
   - Verify version matches `pyproject.toml`

#### 4.4 Production PyPI Upload

1. **Upload to PyPI**

   ```bash
   python -m twine upload dist/*
   ```

2. **Verify Upload**

   ```bash
   pip install fapilog
   python -c "import fapilog; print('PyPI installation successful')"
   ```

3. **Check PyPI Page**
   - Visit [PyPI fapilog page](https://pypi.org/project/fapilog/)
   - Verify all metadata is correct
   - Check that README renders properly

#### 4.5 Troubleshooting PyPI Uploads

**Common Issues:**

1. **Package already exists**

   ```bash
   # Check if version already exists
   pip index versions fapilog

   # If version exists, bump version in pyproject.toml
   # Then rebuild and upload
   python -m build
   python -m twine upload dist/*
   ```

2. **Authentication errors**

   ```bash
   # Verify token is correct
   # Check ~/.pypirc file permissions (should be 600)
   chmod 600 ~/.pypirc
   ```

3. **Metadata validation errors**

   ```bash
   # Check package metadata
   python -m twine check dist/*

   # Verify pyproject.toml is valid
   python -c "import tomllib; tomllib.load(open('pyproject.toml', 'rb'))"
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
