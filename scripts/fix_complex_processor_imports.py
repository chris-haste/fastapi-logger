#!/usr/bin/env python3
"""
Fix complex processor imports from the old processors.py god file.

This handles the tricky cases where multiple processors were imported
from a single file and now need individual imports.
"""

import re
from pathlib import Path


def fix_complex_processor_imports():
    """Fix complex processor imports in test files."""

    tests_dir = Path("tests")

    # Map of old imports to new imports
    processor_mapping = {
        "RedactionProcessor": "from fapilog.processors.redaction import RedactionProcessor",
        "FilterNoneProcessor": "from fapilog.processors.filtering import FilterNoneProcessor",
        "SamplingProcessor": "from fapilog.processors.sampling import SamplingProcessor",
        "Processor": "from fapilog.processors.base import Processor",
    }

    print("🔧 Fixing complex processor imports...")

    for test_file in tests_dir.glob("*.py"):
        print(f"📁 Processing {test_file}")

        with open(test_file) as f:
            content = f.read()

        original_content = content

        # Pattern: from fapilog._internal.processors import X, Y, Z
        multi_import_pattern = r"from fapilog\._internal\.processors import (.+)"
        matches = re.findall(multi_import_pattern, content)

        for match in matches:
            # Parse the imported names
            imported_names = [name.strip() for name in match.split(",")]

            # Build individual import statements
            new_imports = []
            for name in imported_names:
                if name in processor_mapping:
                    new_imports.append(processor_mapping[name])
                else:
                    print(f"⚠️  Unknown processor: {name} in {test_file}")

            # Replace the old import with new imports
            old_import = f"from fapilog._internal.processors import {match}"
            new_import_block = "\n".join(new_imports)
            content = content.replace(old_import, new_import_block)

        # Handle single imports
        for old_name, new_import in processor_mapping.items():
            old_single = f"from fapilog._internal.processors import {old_name}"
            content = content.replace(old_single, new_import)

        # Write back if changed
        if content != original_content:
            with open(test_file, "w") as f:
                f.write(content)
            print(f"✅ Updated {test_file}")
        else:
            print(f"➡️  No changes needed for {test_file}")

    print("🎉 Complex processor import fixes complete!")


if __name__ == "__main__":
    fix_complex_processor_imports()
