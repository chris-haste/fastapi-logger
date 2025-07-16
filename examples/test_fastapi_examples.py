#!/usr/bin/env python3
"""
Test script to verify FastAPI examples work correctly.
This script tests the FastAPI app creation and basic functionality
without requiring uvicorn to be installed.
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_basic_fastapi():
    """Test the basic FastAPI example."""
    print("Testing basic FastAPI example...")

    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "basic_fastapi", "examples/05_fastapi_basic.py"
        )
        basic_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(basic_module)
        app = basic_module.app

        print("✅ Basic FastAPI app created successfully")
        print(f"✅ App title: {app.title}")
        print(f"✅ App version: {app.version}")
        print(f"✅ Routes count: {len(app.routes)}")

        return True
    except Exception as e:
        print(f"❌ Basic FastAPI example failed: {e}")
        return False


def test_middleware_fastapi():
    """Test the middleware FastAPI example."""
    print("\nTesting middleware FastAPI example...")

    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "middleware_fastapi", "examples/06_fastapi_middleware.py"
        )
        middleware_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(middleware_module)
        app = middleware_module.app

        print("✅ Middleware FastAPI app created successfully")
        print(f"✅ App title: {app.title}")
        print(f"✅ App version: {app.version}")
        print(f"✅ Routes count: {len(app.routes)}")

        return True
    except Exception as e:
        print(f"❌ Middleware FastAPI example failed: {e}")
        return False


def test_error_handling_fastapi():
    """Test the error handling FastAPI example."""
    print("\nTesting error handling FastAPI example...")

    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "error_handling_fastapi", "examples/07_fastapi_error_handling.py"
        )
        error_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(error_module)
        app = error_module.app

        print("✅ Error handling FastAPI app created successfully")
        print(f"✅ App title: {app.title}")
        print(f"✅ App version: {app.version}")
        print(f"✅ Routes count: {len(app.routes)}")

        return True
    except Exception as e:
        print(f"❌ Error handling FastAPI example failed: {e}")
        return False


def test_structured_logging_fastapi():
    """Test the structured logging FastAPI example."""
    print("\nTesting structured logging FastAPI example...")

    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "structured_logging_fastapi", "examples/08_fastapi_structured_logging.py"
        )
        structured_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(structured_module)
        app = structured_module.app

        print("✅ Structured logging FastAPI app created successfully")
        print(f"✅ App title: {app.title}")
        print(f"✅ App version: {app.version}")
        print(f"✅ Routes count: {len(app.routes)}")

        return True
    except Exception as e:
        print(f"❌ Structured logging FastAPI example failed: {e}")
        return False


def main():
    """Run all FastAPI example tests."""
    print("=== FastAPI Examples Test ===")
    print("Testing FastAPI integration examples...")
    print()

    results = []

    results.append(test_basic_fastapi())
    results.append(test_middleware_fastapi())
    results.append(test_error_handling_fastapi())
    results.append(test_structured_logging_fastapi())

    print("\n" + "=" * 50)
    print("Test Results:")
    print(f"✅ Passed: {sum(results)}")
    print(f"❌ Failed: {len(results) - sum(results)}")

    if all(results):
        print("\n🎉 All FastAPI examples are working correctly!")
        print("To run the servers, install uvicorn: pip install uvicorn")
        print("Then run: uvicorn examples.05_fastapi_basic:app --reload")
    else:
        print("\n⚠️  Some examples failed. Check the errors above.")

    return all(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
