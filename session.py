"""Save and restore agent transcripts on disk.

Sessions live in ``.orangecode/sessions`` inside the workspace. The directory
is local state and is not committed.
"""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sessions_dir(workspace: Path) -> Path:
    """Return the directory that holds this workspace's transcripts."""
    return workspace / ".orangecode" / "sessions"


def new_session_path(workspace: Path) -> Path:
    """Return a new session path. The file is created on the first save."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return sessions_dir(workspace) / f"{stamp}-{secrets.token_hex(4)}.jsonl"


def save_session(path: Path, messages: list[dict[str, Any]]) -> None:
    """Write the transcript as one JSON object per line."""
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(json.dumps(message, ensure_ascii=False) + "\n" for message in messages)
    path.write_text(body, encoding="utf-8")


def load_session(path: Path) -> list[dict[str, Any]]:
    """Read a transcript written by save_session."""
    messages: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"session line is not an object: {path}")
        messages.append(payload)
    return messages


def resolve_session(workspace: Path, session_id: str) -> Path:
    """Map a session id or file name to a path inside the workspace."""
    name = session_id if session_id.endswith(".jsonl") else f"{session_id}.jsonl"
    return sessions_dir(workspace) / name


def latest_session(workspace: Path) -> Path | None:
    """Return the last session file in lexical order, or None."""
    directory = sessions_dir(workspace)
    if not directory.is_dir():
        return None
    files = sorted(path for path in directory.glob("*.jsonl") if path.is_file())
    if not files:
        return None
    return files[-1]
