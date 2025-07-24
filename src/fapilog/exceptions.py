"""Custom exception classes for fapilog error handling."""

from typing import Any, Dict, Optional


class FapilogError(Exception):
    """Base exception class for all fapilog errors."""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable error message
            context: Optional context dictionary for debugging
        """
        super().__init__(message)
        self.message = message
        # Ensure context is always a dict
        if context is None or not isinstance(context, dict):
            self.context = {}
        else:
            self.context = context

    def __str__(self) -> str:
        if self.context:
            # Expand dict values for user-friendly output
            context_items = []
            for k, v in self.context.items():
                if isinstance(v, dict):
                    context_items.extend([f"{ik}={iv}" for ik, iv in v.items()])
                else:
                    context_items.append(f"{k}={v}")
            context_str = ", ".join(context_items)
            return f"{self.message} (context: {context_str})"
        return self.message


class ConfigurationError(FapilogError):
    """Raised when there are configuration issues."""

    def __init__(
        self,
        message: str,
        setting: Optional[str] = None,
        value: Any = None,
        expected_type: Optional[str] = None,
    ) -> None:
        """Initialize configuration error.

        Args:
            message: Human-readable error message
            setting: Name of the problematic setting
            value: Value that caused the error
            expected_type: Expected type or format
        """
        context = {}
        if setting:
            context["setting"] = setting
        if value is not None:
            context["value"] = value
        if expected_type is not None:
            context["expected_type"] = expected_type
        super().__init__(message, context)


class SinkError(FapilogError):
    """Raised when there are sink-related errors."""

    def __init__(
        self,
        message: str,
        sink_type: Optional[str] = None,
        sink_config: Optional[Dict[str, Any]] = None,
        operation: Optional[str] = None,
    ) -> None:
        """Initialize sink error.

        Args:
            message: Human-readable error message
            sink_type: Type of sink that failed
            sink_config: Configuration that caused the error
            operation: Operation that failed (e.g., "write", "flush", "close")
        """
        context = {}
        if sink_type:
            context["sink_type"] = sink_type
        if sink_config:
            # Filter sensitive fields
            safe_config = {
                k: v
                for k, v in sink_config.items()
                if k not in ["password", "token", "secret", "key", "api_key"]
            }
            context["sink_config"] = safe_config
        if operation:
            context["operation"] = operation
        super().__init__(message, context)

    def __str__(self) -> str:
        if self.context:
            # Expand dict values for user-friendly output
            context_items = []
            for k, v in self.context.items():
                if isinstance(v, dict):
                    context_items.extend([f"{ik}={iv}" for ik, iv in v.items()])
                else:
                    context_items.append(f"{k}={v}")
            context_str = ", ".join(context_items)
            return f"{self.message} (context: {context_str})"
        return self.message


class QueueError(FapilogError):
    """Raised when there are queue-related errors."""

    def __init__(
        self,
        message: str,
        queue_state: Optional[Dict[str, Any]] = None,
        operation: Optional[str] = None,
    ) -> None:
        """Initialize queue error.

        Args:
            message: Human-readable error message
            queue_state: Current state of the queue when error occurred
            operation: Operation that failed (e.g., "enqueue", "process", "shutdown")
        """
        context = {}
        if queue_state:
            context["queue_state"] = queue_state
        if operation:
            context["operation"] = operation
        super().__init__(message, context)

    def __str__(self) -> str:
        if self.context:
            context_items = []
            for k, v in self.context.items():
                if isinstance(v, dict):
                    context_items.extend([f"{ik}={iv}" for ik, iv in v.items()])
                else:
                    context_items.append(f"{k}={v}")
            context_str = ", ".join(context_items)
            return f"{self.message} (context: {context_str})"
        return self.message


class MiddlewareError(FapilogError):
    """Raised when there are middleware-related errors."""

    def __init__(
        self,
        message: str,
        request_info: Optional[Dict[str, Any]] = None,
        operation: Optional[str] = None,
    ) -> None:
        """Initialize middleware error.

        Args:
            message: Human-readable error message
            request_info: Information about the request that caused the error
            operation: Operation that failed
        """
        context = {}
        if request_info:
            context["request_info"] = request_info
        if operation:
            context["operation"] = operation
        super().__init__(message, context)

    def __str__(self) -> str:
        if self.context:
            context_items = []
            for k, v in self.context.items():
                if isinstance(v, dict):
                    context_items.extend([f"{ik}={iv}" for ik, iv in v.items()])
                else:
                    context_items.append(f"{k}={v}")
            context_str = ", ".join(context_items)
            return f"{self.message} (context: {context_str})"
        return self.message


class RedactionError(FapilogError):
    """Raised when there are redaction-related errors."""

    def __init__(
        self, message: str, field: Optional[str] = None, pattern: Optional[str] = None
    ) -> None:
        """Initialize redaction error.

        Args:
            message: Human-readable error message
            field: Field that failed to redact
            pattern: Pattern that caused the error
        """
        context = {}
        if field:
            context["field"] = field
        if pattern:
            context["pattern"] = pattern
        super().__init__(message, context)


class ContextError(FapilogError):
    """Raised when there are context-related errors."""

    def __init__(
        self,
        message: str,
        context_key: Optional[str] = None,
        operation: Optional[str] = None,
    ) -> None:
        """Initialize context error.

        Args:
            message: Human-readable error message
            context_key: Context key that caused the error
            operation: Operation that failed
        """
        context = {}
        if context_key:
            context["context_key"] = context_key
        if operation:
            context["operation"] = operation
        super().__init__(message, context)


class ProcessorError(FapilogError):
    """Base exception for processor-related errors."""


class ProcessorConfigurationError(ProcessorError):
    """Processor configuration is invalid."""

    def __init__(
        self,
        message: str,
        processor_name: Optional[str] = None,
        setting: Optional[str] = None,
        value: Any = None,
    ) -> None:
        """Initialize processor configuration error.

        Args:
            message: Human-readable error message
            processor_name: Name of the processor that failed
            setting: Configuration setting that caused the error
            value: Value that caused the error
        """
        context = {}
        if processor_name:
            context["processor_name"] = processor_name
        if setting:
            context["setting"] = setting
        if value is not None:
            context["value"] = value
        super().__init__(message, context)


class ProcessorExecutionError(ProcessorError):
    """Processor execution failed."""

    def __init__(
        self,
        message: str,
        processor_name: Optional[str] = None,
        operation: Optional[str] = None,
        event_context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize processor execution error.

        Args:
            message: Human-readable error message
            processor_name: Name of the processor that failed
            operation: Operation that failed (e.g., "process", "start", "stop")
            event_context: Context about the event being processed
        """
        context = {}
        if processor_name:
            context["processor_name"] = processor_name
        if operation:
            context["operation"] = operation
        if event_context:
            context["event_context"] = event_context
        super().__init__(message, context)


class ProcessorRegistrationError(ProcessorError):
    """Processor registration failed."""

    def __init__(
        self,
        message: str,
        processor_name: Optional[str] = None,
        registration_type: Optional[str] = None,
    ) -> None:
        """Initialize processor registration error.

        Args:
            message: Human-readable error message
            processor_name: Name of the processor that failed to register
            registration_type: Type of registration that failed
        """
        context = {}
        if processor_name:
            context["processor_name"] = processor_name
        if registration_type:
            context["registration_type"] = registration_type
        super().__init__(message, context)
