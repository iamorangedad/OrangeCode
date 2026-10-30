"""Tests for on-disk session transcripts."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from session import latest_session, load_session, save_session


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "sessions" / "one.jsonl"
    messages = [{"role": "user", "content": "previous"}]
    save_session(path, messages)
    assert load_session(path) == messages


def test_latest_session_uses_file_name_order(tmp_path: Path) -> None:
    directory = tmp_path / ".orangecode" / "sessions"
    save_session(directory / "a.jsonl", [{"role": "user", "content": "old"}])
    save_session(directory / "b.jsonl", [{"role": "user", "content": "new"}])
    found = latest_session(tmp_path)
    assert found is not None
    assert found.name == "b.jsonl"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
