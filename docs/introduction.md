# Introduction

**Transform your application logging from simple text messages into rich, structured data that powers observability, debugging, and compliance.**

Fapilog is the modern logging solution that FastAPI developers have been waiting for. Built specifically for Python applications with first-class FastAPI support, it provides structured JSON logging with automatic context enrichment, trace correlation, and production-ready features out of the box.

---

## Why Use Fapilog?

### **For FastAPI Developers**

- **Zero Configuration** - Works out of the box with automatic middleware integration
- **Request Correlation** - Automatic trace IDs and request context for debugging
- **Performance First** - Async logging queue prevents blocking your application
- **Structured Data** - JSON logs that work seamlessly with modern observability tools

### **For DevOps & SRE Teams**

- **Multiple Output Sinks** - Send logs to files, stdout, Loki, or custom destinations
- **PII Protection** - Automatic redaction of sensitive data for compliance
- **Container Ready** - Multi-instance logging with proper isolation
- **Production Hardened** - Fault tolerance and error handling built-in

### **For Development Teams**

- **Developer Experience** - Simple API that feels natural to Python developers
- **Extensible Architecture** - Custom enrichers and sinks for specific needs
- **Rich Context** - Automatic user tracking, performance metrics, and environment info
- **Debugging Superpowers** - Trace requests across services and correlate errors

---

## Key Benefits

### **1. Structured Logging by Default**

```python
# Instead of: "User 123 logged in"
# You get rich, structured data:
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "info",
  "event": "User logged in",
  "user_id": "123",
  "session_id": "abc123",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "duration_ms": 45.2,
  "trace_id": "req-abc123-def456"
}
```

### **2. Automatic Context Enrichment**

- **Request correlation** across microservices
- **User context** and session tracking
- **Performance metrics** and resource usage
- **Environment information** and deployment details

### **3. Production Ready**

- **Async logging queue** for high-performance applications
- **Multiple output sinks** (file, stdout, Loki, custom)
- **PII redaction** for compliance requirements
- **Error handling** and fault tolerance

### **4. FastAPI Integration**

- **Automatic middleware** registration
- **Request/response logging** with context
- **Error tracking** with full stack traces
- **Performance monitoring** with built-in metrics

---

## Comparison with Alternatives

| Feature                 | Fapilog           | Python logging     | structlog         | loguru            |
| ----------------------- | ----------------- | ------------------ | ----------------- | ----------------- |
| **FastAPI Integration** | ✅ First-class    | ❌ Manual setup    | ❌ Manual setup   | ❌ Manual setup   |
| **Structured JSON**     | ✅ Default        | ❌ Requires config | ✅ Default        | ✅ Default        |
| **Request Correlation** | ✅ Automatic      | ❌ Manual          | ❌ Manual         | ❌ Manual         |
| **Async Queue**         | ✅ Built-in       | ❌ No              | ❌ No             | ❌ No             |
| **Multiple Sinks**      | ✅ Native         | ❌ Complex         | ❌ Complex        | ❌ Complex        |
| **PII Redaction**       | ✅ Automatic      | ❌ Manual          | ❌ Manual         | ❌ Manual         |
| **Container Support**   | ✅ Multi-instance | ❌ Single logger   | ❌ Single logger  | ❌ Single logger  |
| **Performance**         | ✅ Optimized      | ⚠️ Basic           | ⚠️ Basic          | ⚠️ Basic          |
| **Learning Curve**      | ✅ Simple         | ⚠️ Complex         | ⚠️ Complex        | ⚠️ Moderate       |
| **Production Ready**    | ✅ Out of box     | ❌ Requires setup  | ❌ Requires setup | ❌ Requires setup |

### **Why Not Python Logging?**

- **No structured output** - Just text messages
- **Manual correlation** - No automatic request tracking
- **Performance issues** - Synchronous logging can block your app
- **Complex configuration** - Requires extensive setup for production

### **Why Not structlog?**

- **No FastAPI integration** - Manual middleware setup required
- **No async queue** - Synchronous logging can impact performance
- **No built-in sinks** - Requires custom configuration for multiple outputs
- **No PII protection** - Manual redaction implementation needed

### **Why Not loguru?**

- **No request correlation** - Manual trace ID management
- **No container support** - Single logger instance limitations
- **No automatic enrichment** - Manual context addition required
- **Limited extensibility** - Less flexible for custom requirements
