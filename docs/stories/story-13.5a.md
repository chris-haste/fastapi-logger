# Story 13.5a – Implement Basic Metrics Collection System

**Epic:** 13 – Architecture Improvements  
Sprint Target: Sprint #⟪next⟫  
Story Points: 5

**As a library maintainer**  
I want to implement basic metrics collection for queue and sink performance  
So that users can monitor logging performance and health in production environments.

───────────────────────────────────  
Acceptance Criteria

- Metrics collection system for queue performance (size, throughput, latency)
- Metrics for sink performance (success rate, error rate, latency)
- Memory usage monitoring for queue and sinks
- Performance counters for log processing
- Metrics export in Prometheus format
- Comprehensive tests for metrics accuracy
- Documentation for metrics setup and usage

───────────────────────────────────  
Tasks / Technical Checklist

1. **Create metrics collection system in `src/fapilog/_internal/metrics.py`**:

   - `MetricsCollector` class for centralized metrics
   - Queue metrics: size, throughput, drop rate, latency
   - Sink metrics: success rate, error rate, batch size, latency
   - Memory metrics: queue memory usage, sink memory usage
   - Performance metrics: processing time, batch processing time

2. **Add metrics to queue worker in `_internal/queue.py`**:

   - Track queue size and throughput
   - Monitor batch processing performance
   - Track error rates and retry attempts
   - Monitor memory usage

3. **Add metrics to sinks in `sinks/`**:

   - Track success/failure rates
   - Monitor batch processing performance
   - Track network latency for HTTP sinks
   - Monitor memory usage per sink

4. **Create basic Prometheus exporter in `src/fapilog/monitoring.py`**:

   - Export metrics in Prometheus format
   - Provide HTTP endpoint for metrics scraping
   - Include standard metrics (queue_size, sink_errors, etc.)
   - Support basic custom metrics

5. **Add comprehensive tests**:

   - Test metrics collection accuracy
   - Test Prometheus export format
   - Test memory usage monitoring
   - Test performance impact

6. **Update documentation**:
   - Metrics setup guide
   - Metrics reference
   - Basic monitoring examples

───────────────────────────────────  
Dependencies / Notes

- Should be optional and not impact performance when disabled
- Metrics should be configurable (enable/disable, sampling rate)
- Performance impact should be minimal
- Should integrate with existing queue and sink architecture

───────────────────────────────────  
Definition of Done  
✓ Metrics collection system implemented  
✓ Queue and sink metrics tracked  
✓ Memory usage monitoring implemented  
✓ Basic Prometheus exporter working  
✓ Comprehensive tests added  
✓ Performance impact minimal  
✓ Documentation complete  
✓ PR merged to **main** with reviewer approval and green CI  
✓ `CHANGELOG.md` updated under _Unreleased → Added_

───────────────────────────────────  
**CURRENT STATUS: ✅ COMPLETED**

**Completed Tasks:**

- ✅ Create `MetricsCollector` class
- ✅ Add metrics to queue worker
- ✅ Add metrics to sinks
- ✅ Create Prometheus exporter
- ✅ Add comprehensive tests
- ✅ Update documentation
