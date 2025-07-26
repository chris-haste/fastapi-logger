#!/usr/bin/env python3
"""
Test security fix for Issue #81: tempfile.mktemp() replacement.

This test verifies that the insecure tempfile.mktemp() usage has been
replaced with secure NamedTemporaryFile approach in examples/14_multiple_sinks.py.
"""

import os
import tempfile
from pathlib import Path


def test_secure_temporary_file_creation():
    """Test that NamedTemporaryFile creates secure temporary files."""
    # Test the same pattern used in the fixed code
    with tempfile.NamedTemporaryFile(
        mode="w+", suffix=".log", prefix="fapilog_multi_sink_", delete=False
    ) as temp_file:
        log_file_path = temp_file.name

    # Verify the file was created
    assert os.path.exists(log_file_path), "Temporary file should exist"

    # Verify the file has the expected naming pattern
    filename = os.path.basename(log_file_path)
    assert filename.startswith("fapilog_multi_sink_"), "Should have correct prefix"
    assert filename.endswith(".log"), "Should have correct suffix"

    # Verify the file is writable (was opened in w+ mode)
    with open(log_file_path, "w") as f:
        f.write("test content")

    # Verify content was written
    with open(log_file_path) as f:
        content = f.read()
        assert content == "test content", "File should be writable"

    # Clean up (same pattern as in the fixed code)
    try:
        if os.path.exists(log_file_path):
            os.unlink(log_file_path)
    except OSError:
        pass

    # Verify cleanup
    assert not os.path.exists(log_file_path), "File should be cleaned up"


def test_no_insecure_tempfile_usage():
    """Test that examples/14_multiple_sinks.py doesn't use tempfile.mktemp()."""
    example_file = Path("examples/14_multiple_sinks.py")
    assert example_file.exists(), "Example file should exist"

    content = example_file.read_text()

    # Verify no insecure tempfile.mktemp() usage
    assert "tempfile.mktemp" not in content, "Should not use insecure tempfile.mktemp()"

    # Verify secure NamedTemporaryFile usage
    assert "NamedTemporaryFile" in content, "Should use secure NamedTemporaryFile"
    assert "delete=False" in content, "Should use delete=False for manual cleanup"


if __name__ == "__main__":
    test_secure_temporary_file_creation()
    test_no_insecure_tempfile_usage()
    print("✅ All security fix tests passed!")
