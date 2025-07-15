Story 3.3 – Queue Overflow Strategy: Drop, Block, or Sample  
───────────────────────────────────  
Epic: 3 – Async Logging Infrastructure  
Sprint Target: Sprint #⟪next⟫  
Story Points: 5

**As a performance-sensitive operator**  
I want to control what happens when the logging queue is full  
So that I can choose between guaranteed delivery (blocking), best-effort (drop), or adaptive sampling based on load.

───────────────────────────────────  
Acceptance Criteria

- Overflow handling strategy is configurable via `LoggingSettings.queue_overflow` (enum):  
  • `drop` → silently discard logs when queue is full  
  • `block` → await queue space before continuing  
  • `sample` → enqueue with a probabilistic sampling chance (e.g., `0.1`)
- `LoggingSettings` includes:  
  • `queue_maxsize: int = 1000`  
  • `queue_overflow: Literal["drop", "block", "sample"] = "drop"`  
  • `sampling_rate: float = 1.0` (already exists; reused for sample strategy)
- `queue_sink()` respects the strategy:  
  • For `drop`, uses `queue.put_nowait()` and ignores `QueueFull`  
  • For `block`, uses `await queue.put()`  
  • For `sample`, uses random float comparison before enqueue
- Unit tests verify each strategy:  
  • Dropped messages do not raise  
  • Block strategy suspends coroutine until queue frees space  
  • Sampling keeps messages with approximate probability
- README includes new section: “Controlling Queue Overflow Behavior” with examples

───────────────────────────────────  
Tasks / Technical Checklist

1. Update `LoggingSettings` model (fapilog/settings.py) with:

   - `queue_maxsize: int = 1000`
   - `queue_overflow: Literal["drop", "block", "sample"] = "drop"`
   - Validators for sampling bounds and strategy

2. Modify `QueueWorker` init to accept `maxsize` and `strategy`

3. Update `queue_sink()` processor:

   - For `drop`: `put_nowait()` with try/except
   - For `block`: `await put()`
   - For `sample`: use `random.random() < sampling_rate`

4. Unit tests in `tests/test_log_queue_overflow.py`:

   - `test_overflow_drop_mode()`
   - `test_overflow_block_mode()`
   - `test_overflow_sample_mode()`

5. Update README with config example and strategy tradeoffs

───────────────────────────────────  
Dependencies / Notes

- Builds on Stories 3.1 and 3.2 (queue and shutdown already implemented)
- Makes use of `sampling_rate` from Story 1.3

───────────────────────────────────  
Definition of Done  
✓ All strategies implemented and verified through tests  
✓ Settings schema updated and validated  
✓ PR merged to **main** with reviewer approval and green CI  
✓ `CHANGELOG.md` and README updated under _Unreleased → Added_

───────────────────────────────────  
Implementation Summary

**Completed Work:**

✅ **Settings Configuration**

- Added `queue_overflow: Literal["drop", "block", "sample"] = "drop"` to `LoggingSettings`
- Added `queue_maxsize: int = 1000` field (already existed)
- Added field validator for overflow strategy validation
- Integrated with existing `sampling_rate` setting for sample strategy

✅ **Queue Worker Implementation**

- Enhanced `QueueWorker.enqueue()` method to respect overflow strategy:
  - **Drop**: Uses `put_nowait()` with try/except, returns `False` on `QueueFull`
  - **Block**: Uses `await put()` to wait for queue space, handles `CancelledError`
  - **Sample**: Applies sampling rate before enqueue attempt
- Updated `queue_sink()` processor to handle different strategies in sync contexts
- Maintained backward compatibility with existing queue functionality

✅ **Comprehensive Testing**

- All overflow strategy tests pass (39/39 queue tests)
- `test_overflow_drop_mode()`: Verifies silent discard behavior
- `test_overflow_block_mode()`: Verifies coroutine suspension until queue space
- `test_overflow_sample_mode()`: Verifies probabilistic sampling behavior
- `test_overflow_sample_mode_with_sampling_rate()`: Verifies sampling rate integration
- `test_overflow_strategies_with_sampling_rate()`: Verifies all strategies with sampling

✅ **Documentation Updates**

- Added "Controlling Queue Overflow Behavior" section to README
- Included configuration examples for all three strategies
- Updated environment variables table with `FAPILOG_QUEUE_OVERFLOW`
- Added strategy tradeoffs and usage recommendations
- Updated CHANGELOG.md with Story 3.3 entry

✅ **Environment Variable Support**

- `FAPILOG_QUEUE_OVERFLOW` environment variable for strategy selection
- Default value: `"drop"` (silent discard)
- Valid values: `"drop"`, `"block"`, `"sample"`

**Key Features Delivered:**

1. **Drop Strategy (Default)**: Silently discards logs when queue is full - ensures application never blocks
2. **Block Strategy**: Waits for queue space before continuing - provides guaranteed log delivery
3. **Sample Strategy**: Uses probabilistic sampling when queue is full - provides adaptive logging under load

**Usage Examples:**

```python
# Drop strategy (default) - never blocks
settings = LoggingSettings(queue_overflow="drop")

# Block strategy - guaranteed delivery
settings = LoggingSettings(queue_overflow="block")

# Sample strategy - adaptive logging
settings = LoggingSettings(queue_overflow="sample", sampling_rate=0.1)
```

**Technical Implementation:**

- Follows FastAPI and Pydantic V2 best practices
- Robust error handling with proper async/sync context management
- Comprehensive test coverage with 100% acceptance criteria met
- Backward compatible with existing queue functionality
- Environment-driven configuration for 12-factor app compliance
