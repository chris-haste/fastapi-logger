# Examples & Recipes

**Real-world examples and recipes for using Fapilog in different scenarios.**

This section provides practical, copy-paste ready examples that demonstrate Fapilog's capabilities across various use cases. Each example includes complete code, explanations, and best practices.

**See also:** [Quickstart Tutorial](../quickstart.md), [API Reference](../api-reference.md), [User Guide](../user-guide.md)

---

## 🎯 Choose Your Path

### 🆕 **New to Fapilog?**

**[Basic Usage Examples](basic/index.md)**  
_Perfect for developers just getting started_

- Minimal setup and configuration
- Environment-based configurations
- Output formats (JSON, pretty, auto)
- Logging levels and filtering

### 🔧 **Building Web Applications?**

**[FastAPI Integration Examples](fastapi/index.md)**  
_Web application logging patterns_

- Automatic request/response logging
- Custom middleware patterns
- Error handling and trace correlation
- User context enrichment

### 🏭 **Deploying to Production?**

**[Production Deployment Examples](production/index.md)**  
_High-performance and scalable patterns_

- Async queue configuration
- Performance optimization
- Metrics and monitoring
- Container architecture

### 🔒 **Need Advanced Features?**

**[Advanced Patterns Examples](advanced/index.md)**  
_Security, tracing, and enrichment_

- Security logging and audit trails
- PII redaction and compliance
- Distributed tracing
- Custom enrichers

### 🚀 **Building Custom Components?**

**[Sink Development Examples](sinks/index.md)**  
_Custom output destinations_

- Real-world sink implementations
- Integration patterns
- Testing and validation
- Performance optimization

---

## 📊 Quick Reference Table

| Use Case            | Section                           | Key Examples                        |
| ------------------- | --------------------------------- | ----------------------------------- |
| **Getting Started** | [Basic](basic/index.md)           | Setup, Environment Config, Formats  |
| **Web Apps**        | [FastAPI](fastapi/index.md)       | Middleware, Error Handling, Tracing |
| **Production**      | [Production](production/index.md) | Queues, Performance, Monitoring     |
| **Enterprise**      | [Advanced](advanced/index.md)     | Security, PII Redaction, Enrichment |
| **Custom Sinks**    | [Sinks](sinks/index.md)           | PostgreSQL, Elasticsearch, Slack    |

---

## 🚀 Popular Examples

### Quick Start

```python
from fapilog import configure_logging, log

# Basic setup - works immediately
configure_logging()
log.info("Hello, structured logging!", user_id="123")
```

_[Full example →](basic/index.md)_

### FastAPI Integration

```python
from fastapi import FastAPI
from fapilog import configure_logging

app = FastAPI()
configure_logging(app=app)  # Automatic middleware + tracing
```

_[Full example →](fastapi/index.md)_

### Production Queue

```python
from fapilog.settings import LoggingSettings

# High-performance async logging
settings = LoggingSettings(
    queue_enabled=True,
    queue_size=10000,
    batch_size=100
)
configure_logging(settings=settings)
```

_[Full example →](production/index.md)_

### Custom Sink

```python
from fapilog import register_sink, Sink

@register_sink("my_service")
class MyServiceSink(Sink):
    async def write(self, event_dict):
        # Send to your custom destination
        await send_to_service(event_dict)
```

_[Full example →](sinks/index.md)_

---

## 🎓 Learning Path

**Recommended progression for mastering Fapilog:**

```
1. 📚 Start with Basic Examples
   ↓
2. 🔧 Add FastAPI Integration
   ↓
3. 🏭 Optimize for Production
   ↓
4. 🔒 Implement Advanced Patterns
   ↓
5. 🚀 Build Custom Components
```

Each section builds on the previous one, but you can jump to any section based on your immediate needs.

---

## 💡 Tips for Success

### 🎯 **Choose the Right Starting Point**

- **New to structured logging?** → [Basic Examples](basic/index.md)
- **Have a FastAPI app?** → [FastAPI Examples](fastapi/index.md)
- **Ready for production?** → [Production Examples](production/index.md)
- **Need advanced features?** → [Advanced Examples](advanced/index.md)
- **Custom integrations?** → [Sink Examples](sinks/index.md)

### 📋 **Best Practices**

1. **Start Simple** - Begin with basic setup, add complexity gradually
2. **Use Examples** - Copy-paste and adapt the provided examples
3. **Test Thoroughly** - Validate configurations before production
4. **Monitor Performance** - Use metrics to understand impact
5. **Follow Patterns** - Use established patterns for reliability

### 🔗 **Next Steps**

Ready to dive deeper? Each example section includes:

- ✅ Complete, runnable code
- ✅ Detailed explanations
- ✅ Best practices and tips
- ✅ Links to related topics
- ✅ Production deployment guidance

---

## 🆘 Need Help?

- **Documentation Issues?** → [Troubleshooting Guide](../troubleshooting.md)
- **Configuration Questions?** → [Configuration Guide](../config.md)
- **Advanced Development?** → [Advanced Development](../advanced-development.md)
- **Community Support?** → [GitHub Discussions](https://github.com/chris-haste/fastapi-logger/discussions)

---

**Ready to start?** Choose your path above and begin with the examples that match your needs!
