"""Minimal coding-agent loop.

The loop sends the conversation and tool schemas to an OpenAI-compatible
model. Tool results are appended to the same message list until the model
returns plain text or the step limit is reached.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from llm import ChatResult, LLMClient, LLMError, ToolCall
from mcp_client import MCPClient, MCPError
from session import new_session_path, save_session
from snapshot import SnapshotStore, new_turn_id
from tools import ToolRegistry, limit_text, resolve_shell_policy

DEFAULT_MAX_STEPS = 8
DEFAULT_MESSAGE_CHAR_BUDGET = 24000
CONTEXT_CHAR_LIMIT = 6000


class Agent:
    """Runs a tool-calling loop against local or remote models."""

    def __init__(
        self,
        llm: LLMClient,
        registry: ToolRegistry,
        mcp: MCPClient | None = None,
        max_steps: int = DEFAULT_MAX_STEPS,
        check_command: str = "",
        message_char_budget: int = DEFAULT_MESSAGE_CHAR_BUDGET,
        session_path: Path | None = None,
    ) -> None:
        self.llm = llm
        self.registry = registry
        self.mcp = mcp
        self.max_steps = max_steps
        self.check_command = check_command.strip()
        self.message_char_budget = message_char_budget
        self.session_path = session_path
        self.messages: list[dict[str, Any]] = [
            {"role": "system", "content": build_system_prompt(registry.workspace)}
        ]

    @classmethod
    def from_env(cls, interactive: bool = True) -> Agent:
        """Build an agent from environment variables and the current directory.

        One-shot runs pass interactive=False so shell stays disabled unless
        SHELL=allow is set.
        """
        registry = ToolRegistry(Path.cwd(), shell_policy=resolve_shell_policy(interactive))
        llm = LLMClient()
        mcp = _start_mcp(os.getenv("MCP_COMMAND", ""))
        max_steps = _positive_int(os.getenv("MAX_STEPS"), DEFAULT_MAX_STEPS)
        check_command = os.getenv("CHECK_COMMAND", "")
        budget = _positive_int(os.getenv("MESSAGE_CHAR_BUDGET"), DEFAULT_MESSAGE_CHAR_BUDGET)
        return cls(
            llm=llm,
            registry=registry,
            mcp=mcp,
            max_steps=max_steps,
            check_command=check_command,
            message_char_budget=budget,
            session_path=new_session_path(Path.cwd()),
        )

    def schemas(self) -> list[dict[str, Any]]:
        """Return built-in tools plus any tools discovered from MCP."""
        schemas = self.registry.schemas()
        if self.mcp is not None:
            schemas.extend(self.mcp.schemas())
        return schemas

    def tool_names(self) -> list[str]:
        """Return the names the model is allowed to call."""
        names = self.registry.names()
        if self.mcp is not None:
            names.extend(tool["function"]["name"] for tool in self.mcp.schemas())
        return names

    def run(self, user_text: str) -> str:
        """Append a user message and run the loop until a final answer."""
        store = SnapshotStore(self.registry.workspace)
        turn_id = new_turn_id()
        self.registry.snapshotter = lambda relative, existed: store.record(turn_id, relative, existed)
        try:
            return self._run(user_text)
        finally:
            self.registry.snapshotter = None
            self.persist_session()

    def persist_session(self) -> None:
        """Write the full transcript when this agent has a session path."""
        if self.session_path is None:
            return
        save_session(self.session_path, self.messages)

    def _run(self, user_text: str) -> str:
        self.registry.written_paths.clear()
        self.messages.append({"role": "user", "content": user_text})
        schemas = self.schemas()

        for _ in range(self.max_steps):
            try:
                payload = trim_messages(self.messages, self.message_char_budget)
                result = self.llm.chat(payload, tools=schemas)
            except LLMError as exc:
                text = f"Error: {exc}"
                self.messages.append({"role": "assistant", "content": text})
                return text

            if not result.tool_calls:
                text = result.content or ""
                self.messages.append({"role": "assistant", "content": text})
                failure = self._check_failure()
                if failure is None:
                    return text
                self.messages.append({"role": "user", "content": failure})
                continue

            self.messages.append(_assistant_message(result))
            finished = 0
            try:
                for call in result.tool_calls:
                    output = self.execute_tool(call)
                    self.messages.append(
                        {"role": "tool", "tool_call_id": call.id, "content": output}
                    )
                    finished += 1
            except KeyboardInterrupt:
                for call in result.tool_calls[finished:]:
                    self.messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.id,
                            "content": "Error: interrupted",
                        }
                    )
                text = "Interrupted."
                self.messages.append({"role": "assistant", "content": text})
                return text

        text = f"Stopped: reached the maximum of {self.max_steps} tool steps."
        self.messages.append({"role": "assistant", "content": text})
        return text

    def execute_tool(self, call: ToolCall) -> str:
        """Dispatch one tool call to MCP or the built-in registry."""
        if not call.name:
            return "Error: tool name is missing"
        _trace_start(call)
        if self.mcp is not None and self.mcp.owns(call.name):
            output = self.mcp.call(call.name, call.arguments)
        else:
            output = self.registry.execute(call.name, call.arguments)
        _trace_end(call.name, output)
        return output

    def _check_failure(self) -> str | None:
        """Run CHECK_COMMAND after writes. Return a user message when it fails."""
        command = self.check_command
        if not command or not self.registry.written_paths:
            return None
        try:
            completed = subprocess.run(
                command,
                shell=True,
                cwd=self.registry.workspace,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            body = "exit_code: timeout\nError: check command timed out after 120 seconds"
            return f"Check command `{command}` failed.\n{body}"
        body = limit_text(
            f"exit_code: {completed.returncode}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
        if completed.returncode == 0:
            return None
        return f"Check command `{command}` failed.\n{body}"

    def close(self) -> None:
        """Release the MCP server process when one was started."""
        if self.mcp is not None:
            self.mcp.close()
            self.mcp = None


def build_system_prompt(workspace: Path) -> str:
    """Describe the workspace and include a short project brief when present."""
    parts = [
        "You are a coding agent. Use tools to read and modify files in the workspace and to run shell commands.",
        "Search before reading large files, then read only the line range you need.",
        "Change existing files with edit_file and a unique snippet. Use write_file to create files.",
        "Prefer small, correct edits. When the task is done, reply in plain text without a tool call.",
        f"Workspace: {workspace}",
    ]
    brief = _project_brief(workspace)
    if brief:
        parts.append("--- PROJECT CONTEXT ---")
        parts.append(brief)
    return "\n".join(parts)


def _project_brief(workspace: Path) -> str:
    path = workspace / "AGENTS.md"
    if not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if len(text) <= CONTEXT_CHAR_LIMIT:
        return text
    return text[:CONTEXT_CHAR_LIMIT] + "\n...[truncated]"


def _assistant_message(result: ChatResult) -> dict[str, Any]:
    message: dict[str, Any] = {"role": "assistant", "content": result.content or ""}
    message["tool_calls"] = [
        {
            "id": call.id,
            "type": "function",
            "function": {
                "name": call.name,
                "arguments": json.dumps(call.arguments),
            },
        }
        for call in result.tool_calls
    ]
    return message


def _start_mcp(command: str) -> MCPClient | None:
    stripped = command.strip()
    if not stripped:
        return None
    client = MCPClient(stripped)
    try:
        client.start()
    except (MCPError, OSError) as exc:
        print(f"MCP server failed to start: {exc}", file=sys.stderr)
        client.close()
        return None
    return client


def _trace_enabled() -> bool:
    """Return False when TRACE is 0, false, or no. Tracing is on otherwise."""
    return os.getenv("TRACE", "").strip().lower() not in {"0", "false", "no"}


def _trace_start(call: ToolCall) -> None:
    if not _trace_enabled():
        return
    detail = _trace_detail(call.arguments)
    suffix = f" {detail}" if detail else ""
    print(f"→ {call.name}{suffix}", file=sys.stderr)


def _trace_end(name: str, output: str) -> None:
    if not _trace_enabled():
        return
    status = "error" if output.startswith("Error:") else f"{len(output)} chars"
    print(f"← {name} {status}", file=sys.stderr)


def _trace_detail(arguments: dict[str, Any] | None) -> str:
    if not arguments:
        return ""
    parts: list[str] = []
    for key in ("path", "command", "query"):
        value = arguments.get(key)
        if value is None or value == "":
            continue
        text = str(value).replace("\n", " ")
        if len(text) > 80:
            text = text[:77] + "..."
        parts.append(f"{key}={text}")
    return " ".join(parts)


def trim_messages(messages: list[dict[str, Any]], budget: int) -> list[dict[str, Any]]:
    """Return a copy whose non-system text fits the character budget.

    The stored transcript is left unchanged. The system message and the last
    user message stay intact. Oldest tool results are replaced first.
    """
    copied = [dict(message) for message in messages]
    last_user = None
    for index, message in enumerate(copied):
        if message.get("role") == "user":
            last_user = index

    def size() -> int:
        return sum(_message_chars(message) for message in copied if message.get("role") != "system")

    for index, message in enumerate(copied):
        if size() <= budget:
            return copied
        if message.get("role") != "tool":
            continue
        content = message.get("content")
        if not isinstance(content, str) or content.startswith("[trimmed]"):
            continue
        copied[index] = {**message, "content": f"[trimmed] tool result omitted ({len(content)} characters)"}

    for index, message in enumerate(copied):
        if size() <= budget:
            return copied
        if message.get("role") not in {"user", "assistant"} or index == last_user:
            continue
        content = message.get("content")
        if not isinstance(content, str) or content.startswith("[trimmed]"):
            continue
        copied[index] = {**message, "content": f"[trimmed] message omitted ({len(content)} characters)"}
    return copied


def _message_chars(message: dict[str, Any]) -> int:
    content = message.get("content")
    total = len(content) if isinstance(content, str) else 0
    tool_calls = message.get("tool_calls")
    if tool_calls:
        total += len(json.dumps(tool_calls))
    return total


def _positive_int(raw: str | None, default: int) -> int:
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default
