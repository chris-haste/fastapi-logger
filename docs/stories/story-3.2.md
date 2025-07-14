Story 3.2 – Background Queue Worker & Graceful Shutdown  
───────────────────────────────────  
Epic: 3 – Async Logging Infrastructure  
Sprint Target: Sprint #⟪next⟫  
Story Points: 5

**As a system integrator**  
I want the logging queue to flush logs reliably during application shutdown  
So that no log messages are lost when the service exits or is terminated cleanly.

───────────────────────────────────  
Acceptance Criteria

- `QueueWorker` class (from Story 3.1) implements a `shutdown()` coroutine that:  
  • Marks the queue as closed (e.g., with a sentinel or `self._stopping = True`)  
  • Waits for the queue to drain  
  • Ensures all log events are flushed to all registered sinks
- `configure_logging()` adds proper shutdown hooks in both environments:  
  • When used with FastAPI: registers `app.add_event_handler("shutdown", QueueWorker.shutdown)`  
  • When used standalone (e.g., CLI or script): registers `atexit` sync-safe fallback to flush remaining logs
- Worker loop exits cleanly on shutdown, without raising exceptions or leaving background tasks hanging
- Shutdown does not hang indefinitely if queue is idle or already drained
- Unit tests verify:  
  • `shutdown()` flushes remaining events  
  • No events are processed after shutdown  
  • `shutdown()` can be called safely more than once
- README updated with section: “Shutdown Behavior and Log Flushing”

───────────────────────────────────  
Tasks / Technical Checklist

1. Extend `QueueWorker` class in `fapilog/_internal/queue.py`:

   - Add `async def shutdown(self)` to flush and close
   - Add internal `_stopping` flag or sentinel message (`None`)
   - Ensure `run()` breaks cleanly after shutdown initiated

2. Update `configure_logging()`

   - If `app` is provided:  
     • Register `app.add_event_handler("shutdown", queue_worker.shutdown)`
   - Else (CLI mode):  
     • Use `atexit.register(lambda: asyncio.run(queue_worker.shutdown()))` (fallback)

3. Update internal processor (`queue_sink`) to skip enqueueing after shutdown

4. Unit tests in `tests/test_log_queue.py`:

   - `test_shutdown_flushes_events()`
   - `test_shutdown_idempotent()`
   - `test_no_enqueue_after_shutdown()`

5. Update README section on async queue (from Story 3.1) to include shutdown lifecycle

───────────────────────────────────  
Dependencies / Notes

- Builds directly on Story 3.1
- Required foundation for implementing durable or remote sinks (e.g., Loki) safely

───────────────────────────────────  
Definition of Done  
✓ Shutdown logic integrated with both FastAPI and CLI use cases  
✓ Logs are flushed without loss on clean shutdown  
✓ Tests verify flush, idempotency, and blocking behavior  
✓ PR merged to **main** with reviewer approval and green CI  
✓ `CHANGELOG.md` and README updated under _Unreleased → Added_
