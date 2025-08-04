#!/bin/bash
# Fix the most critical broken imports first

echo "🔧 Fixing critical test imports..."

# Core managers (high success rate, low risk)
echo "📁 Fixing core managers..."
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.configuration_manager/from fapilog.core.managers.configuration_manager/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.lifecycle_manager/from fapilog.core.managers.lifecycle_manager/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.sink_manager/from fapilog.core.managers.sink_manager/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.middleware_manager/from fapilog.core.managers.middleware_manager/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.metrics_manager/from fapilog.core.managers.metrics_manager/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.contextual_manager/from fapilog.core.managers.contextual_manager/g' {} \;

# Core factories
echo "🏭 Fixing core factories..."
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.component_factory/from fapilog.core.factories.component_factory/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.container_logger_factory/from fapilog.core.factories.container_logger_factory/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.sink_factory/from fapilog.core.factories.sink_factory/g' {} \;

# Core registries
echo "📋 Fixing core registries..."
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.component_registry/from fapilog.core.registries.component_registry/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.processor_registry/from fapilog.core.registries.processor_registry/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.sink_registry/from fapilog.core.registries.sink_registry/g' {} \;

# Async components - cache
echo "💾 Fixing async cache..."
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.lru_cache/from fapilog.async_components.cache.lru_cache/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.safe_async_cache/from fapilog.async_components.cache.safe_async_cache/g' {} \;

# Async components - concurrency  
echo "🔀 Fixing async concurrency..."
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.async_lock_manager/from fapilog.async_components.concurrency.lock_manager/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.async_task_manager/from fapilog.async_components.concurrency.task_manager/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.background_cleanup_manager/from fapilog.async_components.concurrency.background_cleanup_manager/g' {} \;

# Async components - queue
echo "🚀 Fixing async queue..."
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.queue_worker/from fapilog.async_components.queue.worker/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.queue_integration/from fapilog.async_components.queue.integration/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.batch_manager/from fapilog.async_components.queue.batch_manager/g' {} \;

# Utils
echo "🔧 Fixing utils..."
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.context/from fapilog.utils.context/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.utils/from fapilog.utils.helpers/g' {} \;

# Integrations
echo "🔗 Fixing integrations..."
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.loki_http_client/from fapilog.integrations.loki.client/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.loki_payload_formatter/from fapilog.integrations.loki.formatter/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.pii_patterns/from fapilog.integrations.pii.patterns/g' {} \;

echo "✅ Critical import fixes complete!"