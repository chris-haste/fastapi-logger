## Epic 1 – Core Library Foundation

- **`Story 1.1`**: Create project scaffold (pyproject.toml, packaging, tox/hatch config)
- **`Story 1.2`**: Implement log facade and configure_logging() bootstrap
- **`Story 1.3`**: Design LoggingSettings (Pydantic) with env-var mapping
- **`Story 1.4`**: Provide default structlog pipeline (JSON formatter + pretty console)
- **`Story 1.5`**: Add basic unit tests for facade & settings

## Epic 2 – Middleware & Context Propagation

- Story 2.1: TraceIDMiddleware (generate / forward trace_id, span_id)
- Story 2.2: Request timing & status-code enrichment
- Story 2.3: ContextVars management to avoid cross-request leakage
- Story 2.4: Middleware test coverage with TestClient

## Epic 3 – Async Logging Infrastructure

- Story 3.1: Implement non-blocking in-process queue
- Story 3.2: Background worker coroutine with graceful shutdown hook
- Story 3.3: Back-pressure / overflow strategy (drop, block, sampling toggle)
- Story 3.4: Load-test script to validate queue performance

## Epic 4 – Field Enrichers

- Story 4.1: Hostname & process info enricher
- Story 4.2: Memory / CPU snapshot enricher
- Story 4.3: Request size & response size enrichment
- Story 4.4: Extensible registry for custom enrichers

## Epic 5 – Sink Implementations

- Story 5.1: Stdout sink (sync fallback + async writer)
- Story 5.2: Rotating file sink
- Story 5.3: Loki HTTP sink with batch & retry
- Story 5.4: Plug-in interface for third-party sinks

## Epic 6 – Contextual Enrichers

- Story 6.1: Context Enricher: Request Metadata (method, path, status, duration, client IP)
- Story 6.2: Context Enricher: Correlation + Trace ID Propagation
- Story 6.3: Context Enricher: User and Auth Context

## Epic 7 – Security & Redaction

- Story 7.1: Regex-based field masking utility
- Story 7.2: Allow-list / deny-list filter stage
- Story 7.3: Unit tests for PII redaction paths

## Epic 8 – Observability Integration

- Story 8.1: OpenTelemetry span correlation (traceparent fields)
- Story 8.2: Prometheus counters for error/warn totals
- Story 8.3: Optional slow-SQL timer hook (SQLAlchemy event)

## Epic 9 – Configuration & Runtime Controls

- Story 9.1: FAPILOG_SINKS, FAPILOG_LEVEL, etc. env handling
- Story 9.2: Programmatic overrides (configure_logging(\*\*kwargs))
- Story 9.3: Live log-level toggle endpoint (guarded)
- Story 9.4: Sampling configuration (rate / probabilistic)

## Epic 10 – Test Suite & CI Pipeline

- Story 10.1: Pytest fixtures (caplog_json)
- Story 10.2: Integration tests with Uvicorn & TestClient
- Story 10.3: Performance regression test harness
- Story 10.4: GitHub Actions / Drone CI with lint, type-check, coverage gates

## Epic 11 – Documentation & Developer Experience

- Story 11.1: Expand README.md (quick-start, feature matrix, roadmap)
- Story 11.2: Usage docs for FastAPI + worker scripts
- Story 11.3: Docstrings & sphinx/mkdocs build
- Story 11.4: Example repo / demo docker-compose

## Epic 12 – Copier Template Integration

- Story 12.1: Add fapilog to template dependencies
- Story 12.2: Inject configure_logging() in scaffolded main.py
- Story 12.3: Copier questions → env-var mapping (slow_query, pii_redaction)
- Story 12.4: Template test to assert logs emit in generated project
