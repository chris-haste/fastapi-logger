Configuration Guide
===================

This guide provides a complete reference for all configuration options available in ``fapilog``. All settings can be configured via environment variables or programmatically through the ``LoggingSettings`` class.

Quick Start
-----------

The simplest way to configure ``fapilog`` is through environment variables:

.. code-block:: bash

   # Basic configuration
   export FAPILOG_LEVEL=INFO
   export FAPILOG_SINKS=stdout
   export FAPILOG_JSON_CONSOLE=auto

   # Start your application
   python your_app.py

Or programmatically:

.. code-block:: python

   from fapilog.settings import LoggingSettings
   from fapilog import configure_logging

   settings = LoggingSettings(
       level="INFO",
       sinks=["stdout"],
       json_console="auto"
   )
   logger = configure_logging(settings=settings)

Configuration Reference
=======================

Core Logging Settings
---------------------

.. _log_level:

level
~~~~~

:Type: ``str``
:Default: ``"INFO"``
:Environment Variable: ``FAPILOG_LEVEL``
:Valid Values: ``"DEBUG"``, ``"INFO"``, ``"WARN"``, ``"WARNING"``, ``"ERROR"``, ``"CRITICAL"``

Controls the minimum log level for output. Only messages at or above this level will be logged.

.. code-block:: bash

   # Set to debug for development
   export FAPILOG_LEVEL=DEBUG

   # Set to warning for production
   export FAPILOG_LEVEL=WARNING

.. _sinks:

sinks
~~~~~

:Type: ``Union[List[str], str]``
:Default: ``["stdout"]``
:Environment Variable: ``FAPILOG_SINKS``
:Valid Values: ``"stdout"``, ``"file://path/to/file.log"``, ``"loki://host:port"``

Comma-separated list of sink destinations for log output. Supports multiple sinks for redundancy.

.. code-block:: bash

   # Single sink
   export FAPILOG_SINKS=stdout

   # Multiple sinks
   export FAPILOG_SINKS=stdout,file:///var/log/app.log

   # With Loki
   export FAPILOG_SINKS=stdout,file:///var/log/app.log,loki://loki:3100

.. _json_console:

json_console
~~~~~~~~~~~~

:Type: ``str``
:Default: ``"auto"``
:Environment Variable: ``FAPILOG_JSON_CONSOLE``
:Valid Values: ``"auto"``, ``"json"``, ``"pretty"``

Controls the output format for console (stdout) logs.

- **auto**: Automatically chooses based on TTY detection (pretty in terminals, JSON otherwise)
- **json**: Always output JSON format (one line per event)
- **pretty**: Always output pretty format (colorized, multi-line)

.. code-block:: bash

   # Force JSON output
   export FAPILOG_JSON_CONSOLE=json

   # Force pretty output
   export FAPILOG_JSON_CONSOLE=pretty

   # Auto-detect (default)
   export FAPILOG_JSON_CONSOLE=auto

.. _sampling_rate:

sampling_rate
~~~~~~~~~~~~~

:Type: ``float``
:Default: ``1.0``
:Environment Variable: ``FAPILOG_SAMPLING_RATE``
:Valid Range: ``0.0`` to ``1.0``

Controls the percentage of log messages to process. Useful for high-volume logging scenarios.

.. code-block:: bash

   # Log 50% of messages
   export FAPILOG_SAMPLING_RATE=0.5

   # Log all messages (default)
   export FAPILOG_SAMPLING_RATE=1.0

Redaction Settings
------------------

.. _redact_patterns:

redact_patterns
~~~~~~~~~~~~~~~

:Type: ``Union[List[str], str]``
:Default: ``[]``
:Environment Variable: ``FAPILOG_REDACT_PATTERNS``

Comma-separated list of regex patterns to redact from log messages. Useful for masking sensitive data.

.. code-block:: bash

   # Redact passwords and tokens
   export FAPILOG_REDACT_PATTERNS=password,token,secret

   # Multiple patterns
   export FAPILOG_REDACT_PATTERNS=password,token,secret,api_key

.. _redact_fields:

redact_fields
~~~~~~~~~~~~~

:Type: ``Union[List[str], str]``
:Default: ``[]``
:Environment Variable: ``FAPILOG_REDACT_FIELDS``

Comma-separated list of field names to redact from log messages. Supports dot notation for nested fields.

.. code-block:: bash

   # Redact specific fields
   export FAPILOG_REDACT_FIELDS=user.password,request.headers.authorization

   # Multiple fields
   export FAPILOG_REDACT_FIELDS=password,api_key,secret_token

.. _redact_replacement:

redact_replacement
~~~~~~~~~~~~~~~~~~

:Type: ``str``
:Default: ``"REDACTED"``
:Environment Variable: ``FAPILOG_REDACT_REPLACEMENT``

The replacement value used for redacted fields.

.. code-block:: bash

   # Custom replacement
   export FAPILOG_REDACT_REPLACEMENT=***

   # Empty replacement
   export FAPILOG_REDACT_REPLACEMENT=

.. _redact_level:

redact_level
~~~~~~~~~~~~

:Type: ``str``
:Default: ``"INFO"``
:Environment Variable: ``FAPILOG_REDACT_LEVEL``
:Valid Values: ``"DEBUG"``, ``"INFO"``, ``"WARN"``, ``"WARNING"``, ``"ERROR"``, ``"CRITICAL"``

Minimum log level for redaction. Redaction only applies to messages at or above this level.

.. code-block:: bash

   # Redact in all levels
   export FAPILOG_REDACT_LEVEL=DEBUG

   # Only redact in INFO and above (default)
   export FAPILOG_REDACT_LEVEL=INFO

.. _enable_auto_redact_pii:

enable_auto_redact_pii
~~~~~~~~~~~~~~~~~~~~~~

:Type: ``bool``
:Default: ``True``
:Environment Variable: ``FAPILOG_ENABLE_AUTO_REDACT_PII``

Enables automatic PII (Personally Identifiable Information) detection and redaction.

.. code-block:: bash

   # Disable automatic PII redaction
   export FAPILOG_ENABLE_AUTO_REDACT_PII=false

   # Enable automatic PII redaction (default)
   export FAPILOG_ENABLE_AUTO_REDACT_PII=true

.. _custom_pii_patterns:

custom_pii_patterns
~~~~~~~~~~~~~~~~~~~

:Type: ``List[str]``
:Default: ``[]``
:Environment Variable: ``FAPILOG_CUSTOM_PII_PATTERNS``

Comma-separated list of custom regex patterns for PII detection.

.. code-block:: bash

   # Add custom PII patterns
   export FAPILOG_CUSTOM_PII_PATTERNS=credit_card,ssn,phone_number

Queue Settings
--------------

.. _queue_enabled:

queue_enabled
~~~~~~~~~~~~~

:Type: ``bool``
:Default: ``True``
:Environment Variable: ``FAPILOG_QUEUE_ENABLED``

Enables the async queue for non-blocking logging.

.. code-block:: bash

   # Disable async queue
   export FAPILOG_QUEUE_ENABLED=false

   # Enable async queue (default)
   export FAPILOG_QUEUE_ENABLED=true

.. _queue_maxsize:

queue_maxsize
~~~~~~~~~~~~~

:Type: ``int``
:Default: ``1000``
:Environment Variable: ``FAPILOG_QUEUE_MAXSIZE``

Maximum size of the async log queue.

.. code-block:: bash

   # Larger queue for high-volume logging
   export FAPILOG_QUEUE_MAXSIZE=5000

   # Smaller queue for memory-constrained environments
   export FAPILOG_QUEUE_MAXSIZE=100

.. _queue_overflow:

queue_overflow
~~~~~~~~~~~~~~

:Type: ``Literal["drop", "block", "sample"]``
:Default: ``"drop"``
:Environment Variable: ``FAPILOG_QUEUE_OVERFLOW``

Strategy for handling queue overflow:

- **drop**: Discard new messages when queue is full
- **block**: Wait for space in queue (may block application)
- **sample**: Probabilistically drop messages based on sampling rate

.. code-block:: bash

   # Drop messages when queue is full (default)
   export FAPILOG_QUEUE_OVERFLOW=drop

   # Block until space is available
   export FAPILOG_QUEUE_OVERFLOW=block

   # Sample messages when queue is full
   export FAPILOG_QUEUE_OVERFLOW=sample

.. _queue_batch_size:

queue_batch_size
~~~~~~~~~~~~~~~~

:Type: ``int``
:Default: ``10``
:Environment Variable: ``FAPILOG_QUEUE_BATCH_SIZE``

Number of events to process in a batch.

.. code-block:: bash

   # Larger batches for better throughput
   export FAPILOG_QUEUE_BATCH_SIZE=50

   # Smaller batches for lower latency
   export FAPILOG_QUEUE_BATCH_SIZE=5

.. _queue_batch_timeout:

queue_batch_timeout
~~~~~~~~~~~~~~~~~~~

:Type: ``float``
:Default: ``1.0``
:Environment Variable: ``FAPILOG_QUEUE_BATCH_TIMEOUT``

Maximum time to wait for batch completion (seconds).

.. code-block:: bash

   # Longer timeout for slow sinks
   export FAPILOG_QUEUE_BATCH_TIMEOUT=5.0

   # Shorter timeout for real-time logging
   export FAPILOG_QUEUE_BATCH_TIMEOUT=0.5

Environment Variables vs Programmatic Configuration
===================================================

Environment Variable Approach
-----------------------------

Configure everything through environment variables:

.. code-block:: bash

   export FAPILOG_LEVEL=DEBUG
   export FAPILOG_SINKS=stdout,file:///var/log/app.log
   export FAPILOG_QUEUE_ENABLED=true
   export FAPILOG_REDACT_PATTERNS=password,token

.. code-block:: python

   from fapilog import configure_logging

   # Uses environment variables automatically
   logger = configure_logging()

Programmatic Approach
---------------------

Override settings programmatically:

.. code-block:: python

   from fapilog.settings import LoggingSettings
   from fapilog import configure_logging

   # Override specific settings
   settings = LoggingSettings(
       level="DEBUG",
       sinks=["stdout", "file:///var/log/app.log"],
       queue_enabled=True,
       redact_level="INFO"
   )

   logger = configure_logging(settings=settings)

Mixed Configuration
-------------------

You can combine environment variables with programmatic overrides:

.. code-block:: python

   from fapilog.settings import LoggingSettings
   from fapilog import configure_logging

   # Start with environment defaults, then override
   settings = LoggingSettings()
   settings.level = "DEBUG"  # Override just the level
   settings.sinks.append("file:///var/log/app.log")  # Add a sink

   logger = configure_logging(settings=settings)

Sink-Specific Configuration
===========================

File Sink
---------

File sinks support additional configuration via URI parameters:

.. code-block:: bash

   # Basic file logging
   export FAPILOG_SINKS=file:///var/log/app.log

   # With rotation settings
   export FAPILOG_SINKS=file:///var/log/app.log?maxBytes=10485760&backupCount=3

**File Sink Parameters:**

- **maxBytes**: Maximum file size before rotation (default: 10MB)
- **backupCount**: Number of backup files to keep (default: 5)

Loki Sink
---------

Loki sinks support configuration via URI parameters:

.. code-block:: bash

   # Basic Loki logging
   export FAPILOG_SINKS=loki://loki:3100

   # With labels and batching
   export FAPILOG_SINKS=loki://loki:3100?labels=app=myapi,env=prod&batch_size=50&batch_interval=1.0

**Loki Sink Parameters:**

- **labels**: Static labels for all log streams (e.g., ``app=myapi,env=prod``)
- **batch_size**: Number of logs to buffer before pushing (default: 100)
- **batch_interval**: Max seconds to wait before pushing a batch (default: 2.0)

Configuration Examples
======================

Development Environment
-----------------------

.. code-block:: bash

   # Development settings
   export FAPILOG_LEVEL=DEBUG
   export FAPILOG_SINKS=stdout
   export FAPILOG_JSON_CONSOLE=pretty
   export FAPILOG_QUEUE_ENABLED=true
   export FAPILOG_REDACT_LEVEL=DEBUG
   export FAPILOG_ENABLE_RESOURCE_METRICS=false

Production Environment
----------------------

.. code-block:: bash

   # Production settings
   export FAPILOG_LEVEL=INFO
   export FAPILOG_SINKS=stdout,file:///var/log/app.log,loki://loki:3100
   export FAPILOG_JSON_CONSOLE=json
   export FAPILOG_QUEUE_ENABLED=true
   export FAPILOG_REDACT_LEVEL=INFO
   export FAPILOG_ENABLE_RESOURCE_METRICS=true
   export FAPILOG_REDACT_PATTERNS=password,token,secret
   export FAPILOG_REDACT_FIELDS=user.password,request.headers.authorization

High-Volume Logging
-------------------

.. code-block:: bash

   # High-volume settings
   export FAPILOG_LEVEL=WARNING
   export FAPILOG_SINKS=stdout,file:///var/log/app.log
   export FAPILOG_SAMPLING_RATE=0.1
   export FAPILOG_QUEUE_MAXSIZE=5000
   export FAPILOG_QUEUE_BATCH_SIZE=100
   export FAPILOG_QUEUE_OVERFLOW=drop

Security-Focused
----------------

.. code-block:: bash

   # Security-focused settings
   export FAPILOG_LEVEL=INFO
   export FAPILOG_SINKS=stdout,file:///var/log/app.log
   export FAPILOG_REDACT_LEVEL=DEBUG
   export FAPILOG_REDACT_PATTERNS=password,token,secret,api_key,ssn
   export FAPILOG_REDACT_FIELDS=user.password,request.headers.authorization,response.body
   export FAPILOG_ENABLE_AUTO_REDACT_PII=true
   export FAPILOG_CUSTOM_PII_PATTERNS=credit_card,phone_number

Validation
==========

All configuration values are validated when the settings are loaded. Invalid values will raise a ``ConfigurationError`` with a descriptive message:

.. code-block:: python

   from fapilog.settings import LoggingSettings

   # This will raise ConfigurationError
   settings = LoggingSettings(level="INVALID_LEVEL")

Common validation errors:

- Invalid log levels (must be one of: DEBUG, INFO, WARN, WARNING, ERROR, CRITICAL)
- Invalid sampling rate (must be between 0.0 and 1.0)
- Invalid queue settings (must be positive numbers)
- Invalid sink URIs (must be valid file paths or Loki URLs) 