# Monitoring & Production Guide

**Enterprise-grade monitoring, metrics, and production deployment patterns for fapilog.**

Production environments demand robust monitoring, high availability, and performance optimization. This guide covers fapilog's comprehensive monitoring system, production deployment patterns, performance tuning, and fault tolerance mechanisms for enterprise-scale applications.

**For specialized topics, see:**

- **[Configuration Guide](configuration.md)** - Environment setup and settings tuning
- **[Testing & Development Guide](testing-development.md)** - Performance testing and debugging
- **[Security & Redaction Guide](security.md)** - Production security and compliance

---

## Quick Navigation

**Jump to what you need:**

- **🔍 [Metrics System](#metrics-system)** - Comprehensive monitoring and metrics collection
- **📊 [Prometheus Integration](#prometheus-integration)** - Export metrics for monitoring stacks
- **🚀 [Production Deployment](#production-deployment)** - Container and Kubernetes patterns
- **⚡ [Performance Optimization](#performance-optimization)** - High-throughput tuning
- **🛡️ [High Availability](#high-availability)** - Fault tolerance and resilience
- **🔧 [Health Checks](#health-checks)** - Monitoring and alerting patterns
- **📈 [Scaling Patterns](#scaling-patterns)** - Multi-instance and load balancing
- **🐛 [Production Troubleshooting](#production-troubleshooting)** - Debugging and diagnostics

## Table of Contents

**Monitoring & Metrics**

1. [Metrics System](#metrics-system) - Comprehensive metrics collection
2. [Prometheus Integration](#prometheus-integration) - Export and monitoring
3. [Resource Monitoring](#resource-monitoring) - System resource tracking
4. [Custom Metrics](#custom-metrics) - Application-specific monitoring

**Production Deployment**

5. [Container Deployment](#container-deployment) - Docker and containerization
6. [Kubernetes Integration](#kubernetes-integration) - Cloud-native deployment
7. [Environment Configuration](#environment-configuration) - Production settings
8. [Multi-Service Patterns](#multi-service-patterns) - Microservices logging

**Performance & Scaling**

9. [Performance Optimization](#performance-optimization) - High-throughput tuning
10. [Queue Optimization](#queue-optimization) - Async logging performance
11. [Scaling Patterns](#scaling-patterns) - Horizontal scaling
12. [Load Balancing](#load-balancing) - Traffic distribution

**Reliability & Monitoring**

13. [High Availability](#high-availability) - Fault tolerance patterns
14. [Health Checks](#health-checks) - Service monitoring
15. [Alerting Patterns](#alerting-patterns) - Production alerts
16. [Production Troubleshooting](#production-troubleshooting) - Issue resolution

---

## Metrics System

Fapilog provides comprehensive metrics collection for monitoring logging system performance, queue health, and sink reliability in production environments.

### Core Metrics Overview

**Queue Metrics:**
- Queue size and peak usage
- Throughput (events/second)
- Latency (enqueue/dequeue times)
- Dropped and sampled events
- Memory usage

**Sink Metrics:**
- Success/failure rates per sink
- Write latency and batch sizes
- Retry counts and error rates
- Connection status

**Performance Metrics:**
- Total events processed
- CPU and memory usage
- Processing time per event
- Resource utilization

### Enabling Metrics Collection

**Basic metrics configuration:**

```python
from fapilog.settings import LoggingSettings

settings = LoggingSettings(
    # Enable metrics collection
    metrics_enabled=True,
    
    # Configure sampling window
    metrics_sample_window=1000,  # Keep 1000 recent samples
    
    # Enable resource monitoring
    enable_resource_metrics=True,
    
    # Performance logging
    level="INFO",
    queue_enabled=True
)

configure_logging(settings=settings)
```

**Environment variables:**

```bash
# Enable metrics
export FAPILOG_METRICS_ENABLED=true
export FAPILOG_METRICS_SAMPLE_WINDOW=1000
export FAPILOG_ENABLE_RESOURCE_METRICS=true

# Optional: Prometheus integration
export FAPILOG_METRICS_PROMETHEUS_ENABLED=true
export FAPILOG_METRICS_PROMETHEUS_PORT=8000
```

### Accessing Metrics Programmatically

**Get current metrics:**

```python
from fapilog.monitoring import get_metrics_dict

# Get structured metrics
metrics = get_metrics_dict()

print(f"Queue size: {metrics['queue']['size']}")
print(f"Events/sec: {metrics['performance']['events_per_second']}")
print(f"Memory usage: {metrics['performance']['memory_bytes']}")

# Check sink health
for sink_name, sink_metrics in metrics['sinks'].items():
    print(f"{sink_name}: {sink_metrics['success_rate']:.2%} success rate")
```

**Monitor queue performance:**

```python
from fapilog._internal.metrics import get_metrics_collector

metrics_collector = get_metrics_collector()

if metrics_collector and metrics_collector.is_enabled():
    queue_metrics = metrics_collector.get_queue_metrics()
    
    print(f"Queue size: {queue_metrics.size}")
    print(f"Peak size: {queue_metrics.peak_size}")
    print(f"Total enqueued: {queue_metrics.total_enqueued}")
    print(f"Enqueue latency: {queue_metrics.enqueue_latency_ms:.3f}ms")
    print(f"Memory usage: {queue_metrics.memory_usage_bytes} bytes")
```

### Metrics-Driven Configuration

**Tune configuration based on metrics:**

```python
import time
from fapilog import configure_logging, log
from fapilog.monitoring import get_metrics_dict

# Start with baseline configuration
settings = LoggingSettings(
    queue_enabled=True,
    queue_maxsize=1000,
    queue_batch_size=50,
    metrics_enabled=True
)

configure_logging(settings=settings)

# Generate load and monitor
for i in range(1000):
    log.info("Performance test", iteration=i)
    
    if i % 100 == 0:
        metrics = get_metrics_dict()
        queue_size = metrics['queue']['size']
        
        # Auto-tune based on queue pressure
        if queue_size > 800:  # Queue getting full
            print(f"High queue pressure: {queue_size}")
            # Consider: larger queue, more workers, faster batching
        elif queue_size < 100:  # Queue mostly empty
            print(f"Low queue pressure: {queue_size}")
            # Consider: smaller batches, resource optimization
```

[↑ Back to top](#monitoring--production-guide)

---

## Prometheus Integration

Export fapilog metrics to Prometheus for integration with monitoring stacks like Grafana, AlertManager, and observability platforms.

### Prometheus Exporter Setup

**Enable Prometheus endpoint:**

```python
from fapilog.settings import LoggingSettings

settings = LoggingSettings(
    # Enable metrics
    metrics_enabled=True,
    
    # Enable Prometheus HTTP endpoint
    metrics_prometheus_enabled=True,
    metrics_prometheus_port=8000,
    metrics_prometheus_host="0.0.0.0",
    
    # Application logging
    level="INFO",
    queue_enabled=True
)

configure_logging(settings=settings)

# Metrics available at http://localhost:8000/metrics
```

**Start Prometheus server programmatically:**

```python
from fapilog.monitoring import start_metrics_server

# Start metrics server
exporter = await start_metrics_server(
    host="0.0.0.0",
    port=8000,
    path="/metrics"
)

if exporter:
    print("Prometheus metrics available at http://localhost:8000/metrics")
else:
    print("Failed to start metrics server")
```

### Available Prometheus Metrics

**Queue Metrics:**

```
# Queue size and capacity
fapilog_queue_size
fapilog_queue_peak_size
fapilog_queue_maxsize

# Throughput metrics
fapilog_queue_enqueued_total
fapilog_queue_dequeued_total
fapilog_queue_dropped_total

# Performance metrics
fapilog_queue_enqueue_latency_ms
fapilog_queue_dequeue_latency_ms
fapilog_queue_memory_bytes
```

**Sink Metrics (labeled by sink type):**

```
# Per-sink success/failure rates
fapilog_sink_writes_total{sink="stdout"}
fapilog_sink_successes_total{sink="stdout"}
fapilog_sink_failures_total{sink="file"}
fapilog_sink_success_rate{sink="loki"}

# Per-sink performance
fapilog_sink_latency_ms{sink="stdout"}
fapilog_sink_batch_size{sink="loki"}
fapilog_sink_retry_count{sink="loki"}
```

**System Metrics:**

```
# Overall performance
fapilog_events_total
fapilog_events_per_second
fapilog_memory_bytes
fapilog_cpu_percent

# Processing metrics
fapilog_processing_time_ms
fapilog_enricher_time_ms
fapilog_redaction_time_ms
```

### Prometheus Configuration

**prometheus.yml configuration:**

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'fapilog'
    static_configs:
      - targets: ['app:8000']  # fapilog metrics endpoint
    metrics_path: '/metrics'
    scrape_interval: 10s
    
  - job_name: 'fapilog-cluster'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
```

### Grafana Dashboard

**Sample Grafana queries:**

```promql
# Queue utilization
(fapilog_queue_size / fapilog_queue_maxsize) * 100

# Events per second by instance
rate(fapilog_events_total[5m])

# Sink error rate
rate(fapilog_sink_failures_total[5m]) / rate(fapilog_sink_writes_total[5m])

# Memory usage trend
fapilog_memory_bytes

# Queue latency percentiles
histogram_quantile(0.95, rate(fapilog_queue_enqueue_latency_ms_bucket[5m]))
```

**Alert rules:**

```yaml
groups:
  - name: fapilog.rules
    rules:
      - alert: FapilogQueueFull
        expr: (fapilog_queue_size / fapilog_queue_maxsize) > 0.9
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Fapilog queue near capacity"
          
      - alert: FapilogHighErrorRate
        expr: rate(fapilog_sink_failures_total[5m]) / rate(fapilog_sink_writes_total[5m]) > 0.1
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "High error rate in fapilog sinks"
```

[↑ Back to top](#monitoring--production-guide)

---

## Production Deployment

Deploy fapilog in production environments with container orchestration, environment management, and scalability patterns.

### Container Deployment

**Production Dockerfile:**

```dockerfile
FROM python:3.11-slim

# Create app user for security
RUN groupadd -r app && useradd -r -g app app

# Create directories
RUN mkdir -p /app /var/log/app && \
    chown -R app:app /app /var/log/app

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY --chown=app:app . .

# Set up logging environment
ENV FAPILOG_LEVEL=INFO \
    FAPILOG_FORMAT=json \
    FAPILOG_SINKS=stdout,file \
    FAPILOG_FILE_PATH=/var/log/app/app.log \
    FAPILOG_QUEUE_ENABLED=true \
    FAPILOG_QUEUE_MAXSIZE=5000 \
    FAPILOG_METRICS_ENABLED=true \
    FAPILOG_METRICS_PROMETHEUS_ENABLED=true \
    FAPILOG_METRICS_PROMETHEUS_PORT=8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/metrics || exit 1

# Switch to non-root user
USER app

# Expose ports
EXPOSE 8000 8080

# Start application
CMD ["python", "main.py"]
```

**docker-compose.yml for production:**

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8080:8080"  # Application port
      - "8000:8000"  # Metrics port
    volumes:
      - app-logs:/var/log/app
      - /etc/localtime:/etc/localtime:ro
    environment:
      # Production logging configuration
      FAPILOG_LEVEL: INFO
      FAPILOG_FORMAT: json
      FAPILOG_SINKS: stdout,file,loki
      FAPILOG_FILE_PATH: /var/log/app/app.log
      
      # High-performance queue
      FAPILOG_QUEUE_ENABLED: "true"
      FAPILOG_QUEUE_MAXSIZE: 10000
      FAPILOG_QUEUE_BATCH_SIZE: 100
      FAPILOG_QUEUE_BATCH_TIMEOUT: 0.5
      FAPILOG_QUEUE_OVERFLOW: drop
      
      # Monitoring
      FAPILOG_METRICS_ENABLED: "true"
      FAPILOG_METRICS_PROMETHEUS_ENABLED: "true"
      FAPILOG_ENABLE_RESOURCE_METRICS: "true"
      
      # Security
      FAPILOG_ENABLE_AUTO_REDACT_PII: "true"
      FAPILOG_REDACT_PATTERNS: "password,token,secret,api_key"
      
      # Loki integration
      FAPILOG_LOKI_URL: "http://loki:3100"
      FAPILOG_LOKI_BATCH_SIZE: 200
      
    depends_on:
      - loki
      - prometheus
    restart: unless-stopped
    
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
    restart: unless-stopped
    
  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"
    volumes:
      - loki-data:/loki
    restart: unless-stopped
    
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
    restart: unless-stopped

volumes:
  app-logs:
  prometheus-data:
  loki-data:
  grafana-data:
```

### Kubernetes Integration

**Kubernetes deployment with monitoring:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fapilog-app
  labels:
    app: fapilog-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: fapilog-app
  template:
    metadata:
      labels:
        app: fapilog-app
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      containers:
      - name: app
        image: myapp:latest
        ports:
        - containerPort: 8080
          name: http
        - containerPort: 8000
          name: metrics
        env:
        # Production logging configuration
        - name: FAPILOG_LEVEL
          value: "INFO"
        - name: FAPILOG_FORMAT
          value: "json"
        - name: FAPILOG_SINKS
          value: "stdout,loki"
          
        # High-performance configuration
        - name: FAPILOG_QUEUE_ENABLED
          value: "true"
        - name: FAPILOG_QUEUE_MAXSIZE
          value: "10000"
        - name: FAPILOG_QUEUE_BATCH_SIZE
          value: "100"
        - name: FAPILOG_QUEUE_OVERFLOW
          value: "drop"
          
        # Monitoring
        - name: FAPILOG_METRICS_ENABLED
          value: "true"
        - name: FAPILOG_METRICS_PROMETHEUS_ENABLED
          value: "true"
        - name: FAPILOG_ENABLE_RESOURCE_METRICS
          value: "true"
          
        # Kubernetes-specific enrichment
        - name: POD_NAME
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: NODE_NAME
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
        - name: NAMESPACE
          valueFrom:
            fieldRef:
              fieldPath: metadata.namespace
              
        # Loki integration
        - name: FAPILOG_LOKI_URL
          value: "http://loki:3100"
        - name: FAPILOG_LOKI_BATCH_SIZE
          value: "200"
          
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
            
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
          
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
          
---
apiVersion: v1
kind: Service
metadata:
  name: fapilog-app-service
  labels:
    app: fapilog-app
spec:
  selector:
    app: fapilog-app
  ports:
  - name: http
    port: 80
    targetPort: 8080
  - name: metrics
    port: 8000
    targetPort: 8000
    
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: fapilog-app-monitor
spec:
  selector:
    matchLabels:
      app: fapilog-app
  endpoints:
  - port: metrics
    path: /metrics
    interval: 15s
```

### Environment-Specific Configurations

**Development environment:**

```python
def development_config() -> LoggingSettings:
    """Development configuration - detailed logging and debugging."""
    return LoggingSettings(
        # Verbose logging for development
        level="DEBUG",
        format="pretty",  # Human-readable format
        
        # Simple output
        sinks=["stdout"],
        
        # Small queue for quick feedback
        queue_enabled=True,
        queue_maxsize=100,
        queue_batch_size=1,  # Immediate processing
        
        # Monitoring for development
        enable_resource_metrics=True,
        metrics_enabled=True,
        
        # Relaxed security for debugging
        redact_level="WARNING",  # Allow debug data
        enable_auto_redact_pii=False
    )
```

**Staging environment:**

```python
def staging_config() -> LoggingSettings:
    """Staging configuration - production-like with additional debugging."""
    return LoggingSettings(
        # Production-like logging
        level="INFO",
        format="json",
        
        # Multiple outputs
        sinks=["stdout", "file:///var/log/staging.log", "loki://loki-staging:3100"],
        
        # Medium-performance queue
        queue_enabled=True,
        queue_maxsize=5000,
        queue_batch_size=50,
        queue_batch_timeout=1.0,
        queue_overflow="drop",
        
        # Full monitoring
        enable_resource_metrics=True,
        metrics_enabled=True,
        metrics_prometheus_enabled=True,
        
        # Production-like security
        redact_patterns=["password", "token", "secret"],
        enable_auto_redact_pii=True,
        
        # Sampling for high-volume testing
        sampling_rate=0.5  # 50% sampling
    )
```

**Production environment:**

```python
def production_config() -> LoggingSettings:
    """Production configuration - optimized for performance and security."""
    return LoggingSettings(
        # Optimized logging level
        level="INFO",
        format="json",
        
        # Multiple reliable outputs
        sinks=[
            "stdout",
            "file:///var/log/app.log",
            "loki://loki:3100?batch_size=200&timeout=30"
        ],
        
        # High-performance queue
        queue_enabled=True,
        queue_maxsize=10000,
        queue_batch_size=100,
        queue_batch_timeout=0.5,
        queue_overflow="drop",
        
        # Full monitoring
        enable_resource_metrics=True,
        metrics_enabled=True,
        metrics_prometheus_enabled=True,
        metrics_sample_window=1000,
        
        # Production security
        redact_patterns=["password", "token", "secret", "api_key", "session"],
        redact_fields=["authorization", "x-api-key", "cookie"],
        enable_auto_redact_pii=True,
        custom_pii_patterns=["ssn", "credit_card", "phone"],
        
        # Performance optimization
        sampling_rate=0.1  # 10% sampling for high volume
    )
```

[↑ Back to top](#monitoring--production-guide)

---

## High Availability

Implement fault tolerance, graceful degradation, and resilience patterns for production-grade logging reliability.

### Fault Tolerance Patterns

**Graceful sink degradation:**

```python
from fapilog.sinks import Sink
from fapilog.exceptions import SinkError
import asyncio
import logging

class ResilientMultiSink(Sink):
    """Multi-sink with graceful degradation."""
    
    def __init__(self, primary_sinks, fallback_sinks):
        self.primary_sinks = primary_sinks
        self.fallback_sinks = fallback_sinks
        self.degraded_mode = False
        self.failure_count = 0
        self.max_failures = 5
    
    async def write(self, event):
        """Write with automatic fallback."""
        
        # Try primary sinks first
        if not self.degraded_mode:
            try:
                await self._write_to_sinks(self.primary_sinks, event)
                self.failure_count = 0  # Reset on success
                return
            except Exception as e:
                self.failure_count += 1
                logging.warning(f"Primary sinks failed: {e}")
                
                # Enter degraded mode if too many failures
                if self.failure_count >= self.max_failures:
                    self.degraded_mode = True
                    logging.error("Entering degraded mode - using fallback sinks")
        
        # Use fallback sinks
        try:
            await self._write_to_sinks(self.fallback_sinks, event)
            
            # Try to recover if in degraded mode
            if self.degraded_mode:
                await self._attempt_recovery()
                
        except Exception as e:
            logging.critical(f"All sinks failed: {e}")
            # Last resort: write to stderr
            import sys
            import json
            sys.stderr.write(f"EMERGENCY LOG: {json.dumps(event)}\n")
    
    async def _write_to_sinks(self, sinks, event):
        """Write to a list of sinks with parallel execution."""
        tasks = [sink.write(event) for sink in sinks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check if any sink succeeded
        exceptions = [r for r in results if isinstance(r, Exception)]
        if len(exceptions) == len(results):
            # All sinks failed
            raise SinkError("All sinks in group failed", 
                           operation="write_group", 
                           error_count=len(exceptions))
    
    async def _attempt_recovery(self):
        """Attempt to recover primary sinks."""
        try:
            # Test primary sinks with a health check event
            test_event = {"event": "health_check", "timestamp": "test"}
            await self._write_to_sinks(self.primary_sinks, test_event)
            
            # If successful, exit degraded mode
            self.degraded_mode = False
            self.failure_count = 0
            logging.info("Recovered from degraded mode - primary sinks restored")
            
        except Exception:
            # Recovery failed, stay in degraded mode
            pass
```

**Circuit breaker pattern:**

```python
import time
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreakerSink(Sink):
    """Sink with circuit breaker pattern."""
    
    def __init__(self, underlying_sink, failure_threshold=5, recovery_timeout=60):
        self.underlying_sink = underlying_sink
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.success_count = 0
    
    async def write(self, event):
        """Write with circuit breaker protection."""
        
        if self.state == CircuitState.OPEN:
            # Check if we should try recovery
            if (time.time() - self.last_failure_time) > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                logging.info("Circuit breaker entering half-open state")
            else:
                # Circuit is open, fail fast
                raise SinkError("Circuit breaker is open", 
                               sink_type=type(self.underlying_sink).__name__,
                               operation="write")
        
        try:
            await self.underlying_sink.write(event)
            await self._on_success()
            
        except Exception as e:
            await self._on_failure(e)
            raise
    
    async def _on_success(self):
        """Handle successful write."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= 3:  # Require multiple successes
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logging.info("Circuit breaker closed - sink recovered")
        else:
            self.failure_count = 0  # Reset failure count on success
    
    async def _on_failure(self, exception):
        """Handle failed write."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logging.error(f"Circuit breaker opened due to {self.failure_count} failures")
```

### Retry Mechanisms

**Exponential backoff with jitter:**

```python
import random
import asyncio
from fapilog._internal.error_handling import retry_with_backoff_async

class RetryableSink(Sink):
    """Sink with advanced retry logic."""
    
    def __init__(self, underlying_sink, max_retries=3, base_delay=1.0):
        self.underlying_sink = underlying_sink
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    async def write(self, event):
        """Write with exponential backoff retry."""
        
        async def write_operation():
            return await self.underlying_sink.write(event)
        
        return await retry_with_backoff_async(
            write_operation,
            max_retries=self.max_retries,
            base_delay=self.base_delay,
            max_delay=60.0,
            exponential_base=2.0,
            jitter=True
        )

# Example usage with automatic retry
from fapilog.sinks import LokiSink

# Create sink with retry capability
loki_sink = LokiSink("http://loki:3100")
retryable_loki = RetryableSink(loki_sink, max_retries=5, base_delay=1.0)

# Configure with retry sink
settings = LoggingSettings(
    sinks=[retryable_loki],  # Will automatically retry on failures
    queue_enabled=True
)
```

### Connection Pooling

**Pooled HTTP sink for high availability:**

```python
import aiohttp
import asyncio
from typing import Optional

class PooledHttpSink(Sink):
    """HTTP sink with connection pooling for reliability."""
    
    def __init__(self, url: str, pool_size: int = 10):
        self.url = url
        self.pool_size = pool_size
        self.session: Optional[aiohttp.ClientSession] = None
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize connection pool."""
        if self.session is None:
            async with self._lock:
                if self.session is None:
                    connector = aiohttp.TCPConnector(
                        limit=self.pool_size,
                        limit_per_host=self.pool_size,
                        keepalive_timeout=60,
                        enable_cleanup_closed=True
                    )
                    
                    timeout = aiohttp.ClientTimeout(
                        total=30,
                        connect=10,
                        sock_read=10
                    )
                    
                    self.session = aiohttp.ClientSession(
                        connector=connector,
                        timeout=timeout
                    )
    
    async def write(self, event):
        """Write using pooled connections."""
        await self.initialize()
        
        try:
            async with self.session.post(
                self.url,
                json=event,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status >= 400:
                    raise SinkError(
                        f"HTTP {response.status}: {await response.text()}",
                        sink_type="pooled_http",
                        operation="write",
                        status_code=response.status
                    )
                
        except aiohttp.ClientError as e:
            raise SinkError(f"Connection error: {e}", 
                           sink_type="pooled_http", 
                           operation="write")
    
    async def close(self):
        """Clean up connection pool."""
        if self.session:
            await self.session.close()
```

### Health Monitoring

**Sink health monitoring:**

```python
import time
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class SinkHealth:
    """Health status for a sink."""
    name: str
    healthy: bool
    last_success: Optional[float]
    last_failure: Optional[float]
    success_count: int
    failure_count: int
    success_rate: float

class HealthMonitoringSink(Sink):
    """Sink wrapper that tracks health metrics."""
    
    def __init__(self, underlying_sink, name: str):
        self.underlying_sink = underlying_sink
        self.name = name
        self.success_count = 0
        self.failure_count = 0
        self.last_success = None
        self.last_failure = None
    
    async def write(self, event):
        """Write with health tracking."""
        try:
            await self.underlying_sink.write(event)
            self.success_count += 1
            self.last_success = time.time()
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure = time.time()
            raise
    
    def get_health(self) -> SinkHealth:
        """Get current health status."""
        total_operations = self.success_count + self.failure_count
        success_rate = (self.success_count / total_operations) if total_operations > 0 else 1.0
        
        # Consider healthy if success rate > 95% and recent success
        recent_success = (
            self.last_success is not None and 
            time.time() - self.last_success < 300  # 5 minutes
        )
        
        healthy = success_rate > 0.95 and recent_success
        
        return SinkHealth(
            name=self.name,
            healthy=healthy,
            last_success=self.last_success,
            last_failure=self.last_failure,
            success_count=self.success_count,
            failure_count=self.failure_count,
            success_rate=success_rate
        )

# Health monitoring across all sinks
class HealthMonitor:
    """Monitor health of all sinks."""
    
    def __init__(self):
        self.monitored_sinks: Dict[str, HealthMonitoringSink] = {}
    
    def register_sink(self, sink: Sink, name: str) -> HealthMonitoringSink:
        """Register a sink for monitoring."""
        monitored = HealthMonitoringSink(sink, name)
        self.monitored_sinks[name] = monitored
        return monitored
    
    def get_overall_health(self) -> Dict[str, SinkHealth]:
        """Get health status of all sinks."""
        return {
            name: sink.get_health() 
            for name, sink in self.monitored_sinks.items()
        }
    
    def is_system_healthy(self) -> bool:
        """Check if the overall logging system is healthy."""
        health_status = self.get_overall_health()
        
        if not health_status:
            return False
        
        healthy_sinks = sum(1 for h in health_status.values() if h.healthy)
        total_sinks = len(health_status)
        
        # System is healthy if at least 50% of sinks are healthy
        return (healthy_sinks / total_sinks) >= 0.5
```

[↑ Back to top](#monitoring--production-guide)

---

## Health Checks

Implement comprehensive health monitoring for production logging systems with HTTP endpoints, metrics integration, and alerting patterns.

### HTTP Health Endpoints

**FastAPI health check integration:**

```python
from fastapi import FastAPI, HTTPException
from fapilog import configure_logging, log
from fapilog.monitoring import get_metrics_dict
from fapilog._internal.metrics import get_metrics_collector

app = FastAPI()
configure_logging(app=app)

@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    try:
        # Test logging system
        log.info("Health check performed", check_type="basic")
        
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "service": "fapilog-app",
            "version": "1.0.0"
        }
    except Exception as e:
        log.error("Health check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service unhealthy")

@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with metrics."""
    try:
        # Get metrics
        metrics = get_metrics_dict()
        metrics_collector = get_metrics_collector()
        
        # Check queue health
        queue_health = "healthy"
        if metrics.get('queue'):
            queue_size = metrics['queue']['size']
            queue_maxsize = metrics['queue'].get('maxsize', 1000)
            utilization = queue_size / queue_maxsize
            
            if utilization > 0.9:
                queue_health = "critical"
            elif utilization > 0.7:
                queue_health = "warning"
        
        # Check sink health
        sink_health = {}
        if metrics.get('sinks'):
            for sink_name, sink_metrics in metrics['sinks'].items():
                success_rate = sink_metrics.get('success_rate', 1.0)
                if success_rate > 0.95:
                    sink_health[sink_name] = "healthy"
                elif success_rate > 0.8:
                    sink_health[sink_name] = "warning"
                else:
                    sink_health[sink_name] = "critical"
        
        # Overall status
        overall_status = "healthy"
        if queue_health == "critical" or any(s == "critical" for s in sink_health.values()):
            overall_status = "critical"
        elif queue_health == "warning" or any(s == "warning" for s in sink_health.values()):
            overall_status = "warning"
        
        health_response = {
            "status": overall_status,
            "timestamp": time.time(),
            "components": {
                "queue": {
                    "status": queue_health,
                    "size": metrics.get('queue', {}).get('size', 0),
                    "utilization": f"{utilization:.1%}" if 'queue' in metrics else "N/A"
                },
                "sinks": sink_health,
                "metrics": {
                    "status": "healthy" if metrics_collector and metrics_collector.is_enabled() else "disabled",
                    "events_per_second": metrics.get('performance', {}).get('events_per_second', 0)
                }
            },
            "metrics": metrics
        }
        
        if overall_status == "critical":
            raise HTTPException(status_code=503, detail=health_response)
        
        return health_response
        
    except HTTPException:
        raise
    except Exception as e:
        log.error("Detailed health check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Health check failed")

@app.get("/ready")
async def readiness_check():
    """Kubernetes readiness probe."""
    try:
        # Test that we can write a log
        log.debug("Readiness check", check_type="readiness")
        
        # Check if metrics are available (optional)
        metrics = get_metrics_dict()
        
        return {
            "status": "ready",
            "timestamp": time.time()
        }
    except Exception as e:
        log.error("Readiness check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service not ready")

@app.get("/metrics/health")
async def metrics_health():
    """Health check specifically for metrics system."""
    try:
        metrics_collector = get_metrics_collector()
        
        if not metrics_collector or not metrics_collector.is_enabled():
            return {
                "status": "disabled",
                "message": "Metrics collection is disabled"
            }
        
        metrics = get_metrics_dict()
        
        return {
            "status": "healthy",
            "metrics_enabled": True,
            "sample_window": metrics_collector.sample_window,
            "queue_metrics": bool(metrics.get('queue')),
            "sink_metrics": bool(metrics.get('sinks')),
            "performance_metrics": bool(metrics.get('performance'))
        }
        
    except Exception as e:
        log.error("Metrics health check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Metrics system unhealthy")
```

### Kubernetes Health Probes

**Kubernetes deployment with health checks:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fapilog-app
spec:
  template:
    spec:
      containers:
      - name: app
        image: myapp:latest
        ports:
        - containerPort: 8080
        - containerPort: 8000
        
        # Liveness probe - restart if failing
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
          
        # Readiness probe - remove from service if failing
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 2
          
        # Startup probe - wait for app to start
        startupProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 10
```

### Monitoring Integration

**Custom metrics for monitoring systems:**

```python
import time
from prometheus_client import Counter, Histogram, Gauge

# Custom application metrics
health_check_counter = Counter('app_health_checks_total', 'Total health checks', ['status'])
health_check_duration = Histogram('app_health_check_duration_seconds', 'Health check duration')
system_health_gauge = Gauge('app_system_health', 'System health status (1=healthy, 0=unhealthy)')

async def monitored_health_check():
    """Health check with custom metrics."""
    start_time = time.time()
    
    try:
        # Perform health checks
        metrics = get_metrics_dict()
        
        # Check queue health
        queue_healthy = True
        if metrics.get('queue'):
            utilization = metrics['queue']['size'] / metrics['queue'].get('maxsize', 1000)
            queue_healthy = utilization < 0.9
        
        # Check sink health
        sinks_healthy = True
        if metrics.get('sinks'):
            for sink_metrics in metrics['sinks'].values():
                if sink_metrics.get('success_rate', 1.0) < 0.95:
                    sinks_healthy = False
                    break
        
        # Overall health
        overall_healthy = queue_healthy and sinks_healthy
        
        # Update metrics
        status = "healthy" if overall_healthy else "unhealthy"
        health_check_counter.labels(status=status).inc()
        system_health_gauge.set(1 if overall_healthy else 0)
        
        duration = time.time() - start_time
        health_check_duration.observe(duration)
        
        return {
            "status": status,
            "queue_healthy": queue_healthy,
            "sinks_healthy": sinks_healthy,
            "duration": duration
        }
        
    except Exception as e:
        health_check_counter.labels(status="error").inc()
        system_health_gauge.set(0)
        
        duration = time.time() - start_time
        health_check_duration.observe(duration)
        
        raise
```

### Alerting Patterns

**Prometheus alerting rules for fapilog:**

```yaml
groups:
  - name: fapilog-alerts
    rules:
      # Critical alerts
      - alert: FapilogDown
        expr: up{job="fapilog"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Fapilog service is down"
          description: "Fapilog service {{ $labels.instance }} has been down for more than 1 minute"
          
      - alert: FapilogQueueFull
        expr: (fapilog_queue_size / fapilog_queue_maxsize) > 0.95
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Fapilog queue near capacity"
          description: "Queue utilization is {{ $value | humanizePercentage }} on {{ $labels.instance }}"
          
      - alert: FapilogHighErrorRate
        expr: |
          (
            rate(fapilog_sink_failures_total[5m]) / 
            rate(fapilog_sink_writes_total[5m])
          ) > 0.1
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "High error rate in fapilog sinks"
          description: "Error rate is {{ $value | humanizePercentage }} on {{ $labels.instance }}"
          
      # Warning alerts
      - alert: FapilogQueueHigh
        expr: (fapilog_queue_size / fapilog_queue_maxsize) > 0.7
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Fapilog queue utilization high"
          description: "Queue utilization is {{ $value | humanizePercentage }} on {{ $labels.instance }}"
          
      - alert: FapilogSlowProcessing
        expr: fapilog_queue_enqueue_latency_ms > 100
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Fapilog slow queue processing"
          description: "Queue latency is {{ $value }}ms on {{ $labels.instance }}"
          
      - alert: FapilogMemoryHigh
        expr: fapilog_memory_bytes > 100 * 1024 * 1024  # 100MB
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Fapilog high memory usage"
          description: "Memory usage is {{ $value | humanizeBytes }} on {{ $labels.instance }}"
```

**Slack notification webhook:**

```python
import aiohttp
import json

async def send_slack_alert(webhook_url: str, alert_data: dict):
    """Send alert to Slack webhook."""
    
    # Format message
    severity_emoji = {
        "critical": "🚨",
        "warning": "⚠️",
        "info": "ℹ️"
    }
    
    severity = alert_data.get("severity", "info")
    emoji = severity_emoji.get(severity, "📝")
    
    message = {
        "text": f"{emoji} Fapilog Alert: {alert_data.get('summary', 'Unknown alert')}",
        "attachments": [
            {
                "color": "danger" if severity == "critical" else "warning",
                "fields": [
                    {
                        "title": "Severity",
                        "value": severity.title(),
                        "short": True
                    },
                    {
                        "title": "Instance",
                        "value": alert_data.get("instance", "unknown"),
                        "short": True
                    },
                    {
                        "title": "Description",
                        "value": alert_data.get("description", "No description available"),
                        "short": False
                    }
                ],
                "footer": "Fapilog Monitoring",
                "ts": int(time.time())
            }
        ]
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(webhook_url, json=message) as response:
            if response.status != 200:
                log.error("Failed to send Slack alert", 
                         status=response.status, 
                         response=await response.text())
```

[↑ Back to top](#monitoring--production-guide)

---

## Production Troubleshooting

Comprehensive debugging, diagnostics, and issue resolution patterns for production fapilog deployments.

### Common Production Issues

**Issue 1: High Queue Utilization**

```python
# Diagnostic script for queue issues
from fapilog.monitoring import get_metrics_dict
from fapilog._internal.metrics import get_metrics_collector

def diagnose_queue_issues():
    """Diagnose queue performance issues."""
    metrics = get_metrics_dict()
    
    if not metrics.get('queue'):
        print("❌ Queue metrics not available - check if metrics are enabled")
        return
    
    queue_metrics = metrics['queue']
    
    print("🔍 Queue Diagnostics")
    print(f"Current size: {queue_metrics['size']}")
    print(f"Peak size: {queue_metrics.get('peak_size', 'N/A')}")
    print(f"Max size: {queue_metrics.get('maxsize', 'N/A')}")
    
    if queue_metrics.get('maxsize'):
        utilization = queue_metrics['size'] / queue_metrics['maxsize']
        print(f"Utilization: {utilization:.1%}")
        
        if utilization > 0.9:
            print("🚨 CRITICAL: Queue near capacity")
            print("Recommendations:")
            print("  - Increase FAPILOG_QUEUE_MAXSIZE")
            print("  - Increase FAPILOG_QUEUE_BATCH_SIZE")
            print("  - Decrease FAPILOG_QUEUE_BATCH_TIMEOUT")
            print("  - Consider FAPILOG_QUEUE_OVERFLOW=drop")
        elif utilization > 0.7:
            print("⚠️  WARNING: Queue utilization high")
            print("Recommendations:")
            print("  - Monitor trends")
            print("  - Consider performance tuning")
    
    # Check processing performance
    enqueue_latency = queue_metrics.get('enqueue_latency_ms', 0)
    if enqueue_latency > 10:
        print(f"⚠️  High enqueue latency: {enqueue_latency:.3f}ms")
        print("Recommendations:")
        print("  - Check sink performance")
        print("  - Consider increasing batch timeout")
    
    # Check dropped events
    dropped = queue_metrics.get('dropped_total', 0)
    if dropped > 0:
        print(f"⚠️  Dropped events: {dropped}")
        print("Recommendations:")
        print("  - Increase queue size")
        print("  - Optimize sink performance")
        print("  - Consider sampling")

# Run diagnostics
diagnose_queue_issues()
```

**Issue 2: Sink Failures**

```python
def diagnose_sink_issues():
    """Diagnose sink connectivity and performance issues."""
    metrics = get_metrics_dict()
    
    if not metrics.get('sinks'):
        print("❌ Sink metrics not available")
        return
    
    print("🔍 Sink Diagnostics")
    
    for sink_name, sink_metrics in metrics['sinks'].items():
        print(f"\n📊 Sink: {sink_name}")
        
        success_rate = sink_metrics.get('success_rate', 1.0)
        writes_total = sink_metrics.get('writes_total', 0)
        failures_total = sink_metrics.get('failures_total', 0)
        latency = sink_metrics.get('latency_ms', 0)
        
        print(f"  Success rate: {success_rate:.1%}")
        print(f"  Total writes: {writes_total}")
        print(f"  Total failures: {failures_total}")
        print(f"  Average latency: {latency:.3f}ms")
        
        # Diagnose issues
        if success_rate < 0.95:
            print(f"  🚨 CRITICAL: Low success rate")
            if sink_name == "loki":
                print("  Loki troubleshooting:")
                print("    - Check Loki service availability")
                print("    - Verify FAPILOG_LOKI_URL is correct")
                print("    - Check network connectivity")
                print("    - Verify Loki batch size settings")
            elif sink_name == "file":
                print("  File troubleshooting:")
                print("    - Check file permissions")
                print("    - Verify disk space")
                print("    - Check FAPILOG_FILE_PATH directory exists")
            
        if latency > 1000:  # 1 second
            print(f"  ⚠️  High latency: {latency:.3f}ms")
            print("  Recommendations:")
            print("    - Check network connectivity")
            print("    - Increase timeout settings")
            print("    - Consider connection pooling")

diagnose_sink_issues()
```

### Performance Debugging

**Comprehensive performance analysis:**

```python
import time
import asyncio
from fapilog import configure_logging, log
from fapilog.monitoring import get_metrics_dict

async def performance_benchmark():
    """Benchmark logging performance."""
    
    print("🚀 Performance Benchmark Starting...")
    
    # Configure for testing
    from fapilog.settings import LoggingSettings
    settings = LoggingSettings(
        level="INFO",
        queue_enabled=True,
        queue_maxsize=10000,
        queue_batch_size=100,
        metrics_enabled=True,
        sinks=["stdout"]  # Fast sink for testing
    )
    
    configure_logging(settings=settings)
    
    # Warmup
    for i in range(100):
        log.info("Warmup", iteration=i)
    
    await asyncio.sleep(1)  # Let queue settle
    
    # Get baseline metrics
    baseline_metrics = get_metrics_dict()
    baseline_events = baseline_metrics.get('performance', {}).get('total_events', 0)
    
    # Performance test
    num_events = 10000
    start_time = time.perf_counter()
    
    for i in range(num_events):
        log.info("Performance test", 
                 iteration=i, 
                 batch=i // 100,
                 data=f"test_data_{i}")
    
    end_time = time.perf_counter()
    
    # Wait for processing
    await asyncio.sleep(2)
    
    # Get final metrics
    final_metrics = get_metrics_dict()
    final_events = final_metrics.get('performance', {}).get('total_events', 0)
    
    # Calculate results
    duration = end_time - start_time
    throughput = num_events / duration
    processed_events = final_events - baseline_events
    
    print(f"\n📊 Performance Results:")
    print(f"Events generated: {num_events}")
    print(f"Duration: {duration:.3f} seconds")
    print(f"Throughput: {throughput:.1f} events/second")
    print(f"Events processed: {processed_events}")
    
    # Queue analysis
    queue_metrics = final_metrics.get('queue', {})
    if queue_metrics:
        print(f"\n📋 Queue Analysis:")
        print(f"Final queue size: {queue_metrics.get('size', 'N/A')}")
        print(f"Peak queue size: {queue_metrics.get('peak_size', 'N/A')}")
        print(f"Enqueue latency: {queue_metrics.get('enqueue_latency_ms', 'N/A'):.3f}ms")
        print(f"Total enqueued: {queue_metrics.get('total_enqueued', 'N/A')}")
        print(f"Total dropped: {queue_metrics.get('total_dropped', 'N/A')}")
    
    # Performance recommendations
    print(f"\n💡 Recommendations:")
    if throughput < 1000:
        print("  ⚠️  Low throughput detected")
        print("    - Increase queue batch size")
        print("    - Reduce batch timeout")
        print("    - Check sink performance")
    elif throughput > 10000:
        print("  ✅ Excellent throughput")
    else:
        print("  ✅ Good throughput")
    
    if queue_metrics.get('total_dropped', 0) > 0:
        print("  ⚠️  Events were dropped")
        print("    - Increase queue size")
        print("    - Optimize sink performance")

# Run benchmark
asyncio.run(performance_benchmark())
```

### Memory and Resource Debugging

**Memory leak detection:**

```python
import psutil
import time
import gc
from fapilog import configure_logging, log

def memory_leak_test():
    """Test for memory leaks in logging system."""
    
    print("🔍 Memory Leak Detection")
    
    # Get initial memory
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    print(f"Initial memory: {initial_memory:.1f} MB")
    
    # Configure logging
    configure_logging()
    
    # Generate logs in batches
    batch_size = 1000
    num_batches = 10
    
    memory_readings = [initial_memory]
    
    for batch in range(num_batches):
        print(f"Batch {batch + 1}/{num_batches}")
        
        # Generate logs
        for i in range(batch_size):
            log.info("Memory test", 
                     batch=batch, 
                     iteration=i,
                     large_data="x" * 100)  # Some data to log
        
        # Force garbage collection
        gc.collect()
        
        # Measure memory
        current_memory = process.memory_info().rss / 1024 / 1024
        memory_readings.append(current_memory)
        
        print(f"  Memory: {current_memory:.1f} MB")
        
        time.sleep(1)  # Let processing complete
    
    # Analysis
    final_memory = memory_readings[-1]
    memory_growth = final_memory - initial_memory
    
    print(f"\n📊 Memory Analysis:")
    print(f"Initial: {initial_memory:.1f} MB")
    print(f"Final: {final_memory:.1f} MB")
    print(f"Growth: {memory_growth:.1f} MB")
    print(f"Growth per 1000 events: {memory_growth / num_batches:.3f} MB")
    
    # Check for concerning growth
    if memory_growth > 50:  # 50MB growth
        print("  🚨 CONCERNING: Significant memory growth detected")
        print("    - Check for memory leaks")
        print("    - Verify queue cleanup")
        print("    - Check sink resource management")
    elif memory_growth > 10:  # 10MB growth
        print("  ⚠️  MODERATE: Some memory growth detected")
        print("    - Monitor in production")
        print("    - Consider periodic restarts")
    else:
        print("  ✅ GOOD: Minimal memory growth")

memory_leak_test()
```

### Configuration Debugging

**Configuration validation and debugging:**

```python
def debug_configuration():
    """Debug fapilog configuration issues."""
    
    print("🔧 Configuration Debug")
    
    # Check environment variables
    import os
    fapilog_vars = {k: v for k, v in os.environ.items() if k.startswith('FAPILOG_')}
    
    print(f"\n🌍 Environment Variables ({len(fapilog_vars)} found):")
    for key, value in fapilog_vars.items():
        # Mask sensitive values
        display_value = "***" if any(secret in key.lower() for secret in ['password', 'token', 'secret']) else value
        print(f"  {key} = {display_value}")
    
    # Load and validate settings
    try:
        from fapilog.settings import LoggingSettings
        settings = LoggingSettings()
        
        print(f"\n⚙️  Loaded Settings:")
        print(f"  Level: {settings.level}")
        print(f"  Format: {settings.format}")
        print(f"  Sinks: {settings.sinks}")
        print(f"  Queue enabled: {settings.queue_enabled}")
        print(f"  Queue size: {settings.queue_maxsize}")
        print(f"  Metrics enabled: {settings.metrics_enabled}")
        
        # Test configuration
        configure_logging(settings=settings)
        log.info("Configuration test successful")
        print("  ✅ Configuration loaded successfully")
        
    except Exception as e:
        print(f"  ❌ Configuration error: {e}")
        print("  Check environment variables and settings")
    
    # Check dependencies
    print(f"\n📦 Dependencies:")
    
    dependencies = [
        ("structlog", "Core logging"),
        ("pydantic", "Settings validation"),
        ("httpx", "Loki sink (optional)"),
        ("prometheus_client", "Metrics (optional)"),
        ("psutil", "Resource metrics (optional)")
    ]
    
    for package, description in dependencies:
        try:
            __import__(package)
            print(f"  ✅ {package}: Available ({description})")
        except ImportError:
            required = package in ["structlog", "pydantic"]
            status = "❌ REQUIRED" if required else "⚠️  Optional"
            print(f"  {status} {package}: Not installed ({description})")

debug_configuration()
```

### Network Connectivity Debugging

**Test sink connectivity:**

```python
import asyncio
import aiohttp

async def test_loki_connectivity():
    """Test Loki sink connectivity."""
    
    print("🌐 Testing Loki Connectivity")
    
    loki_url = os.getenv("FAPILOG_LOKI_URL", "http://localhost:3100")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Test basic connectivity
            async with session.get(f"{loki_url}/ready") as response:
                if response.status == 200:
                    print(f"  ✅ Loki ready endpoint accessible")
                else:
                    print(f"  ⚠️  Loki ready endpoint returned {response.status}")
            
            # Test push endpoint
            test_log = {
                "streams": [
                    {
                        "stream": {"job": "test"},
                        "values": [
                            [str(int(time.time() * 1000000000)), "test log entry"]
                        ]
                    }
                ]
            }
            
            async with session.post(
                f"{loki_url}/loki/api/v1/push",
                json=test_log,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status in [200, 204]:
                    print(f"  ✅ Loki push endpoint accessible")
                else:
                    print(f"  ❌ Loki push failed: {response.status}")
                    print(f"     Response: {await response.text()}")
    
    except aiohttp.ClientError as e:
        print(f"  ❌ Connection error: {e}")
        print("  Check:")
        print("    - Loki service is running")
        print("    - Network connectivity")
        print("    - FAPILOG_LOKI_URL setting")
    except Exception as e:
        print(f"  ❌ Unexpected error: {e}")

# Run connectivity test
asyncio.run(test_loki_connectivity())
```

[↑ Back to top](#monitoring--production-guide)

---

## Best Practices Summary

### 🔍 **Monitoring Checklist**

- ✅ Enable comprehensive metrics collection
- ✅ Set up Prometheus integration for observability stacks
- ✅ Configure appropriate alert thresholds
- ✅ Monitor queue utilization and sink health
- ✅ Track performance trends over time

### 🚀 **Deployment Checklist**

- ✅ Use container-based deployment with proper resource limits
- ✅ Configure environment-specific settings
- ✅ Implement health checks and readiness probes
- ✅ Set up log aggregation and centralized monitoring
- ✅ Plan for horizontal scaling and load distribution

### ⚡ **Performance Checklist**

- ✅ Tune queue size and batch settings for your workload
- ✅ Choose appropriate overflow strategies
- ✅ Monitor memory usage and resource consumption
- ✅ Implement sampling for high-volume scenarios
- ✅ Use connection pooling for external sinks

### 🛡️ **Reliability Checklist**

- ✅ Implement graceful degradation patterns
- ✅ Use circuit breakers for external dependencies
- ✅ Configure retry mechanisms with exponential backoff
- ✅ Set up fallback sinks for critical scenarios
- ✅ Monitor sink health and implement automatic recovery

Production-ready fapilog deployments require careful attention to monitoring, performance tuning, and reliability patterns. This guide provides the foundation for enterprise-scale logging infrastructure that scales with your applications and provides the observability needed for successful production operations.

[↑ Back to top](#monitoring--production-guide) 