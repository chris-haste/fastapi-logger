Story 3.1 – Non-Blocking In-Process Log Queue  
───────────────────────────────────  
Epic: 3 – Async Logging Infrastructure  
Sprint Target: Sprint #⟪next⟫  
Story Points: 8

**As a performance-conscious developer**  
I want logs to be written through a non-blocking, in-process queue  
So that log calls never block the asyncio event loop and remain performant under high concurrency.

───────────────────────────────────  
Acceptance Criteria

- A background log queue is implemented in **`fapilog/_internal/queue.py`** using `asyncio.Queue`.
- A coroutine-based log sink processor (`queue_sink`) is defined and injected into the structlog pipeline.
- Log events are enqueued as structured dicts (not raw strings).
- A background task (`QueueWorker`) pulls from the queue and dispatches events to concrete sinks (e.g., stdout, file, Loki).
- If the queue is full, log calls are **dropped silently** (default), or sampled if configured.
- `configure_logging()` ensures the queue worker is started once (global task), and shut down gracefully via `atexit` or `FastAPI.on_shutdown`.
- Unit tests verify:  
  • Logs are correctly queued and dispatched  
  • Queue capacity respected (e.g., 1000 by default)  
  • Overfilled queue drops messages without exceptions  
  • Queue does not block `await` points
- README documents the async nature of the queue and performance benefits

───────────────────────────────────  
Tasks / Technical Checklist

1. Create `QueueWorker` class in `fapilog/_internal/queue.py`

   - Holds an `asyncio.Queue(maxsize=N)`
   - Accepts `List[Sink]` instances
   - Starts via `asyncio.create_task(self.run())`
   - Implements `run()` loop with retry and backoff on failure

2. Define `queue_sink(event_dict)` processor

   - Serializes log event
   - Pushes into `QueueWorker.queue`
   - If full, skip or sample depending on settings

3. Modify `configure_logging()` to instantiate and register `QueueWorker`

   - Run via `asyncio.get_event_loop().create_task(...)`
   - Add graceful shutdown via FastAPI `on_shutdown` or `atexit.register(...)` for CLI environments

4. Update processor pipeline (Story 1.4) to route to `queue_sink` instead of final sync sink

5. Unit tests in `tests/test_log_queue.py`

   - `test_basic_enqueue_and_flush`
   - `test_queue_capacity_drop`
   - `test_worker_nonblocking_under_load`

6. README – new section: “Async Logging Queue” with performance rationale

───────────────────────────────────  
Dependencies / Notes

- Builds on Story 1.4’s pipeline logic
- Will support multiple downstream sinks in later stories (e.g., stdout, Loki)
- Requires `asyncio.run()` compatibility; recommend testing both standalone and with FastAPI

───────────────────────────────────  
Definition of Done  
✓ Log queue and worker are integrated with `configure_logging()`  
✓ Logs flow through async queue and background task  
✓ Tests pass and show non-blocking behavior under load  
✓ PR merged to **main** with reviewer approval and green CI  
✓ `CHANGELOG.md` and README updated under _Unreleased → Added_
