"""Copy files before a request changes them so that request can be undone.

Snapshots live in ``.orangecode/snapshots/<turn-id>``. Restoring a turn writes
the saved bytes back and deletes files that the turn created. It does not run git.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def new_turn_id() -> str:
    """Return a sortable id for one user request."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return stamp


def snapshots_dir(workspace: Path) -> Path:
    """Return the directory that holds workspace snapshots."""
    return workspace / ".orangecode" / "snapshots"


class SnapshotStore:
    """Record the first version of each path changed during a turn."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = Path(workspace)
        self._seen: dict[str, set[str]] = {}

    def record(self, turn_id: str, relative: Path, existed: bool) -> None:
        """Save the original bytes, or mark a path that did not exist yet."""
        if not _safe_relative(relative):
            return
        key = relative.as_posix()
        seen = self._seen.setdefault(turn_id, set())
        if key in seen:
            return
        seen.add(key)
        manifest = _read_manifest(self.workspace, turn_id)
        if existed:
            source = self.workspace / relative
            destination = snapshots_dir(self.workspace) / turn_id / "files" / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_bytes())
            manifest["modified"].append(key)
        else:
            manifest["created"].append(key)
        _write_manifest(self.workspace, turn_id, manifest)


def undo_latest(workspace: Path) -> str:
    """Restore the newest snapshot and remove it. Return a short status."""
    turn = latest_snapshot(workspace)
    if turn is None:
        return "Nothing to undo."
    manifest = json.loads((turn / "manifest.json").read_text(encoding="utf-8"))
    for key in manifest.get("modified", []):
        source = turn / "files" / key
        destination = workspace / key
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
    for key in manifest.get("created", []):
        destination = workspace / key
        if destination.is_file():
            destination.unlink()
    name = turn.name
    shutil.rmtree(turn)
    return f"Restored {name}."


def latest_snapshot(workspace: Path) -> Path | None:
    """Return the newest turn directory that has a manifest."""
    directory = snapshots_dir(workspace)
    if not directory.is_dir():
        return None
    turns = sorted(path for path in directory.iterdir() if (path / "manifest.json").is_file())
    if not turns:
        return None
    return turns[-1]


def _safe_relative(relative: Path) -> bool:
    return bool(relative.parts) and ".." not in relative.parts and not relative.is_absolute()


def _read_manifest(workspace: Path, turn_id: str) -> dict[str, list[str]]:
    path = snapshots_dir(workspace) / turn_id / "manifest.json"
    if not path.is_file():
        return {"modified": [], "created": []}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        "modified": list(payload.get("modified", [])),
        "created": list(payload.get("created", [])),
    }


def _write_manifest(workspace: Path, turn_id: str, manifest: dict[str, list[str]]) -> None:
    directory = snapshots_dir(workspace) / turn_id
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
