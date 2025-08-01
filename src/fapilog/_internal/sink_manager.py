"""Sink management for fapilog logging components.

This module provides a dedicated SinkManager class that handles
all sink-related operations extracted from LoggingContainer, following
the single responsibility principle.

Key Features:
- Sink creation and configuration from settings
- Queue worker setup and management
- Sink lifecycle operations (start, stop, cleanup)
- Thread-safe operations
- Extensible design for future sink implementations
- Clean interface with proper error handling
"""

import threading
from typing import Any, List, Optional

from ..exceptions import SinkConfigurationError, SinkErrorContextBuilder
from ..settings import LoggingSettings
from ..sinks.base import Sink
from ..sinks.file import create_file_sink_from_uri
from ..sinks.loki import create_loki_sink_from_uri
from ..sinks.stdout import StdoutSink
from .error_handling import handle_configuration_error
from .queue_worker import QueueWorker
from .sink_factory import create_custom_sink_from_uri


class SinkManager:
    """Manages sink creation, configuration, and lifecycle operations.

    This class handles all sink-related operations including creating sinks
    from settings, setting up queue workers, and managing sink lifecycles.

    Design Principles:
    - Clean separation of sink management concerns
    - Thread-safe operations
    - Extensible design for future sink types
    - Proper error handling with descriptive context
    - No dependencies on configuration, lifecycle, or middleware logic
    """

    def __init__(self, container_id: str) -> None:
        """Initialize the sink manager.

        Args:
            container_id: Unique identifier for the associated container
        """
        self._container_id = container_id
        self._lock = threading.RLock()
        self._sinks: List[Any] = []
        self._queue_worker: Optional[QueueWorker] = None

    def setup_queue_worker(
        self, settings: LoggingSettings, console_format: str, container: Any
    ) -> QueueWorker:
        """Set up the queue worker with appropriate sinks.

        Creates sinks based on settings configuration and initializes
        a QueueWorker with the created sinks and queue configuration.

        Args:
            settings: LoggingSettings containing sink and queue configuration
            console_format: Console format style ("pretty", "json", or "auto")
            container: LoggingContainer instance for sink initialization

        Returns:
            QueueWorker: Configured queue worker instance

        Raises:
            SinkConfigurationError: If sink creation fails
            ConfigurationError: If queue worker creation fails
        """
        with self._lock:
            # Create sinks based on settings
            self._sinks = []

            for sink_item in settings.sinks:
                # Handle direct Sink instances
                if isinstance(sink_item, Sink):
                    self._sinks.append(sink_item)
                    continue

                # Handle string URIs (existing logic)
                sink_uri = sink_item
                if sink_uri == "stdout":
                    # Map console_format to StdoutSink mode
                    if console_format == "pretty":
                        mode = "pretty"
                    elif console_format == "json":
                        mode = "json"
                    else:
                        mode = "auto"
                    self._sinks.append(StdoutSink(mode=mode, container=container))
                elif sink_uri.startswith("file://"):
                    try:
                        self._sinks.append(
                            create_file_sink_from_uri(sink_uri, container=container)
                        )
                    except Exception as e:
                        context = SinkErrorContextBuilder.build_write_context(
                            sink_name="file",
                            event_dict={"uri": sink_uri},
                            operation="initialize",
                        )
                        raise SinkConfigurationError(str(e), "file", context) from e
                elif (
                    sink_uri.startswith(("loki://", "https://")) and "loki" in sink_uri
                ):
                    try:
                        self._sinks.append(
                            create_loki_sink_from_uri(sink_uri, container=container)
                        )
                    except ImportError as e:
                        context = SinkErrorContextBuilder.build_write_context(
                            sink_name="loki",
                            event_dict={"uri": sink_uri},
                            operation="initialize",
                        )
                        raise SinkConfigurationError(str(e), "loki", context) from e
                    except Exception as e:
                        context = SinkErrorContextBuilder.build_write_context(
                            sink_name="loki",
                            event_dict={"uri": sink_uri},
                            operation="initialize",
                        )
                        raise SinkConfigurationError(str(e), "loki", context) from e
                else:
                    # Try custom sink from registry
                    try:
                        self._sinks.append(create_custom_sink_from_uri(sink_uri))
                    except SinkConfigurationError as e:
                        # If it's a custom sink error, re-raise with sink error handling
                        context = SinkErrorContextBuilder.build_write_context(
                            sink_name=e.sink_name or "custom",
                            event_dict={"uri": sink_uri},
                            operation="initialize",
                        )
                        raise SinkConfigurationError(
                            str(e), e.sink_name or "custom", context
                        ) from e
                    except Exception as e:
                        # Unknown sink type or other error
                        context = SinkErrorContextBuilder.build_write_context(
                            sink_name="unknown",
                            event_dict={"uri": sink_uri},
                            operation="initialize",
                        )
                        raise SinkConfigurationError(
                            f"Unknown sink type: {sink_uri}", "unknown", context
                        ) from e

            # Create queue worker with error handling
            try:
                worker = QueueWorker(
                    sinks=self._sinks,
                    queue_max_size=settings.queue.maxsize,
                    batch_size=settings.queue.batch_size,
                    batch_timeout=settings.queue.batch_timeout,
                    retry_delay=settings.queue.retry_delay,
                    max_retries=settings.queue.max_retries,
                    overflow_strategy=settings.queue.overflow,
                    sampling_rate=settings.sampling_rate,
                    container=container,
                )
                self._queue_worker = worker
                return worker
            except Exception as e:
                queue_config = {
                    "queue_max_size": settings.queue.maxsize,
                    "batch_size": settings.queue.batch_size,
                    "batch_timeout": settings.queue.batch_timeout,
                    "retry_delay": settings.queue.retry_delay,
                    "max_retries": settings.queue.max_retries,
                    "overflow_strategy": settings.queue.overflow,
                    "sampling_rate": settings.sampling_rate,
                }
                raise handle_configuration_error(
                    e, "queue_worker", queue_config, "valid queue configuration"
                ) from e

    def create_sinks_from_settings(  # noqa: vulture
        self, settings: LoggingSettings, console_format: str, container: Any
    ) -> List[Any]:
        """Create sinks from settings without setting up queue worker.

        This is a utility method for creating sinks when queue worker
        setup is not needed or will be done separately.

        Args:
            settings: LoggingSettings containing sink configuration
            console_format: Console format style ("pretty", "json", or "auto")
            container: LoggingContainer instance for sink initialization

        Returns:
            List[Any]: List of created sink instances

        Raises:
            SinkConfigurationError: If sink creation fails
        """
        # This is essentially the sink creation part of setup_queue_worker
        # but without the queue worker creation
        sinks = []

        for sink_item in settings.sinks:
            # Handle direct Sink instances
            if isinstance(sink_item, Sink):
                sinks.append(sink_item)
                continue

            # Handle string URIs (same logic as in setup_queue_worker)
            sink_uri = sink_item
            if sink_uri == "stdout":
                # Map console_format to StdoutSink mode
                if console_format == "pretty":
                    mode = "pretty"
                elif console_format == "json":
                    mode = "json"
                else:
                    mode = "auto"
                sinks.append(StdoutSink(mode=mode, container=container))
            elif sink_uri.startswith("file://"):
                try:
                    sinks.append(
                        create_file_sink_from_uri(sink_uri, container=container)
                    )
                except Exception as e:
                    context = SinkErrorContextBuilder.build_write_context(
                        sink_name="file",
                        event_dict={"uri": sink_uri},
                        operation="initialize",
                    )
                    raise SinkConfigurationError(str(e), "file", context) from e
            elif sink_uri.startswith(("loki://", "https://")) and "loki" in sink_uri:
                try:
                    sinks.append(
                        create_loki_sink_from_uri(sink_uri, container=container)
                    )
                except ImportError as e:
                    context = SinkErrorContextBuilder.build_write_context(
                        sink_name="loki",
                        event_dict={"uri": sink_uri},
                        operation="initialize",
                    )
                    raise SinkConfigurationError(str(e), "loki", context) from e
                except Exception as e:
                    context = SinkErrorContextBuilder.build_write_context(
                        sink_name="loki",
                        event_dict={"uri": sink_uri},
                        operation="initialize",
                    )
                    raise SinkConfigurationError(str(e), "loki", context) from e
            else:
                # Try custom sink from registry
                try:
                    sinks.append(create_custom_sink_from_uri(sink_uri))
                except SinkConfigurationError as e:
                    # If it's a custom sink error, re-raise with sink error handling
                    context = SinkErrorContextBuilder.build_write_context(
                        sink_name=e.sink_name or "custom",
                        event_dict={"uri": sink_uri},
                        operation="initialize",
                    )
                    raise SinkConfigurationError(
                        str(e), e.sink_name or "custom", context
                    ) from e
                except Exception as e:
                    # Unknown sink type or other error
                    context = SinkErrorContextBuilder.build_write_context(
                        sink_name="unknown",
                        event_dict={"uri": sink_uri},
                        operation="initialize",
                    )
                    raise SinkConfigurationError(
                        f"Unknown sink type: {sink_uri}", "unknown", context
                    ) from e

        return sinks

    def start_sinks(self) -> None:  # noqa: vulture
        """Start all managed sinks.

        This method can be used to explicitly start sinks that support
        lifecycle operations.
        """
        with self._lock:
            for sink in self._sinks:
                if hasattr(sink, "start"):
                    sink.start()

    def stop_sinks(self) -> None:
        """Stop all managed sinks.

        This method gracefully stops all sinks that support
        lifecycle operations.
        """
        with self._lock:
            for sink in self._sinks:
                if hasattr(sink, "stop"):
                    try:
                        sink.stop()
                    except Exception:
                        # Continue stopping other sinks even if one fails
                        pass

    def cleanup_sinks(self) -> None:
        """Clean up and reset all managed sinks.

        This method performs cleanup operations and resets the sink list.
        """
        with self._lock:
            self.stop_sinks()
            self._sinks.clear()
            self._queue_worker = None

    def get_sinks(self) -> List[Any]:
        """Get the current list of managed sinks.

        Returns:
            List[Any]: Copy of the current sink list
        """
        with self._lock:
            return self._sinks.copy()

    def get_queue_worker(self) -> Optional[QueueWorker]:
        """Get the current queue worker instance.

        Returns:
            Optional[QueueWorker]: Current queue worker or None if not set up
        """
        return self._queue_worker
