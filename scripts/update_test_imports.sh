#!/bin/bash
# Mass update test imports after Phase 5 refactoring

echo "🔧 Updating test imports for Phase 5 refactoring..."

# Phase 5 Part 1: settings.py → config/ package
echo "📝 Updating settings imports..."
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\.settings import/from fapilog.config import/g' {} \;

# Phase 5 Part 2: monitoring.py → monitoring/ package (already working due to __init__.py)
echo "📊 Monitoring imports should already work via __init__.py exports..."

# Phase 5 Part 3: enrichers.py → enrichers/ package (already working due to __init__.py)
echo "🚀 Enrichers imports should already work via __init__.py exports..."

# Update _internal imports to new locations
echo "🔧 Updating _internal imports..."

# Core managers
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.configuration_manager/from fapilog.core.managers.configuration_manager/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.lifecycle_manager/from fapilog.core.managers.lifecycle_manager/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.sink_manager/from fapilog.core.managers.sink_manager/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.middleware_manager/from fapilog.core.managers.middleware_manager/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.metrics_manager/from fapilog.core.managers.metrics_manager/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.contextual_manager/from fapilog.core.managers.contextual_manager/g' {} \;

# Core factories
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.component_factory/from fapilog.core.factories.component_factory/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.container_logger_factory/from fapilog.core.factories.container_logger_factory/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.sink_factory/from fapilog.core.factories.sink_factory/g' {} \;

# Core registries
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.component_registry/from fapilog.core.registries.component_registry/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.processor_registry/from fapilog.core.registries.processor_registry/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.sink_registry/from fapilog.core.registries.sink_registry/g' {} \;

# Async components - cache
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.lru_cache/from fapilog.async_components.cache.lru_cache/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.safe_async_cache/from fapilog.async_components.cache.safe_async_cache/g' {} \;

# Async components - concurrency
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.async_lock_manager/from fapilog.async_components.concurrency.lock_manager/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.async_task_manager/from fapilog.async_components.concurrency.task_manager/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.background_cleanup_manager/from fapilog.async_components.concurrency.background_cleanup_manager/g' {} \;

# Async components - queue
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.queue_worker/from fapilog.async_components.queue.worker/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.queue_integration/from fapilog.async_components.queue.integration/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.batch_manager/from fapilog.async_components.queue.batch_manager/g' {} \;

# Integrations - loki
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.loki_http_client/from fapilog.integrations.loki.client/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.loki_payload_formatter/from fapilog.integrations.loki.formatter/g' {} \;

# Integrations - pii
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.pii_patterns/from fapilog.integrations.pii.patterns/g' {} \;

# Utils
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.context/from fapilog.utils.context/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.utils/from fapilog.utils.helpers/g' {} \;

# Processors
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.processor import/from fapilog.processors.base import/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.async_processor_base/from fapilog.processors.async_base/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.deduplication_processor/from fapilog.processors.deduplication/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.throttle_processor/from fapilog.processors.throttling/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.processor_error_handling/from fapilog.processors.error_handling/g' {} \;

# Processors from processors.py (god file)
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.processors import/from fapilog.processors.redaction import RedactionProcessor\nfrom fapilog.processors.filtering import FilterNoneProcessor\nfrom fapilog.processors.sampling import SamplingProcessor\n# from fapilog.processors.base import/g' {} \;

# Internal modules that remain
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.error_handling/from fapilog._internal.error_handling/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.metrics/from fapilog._internal.metrics/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.processor_metrics/from fapilog._internal.processor_metrics/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.testing/from fapilog._internal.testing/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.templates/from fapilog._internal.templates/g' {} \;

echo "✅ Test import updates complete!"
echo "🧪 Run 'python -m pytest tests/ -x --tb=short' to verify"