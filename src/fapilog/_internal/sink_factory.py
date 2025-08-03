"""Sink factory functions for creating sinks from URIs.

This module provides factory functions for creating sink instances from URI strings,
supporting both built-in and custom registered sinks.
"""

import urllib.parse
from typing import Any, Dict

from ..exceptions import SinkConfigurationError
from ..sinks import Sink
from .sink_registry import SinkRegistry


def create_custom_sink_from_uri(uri: str) -> Sink:
    """Create a custom sink instance from a URI.

    Args:
        uri: URI string in format: scheme://[user:pass@]host[:port]/path[?param=value]

    Returns:
        Configured sink instance

    Raises:
        SinkConfigurationError: If URI is invalid or sink is not registered

    Example:
        uri = "postgres://user:pass@localhost:5432/logs?pool_size=10"
        sink = create_custom_sink_from_uri(uri)
    """
    try:
        parsed = urllib.parse.urlparse(uri)
    except Exception as e:
        raise SinkConfigurationError(
            f"Invalid URI format: {e}", "unknown", {"uri": uri}
        ) from e

    if not parsed.scheme:
        raise SinkConfigurationError(
            "URI must have a scheme (e.g., postgres://...)", "unknown", {"uri": uri}
        )

    # Get registered sink class
    sink_class = SinkRegistry.get(parsed.scheme)
    if not sink_class:
        available_sinks = list(SinkRegistry.list().keys())
        available_str = ", ".join(available_sinks) if available_sinks else "none"
        raise SinkConfigurationError(
            f"Unknown sink type '{parsed.scheme}'. "
            f"Available custom sinks: {available_str}",
            parsed.scheme,
            {"uri": uri},
        )

    # Parse URI parameters
    kwargs = _parse_uri_parameters(parsed)

    try:
        return sink_class(**kwargs)
    except Exception as e:
        raise SinkConfigurationError(
            f"Failed to create {parsed.scheme} sink: {e}", parsed.scheme, {"uri": uri}
        ) from e


def _parse_uri_parameters(parsed: urllib.parse.ParseResult) -> Dict[str, Any]:
    """Parse URI into parameters for sink constructor.

    Args:
        parsed: Parsed URI components

    Returns:
        Dictionary of parameters for sink constructor
    """
    params = {}

    # Extract basic connection components
    if parsed.hostname:
        params["host"] = parsed.hostname

    if parsed.port:
        params["port"] = parsed.port

    if parsed.username:
        params["username"] = parsed.username

    if parsed.password:
        params["password"] = parsed.password

    # Extract path as database/target if present
    if parsed.path and parsed.path != "/":
        # Remove leading slash
        path = parsed.path.lstrip("/")
        if path:
            params["database"] = path

    # Parse query parameters
    if parsed.query:
        query_params = urllib.parse.parse_qs(parsed.query)
        for key, values in query_params.items():
            # Take the first value for each parameter
            if values:
                value = values[0]
                # Try to convert to appropriate types
                params[key] = _convert_parameter_value(value)

    return params


def _convert_parameter_value(value: str) -> Any:
    """Convert string parameter value to appropriate type.

    Args:
        value: String value from URI parameter

    Returns:
        Converted value (bool, int, float, or original string)
    """
    # Handle boolean values
    if value.lower() in ("true", "yes", "1", "on"):
        return True
    elif value.lower() in ("false", "no", "0", "off"):
        return False

    # Try to convert to number
    try:
        # Try integer first
        if "." not in value:
            return int(value)
        else:
            return float(value)
    except ValueError:
        # Return as string if conversion fails
        return value
