# GitHub Epic Labels Reference

This document provides a comprehensive mapping of GitHub epic labels to help automatically determine which epic is most appropriate for issues and stories.

## Epic Label Mapping

### `epic:core-foundation` (Epic 1 – Core Library Foundation)

**GitHub Description:** Core Library Foundation  
**Focus Areas:**

- Project scaffold and packaging setup
- Basic logging facade and `configure_logging()` function
- `LoggingSettings` with Pydantic and environment variable mapping
- Default structlog pipeline (JSON formatter + pretty console)
- Basic unit tests for facade and settings

**When to Use:**

- Setting up project structure, build tools, or packaging
- Core logging configuration and setup functionality
- Basic logging facade implementation
- Environment variable configuration systems
- Fundamental project infrastructure

**Example Issues:**

- Project scaffold creation (pyproject.toml, packaging)
- Implementing `configure_logging()` bootstrap
- Adding basic unit test framework
- Core library API design

---

### `epic:middleware-context` (Epic 2 – Middleware & Context Propagation)

**GitHub Description:** Middleware & Context Propagation  
**Focus Areas:**

- TraceIDMiddleware (generate/forward trace_id, span_id)
- Request timing and status-code enrichment
- ContextVars management to avoid cross-request leakage
- FastAPI middleware integration

**When to Use:**

- HTTP middleware development
- Request/response trace correlation
- Context propagation between requests
- Request timing and metadata collection
- FastAPI-specific middleware features

**Example Issues:**

- Implementing trace ID generation
- Adding request timing middleware
- Context variable management
- Middleware test coverage

---

### `epic:async-logging` (Epic 3 – Async Logging Infrastructure)

**GitHub Description:** Async Logging Infrastructure  
**Focus Areas:**

- Non-blocking in-process queue implementation
- Background worker coroutine with graceful shutdown
- Back-pressure and overflow strategies (drop, block, sampling)
- High-performance async logging architecture

**When to Use:**

- Asynchronous logging systems
- Queue-based log processing
- Background worker implementation
- Performance optimization for high-throughput logging
- Graceful shutdown and resource management

**Example Issues:**

- Implementing async log queues
- Background worker coroutines
- Load testing and performance validation
- Overflow strategy implementation

---

### `epic:field-enrichers` (Epic 4 – Field Enrichers)

**GitHub Description:** Field Enrichers  
**Focus Areas:**

- Hostname and process info enrichers
- Memory/CPU snapshot enrichers
- Request/response size enrichment
- Extensible registry for custom enrichers

**When to Use:**

- Adding metadata to log events
- System resource monitoring
- Process and host information collection
- Custom enricher development
- Registry systems for enrichers

**Example Issues:**

- Adding hostname/PID enrichers
- CPU and memory monitoring
- Custom enricher registry
- Request size tracking

---

### `epic:sink-implementations` (Epic 5 – Sink Implementations)

**GitHub Description:** Sink Implementations  
**Focus Areas:**

- Stdout sink (sync fallback + async writer)
- Rotating file sink implementation
- HTTP-based sinks (Loki, custom endpoints)
- Plugin interface for third-party sinks

**When to Use:**

- Log output destinations (files, stdout, HTTP endpoints)
- Sink implementation and interfaces
- Log rotation and file management
- Third-party logging service integration
- Plugin architecture for sinks

**Example Issues:**

- File sink implementation
- Stdout sink with async support
- Log rotation features
- Third-party sink plugins

---

### `epic:contextual-enrichers` (Epic 6 – Contextual Enrichers)

**GitHub Description:** Contextual Enrichers  
**Focus Areas:**

- Request metadata enrichment (method, path, status, duration, client IP)
- Correlation and trace ID propagation
- User and authentication context enrichment

**When to Use:**

- HTTP request context enrichment
- User authentication context
- Request correlation across services
- Client information tracking
- Session and security context

**Example Issues:**

- Request metadata enrichers
- User context propagation
- Authentication enrichment
- Client IP tracking

---

### `epic:data-redaction` (Epic 7 – Security & Redaction)

**GitHub Description:** Data Redaction  
**Focus Areas:**

- Regex-based field masking utilities
- Allow-list/deny-list filter stages
- PII (Personally Identifiable Information) detection
- Security and compliance features

**When to Use:**

- Data privacy and security
- PII detection and redaction
- Field masking and filtering
- Compliance requirements (GDPR, HIPAA, SOC2)
- Security logging practices

**Example Issues:**

- PII auto-detection
- Field redaction systems
- Security compliance features
- Data masking utilities

---

### `epic:loki-integration` (Subset of Epic 5 – Loki-Specific Features)

**GitHub Description:** Loki Integration  
**Focus Areas:**

- Grafana Loki HTTP sink implementation
- Loki-specific batching and retry logic
- Loki query optimization
- Grafana dashboard integration

**When to Use:**

- Grafana Loki logging backend
- Loki-specific features and optimizations
- Grafana dashboard integration
- Loki query and indexing optimization

**Example Issues:**

- Loki HTTP sink implementation
- Loki batch processing
- Grafana integration features
- Loki-specific configuration

---

### `epic:architecture-improvements` (Epic 13 – Architecture Improvements)

**GitHub Description:** Architecture Improvements  
**Focus Areas:**

- Eliminating global state and implementing dependency injection
- Refactoring large functions into smaller, focused functions
- Standardizing error handling patterns
- Plugin architecture and registry systems
- Performance benchmarks and optimization

**When to Use:**

- Code quality improvements
- Architecture refactoring
- Error handling standardization
- Plugin and registry systems
- Performance optimization
- Technical debt reduction

**Example Issues:**

- Dependency injection implementation
- Function refactoring
- Error handling patterns
- Plugin registry systems
- Performance benchmarking

---

### `epic:developer-experience` (Epic 9 – Developer Experience & CI)

**GitHub Description:** Developer Experience & CI  
**Focus Areas:**

- Development tools (pre-commit, linting, type checking)
- CI/CD pipeline setup
- Release automation and packaging
- Developer workflow optimization

**When to Use:**

- Development tooling and workflow
- CI/CD pipeline configuration
- Code quality tools (linting, type checking)
- Developer productivity enhancements
- Build and release automation

**Example Issues:**

- Pre-commit hook setup
- CI/CD pipeline configuration
- Linting and type checking tools
- Release automation

---

### `epic:documentation` (Epic 15 – Documentation Overhaul)

**GitHub Description:** Documentation  
**Focus Areas:**

- Comprehensive documentation (README, API docs, examples)
- ReadTheDocs integration and structure
- Developer-centric documentation style
- Quickstart guides and tutorials

**When to Use:**

- Documentation creation and improvement
- API reference documentation
- User guides and tutorials
- Documentation infrastructure
- Example code and samples

**Example Issues:**

- API documentation generation
- User guide creation
- Documentation site setup
- Example code development

---

### `epic:packaging-distribution` (Epic 12 – Packaging & Distribution)

**GitHub Description:** Packaging & Distribution  
**Focus Areas:**

- Python packaging and distribution
- PyPI publishing automation
- Package metadata and dependencies
- Distribution optimization

**When to Use:**

- Python package management
- PyPI publishing and distribution
- Package configuration
- Dependency management
- Distribution automation

**Example Issues:**

- PyPI package configuration
- Distribution automation
- Package dependency management
- Publishing pipeline setup

---

### `epic:release-versioning` (Epic 12 – Release & Versioning)

**GitHub Description:** Release & Versioning  
**Focus Areas:**

- Version management and release processes
- Changelog generation
- Release automation
- Version compatibility

**When to Use:**

- Release process automation
- Version management
- Changelog maintenance
- Release documentation
- Version compatibility

**Example Issues:**

- Automated release processes
- Version bump automation
- Changelog generation
- Release documentation

---

## Automatic Epic Assignment Guidelines

### Priority Order for Classification

When an issue could fit multiple epics, use this priority order:

1. **Architecture/Technical Debt** → `epic:architecture-improvements`
2. **Core Functionality** → `epic:core-foundation`
3. **Specific Feature Area** → Use specific epic (e.g., `epic:data-redaction`, `epic:async-logging`)
4. **Infrastructure/Tooling** → `epic:developer-experience`
5. **Documentation** → `epic:documentation`

### Keywords for Automatic Detection

#### Core Foundation

- Keywords: scaffold, packaging, configure_logging, bootstrap, settings, pydantic, environment
- File patterns: `pyproject.toml`, `src/fapilog/__init__.py`, `bootstrap.py`, `settings.py`

#### Middleware & Context

- Keywords: middleware, trace, correlation, context, request, response, FastAPI
- File patterns: `middleware.py`, `context.py`, `trace.py`

#### Async Logging

- Keywords: async, queue, worker, background, performance, non-blocking, coroutine
- File patterns: `queue.py`, `worker.py`, async-related files

#### Field Enrichers

- Keywords: enricher, metadata, hostname, process, memory, CPU, system
- File patterns: `enrichers.py`, enricher-related files

#### Sink Implementations

- Keywords: sink, output, file, stdout, loki, destination, writer
- File patterns: `sinks/`, sink-related files

#### Data Redaction

- Keywords: redaction, PII, mask, security, privacy, compliance, GDPR
- File patterns: `redactors.py`, `pii_patterns.py`, security-related files

#### Architecture Improvements

- Keywords: refactor, architecture, global state, dependency injection, registry, performance
- File patterns: `container.py`, `registry.py`, architecture improvements

#### Developer Experience

- Keywords: CI, CD, lint, test, pre-commit, tox, hatch, development
- File patterns: `.github/`, `tox.ini`, `pyproject.toml` (dev tools)

#### Documentation

- Keywords: documentation, docs, README, examples, tutorial, guide
- File patterns: `docs/`, `README.md`, `examples/`

### Example Classification Logic

```python
def classify_epic(issue_title, issue_body, file_paths):
    """
    Classify an issue into the most appropriate epic based on content analysis.

    Returns the epic label that best matches the issue.
    """
    # Implementation would analyze keywords, file patterns, and context
    # to automatically suggest the most appropriate epic label
    pass
```

This mapping enables automatic epic classification based on issue content, file paths, and keyword analysis, ensuring consistent project organization and reducing manual classification overhead.
