# Fapilog Documentation

> **Note:** All documentation is written in Markdown (`.md`). Do not add `.rst` files or navigation.

**Current Version:** {{ version }} | [Changelog](https://github.com/chris-haste/fastapi-logger/blob/main/CHANGELOG.md) | [GitHub](https://github.com/chris-haste/fastapi-logger)

---

> 🚀 **New to Fapilog? Start Here:**
>
> 1. [Introduction](introduction.md) → Overview and key benefits
> 2. [Primer](primer.md) → What is Fapilog and core concepts
> 3. [Quickstart](quickstart.md) → Get up and running in 5 minutes
> 4. [Core Concepts](core-concepts.md) → Understand the architecture
> 5. [User Guide](user-guide.md) → Step-by-step tutorials

---

```{toctree}
:maxdepth: 2
:caption: 📚 Getting Started

introduction.md
primer.md
quickstart.md
core-concepts.md
```

```{toctree}
:maxdepth: 2
:caption: 🔧 Core Usage

user-guide.md
config.md
api-reference.md
```

```{toctree}
:maxdepth: 2
:caption: 📘 Feature Guides

guides/fastapi-integration.md
guides/configuration.md
guides/security.md
guides/sinks.md
guides/testing-development.md
guides/monitoring-production.md
```

```{toctree}
:maxdepth: 2
:caption: 📖 Examples & Patterns

examples/index.md
examples/basic/index.md
examples/fastapi/index.md
examples/production/index.md
examples/advanced/index.md
examples/sinks/index.md
```

```{toctree}
:maxdepth: 2
:caption: 🚀 Advanced Development

advanced-development.md
sink-development.md
sink-best-practices.md
sink-performance.md
sink-troubleshooting.md
```

```{toctree}
:maxdepth: 2
:caption: 🆘 Help & Community

troubleshooting.md
faq.md
contributing.md
style-guide.md
```

---

## Documentation Sections

### 📚 Getting Started

_Perfect for developers new to Fapilog_

- **[Introduction](introduction.md)** - Overview, benefits, and why choose Fapilog
- **[Primer](primer.md)** - What is Fapilog and core concepts
- **[Quickstart](quickstart.md)** - Get up and running in 5 minutes
- **[Core Concepts](core-concepts.md)** - Understand the architecture and fundamentals

### 🔧 Core Usage

_Essential guides for day-to-day development_

- **[User Guide](user-guide.md)** - Step-by-step tutorials and common patterns
- **[Configuration](config.md)** - Environment setup and advanced settings
- **[API Reference](api-reference.md)** - Complete technical reference

### 📘 Feature Guides

_Comprehensive guides for specific features and capabilities_

- **[FastAPI Integration Guide](guides/fastapi-integration.md)** - Complete guide to middleware, context management, and FastAPI patterns
- **[Configuration Guide](guides/configuration.md)** - Complete guide to environment variables, programmatic settings, and production configuration
- **[Security & Redaction Guide](guides/security.md)** - Complete guide to data protection, PII redaction, and compliance frameworks
- **[Sinks Guide](guides/sinks.md)** - Complete guide to output destinations, custom sinks, and sink registry
- **[Testing & Development Guide](guides/testing-development.md)** - Complete guide to testing custom components, debugging, and development workflows
- **[Monitoring & Production Guide](guides/monitoring-production.md)** - Complete guide to metrics, deployment patterns, performance optimization, and high availability

### 📖 Examples & Patterns

_Real-world usage patterns and recipes_

- **[Examples Overview](examples/index.md)** - Choose your learning path
- **[Basic Usage](examples/basic/index.md)** - Perfect for beginners
- **[FastAPI Integration](examples/fastapi/index.md)** - Web application patterns
- **[Production Deployment](examples/production/index.md)** - High-performance configurations
- **[Advanced Patterns](examples/advanced/index.md)** - Security, tracing, enrichment
- **[Sink Development](examples/sinks/index.md)** - Custom output destinations

### 🚀 Advanced Development

_For developers building custom components and optimizing performance_

- **[Advanced Development Overview](advanced-development.md)** - Your gateway to advanced Fapilog development
- **[Sink Development](sink-development.md)** - Build custom sinks for any destination
- **[Sink Best Practices](sink-best-practices.md)** - Production-ready patterns and error handling
- **[Sink Performance](sink-performance.md)** - Optimization techniques for high-throughput
- **[Sink Troubleshooting](sink-troubleshooting.md)** - Debug and resolve common issues

### 🆘 Help & Community

_When you need assistance or want to contribute_

- **[Troubleshooting](troubleshooting.md)** - Common issues and solutions
- **[FAQ](faq.md)** - Frequently asked questions
- **[Contributing](contributing.md)** - How to contribute to the project
- **[Style Guide](style-guide.md)** - Documentation standards

---

## Quick Navigation by Use Case

### 🆕 **New to Fapilog?**

Start with: [Introduction](introduction.md) → [Primer](primer.md) → [Quickstart](quickstart.md) → [Basic Examples](examples/basic/index.md)

### 🔨 **Building an Application?**

Focus on: [User Guide](user-guide.md) → [Configuration](config.md) → [FastAPI Examples](examples/fastapi/index.md)

### 🏗️ **Need Custom Sinks?**

Jump to: [Advanced Development](advanced-development.md) → [Sink Development](sink-development.md) → [Sink Examples](examples/sinks/index.md)

### 🚀 **Deploying to Production?**

Review: [Configuration](config.md) → [Production Examples](examples/production/index.md) → [Troubleshooting](troubleshooting.md)

### 🤝 **Want to Contribute?**

See: [Contributing](contributing.md) → [Style Guide](style-guide.md)

---

## Developer Learning Path

This documentation follows a progressive learning path designed for developers:

```
📚 Getting Started
  ↓
🔧 Master Core Usage
  ↓
📖 Explore Examples & Patterns
  ↓
🚀 Advanced Development (Custom Sinks, Performance)
  ↓
🆘 Production Support & Community
```

Each section builds on the previous one, but you can jump to any section based on your immediate needs.

---

## Related Resources

- **Current Version**: {{ version }}
- **GitHub Repository**: [chris-haste/fastapi-logger](https://github.com/chris-haste/fastapi-logger)
- **PyPI Package**: [fapilog](https://pypi.org/project/fapilog/)
- **Changelog**: [Release History](https://github.com/chris-haste/fastapi-logger/blob/main/CHANGELOG.md)
- **Issues & Discussions**: [GitHub Issues](https://github.com/chris-haste/fastapi-logger/issues)

---

## Documentation Standards

All documentation follows these principles:

- **Developer-centric** - Written for developers, by developers
- **Progressive disclosure** - From basic to advanced concepts
- **Copy-paste ready** - All examples are tested and working
- **Cross-referenced** - Clear navigation between related topics
- **Maintainable** - Single source of truth for each topic
