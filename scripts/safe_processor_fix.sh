#!/bin/bash
# EXTREMELY SAFE processor import fixes - only simple single imports

echo "🔧 SAFE processor import fixes (single imports only)..."

# Create backups first
echo "💾 Creating backups..."
for file in tests/test_*redaction*.py tests/test_pipeline.py; do
    if [ -f "$file" ]; then
        cp "$file" "$file.backup"
        echo "✅ Backed up $file"
    fi
done

# Only fix the simple, safe single imports
echo "🔄 Fixing safe single imports..."

# RedactionProcessor - SAFE
find tests/ -name "*.py" -exec sed -i '' 's/^from fapilog\._internal\.processors import RedactionProcessor$/from fapilog.processors.redaction import RedactionProcessor/g' {} \;

# SamplingProcessor - SAFE  
find tests/ -name "*.py" -exec sed -i '' 's/^from fapilog\._internal\.processors import SamplingProcessor$/from fapilog.processors.sampling import SamplingProcessor/g' {} \;

# FilterNoneProcessor - SAFE
find tests/ -name "*.py" -exec sed -i '' 's/^from fapilog\._internal\.processors import FilterNoneProcessor$/from fapilog.processors.filtering import FilterNoneProcessor/g' {} \;

echo "✅ Safe processor import fixes complete!"
echo "⚠️  Multi-line and complex imports require manual handling"