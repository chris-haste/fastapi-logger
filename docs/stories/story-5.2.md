Story 5.2 – File Sink with Rotation Support  
───────────────────────────────────  
Epic: 5 – Sink Implementations  
Sprint Target: Sprint #⟪next⟫  
Story Points: 5

**As a developer or operator**  
I want logs to be written to a file with automatic rotation  
So that I can persist logs on disk without risking unlimited file growth.

───────────────────────────────────  
Acceptance Criteria

- A `FileSink` class is implemented in **`fapilog/sinks/file.py`**
- Supports writing logs in JSON format to a specified file path
- Supports log rotation using `logging.handlers.RotatingFileHandler` with parameters:  
  • `maxBytes` (default: 10 MB)  
  • `backupCount` (default: 5)
- Accepts configuration via a `file://` URI-style string in `FAPILOG_SINKS`, e.g.:  
  `file:///var/log/myapp.log?maxBytes=10485760&backupCount=3`
- The sink is async: `async def write(event_dict: dict)` internally delegates to a thread-safe standard handler
- File is flushed immediately to avoid data loss in crash scenarios
- Unit tests verify:  
  • Log file created and written to  
  • Rotation occurs when file exceeds threshold  
  • Parsed query parameters override defaults  
  • URI with invalid path or params raises helpful error

───────────────────────────────────  
Tasks / Technical Checklist

1. Implement `FileSink` in `fapilog/sinks/file.py`:

   - Parse file path and rotation options from `file://` URI
   - Use `RotatingFileHandler` from `logging.handlers`
   - Ensure thread-safe writing (`logger.handle(record)`)
   - Flush after every log write

2. Add file sink support to sink loader in `configure_logging()`

   - If `FAPILOG_SINKS` includes a `file://` URI, initialize `FileSink` with parsed config

3. Unit tests in `tests/test_file_sink.py`:

   - `test_file_sink_writes_log()`
   - `test_rotation_behavior()`
   - `test_invalid_uri_handling()`
   - Use temporary files and small `maxBytes` for testability

4. Update README:
   - “Sink Configuration” section → document `file://` format
   - Example usage with rotation settings

───────────────────────────────────  
Dependencies / Notes

- Depends on Python stdlib only (`logging`, `urllib.parse`, `pathlib`)
- Later stories (e.g. Loki sink) will follow same pattern for URI-based sink config

───────────────────────────────────  
Definition of Done  
✓ FileSink implemented with rotation and URI-based config  
✓ Logs written in JSON and rotate when size thresholds are exceeded  
✓ Tests validate functionality and edge cases  
✓ PR merged to **main** with reviewer approval and green CI  
✓ `CHANGELOG.md` and README updated under _Unreleased → Added_
