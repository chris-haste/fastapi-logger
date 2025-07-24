"""Evaluate conditions for enricher enablement."""

import logging
import os
from typing import Any, Dict

from .enricher_registry import EnricherMetadata


class EnricherConditions:
    """Evaluate conditions for enricher enablement."""

    @staticmethod
    def should_enable_enricher(
        metadata: EnricherMetadata, context: Dict[str, Any]
    ) -> bool:
        """Check if enricher should be enabled based on conditions.

        Args:
            metadata: Enricher metadata containing conditions
            context: Current execution context

        Returns:
            True if enricher should be enabled, False otherwise
        """
        conditions = metadata.conditions

        if not conditions:
            # No conditions means always enabled
            return True

        # Environment-based conditions
        if not _check_environment_condition(conditions, context):
            return False

        # Log level conditions
        if not _check_log_level_condition(conditions, context):
            return False

        # Runtime conditions (custom functions)
        if not _check_runtime_condition(conditions, context):
            return False

        # Feature flag conditions
        if not _check_feature_flag_condition(conditions, context):
            return False

        # Time-based conditions
        if not _check_time_condition(conditions, context):
            return False

        # Request-based conditions
        if not _check_request_condition(conditions, context):
            return False

        return True

    @staticmethod
    def evaluate_condition_expression(expression: str, context: Dict[str, Any]) -> bool:
        """Evaluate a condition expression safely.

        Args:
            expression: Python expression to evaluate
            context: Variables available in the expression

        Returns:
            Result of expression evaluation

        Note:
            This is a simplified implementation. In production,
            consider using a proper expression language like
            Python's ast module for safety.
        """
        try:
            # Simple expression evaluation - can be enhanced
            # For safety, we limit available functions and variables
            safe_context = {
                "context": context,
                "env": os.environ.get,
                "has_key": lambda key: key in context,
                "get": context.get,
                # Math functions
                "min": min,
                "max": max,
                "len": len,
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
            }
            return bool(eval(expression, {"__builtins__": {}}, safe_context))
        except Exception as e:
            # Log the error and default to False
            logger = logging.getLogger(__name__)
            logger.debug(f"Failed to evaluate condition expression '{expression}': {e}")
            return False


def _check_environment_condition(
    conditions: Dict[str, Any], context: Dict[str, Any]
) -> bool:
    """Check environment-based condition."""
    if "environment" not in conditions:
        return True

    required_envs = conditions["environment"]
    if isinstance(required_envs, str):
        required_envs = [required_envs]

    current_env = context.get("environment", os.getenv("ENVIRONMENT", "development"))
    return current_env in required_envs


def _check_log_level_condition(
    conditions: Dict[str, Any], context: Dict[str, Any]
) -> bool:
    """Check log level condition."""
    if "min_level" not in conditions:
        return True

    min_level = conditions["min_level"]
    current_level = context.get("level", "INFO")

    # Define level hierarchy
    level_hierarchy = {
        "DEBUG": 10,
        "INFO": 20,
        "WARNING": 30,
        "WARN": 30,
        "ERROR": 40,
        "CRITICAL": 50,
        "FATAL": 50,
    }

    min_level_num = level_hierarchy.get(min_level.upper(), 20)
    current_level_num = level_hierarchy.get(current_level.upper(), 20)

    return current_level_num >= min_level_num


def _check_runtime_condition(
    conditions: Dict[str, Any], context: Dict[str, Any]
) -> bool:
    """Check runtime/custom function condition."""
    if "condition_func" not in conditions:
        return True

    condition_func = conditions["condition_func"]

    if callable(condition_func):
        try:
            return bool(condition_func(context))
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.debug(f"Runtime condition function failed: {e}")
            return False

    return True


def _check_feature_flag_condition(
    conditions: Dict[str, Any], context: Dict[str, Any]
) -> bool:
    """Check feature flag condition."""
    if "feature_flags" not in conditions:
        return True

    required_flags = conditions["feature_flags"]
    if isinstance(required_flags, str):
        required_flags = [required_flags]

    # Check each required flag
    for flag in required_flags:
        # Try context first, then environment variable
        flag_value = context.get(
            f"feature_{flag}", os.getenv(f"FEATURE_{flag.upper()}", "false")
        )

        # Convert to boolean
        if isinstance(flag_value, str):
            flag_enabled = flag_value.lower() in ("true", "1", "yes", "on")
        else:
            flag_enabled = bool(flag_value)

        if not flag_enabled:
            return False

    return True


def _check_time_condition(conditions: Dict[str, Any], context: Dict[str, Any]) -> bool:
    """Check time-based condition."""
    if "time_range" not in conditions:
        return True

    time_range = conditions["time_range"]

    # Simple time range check (hour-based)
    if "start_hour" in time_range and "end_hour" in time_range:
        import datetime

        current_hour = datetime.datetime.now().hour
        start_hour = time_range["start_hour"]
        end_hour = time_range["end_hour"]

        if start_hour <= end_hour:
            # Same day range
            return start_hour <= current_hour <= end_hour
        else:
            # Overnight range (e.g., 22:00 to 06:00)
            return current_hour >= start_hour or current_hour <= end_hour

    return True


def _check_request_condition(
    conditions: Dict[str, Any], context: Dict[str, Any]
) -> bool:
    """Check request-based condition."""
    if "request" not in conditions:
        return True

    request_conditions = conditions["request"]

    # Check HTTP method
    if "methods" in request_conditions:
        allowed_methods = request_conditions["methods"]
        if isinstance(allowed_methods, str):
            allowed_methods = [allowed_methods]

        current_method = context.get("method", context.get("http_method", ""))
        if current_method and current_method.upper() not in [
            m.upper() for m in allowed_methods
        ]:
            return False

    # Check path patterns
    if "path_patterns" in request_conditions:
        import re

        patterns = request_conditions["path_patterns"]
        if isinstance(patterns, str):
            patterns = [patterns]

        current_path = context.get("path", context.get("url_path", ""))
        if current_path:
            for pattern in patterns:
                if re.match(pattern, current_path):
                    break
            else:
                # No pattern matched
                return False

    # Check user roles
    if "user_roles" in request_conditions:
        required_roles = request_conditions["user_roles"]
        if isinstance(required_roles, str):
            required_roles = [required_roles]

        user_roles = context.get("user_roles", [])
        if isinstance(user_roles, str):
            user_roles = [user_roles]

        # Check if user has any of the required roles
        if not any(role in user_roles for role in required_roles):
            return False

    return True


def _should_enable_for_level(current_level: str, min_level: str) -> bool:
    """Check if enricher should be enabled for given log level.

    Args:
        current_level: Current log level
        min_level: Minimum required level

    Returns:
        True if current level meets minimum requirement
    """
    level_hierarchy = {
        "DEBUG": 10,
        "INFO": 20,
        "WARNING": 30,
        "WARN": 30,
        "ERROR": 40,
        "CRITICAL": 50,
        "FATAL": 50,
    }

    min_level_num = level_hierarchy.get(min_level.upper(), 20)
    current_level_num = level_hierarchy.get(current_level.upper(), 20)

    return current_level_num >= min_level_num
