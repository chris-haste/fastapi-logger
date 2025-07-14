Story 8.1 – Loki Sink: Basic Push Support  
───────────────────────────────────  
Epic: 8 – Loki Integration  
Sprint Target: Sprint #⟪next⟫  
Story Points: 8

**As a developer running a Loki/Grafana stack**  
I want log events to be sent directly to a Loki endpoint  
So that I can search and visualize logs using Grafana.

───────────────────────────────────  
Acceptance Criteria

- A `LokiSink` class is implemented under `fapilog/sinks/loki.py`
- Log entries are pushed via HTTP to a Loki-compatible `/loki/api/v1/push` endpoint
- Endpoint URL, auth headers, and tenant (if applicable) are configurable
- Batches logs efficiently (by stream) and supports async transport using `httpx.AsyncClient`
- Logs are grouped by `stream_labels` (e.g., `app`, `env`, `level`)
- Unit tests simulate push to a mock Loki server and confirm request structure
- Loki sink is enabled via `[project.optional-dependencies.loki]`
- README includes a Loki usage section with example config

───────────────────────────────────  
Tasks / Technical Checklist

1. Implement `LokiSink`:

   - Accepts `LokiSinkConfig` dataclass (URL, labels, auth, etc.)
   - Batches events into streams: `{labels: [(ts, line), ...]}`
   - Sends payloads via `httpx.AsyncClient.post()`
   - Handles retries and logs on failure

2. Add `LOKI_URL`, `LOKI_LABELS`, `LOKI_HEADERS`, `LOKI_TENANT_ID` to `fapilog/settings.py`

   - Use envvar-driven Pydantic settings
   - Default to disabled if no URL is provided

3. Register sink only if `LOKI_URL` is set

   - Append to processor chain dynamically in `configure_logging()`

4. Unit tests in `tests/sinks/test_loki.py`:

   - `test_loki_payload_format()`
   - `test_successful_push()`
   - `test_failure_logging()`
   - Use `httpx_mock` or custom ASGI server

5. Add `loki = ["httpx>=0.27"]` to `pyproject.toml` optional deps

   - Include in `extras_require` and README install guidance

6. README updates:
   - “Loki Integration” section
   - Show required settings and sample log in Grafana format
   - Explain behavior on network failure

───────────────────────────────────  
Dependencies / Notes

- Should avoid blocking the request thread (use async queue if needed)
- This implementation assumes Loki accepts JSON line logs grouped by stream

───────────────────────────────────  
Definition of Done  
✓ Logs can be sent to Loki in proper format  
✓ Config is driven by environment or init  
✓ Tests simulate push and validate format  
✓ PR merged to **main** with reviewer approval  
✓ `CHANGELOG.md` and README updated under _Unreleased → Added_
