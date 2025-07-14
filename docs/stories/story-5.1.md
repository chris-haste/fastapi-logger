Story 5.1 – Stdout Sink Implementation  
───────────────────────────────────  
Epic: 5 – Sink Implementations  
Sprint Target: Sprint #⟪next⟫  
Story Points: 5

**As a developer running in containers or local dev environments**  
I want log events to be written to stdout in either JSON or human-readable form  
So that I can view structured or pretty logs in Docker, Kubernetes, or my terminal.

───────────────────────────────────  
Acceptance Criteria

- A concrete `StdoutSink` class is implemented in **`fapilog/sinks/stdout.py`**
- Sink supports both:  
  • JSON output (compact, one-line-per-event)  
  • Pretty console output (colorized, multiline) using `structlog.dev.ConsoleRenderer`
- Output format is selected based on `LoggingSettings.json_console`:  
  • `json` → force JSON  
  • `pretty` → force pretty output  
  • `auto` (default) → pretty if `sys.stderr.isatty()` else JSON
- Sink is async and implements `async def write(event_dict: dict)`
- Integrated with the logging queue (`QueueWorker`) and used as the default sink
- Unit tests verify:  
  • Correct format output based on mode  
  • Output written to `sys.stdout` (or captured stream)  
  • Pretty output includes ANSI codes when enabled
- README documents the stdout sink and how to force pretty mode in development

───────────────────────────────────  
Tasks / Technical Checklist

1. Implement `StdoutSink` in `fapilog/sinks/stdout.py`:

   - Constructor accepts a `mode` (`"json" | "pretty" | "auto"`)
   - Uses `print(..., file=sys.stdout, flush=True)` for output
   - Uses `structlog.dev.ConsoleRenderer` or `json.dumps()`

2. Add to sink registration in `configure_logging()` or `QueueWorker` initialization:

   - Use as default when `FAPILOG_SINKS=stdout`

3. Update `LoggingSettings` (if not already supported):

   - Field: `json_console: Literal["auto", "json", "pretty"] = "auto"`

4. Unit tests in `tests/test_stdout_sink.py`:

   - `test_json_output_format()`
   - `test_pretty_output_format()`
   - `test_auto_mode_tty_detection()`
   - Use `capsys` or mocked `sys.stdout`

5. README updates:
   - “Sink Configuration” section
   - Describe `stdout` usage and mode selection behavior

───────────────────────────────────  
Dependencies / Notes

- Sink is always included; no extra dependencies
- Will be complemented by `file://` and `loki://` sinks in future stories

───────────────────────────────────  
Definition of Done  
✓ StdoutSink implemented with proper formatting support  
✓ Works with queue system and respects configuration  
✓ Unit tests pass for all modes  
✓ PR merged to **main** with reviewer approval and green CI  
✓ `CHANGELOG.md` and README updated under _Unreleased → Added_
