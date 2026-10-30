#!/usr/bin/env python3
"""Run the Orange Code unit tests."""

import os
import subprocess
import sys
from pathlib import Path


def run_test_file(test_file: str, description: str) -> bool:
    """Run one test module and return True when it passes."""
    print(f"\n{'=' * 60}")
    print(f"Running {description}")
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

    if result.returncode == 0:
        print(f"PASS: {description}")
        return True
    print(f"FAIL: {description}")
    return False


def main() -> int:
    """Run every unit-test module and print a summary."""
    print("Orange Code unit tests")
    tests_dir = Path(__file__).parent
    project_root = tests_dir.parent
    test_files = [
        (project_root / "tests" / "test_tools.py", "Built-in tools"),
        (project_root / "tests" / "test_llm.py", "Chat client"),
        (project_root / "tests" / "test_agent.py", "Agent loop"),
        (project_root / "tests" / "test_mcp.py", "MCP client"),
        (project_root / "tests" / "test_session.py", "Sessions"),
        (project_root / "tests" / "test_environment.py", "Environment"),
    ]

    results = []
    for test_file, description in test_files:
        if test_file.exists():
            results.append((description, run_test_file(str(test_file), description)))
        else:
            print(f"Missing test file: {test_file}")
            results.append((description, False))

    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"\nResults: {passed}/{total} modules passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
