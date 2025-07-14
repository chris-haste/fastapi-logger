Story 5.3 – Loki Sink via HTTP Push  
───────────────────────────────────  
Epic: 5 – Sink Implementations  
Sprint Target: Sprint #⟪next⟫  
Story Points: 8

**As an SRE or observability engineer**  
I want log events to be pushed to a Loki endpoint over HTTP  
So that I can centralize logs from distributed services in a Grafana stack.

───────────────────────────────────  
Acceptance Criteria

- A `LokiSink` class is implemented in **`fapilog/sinks/loki.py`**
- Accepts `loki://` or `https://` URI-style config with optional parameters:  
  • `labels` (static label map or string), e.g., `labels=app=myapi,env=prod`  
  • `batch_size` (default: 100)  
  • `batch_interval` (default: 2 seconds)
- Sink buffers logs and pushes them in batches to `/loki/api/v1/push`
- Each log is formatted as a Loki-compatible line:  
  • Timestamp (RFC3339 or nanosecond Unix time)  
  • Line string: JSON-serialized log event
- Push is performed with `httpx.AsyncClient`
- Failures are logged with `log.warning()` and retried with exponential backoff
- If `fapilog` is installed without the `loki` extra, usage raises `ImportError` with guidance
- Unit tests verify:  
  • Correct formatting of Loki batch  
  • Buffering and flush behavior  
  • Label parsing from URI  
  • Failure handling and retries
- README documents Loki support, URI configuration, and install instructions

───────────────────────────────────  
Tasks / Technical Checklist

1. Add `httpx` to `pyproject.toml` under optional dependencies:

   - `[project.optional-dependencies]`
     ```toml
     loki = ["httpx>=0.27"]
     ```

2. Implement `LokiSink` in `fapilog/sinks/loki.py`:

   - Accepts URI + query string params
   - Buffers logs and flushes on batch size or interval
   - Uses `httpx.AsyncClient` to push batch to `/loki/api/v1/push`
   - Constructs payload in expected format:
     ```json
     {
       "streams": [
         {
           "stream": {"label_key": "value"},
           "values": [[<timestamp>, <logline>], ...]
         }
       ]
     }
     ```

3. Add to sink loader in `configure_logging()`:

   - If sink URL starts with `loki://` or `https://`, parse and instantiate `LokiSink`
   - Handle `ImportError` gracefully if `httpx` is not installed

4. Unit tests in `tests/test_loki_sink.py`:

   - `test_batch_push_format()`
   - `test_uri_label_parsing()`
   - `test_flush_on_batch_size()`
   - `test_retry_on_failure()`
   - Use `httpx.MockTransport` or patch `httpx.AsyncClient.post`

5. README updates:
   - Installation: `pip install fapilog[loki]`
   - Example:
     ```env
     FAPILOG_SINKS=loki://loki:3100?labels=app=myapi,env=dev
     ```
   - Notes on batching and retry behavior

───────────────────────────────────  
Dependencies / Notes

- Optional `httpx` dependency; users must opt-in via `[loki]` extra
- Batch-based push model reduces HTTP load and aligns with Loki performance best practices

───────────────────────────────────  
Definition of Done  
✓ LokiSink implemented, registered, and tested  
✓ Compatible with `QueueWorker` and respects batching settings  
✓ All tests pass; CI green  
✓ PR merged to **main** with reviewer approval  
✓ `CHANGELOG.md` and README updated under _Unreleased → Added_
