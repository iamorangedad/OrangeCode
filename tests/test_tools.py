"""Tests for built-in workspace tools."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from tools import ToolRegistry


def test_read_and_write_round_trip(tmp_path: Path) -> None:
    registry = ToolRegistry(tmp_path)
    assert "Wrote" in registry.execute("write_file", {"path": "src/app.py", "content": "print(1)\n"})
    assert registry.execute("read_file", {"path": "src/app.py"}) == "print(1)\n"


def test_read_missing_file_returns_error(tmp_path: Path) -> None:
    registry = ToolRegistry(tmp_path)
    result = registry.execute("read_file", {"path": "missing.py"})
    assert result.startswith("Error: file not found")


def test_path_outside_workspace_is_rejected(tmp_path: Path) -> None:
    registry = ToolRegistry(tmp_path)
    result = registry.execute("read_file", {"path": "/etc/passwd"})
    assert "outside the workspace" in result


def test_list_files_marks_directories(tmp_path: Path) -> None:
    registry = ToolRegistry(tmp_path)
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "mod.py").write_text("x", encoding="utf-8")
    (tmp_path / "README.md").write_text("hi", encoding="utf-8")
    listing = registry.execute("list_files", {"path": "."})
    assert "README.md" in listing
    assert "pkg/" in listing


def test_execute_shell_runs_in_workspace(tmp_path: Path) -> None:
    registry = ToolRegistry(tmp_path)
    (tmp_path / "note.txt").write_text("hello", encoding="utf-8")
    result = registry.execute("execute_shell", {"command": "cat note.txt"})
    assert "exit_code: 0" in result
    assert "hello" in result


def test_unconfirmed_shell_does_not_run(tmp_path: Path) -> None:
    registry = ToolRegistry(tmp_path, confirm_shell=True, confirmer=lambda _command: False)
    result = registry.execute("execute_shell", {"command": "echo should-not-run"})
    assert result == "Error: command was not confirmed"


def test_unknown_tool(tmp_path: Path) -> None:
    registry = ToolRegistry(tmp_path)
    assert "unknown tool" in registry.execute("missing", {})


def test_schemas_use_openai_function_shape(tmp_path: Path) -> None:
    registry = ToolRegistry(tmp_path)
    names = [item["function"]["name"] for item in registry.schemas()]
    assert names == ["read_file", "write_file", "edit_file", "search", "list_files", "execute_shell"]


def test_read_file_line_range_includes_line_numbers(tmp_path: Path) -> None:
    registry = ToolRegistry(tmp_path)
    (tmp_path / "math_utils.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    result = registry.execute("read_file", {"path": "math_utils.py", "start_line": 2, "end_line": 2})
    assert "lines 2-2 of 2" in result
    assert "2|    return a - b" in result
    assert "def add" not in result


def test_search_returns_path_and_line(tmp_path: Path) -> None:
    registry = ToolRegistry(tmp_path)
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "math_utils.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "hidden.py").write_text("return a - b\n", encoding="utf-8")
    result = registry.execute("search", {"query": "return a - b"})
    assert "pkg/math_utils.py:2:     return a - b" in result
    assert ".git" not in result


def test_search_regex_and_no_match(tmp_path: Path) -> None:
    registry = ToolRegistry(tmp_path)
    (tmp_path / "app.py").write_text("value = 12\n", encoding="utf-8")
    assert "app.py:1:" in registry.execute("search", {"query": r"value = \d+", "regex": True})
    assert registry.execute("search", {"query": "missing"}) == "(no matches)"
    assert "invalid regular expression" in registry.execute("search", {"query": "(", "regex": True})


def test_edit_file_replaces_unique_snippet(tmp_path: Path) -> None:
    registry = ToolRegistry(tmp_path)
    (tmp_path / "math_utils.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    result = registry.execute(
        "edit_file",
        {"path": "math_utils.py", "old_text": "return a - b", "new_text": "return a + b"},
    )
    assert "replaced lines 2-2 with lines 2-2" in result
    assert "2|    return a + b" in result
    assert (tmp_path / "math_utils.py").read_text(encoding="utf-8") == "def add(a, b):\n    return a + b\n"


def test_secret_file_is_not_read(tmp_path: Path) -> None:
    registry = ToolRegistry(tmp_path)
    (tmp_path / ".env").write_text("TOKEN=secret\n", encoding="utf-8")
    result = registry.execute("read_file", {"path": ".env"})
    assert result.startswith("Error: path is not available")
    assert "TOKEN" not in result


def test_search_skips_secret_files(tmp_path: Path) -> None:
    registry = ToolRegistry(tmp_path)
    (tmp_path / ".env").write_text("TOKEN=secret\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("TOKEN = 1\n", encoding="utf-8")
    result = registry.execute("search", {"query": "TOKEN"})
    assert "app.py:1:" in result
    assert ".env" not in result


def test_write_inside_git_directory_is_rejected(tmp_path: Path) -> None:
    registry = ToolRegistry(tmp_path)
    result = registry.execute("write_file", {"path": ".git/config", "content": "x"})
    assert result.startswith("Error: path is not available")
    assert not (tmp_path / ".git" / "config").exists()


def test_edit_file_rejects_missing_and_repeated_text(tmp_path: Path) -> None:
    registry = ToolRegistry(tmp_path)
    (tmp_path / "app.py").write_text("x = 1\nx = 1\n", encoding="utf-8")
    missing = registry.execute("edit_file", {"path": "app.py", "old_text": "absent", "new_text": "y"})
    repeated = registry.execute("edit_file", {"path": "app.py", "old_text": "x = 1", "new_text": "x = 2"})
    assert missing == "Error: old text not found"
    assert "matched 2 times" in repeated
    assert (tmp_path / "app.py").read_text(encoding="utf-8") == "x = 1\nx = 1\n"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
