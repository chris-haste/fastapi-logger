"""Internal utilities for fapilog."""

import datetime
import decimal
import json
import threading
import uuid
from collections.abc import Mapping, Sequence
from typing import Any, Optional, Set, Union

import structlog


def get_logger(name: Optional[str] = None) -> structlog.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Optional logger name

    Returns:
        A structured logger instance
    """
    return structlog.get_logger(name)  # type: ignore[no-any-return]


# Thread-local storage for circular reference tracking
_thread_local = threading.local()


def _get_seen_objects() -> Set[int]:
    """Get thread-local set for tracking seen object IDs."""
    if not hasattr(_thread_local, "seen_objects"):
        _thread_local.seen_objects = set()
    return _thread_local.seen_objects


def _clear_seen_objects() -> None:
    """Clear thread-local seen objects set."""
    if hasattr(_thread_local, "seen_objects"):
        _thread_local.seen_objects.clear()


def safe_json_serialize(
    obj: Any,
    max_depth: int = 10,
    max_size: int = 1024 * 1024,  # 1MB default
    fallback_repr: str = "<non-serializable>",
    ensure_ascii: bool = False,
    sort_keys: bool = False,
    indent: Optional[Union[int, str]] = None,
) -> str:
    """Safely serialize objects to JSON with comprehensive error handling.

    This function handles circular references, non-serializable types, and
    provides configurable limits to prevent memory issues.

    Args:
        obj: The object to serialize
        max_depth: Maximum recursion depth (default: 10)
        max_size: Maximum output size in bytes (default: 1MB)
        fallback_repr: Fallback representation for non-serializable objects
        ensure_ascii: Whether to escape non-ASCII characters (default: False)
        sort_keys: Whether to sort dictionary keys (default: False)
        indent: JSON indentation (None for compact output)

    Returns:
        JSON string representation of the object

    Raises:
        ValueError: If max_size is exceeded
    """
    # Clear any previous tracking state
    _clear_seen_objects()

    try:
        # First pass: convert to safe representation
        safe_obj = _make_json_safe(obj, max_depth, fallback_repr)

        # Second pass: serialize to JSON
        result = json.dumps(
            safe_obj,
            ensure_ascii=ensure_ascii,
            sort_keys=sort_keys,
            indent=indent,
            separators=(",", ":") if indent is None else None,
        )

        # Check size limit
        if len(result.encode("utf-8")) > max_size:
            # Try to create a truncated version
            truncated_msg = f"<truncated: exceeded {max_size} bytes>"
            if isinstance(obj, dict):
                # For dicts, try to preserve some key information
                safe_obj = {
                    "_truncated": True,
                    "_original_type": type(obj).__name__,
                    "_size_exceeded": max_size,
                    "_sample_keys": list(obj.keys())[:5]
                    if hasattr(obj, "keys")
                    else [],
                }
            elif isinstance(obj, (list, tuple)):
                # For sequences, show length and some samples
                safe_obj = {
                    "_truncated": True,
                    "_original_type": type(obj).__name__,
                    "_size_exceeded": max_size,
                    "_length": len(obj) if hasattr(obj, "__len__") else "unknown",
                }
            else:
                safe_obj = truncated_msg

            result = json.dumps(safe_obj, ensure_ascii=ensure_ascii)

        return result

    finally:
        # Always clean up tracking state
        _clear_seen_objects()


def _make_json_safe(
    obj: Any, max_depth: int, fallback_repr: str, current_depth: int = 0
) -> Any:
    """Convert an object to a JSON-safe representation.

    Args:
        obj: The object to convert
        max_depth: Maximum recursion depth
        fallback_repr: Fallback representation for non-serializable objects
        current_depth: Current recursion depth

    Returns:
        JSON-safe representation of the object
    """
    # Check depth limit
    if current_depth > max_depth:
        return f"<max_depth_exceeded: {max_depth}>"

    # Handle None, booleans, numbers, and strings (already JSON-safe)
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj

    # Handle circular references for complex objects
    obj_id = id(obj)
    seen_objects = _get_seen_objects()

    if obj_id in seen_objects:
        return f"<circular_reference: {type(obj).__name__}>"

    # Add to seen objects for complex types
    if not isinstance(obj, (str, int, float, bool, type(None))):
        seen_objects.add(obj_id)

    try:
        # Handle common non-serializable types
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        elif isinstance(obj, datetime.date):
            return obj.isoformat()
        elif isinstance(obj, datetime.time):
            return obj.isoformat()
        elif isinstance(obj, uuid.UUID):
            return str(obj)
        elif isinstance(obj, decimal.Decimal):
            return float(obj)
        elif isinstance(obj, bytes):
            try:
                return obj.decode("utf-8")
            except UnicodeDecodeError:
                return f"<bytes: {len(obj)} bytes>"
        elif isinstance(obj, bytearray):
            try:
                return bytes(obj).decode("utf-8")
            except UnicodeDecodeError:
                return f"<bytearray: {len(obj)} bytes>"
        elif callable(obj):
            # Handle functions and methods first (before custom class check)
            return f"<function: {getattr(obj, '__name__', 'unknown')}>"
        elif hasattr(obj, "__dict__") and hasattr(obj, "__class__"):
            # Handle custom classes by converting to dict
            try:
                obj_dict = {
                    "_type": obj.__class__.__name__,
                    "_module": getattr(obj.__class__, "__module__", "unknown"),
                }
                # Add instance attributes
                for key, value in obj.__dict__.items():
                    # Skip private attributes to avoid recursion issues
                    if not key.startswith("_"):
                        obj_dict[key] = _make_json_safe(
                            value, max_depth, fallback_repr, current_depth + 1
                        )
                return obj_dict
            except Exception:
                return f"<{type(obj).__name__}: {fallback_repr}>"
        elif isinstance(obj, dict) or isinstance(obj, Mapping):
            # Handle dictionaries and mapping types
            result = {}
            for key, value in obj.items():
                # Convert key to string if it's not already
                safe_key = str(key) if not isinstance(key, str) else key
                result[safe_key] = _make_json_safe(
                    value, max_depth, fallback_repr, current_depth + 1
                )
            return result
        elif isinstance(obj, (list, tuple)) or isinstance(obj, Sequence):
            # Handle lists, tuples, and sequence types (but not strings)
            if isinstance(obj, str):
                return obj
            return [
                _make_json_safe(item, max_depth, fallback_repr, current_depth + 1)
                for item in obj
            ]
        elif isinstance(obj, set):
            # Convert sets to lists
            return [
                _make_json_safe(item, max_depth, fallback_repr, current_depth + 1)
                for item in obj
            ]

        else:
            # Try to use the object's string representation
            try:
                str_repr = str(obj)
                # Avoid infinite recursion by limiting string length
                if len(str_repr) > 200:
                    str_repr = str_repr[:200] + "..."
                return f"<{type(obj).__name__}: {str_repr}>"
            except Exception:
                return f"<{type(obj).__name__}: {fallback_repr}>"

    finally:
        # Remove from seen objects when done processing this object
        if obj_id in seen_objects:
            seen_objects.discard(obj_id)
