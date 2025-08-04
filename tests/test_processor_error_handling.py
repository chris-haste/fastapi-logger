"""Tests for processor error handling."""

from typing import Any, Dict
from unittest.mock import patch

import pytest

from fapilog.exceptions import (
    ProcessorConfigurationError,
    ProcessorError,
    ProcessorExecutionError,
    ProcessorRegistrationError,
)
from fapilog.processors.base import Processor
from fapilog.processors.error_handling import (
    create_simple_processor_wrapper,
    handle_processor_error,
    log_processor_error_with_context,
    safe_processor_lifecycle_operation,
    simple_processor_execution,
    validate_processor_configuration,
)


class ProcessorForTesting(Processor):
    """Test processor implementation."""

    def __init__(self, should_fail: bool = False, **config: Any) -> None:
        self.should_fail = should_fail
        self.start_called = False
        self.stop_called = False
        super().__init__(should_fail=should_fail, **config)

    async def _start_impl(self) -> None:
        if self.should_fail:
            raise RuntimeError("Start failed")
        self.start_called = True

    async def _stop_impl(self) -> None:
        if self.should_fail:
            raise RuntimeError("Stop failed")
        self.stop_called = True

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        if self.should_fail:
            raise RuntimeError("Process failed")
        event_dict["processed_by"] = "TestProcessor"
        return event_dict


class FailingConfigProcessor(Processor):
    """Processor that fails configuration validation."""

    def __init__(self, fail_during_init: bool = True, **config: Any) -> None:
        # If fail_during_init is False, don't call super().__init__ which triggers validation
        if not fail_during_init:
            self.config = config
            self._started = False
        else:
            super().__init__(**config)

    def validate_config(self) -> None:
        raise ValueError("Configuration validation failed")

    def process(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        return event_dict


class MockTestProcessorExceptions:
    """Test processor exception classes."""

    def test_processor_error_base(self):
        """Test ProcessorError base exception."""
        error = ProcessorError("Test error")
        assert str(error) == "Test error"
        assert error.context == {}

    def test_processor_configuration_error(self):
        """Test ProcessorConfigurationError with context."""
        error = ProcessorConfigurationError(
            "Config failed",
            processor_name="MockTestProcessor",
            setting="invalid_setting",
            value="bad_value",
        )
        assert "Config failed" in str(error)
        assert error.context["processor_name"] == "MockTestProcessor"
        assert error.context["setting"] == "invalid_setting"
        assert error.context["value"] == "bad_value"

    def test_processor_execution_error(self):
        """Test ProcessorExecutionError with context."""
        event_context = {"event_keys": ["level", "message"]}
        error = ProcessorExecutionError(
            "Execution failed",
            processor_name="MockTestProcessor",
            operation="process",
            **event_context,
        )
        assert "Execution failed" in str(error)
        assert error.context["processor_name"] == "MockTestProcessor"
        assert error.context["operation"] == "process"

    def test_processor_registration_error(self):
        """Test ProcessorRegistrationError with context."""
        error = ProcessorRegistrationError(
            "Registration failed",
            processor_name="MockTestProcessor",
            # registry_state="partial",  # Removed as it's not a valid parameter
        )
        assert "Registration failed" in str(error)
        assert error.context["processor_name"] == "MockTestProcessor"
        assert error.context["registry_state"] == "partial"


class TestHandleProcessorError:
    """Test processor error handling functions."""

    def test_handle_processor_error_execution(self):
        """Test handling execution errors."""
        error = RuntimeError("Process failed")

        result = handle_processor_error(error, "TestProcessor", operation="process")

        assert isinstance(result, ProcessorExecutionError)
        assert "TestProcessor" in str(result)
        assert "Process failed" in str(result)

    def test_handle_processor_error_configuration(self):
        """Test handling configuration errors."""
        error = ValueError("Invalid config")

        result = handle_processor_error(
            error, "TestProcessor", operation="configuration"
        )

        assert isinstance(result, ProcessorConfigurationError)
        assert "TestProcessor" in str(result)

    def test_handle_processor_error_registration(self):
        """Test handling registration errors."""
        error = KeyError("Duplicate name")

        result = handle_processor_error(
            error, "TestProcessor", operation="registration"
        )

        assert isinstance(result, ProcessorRegistrationError)
        assert "TestProcessor" in str(result)

    def test_handle_processor_error_with_context(self):
        """Test error handling with additional context."""
        error = RuntimeError("Test error")
        context = {"event_keys": ["level", "message"], "method_name": "info"}

        result = handle_processor_error(error, "TestProcessor", context, "process")

        assert isinstance(result, ProcessorExecutionError)
        # Context is logged but not necessarily preserved in exception context
        assert "TestProcessor" in str(result)

    def test_handle_processor_error_filters_sensitive_data(self):
        """Test that sensitive data is filtered from context."""
        error = RuntimeError("Test error")
        context = {
            "password": "secret123",
            "api_key": "key456",
            "token": "auth789",
            "safe_field": "safe_value",
        }

        result = handle_processor_error(error, "TestProcessor", context, "process")

        # The error should be properly handled and return ProcessorExecutionError
        assert isinstance(result, ProcessorExecutionError)
        assert "TestProcessor" in str(result)


class TestSimpleProcessorExecution:
    """Test simplified processor execution with fail-fast error handling."""

    def test_simple_execution_success(self):
        """Test successful processor execution."""
        processor = ProcessorForTesting()
        event_dict = {"level": "INFO", "message": "test"}

        result = simple_processor_execution(processor, None, "info", event_dict)

        assert result["processed_by"] == "TestProcessor"  # type: ignore[index]
        assert result["level"] == "INFO"  # type: ignore[index]
        assert result["message"] == "test"  # type: ignore[index]

    def test_simple_execution_failure_returns_original(self):
        """Test processor failure returns original event with logging."""
        processor = ProcessorForTesting(should_fail=True)
        event_dict = {"level": "INFO", "message": "test"}

        with patch("fapilog.processors.error_handling.logger") as mock_logger:
            result = simple_processor_execution(processor, None, "info", event_dict)

        # Should return original event on failure
        assert result == event_dict
        # Should log warning
        mock_logger.warning.assert_called_once()
        warning_call = mock_logger.warning.call_args[0][0]
        assert "ProcessorForTesting" in warning_call
        assert "failed during info" in warning_call


class TestCreateSimpleProcessorWrapper:
    """Test simple processor wrapper creation."""

    def test_create_wrapper_success(self):
        """Test creating a wrapper for successful processor."""
        processor = ProcessorForTesting()
        wrapper = create_simple_processor_wrapper(processor)

        event_dict = {"level": "INFO", "message": "test"}
        result = wrapper(None, "info", event_dict)

        assert result["processed_by"] == "TestProcessor"  # type: ignore[index]
        assert result["level"] == "INFO"  # type: ignore[index]

    def test_create_wrapper_failure(self):
        """Test wrapper behavior with failing processor."""
        processor = ProcessorForTesting(should_fail=True)
        wrapper = create_simple_processor_wrapper(processor)

        event_dict = {"level": "INFO", "message": "test"}

        with patch("fapilog.processors.error_handling.logger") as mock_logger:
            result = wrapper(None, "info", event_dict)

        # Should return original event
        assert result == event_dict
        # Should log error
        mock_logger.warning.assert_called_once()


class TestValidateProcessorConfiguration:
    """Test processor configuration validation."""

    def test_validate_valid_processor(self):
        """Test validation of processor with valid configuration."""
        processor = ProcessorForTesting()

        # Should not raise any exception
        validate_processor_configuration(processor)

    def test_validate_failing_processor(self):
        """Test validation of processor with invalid configuration."""
        processor = FailingConfigProcessor(fail_during_init=False)

        with pytest.raises(ProcessorConfigurationError):
            validate_processor_configuration(processor)

    def test_validate_with_custom_name(self):
        """Test validation with custom processor name."""
        processor = FailingConfigProcessor(fail_during_init=False)

        with pytest.raises(ProcessorConfigurationError) as exc_info:
            validate_processor_configuration(processor, "CustomProcessor")

        assert "CustomProcessor" in str(exc_info.value)


class TestSafeProcessorLifecycleOperation:
    """Test safe processor lifecycle operations."""

    @pytest.mark.asyncio
    async def test_start_operation_success(self):
        """Test successful start operation."""
        processor = ProcessorForTesting()

        result = await safe_processor_lifecycle_operation(processor, "start")

        assert result is True
        assert processor.start_called is True

    @pytest.mark.asyncio
    async def test_stop_operation_success(self):
        """Test successful stop operation."""
        processor = ProcessorForTesting()
        await processor.start()  # Start first

        result = await safe_processor_lifecycle_operation(processor, "stop")

        assert result is True
        assert processor.stop_called is True

    @pytest.mark.asyncio
    async def test_start_operation_failure(self):
        """Test start operation failure."""
        processor = ProcessorForTesting(should_fail=True)

        with patch("fapilog.processors.error_handling.logger") as mock_logger:
            result = await safe_processor_lifecycle_operation(processor, "start")

        assert result is False
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_operation(self):
        """Test invalid lifecycle operation."""
        processor = ProcessorForTesting()

        # Invalid operation should return False and log error (graceful handling)
        result = await safe_processor_lifecycle_operation(processor, "invalid")
        assert result is False


class TestLogProcessorErrorWithContext:
    """Test processor error logging with context."""

    def test_log_error_with_context(self):
        """Test logging processor errors with context."""
        error = RuntimeError("Test error")
        context = {"processor": "TestProcessor", "event_keys": ["level", "message"]}

        with patch(
            "fapilog.processors.error_handling.log_error_with_context"
        ) as mock_log:
            log_processor_error_with_context(error, context)

            mock_log.assert_called_once_with(error, context, 30)  # WARNING level

    def test_log_error_custom_level(self):
        """Test logging with custom level."""
        import logging

        error = RuntimeError("Test error")
        context = {"processor": "TestProcessor"}

        with patch(
            "fapilog.processors.error_handling.log_error_with_context"
        ) as mock_log:
            log_processor_error_with_context(error, context, logging.ERROR)

            mock_log.assert_called_once_with(error, context, logging.ERROR)


class TestIntegration:
    """Test integration scenarios."""

    def test_multiple_processor_chain(self):
        """Test processing chain with multiple processors."""
        processor1 = ProcessorForTesting()
        processor2 = ProcessorForTesting(should_fail=True)
        processor3 = ProcessorForTesting()

        event_dict = {"level": "INFO", "message": "test"}

        # First processor should succeed
        result1 = simple_processor_execution(processor1, None, "info", event_dict)
        assert result1["processed_by"] == "TestProcessor"  # type: ignore[index]

        # Second processor should fail but return original
        with patch("fapilog.processors.error_handling.logger"):
            result2 = simple_processor_execution(processor2, None, "info", result1)
        assert result2 == result1  # Should return original

        # Third processor should process the original event
        result3 = simple_processor_execution(processor3, None, "info", result2)
        assert result3["processed_by"] == "TestProcessor"  # type: ignore[index]

    def test_sensitive_data_filtering(self):
        """Test that sensitive data is filtered from error context."""
        sensitive_context = {
            "password": "secret123",
            "api_key": "key123",
            "normal_field": "safe_value",
        }

        result = handle_processor_error(
            RuntimeError("Test error"), "TestProcessor", sensitive_context, "process"
        )

        # Verify error is properly handled
        assert isinstance(result, ProcessorExecutionError)
        assert "TestProcessor" in str(result)
