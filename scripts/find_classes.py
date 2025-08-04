#!/usr/bin/env python3
"""Script to find all class definitions in the project and sort them alphabetically.

This script helps identify duplicate class names across the codebase.
"""

import ast
from pathlib import Path
from typing import Dict, List, NamedTuple


class ClassInfo(NamedTuple):
    """Information about a class definition."""

    name: str
    file_path: str
    line_number: int
    parent_class: str = ""
    is_abstract: bool = False


def find_classes_in_file(file_path: Path) -> List[ClassInfo]:
    """Parse a Python file and extract all class definitions."""
    classes = []

    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
    except (UnicodeDecodeError, FileNotFoundError):
        return classes

    try:
        tree = ast.parse(content)
    except SyntaxError:
        # Skip files with syntax errors
        return classes

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            # Get parent class names
            bases = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    bases.append(base.id)
                elif isinstance(base, ast.Attribute):
                    bases.append(ast.unparse(base))

            # Check if it's an abstract class
            is_abstract = any(
                decorator.id == "abstractmethod"
                for decorator in node.decorator_list
                if isinstance(decorator, ast.Name)
            )

            classes.append(
                ClassInfo(
                    name=node.name,
                    file_path=str(file_path),
                    line_number=node.lineno,
                    parent_class=", ".join(bases) if bases else "",
                    is_abstract=is_abstract,
                )
            )

    return classes


def find_all_classes(project_root: Path) -> List[ClassInfo]:
    """Find all class definitions in the project."""
    all_classes = []

    # Find all Python files
    python_files = list(project_root.rglob("*.py"))

    # Filter out common directories to skip
    skip_dirs = {
        ".git",
        "__pycache__",
        ".pytest_cache",
        "htmlcov",
        "build",
        "dist",
        ".tox",
        ".venv",
        "venv",
        "env",
        "node_modules",
        ".mypy_cache",
        ".ruff_cache",
    }

    for file_path in python_files:
        # Skip files in directories we want to ignore
        if any(skip_dir in file_path.parts for skip_dir in skip_dirs):
            continue

        classes = find_classes_in_file(file_path)
        all_classes.extend(classes)

    return all_classes


def find_duplicate_classes(classes: List[ClassInfo]) -> Dict[str, List[ClassInfo]]:
    """Find classes with duplicate names."""
    class_groups = {}

    for class_info in classes:
        if class_info.name not in class_groups:
            class_groups[class_info.name] = []
        class_groups[class_info.name].append(class_info)

    # Return only groups with more than one class
    return {name: group for name, group in class_groups.items() if len(group) > 1}


def print_class_summary(
    classes: List[ClassInfo], show_duplicates_only: bool = False
) -> None:
    """Print a summary of all classes found."""
    if not classes:
        print("No classes found.")
        return

    # Sort classes alphabetically
    sorted_classes = sorted(classes, key=lambda x: x.name.lower())

    print(f"\n📊 Found {len(classes)} class definitions across the project")
    print("=" * 80)

    if show_duplicates_only:
        duplicates = find_duplicate_classes(classes)
        if not duplicates:
            print("✅ No duplicate class names found!")
            return

        print(f"\n⚠️  Found {len(duplicates)} duplicate class names:")
        print("=" * 80)

        for class_name, class_list in sorted(duplicates.items()):
            print(f"\n🔴 Duplicate: '{class_name}' ({len(class_list)} instances)")
            for i, class_info in enumerate(class_list, 1):
                parent_info = (
                    f" (inherits from: {class_info.parent_class})"
                    if class_info.parent_class
                    else ""
                )
                abstract_info = " [ABSTRACT]" if class_info.is_abstract else ""
                print(
                    f"   {i}. {class_info.file_path}:{class_info.line_number}{parent_info}{abstract_info}"
                )
    else:
        print("\n📋 All classes (sorted alphabetically):")
        print("=" * 80)

        current_letter = ""
        for class_info in sorted_classes:
            first_letter = class_info.name[0].upper()
            if first_letter != current_letter:
                current_letter = first_letter
                print(f"\n{current_letter}")
                print("-" * 40)

            parent_info = (
                f" (inherits from: {class_info.parent_class})"
                if class_info.parent_class
                else ""
            )
            abstract_info = " [ABSTRACT]" if class_info.is_abstract else ""
            print(
                f"  {class_info.name:<30} {class_info.file_path}:{class_info.line_number}{parent_info}{abstract_info}"
            )


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Find all class definitions in the project and sort them alphabetically"
    )
    parser.add_argument(
        "--duplicates-only", action="store_true", help="Show only duplicate class names"
    )
    parser.add_argument("--output", type=str, help="Output file path for the results")
    parser.add_argument(
        "--root",
        type=str,
        default=".",
        help="Project root directory (default: current directory)",
    )

    args = parser.parse_args()

    project_root = Path(args.root)
    if not project_root.exists():
        print(f"❌ Error: Project root '{project_root}' does not exist")
        return 1

    print(f"🔍 Scanning for classes in: {project_root.absolute()}")

    # Find all classes
    classes = find_all_classes(project_root)

    if args.output:
        # Save to file
        with open(args.output, "w", encoding="utf-8") as f:
            if args.duplicates_only:
                duplicates = find_duplicate_classes(classes)
                if duplicates:
                    f.write(f"Found {len(duplicates)} duplicate class names:\n")
                    f.write("=" * 80 + "\n")
                    for class_name, class_list in sorted(duplicates.items()):
                        f.write(
                            f"\nDuplicate: '{class_name}' ({len(class_list)} instances)\n"
                        )
                        for i, class_info in enumerate(class_list, 1):
                            parent_info = (
                                f" (inherits from: {class_info.parent_class})"
                                if class_info.parent_class
                                else ""
                            )
                            abstract_info = (
                                " [ABSTRACT]" if class_info.is_abstract else ""
                            )
                            f.write(
                                f"  {i}. {class_info.file_path}:{class_info.line_number}{parent_info}{abstract_info}\n"
                            )
                else:
                    f.write("✅ No duplicate class names found!\n")
            else:
                f.write(f"Found {len(classes)} class definitions:\n")
                f.write("=" * 80 + "\n")
                for class_info in sorted(classes, key=lambda x: x.name.lower()):
                    parent_info = (
                        f" (inherits from: {class_info.parent_class})"
                        if class_info.parent_class
                        else ""
                    )
                    abstract_info = " [ABSTRACT]" if class_info.is_abstract else ""
                    f.write(
                        f"{class_info.name:<30} {class_info.file_path}:{class_info.line_number}{parent_info}{abstract_info}\n"
                    )

        print(f"📄 Results saved to: {args.output}")
    else:
        # Print to console
        print_class_summary(classes, show_duplicates_only=args.duplicates_only)

    return 0


if __name__ == "__main__":
    exit(main())
