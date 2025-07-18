import json
import os
import tempfile

import pytest
from fapilog.sinks.file import (
    FileSink,
    create_file_sink_from_uri,
    parse_file_uri,
)


@pytest.mark.asyncio
async def test_file_sink_writes_log():
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, "test.log")
        sink = FileSink(log_path)
        event = {"msg": "hello", "level": "info"}
        await sink.write(event)
        sink.close()
        with open(log_path, encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["msg"] == "hello"
        assert data["level"] == "info"


@pytest.mark.asyncio
async def test_rotation_behavior():
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, "rotate.log")
        # Set maxBytes very small to force rotation
        sink = FileSink(log_path, max_bytes=50, backup_count=2)
        # Write enough events to trigger rotation
        for i in range(10):
            await sink.write({"msg": f"event-{i}", "i": i})
        sink.close()
        # Check that rotated files exist
        files = os.listdir(tmpdir)
        log_files = [f for f in files if f.startswith("rotate.log")]
        assert any(f == "rotate.log" for f in log_files)
        assert any(f.startswith("rotate.log.") for f in log_files)


@pytest.mark.asyncio
async def test_invalid_uri_handling():
    # Invalid scheme
    with pytest.raises(ValueError):
        parse_file_uri("notafile:///tmp/foo.log")
    # Missing path
    with pytest.raises(ValueError):
        parse_file_uri("file://")
    # Invalid maxBytes
    with pytest.raises(ValueError):
        parse_file_uri("file:///tmp/foo.log?maxBytes=abc")
    # Invalid backupCount
    with pytest.raises(ValueError):
        parse_file_uri("file:///tmp/foo.log?backupCount=-1")


def test_parse_file_uri_defaults_and_params():
    uri = "file:///tmp/foo.log"
    path, max_bytes, backup_count = parse_file_uri(uri)
    assert path == "/tmp/foo.log"
    assert max_bytes == 10 * 1024 * 1024
    assert backup_count == 5

    uri2 = "file:///tmp/bar.log?maxBytes=12345&backupCount=7"
    path2, max_bytes2, backup_count2 = parse_file_uri(uri2)
    assert path2 == "/tmp/bar.log"
    assert max_bytes2 == 12345
    assert backup_count2 == 7


def test_create_file_sink_from_uri(tmp_path):
    uri = f"file://{tmp_path}/my.log?maxBytes=100&backupCount=1"
    sink = create_file_sink_from_uri(uri)
    assert isinstance(sink, FileSink)
    assert sink.max_bytes == 100
    assert sink.backup_count == 1
    assert str(sink.file_path).endswith("my.log")
    sink.close()


def test_parse_file_uri_edge_cases():
    # Test Windows path handling
    uri = "file:///C:/path/to/file.log"
    path, max_bytes, backup_count = parse_file_uri(uri)
    assert path == "C:/path/to/file.log"

    # Test with empty query string (should not raise)
    uri2 = "file:///tmp/test.log?"
    path2, max_bytes2, backup_count2 = parse_file_uri(uri2)
    assert path2 == "/tmp/test.log"
    assert max_bytes2 == 10 * 1024 * 1024
    assert backup_count2 == 5

    # Test with maxBytes present but empty (should use default)
    uri3 = "file:///tmp/test.log?maxBytes="
    path3, max_bytes3, backup_count3 = parse_file_uri(uri3)
    assert path3 == "/tmp/test.log"
    assert max_bytes3 == 10 * 1024 * 1024
    assert backup_count3 == 5

    # Test with backupCount present but empty (should use default)
    uri4 = "file:///tmp/test.log?backupCount="
    path4, max_bytes4, backup_count4 = parse_file_uri(uri4)
    assert path4 == "/tmp/test.log"
    assert max_bytes4 == 10 * 1024 * 1024
    assert backup_count4 == 5


def test_file_sink_directory_creation(tmp_path):
    # Test that directories are created automatically
    log_dir = tmp_path / "logs" / "subdir"
    log_file = log_dir / "app.log"

    sink = FileSink(str(log_file))
    assert log_dir.exists()
    assert log_file.parent.exists()
    sink.close()


@pytest.mark.asyncio
async def test_file_sink_close_safety():
    # Test that close() is safe to call multiple times
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, "test.log")
        sink = FileSink(log_path)

        # Close multiple times should not raise
        sink.close()
        sink.close()
        sink.close()


def test_parse_file_uri_generic_exception_handling():
    # Test that generic exceptions are wrapped in ValueError
    # This tests the final except block in parse_file_uri
    with pytest.raises(ValueError, match="Invalid file URI"):
        # This will cause a generic exception in urlparse
        parse_file_uri("file://invalid[uri")
