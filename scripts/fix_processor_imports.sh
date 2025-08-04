#!/bin/bash
# Fix processor imports - the most complex remaining imports

echo "🔧 Fixing processor imports..."

# Base processor imports
echo "📝 Fixing base processor imports..."
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.processor import/from fapilog.processors.base import/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.async_processor_base/from fapilog.processors.async_base/g' {} \;

# Specific processor imports
echo "🔄 Fixing specific processor imports..."
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.deduplication_processor/from fapilog.processors.deduplication/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.throttle_processor/from fapilog.processors.throttling/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/from fapilog\._internal\.processor_error_handling/from fapilog.processors.error_handling/g' {} \;

# Complex processor imports from the god file - need manual handling
echo "⚠️  Complex processor imports detected - see fix_complex_processor_imports.py"

echo "✅ Basic processor import fixes complete!"
echo "🔍 Run: python scripts/fix_complex_processor_imports.py"