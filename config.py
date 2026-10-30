"""Read orangecode.toml from a workspace.

Only model, base URL, step limit, check command, shell policy, and MCP command
are accepted. An api_key entry is ignored. Environment variables override the file.
"""

from __future__ import annotations

from pathlib import Path

FIELDS = ("model", "base_url", "max_steps", "check_command", "shell", "mcp_command")


def load_project_config(workspace: Path) -> dict[str, str]:
    """Return the supported settings from orangecode.toml, if the file exists."""
    path = Path(workspace) / "orangecode.toml"
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or "=" not in line:
            continue
        key, token = line.split("=", 1)
        key = key.strip()
        if key not in FIELDS:
            continue
        values[key] = _parse_scalar(token.strip())
    return values


def prefer_env(env_value: str | None, file_value: str | None) -> str | None:
    """Use a non-empty environment value, otherwise the file value."""
    if env_value is not None and env_value.strip() != "":
        return env_value
    if file_value is not None and file_value.strip() != "":
        return file_value
    return None


def _parse_scalar(token: str) -> str:
    if len(token) >= 2 and token[0] == token[-1] and token[0] in {'"', "'"}:
        body = token[1:-1]
        if token[0] == '"':
            return body.replace('\\"', '"').replace("\\\\", "\\")
        return body
    return token
