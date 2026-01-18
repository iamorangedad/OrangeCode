#!/usr/bin/env python3
"""
Main test runner for Orange Code project
Runs all unit tests for core functionality
"""

import sys
import os
import subprocess
from pathlib import Path


def run_test_file(test_file, description):
    """Run a single test file"""
    print(f"\n{'=' * 60}")
    print(f"🧪 Running {description}")
    print(f"{'=' * 60}")

    result = subprocess.run(
        [sys.executable, test_file],
        cwd=os.path.dirname(test_file),
        capture_output=True,
        text=True,
    )

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    success = result.returncode == 0
    if success:
        print(f"✅ {description} passed")
    else:
        print(f"❌ {description} failed")

    return success


def main():
    """Main test runner"""
    print("🍊 Orange Code - Unit Test Suite")
    print("=" * 60)
    print("Running comprehensive unit tests for all core modules")
    print("=" * 60)

    # Get tests directory
    tests_dir = Path(__file__).parent
    project_root = tests_dir.parent

    # Define test files
    test_files = [
        {
            "file": project_root / "tests" / "test_tools.py",
            "description": "Tool Registration and Permission Tests",
        },
        {
            "file": project_root / "tests" / "test_retry.py",
            "description": "LLM Retry Mechanism Tests",
        },
        {
            "file": project_root / "tests" / "test_tool_executor.py",
            "description": "Tool Executor Tests",
        },
        {
            "file": project_root / "tests" / "test_utils.py",
            "description": "Utility Functions Tests",
        },
        {
            "file": project_root / "tests" / "test_environment.py",
            "description": "Environment Setup Tests",
        },
    ]

    # Run all tests
    results = []
    for test_info in test_files:
        test_file = test_info["file"]
        if test_file.exists():
            success = run_test_file(str(test_file), test_info["description"])
            results.append((test_info["description"], success))
        else:
            print(f"⚠️  Test file not found: {test_file}")
            results.append((test_info["description"], False))

    # Print summary
    print(f"\n{'=' * 60}")
    print("📊 Test Summary")
    print(f"{'=' * 60}")

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for description, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {description}")

    print(f"\n📈 Results: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Orange Code is ready for deployment.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
