"""Tests for DeduplicationProcessor duplicate event filtering."""

import hashlib
import json
import threading
import time

import pytest

from fapilog._internal.processors import DeduplicationProcessor
from fapilog.exceptions import ProcessorConfigurationError


class TestDeduplicationProcessor:
    """Test DeduplicationProcessor functionality."""

    def test_deduplication_processor_initialization(self):
        """Test DeduplicationProcessor initialization with valid parameters."""
        processor = DeduplicationProcessor(
            window_seconds=60,
            dedupe_fields=["event", "service", "error_code"],
            max_cache_size=5000,
            hash_algorithm="sha256",
        )

        assert processor.window_seconds == 60
        assert processor.dedupe_fields == ["event", "service", "error_code"]
        assert processor.max_cache_size == 5000
        assert processor.hash_algorithm == "sha256"
        assert isinstance(processor._event_cache, dict)
        assert isinstance(processor._lock, threading.Lock)

    def test_deduplication_processor_default_values(self):
        """Test DeduplicationProcessor with default configuration."""
        processor = DeduplicationProcessor()

        assert processor.window_seconds == 300
        assert processor.dedupe_fields == ["event", "level", "hostname"]
        assert processor.max_cache_size == 10000
        assert processor.hash_algorithm == "md5"

    def test_deduplication_processor_config_validation(self):
        """Test configuration validation for DeduplicationProcessor."""
        # Valid configuration should work
        processor = DeduplicationProcessor(
            window_seconds=60,
            dedupe_fields=["event"],
            max_cache_size=1000,
            hash_algorithm="sha1",
        )
        processor.validate_config()  # Should not raise

        # Invalid window_seconds
        with pytest.raises(
            ProcessorConfigurationError,
            match="window_seconds must be a positive integer",
        ):
            DeduplicationProcessor(window_seconds=0)

        with pytest.raises(
            ProcessorConfigurationError,
            match="window_seconds must be a positive integer",
        ):
            DeduplicationProcessor(window_seconds=-10)

        # Invalid max_cache_size
        with pytest.raises(
            ProcessorConfigurationError,
            match="max_cache_size must be a positive integer",
        ):
            DeduplicationProcessor(max_cache_size=0)

        with pytest.raises(
            ProcessorConfigurationError,
            match="max_cache_size must be a positive integer",
        ):
            DeduplicationProcessor(max_cache_size=-100)

        # Invalid dedupe_fields
        with pytest.raises(
            ProcessorConfigurationError,
            match="dedupe_fields cannot be empty and must be a list",
        ):
            DeduplicationProcessor(dedupe_fields=[])

        # Invalid hash_algorithm
        with pytest.raises(
            ProcessorConfigurationError,
            match="hash_algorithm must be 'md5', 'sha1', or 'sha256'",
        ):
            DeduplicationProcessor(hash_algorithm="sha512")

        with pytest.raises(
            ProcessorConfigurationError,
            match="hash_algorithm must be 'md5', 'sha1', or 'sha256'",
        ):
            DeduplicationProcessor(hash_algorithm="invalid")

    def test_signature_generation_md5(self):
        """Test signature generation with MD5 algorithm."""
        processor = DeduplicationProcessor(
            dedupe_fields=["event", "level"], hash_algorithm="md5"
        )

        event_dict = {
            "event": "Database connection failed",
            "level": "ERROR",
            "timestamp": "2023-01-01T00:00:00Z",
            "service": "api",  # This should be ignored
        }

        signature = processor._generate_signature(event_dict)

        # Verify the signature is consistent
        signature2 = processor._generate_signature(event_dict)
        assert signature == signature2

        # Verify it's an MD5 hash (32 characters)
        assert len(signature) == 32
        assert all(c in "0123456789abcdef" for c in signature)

        # Verify it's based on the correct fields
        expected_data = {"event": "Database connection failed", "level": "ERROR"}
        expected_str = json.dumps(expected_data, sort_keys=True)
        expected_hash = hashlib.md5(expected_str.encode()).hexdigest()
        assert signature == expected_hash

    def test_signature_generation_sha256(self):
        """Test signature generation with SHA256 algorithm."""
        processor = DeduplicationProcessor(
            dedupe_fields=["event"], hash_algorithm="sha256"
        )

        event_dict = {"event": "Test message", "other": "ignored"}
        signature = processor._generate_signature(event_dict)

        # Verify it's a SHA256 hash (64 characters)
        assert len(signature) == 64
        assert all(c in "0123456789abcdef" for c in signature)

    def test_signature_generation_missing_fields(self):
        """Test signature generation when dedupe_fields are missing from event."""
        processor = DeduplicationProcessor(
            dedupe_fields=["event", "missing_field"], hash_algorithm="md5"
        )

        event_dict = {"event": "Test message", "other": "data"}
        signature = processor._generate_signature(event_dict)

        # Should only include fields that exist
        expected_data = {"event": "Test message"}
        expected_str = json.dumps(expected_data, sort_keys=True)
        expected_hash = hashlib.md5(expected_str.encode()).hexdigest()
        assert signature == expected_hash

    def test_duplicate_detection_basic(self):
        """Test basic duplicate detection functionality."""
        processor = DeduplicationProcessor(
            window_seconds=60, dedupe_fields=["event", "level"]
        )

        event1 = {
            "event": "Database error",
            "level": "ERROR",
            "timestamp": "2023-01-01T00:00:00Z",
        }

        # First event should pass through
        result1 = processor.process(None, "error", event1)
        assert result1 == event1

        # Identical event should be deduplicated (dropped)
        result2 = processor.process(None, "error", event1)
        assert result2 is None

        # Different event should pass through
        event2 = {
            "event": "Network error",
            "level": "ERROR",
            "timestamp": "2023-01-01T00:00:01Z",
        }
        result3 = processor.process(None, "error", event2)
        assert result3 == event2

    def test_duplicate_detection_different_signatures(self):
        """Test that events with different signatures are not deduplicated."""
        processor = DeduplicationProcessor(
            window_seconds=60, dedupe_fields=["event", "error_code"]
        )

        event1 = {"event": "Database error", "error_code": "DB001"}
        event2 = {
            "event": "Database error",
            "error_code": "DB002",
        }  # Different error code

        # Both should pass through (different signatures)
        result1 = processor.process(None, "error", event1)
        result2 = processor.process(None, "error", event2)

        assert result1 == event1
        assert result2 == event2

        # Now duplicate the first one - should be dropped
        result3 = processor.process(None, "error", event1)
        assert result3 is None

    def test_time_window_expiration(self):
        """Test that duplicates are allowed after time window expires."""
        processor = DeduplicationProcessor(
            window_seconds=1,
            dedupe_fields=["event"],  # Very short window for testing
        )

        event = {"event": "Test message", "timestamp": "2023-01-01T00:00:00Z"}

        # First event passes
        result1 = processor.process(None, "info", event)
        assert result1 == event

        # Immediate duplicate is dropped
        result2 = processor.process(None, "info", event)
        assert result2 is None

        # Wait for window to expire
        time.sleep(1.1)

        # Now should pass again (outside window)
        result3 = processor.process(None, "info", event)
        assert result3 == event

    def test_duplicate_count_tracking(self):
        """Test that duplicate counts are tracked correctly."""
        processor = DeduplicationProcessor(window_seconds=60, dedupe_fields=["event"])

        event = {"event": "Repeated message"}

        # First event
        processor.process(None, "info", event)

        # Get the signature to check cache directly
        signature = processor._generate_signature(event)
        assert signature in processor._event_cache
        _, count = processor._event_cache[signature]
        assert count == 1

        # Process duplicates
        for _i in range(5):
            processor.process(None, "info", event)

        # Check count increased
        _, count = processor._event_cache[signature]
        assert count == 6

    def test_cache_size_limiting(self):
        """Test cache size limiting and eviction."""
        processor = DeduplicationProcessor(
            window_seconds=300, max_cache_size=5, dedupe_fields=["event"]
        )

        # Fill cache beyond limit
        for i in range(10):
            event = {"event": f"Message {i}"}
            processor.process(None, "info", event)

        # Cache should be limited to max_cache_size (some eviction should occur)
        assert len(processor._event_cache) <= processor.max_cache_size

    def test_cache_cleanup_expired_entries(self):
        """Test automatic cleanup of expired cache entries."""
        processor = DeduplicationProcessor(
            window_seconds=1,
            dedupe_fields=["event"],  # Short window
        )

        # Add some events
        for i in range(3):
            event = {"event": f"Message {i}"}
            processor.process(None, "info", event)

        assert len(processor._event_cache) == 3

        # Wait for expiration
        time.sleep(1.1)

        # Process a new event to trigger cleanup
        new_event = {"event": "New message"}
        processor.process(None, "info", new_event)

        # Only the new event should remain
        assert len(processor._event_cache) == 1

    def test_thread_safety(self):
        """Test that the processor is thread-safe."""
        processor = DeduplicationProcessor(
            window_seconds=60, dedupe_fields=["event", "worker_id"]
        )

        results = []
        errors = []

        def worker(worker_id: int):
            try:
                for i in range(20):
                    event = {
                        "event": f"Worker message {i}",
                        "worker_id": worker_id,
                        "timestamp": time.time(),
                    }
                    result = processor.process(None, "info", event)
                    results.append(result is not None)
            except Exception as e:
                errors.append(e)

        # Run multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # No errors should occur
        assert len(errors) == 0

        # All events should pass (different signatures per worker)
        assert all(results)

        # Should have entries for each worker
        assert len(processor._event_cache) >= 5

    def test_cache_stats(self):
        """Test cache statistics reporting."""
        processor = DeduplicationProcessor(
            window_seconds=60, dedupe_fields=["event"], max_cache_size=1000
        )

        # Initially empty
        stats = processor.cache_stats
        assert stats["unique_signatures"] == 0
        assert stats["total_events_seen"] == 0
        assert stats["cache_size"] == 0
        assert stats["max_cache_size"] == 1000

        # Add some events
        event1 = {"event": "Message 1"}
        event2 = {"event": "Message 2"}

        processor.process(None, "info", event1)
        processor.process(None, "info", event1)  # Duplicate
        processor.process(None, "info", event2)

        stats = processor.cache_stats
        assert stats["unique_signatures"] == 2
        assert stats["total_events_seen"] == 3  # 2 + 1 duplicate
        assert stats["cache_size"] == 2

    def test_eviction_oldest_entries(self):
        """Test that oldest entries are evicted when cache is full."""
        processor = DeduplicationProcessor(
            window_seconds=300, max_cache_size=10, dedupe_fields=["event"]
        )

        # Fill cache
        for i in range(10):
            event = {"event": f"Message {i}"}
            processor.process(None, "info", event)

        # Get first signature
        first_event = {"event": "Message 0"}
        first_signature = processor._generate_signature(first_event)
        assert first_signature in processor._event_cache

        # Add more events to trigger eviction
        for i in range(10, 15):
            event = {"event": f"Message {i}"}
            processor.process(None, "info", event)

        # First signature should be evicted (oldest)
        assert first_signature not in processor._event_cache
        assert len(processor._event_cache) <= processor.max_cache_size

    def test_different_hash_algorithms(self):
        """Test all supported hash algorithms produce different results."""
        processors = {
            "md5": DeduplicationProcessor(hash_algorithm="md5"),
            "sha1": DeduplicationProcessor(hash_algorithm="sha1"),
            "sha256": DeduplicationProcessor(hash_algorithm="sha256"),
        }

        event = {"event": "Test message", "level": "INFO"}

        signatures = {}
        for algo, proc in processors.items():
            signature = proc._generate_signature(event)
            signatures[algo] = signature

        # All should be different
        assert len(set(signatures.values())) == 3

        # Check expected lengths
        assert len(signatures["md5"]) == 32
        assert len(signatures["sha1"]) == 40
        assert len(signatures["sha256"]) == 64


class TestDeduplicationProcessorIntegration:
    """Test DeduplicationProcessor integration scenarios."""

    def test_processor_with_real_log_structure(self):
        """Test processor with realistic log event structure."""
        processor = DeduplicationProcessor(
            window_seconds=60,
            dedupe_fields=["event", "error_code", "service"],
        )

        log_event = {
            "event": "Payment processing failed",
            "level": "ERROR",
            "timestamp": "2023-01-01T00:00:00Z",
            "service": "payment-service",
            "error_code": "PAY001",
            "user_id": "user123",
            "amount": 99.99,
            "trace_id": "abc-123-def",
        }

        # First event passes
        result1 = processor.process(None, "error", log_event)
        assert result1 == log_event

        # Duplicate with same signature fields should be dropped
        duplicate_event = log_event.copy()
        duplicate_event["trace_id"] = (
            "different-trace"  # Different trace but same signature
        )
        result2 = processor.process(None, "error", duplicate_event)
        assert result2 is None

        # Different error code should pass
        different_event = log_event.copy()
        different_event["error_code"] = "PAY002"
        result3 = processor.process(None, "error", different_event)
        assert result3 == different_event

    def test_processor_registration(self):
        """Test that DeduplicationProcessor is properly registered."""
        # Import processors module first to ensure registration happens
        import fapilog._internal.processors  # noqa: F401
        from fapilog._internal.processor_registry import ProcessorRegistry

        # Ensure DeduplicationProcessor is registered (in case other tests cleared it)
        ProcessorRegistry.register("deduplication", DeduplicationProcessor)

        # Should be registered as "deduplication"
        registered_class = ProcessorRegistry.get("deduplication")
        assert registered_class is DeduplicationProcessor

    def test_deduplication_with_complex_nested_data(self):
        """Test deduplication with complex nested event data."""
        processor = DeduplicationProcessor(
            window_seconds=60, dedupe_fields=["event", "error_details"]
        )

        event1 = {
            "event": "API call failed",
            "error_details": {
                "code": 500,
                "message": "Internal server error",
                "endpoint": "/api/users",
            },
            "metadata": {"request_id": "req-123", "timestamp": "2023-01-01T00:00:00Z"},
        }

        event2 = {
            "event": "API call failed",
            "error_details": {
                "code": 500,
                "message": "Internal server error",
                "endpoint": "/api/users",
            },
            "metadata": {"request_id": "req-456", "timestamp": "2023-01-01T00:01:00Z"},
        }

        # Both events have same signature (event + error_details)
        result1 = processor.process(None, "error", event1)
        assert result1 == event1

        # Should be deduplicated despite different metadata
        result2 = processor.process(None, "error", event2)
        assert result2 is None

    def test_memory_efficiency_large_cache(self):
        """Test memory efficiency with large cache operations."""
        processor = DeduplicationProcessor(
            window_seconds=3600, max_cache_size=1000, dedupe_fields=["event", "id"]
        )

        # Generate many unique events
        for i in range(500):
            event = {"event": "Bulk operation", "id": i, "data": f"payload-{i}"}
            result = processor.process(None, "info", event)
            assert result is not None

        # Generate some duplicates
        for i in range(100):
            event = {
                "event": "Bulk operation",
                "id": i,
                "data": f"different-payload-{i}",
            }
            result = processor.process(None, "info", event)
            assert result is None  # Should be deduplicated

        # Cache should be managed properly
        assert len(processor._event_cache) <= processor.max_cache_size

        # Stats should reflect the operations
        stats = processor.cache_stats
        assert stats["total_events_seen"] >= 600  # 500 unique + 100 duplicates
