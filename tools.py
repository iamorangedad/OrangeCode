"""Built-in workspace tools for the coding agent."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Mapping

MAX_OUTPUT_CHARS = 20000
MAX_LIST_ENTRIES = 200
MAX_SEARCH_MATCHES = 50
MAX_SEARCH_FILE_BYTES = 1_000_000
MAX_FULL_READ_LINES = 400
SKIP_DIRS = {".git", ".orangecode", "__pycache__", ".venv", "node_modules"}
_SECRET_NAMES = {".env", ".netrc", "id_rsa", "id_dsa", "credentials.json"}
_SECRET_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}
_DENIED_PARTS = {".git", ".orangecode"}


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
        shell_policy: str | None = None,
    ) -> None:
        self.workspace = Path(workspace).resolve()
        self.shell_policy = _coerce_shell_policy(shell_policy, confirm_shell)
        self.confirm_shell = self.shell_policy == "ask"
        self.confirmer = confirmer or _prompt_to_confirm
        self.shell_timeout = shell_timeout
        self.written_paths: set[str] = set()

    def schemas(self) -> list[dict[str, Any]]:
        """Return OpenAI tool definitions for the built-in tools."""
        return [
            _schema(
                "read_file",
                "Read a UTF-8 text file inside the workspace. Pass start_line and end_line to read a slice with line numbers.",
                {
                    "path": _string("File path inside the workspace."),
                    "start_line": _integer("First line to read, starting at 1. Omit to read from the beginning."),
                    "end_line": _integer("Last line to read, inclusive. Omit to read through the end."),
                },
                ["path"],
            ),
            _schema(
                "write_file",
                "Create or overwrite a UTF-8 text file inside the workspace. Prefer edit_file when changing an existing file.",
                {
                    "path": _string("File path inside the workspace."),
                    "content": _string("Full file contents to write."),
                },
                ["path", "content"],
            ),
            _schema(
                "edit_file",
                "Replace one unique text snippet in a file. Fails when the snippet is missing or appears more than once.",
                {
                    "path": _string("File path inside the workspace."),
                    "old_text": _string("Exact snippet to replace. It must occur once in the file."),
                    "new_text": _string("Replacement text. Use an empty string to delete the snippet."),
                },
                ["path", "old_text", "new_text"],
            ),
            _schema(
                "search",
                "Search text files in the workspace and return matching path, line number, and line text.",
                {
                    "query": _string("Text to find. Interpreted as a regular expression when regex is true."),
                    "path": _string("File or directory to search. Defaults to the workspace root."),
                    "regex": {
                        "type": "boolean",
                        "description": "When true, treat query as a Python regular expression matched per line.",
                    },
                },
                ["query"],
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
        return ["read_file", "write_file", "edit_file", "search", "list_files", "execute_shell"]

    def execute(self, name: str, arguments: dict[str, Any] | None) -> str:
        """Run one built-in tool and return text for the model."""
        args = arguments or {}
        try:
            if name == "read_file":
                return self.read_file(
                    str(args.get("path", "")),
                    _optional_int(args.get("start_line")),
                    _optional_int(args.get("end_line")),
                )
            if name == "write_file":
                return self.write_file(str(args.get("path", "")), str(args.get("content", "")))
            if name == "edit_file":
                if "old_text" not in args or "new_text" not in args:
                    return "Error: old_text and new_text are required"
                return self.edit_file(str(args.get("path", "")), str(args["old_text"]), str(args["new_text"]))
            if name == "search":
                return self.search(
                    str(args.get("query", "")),
                    str(args.get("path", ".") or "."),
                    _optional_bool(args.get("regex"), False),
                )
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

    def read_file(self, path: str, start_line: int | None = None, end_line: int | None = None) -> str:
        """Read a text file, or a 1-based inclusive line range with line numbers."""
        target = self._resolve(path)
        denied = self._unavailable(target, path)
        if denied:
            return denied
        if not target.is_file():
            return f"Error: file not found: {path}"
        text = target.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        if start_line is None and end_line is None:
            if len(lines) > MAX_FULL_READ_LINES:
                return (
                    f"Error: {path} has {len(lines)} lines. "
                    "Pass start_line and end_line, or search first."
                )
            return limit_text(text)

        start = 1 if start_line is None else start_line
        end = len(lines) if end_line is None else end_line
        if start < 1 or (end_line is not None and end < 1):
            return "Error: line numbers start at 1"
        if not lines or start > len(lines):
            return f"Error: start_line {start} is past the end of the file ({len(lines)} lines)"
        end = min(end, len(lines))
        if end < start:
            return "Error: end_line is before start_line"

        numbered = [f"{index}|{lines[index - 1]}" for index in range(start, end + 1)]
        relative = target.relative_to(self.workspace)
        header = f"{relative} lines {start}-{end} of {len(lines)}"
        return limit_text(header + "\n" + "\n".join(numbered))

    def edit_file(self, path: str, old_text: str, new_text: str) -> str:
        """Replace one unique snippet and report the line span that changed."""
        if not path:
            return "Error: path is required"
        if old_text == "":
            return "Error: old_text is required"
        target = self._resolve(path)
        denied = self._unavailable(target, path)
        if denied:
            return denied
        if not target.is_file():
            return f"Error: file not found: {path}"

        original = target.read_text(encoding="utf-8", errors="replace")
        matches = original.count(old_text)
        if matches == 0:
            return "Error: old text not found"
        if matches > 1:
            return f"Error: old text matched {matches} times; provide a larger unique snippet"

        start = original.find(old_text)
        old_span = _line_span(original, start, old_text)
        updated = original.replace(old_text, new_text, 1)
        _write_atomic(target, updated)
        new_span = _line_span(updated, start, new_text) if new_text else old_span
        relative = target.relative_to(self.workspace)
        self.written_paths.add(str(relative))
        if new_text:
            preview = _numbered_snippet(updated, new_span[0], new_span[1])
            return (
                f"Edited {relative}: replaced lines {old_span[0]}-{old_span[1]} "
                f"with lines {new_span[0]}-{new_span[1]}.\n{preview}"
            )
        return f"Edited {relative}: deleted lines {old_span[0]}-{old_span[1]}."

    def search(self, query: str, path: str = ".", regex: bool = False) -> str:
        """Find lines inside workspace text files."""
        if query == "":
            return "Error: query is required"
        pattern: re.Pattern[str] | None = None
        if regex:
            try:
                pattern = re.compile(query)
            except re.error as exc:
                return f"Error: invalid regular expression: {exc}"

        root = self._resolve(path or ".")
        if not root.exists():
            return f"Error: path not found: {path}"

        matches: list[str] = []
        for file_path in _iter_text_files(root):
            resolved = file_path.resolve()
            try:
                relative = resolved.relative_to(self.workspace)
            except ValueError:
                continue
            if path_is_denied(relative):
                continue
            text = _read_searchable(resolved)
            if text is None:
                continue
            for number, line in enumerate(text.splitlines(), start=1):
                found = pattern.search(line) if pattern is not None else query in line
                if not found:
                    continue
                matches.append(f"{relative}:{number}: {line}")
                if len(matches) >= MAX_SEARCH_MATCHES:
                    body = "\n".join(matches)
                    return body + f"\n...[truncated at {MAX_SEARCH_MATCHES} matches]"

        if not matches:
            return "(no matches)"
        return "\n".join(matches)

    def write_file(self, path: str, content: str) -> str:
        """Write a text file inside the workspace, creating parent directories."""
        if not path:
            return "Error: path is required"
        target = self._resolve(path)
        denied = self._unavailable(target, path)
        if denied:
            return denied
        _write_atomic(target, content)
        relative = target.relative_to(self.workspace)
        self.written_paths.add(str(relative))
        return f"Wrote {relative} ({len(content)} characters)"

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
        if self.shell_policy == "deny":
            return "Error: shell is disabled. Set SHELL=allow to run commands."
        if self.shell_policy == "ask":
            if self.confirmer is _prompt_to_confirm and not sys.stdin.isatty():
                return "Error: shell needs a terminal or SHELL=allow"
            if not self.confirmer(command):
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

    def _unavailable(self, target: Path, display: str) -> str | None:
        """Return an error when the resolved path is a secret or VCS path."""
        relative = target.relative_to(self.workspace)
        if path_is_denied(relative):
            return f"Error: path is not available: {display}"
        return None


def resolve_shell_policy(interactive: bool, environ: Mapping[str, str] | None = None) -> str:
    """Pick ask, allow, or deny for this process.

    ``SHELL`` wins when it is exactly ask, allow, or deny. A normal login
    shell path such as ``/bin/bash`` is ignored. ``CONFIRM_SHELL=1`` means
    ask and ``CONFIRM_SHELL=0`` means allow. Otherwise interactive sessions
    ask, and one-shot runs deny.
    """
    env = os.environ if environ is None else environ
    chosen = env.get("SHELL", "").strip().lower()
    if chosen in {"ask", "allow", "deny"}:
        return chosen
    confirm = env.get("CONFIRM_SHELL", "").strip().lower()
    if confirm in {"1", "true", "yes"}:
        return "ask"
    if confirm in {"0", "false", "no"}:
        return "allow"
    return "ask" if interactive else "deny"


def _coerce_shell_policy(shell_policy: str | None, confirm_shell: bool) -> str:
    if shell_policy is not None:
        if shell_policy not in {"ask", "allow", "deny"}:
            raise ValueError(f"unknown shell policy: {shell_policy}")
        return shell_policy
    return "ask" if confirm_shell else "allow"


def path_is_denied(relative: Path) -> bool:
    """Return True for secret files and for paths inside .git or .orangecode."""
    if any(part in _DENIED_PARTS for part in relative.parts):
        return True
    name = relative.name
    if name in _SECRET_NAMES or name.startswith(".env."):
        return True
    return relative.suffix.lower() in _SECRET_SUFFIXES


def _write_atomic(target: Path, content: str) -> None:
    """Replace a file by writing a sibling temp file and renaming it."""
    parent = target.parent
    if not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)
    temporary = parent / f".{target.name}.{os.getpid()}.tmp"
    try:
        temporary.write_text(content, encoding="utf-8")
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def _prompt_to_confirm(command: str) -> bool:
    answer = input(f"Run `{command}`? [y/N] ").strip().lower()
    return answer in {"y", "yes"}


def _iter_text_files(root: Path):
    """Yield files under root, skipping dependency and VCS directories."""
    if root.is_file():
        yield root
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS]
        for name in filenames:
            yield Path(dirpath) / name


def _read_searchable(path: Path) -> str | None:
    """Return file text, or None for binary and oversized files."""
    try:
        if path.stat().st_size > MAX_SEARCH_FILE_BYTES:
            return None
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data:
        return None
    return data.decode("utf-8", errors="replace")


def _line_span(text: str, start: int, snippet: str) -> tuple[int, int]:
    """Return the 1-based inclusive line span of snippet at start."""
    if snippet == "":
        line = text.count("\n", 0, start) + 1
        return line, line
    start_line = text.count("\n", 0, start) + 1
    end_line = start_line + snippet.count("\n")
    if snippet.endswith("\n"):
        end_line -= 1
    return start_line, max(start_line, end_line)


def _numbered_snippet(text: str, start_line: int, end_line: int) -> str:
    lines = text.splitlines()
    selected = [f"{index}|{lines[index - 1]}" for index in range(start_line, end_line + 1) if index <= len(lines)]
    return "\n".join(selected)


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _optional_bool(value: Any, default: bool) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes"}:
            return True
        if lowered in {"0", "false", "no"}:
            return False
    return bool(value)


def _string(description: str) -> dict[str, str]:
    return {"type": "string", "description": description}


def _integer(description: str) -> dict[str, str]:
    return {"type": "integer", "description": description}


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
