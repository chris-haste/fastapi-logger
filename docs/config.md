# Configuration Guide

This guide provides a complete reference for all configuration options available in `fapilog`. All settings can be configured via environment variables or programmatically through the `LoggingSettings` class.

**Current Version:** {{ version }} | [Changelog](https://github.com/chris-haste/fastapi-logger/blob/main/CHANGELOG.md)

**See also:** [User Guide](user-guide.md), [API Reference](api-reference.md), [Quickstart](quickstart.md), [Primer](primer.md), [Style Guide](style-guide.md)

## Quick Start

The simplest way to configure `fapilog` is through environment variables:

```bash
# Basic configuration
export FAPILOG_LEVEL=INFO
export FAPILOG_SINKS=stdout
export FAPILOG_JSON_CONSOLE=auto

# Start your application
python your_app.py
```

Or programmatically:

```python
from fapilog.settings import LoggingSettings
from fapilog import configure_logging

settings = LoggingSettings(
    level="INFO",
    sinks=["stdout"],
    json_console="auto"
)
logger = configure_logging(settings=settings)
```

**See also:** [Quickstart](quickstart.md), [User Guide](user-guide.md#configuration)

## Configuration Reference

### Core Logging Settings

#### `level` {#log_level}

**Type:** `str`  
**Default:** `"INFO"`  
**Environment Variable:** `FAPILOG_LEVEL`  
**Valid Values:** `"DEBUG"`, `"INFO"`, `"WARN"`, `"WARNING"`, `"ERROR"`, `"CRITICAL"`

Controls the minimum log level for output. Only messages at or above this level will be logged.

```bash
# Set to debug for development
export FAPILOG_LEVEL=DEBUG

# Set to warning for production
export FAPILOG_LEVEL=WARNING
```

#### `sinks` {#sinks}

**Type:** `Union[List[str], str]`  
**Default:** `["stdout"]`  
**Environment Variable:** `FAPILOG_SINKS`  
**Valid Values:** `"stdout"`, `"file://path/to/file.log"`, `"loki://host:port"`

Comma-separated list of sink destinations for log output. Supports multiple sinks for redundancy.

```bash
# Single sink
export FAPILOG_SINKS=stdout

# Multiple sinks
export FAPILOG_SINKS=stdout,file:///var/log/app.log

# With Loki
export FAPILOG_SINKS=stdout,file:///var/log/app.log,loki://loki:3100
```

#### `json_console` {#json_console}

**Type:** `str`  
**Default:** `"auto"`  
**Environment Variable:** `FAPILOG_JSON_CONSOLE`  
**Valid Values:** `"auto"`, `"json"`, `"pretty"`

Controls the output format for console (stdout) logs.

- **`auto`**: Automatically chooses based on TTY detection (pretty in terminals, JSON otherwise)
- **`json`**: Always output JSON format (one line per event)
- **`pretty`**: Always output pretty format (colorized, multi-line)

```bash
# Force JSON output
export FAPILOG_JSON_CONSOLE=json

# Force pretty output
export FAPILOG_JSON_CONSOLE=pretty

# Auto-detect (default)
export FAPILOG_JSON_CONSOLE=auto
```

#### `sampling_rate` {#sampling_rate}

**Type:** `float`  
**Default:** `1.0`  
**Environment Variable:** `FAPILOG_SAMPLING_RATE`  
**Valid Range:** `0.0` to `1.0`

Controls the percentage of log messages to process. Useful for high-volume logging scenarios.

```bash
# Log 50% of messages
export FAPILOG_SAMPLING_RATE=0.5

# Log all messages (default)
export FAPILOG_SAMPLING_RATE=1.0
```

### Redaction Settings

#### `redact_patterns` {#redact_patterns}

**Type:** `Union[List[str], str]`  
**Default:** `[]`  
**Environment Variable:** `FAPILOG_REDACT_PATTERNS`

Comma-separated list of regex patterns to redact from log messages. Useful for masking sensitive data.

```bash
# Redact passwords and tokens
export FAPILOG_REDACT_PATTERNS=password,token,secret

# Multiple patterns
export FAPILOG_REDACT_PATTERNS=password,token,secret,api_key
```

#### `redact_fields` {#redact_fields}

**Type:** `Union[List[str], str]`  
**Default:** `[]`  
**Environment Variable:** `FAPILOG_REDACT_FIELDS`

Comma-separated list of field names to redact from log messages. Supports dot notation for nested fields.

```bash
# Redact specific fields
export FAPILOG_REDACT_FIELDS=user.password,request.headers.authorization

# Multiple fields
export FAPILOG_REDACT_FIELDS=password,api_key,secret_token
```

#### `redact_replacement` {#redact_replacement}

**Type:** `str`  
**Default:** `"REDACTED"`  
**Environment Variable:** `FAPILOG_REDACT_REPLACEMENT`

The replacement value used for redacted fields.

```bash
# Custom replacement
export FAPILOG_REDACT_REPLACEMENT=***

# Empty replacement
export FAPILOG_REDACT_REPLACEMENT=
```

#### `redact_level` {#redact_level}

**Type:** `str`  
**Default:** `"INFO"`  
**Environment Variable:** `FAPILOG_REDACT_LEVEL`  
**Valid Values:** `"DEBUG"`, `"INFO"`, `"WARN"`, `"WARNING"`, `"ERROR"`, `"CRITICAL"`

Minimum log level for redaction. Redaction only applies to messages at or above this level.

```bash
# Redact in all levels
export FAPILOG_REDACT_LEVEL=DEBUG

# Only redact in INFO and above (default)
export FAPILOG_REDACT_LEVEL=INFO
```

#### `enable_auto_redact_pii` {#enable_auto_redact_pii}

**Type:** `bool`  
**Default:** `True`  
**Environment Variable:** `FAPILOG_ENABLE_AUTO_REDACT_PII`

Enables automatic PII (Personally Identifiable Information) detection and redaction.

```bash
# Disable automatic PII redaction
export FAPILOG_ENABLE_AUTO_REDACT_PII=false

# Enable automatic PII redaction (default)
export FAPILOG_ENABLE_AUTO_REDACT_PII=true
```

#### `custom_pii_patterns` {#custom_pii_patterns}

**Type:** `List[str]`  
**Default:** `[]`  
**Environment Variable:** `FAPILOG_CUSTOM_PII_PATTERNS`

Comma-separated list of custom regex patterns for PII detection.

```bash
# Add custom PII patterns
export FAPILOG_CUSTOM_PII_PATTERNS=credit_card,ssn,phone_number
```

### Queue Settings

#### `queue_enabled` {#queue_enabled}

**Type:** `bool`  
**Default:** `True`  
**Environment Variable:** `FAPILOG_QUEUE_ENABLED`

Enables the async queue for non-blocking logging.

```bash
# Disable async queue
export FAPILOG_QUEUE_ENABLED=false

# Enable async queue (default)
export FAPILOG_QUEUE_ENABLED=true
```

#### `queue_maxsize` {#queue_maxsize}

**Type:** `int`  
**Default:** `1000`  
**Environment Variable:** `FAPILOG_QUEUE_MAXSIZE`

Maximum size of the async log queue.

```bash
# Larger queue for high-volume logging
export FAPILOG_QUEUE_MAXSIZE=5000

# Smaller queue for memory-constrained environments
export FAPILOG_QUEUE_MAXSIZE=100
```

#### `queue_overflow` {#queue_overflow}

**Type:** `Literal["drop", "block", "sample"]`  
**Default:** `"drop"`  
**Environment Variable:** `FAPILOG_QUEUE_OVERFLOW`

Strategy for handling queue overflow:

- **`drop`**: Discard new messages when queue is full
- **`block`**: Wait for space in queue (may block application)
- **`sample`**: Probabilistically drop messages based on sampling rate

```bash
# Drop messages when queue is full (default)
export FAPILOG_QUEUE_OVERFLOW=drop

# Block until space is available
export FAPILOG_QUEUE_OVERFLOW=block

# Sample messages when queue is full
export FAPILOG_QUEUE_OVERFLOW=sample
```

#### `queue_batch_size` {#queue_batch_size}

**Type:** `int`  
**Default:** `10`  
**Environment Variable:** `FAPILOG_QUEUE_BATCH_SIZE`

Number of events to process in a batch.

```bash
# Larger batches for better throughput
export FAPILOG_QUEUE_BATCH_SIZE=50

# Smaller batches for lower latency
export FAPILOG_QUEUE_BATCH_SIZE=5
```

#### `queue_batch_timeout` {#queue_batch_timeout}

**Type:** `float`  
**Default:** `1.0`  
**Environment Variable:** `FAPILOG_QUEUE_BATCH_TIMEOUT`

Maximum time to wait for batch completion (seconds).

```bash
# Longer timeout for slow sinks
export FAPILOG_QUEUE_BATCH_TIMEOUT=5.0

# Shorter timeout for real-time logging
export FAPILOG_QUEUE_BATCH_TIMEOUT=0.5
```

#### `queue_retry_delay` {#queue_retry_delay}

**Type:** `float`  
**Default:** `1.0`  
**Environment Variable:** `FAPILOG_QUEUE_RETRY_DELAY`

Delay between retries on sink failures (seconds).

```bash
# Longer delay between retries
export FAPILOG_QUEUE_RETRY_DELAY=5.0

# Shorter delay for faster recovery
export FAPILOG_QUEUE_RETRY_DELAY=0.5
```

#### `queue_max_retries` {#queue_max_retries}

**Type:** `int`  
**Default:** `3`  
**Environment Variable:** `FAPILOG_QUEUE_MAX_RETRIES`

Maximum number of retries per event.

```bash
# More retries for unreliable sinks
export FAPILOG_QUEUE_MAX_RETRIES=10

# Fewer retries for fast failure
export FAPILOG_QUEUE_MAX_RETRIES=1
```

### Advanced Settings

#### `enable_resource_metrics` {#enable_resource_metrics}

**Type:** `bool`  
**Default:** `False`  
**Environment Variable:** `FAPILOG_ENABLE_RESOURCE_METRICS`

Enables memory and CPU usage metrics in log entries.

```bash
# Enable resource metrics
export FAPILOG_ENABLE_RESOURCE_METRICS=true

# Disable resource metrics (default)
export FAPILOG_ENABLE_RESOURCE_METRICS=false
```

#### `trace_id_header` {#trace_id_header}

**Type:** `str`  
**Default:** `"X-Request-ID"`  
**Environment Variable:** `FAPILOG_TRACE_ID_HEADER`

HTTP header name for incoming trace ID.

```bash
# Custom trace ID header
export FAPILOG_TRACE_ID_HEADER=X-Custom-Trace-ID

# Use standard header
export FAPILOG_TRACE_ID_HEADER=X-Request-ID
```

#### `enable_httpx_trace_propagation` {#enable_httpx_trace_propagation}

**Type:** `bool`  
**Default:** `False`  
**Environment Variable:** `FAPILOG_ENABLE_HTTPX_TRACE_PROPAGATION`

Enables automatic trace ID propagation in `httpx.AsyncClient`.

```bash
# Enable trace propagation
export FAPILOG_ENABLE_HTTPX_TRACE_PROPAGATION=true

# Disable trace propagation (default)
export FAPILOG_ENABLE_HTTPX_TRACE_PROPAGATION=false
```

#### `user_context_enabled` {#user_context_enabled}

**Type:** `bool`  
**Default:** `True`  
**Environment Variable:** `FAPILOG_USER_CONTEXT_ENABLED`

Enables user context enrichment in log entries.

```bash
# Enable user context (default)
export FAPILOG_USER_CONTEXT_ENABLED=true

# Disable user context
export FAPILOG_USER_CONTEXT_ENABLED=false
```

### Metrics Collection Settings

#### `metrics_enabled` {#metrics_enabled}

**Type:** `bool`  
**Default:** `False`  
**Environment Variable:** `FAPILOG_METRICS_ENABLED`

Enables comprehensive metrics collection for queue and sink performance monitoring.

```bash
# Enable metrics collection
export FAPILOG_METRICS_ENABLED=true

# Disable metrics collection (default)
export FAPILOG_METRICS_ENABLED=false
```

#### `metrics_sample_window` {#metrics_sample_window}

**Type:** `int`  
**Default:** `100`  
**Environment Variable:** `FAPILOG_METRICS_SAMPLE_WINDOW`

Number of recent samples to keep for calculating average metrics.

```bash
# Larger window for more stable averages
export FAPILOG_METRICS_SAMPLE_WINDOW=200

# Smaller window for more responsive metrics
export FAPILOG_METRICS_SAMPLE_WINDOW=50
```

#### `metrics_prometheus_enabled` {#metrics_prometheus_enabled}

**Type:** `bool`  
**Default:** `False`  
**Environment Variable:** `FAPILOG_METRICS_PROMETHEUS_ENABLED`

Enables Prometheus metrics HTTP endpoint for scraping.

```bash
# Enable Prometheus exporter
export FAPILOG_METRICS_PROMETHEUS_ENABLED=true

# Disable Prometheus exporter (default)
export FAPILOG_METRICS_PROMETHEUS_ENABLED=false
```

#### `metrics_prometheus_port` {#metrics_prometheus_port}

**Type:** `int`  
**Default:** `8000`  
**Environment Variable:** `FAPILOG_METRICS_PROMETHEUS_PORT`

Port for the Prometheus metrics HTTP endpoint.

```bash
# Custom port
export FAPILOG_METRICS_PROMETHEUS_PORT=9090

# Default port
export FAPILOG_METRICS_PROMETHEUS_PORT=8000
```

#### `metrics_prometheus_host` {#metrics_prometheus_host}

**Type:** `str`  
**Default:** `"0.0.0.0"`  
**Environment Variable:** `FAPILOG_METRICS_PROMETHEUS_HOST`

Host address for the Prometheus metrics HTTP endpoint.

```bash
# Bind to localhost only
export FAPILOG_METRICS_PROMETHEUS_HOST=127.0.0.1

# Bind to all interfaces (default)
export FAPILOG_METRICS_PROMETHEUS_HOST=0.0.0.0
```

## Overriding Configuration

### Environment Variables

All settings can be overridden using environment variables with the `FAPILOG_` prefix:

```bash
# Override multiple settings
export FAPILOG_LEVEL=DEBUG
export FAPILOG_SINKS=stdout,file:///var/log/app.log
export FAPILOG_QUEUE_ENABLED=true
export FAPILOG_REDACT_LEVEL=INFO
```

### Programmatic Override

You can also override settings programmatically:

```python
from fapilog.settings import LoggingSettings
from fapilog import configure_logging

# Override specific settings
settings = LoggingSettings(
    level="DEBUG",
    sinks=["stdout", "file:///var/log/app.log"],
    queue_enabled=True,
    redact_level="INFO"
)

logger = configure_logging(settings=settings)
```

### Mixed Configuration

You can combine environment variables with programmatic overrides:

```python
from fapilog.settings import LoggingSettings
from fapilog import configure_logging

# Start with environment defaults, then override
settings = LoggingSettings()
settings.level = "DEBUG"  # Override just the level
settings.sinks.append("file:///var/log/app.log")  # Add a sink

logger = configure_logging(settings=settings)
```

## Sink-Specific Configuration

### File Sink

File sinks support additional configuration via URI parameters:

```bash
# Basic file logging
export FAPILOG_SINKS=file:///var/log/app.log

# With rotation settings
export FAPILOG_SINKS=file:///var/log/app.log?maxBytes=10485760&backupCount=3
```

**File Sink Parameters:**

- **`maxBytes`**: Maximum file size before rotation (default: 10MB)
- **`backupCount`**: Number of backup files to keep (default: 5)

### Loki Sink

Loki sinks support configuration via URI parameters:

```bash
# Basic Loki logging
export FAPILOG_SINKS=loki://loki:3100

# With labels and batching
export FAPILOG_SINKS=loki://loki:3100?labels=app=myapi,env=prod&batch_size=50&batch_interval=1.0
```

**Loki Sink Parameters:**

- **`labels`**: Static labels for all log streams (e.g., `app=myapi,env=prod`)
- **`batch_size`**: Number of logs to buffer before pushing (default: 100)
- **`batch_interval`**: Max seconds to wait before pushing a batch (default: 2.0)

## Configuration Examples

### Development Environment

```bash
# Development settings
export FAPILOG_LEVEL=DEBUG
export FAPILOG_SINKS=stdout
export FAPILOG_JSON_CONSOLE=pretty
export FAPILOG_QUEUE_ENABLED=true
export FAPILOG_REDACT_LEVEL=DEBUG
export FAPILOG_ENABLE_RESOURCE_METRICS=false
```

### Production Environment

```bash
# Production settings
export FAPILOG_LEVEL=INFO
export FAPILOG_SINKS=stdout,file:///var/log/app.log,loki://loki:3100
export FAPILOG_JSON_CONSOLE=json
export FAPILOG_QUEUE_ENABLED=true
export FAPILOG_REDACT_LEVEL=INFO
export FAPILOG_ENABLE_RESOURCE_METRICS=true
export FAPILOG_REDACT_PATTERNS=password,token,secret
export FAPILOG_REDACT_FIELDS=user.password,request.headers.authorization
```

### High-Volume Logging

```bash
# High-volume settings
export FAPILOG_LEVEL=WARNING
export FAPILOG_SINKS=stdout,file:///var/log/app.log
export FAPILOG_SAMPLING_RATE=0.1
export FAPILOG_QUEUE_MAXSIZE=5000
export FAPILOG_QUEUE_BATCH_SIZE=100
export FAPILOG_QUEUE_OVERFLOW=drop
```

### Security-Focused

```bash
# Security-focused settings
export FAPILOG_LEVEL=INFO
export FAPILOG_SINKS=stdout,file:///var/log/app.log
export FAPILOG_REDACT_LEVEL=DEBUG
export FAPILOG_REDACT_PATTERNS=password,token,secret,api_key,ssn
export FAPILOG_REDACT_FIELDS=user.password,request.headers.authorization,response.body
export FAPILOG_ENABLE_AUTO_REDACT_PII=true
export FAPILOG_CUSTOM_PII_PATTERNS=credit_card,phone_number
```

## Validation

All configuration values are validated when the settings are loaded. Invalid values will raise a `ConfigurationError` with a descriptive message:

```python
from fapilog.settings import LoggingSettings

# This will raise ConfigurationError
settings = LoggingSettings(level="INVALID_LEVEL")
```

Common validation errors:

- Invalid log levels (must be one of: DEBUG, INFO, WARN, WARNING, ERROR, CRITICAL)
- Invalid sampling rate (must be between 0.0 and 1.0)
- Invalid queue settings (must be positive numbers)
- Invalid sink URIs (must be valid file paths or Loki URLs)
