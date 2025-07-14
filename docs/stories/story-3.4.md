Story 3.4 – Load Testing the Logging Queue  
───────────────────────────────────  
Epic: 3 – Async Logging Infrastructure  
Sprint Target: Sprint #⟪next⟫  
Story Points: 5

**As a performance engineer**  
I want to simulate high-throughput logging scenarios  
So that I can verify the logging queue performs reliably under load and does not degrade service responsiveness.

───────────────────────────────────  
Acceptance Criteria

- A standalone test script (`scripts/load_test_log_queue.py`) generates structured logs at high frequency using `fapilog.log`.
- The script allows configurable parameters via CLI or env:  
  • concurrency level (number of concurrent tasks)  
  • log rate per task (logs/sec)  
  • duration of test (seconds)  
  • queue strategy and maxsize
- Test run reports:  
  • Total logs attempted  
  • Logs successfully enqueued  
  • Dropped logs (if applicable)  
  • Average enqueue latency (non-blocking and blocking modes)
- Supports testing all overflow strategies: `drop`, `block`, `sample`
- README includes instructions to run the test locally and interpret results
- Does not require external dependencies beyond `fapilog` and stdlib

───────────────────────────────────  
Tasks / Technical Checklist

1. Create `scripts/load_test_log_queue.py`:

   - Async entry point
   - Parse args or env vars for config
   - Spawn N concurrent coroutines logging at fixed interval
   - Use `configure_logging()` with target queue settings
   - Track counters for attempted, enqueued, dropped

2. Expose optional debug sink that records log delivery counts internally for instrumentation

3. Use `asyncio.sleep()` and `time.perf_counter()` to measure enqueue latency per log

4. Support all overflow strategies and print summary at end:

   - “Total logs attempted: 50,000”
   - “Successfully enqueued: 49,875”
   - “Dropped: 125”
   - “Avg enqueue latency: 42 µs”

5. Add to `tool.poetry.scripts` or `Makefile` for easy execution:

   - `make test-queue-load` or `python scripts/load_test_log_queue.py`

6. Add section to README: “Benchmarking Logging Queue”

───────────────────────────────────  
Dependencies / Notes

- Builds on Stories 3.1–3.3
- Ideal target: maintain <100 µs enqueue latency @ 10k logs/sec with default config

───────────────────────────────────  
Definition of Done  
✓ Script runs standalone with tunable parameters  
✓ Output shows key performance metrics  
✓ All overflow strategies supported  
✓ PR merged to **main** with reviewer approval and green CI  
✓ `CHANGELOG.md` and README updated under _Unreleased → Added_
