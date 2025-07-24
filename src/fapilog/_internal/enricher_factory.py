"""Factory for creating enrichers from URI configurations."""

from typing import Any, Dict
from urllib.parse import parse_qsl, urlparse

from ..exceptions import EnricherConfigurationError


class EnricherFactory:
    """Factory for creating enrichers from URI configurations."""

    @staticmethod
    def create_enricher_from_uri(uri: str) -> Any:
        """Create an enricher instance from URI configuration.

        Example URIs:
        - user_context://api.auth.com/user?timeout=5
        - database://localhost:5432/users?table=user_profiles
        - redis://localhost:6379/0?prefix=user:
        - environment://static?version=1.0.0&deployment=prod
        - file://logs?path=/var/log/app.log&format=json

        Args:
            uri: URI string defining the enricher configuration

        Returns:
            Configured enricher instance

        Raises:
            EnricherConfigurationError: If URI is invalid or enricher
                cannot be created
        """
        # Use shared URI validation for consistent error handling
        from .uri_validation import check_scheme_with_helpful_error

        try:
            scheme = check_scheme_with_helpful_error(uri, "enricher")
        except ValueError as e:
            raise EnricherConfigurationError(
                str(e), scheme=None, params={"uri": uri}
            ) from e

        # Parse URI for parameters
        try:
            parsed = urlparse(uri)
        except Exception as e:
            raise EnricherConfigurationError(
                f"Invalid URI format: {e}",
                scheme=None,
                params={"uri": uri, "error": str(e)},
            ) from e

        # Get registered enricher class
        from .enricher_registry import EnricherRegistry

        metadata = EnricherRegistry.get_metadata(scheme)

        if not metadata:
            available_schemes = list(EnricherRegistry.list_enrichers().keys())
            raise EnricherConfigurationError(
                f"Unknown enricher scheme: {scheme}",
                scheme=scheme,
                available_schemes=available_schemes,
                params={"uri": uri},
            )

        # Extract and validate parameters from URI
        params = _extract_uri_params(parsed)

        # Enhanced async-specific parameter handling
        if metadata.async_capable:
            # Set default timeout if not specified
            if "timeout" not in params:
                params["timeout"] = 5.0
            # Ensure timeout is a valid float and reasonable
            else:
                try:
                    timeout_value = float(params["timeout"])
                    if timeout_value <= 0:
                        raise ValueError("Timeout must be positive")
                    if timeout_value > 300:  # 5 minutes max
                        raise ValueError("Timeout too large (max 300 seconds)")
                    params["timeout"] = timeout_value
                except (ValueError, TypeError) as e:
                    raise EnricherConfigurationError(
                        (f"Invalid timeout value for async enricher {scheme}: {e}"),
                        scheme=scheme,
                        params=params,
                        error=("timeout must be a positive number ≤ 300 seconds"),
                    ) from e

        # Create enricher instance via registry (handles async wrapping)
        try:
            return EnricherRegistry.get_instance(scheme, **params)
        except Exception as e:
            raise EnricherConfigurationError(
                f"Failed to instantiate enricher {scheme}: {e}",
                scheme=scheme,
                params=params,
                error=str(e),
            ) from e

    @staticmethod
    def create_enrichers_from_uris(uris: list) -> Dict[str, Any]:
        """Create multiple enrichers from a list of URIs.

        Args:
            uris: List of URI strings

        Returns:
            Dictionary mapping scheme names to enricher instances

        Raises:
            EnricherConfigurationError: If any URI is invalid
        """
        enrichers = {}
        errors = []

        for uri in uris:
            try:
                scheme = _extract_scheme_from_uri(uri)
                enricher = EnricherFactory.create_enricher_from_uri(uri)
                enrichers[scheme] = enricher
            except EnricherConfigurationError as e:
                errors.append(f"URI '{uri}': {e}")
            except Exception as e:
                errors.append(f"URI '{uri}': Unexpected error: {e}")

        if errors:
            raise EnricherConfigurationError(
                f"Failed to create enricher from URI: {errors[0]}",
                error="; ".join(errors),
                params={"failed_uris": len(errors), "total_uris": len(uris)},
            )

        return enrichers

    @staticmethod
    def validate_enricher_uri(uri: str) -> bool:
        """Validate an enricher URI without creating the instance.

        Args:
            uri: URI string to validate

        Returns:
            True if URI is valid, False otherwise
        """
        try:
            EnricherFactory.create_enricher_from_uri(uri)
            return True
        except Exception:
            return False


def _extract_scheme_from_uri(uri: str) -> str:
    """Extract scheme from URI with error handling."""
    try:
        parsed = urlparse(uri)
        if not parsed.scheme:
            raise ValueError(f"No scheme found in URI: {uri}")
        return parsed.scheme
    except Exception as e:
        raise EnricherConfigurationError(
            f"Invalid URI format: {e}", params={"uri": uri}
        ) from e


def _extract_uri_params(parsed_uri) -> Dict[str, Any]:
    """Extract parameters from parsed URI with improved validation."""
    params = {}

    # Add hostname as host parameter if present (excluding port)
    if parsed_uri.hostname:
        params["host"] = parsed_uri.hostname

    # Add port as separate parameter if present
    if parsed_uri.port:
        params["port"] = parsed_uri.port

    # Add username and password if present
    if parsed_uri.username:
        params["username"] = parsed_uri.username
    if parsed_uri.password:
        params["password"] = parsed_uri.password

    # Add path as path parameter if present and not empty
    if parsed_uri.path and parsed_uri.path != "/":
        # Remove leading slash for cleaner parameter
        params["path"] = parsed_uri.path.lstrip("/")

    # Parse query parameters with type conversion
    if parsed_uri.query:
        query_params = parse_qsl(parsed_uri.query, keep_blank_values=True)
        for key, value in query_params:
            # Attempt basic type conversion
            if value.lower() in ("true", "false"):
                params[key] = value.lower() == "true"
            elif value.isdigit():
                params[key] = int(value)
            elif _is_float(value):
                params[key] = float(value)
            else:
                params[key] = value

    return params


def _is_float(value: str) -> bool:
    """Check if string represents a float."""
    try:
        float(value)
        return True
    except ValueError:
        return False
