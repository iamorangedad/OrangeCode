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
    assert names == ["read_file", "write_file", "list_files", "execute_shell"]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
