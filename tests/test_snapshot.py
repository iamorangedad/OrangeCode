"""Tests for request snapshots and undo."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from agent import Agent
from llm import ChatResult, ToolCall
from orangecode import main
from snapshot import SnapshotStore, undo_latest
from tools import ToolRegistry


def test_snapshot_saves_the_original_and_marks_created_files(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_bytes(b"old\n")
    registry = ToolRegistry(tmp_path)
    store = SnapshotStore(tmp_path)
    registry.snapshotter = lambda relative, existed: store.record("turn-1", relative, existed)
    registry.write_file("app.py", "new\n")
    registry.write_file("created.py", "hi\n")
    registry.write_file("app.py", "newer\n")

    saved = tmp_path / ".orangecode" / "snapshots" / "turn-1" / "files" / "app.py"
    assert saved.read_bytes() == b"old\n"
    manifest = (tmp_path / ".orangecode" / "snapshots" / "turn-1" / "manifest.json").read_text(encoding="utf-8")
    assert '"modified": ["app.py"]' in manifest
    assert '"created": ["created.py"]' in manifest


def test_undo_restores_modified_files_and_deletes_created_files(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("old\n", encoding="utf-8")
    registry = ToolRegistry(tmp_path)
    store = SnapshotStore(tmp_path)
    registry.snapshotter = lambda relative, existed: store.record("turn-1", relative, existed)
    registry.edit_file("app.py", "old", "new")
    registry.write_file("created.py", "hi\n")

    assert undo_latest(tmp_path) == "Restored turn-1."
    assert (tmp_path / "app.py").read_text(encoding="utf-8") == "old\n"
    assert not (tmp_path / "created.py").exists()
    assert undo_latest(tmp_path) == "Nothing to undo."


def test_agent_snapshots_existing_files_before_a_write(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("old\n", encoding="utf-8")

    class _LLM:
        def __init__(self) -> None:
            self.calls = 0

        def chat(self, messages, tools=None):
            self.calls += 1
            if self.calls == 1:
                return ChatResult(
                    content=None,
                    tool_calls=[
                        ToolCall(id="call_1", name="write_file", arguments={"path": "app.py", "content": "new\n"})
                    ],
                )
            return ChatResult(content="done", tool_calls=[])

    agent = Agent(_LLM(), ToolRegistry(tmp_path))
    assert agent.run("change app.py") == "done"
    saved = list((tmp_path / ".orangecode" / "snapshots").glob("*/files/app.py"))
    assert len(saved) == 1
    assert saved[0].read_text(encoding="utf-8") == "old\n"
    assert (tmp_path / "app.py").read_text(encoding="utf-8") == "new\n"


def test_cli_undo_restores_the_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "app.py").write_text("old\n", encoding="utf-8")
    registry = ToolRegistry(tmp_path)
    store = SnapshotStore(tmp_path)
    registry.snapshotter = lambda relative, existed: store.record("turn-1", relative, existed)
    registry.write_file("app.py", "new\n")
    registry.write_file("created.py", "hi\n")

    assert main(["--undo"]) == 0
    assert "Restored turn-1." in capsys.readouterr().out
    assert (tmp_path / "app.py").read_text(encoding="utf-8") == "old\n"
    assert not (tmp_path / "created.py").exists()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
