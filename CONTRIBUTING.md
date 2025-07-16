# Contributing to fapilog

First, thank you for considering contributing to **fapilog**! Your help is appreciated, whether it's filing an issue, improving documentation, or submitting code.

---

## 📜 Code of Conduct

We follow the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). Please be respectful and constructive in all interactions.

---

## 💡 How to Contribute

You can contribute in many ways:

- File bug reports and feature requests via [GitHub Issues](https://github.com/fapilog/fapilog/issues)
- Improve or clarify the documentation
- Submit bug fixes or new features via Pull Request (PR)
- Add tests for new or existing features
- Improve the async logging queue performance
- Add new sinks (Loki, HTTP endpoints, etc.)
- Enhance the middleware or enrichers

---

## ⚙️ Development Setup

### 1. Fork and Clone

```bash
git clone https://github.com/your-username/fapilog.git
cd fapilog
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -e ".[dev]"
```

This installs the package in editable mode with all development dependencies including:

- `pytest` and `pytest-asyncio` for testing
- `ruff` for linting and formatting
- `mypy` for type checking
- `pytest-cov` for coverage reporting
- `fastapi` and `httpx` for integration tests

### 4. Run the Tests

```bash
hatch run test
```

This runs the full test suite with coverage reporting. The project enforces a minimum coverage threshold of 90%.

### 5. Format and Lint

We use [`ruff`](https://docs.astral.sh/ruff/) for both linting and formatting:

```bash
hatch run lint
```

Or run formatting and linting separately:

```bash
ruff format .
ruff check .
```

### 6. Type Checking

```bash
hatch run typecheck
```

---

## 🧪 Testing

### Running Tests

- **Full test suite**: `hatch run test`
- **Coverage report**: `hatch run test-cov`
- **Load testing**: `hatch run test-queue-load`

### Test Coverage

The project enforces a **90% minimum coverage threshold**. Pull requests must maintain or improve test coverage. Coverage reports are generated in `htmlcov/` after running tests.

### Test Structure

- **Unit tests**: `tests/test_*.py`
- **Integration tests**: Marked with `@pytest.mark.integration`
- **Async tests**: Marked with `@pytest.mark.asyncio`
- **Slow tests**: Marked with `@pytest.mark.slow`

---

## 🏗️ Project Structure

```
src/fapilog/
├── __init__.py          # Public API
├── bootstrap.py         # Logging configuration
├── middleware.py        # FastAPI middleware
├── enrichers.py        # Log enrichment
├── pipeline.py          # Logging pipeline
├── settings.py          # Configuration
├── _internal/          # Internal utilities
│   ├── context.py      # Context management
│   ├── queue.py        # Async queue
│   └── utils.py        # Utilities
└── sinks/              # Log output handlers
    ├── __init__.py
    ├── stdout.py       # Console output
    └── loki.py         # Loki integration
```

### Key Components

- **Middleware**: `TraceIDMiddleware` for request tracing
- **Queue**: Async, non-blocking log processing
- **Sinks**: Pluggable output handlers (stdout, Loki, etc.)
- **Enrichers**: Context-aware log enhancement
- **Settings**: Pydantic-based configuration

---

## ✅ Submitting a Pull Request

1. Create a new branch from `main`:

   ```bash
   git checkout -b feature/my-awesome-feature
   ```

2. Follow existing code style and add appropriate tests.

3. Run tests and lint before submitting:

   ```bash
   hatch run test
   hatch run lint
   hatch run typecheck
   ```

4. Push to your fork and open a PR with a **clear description** of your changes and motivation.

> We squash and merge PRs. Keep commits clean and meaningful.

---

## 🔧 Development Commands

| Command                     | Description                      |
| --------------------------- | -------------------------------- |
| `hatch run lint`            | Run Ruff linter and formatter    |
| `hatch run typecheck`       | Run MyPy type checker            |
| `hatch run test`            | Run pytest with coverage         |
| `hatch run test-cov`        | Run tests with detailed coverage |
| `hatch run test-queue-load` | Run async queue load testing     |

---

## 🧱 Dependencies

### Core Dependencies

- `structlog` - Structured logging (required)
- `pydantic>=2.0.0` - Settings and validation
- `pydantic-settings>=2.0.0` - Configuration management
- `anyio` - Async utilities

### Optional Dependencies

- `fastapi>=0.100.0` - For FastAPI integration
- `httpx>=0.27.0` - For HTTP sinks and testing
- `psutil>=5.9` - For resource metrics

### Development Dependencies

- `pytest>=7.0.0` - Testing framework
- `pytest-asyncio>=0.21.0` - Async test support
- `ruff>=0.1.0` - Linting and formatting
- `mypy>=1.0.0` - Type checking
- `pytest-cov>=4.0.0` - Coverage reporting

**Note**: Your code **may not introduce unnecessary dependencies**. All new dependencies must be justified and approved.

---

## 🚀 Performance Considerations

When contributing to fapilog, consider the performance impact:

- **Async-first**: All I/O operations should be non-blocking
- **Queue efficiency**: The async queue is critical for performance
- **Memory usage**: Avoid unbounded memory growth
- **Context propagation**: Use `contextvars` for request-scoped data

---

## 📝 License

By contributing, you agree that your contributions will be licensed under the MIT License, the same as the rest of the project.

---

Thanks again for helping improve **fapilog**!
