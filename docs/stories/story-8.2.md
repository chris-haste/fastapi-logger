Story 8.2 – Loki Sink: Buffered Queue + Background Worker  
───────────────────────────────────  
Epic: 8 – Loki Integration  
Sprint Target: Sprint #⟪next⟫  
Story Points: 8

**As a developer using Loki in production**  
I want logs to be queued and sent in batches via a background worker  
So that logging is non-blocking and reliable even under load.

───────────────────────────────────  
Acceptance Criteria

- A buffered queue mechanism is implemented to decouple log production from delivery
- Logs are collected in an in-memory queue and flushed periodically or when a batch size is reached
- A background task handles sending logs to Loki via the existing `LokiSink`
- Queue size, flush interval, and batch size are configurable
- Worker starts automatically when the Loki sink is configured
- If the queue overflows, a warning is logged and excess messages are dropped
- Graceful shutdown flushes remaining logs before exit
- Unit tests verify queuing, batching, flushing, and overflow behavior
- README documents buffering behavior and tuning parameters

───────────────────────────────────  
Tasks / Technical Checklist

1. Implement `LokiQueueManager` in `fapilog/_internal/queue.py`:

   - Async queue with size limit
   - Background `flush_loop()` coroutine started on first use
   - Uses `asyncio.create_task()` and `anyio.sleep()` for periodic flush

2. Update `LokiSink` to accept log batches and handle flush triggers

3. Add config options to `fapilog/settings.py`:

   - `LOKI_BUFFER_SIZE: int = 1000`
   - `LOKI_BATCH_SIZE: int = 100`
   - `LOKI_FLUSH_INTERVAL: float = 2.0` (seconds)

4. Register queue and background task in `configure_logging()` when Loki is active

   - Ensure it runs under FastAPI lifecycle context or lifespan event

5. Add shutdown hook to flush logs before exit

   - Compatible with FastAPI shutdown events

6. Unit tests in `tests/sinks/test_loki_buffering.py`:

   - `test_logs_queued_and_flushed()`
   - `test_flush_on_batch_size()`
   - `test_overflow_behavior()`
   - `test_shutdown_flushes_queue()`

7. README updates:
   - Add “Buffered Logging” section under Loki Integration
   - Explain async behavior and recommended production settings

───────────────────────────────────  
Dependencies / Notes

- Uses `anyio` for async-agnostic timers and task management
- FastAPI app should run with `lifespan="on"` for safe background task handling
- Consider support for a synchronous fallback in constrained environments (future story)

───────────────────────────────────  
Definition of Done  
✓ Logs are buffered and flushed via async worker  
✓ Non-blocking behavior is confirmed by tests  
✓ Overflow and shutdown scenarios are gracefully handled  
✓ PR merged to **main** with reviewer approval  
✓ `CHANGELOG.md` and README updated under _Unreleased → Added_
