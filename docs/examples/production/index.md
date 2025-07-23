# Production Deployment Examples

**High-performance logging for production environments**

This section covers production-grade patterns including async queues, performance optimization, monitoring, and container architecture for scalable logging systems.

---

## 📚 What You'll Learn

- **Queue Configuration** - Async logging for high throughput
- **Overflow Strategies** - Handle logging bursts gracefully
- **Performance Testing** - Measure and optimize logging performance
- **Batch Processing** - Optimize for bulk operations
- **Metrics & Monitoring** - Monitor your logging system
- **Container Architecture** - Multi-service logging patterns

---

## 🚀 Examples

### 09 - Queue Configuration

**Configure async logging queue for high-performance applications**

```python
#!/usr/bin/env python3
"""
Example 9: Queue Configuration

This example demonstrates how to configure and use the async logging queue in fapilog.
It shows how queue settings affect logging behavior and performance.
"""

import time

from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings


def main():
    print("=== Queue Configuration Example ===\n")

    # Configure logging with queue enabled
    settings = LoggingSettings(
        level="INFO",
        json_console="pretty",
        queue_enabled=True,  # Enable async queue
        queue_maxsize=5,  # Small queue for demonstration
        queue_batch_size=2,  # Process 2 events per batch
        queue_batch_timeout=0.5,  # 0.5s max wait for batch
        queue_overflow="drop",  # Drop logs if queue is full
    )
    configure_logging(settings=settings)

    print("Queue settings:")
    print(f"  queue_enabled: {settings.queue_enabled}")
    print(f"  queue_maxsize: {settings.queue_maxsize}")
    print(f"  queue_batch_size: {settings.queue_batch_size}")
    print(f"  queue_batch_timeout: {settings.queue_batch_timeout}")
    print(f"  queue_overflow: {settings.queue_overflow}")
    print()

    print("Logging 10 events rapidly to demonstrate queue behavior...")
    for i in range(10):
        log.info("Queue test event", event_number=i)
        time.sleep(0.05)  # Rapid fire

    print("\nAll events enqueued. Waiting for queue to flush...")
    time.sleep(2)  # Wait for queue to process

    print("\nKey takeaways:")
    print("✅ Async queue decouples logging from main thread")
    print("✅ Small queue size can drop logs if overwhelmed")
    print("✅ Batch size and timeout control flush behavior")
    print("✅ Overflow strategy determines what happens when full")
    print("✅ Use larger queue and batch size for production")


if __name__ == "__main__":
    main()
```

**Production Settings:**

```python
# High-throughput production configuration
settings = LoggingSettings(
    queue_enabled=True,
    queue_maxsize=10000,      # Large queue for bursts
    queue_batch_size=100,     # Batch for efficiency
    queue_batch_timeout=0.5,  # Flush every 500ms
    overflow_strategy="drop"  # Drop logs if queue full
)
```

**Key Features:**

- ✅ Async queue processing
- ✅ Configurable queue size
- ✅ Batching for efficiency
- ✅ Non-blocking operation

---

### 10 - Overflow Strategies

**Handle queue overflow in different scenarios**

```python
#!/usr/bin/env python3
"""
Example 10: Overflow Strategies

This example demonstrates different overflow strategies for handling
queue overflow scenarios in high-load situations.
"""

from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings


def main():
    print("=== Overflow Strategies Example ===\n")

    # Drop strategy (high performance, may lose logs)
    print("1. Drop strategy (high performance):")
    drop_settings = LoggingSettings(
        queue_enabled=True,
        queue_maxsize=3,  # Very small for demo
        queue_overflow="drop"
    )
    configure_logging(settings=drop_settings)

    for i in range(10):
        log.info("Drop strategy test", event_number=i)
    print("   → May lose some logs under load but won't block app\n")

    # Block strategy (guaranteed delivery, may block app)
    print("2. Block strategy (guaranteed delivery):")
    block_settings = LoggingSettings(
        queue_enabled=True,
        queue_maxsize=100,
        queue_overflow="block"
    )
    configure_logging(settings=block_settings)
    print("   → Guarantees all logs are processed but may slow app\n")

    # Sample strategy (keep percentage under load)
    print("3. Sample strategy (balanced approach):")
    sample_settings = LoggingSettings(
        queue_enabled=True,
        queue_maxsize=100,
        queue_overflow="sample",
        sampling_rate=0.1  # Keep 10% of logs when overwhelmed
    )
    configure_logging(settings=sample_settings)
    print("   → Keeps representative sample when overwhelmed")


if __name__ == "__main__":
    main()
```

**Strategy Comparison:**

| Strategy   | Performance | Reliability | Use Case                           |
| ---------- | ----------- | ----------- | ---------------------------------- |
| **Drop**   | Highest     | Lowest      | High-throughput, non-critical logs |
| **Block**  | Lowest      | Highest     | Critical logs, low-throughput      |
| **Sample** | Medium      | Medium      | Balanced production workloads      |

**Key Features:**

- ✅ Drop strategy for high performance
- ✅ Block strategy for guaranteed delivery
- ✅ Sample strategy for load balancing

---

### 11 - Performance Testing

**Test logging performance under load**

```python
#!/usr/bin/env python3
"""
Example 11: Performance Testing

This example demonstrates how to test and measure logging performance
under different configurations and load scenarios.
"""

import asyncio
import time
from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings


async def performance_test(config_name: str, settings: LoggingSettings, event_count: int = 1000):
    """Run a performance test with specific settings."""
    print(f"\n=== {config_name} Performance Test ===")
    configure_logging(settings=settings)

    start_time = time.time()

    # Log messages rapidly
    for i in range(event_count):
        log.info("Performance test message",
                 iteration=i,
                 timestamp=time.time(),
                 test_config=config_name)

        if i % 100 == 0:  # Minimal delay every 100 messages
            await asyncio.sleep(0.001)

    # Wait for queue to process (if enabled)
    if settings.queue_enabled:
        await asyncio.sleep(2)

    duration = time.time() - start_time
    rate = event_count / duration

    print(f"Logged {event_count} messages in {duration:.2f}s")
    print(f"Rate: {rate:.0f} messages/second")
    print(f"Config: queue={settings.queue_enabled}, batch_size={getattr(settings, 'queue_batch_size', 'N/A')}")

    return rate


async def main():
    """Run performance comparison tests."""
    print("=== Logging Performance Comparison ===")

    # Test 1: Synchronous logging
    sync_settings = LoggingSettings(
        level="INFO",
        json_console="json",
        queue_enabled=False
    )
    sync_rate = await performance_test("Synchronous", sync_settings, 500)

    # Test 2: Async queue with small batches
    small_batch_settings = LoggingSettings(
        level="INFO",
        json_console="json",
        queue_enabled=True,
        queue_maxsize=1000,
        queue_batch_size=10,
        queue_batch_timeout=0.1
    )
    small_rate = await performance_test("Small Batches", small_batch_settings, 1000)

    # Test 3: Async queue with large batches
    large_batch_settings = LoggingSettings(
        level="INFO",
        json_console="json",
        queue_enabled=True,
        queue_maxsize=10000,
        queue_batch_size=100,
        queue_batch_timeout=0.5
    )
    large_rate = await performance_test("Large Batches", large_batch_settings, 2000)

    print(f"\n=== Performance Summary ===")
    print(f"Synchronous:    {sync_rate:.0f} msg/sec")
    print(f"Small Batches:  {small_rate:.0f} msg/sec")
    print(f"Large Batches:  {large_rate:.0f} msg/sec")
    print(f"Improvement:    {large_rate/sync_rate:.1f}x faster with large batches")


if __name__ == "__main__":
    asyncio.run(main())
```

**Key Features:**

- ✅ Throughput benchmarking
- ✅ Performance metrics
- ✅ Load testing patterns
- ✅ Configuration comparison

---

### 12 - Batch Processing

**Optimize logging for batch operations**

```python
#!/usr/bin/env python3
"""
Example 12: Batch Processing

This example demonstrates optimized logging patterns for high-volume
batch processing operations with progress tracking and error handling.
"""

import asyncio
import time
import random
from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings


def generate_batch_id():
    """Generate a unique batch ID."""
    return f"batch_{int(time.time())}_{random.randint(1000, 9999)}"


async def process_item(item):
    """Simulate processing a single item."""
    await asyncio.sleep(random.uniform(0.01, 0.05))

    # Simulate occasional failures
    if random.random() < 0.05:  # 5% failure rate
        raise Exception(f"Processing failed for item {item.get('id', 'unknown')}")

    return {"status": "processed", "item_id": item.get("id")}


async def process_batch(items: list):
    """Process a batch of items with comprehensive logging."""
    batch_id = generate_batch_id()

    log.info("Batch processing started",
             batch_id=batch_id,
             item_count=len(items),
             estimated_duration_minutes=(len(items) * 0.03) / 60)

    processed = 0
    errors = 0
    start_time = time.time()

    for i, item in enumerate(items):
        try:
            result = await process_item(item)
            processed += 1

            # Log progress every 100 items
            if processed % 100 == 0:
                elapsed = time.time() - start_time
                items_per_second = processed / elapsed
                estimated_remaining = (len(items) - processed) / items_per_second

                log.info("Batch progress",
                         batch_id=batch_id,
                         processed=processed,
                         total=len(items),
                         progress_percent=round((processed / len(items)) * 100, 1),
                         items_per_second=round(items_per_second, 1),
                         estimated_remaining_seconds=round(estimated_remaining))

        except Exception as e:
            errors += 1
            log.error("Item processing failed",
                      batch_id=batch_id,
                      item_id=item.get("id", f"item_{i}"),
                      error=str(e),
                      error_count=errors)

    # Log batch completion
    total_duration = time.time() - start_time
    success_rate = (processed / len(items)) * 100

    log.info("Batch processing completed",
             batch_id=batch_id,
             total_items=len(items),
             processed=processed,
             errors=errors,
             success_rate=round(success_rate, 1),
             total_duration_seconds=round(total_duration, 2),
             items_per_second=round(len(items) / total_duration, 1))

    return {
        "batch_id": batch_id,
        "processed": processed,
        "errors": errors,
        "success_rate": success_rate
    }


async def main():
    """Run batch processing example."""
    # Configure for batch processing
    settings = LoggingSettings(
        level="INFO",
        json_console="json",
        queue_enabled=True,
        queue_maxsize=5000,      # Large queue for batch operations
        queue_batch_size=50,     # Medium batches for balanced performance
        queue_batch_timeout=1.0  # Longer timeout for batch operations
    )

    configure_logging(settings=settings)

    # Generate sample data
    items = [{"id": f"item_{i:04d}", "data": f"sample_data_{i}"} for i in range(500)]

    log.info("Starting batch processing example",
             total_batches=1,
             items_per_batch=len(items))

    # Process the batch
    result = await process_batch(items)

    log.info("Batch processing example completed",
             **result)


if __name__ == "__main__":
    asyncio.run(main())
```

**Key Features:**

- ✅ Batch progress logging
- ✅ Error aggregation
- ✅ Performance tracking
- ✅ Progress estimation

---

### 21 - Metrics & Monitoring

**Monitor logging system performance and resource usage**

```python
#!/usr/bin/env python3
"""
Example 21: Metrics & Monitoring

This example demonstrates how to monitor the logging system itself
using built-in metrics and resource monitoring capabilities.
"""

import asyncio
import time
from fapilog import configure_logging, log
from fapilog.settings import LoggingSettings
from fapilog.monitoring import get_metrics_dict


async def generate_load():
    """Generate logging load to demonstrate metrics."""
    for i in range(100):
        log.info("Load generation event",
                 event_number=i,
                 load_type="metrics_demo")
        await asyncio.sleep(0.01)


async def monitor_metrics():
    """Monitor and display logging metrics."""
    print("=== Logging System Metrics ===\n")

    for round_num in range(5):
        # Get current metrics
        metrics = get_metrics_dict()

        print(f"Round {round_num + 1}:")
        print(f"  Queue size: {metrics.get('queue', {}).get('size', 'N/A')}")
        print(f"  Total events: {metrics.get('performance', {}).get('total_log_events', 'N/A')}")
        print(f"  Events/sec: {metrics.get('performance', {}).get('events_per_second', 'N/A')}")
        print(f"  Memory usage: {metrics.get('performance', {}).get('memory_bytes', 'N/A')} bytes")
        print(f"  CPU percent: {metrics.get('performance', {}).get('cpu_percent', 'N/A')}%")
        print()

        # Generate some load
        await generate_load()
        await asyncio.sleep(2)


async def main():
    """Run metrics monitoring example."""
    # Enable resource metrics
    settings = LoggingSettings(
        level="INFO",
        json_console="pretty",
        enable_resource_metrics=True,
        queue_enabled=True,
        queue_maxsize=1000,
        queue_batch_size=10
    )

    configure_logging(settings=settings)

    log.info("Starting metrics monitoring example",
             monitoring_enabled=True,
             resource_metrics=True)

    # Run monitoring
    await monitor_metrics()

    log.info("Metrics monitoring example completed")


if __name__ == "__main__":
    asyncio.run(main())
```

**Prometheus Integration:**

```python
# For Prometheus metrics export
settings = LoggingSettings(
    enable_resource_metrics=True,
    metrics_prometheus_enabled=True,
    metrics_prometheus_port=8000
)

# Access metrics at: http://localhost:8000/metrics
```

**Key Features:**

- ✅ Real-time metrics collection
- ✅ Resource usage monitoring
- ✅ Queue performance metrics
- ✅ Prometheus export support

---

## 🏗️ Production Architecture

### **High-Throughput Setup**

```python
# Optimized for 10,000+ events/second
settings = LoggingSettings(
    queue_enabled=True,
    queue_maxsize=50000,
    queue_batch_size=1000,
    queue_batch_timeout=1.0,
    overflow_strategy="drop"
)
```

### **Reliable Delivery Setup**

```python
# Optimized for guaranteed delivery
settings = LoggingSettings(
    queue_enabled=True,
    queue_maxsize=5000,
    queue_batch_size=50,
    queue_batch_timeout=0.1,
    overflow_strategy="block"
)
```

### **Monitoring & Observability**

```python
# Production monitoring
settings = LoggingSettings(
    enable_resource_metrics=True,
    metrics_prometheus_enabled=True,
    metrics_prometheus_port=8000
)
```

---

## 🎯 Next Steps

### 🔒 **Security & Compliance**

- **[Advanced Patterns](../advanced/index.md)** - PII redaction, security logging, compliance

### 🚀 **Custom Components**

- **[Sink Development](../sinks/index.md)** - Send logs to enterprise systems

### 📖 **Deep Dive**

- **[Configuration Guide](../../config.md)** - Complete production configuration
- **[Advanced Development](../../advanced-development.md)** - Build custom components

---

## 💡 Production Tips

1. **Size Your Queue** - Match queue size to your traffic patterns
2. **Choose Strategy Wisely** - Drop for performance, block for reliability
3. **Monitor Everything** - Use metrics to understand your logging performance
4. **Test Under Load** - Benchmark before deploying to production
5. **Plan for Failures** - Handle overflow and errors gracefully
6. **Use Containers** - Isolate logging for different services

Ready for advanced patterns? Check out [advanced examples](../advanced/index.md)!
