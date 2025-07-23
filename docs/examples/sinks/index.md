# Sink Examples

**Custom output destinations and integration patterns**

This section covers sink development and real-world examples for sending logs to databases, external services, and custom destinations. Perfect for developers who need to integrate with systems not supported out-of-the-box.

---

## 📚 What You'll Learn

- **Real-World Sinks** - Production-ready examples (PostgreSQL, Elasticsearch, Slack, Redis)
- **Integration Patterns** - FastAPI, Docker, Kubernetes deployment patterns
- **Custom Development** - Build your own sinks from scratch
- **Testing & Debugging** - Validate sink implementations

---

## 🎯 When You Need Custom Sinks

**✅ Perfect for custom sinks:**

- MongoDB, Kafka, Custom APIs
- Proprietary enterprise systems
- Specialized monitoring platforms
- Custom analytics pipelines

**⚠️ Check existing options first:**

- PostgreSQL, Elasticsearch, Redis
- File outputs, Loki integration

**❌ Built-in sinks available:**

- Basic file output, stdout, syslog

---

## 🚀 Real-World Sink Examples

### [PostgreSQL Sink](../../sink_examples/postgres_sink.py)

**Database logging with connection pooling and error handling**

```python
import asyncpg
from fapilog import register_sink, Sink

@register_sink("postgres")
class PostgresSink(Sink):
    def __init__(self, host="localhost", port=5432, database="logs",
                 user=None, password=None, **kwargs):
        super().__init__()
        # Configuration validation
        if not all([database, user, password]):
            raise ValueError("database, user, and password are required")

        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.pool = None

    async def start(self):
        """Initialize database connection pool."""
        self.pool = await asyncpg.create_pool(
            host=self.host, port=self.port,
            database=self.database, user=self.user, password=self.password
        )

    async def write(self, event_dict: Dict[str, Any]) -> None:
        """Write log event to PostgreSQL."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO logs (timestamp, level, event, data)
                VALUES ($1, $2, $3, $4)
            """, event_dict.get("timestamp"), event_dict.get("level"),
                 event_dict.get("event"), event_dict)
```

**Key Features:**

- ✅ Connection pooling for performance
- ✅ Comprehensive error handling
- ✅ Configuration validation
- ✅ Production-ready patterns

---

### [Elasticsearch Sink](../../sink_examples/elasticsearch_sink.py)

**Search index integration for log analytics**

High-performance Elasticsearch integration with automatic index management and bulk operations.

**Key Features:**

- ✅ Elasticsearch client integration
- ✅ Index management
- ✅ Bulk operation support
- ✅ Error handling and retries

---

### [Slack Sink](../../sink_examples/slack_sink.py)

**Real-time alerting for critical events**

Send error logs and alerts directly to Slack channels with rich formatting and filtering.

**Key Features:**

- ✅ Webhook integration
- ✅ Level-based filtering
- ✅ Rich message formatting
- ✅ Error context preservation

---

### [Redis Sink](../../sink_examples/redis_sink.py)

**High-speed caching and pub/sub patterns**

Redis integration for high-speed logging, caching, and pub/sub notification patterns.

**Key Features:**

- ✅ Redis connection management
- ✅ Pub/sub pattern support
- ✅ TTL-based log retention
- ✅ High-performance operations

---

## 🐳 Integration Patterns

### [FastAPI Integration](../../sink_integrations/fastapi_integration.py)

**Web application patterns with custom sinks**

```python
from fastapi import FastAPI
from fapilog import configure_logging, register_sink

@register_sink("custom")
class CustomSink(Sink):
    # Your custom sink implementation
    pass

app = FastAPI()
configure_logging(
    app=app,
    sinks=["custom://localhost:8080", "stdout"]
)
```

**Key Features:**

- ✅ FastAPI lifecycle integration
- ✅ Multiple sink configuration
- ✅ Request correlation
- ✅ Production deployment patterns

---

### [Docker Integration](../../sink_integrations/docker_integration.py)

**Containerized deployment with environment configuration**

Docker patterns for deploying applications with custom sinks using environment variables and container orchestration.

**Key Features:**

- ✅ Environment-based configuration
- ✅ Container networking
- ✅ Multi-stage builds
- ✅ Production deployment

---

### [Kubernetes Integration](../../sink_integrations/kubernetes_integration.py)

**Cloud-native patterns for microservices**

Kubernetes deployment patterns with ConfigMaps, Secrets, and service discovery for custom sink integration.

**Key Features:**

- ✅ ConfigMap configuration
- ✅ Secret management
- ✅ Service discovery
- ✅ Health checks

---

## 🔧 Custom Sink Development

### [13 - Loki Sink](../../13_loki_sink.py)

**Complete Loki integration example**

Full implementation of Grafana Loki sink with label management, batching, and error handling.

### [14 - Multiple Sinks](../../14_multiple_sinks.py)

**Configure multiple output destinations**

```python
from fapilog import configure_logging
from fapilog.sinks.stdout import StdoutSink
from fapilog.sinks.file import FileSink

stdout_sink = StdoutSink(pretty=True)
file_sink = FileSink("/var/log/app.log")

configure_logging(sinks=[stdout_sink, file_sink])
```

### [15 - Custom Sink](../../15_custom_sink.py)

**Build custom sinks from scratch**

Complete tutorial for building custom sinks with HTTP endpoints, batching, and error handling.

---

## 🧪 Testing & Validation

### [Sink Testing Examples](../../sink_testing_examples.py)

**Comprehensive testing patterns for custom sinks**

Testing frameworks and patterns for validating sink implementations including unit tests, integration tests, and performance benchmarks.

**Key Features:**

- ✅ Unit testing patterns
- ✅ Integration test frameworks
- ✅ Performance benchmarking
- ✅ Error scenario testing

---

## 🎯 Next Steps

### 📚 **Learn Sink Development**

- **[Sink Development Guide](../../sink-development.md)** - Complete development tutorial
- **[Sink Best Practices](../../sink-best-practices.md)** - Production-ready patterns
- **[Sink Performance Guide](../../sink-performance.md)** - Optimization techniques

### 🚀 **Advanced Topics**

- **[Advanced Development](../../advanced-development.md)** - Complete advanced guide
- **[Advanced Patterns](../advanced/index.md)** - Security, tracing, enrichment

### 🏭 **Production Deployment**

- **[Production Examples](../production/index.md)** - High-performance configurations
- **[Configuration Guide](../../config.md)** - Enterprise settings

---

## 💡 Sink Development Tips

1. **Study Examples** - Start with real-world implementations
2. **Handle Errors** - Never let sink errors break your app
3. **Test Thoroughly** - Use the testing frameworks provided
4. **Optimize Performance** - Implement batching for high throughput
5. **Follow Patterns** - Use the integration examples for deployment
6. **Join Community** - Share your sinks with other developers

Ready to build your own? Start with the [Sink Development Guide](../../sink-development.md)!
