# Sinks Guide

**Complete guide to output destinations in fapilog - from built-in sinks to custom implementations.**

Sinks handle writing log events to different destinations. Whether you need simple console output, file rotation, remote log aggregation, or custom integrations, this guide covers everything you need to know.

### 🚀 Quick Navigation

**Common Tasks:**

- [Just want basic console logging?](#stdout-sink) → Stdout Sink
- [Need file rotation?](#file-sink) → File Sink
- [Using Grafana Loki?](#loki-sink) → Loki Integration
- [Building a custom sink?](#basic-custom-sink) → Custom Implementation
- [Want production examples?](#postgresql-sink) → PostgreSQL, Slack & Elasticsearch
- [Having issues?](#common-issues) → Troubleshooting Guide

## Table of Contents

**Getting Started**

- [Quick Start](#quick-start) - Basic sink configuration and usage
- [Built-in Sinks](#built-in-sinks) - stdout, file, and Loki sinks
  - [Stdout Sink](#stdout-sink) - Console output with formatting
  - [File Sink](#file-sink) - File output with rotation
  - [Loki Sink](#loki-sink) - Grafana Loki integration

**Custom Development**

- [Custom Sinks](#custom-sinks) - Building your own sinks
  - [Basic Custom Sink](#basic-custom-sink) - Simple implementation
  - [Error Handling Best Practices](#error-handling-best-practices) - Robust patterns
  - [Performance Patterns](#performance-patterns) - Batching and async
- [Sink Registry](#sink-registry) - Registration and URI configuration
  - [Basic Registration](#basic-registration) - @register_sink decorator
  - [URI Configuration](#uri-configuration) - String-based config
  - [Registry Management](#registry-management) - List and check sinks

**Implementation Examples**

- [Real-World Examples](#real-world-examples) - Production-ready sinks
  - [PostgreSQL Sink](#postgresql-sink) - Database logging with pooling
  - [Slack Alert Sink](#slack-alert-sink) - Error notifications
  - [Elasticsearch Sink](#elasticsearch-sink) - Log indexing
- [Integration with FastAPI](#integration-with-fastapi) - Lifecycle and health checks

**Reference**

- [Troubleshooting](#troubleshooting) - Common issues and solutions
- [Best Practices](#best-practices) - Design principles and testing

---

## Quick Start

**Basic sink usage:**

```python
from fapilog import configure_logging
from fapilog.settings import LoggingSettings

# Single sink
configure_logging(sinks=["stdout"])

# Multiple sinks
settings = LoggingSettings(sinks=["stdout", "file", "loki"])
configure_logging(settings=settings)
```

**Configuration methods:**

```python
# Via settings object
settings = LoggingSettings(sinks=["stdout", "file:/var/log/app.log"])

# Via environment variable
export FAPILOG_SINKS=stdout,file,loki

# Mixed approaches
settings = LoggingSettings(sinks=["stdout", custom_sink_instance])
```

---

## Built-in Sinks

### Stdout Sink

**Console output with JSON or pretty formatting.**

```python
# Automatic format selection
configure_logging(sinks=["stdout"])

# Force JSON output (production)
settings = LoggingSettings(format="json", sinks=["stdout"])

# Force pretty output (development)
settings = LoggingSettings(format="pretty", sinks=["stdout"])
```

**Output examples:**

```json
// JSON format (production)
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "info",
  "event": "User logged in",
  "trace_id": "abc123def456",
  "user_id": "123"
}
```

```
// Pretty format (development)
2024-01-15T10:30:45.123Z [INFO] User logged in trace_id=abc123def456 user_id=123
```

**Features:**

- Automatic format detection based on environment
- Thread-safe writing with automatic flushing
- No configuration required for basic usage

### File Sink

**File output with automatic rotation support.**

```python
# Basic file logging
settings = LoggingSettings(sinks=["file:/var/log/app.log"])

# With rotation
settings = LoggingSettings(
    sinks=["file:/var/log/app.log?max_size=10MB&backup_count=5"]
)

# Multiple files
settings = LoggingSettings(sinks=[
    "file:/var/log/app.log",
    "file:/var/log/errors.log?level=ERROR"  # Error-only file
])
```

**Configuration options:**

| Parameter      | Type  | Default | Description                      |
| -------------- | ----- | ------- | -------------------------------- |
| `max_size`     | `str` | `None`  | Maximum file size (e.g., "10MB") |
| `backup_count` | `int` | `0`     | Number of backup files to keep   |

**Rotation behavior:**

- When `max_size` is reached, current file is renamed to `.1`, `.2`, etc.
- Oldest backup beyond `backup_count` is deleted
- New logs continue in the original filename

**Example with rotation:**

```python
# Rotate at 10MB, keep 5 backups
settings = LoggingSettings(
    sinks=["file:/var/log/app.log?max_size=10MB&backup_count=5"]
)

# Results in files:
# /var/log/app.log      (current)
# /var/log/app.log.1    (previous)
# /var/log/app.log.2    (older)
# ...
# /var/log/app.log.5    (oldest kept)
```

### Loki Sink

**Send logs to Grafana Loki for aggregation and querying.**

```python
# Basic Loki integration
settings = LoggingSettings(sinks=["loki://http://localhost:3100"])

# With custom labels
settings = LoggingSettings(sinks=[
    "loki://http://localhost:3100?app=myapp&env=production"
])

# Advanced configuration
settings = LoggingSettings(sinks=[
    "loki://http://loki.example.com:3100?batch_size=200&batch_timeout=2.0"
])
```

**Configuration options:**

| Parameter       | Type    | Default | Description              |
| --------------- | ------- | ------- | ------------------------ |
| `labels`        | `dict`  | `{}`    | Static labels to add     |
| `batch_size`    | `int`   | `100`   | Events per batch         |
| `batch_timeout` | `float` | `1.0`   | Batch timeout in seconds |

**Loki integration example:**

```python
from fapilog import configure_logging, log

# Configure with Loki
settings = LoggingSettings(sinks=[
    "stdout",  # Local development
    "loki://http://loki.monitoring.svc.cluster.local:3100?app=user-service&env=production"
])
configure_logging(settings=settings)

# Logs appear in both console and Loki
log.info("User action", user_id="123", action="login")
```

**Querying in Grafana:**

```logql
{app="user-service", env="production"}
| json
| user_id="123"
```

[↑ Back to top](#sinks-guide)

---

## Custom Sinks

**Create custom sinks for specialized output destinations.**

### Basic Custom Sink

```python
from fapilog import Sink
from typing import Dict, Any

class DatabaseSink(Sink):
    def __init__(self, connection_string: str):
        super().__init__()
        self.connection_string = connection_string
        self.connection = None

    async def start(self):
        """Initialize database connection."""
        self.connection = await create_connection(self.connection_string)

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Write log event to database."""
        await self.connection.execute(
            "INSERT INTO logs (timestamp, level, message, metadata) VALUES (?, ?, ?, ?)",
            (
                event_dict.get("timestamp"),
                event_dict.get("level"),
                event_dict.get("event"),
                json.dumps(event_dict)
            )
        )

    async def stop(self):
        """Clean up database connection."""
        if self.connection:
            await self.connection.close()

# Usage
custom_sink = DatabaseSink("postgresql://user:pass@localhost/logs")
settings = LoggingSettings(sinks=["stdout", custom_sink])
configure_logging(settings=settings)
```

### Required vs Optional Methods

| Method       | Required        | Purpose                       | When to Implement            |
| ------------ | --------------- | ----------------------------- | ---------------------------- |
| `write()`    | ✅ **Required** | Process individual log events | Always implement             |
| `__init__()` | ✅ **Required** | Initialize sink state         | Always implement             |
| `start()`    | Optional        | Setup connections/resources   | When using external services |
| `stop()`     | Optional        | Cleanup resources             | When using external services |
| `flush()`    | Optional        | Force data persistence        | When buffering data          |

### Error Handling Best Practices

**1. Never break the application:**

```python
class RobustSink(Sink):
    async def write(self, event_dict: Dict[str, Any]) -> None:
        try:
            await self._send_to_service(event_dict)
        except Exception as e:
            # Log error but don't re-raise
            import logging
            logging.getLogger(__name__).error(
                f"Sink {self._sink_name} failed: {e}",
                extra={"sink_error": True, "original_event": event_dict}
            )
```

**2. Implement retry logic:**

```python
class RetryableSink(Sink):
    def __init__(self, max_retries: int = 3):
        super().__init__()
        self.max_retries = max_retries

    async def write(self, event_dict: Dict[str, Any]) -> None:
        for attempt in range(self.max_retries):
            try:
                await self._send_to_service(event_dict)
                return  # Success
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise  # Final attempt failed
                await asyncio.sleep(1.0 * (2 ** attempt))  # Exponential backoff
```

**3. Handle different error types:**

```python
class SmartSink(Sink):
    async def write(self, event_dict: Dict[str, Any]) -> None:
        try:
            await self._send_to_service(event_dict)
        except ConnectionError:
            # Network issues - queue for retry
            await self._queue_for_retry(event_dict)
        except ValueError as e:
            # Invalid data - log and skip
            logging.warning(f"Invalid event data: {e}")
        except Exception as e:
            # Unexpected error - log and continue
            logging.error(f"Unexpected sink error: {e}")
```

### Performance Patterns

**Batching for high-throughput:**

```python
class BatchedSink(Sink):
    def __init__(self, batch_size: int = 100, batch_timeout: float = 5.0):
        super().__init__()
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.buffer: List[Dict[str, Any]] = []
        self._send_task: Optional[asyncio.Task] = None

    async def start(self):
        self._send_task = asyncio.create_task(self._batch_sender())

    async def write(self, event_dict: Dict[str, Any]) -> None:
        self.buffer.append(event_dict)
        if len(self.buffer) >= self.batch_size:
            await self._send_buffered_data()

    async def _batch_sender(self):
        """Background task for periodic batch sending."""
        while True:
            await asyncio.sleep(self.batch_timeout)
            await self._send_buffered_data()

    async def _send_buffered_data(self):
        if self.buffer:
            await self._send_batch(self.buffer)
            self.buffer.clear()

    async def stop(self):
        if self._send_task:
            self._send_task.cancel()
        if self.buffer:
            await self._send_batch(self.buffer)
```

**Async HTTP patterns:**

```python
class AsyncHTTPSink(Sink):
    def __init__(self, url: str, timeout: float = 10.0):
        super().__init__()
        self.url = url
        self.session: Optional[aiohttp.ClientSession] = None

    async def start(self):
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self.session = aiohttp.ClientSession(timeout=timeout)

    async def write(self, event_dict: Dict[str, Any]) -> None:
        async with self.session.post(self.url, json=event_dict) as response:
            response.raise_for_status()

    async def stop(self):
        if self.session:
            await self.session.close()
```

[↑ Back to top](#sinks-guide)

---

## Sink Registry

**Register custom sinks for reuse across applications using string identifiers.**

### Basic Registration

```python
from fapilog import register_sink, Sink

@register_sink("webhook")
class WebhookSink(Sink):
    def __init__(self, url: str, auth_token: str = None):
        super().__init__()
        self.url = url
        self.auth_token = auth_token

    async def write(self, event_dict: Dict[str, Any]) -> None:
        headers = {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        async with aiohttp.ClientSession() as session:
            async with session.post(self.url, json=event_dict, headers=headers) as response:
                response.raise_for_status()

# Use in configuration
settings = LoggingSettings(sinks=[
    "webhook://api.example.com/logs?auth_token=abc123"
])
```

### URI Configuration

**Configure registered sinks using URI syntax:**

```python
# URI format: scheme://host:port/path?param1=value1&param2=value2

settings = LoggingSettings(sinks=[
    "webhook://api.example.com/logs",
    "webhook://api.example.com/logs?auth_token=secret&timeout=30",
    "database://postgres:5432/logs?table=app_logs&batch_size=50"
])
```

### Registry Management

```python
from fapilog._internal.sink_registry import SinkRegistry

# List all registered sinks
all_sinks = SinkRegistry.list_sinks()
print(all_sinks)  # ['stdout', 'file', 'loki', 'webhook', 'database']

# Check if sink exists
exists = SinkRegistry.is_registered("webhook")

# Get sink class
sink_class = SinkRegistry.get_sink("webhook")
```

### Best Practices for Registration

**1. Use descriptive names:**

```python
@register_sink("elasticsearch")
class ElasticsearchSink(Sink):
    pass

@register_sink("slack_alerts")
class SlackAlertSink(Sink):
    pass
```

**2. Support URI parameters:**

```python
@register_sink("database")
class DatabaseSink(Sink):
    def __init__(self, host: str, port: int = 5432, database: str = "logs", table: str = "events"):
        super().__init__()
        self.host = host
        self.port = port
        self.database = database
        self.table = table

# URI: database://localhost:5432/app_logs?table=user_events
```

**3. Document your sink:**

```python
@register_sink("custom_service")
class CustomServiceSink(Sink):
    """
    Send logs to custom service API.

    URI Format: custom_service://host:port/path?param=value

    Parameters:
        host (str): Target hostname
        port (int): Target port (default: 8080)
        timeout (float): Request timeout in seconds (default: 30.0)
        api_key (str): Authentication API key

    Example:
        custom_service://api.example.com:8080/logs?timeout=10&api_key=abc123
    """
    pass
```

[↑ Back to top](#sinks-guide)

---

## Real-World Examples

### PostgreSQL Sink

**Store logs in PostgreSQL with connection pooling and batching for production workloads.**

```python
import asyncio
import asyncpg
import json
import time
from typing import Dict, Any, List, Optional
from fapilog import register_sink, Sink

@register_sink("postgresql")
class PostgreSQLSink(Sink):
    """
    Production-ready PostgreSQL sink with connection pooling and batching.

    Features:
    - Connection pooling for high performance
    - Automatic schema creation
    - Batched inserts for efficiency
    - Robust error handling with retries
    - Graceful connection management

    URI Format: postgresql://user:password@host:port/database?table=logs&batch_size=100
    """

    def __init__(
        self,
        host: str,
        port: int = 5432,
        database: str = "logs",
        user: str = "postgres",
        password: str = "",
        table: str = "application_logs",
        batch_size: int = 100,
        batch_timeout: float = 5.0,
        pool_size: int = 10,
        max_retries: int = 3
    ):
        super().__init__()
        self.dsn = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        self.table = table
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.pool_size = pool_size
        self.max_retries = max_retries

        # State management
        self.pool: Optional[asyncpg.Pool] = None
        self.buffer: List[Dict[str, Any]] = []
        self._batch_task: Optional[asyncio.Task] = None
        self._started = False

    async def start(self):
        """Initialize connection pool and create table schema."""
        if self._started:
            return

        try:
            # Create connection pool
            self.pool = await asyncpg.create_pool(
                self.dsn,
                min_size=2,
                max_size=self.pool_size,
                command_timeout=60
            )

            # Create table if it doesn't exist
            await self._create_table_if_not_exists()

            # Start background batch processor
            self._batch_task = asyncio.create_task(self._batch_processor())

            self._started = True
            print(f"✅ PostgreSQL sink connected to {self.dsn}")

        except Exception as e:
            print(f"❌ PostgreSQL sink failed to start: {e}")
            raise

    async def stop(self):
        """Clean shutdown with final data flush."""
        if not self._started:
            return

        # Cancel background task
        if self._batch_task:
            self._batch_task.cancel()
            try:
                await self._batch_task
            except asyncio.CancelledError:
                pass

        # Flush remaining data
        if self.buffer:
            await self._flush_buffer()

        # Close connection pool
        if self.pool:
            await self.pool.close()

        self._started = False
        print("✅ PostgreSQL sink shutdown complete")

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Add log event to buffer for batched insert."""
        if not self._started:
            raise RuntimeError("PostgreSQL sink not started")

        # Add timestamp if not present
        if 'timestamp' not in event_dict:
            event_dict['timestamp'] = time.time()

        self.buffer.append(event_dict)

        # Flush immediately if buffer is full
        if len(self.buffer) >= self.batch_size:
            await self._flush_buffer()

    async def _create_table_if_not_exists(self):
        """Create logs table with optimized schema."""
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.table} (
            id BIGSERIAL PRIMARY KEY,
            timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            level VARCHAR(20) NOT NULL,
            event TEXT NOT NULL,
            trace_id VARCHAR(64),
            span_id VARCHAR(64),
            user_id VARCHAR(64),
            hostname VARCHAR(255),
            pid INTEGER,
            metadata JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        -- Indexes for common queries
        CREATE INDEX IF NOT EXISTS idx_{self.table}_timestamp ON {self.table} (timestamp);
        CREATE INDEX IF NOT EXISTS idx_{self.table}_level ON {self.table} (level);
        CREATE INDEX IF NOT EXISTS idx_{self.table}_trace_id ON {self.table} (trace_id) WHERE trace_id IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_{self.table}_user_id ON {self.table} (user_id) WHERE user_id IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_{self.table}_metadata_gin ON {self.table} USING GIN (metadata);
        """

        async with self.pool.acquire() as conn:
            await conn.execute(create_table_sql)

    async def _batch_processor(self):
        """Background task that flushes buffer periodically."""
        while True:
            try:
                await asyncio.sleep(self.batch_timeout)
                if self.buffer:
                    await self._flush_buffer()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"⚠️ PostgreSQL batch processor error: {e}")

    async def _flush_buffer(self):
        """Flush current buffer to database with retry logic."""
        if not self.buffer:
            return

        batch = self.buffer.copy()
        self.buffer.clear()

        for attempt in range(self.max_retries):
            try:
                await self._insert_batch(batch)
                return  # Success
            except Exception as e:
                if attempt == self.max_retries - 1:
                    print(f"❌ PostgreSQL insert failed after {self.max_retries} attempts: {e}")
                    # Could implement dead letter queue here
                else:
                    print(f"⚠️ PostgreSQL insert attempt {attempt + 1} failed: {e}")
                    await asyncio.sleep(1.0 * (2 ** attempt))  # Exponential backoff

    async def _insert_batch(self, batch: List[Dict[str, Any]]):
        """Insert a batch of log events using efficient bulk insert."""
        if not batch:
            return

        # Prepare data for bulk insert
        records = []
        for event in batch:
            # Extract common fields
            timestamp = event.get('timestamp', time.time())
            level = event.get('level', 'INFO')
            message = event.get('event', '')
            trace_id = event.get('trace_id')
            span_id = event.get('span_id')
            user_id = event.get('user_id')
            hostname = event.get('hostname')
            pid = event.get('pid')

            # Store remaining fields as metadata
            metadata = {k: v for k, v in event.items()
                       if k not in {'timestamp', 'level', 'event', 'trace_id',
                                   'span_id', 'user_id', 'hostname', 'pid'}}

            records.append((
                # Convert timestamp to datetime
                asyncpg.pgproto.core.timestamp_from_unix(timestamp),
                level,
                message,
                trace_id,
                span_id,
                user_id,
                hostname,
                pid,
                json.dumps(metadata) if metadata else None
            ))

        # Bulk insert using copy_records_to_table for maximum performance
        async with self.pool.acquire() as conn:
            await conn.copy_records_to_table(
                self.table,
                records=records,
                columns=['timestamp', 'level', 'event', 'trace_id', 'span_id',
                        'user_id', 'hostname', 'pid', 'metadata']
            )

    async def flush(self):
        """Force flush of current buffer."""
        await self._flush_buffer()

# Usage examples
@register_sink("postgres")  # Alias for convenience
class PostgreSQLSinkAlias(PostgreSQLSink):
    pass

# Configuration examples
settings = LoggingSettings(sinks=[
    # Basic usage
    "postgresql://user:password@localhost:5432/myapp",

    # With custom table and batching
    "postgresql://user:password@localhost:5432/logs?table=api_logs&batch_size=200",

    # Production configuration
    "postgresql://user:password@db.example.com:5432/production_logs?table=application_logs&batch_size=500&pool_size=20"
])

# Direct instantiation
postgres_sink = PostgreSQLSink(
    host="localhost",
    port=5432,
    database="myapp",
    user="logger",
    password="secure_password",
    table="application_logs",
    batch_size=100,
    pool_size=10
)

# FastAPI integration with lifecycle management
from fastapi import FastAPI
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    postgres_sink = PostgreSQLSink(
        host="localhost",
        database="myapp",
        user="logger",
        password="password"
    )
    await postgres_sink.start()

    settings = LoggingSettings(sinks=["stdout", postgres_sink])
    configure_logging(settings=settings, app=app)

    yield

    # Shutdown
    await postgres_sink.stop()

app = FastAPI(lifespan=lifespan)
```

**Key Features:**

**🚀 Performance Optimized**

- Connection pooling for concurrent requests
- Batched inserts using PostgreSQL `COPY` for maximum throughput
- Background batch processor with configurable timeouts
- Efficient JSONB storage for metadata

**🛡️ Production Ready**

- Robust error handling with exponential backoff
- Graceful connection management and cleanup
- Automatic table creation with optimized indexes
- Health monitoring and logging

**🔧 Flexible Configuration**

- URI-based configuration support
- Customizable table names and batch sizes
- Connection pool sizing options
- Integration with FastAPI lifecycle events

**📊 Database Schema**

The sink creates an optimized table structure:

```sql
CREATE TABLE application_logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    level VARCHAR(20) NOT NULL,
    event TEXT NOT NULL,
    trace_id VARCHAR(64),
    span_id VARCHAR(64),
    user_id VARCHAR(64),
    hostname VARCHAR(255),
    pid INTEGER,
    metadata JSONB,  -- Flexible storage for additional fields
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Performance indexes
CREATE INDEX idx_application_logs_timestamp ON application_logs (timestamp);
CREATE INDEX idx_application_logs_level ON application_logs (level);
CREATE INDEX idx_application_logs_trace_id ON application_logs (trace_id);
CREATE INDEX idx_application_logs_metadata_gin ON application_logs USING GIN (metadata);
```

**🔍 Querying Your Logs**

```sql
-- Find all errors in the last hour
SELECT * FROM application_logs
WHERE level = 'ERROR'
AND timestamp > NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC;

-- Search within metadata
SELECT * FROM application_logs
WHERE metadata @> '{"user_id": "123"}'::jsonb;

-- Trace-specific logs
SELECT * FROM application_logs
WHERE trace_id = 'abc123def456'
ORDER BY timestamp;
```

[↑ Back to top](#sinks-guide)

### Slack Alert Sink

**Send error logs to Slack channels:**

```python
@register_sink("slack_alerts")
class SlackAlertSink(Sink):
    def __init__(self, webhook_url: str, channel: str = "#alerts",
                 batch_size: int = 5, batch_timeout: float = 30.0):
        super().__init__()
        self.webhook_url = webhook_url
        self.channel = channel
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.buffer: List[Dict[str, Any]] = []
        self.session: Optional[aiohttp.ClientSession] = None

    async def start(self):
        self.session = aiohttp.ClientSession()

    async def write(self, event_dict: Dict[str, Any]) -> None:
        # Only send error-level logs
        if event_dict.get("level") != "error":
            return

        self.buffer.append(event_dict)
        if len(self.buffer) >= self.batch_size:
            await self._send_alerts()

    async def _send_alerts(self):
        if not self.buffer:
            return

        message = self._prepare_slack_message(self.buffer)
        async with self.session.post(self.webhook_url, json=message) as response:
            response.raise_for_status()

        self.buffer.clear()

    def _prepare_slack_message(self, alerts):
        error_count = len(alerts)
        trace_ids = [alert.get("trace_id") for alert in alerts if alert.get("trace_id")]

        return {
            "channel": self.channel,
            "text": f"🚨 {error_count} error(s) detected",
            "attachments": [{
                "color": "danger",
                "fields": [
                    {"title": "Error Count", "value": str(error_count), "short": True},
                    {"title": "Trace IDs", "value": ", ".join(trace_ids[:5]), "short": True}
                ]
            }]
        }

    async def stop(self):
        if self.buffer:
            await self._send_alerts()
        if self.session:
            await self.session.close()

# Usage
settings = LoggingSettings(sinks=[
    "stdout",
    "slack_alerts://hooks.slack.com/services/YOUR/WEBHOOK/URL?channel=#alerts"
])
```

### Elasticsearch Sink

**Index logs in Elasticsearch:**

```python
@register_sink("elasticsearch")
class ElasticsearchSink(Sink):
    def __init__(self, hosts: str, index_prefix: str = "logs",
                 batch_size: int = 100, batch_timeout: float = 5.0):
        super().__init__()
        self.hosts = hosts.split(",")
        self.index_prefix = index_prefix
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.buffer: List[Dict[str, Any]] = []
        self.es_client = None

    async def start(self):
        from elasticsearch import AsyncElasticsearch
        self.es_client = AsyncElasticsearch(self.hosts)

    async def write(self, event_dict: Dict[str, Any]) -> None:
        self.buffer.append(event_dict)
        if len(self.buffer) >= self.batch_size:
            await self._index_documents()

    async def _index_documents(self):
        if not self.buffer:
            return

        # Prepare bulk indexing
        actions = []
        for doc in self.buffer:
            timestamp = doc.get("timestamp", time.time())
            index_name = f"{self.index_prefix}-{datetime.fromtimestamp(timestamp).strftime('%Y.%m.%d')}"

            actions.append({"index": {"_index": index_name}})
            actions.append(doc)

        # Bulk index
        from elasticsearch.helpers import async_bulk
        await async_bulk(self.es_client, actions)
        self.buffer.clear()

    async def stop(self):
        if self.buffer:
            await self._index_documents()
        if self.es_client:
            await self.es_client.close()

# Usage
settings = LoggingSettings(sinks=[
    "elasticsearch://localhost:9200?index_prefix=app-logs&batch_size=200"
])
```

[↑ Back to top](#sinks-guide)

---

## Integration with FastAPI

### Lifecycle Management

```python
from fastapi import FastAPI
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize custom sinks
    database_sink = DatabaseSink("postgresql://user:pass@localhost/logs")
    await database_sink.start()

    slack_sink = SlackAlertSink("https://hooks.slack.com/...")
    await slack_sink.start()

    # Configure logging with custom sinks
    settings = LoggingSettings(sinks=["stdout", database_sink, slack_sink])
    configure_logging(settings=settings, app=app)

    yield

    # Shutdown: Clean up sinks
    await database_sink.stop()
    await slack_sink.stop()

app = FastAPI(lifespan=lifespan)
```

### Health Check Integration

```python
class MonitoredSink(Sink):
    def __init__(self):
        super().__init__()
        self.write_count = 0
        self.error_count = 0
        self.last_write_time = None

    async def write(self, event_dict: Dict[str, Any]) -> None:
        try:
            await self._send_to_service(event_dict)
            self.write_count += 1
            self.last_write_time = time.time()
        except Exception as e:
            self.error_count += 1
            raise

    def health_status(self) -> Dict[str, Any]:
        return {
            "sink_name": self._sink_name,
            "status": "healthy" if self.error_count == 0 else "degraded",
            "write_count": self.write_count,
            "error_count": self.error_count,
            "last_write_time": self.last_write_time
        }

# Add health check endpoint
@app.get("/health/sinks")
async def sink_health():
    return [sink.health_status() for sink in monitored_sinks]
```

[↑ Back to top](#sinks-guide)

---

## Troubleshooting

### Common Issues

**1. Sink not receiving events**

```python
# Check if sink is properly registered
from fapilog._internal.sink_registry import SinkRegistry
print(SinkRegistry.list_sinks())

# Verify sink configuration
settings = LoggingSettings(sinks=["your_sink"])
print(settings.sinks)  # Should show your sink
```

**2. Connection errors**

```python
class ConnectionTestSink(Sink):
    async def start(self):
        try:
            await self._test_connection()
            print("✅ Connection successful")
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            raise

    async def _test_connection(self):
        # Your connection test logic
        pass
```

**3. Performance issues**

```python
# Monitor sink performance
class PerformanceSink(Sink):
    def __init__(self):
        super().__init__()
        self.write_times = []

    async def write(self, event_dict: Dict[str, Any]) -> None:
        start_time = time.time()
        try:
            await self._actual_write(event_dict)
        finally:
            duration = time.time() - start_time
            self.write_times.append(duration)

            # Log slow writes
            if duration > 1.0:  # 1 second threshold
                print(f"⚠️ Slow sink write: {duration:.2f}s")

    def get_avg_write_time(self):
        return sum(self.write_times) / len(self.write_times) if self.write_times else 0
```

### Debug Mode

```python
# Enable debug logging for sinks
import logging
logging.getLogger("fapilog.sinks").setLevel(logging.DEBUG)

# Add debug sink to trace events
class DebugSink(Sink):
    async def write(self, event_dict: Dict[str, Any]) -> None:
        print(f"🐛 Debug sink received: {event_dict}")

settings = LoggingSettings(sinks=["debug", "your_actual_sink"])
```

---

## Best Practices

### 1. Sink Design Principles

- **Single Responsibility**: Each sink handles one output destination
- **Fail-Safe**: Sink errors shouldn't break application logging
- **Async-First**: Use async/await patterns for I/O operations
- **Resource Management**: Properly initialize and cleanup resources

### 2. Performance Optimization

- **Batch Operations**: Group multiple events for bulk operations
- **Connection Pooling**: Reuse connections across writes
- **Circuit Breaking**: Disable failing sinks temporarily
- **Backpressure**: Handle queue overflow gracefully

### 3. Monitoring and Observability

- **Health Checks**: Expose sink status via health endpoints
- **Metrics**: Track write counts, error rates, latencies
- **Alerting**: Monitor sink failures and performance degradation
- **Logging**: Log sink operations (but avoid recursive logging!)

### 4. Testing Custom Sinks

```python
import pytest
from fapilog.testing import MockSink

@pytest.mark.asyncio
async def test_custom_sink():
    sink = CustomSink("test://config")
    await sink.start()

    test_event = {"level": "info", "event": "test message"}
    await sink.write(test_event)

    # Verify sink behavior
    assert sink.write_count == 1

    await sink.stop()

# Use MockSink for testing
mock_sink = MockSink()
settings = LoggingSettings(sinks=[mock_sink])
configure_logging(settings=settings)

# Verify events were sent to mock
assert len(mock_sink.events) == expected_count
```

[↑ Back to top](#sinks-guide)

---

## Summary

This guide covered:

- **Built-in sinks**: stdout, file, and Loki with configuration options
- **Custom sink development**: interfaces, patterns, and best practices
- **Sink registry**: registration and URI-based configuration
- **Real-world examples**: Slack alerts, Elasticsearch indexing
- **FastAPI integration**: lifecycle management and health checks
- **Troubleshooting**: common issues and debugging techniques
- **Best practices**: design principles and testing approaches

**Next steps:**

- Try the [Monitoring Guide](monitoring.md) for sink performance tracking
- See [Production Deployment](production.md) for scaling considerations
- Check [API Reference](../api-reference.md) for quick parameter lookup
