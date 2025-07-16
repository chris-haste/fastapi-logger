# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Story 5.2**: File Sink with Rotation Support
  - New `FileSink` class in `fapilog/sinks/file.py` with automatic log rotation using `logging.handlers.RotatingFileHandler`
  - URI-based configuration format: `file:///path/to/log.log?maxBytes=10485760&backupCount=5`
  - Configurable rotation parameters: `maxBytes` (default: 10 MB) and `backupCount` (default: 5)
  - Thread-safe async writing with immediate flush to prevent data loss in crash scenarios
  - Automatic directory creation for log file paths
  - Integration with sink loader in `configure_logging()` for environment-based configuration
  - Comprehensive unit tests (5 tests) covering file creation, rotation behavior, URI parsing, and error handling
  - Tests verify log file creation and writing, rotation occurs when file exceeds threshold, parsed query parameters override defaults, and invalid URIs raise helpful errors
  - Updated README with "File Sink" section documenting configuration, URI format, features, and production usage examples
  - Perfect for production environments requiring persistent logs with automatic size management
  - Support for multiple sinks simultaneously (e.g., `stdout,file:///var/log/app.log`)
- **Story 5.1**: Stdout Sink Implementation
  - Enhanced `StdoutSink` class with new mode parameter supporting `"json"`, `"pretty"`, and `"auto"` options
  - Integration with `structlog.dev.ConsoleRenderer` for proper pretty console output with ANSI color codes
  - Automatic TTY detection in `auto` mode: pretty output in interactive terminals, JSON in non-interactive environments
  - Updated sink integration in `bootstrap.py` to use new mode parameter instead of deprecated `pretty` boolean
  - Comprehensive unit tests (12 tests) covering all output formats, TTY detection, mode selection, and edge cases
  - Tests verify JSON output is compact and valid, pretty output contains ANSI codes, and auto mode correctly detects TTY
  - Updated existing tests in `test_log_queue.py` to use new interface
  - Updated README with "Sink Configuration" section documenting stdout sink usage and mode selection behavior
  - Perfect for development (pretty logs in terminal) and production (JSON logs in Docker/Kubernetes)
  - Default sink behavior with proper integration into async queue system
- **Story 5.3**: Loki Sink via HTTP Push
  - New `LokiSink` class in `fapilog/sinks/loki.py` for pushing logs to Grafana Loki over HTTP
  - Supports `loki://` and `https://` URI-style config with `labels`, `batch_size`, and `batch_interval` parameters
  - Buffers logs and pushes them in batches to `/loki/api/v1/push` using `httpx.AsyncClient`
  - Each log is formatted as a Loki-compatible line: nanosecond timestamp and JSON-serialized event
  - Failures are logged and retried with exponential backoff; clear ImportError if `httpx` is missing
  - Unit tests verify batch formatting, buffering, label parsing, and retry logic
  - README documents Loki support, configuration, and install instructions
- **Story 4.4**: Custom Enricher Registry and Hook Support
  - Global registry for custom enrichers in `fapilog/enrichers.py` with `register_enricher(fn)` and `clear_enrichers()` functions
  - Custom enrichers are automatically included at the end of the processor chain in registration order
  - Enricher functions follow structlog processor signature: `(logger, method_name, event_dict) → event_dict`
  - Duplicate registration prevention (same function reference or name)
  - Exception handling ensures enricher failures don't break the logging pipeline
  - Comprehensive unit tests (13 tests) covering registration, execution order, duplicate handling, and error scenarios
  - Integration tests (5 tests) verifying custom enrichers work correctly in the full pipeline
  - Updated README with "Custom Enrichers" section including usage examples and best practices
  - Enables application-specific metadata injection without modifying core library
  - Test isolation support via `clear_enrichers()` for clean test state
- **Story 4.3**: Request Size & Response Size Enricher
  - New `body_size_enricher` processor that specifically adds `req_bytes` and `res_bytes` fields to log events
  - Request body size capture via `Content-Length` header or body size calculation
  - Response body size capture via `len(response.body)` when available
  - Works for standard JSON, form, and plain requests with graceful fallback to `Content-Length` header
  - Enricher positioned after context and before final rendering in processor chain
  - Logs emitted outside HTTP context do not raise errors—fields are omitted gracefully
  - Comprehensive unit tests verifying accurate request/response size measurement for various methods
  - Tests verify enricher skips gracefully when context is missing and field values are numeric
  - Integration with existing `TraceIDMiddleware` infrastructure for context variable management
  - Fields are only added if not already present, allowing manual override of values
  - Updated README "Log Fields" section already documents `req_bytes` and `res_bytes` fields
- **Story 4.2**: Memory & CPU Snapshot Enricher
  - New `resource_snapshot_enricher` processor that adds `memory_mb` and `cpu_percent` fields to all log events
  - Memory usage capture via `psutil.Process().memory_info().rss` converted to megabytes (rounded float)
  - CPU usage capture via `psutil.Process().cpu_percent(interval=None)` as percentage (0.0-100.0)
  - Cached `psutil.Process()` object for performance optimization using `@lru_cache`
  - Optional dependency on `psutil>=5.9` via `fapilog[metrics]` package
  - Conditional inclusion based on `LoggingSettings.enable_resource_metrics` (default: False)
  - Environment variable support: `FAPILOG_ENABLE_RESOURCE_METRICS` for easy configuration
  - Graceful error handling for cases where process info cannot be retrieved (OSError, AttributeError)
  - Fields are only added if not already present, allowing manual override of values
  - Enricher positioned after request/response enricher, before sampling processor
  - Comprehensive unit tests covering field presence, value validation, opt-out logic, and error handling
  - Integration tests verifying pipeline inclusion/exclusion based on settings
  - Updated README with "Resource Metrics" section including configuration, dependencies, and performance considerations
  - Updated "Log Fields" documentation to include `memory_mb` and `cpu_percent` fields
- **Story 4.1**: Hostname & Process Info Enricher
  - New `host_process_enricher` processor that adds `hostname` and `pid` fields to all log events
  - Automatic hostname detection via `socket.gethostname()` with performance caching using `@lru_cache`
  - Process ID capture via `os.getpid()` with caching for optimal performance
  - Fields are only added if not already present, allowing manual override of values
  - Enricher positioned early in processor chain (before redaction and rendering)
  - Zero external dependencies beyond standard library (`socket`, `os`)
  - Comprehensive unit tests covering field presence, manual override, caching, and edge cases
  - Updated README "Log Fields" section to document `hostname` and `pid` fields
  - Integration with existing processor pipeline ensuring consistent log format
- **Story 3.4**: Load Testing the Logging Queue
  - Comprehensive load testing script (`scripts/load_test_log_queue.py`) for simulating high-throughput logging scenarios
  - Configurable test parameters via CLI arguments or environment variables: concurrency, rate, duration, queue settings
  - Performance metrics tracking: total logs attempted, successfully enqueued, dropped logs, average enqueue latency
  - Support for all overflow strategies (drop, block, sample) with detailed performance reporting
  - Integration with hatch scripts: `hatch run test-queue-load` for easy execution
  - Updated README with "Benchmarking Logging Queue" section including usage examples and performance targets
  - Performance assessment with latency thresholds: <100 µs (excellent), <500 µs (good), >500 µs (poor)
  - Environment variable support for all test parameters: `LOAD_TEST_CONCURRENCY`, `LOAD_TEST_RATE`, `LOAD_TEST_DURATION`, etc.
  - Detailed test output with min/max latency, throughput analysis, and queue configuration summary
  - No external dependencies beyond `fapilog` and standard library modules
- **Story 3.3**: Queue Overflow Strategy: Drop, Block, or Sample
  - Configurable queue overflow handling via `LoggingSettings.queue_overflow` with three strategies:
    - `drop`: Silently discard logs when queue is full (default)
    - `block`: Wait for queue space before continuing (guaranteed delivery)
    - `sample`: Use probabilistic sampling when queue is full (adaptive logging)
  - Enhanced `QueueWorker.enqueue()` method to respect overflow strategy settings
  - Updated `queue_sink()` processor to handle different overflow strategies in sync contexts
  - Comprehensive unit tests for all overflow strategies with proper async/sync behavior
  - Updated README with "Controlling Queue Overflow Behavior" section and configuration examples
  - Environment variable support: `FAPILOG_QUEUE_OVERFLOW` for strategy selection
  - Integration with existing `sampling_rate` setting for sample strategy
- **Story 3.2**: Background Queue Worker & Graceful Shutdown
  - Enhanced `QueueWorker` shutdown with proper event loop management and timeout handling
  - Added `shutdown_sync()` method for safe shutdown from sync contexts (atexit, CLI)
  - Fixed event loop conflicts during shutdown using `run_coroutine_threadsafe`
  - Improved shutdown reliability with 5-second timeout to prevent hanging
  - Queue worker now tracks its event loop and ensures shutdown runs on the correct loop
  - Graceful degradation: if worker loop is unavailable, falls back to `asyncio.run()`
  - All tests now pass with robust async/sync shutdown handling
  - Updated test suite to use `@pytest.mark.asyncio` decorators for async tests
  - Fixed pytest-asyncio compatibility issues by pinning to version 0.23.6
- **Story 3.1**: Non-Blocking In-Process Log Queue
  - Async log queue implementation using `asyncio.Queue` for non-blocking logging
  - Background `QueueWorker` coroutine that processes log events in batches
  - Graceful degradation: when queue is full, events are dropped silently to prevent blocking
  - Retry logic with exponential backoff for failed sink writes
  - Graceful shutdown via `atexit` or FastAPI `on_shutdown` handlers
  - Comprehensive unit tests verifying queue behavior, capacity limits, and non-blocking performance
  - Queue configuration via environment variables: `FAPILOG_QUEUE_ENABLED`, `FAPILOG_QUEUE_SIZE`, `FAPILOG_QUEUE_BATCH_SIZE`, etc.
  - Updated README with "Async Logging Queue" section documenting performance benefits and configuration
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
- **Story 5.4**: Multi-Sink Fan-out Support
  - Logging now supports multiple sinks in parallel (fan-out) via the `FAPILOG_SINKS` environment variable or programmatic configuration.
  - All sinks receive the same log event; failures in one sink do not block others (full error isolation).
  - Internal runner uses `asyncio.gather(..., return_exceptions=True)` for concurrent, robust delivery.
  - Misconfigured sinks raise errors at startup, not at runtime.
  - Comprehensive unit tests in `tests/test_multi_sink.py` verify fan-out, error isolation, and startup validation.
  - README updated with a dedicated "Multiple Sink Support" section and usage examples.

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
