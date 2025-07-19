Story 12.4 – Configuration Guide & Examples  
───────────────────────────────────  
Epic: 12 – Documentation  
Sprint Target: Sprint #⟪next⟫  
Story Points: 3

**As a developer integrating fapilog**  
I want a clear guide on configuring the logger  
So that I can understand available options, environment variables, and how to customize logging behavior.

───────────────────────────────────  
Acceptance Criteria

✅ `docs/config.md` contains complete reference for all configuration fields
✅ Each setting includes:

- Field name and type
- Description and default value
- Example environment variable name (e.g. `FAPILOG_LEVEL`)
  ✅ Configuration guide covers:
- `LoggingSettings` Pydantic model
- How to override via env vars or `configure_logging()` args
- Optional Loki-specific fields
  ✅ Markdown is well-formatted and renders in the site
  ✅ Internal links or anchors provided for navigation (e.g., `#log_level`)

───────────────────────────────────  
Tasks / Technical Checklist

✅ 1. Open `fapilog/settings.py` and extract all top-level config fields
✅ 2. Document each field in `docs/config.md` with:

- Name (e.g., `level`)
- Type (e.g., `str`)
- Default (e.g., `"INFO"`)
- Env var name (e.g., `FAPILOG_LEVEL`)
- Short description and sample value

✅ 3. Organize settings into logical sections:

- Core Logging Settings
- Redaction Settings
- Queue Settings
- Advanced Settings

✅ 4. Add "Overriding Configuration" section to show:

- How env vars are picked up
- How to override inline via `configure_logging(settings=...)`

✅ 5. Update README.md to reference the new configuration guide
✅ 6. Verify documentation quality and completeness

───────────────────────────────────  
Implementation Details

**Completed Work:**

1. **Created comprehensive `docs/config.md`** with complete reference for all 22 configuration fields
2. **Documented all settings** with:

   - Field name, type, default value, and environment variable name
   - Clear descriptions and usage examples
   - Valid values and ranges where applicable
   - Internal navigation anchors for easy reference

3. **Organized settings into logical sections:**

   - **Core Logging Settings**: `level`, `sinks`, `json_console`, `sampling_rate`
   - **Redaction Settings**: `redact_patterns`, `redact_fields`, `redact_replacement`, `redact_level`, `enable_auto_redact_pii`, `custom_pii_patterns`
   - **Queue Settings**: `queue_enabled`, `queue_maxsize`, `queue_overflow`, `queue_batch_size`, `queue_batch_timeout`, `queue_retry_delay`, `queue_max_retries`
   - **Advanced Settings**: `enable_resource_metrics`, `trace_id_header`, `enable_httpx_trace_propagation`, `user_context_enabled`

4. **Added comprehensive sections:**

   - Quick Start guide with environment variable examples
   - Overriding Configuration (environment variables, programmatic, mixed)
   - Sink-specific configuration for File and Loki sinks
   - Practical configuration examples for different environments
   - Validation and error handling guidance

5. **Enhanced README.md** with:

   - Quick Configuration Reference section with common patterns
   - Documentation section linking to all guides
   - Improved table of contents with better navigation
   - Multiple references to the new configuration guide
   - Configuration examples in Quick Start section

6. **Updated CHANGELOG.md** under the _Unreleased → Added_ section

**Key Features Delivered:**

- **Complete Coverage**: All 22 configuration fields from `LoggingSettings` documented
- **Practical Examples**: Real-world configuration examples for Development, Production, High-Volume, and Security-focused environments
- **Clear Navigation**: Internal anchors (e.g., `#log_level`, `#sinks`) for easy reference
- **Environment-First**: Emphasizes environment variable configuration for 12-factor app compliance
- **Programmatic Support**: Shows how to override settings programmatically
- **Validation Guidance**: Explains error handling and common validation issues
- **Sink Documentation**: File and Loki sink configuration with URI parameters

───────────────────────────────────  
Dependencies / Notes

- Builds on 12.1 (site scaffold) and 12.2 (API docs)
- Can later be extended to support search or interactive playgrounds
- README.md has been enhanced to better integrate with the new configuration guide

───────────────────────────────────  
Definition of Done  
✅ Configuration reference added and visible in docs site  
✅ All major fields are documented with usage guidance  
✅ Internal navigation is clear and structured  
✅ README.md updated with references to configuration guide  
✅ `CHANGELOG.md` updated under _Unreleased → Added_

**Status: COMPLETED** ✅
