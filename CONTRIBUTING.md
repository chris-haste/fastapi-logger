# Contributing to FastAPI-Logger

Thank you for your interest in contributing to FastAPI-Logger! This document provides guidelines for contributing to the project.

## 🚀 Quick Start

1. **Fork** the repository
2. **Clone** your fork locally
3. **Create** a feature branch: `git checkout -b feat/your-feature`
4. **Make** your changes
5. **Test** your changes locally
6. **Commit** with clear messages
7. **Push** to your fork
8. **Create** a pull request

## 📋 Development Setup

### Prerequisites

- Python 3.11+
- Hatch (for development)

### Local Development

```bash
# Clone and setup
git clone https://github.com/your-username/fastapi-logger.git
cd fastapi-logger

# Install development dependencies
hatch env create
hatch shell

# Run tests
hatch run test:test

# Run linting
hatch run lint:lint

# Run type checking
hatch run typecheck:typecheck

# Build package
python -m build
```

## 🛡️ CI/CD Guidelines

### Workflow Changes

**⚠️ Important**: Changes to CI/CD files require maintainer review and approval.

#### Protected Files

The following files require maintainer approval for changes:

- `.github/workflows/` - All workflow files
- `.github/CODEOWNERS` - Code ownership rules
- `pyproject.toml` - Project configuration
- `tox.ini` - Test environment configuration
- `src/fapilog/` - Core library code

#### Workflow Modification Rules

1. **Test locally first**: Use `act` to test workflows locally
2. **Follow naming conventions**: Use existing job and step names
3. **Document changes**: Explain why changes are needed
4. **Maintain compatibility**: Don't break existing functionality
5. **Security first**: Never commit secrets or sensitive data

#### Required CI Jobs

All pull requests must pass these checks:

- ✅ **Build & Lint** - Code formatting and style
- ✅ **Test (3.11)** - Unit and integration tests
- ✅ **Type Check** - Static type checking
- ✅ **Tox (Compatibility)** - Multi-environment testing

### Testing Workflows Locally

```bash
# Install act (GitHub Actions runner)
brew install act  # macOS
# or download from: https://github.com/nektos/act

# Test a specific workflow
act pull_request -W .github/workflows/ci.yml

# Test with specific event
act push -W .github/workflows/ci.yml
```

## 📝 Code Style

### Python Code

- Follow **PEP 8** style guidelines
- Use **type hints** for all functions
- Write **docstrings** for public APIs
- Keep functions **small and focused**

### Commit Messages

Use conventional commit format:

```
type(scope): description

feat(ci): add workflow validation job
fix(test): resolve import error in tox environment
docs(readme): update installation instructions
```

### Pull Request Guidelines

1. **Clear title**: Describe the change concisely
2. **Detailed description**: Explain what and why
3. **Link issues**: Reference related issues
4. **Test coverage**: Ensure tests pass locally
5. **Documentation**: Update docs if needed

## 🧪 Testing

### Running Tests

```bash
# All tests
hatch run test:test

# Specific test file
hatch run test:test tests/test_bootstrap.py

# With coverage
hatch run test:test --cov=src/fapilog --cov-report=html

# Tox environments
tox -e py311
```

### Test Requirements

- **90%+ coverage** required
- **All tests must pass**
- **No linting errors**
- **Type checking passes**

## 🔧 Development Tools

### Pre-commit Hooks

This project uses pre-commit hooks to ensure code quality. The hooks include:

- **Ruff** - Linting and code formatting
- **MyPy** - Type checking
- **Vulture** - Dead code detection

```bash
# Install development dependencies (includes pre-commit)
pip install -e ".[dev]"

# Install the git hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files

# Run specific hooks
pre-commit run ruff --all-files
pre-commit run mypy --all-files
pre-commit run vulture --all-files
```

### Local Validation

```bash
# Format code
hatch run lint:lint

# Type check
hatch run typecheck:typecheck

# Dead code detection
vulture src/ tests/

# Security scan
bandit -r src/

# Dependency check
safety check
```

### Building Packages

This project uses `python -m build` to create distribution packages. This is useful for testing your changes as a built package or for creating releases.

#### Prerequisites

The build process requires the `build` package, which is included in the dev dependencies:

```bash
# Install dev dependencies (includes build)
pip install -e ".[dev]"
```

#### Building Packages

```bash
# Build both wheel and source distribution
python -m build

# Build only wheel
python -m build --wheel

# Build only source distribution
python -m build --sdist

# Build to specific output directory
python -m build --outdir ./my-dist/
```

#### Testing Built Packages

After building, you can test the packages locally:

```bash
# Install the built wheel
pip install dist/*.whl

# Test that the package works
python -c "import fapilog; print('Package installed successfully!')"

# Uninstall for testing
pip uninstall fapilog -y
```

#### Build Artifacts

The build process creates:

- **Wheel** (`.whl`): Binary distribution for fast installation
- **Source Distribution** (`.tar.gz`): Source code archive for compatibility

Both artifacts are saved to the `dist/` directory, which is automatically ignored by git.

#### Troubleshooting

- **Build fails**: Ensure all dependencies are installed with `pip install -e ".[dev]"`
- **Import errors**: Check that the package structure in `src/fapilog/` is correct
- **Metadata issues**: Verify `pyproject.toml` has all required fields (name, version, description, etc.)

## 🚨 Security Guidelines

### Never Commit

- API keys or tokens
- Database credentials
- Private SSH keys
- Personal information
- Hardcoded passwords

### Security Best Practices

1. **Use environment variables** for secrets
2. **Validate inputs** thoroughly
3. **Sanitize outputs** appropriately
4. **Follow OWASP guidelines**
5. **Report security issues** privately

## 📚 Documentation

### Code Documentation

- **Docstrings**: All public functions and classes
- **Type hints**: Comprehensive type annotations
- **Examples**: Include usage examples
- **API docs**: Keep documentation current

### Project Documentation

- **README.md**: Project overview and quick start
- **CHANGELOG.md**: Version history and changes
- **docs/**: Detailed documentation
- **examples/**: Working code examples

### Changelog Conventions

This project follows the [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format. When contributing:

1. **Add entries under `[Unreleased]`**: All new changes go in the `## [Unreleased]` section
2. **Use appropriate categories**:
   - `### Added` - New features
   - `### Changed` - Changes to existing functionality
   - `### Fixed` - Bug fixes
   - `### Removed` - Removed features
   - `### Deprecated` - Soon-to-be removed features
3. **Include story references**: Reference the story number (e.g., "Story 10.1") for traceability
4. **Be descriptive**: Explain what changed and why it matters to users
5. **Keep entries concise**: Focus on user-visible changes, not implementation details

**Example:**

```markdown
### Added

- **Story 10.1**: CHANGELOG tracking and conventions
  - Added changelog link to README.md
  - Added changelog conventions to CONTRIBUTING.md
  - Established Keep a Changelog format compliance
```

## 🤝 Community Guidelines

### Be Respectful

- **Constructive feedback** only
- **Help newcomers** learn
- **Credit contributors** appropriately
- **Follow the code of conduct**

### Communication

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Questions and general discussion
- **Pull Requests**: Code contributions
- **Releases**: Version announcements

## 🎯 Getting Help

### Before Asking

1. **Check existing issues** for similar problems
2. **Read the documentation** thoroughly
3. **Search discussions** for solutions
4. **Test with minimal examples**

### When Creating Issues

- **Clear title**: Describe the problem
- **Detailed description**: Steps to reproduce
- **Environment info**: OS, Python version, etc.
- **Code examples**: Minimal reproducing code
- **Expected vs actual**: What you expected vs what happened

## 📄 License

By contributing to FastAPI-Logger, you agree that your contributions will be licensed under the same license as the project.

---

Thank you for contributing to FastAPI-Logger! 🚀
