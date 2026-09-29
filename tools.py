"""Built-in workspace tools for the coding agent."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Callable

MAX_OUTPUT_CHARS = 20000
MAX_LIST_ENTRIES = 200
SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules"}


def limit_text(text: str, limit: int = MAX_OUTPUT_CHARS) -> str:
    """Trim long tool output so it can fit in a later model request."""
    if len(text) <= limit:
        return text
    omitted = len(text) - limit
    return text[:limit] + f"\n...[truncated {omitted} characters]"


class ToolRegistry:
    """File and shell tools restricted to a workspace directory."""

    def __init__(
        self,
        workspace: Path | str,
        confirm_shell: bool = False,
        confirmer: Callable[[str], bool] | None = None,
        shell_timeout: int = 30,
    ) -> None:
        self.workspace = Path(workspace).resolve()
        self.confirm_shell = confirm_shell
        self.confirmer = confirmer or _prompt_to_confirm
        self.shell_timeout = shell_timeout

    def schemas(self) -> list[dict[str, Any]]:
        """Return OpenAI tool definitions for the built-in tools."""
        return [
            _schema(
                "read_file",
                "Read a UTF-8 text file inside the workspace.",
                {"path": _string("File path inside the workspace.")},
                ["path"],
            ),
            _schema(
                "write_file",
                "Create or overwrite a UTF-8 text file inside the workspace.",
                {
                    "path": _string("File path inside the workspace."),
                    "content": _string("Full file contents to write."),
                },
                ["path", "content"],
            ),
            _schema(
                "list_files",
                "List files and directories inside the workspace.",
                {
                    "path": _string("Directory path inside the workspace. Defaults to the workspace root."),
                    "recursive": {
                        "type": "boolean",
                        "description": "When true, walk subdirectories. Skips .git, virtualenvs, and node_modules.",
                    },
                },
                [],
            ),
            _schema(
                "execute_shell",
                "Run a shell command with the workspace as the working directory.",
                {
                    "command": _string("Shell command to run."),
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds. Defaults to 30 and cannot exceed 120.",
                    },
                },
                ["command"],
            ),
        ]

    def names(self) -> list[str]:
        """Return built-in tool names."""
        return ["read_file", "write_file", "list_files", "execute_shell"]

    def execute(self, name: str, arguments: dict[str, Any] | None) -> str:
        """Run one built-in tool and return text for the model."""
        args = arguments or {}
        try:
            if name == "read_file":
                return self.read_file(str(args.get("path", "")))
            if name == "write_file":
                return self.write_file(str(args.get("path", "")), str(args.get("content", "")))
            if name == "list_files":
                path = str(args.get("path", ".") or ".")
                recursive = bool(args.get("recursive", False))
                return self.list_files(path, recursive)
            if name == "execute_shell":
                timeout = args.get("timeout", self.shell_timeout)
                return self.execute_shell(str(args.get("command", "")), timeout)
            return f"Error: unknown tool '{name}'"
        except Exception as exc:
            return f"Error: {exc}"

    def read_file(self, path: str) -> str:
        """Read a text file inside the workspace."""
        target = self._resolve(path)
        if not target.is_file():
            return f"Error: file not found: {path}"
        text = target.read_text(encoding="utf-8", errors="replace")
        return limit_text(text)

    def write_file(self, path: str, content: str) -> str:
        """Write a text file inside the workspace, creating parent directories."""
        if not path:
            return "Error: path is required"
        target = self._resolve(path)
        parent = target.parent
        if not parent.exists():
            parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"Wrote {target.relative_to(self.workspace)} ({len(content)} characters)"

    def list_files(self, path: str = ".", recursive: bool = False) -> str:
        """List workspace entries, capped so the result stays small."""
        target = self._resolve(path or ".")
        if not target.exists():
            return f"Error: path not found: {path}"
        if target.is_file():
            return str(target.relative_to(self.workspace))

        entries: list[str] = []
        if recursive:
            for item in target.rglob("*"):
                if any(part in SKIP_DIRS for part in item.relative_to(self.workspace).parts):
                    continue
                suffix = "/" if item.is_dir() else ""
                entries.append(str(item.relative_to(self.workspace)) + suffix)
                if len(entries) >= MAX_LIST_ENTRIES:
                    break
        else:
            for item in sorted(target.iterdir(), key=lambda entry: entry.name):
                if item.name in SKIP_DIRS:
                    continue
                suffix = "/" if item.is_dir() else ""
                entries.append(str(item.relative_to(self.workspace)) + suffix)
                if len(entries) >= MAX_LIST_ENTRIES:
                    break

        if not entries:
            return "(empty)"
        body = "\n".join(entries)
        if len(entries) >= MAX_LIST_ENTRIES:
            body += f"\n...[truncated at {MAX_LIST_ENTRIES} entries]"
        return body

    def execute_shell(self, command: str, timeout: Any = None) -> str:
        """Run a command in the workspace and return stdout, stderr, and the exit code."""
        if not command.strip():
            return "Error: command is required"
        if self.confirm_shell and not self.confirmer(command):
            return "Error: command was not confirmed"

        try:
            seconds = int(timeout) if timeout is not None else self.shell_timeout
        except (TypeError, ValueError):
            seconds = self.shell_timeout
        seconds = max(1, min(seconds, 120))

        try:
            completed = subprocess.run(
                command,
                shell=True,
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=seconds,
            )
        except subprocess.TimeoutExpired:
            return f"Error: command timed out after {seconds} seconds"

        output = (
            f"exit_code: {completed.returncode}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
        return limit_text(output)

    def _resolve(self, path: str) -> Path:
        if not path:
            raise ValueError("path is required")
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = self.workspace / candidate
        resolved = candidate.resolve()
        try:
            resolved.relative_to(self.workspace)
        except ValueError as exc:
            raise ValueError(f"path is outside the workspace: {path}") from exc
        return resolved


def _prompt_to_confirm(command: str) -> bool:
    answer = input(f"Run `{command}`? [y/N] ").strip().lower()
    return answer in {"y", "yes"}


def _string(description: str) -> dict[str, str]:
    return {"type": "string", "description": description}


def _schema(
    name: str,
    description: str,
    properties: dict[str, Any],
    required: list[str],
) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }
