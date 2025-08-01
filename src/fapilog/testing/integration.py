"""Integration testing tools for sink registry."""

import asyncio
import os
from typing import Any, Dict, List, Optional, Type
from urllib.parse import urlencode

from .._internal.sink_registry import SinkRegistry
from ..settings import LoggingSettings
from ..sinks import Sink


class SinkIntegrationTester:
    """Test integration with the full logging system."""

    def __init__(self):
        self.test_app = None
        self._original_sinks = {}
        self._test_results: List[Dict[str, Any]] = []

    def _backup_sink_registry(self) -> None:
        """Backup current sink registry state."""
        self._original_sinks = SinkRegistry._sinks.copy()

    def _restore_sink_registry(self) -> None:
        """Restore original sink registry state."""
        SinkRegistry._sinks = self._original_sinks

    async def test_with_fastapi(
        self, sink_class: Type[Sink], sink_name: str = "test", **sink_kwargs: Any
    ) -> Dict[str, Any]:
        """Test sink integration with FastAPI.

        Args:
            sink_class: Sink class to test
            sink_name: Name to register the sink under
            **sink_kwargs: Sink configuration parameters

        Returns:
            Integration test results
        """
        try:
            # Import FastAPI-related modules
            from fastapi import FastAPI

            from ..bootstrap import configure_logging

            # Backup registry
            self._backup_sink_registry()

            # Create test app
            app = FastAPI(title="Sink Integration Test")

            # Register sink temporarily
            SinkRegistry.register(sink_name, sink_class)

            # Create sink URI
            if sink_kwargs:
                uri = f"{sink_name}://test?{urlencode(sink_kwargs)}"
            else:
                uri = f"{sink_name}://test"

            # Configure logging with the test sink
            logger = configure_logging(app=app, sinks=[uri])

            # Test logging through the full system
            test_messages = [
                {"level": "info", "message": "Integration test info"},
                {"level": "warning", "message": "Integration test warning"},
                {"level": "error", "message": "Integration test error"},
            ]

            for msg in test_messages:
                if msg["level"] == "info":
                    logger.info(msg["message"], test_type="integration")
                elif msg["level"] == "warning":
                    logger.warning(msg["message"], test_type="integration")
                elif msg["level"] == "error":
                    logger.error(msg["message"], test_type="integration")

            # Allow time for async processing
            await asyncio.sleep(0.1)

            result = {
                "success": True,
                "sink_name": sink_name,
                "sink_class": sink_class.__name__,
                "uri": uri,
                "messages_sent": len(test_messages),
                "app_configured": True,
                "logger_created": logger is not None,
            }

        except Exception as e:
            result = {
                "success": False,
                "error": str(e),
                "sink_name": sink_name,
                "sink_class": sink_class.__name__,
            }
        finally:
            # Restore registry
            self._restore_sink_registry()

        self._test_results.append(result)
        return result

    def test_environment_configuration(
        self, sink_class: Type[Sink], env_vars: Dict[str, str], sink_name: str = "test"
    ) -> Dict[str, Any]:
        """Test sink configuration via environment variables.

        Args:
            sink_class: Sink class to test
            env_vars: Environment variables to set
            sink_name: Name to register the sink under

        Returns:
            Environment configuration test results
        """
        original_env = {}

        try:
            # Backup and set environment variables
            for key, value in env_vars.items():
                original_env[key] = os.environ.get(key)
                os.environ[key] = value

            # Backup registry
            self._backup_sink_registry()

            # Register sink
            SinkRegistry.register(sink_name, sink_class)

            # Test configuration via environment
            settings = LoggingSettings()

            # Check if sink is properly configured
            sink_found = any(sink_name in str(sink) for sink in settings.sinks)

            result = {
                "success": True,
                "sink_name": sink_name,
                "sink_class": sink_class.__name__,
                "env_vars_set": list(env_vars.keys()),
                "sink_found_in_settings": sink_found,
                "settings_sinks": settings.sinks,
            }

        except Exception as e:
            result = {
                "success": False,
                "error": str(e),
                "sink_name": sink_name,
                "sink_class": sink_class.__name__,
                "env_vars_set": list(env_vars.keys()) if env_vars else [],
            }
        finally:
            # Restore environment
            for key, original_value in original_env.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value

            # Restore registry
            self._restore_sink_registry()

        self._test_results.append(result)
        return result

    async def test_container_integration(
        self,
        sink_class: Type[Sink],
        sink_name: str = "test",
        **sink_kwargs: Any,
    ) -> Dict[str, Any]:
        """Test sink with LoggingContainer integration.

        Args:
            sink_class: Sink class to test
            sink_name: Name to register the sink under
            **sink_kwargs: Sink configuration parameters

        Returns:
            Container integration test results
        """
        try:
            # Backup registry
            self._backup_sink_registry()

            # Register sink
            SinkRegistry.register(sink_name, sink_class)

            # Create sink URI
            if sink_kwargs:
                uri = f"{sink_name}://test?{urlencode(sink_kwargs)}"
            else:
                uri = f"{sink_name}://test"

            # Test with container
            from ..container import LoggingContainer
            from ..settings import LoggingSettings

            settings = LoggingSettings(sinks=[uri])
            container = LoggingContainer(settings)
            logger = container.configure()

            # Test logging
            logger.info("Container integration test")

            result = {
                "success": True,
                "sink_name": sink_name,
                "sink_class": sink_class.__name__,
                "sinks_count": len(container._sinks),
            }

        except Exception as e:
            result = {
                "success": False,
                "error": str(e),
                "sink_name": sink_name,
                "sink_class": sink_class.__name__,
            }
        finally:
            # Clean up container and queue worker
            if "container" in locals():
                try:
                    # Shutdown queue worker if it exists
                    if hasattr(container, "_queue_worker") and container._queue_worker:
                        container._queue_worker.shutdown_sync()
                    # Give a moment for cleanup
                    await asyncio.sleep(0.1)
                except Exception:
                    pass  # Ignore cleanup errors

            # Restore registry
            self._restore_sink_registry()

        self._test_results.append(result)
        return result

    async def test_queue_integration(
        self,
        sink_class: Type[Sink],
        sink_name: str = "test",
        queue_settings: Optional[Dict[str, Any]] = None,
        **sink_kwargs: Any,
    ) -> Dict[str, Any]:
        """Test sink with queue system integration.

        Args:
            sink_class: Sink class to test
            sink_name: Name to register the sink under
            queue_settings: Queue configuration
            **sink_kwargs: Sink configuration parameters

        Returns:
            Queue integration test results
        """
        if queue_settings is None:
            queue_settings = {
                "queue_enabled": True,
                "queue_maxsize": 100,
                "queue_batch_size": 10,
            }

        try:
            # Backup registry
            self._backup_sink_registry()

            # Register sink
            SinkRegistry.register(sink_name, sink_class)

            # Create sink URI
            if sink_kwargs:
                uri = f"{sink_name}://test?{urlencode(sink_kwargs)}"
            else:
                uri = f"{sink_name}://test"

            # Create settings with queue enabled
            settings_dict = {"sinks": [uri], **queue_settings}
            settings = LoggingSettings(**settings_dict)

            # Test with container
            from ..container import LoggingContainer

            container = LoggingContainer(settings)
            logger = container.configure()

            # Send multiple test messages
            num_messages = 25
            for i in range(num_messages):
                logger.info(f"Queue test message {i}", test_index=i)

            # Allow time for queue processing
            await asyncio.sleep(0.5)

            # Check queue worker state
            queue_worker = container._queue_worker

            result = {
                "success": True,
                "sink_name": sink_name,
                "sink_class": sink_class.__name__,
                "messages_sent": num_messages,
                "queue_enabled": settings.queue_enabled,
                "queue_worker_running": queue_worker._running
                if queue_worker
                else False,
                "queue_size": queue_worker.queue.qsize() if queue_worker else 0,
                "sinks_count": len(container._sinks),
            }

        except Exception as e:
            result = {
                "success": False,
                "error": str(e),
                "sink_name": sink_name,
                "sink_class": sink_class.__name__,
            }
        finally:
            # Clean up container and queue worker
            if "container" in locals():
                try:
                    # Shutdown queue worker if it exists
                    if hasattr(container, "_queue_worker") and container._queue_worker:
                        container._queue_worker.shutdown_sync()
                    # Give a moment for cleanup
                    await asyncio.sleep(0.1)
                except Exception:
                    pass  # Ignore cleanup errors

            # Restore registry
            self._restore_sink_registry()

        self._test_results.append(result)
        return result

    async def test_error_handling(
        self,
        sink_class: Type[Sink],
        sink_name: str = "test",
        should_fail: bool = True,
        **sink_kwargs: Any,
    ) -> Dict[str, Any]:
        """Test error handling integration.

        Args:
            sink_class: Sink class to test
            sink_name: Name to register the sink under
            should_fail: Whether the sink should fail for testing
            **sink_kwargs: Sink configuration parameters

        Returns:
            Error handling test results
        """
        try:
            # Backup registry
            self._backup_sink_registry()

            # Register sink
            SinkRegistry.register(sink_name, sink_class)

            # Create sink URI with should_fail parameter
            params = {"should_fail": should_fail, **sink_kwargs}
            if params:
                uri = f"{sink_name}://test?{urlencode(params)}"
            else:
                uri = f"{sink_name}://test"

            # Test with container
            from ..container import LoggingContainer
            from ..settings import LoggingSettings

            settings = LoggingSettings(sinks=[uri])
            container = LoggingContainer(settings)
            logger = container.configure()

            # Test logging with potential errors
            try:
                logger.error("Error handling test")
                error_occurred = False
            except Exception:
                error_occurred = True

            result = {
                "success": True,
                "sink_name": sink_name,
                "sink_class": sink_class.__name__,
                "error_occurred": error_occurred,
                "should_fail": should_fail,
            }

        except Exception as e:
            result = {
                "success": False,
                "error": str(e),
                "sink_name": sink_name,
                "sink_class": sink_class.__name__,
            }
        finally:
            # Clean up container and queue worker
            if "container" in locals():
                try:
                    # Shutdown queue worker if it exists
                    if hasattr(container, "_queue_worker") and container._queue_worker:
                        container._queue_worker.shutdown_sync()
                    # Give a moment for cleanup
                    await asyncio.sleep(0.1)
                except Exception:
                    pass  # Ignore cleanup errors

            # Restore registry
            self._restore_sink_registry()

        self._test_results.append(result)
        return result

    async def run_integration_suite(
        self, sink_class: Type[Sink], sink_name: str = "test_suite", **sink_kwargs: Any
    ) -> Dict[str, Any]:
        """Run a comprehensive integration test suite.

        Args:
            sink_class: Sink class to test
            sink_name: Name to register the sink under
            **sink_kwargs: Sink configuration parameters

        Returns:
            Complete integration test results
        """
        print(f"Running integration test suite for {sink_class.__name__}...")

        # Run all integration tests
        tests = [
            ("fastapi", self.test_with_fastapi(sink_class, sink_name, **sink_kwargs)),
            (
                "container",
                self.test_container_integration(sink_class, sink_name, **sink_kwargs),
            ),
            (
                "queue",
                self.test_queue_integration(sink_class, sink_name, **sink_kwargs),
            ),
        ]

        results = {}
        passed = 0
        total = len(tests)

        for test_name, test_coro in tests:
            print(f"  Running {test_name} integration test...")
            try:
                result = await test_coro
                results[test_name] = result
                if result.get("success", False):
                    passed += 1
                    print(f"    ✓ {test_name} passed")
                else:
                    print(
                        f"    ✗ {test_name} failed: {result.get('error', 'Unknown error')}"
                    )
            except Exception as e:
                results[test_name] = {
                    "success": False,
                    "error": f"Test execution failed: {str(e)}",
                }
                print(f"    ✗ {test_name} failed with exception: {e}")

        # Summary
        summary = {
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": passed / total if total > 0 else 0,
            "sink_class": sink_class.__name__,
            "sink_name": sink_name,
            "test_results": results,
        }

        print("\nIntegration test suite completed:")
        print(f"  Passed: {passed}/{total}")
        print(f"  Success rate: {summary['success_rate']:.1%}")

        return summary

    def get_test_results(self) -> List[Dict[str, Any]]:
        """Get all test results.

        Returns:
            List of all test results
        """
        return self._test_results.copy()

    def clear_test_results(self) -> None:
        """Clear all test results."""
        self._test_results.clear()

    def print_test_summary(self) -> None:
        """Print a summary of all test results."""
        if not self._test_results:
            print("No integration test results available.")
            return

        total = len(self._test_results)
        passed = sum(1 for r in self._test_results if r.get("success", False))

        print("\n=== Integration Test Summary ===")
        print(f"Total tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success rate: {passed / total:.1%}")

        # Show failed tests
        failed_tests = [r for r in self._test_results if not r.get("success", False)]
        if failed_tests:
            print("\nFailed tests:")
            for test in failed_tests:
                print(
                    f"  - {test.get('sink_class', 'Unknown')}: {test.get('error', 'Unknown error')}"
                )

        print("=" * 32)
