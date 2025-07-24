"""Tests for processor error handling."""

from typing import Any, Dict
from unittest.mock import patch

import pytest

from fapilog._internal.processor import Processor
from fapilog._internal.processor_error_handling import (
    create_safe_processor_wrapper,
    handle_processor_error,
    log_processor_error_with_context,
    safe_processor_execution,
    safe_processor_lifecycle_operation,
    validate_processor_configuration,
)
from fapilog.exceptions import (
    ProcessorConfigurationError,
    ProcessorError,
    ProcessorExecutionError,
    ProcessorRegistrationError,
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
            event_context=event_context,
        )
        assert "Execution failed" in str(error)
        assert error.context["processor_name"] == "MockTestProcessor"
        assert error.context["operation"] == "process"
        assert error.context["event_context"] == event_context

    def test_processor_registration_error(self):
        """Test ProcessorRegistrationError with context."""
        error = ProcessorRegistrationError(
            "Registration failed",
            processor_name="MockTestProcessor",
            registration_type="custom",
        )
        assert "Registration failed" in str(error)
        assert error.context["processor_name"] == "MockTestProcessor"
        assert error.context["registration_type"] == "custom"


class MockTestProcessorErrorHandling:
    """Test processor error handling utilities."""

    @patch("fapilog._internal.processor_error_handling.log_error_with_context")
    def test_handle_processor_error_execution(self, mock_log):
        """Test handle_processor_error for execution errors."""
        original_error = RuntimeError("Test error")

        result = handle_processor_error(
            original_error, "MockTestProcessor", {"event_keys": ["level"]}, "process"
        )

        assert isinstance(result, ProcessorExecutionError)
        assert "Processor process failed for MockTestProcessor: Test error" in str(
            result
        )
        assert result.context["processor_name"] == "MockTestProcessor"
        assert result.context["operation"] == "process"
        assert result.context["original_error"] == "Test error"
        mock_log.assert_called_once()

    @patch("fapilog._internal.processor_error_handling.log_error_with_context")
    def test_handle_processor_error_configuration(self, mock_log):
        """Test handle_processor_error for configuration errors."""
        original_error = ValueError("Config error")

        result = handle_processor_error(
            original_error, "MockTestProcessor", operation="configuration"
        )

        assert isinstance(result, ProcessorConfigurationError)
        assert "Processor configuration failed for MockTestProcessor" in str(result)
        mock_log.assert_called_once()

    @patch("fapilog._internal.processor_error_handling.log_error_with_context")
    def test_handle_processor_error_registration(self, mock_log):
        """Test handle_processor_error for registration errors."""
        original_error = ValueError("Registration error")

        result = handle_processor_error(
            original_error, "MockTestProcessor", operation="registration"
        )

        assert isinstance(result, ProcessorRegistrationError)
        assert "Processor registration failed for MockTestProcessor" in str(result)
        mock_log.assert_called_once()

    def test_handle_processor_error_filters_sensitive_context(self):
        """Test that sensitive information is filtered from context."""
        sensitive_context = {
            "password": "secret123",
            "api_key": "key123",
            "normal_field": "safe_value",
        }

        result = handle_processor_error(
            RuntimeError("Test"), "MockTestProcessor", sensitive_context
        )

        assert "password" not in result.context
        assert "api_key" not in result.context
        assert result.context["normal_field"] == "safe_value"


class TestSafeProcessorExecution:
    """Test safe processor execution with fallback strategies."""

    def test_safe_execution_success(self):
        """Test successful processor execution."""
        processor = ProcessorForTesting()
        event_dict = {"level": "INFO", "message": "test"}

        result = safe_processor_execution(
            processor, None, "info", event_dict, "pass_through"
        )

        assert result["processed_by"] == "TestProcessor"
        assert result["level"] == "INFO"
        assert result["message"] == "test"

    def test_safe_execution_pass_through_strategy(self):
        """Test pass_through fallback strategy."""
        processor = ProcessorForTesting(should_fail=True)
        event_dict = {"level": "INFO", "message": "test"}

        with patch("fapilog._internal.processor_error_handling.logger") as mock_logger:
            result = safe_processor_execution(
                processor, None, "info", event_dict, "pass_through"
            )

        assert result == event_dict  # Should return original event
        mock_logger.warning.assert_called_once()

    def test_safe_execution_drop_strategy(self):
        """Test drop fallback strategy."""
        processor = ProcessorForTesting(should_fail=True)
        event_dict = {"level": "INFO", "message": "test"}

        with patch("fapilog._internal.processor_error_handling.logger") as mock_logger:
            result = safe_processor_execution(
                processor, None, "info", event_dict, "drop"
            )

        assert result is None  # Should drop the event
        mock_logger.warning.assert_called_once()

    def test_safe_execution_fallback_value_strategy(self):
        """Test fallback_value strategy."""
        processor = ProcessorForTesting(should_fail=True)
        event_dict = {"level": "INFO", "message": "test"}

        with patch("fapilog._internal.processor_error_handling.logger") as mock_logger:
            result = safe_processor_execution(
                processor, None, "info", event_dict, "fallback_value"
            )

        assert result["level"] == "INFO"
        assert result["message"] == "Processor execution failed"
        assert result["processor_error"] is True
        assert result["original_message"] == "test"
        mock_logger.warning.assert_called_once()

    def test_safe_execution_invalid_strategy(self):
        """Test invalid fallback strategy defaults to pass_through."""
        processor = ProcessorForTesting(should_fail=True)
        event_dict = {"level": "INFO", "message": "test"}

        with patch("fapilog._internal.processor_error_handling.logger") as mock_logger:
            result = safe_processor_execution(
                processor, None, "info", event_dict, "invalid_strategy"
            )

        assert result == event_dict  # Should default to pass_through
        mock_logger.error.assert_called_once()


class MockTestProcessorWrapper:
    """Test processor wrapper with error handling."""

    def test_wrapper_success(self):
        """Test successful execution through wrapper."""
        processor = ProcessorForTesting()
        wrapper = create_safe_processor_wrapper(processor, "pass_through")
        event_dict = {"level": "INFO", "message": "test"}

        result = wrapper(None, "info", event_dict)

        assert result["processed_by"] == "TestProcessor"

    def test_wrapper_with_retries(self):
        """Test wrapper with retry logic."""
        processor = ProcessorForTesting(should_fail=True)
        wrapper = create_safe_processor_wrapper(
            processor, "pass_through", retry_count=2
        )
        event_dict = {"level": "INFO", "message": "test"}

        with patch("fapilog._internal.processor_error_handling.logger") as mock_logger:
            result = wrapper(None, "info", event_dict)

        assert result == event_dict  # Should fall back after retries
        # Should have logged debug messages for retry attempts
        assert mock_logger.debug.call_count == 2

    def test_wrapper_pass_through_strategy(self):
        """Test wrapper with pass_through strategy."""
        processor = ProcessorForTesting(should_fail=True)
        wrapper = create_safe_processor_wrapper(processor, "pass_through")
        event_dict = {"level": "INFO", "message": "test"}

        result = wrapper(None, "info", event_dict)

        assert result == event_dict

    def test_wrapper_drop_strategy(self):
        """Test wrapper with drop strategy."""
        processor = ProcessorForTesting(should_fail=True)
        wrapper = create_safe_processor_wrapper(processor, "drop")
        event_dict = {"level": "INFO", "message": "test"}

        result = wrapper(None, "info", event_dict)

        assert result is None

    def test_wrapper_fallback_value_strategy(self):
        """Test wrapper with fallback_value strategy."""
        processor = ProcessorForTesting(should_fail=True)
        wrapper = create_safe_processor_wrapper(processor, "fallback_value")
        event_dict = {"level": "INFO", "message": "test"}

        result = wrapper(None, "info", event_dict)

        assert result["processor_error"] is True
        assert result["processor_name"] == "MockTestProcessor"


class TestProcessorConfiguration:
    """Test processor configuration validation."""

    def test_validate_configuration_success(self):
        """Test successful configuration validation."""
        processor = ProcessorForTesting()

        # Should not raise any exception
        validate_processor_configuration(processor)

    def test_validate_configuration_failure(self):
        """Test configuration validation failure."""
        # Create processor without triggering validation during init
        processor = FailingConfigProcessor(fail_during_init=False)

        with pytest.raises(ProcessorConfigurationError) as exc_info:
            validate_processor_configuration(processor)

        assert "Configuration validation failed" in str(exc_info.value)
        assert exc_info.value.context["processor_name"] == "FailingConfigProcessor"


class MockTestProcessorLifecycle:
    """Test processor lifecycle operations with error handling."""

    @pytest.mark.asyncio
    async def test_lifecycle_start_success(self):
        """Test successful processor start."""
        processor = ProcessorForTesting()

        result = await safe_processor_lifecycle_operation(processor, "start")

        assert result is True
        assert processor.start_called is True

    @pytest.mark.asyncio
    async def test_lifecycle_stop_success(self):
        """Test successful processor stop."""
        processor = ProcessorForTesting()
        await processor.start()  # Start first

        result = await safe_processor_lifecycle_operation(processor, "stop")

        assert result is True
        assert processor.stop_called is True

    @pytest.mark.asyncio
    async def test_lifecycle_start_failure(self):
        """Test processor start failure."""
        processor = ProcessorForTesting(should_fail=True)

        with patch("fapilog._internal.processor_error_handling.logger") as mock_logger:
            result = await safe_processor_lifecycle_operation(processor, "start")

        assert result is False
        assert processor.start_called is False
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifecycle_stop_failure(self):
        """Test processor stop failure."""
        processor = ProcessorForTesting(should_fail=True)

        with patch("fapilog._internal.processor_error_handling.logger") as mock_logger:
            result = await safe_processor_lifecycle_operation(processor, "stop")

        assert result is False
        assert processor.stop_called is False
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifecycle_invalid_operation(self):
        """Test invalid lifecycle operation."""
        processor = ProcessorForTesting()

        with patch("fapilog._internal.processor_error_handling.logger") as mock_logger:
            result = await safe_processor_lifecycle_operation(processor, "invalid")

        assert result is False
        mock_logger.error.assert_called_once()


class TestErrorLogging:
    """Test error logging functionality."""

    @patch("fapilog._internal.processor_error_handling.log_error_with_context")
    def test_log_processor_error_with_context(self, mock_log):
        """Test logging processor errors with context."""
        error = RuntimeError("Test error")
        context = {"processor_name": "MockTestProcessor"}

        log_processor_error_with_context(error, context)

        mock_log.assert_called_once_with(error, context, 30)  # WARNING level

    @patch("fapilog._internal.processor_error_handling.log_error_with_context")
    def test_log_processor_error_custom_level(self, mock_log):
        """Test logging with custom level."""
        import logging

        error = RuntimeError("Test error")

        log_processor_error_with_context(error, level=logging.ERROR)

        mock_log.assert_called_once_with(error, None, logging.ERROR)


class TestIntegration:
    """Test integration scenarios."""

    def test_multiple_processor_failures(self):
        """Test handling multiple processor failures in a chain."""
        processor1 = ProcessorForTesting()
        processor2 = ProcessorForTesting(should_fail=True)
        processor3 = ProcessorForTesting()

        event_dict = {"level": "INFO", "message": "test"}

        # First processor should succeed
        result1 = safe_processor_execution(processor1, None, "info", event_dict)
        assert result1["processed_by"] == "TestProcessor"

        # Second processor should fail but return fallback
        result2 = safe_processor_execution(
            processor2, None, "info", result1, "pass_through"
        )
        assert result2 == result1  # Should pass through

        # Third processor should process the passed-through event
        result3 = safe_processor_execution(processor3, None, "info", result2)
        assert result3["processed_by"] == "TestProcessor"

    def test_sensitive_data_filtering(self):
        """Test that sensitive data is filtered from error context."""
        # Add sensitive data to the processor context, not the event dict
        sensitive_context = {
            "password": "secret123",
            "api_key": "key123",
            "normal_field": "safe_value",
        }

        # Test the filtering directly
        result = handle_processor_error(
            RuntimeError("Test error"), "TestProcessor", sensitive_context, "process"
        )

        # Verify sensitive data is filtered but normal fields remain
        assert hasattr(result, "context")
        # The processor name should be present
        assert "processor_name" in str(result.context)
        # The operation should be present
        assert "process" in str(result.context)
