# Sink Troubleshooting Guide

**Part of the [Advanced Development](advanced-development.md) journey - Debug and resolve common issues**

> 📚 **Previous Steps:** [Sink Development Guide](sink-development.md) → [Sink Best Practices](sink-best-practices.md) → [Sink Performance Guide](sink-performance.md)

---

## Overview

This guide helps you debug and resolve common issues when developing and deploying custom sinks. Use this as your reference when things go wrong or when optimizing sink performance in production.

**This is Step 4 in the Sink Development Journey:**

1. [Learn the Fundamentals](sink-development.md)
2. [Production-Ready Development](sink-best-practices.md)
3. [Performance Optimization](sink-performance.md)
4. **Debugging & Troubleshooting** (You are here)

---

## Common Issues and Solutions

### Sink Registration Fails

**Error:** `SinkRegistrationError: Failed to register sink 'my_sink'`

**Solutions:**

- Ensure sink class inherits from `Sink`
- Check that `write` method is async
- Verify sink name is unique

### URI Parsing Errors

**Error:** `SinkConfigurationError: Invalid URI format`

**Solutions:**

- Use standard URI format: `scheme://[user:pass@]host[:port]/path[?param=value]`
- URL-encode special characters in parameters
- Check parameter names match sink constructor

### Performance Issues

**Symptoms:** High latency, memory leaks, connection timeouts

**Solutions:**

- Implement batching for high throughput
- Use connection pooling for external services
- Add proper error handling and retries
- Monitor sink performance with testing utilities

---

## 🎉 Congratulations! Sink Development Journey Complete

You've now mastered the complete sink development journey:

✅ **[Fundamentals](sink-development.md)** - Architecture and basic implementation  
✅ **[Best Practices](sink-best-practices.md)** - Production-ready patterns  
✅ **[Performance](sink-performance.md)** - High-throughput optimization  
✅ **[Troubleshooting](sink-troubleshooting.md)** - Debugging and problem resolution

**You're now equipped to:**

- Build custom sinks for any destination
- Deploy them safely in production
- Optimize for high performance
- Debug issues when they arise

---

## What's Next?

### 🚀 **Advanced Topics**

- **[Container Architecture](../examples/index.md#container-architecture)** - Multi-service logging patterns
- **[Custom Enrichers](advanced-development.md#custom-enrichers)** - Add custom context to logs
- **[Performance Monitoring](../examples/index.md#performance--monitoring)** - Monitor your logging system

### 🤝 **Community Engagement**

- **[Share Your Sink](https://github.com/chris-haste/fastapi-logger/discussions)** - Help other developers
- **[Contributing Guide](contributing.md)** - Submit improvements back to the project
- **[GitHub Issues](https://github.com/chris-haste/fastapi-logger/issues)** - Report bugs or request features

### 📖 **Continue Learning**

- **[Real-World Examples](../examples/sink_examples/)** - Study production implementations
- **[Integration Patterns](../examples/sink_integrations/)** - FastAPI, Docker, Kubernetes
- **[Advanced Development Overview](advanced-development.md)** - Explore other advanced topics

---

## Quick Reference

**Need help with a specific issue?**

- **Registration problems** → Check inheritance and method signatures
- **URI configuration** → Verify format and parameter names
- **Performance issues** → Review [Performance Guide](sink-performance.md)
- **Production deployment** → Follow [Best Practices](sink-best-practices.md)

**Want to share your sink?**

- **[Community Discussions](https://github.com/chris-haste/fastapi-logger/discussions)** - Share implementations
- **[Contributing Guide](contributing.md)** - Submit to the official project

---

## Resources

- **[Advanced Development Overview](advanced-development.md)** - Complete advanced topics overview
- **[Sink Examples](../examples/sink_examples/)** - Real-world troubleshooting examples
- **[Community Support](https://github.com/chris-haste/fastapi-logger/discussions)** - Get help from other developers
- **[GitHub Issues](https://github.com/chris-haste/fastapi-logger/issues)** - Report bugs or request features
