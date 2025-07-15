# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Story 2.3**: ContextVar Utilities & Leak Prevention
  - ContextVar utilities for safe context management with `get_context()`, `bind_context()`, `clear_context()`, and `context_copy()` functions
  - Automatic context propagation to background tasks using `asyncio.create_task(context_copy().run(func))`
  - Context leak prevention ensuring separate requests receive different trace_ids
  - Comprehensive unit tests for context utilities with 100% coverage
  - Background task context propagation example in README
- Request & Response Metadata Enricher with automatic capture of HTTP status codes, request/response body sizes, latency, and user-agent information
- Automatic enrichment of all log events with `status_code`, `latency_ms`, `req_bytes`, `res_bytes`, and `user_agent` fields
- Comprehensive unit tests for request/response metadata enrichment covering POST requests with bodies, GET requests without bodies, and out-of-context logging
- Baseline unit tests with comprehensive coverage for core functionality
- Coverage gate enforcing minimum 85% test coverage threshold
- GitHub Actions CI workflow with automated test execution
- Expanded test suite covering import/bootstrap path, settings validation, and processor pipeline
- Test coverage reporting with HTML and terminal output
- **Story 2.4**: Test Coverage for Middleware & Context Propagation
  - Achieved ≥90% enforced test coverage for `middleware.py` and `context.py` (trace propagation, request/response enrichment, context utilities)
  - Added/expanded tests for TraceIDMiddleware: header passthrough, trace generation, context cleanup, error handling, and idempotent registration
  - Verified request/response metadata enrichment (status code, latency, byte sizes, user-agent)
  - Ensured context utility helpers (`get_context`, `bind_context`, `clear_context`, `context_copy`) are fully covered
  - Added tests for context propagation in background tasks and isolation between concurrent requests (no context leakage)
  - CI and local coverage gate now enforce 90%+ threshold; PRs below threshold will fail
  - Updated README with contributor instructions for running middleware/context tests and viewing coverage delta

### Changed

- Enhanced test_import.py with actual log.info call testing
- Improved test organization and coverage reporting

### Fixed

- None

### Removed

- None

## [0.1.0] - 2024-01-01

### Added

- Initial release of fapilog library
- Core logging functionality with structured JSON output
- FastAPI middleware integration
- Configurable sinks (stdout, loki)
- Environment-based configuration
- Pydantic V2 settings management
