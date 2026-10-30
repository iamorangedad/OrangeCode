"""Minimal MCP client over stdio.

The client speaks JSON-RPC with Content-Length framing, lists tools, and
calls them. It does not implement an MCP server, resources, or prompts.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import threading
import time
from typing import Any, BinaryIO


PROTOCOL_VERSION = "2024-11-05"


class MCPError(Exception):
    """Raised when the MCP server returns an error or the transport fails."""


def encode_message(payload: dict[str, Any]) -> bytes:
    """Frame one JSON-RPC message the way MCP stdio expects."""
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
    return header + body


def read_message(stream: BinaryIO) -> dict[str, Any]:
    """Read one Content-Length framed JSON-RPC message."""
    headers: dict[str, str] = {}
    while True:
        line = stream.readline()
        if not line:
            raise MCPError("MCP server closed the connection")
        if line in (b"\r\n", b"\n"):
            break
        decoded = line.decode("ascii", errors="replace")
        if ":" not in decoded:
            continue
        key, value = decoded.split(":", 1)
        headers[key.strip().lower()] = value.strip()

    if "content-length" not in headers:
        raise MCPError("MCP message is missing Content-Length")

    length = int(headers["content-length"])
    body = stream.read(length)
    if len(body) < length:
        raise MCPError("Incomplete MCP message")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise MCPError(f"MCP message was not JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise MCPError("MCP message was not a JSON object")
    return payload


def resolve_mcp_timeout(raw: str | None = None) -> float:
    """Return the MCP read timeout in seconds, capped at 120.

    An empty or invalid value falls back to 30 seconds. ``None`` reads
    ``MCP_TIMEOUT`` from the environment.
    """
    if raw is None:
        raw = os.getenv("MCP_TIMEOUT")
    if raw is None or not str(raw).strip():
        return 30.0
    try:
        value = float(raw)
    except ValueError:
        return 30.0
    if value <= 0:
        return 30.0
    return min(value, 120.0)


class MCPClient:
    """Stdio MCP client that exposes server tools with an mcp_ prefix."""

    def __init__(self, command: str | list[str], timeout: float | None = None) -> None:
        self.command = shlex.split(command) if isinstance(command, str) else list(command)
        self.timeout = resolve_mcp_timeout() if timeout is None else resolve_mcp_timeout(str(timeout))
        self.process: subprocess.Popen[bytes] | None = None
        self._next_id = 0
        self._tools: dict[str, str] = {}
        self._schemas: list[dict[str, Any]] = []

    def start(self) -> None:
        """Spawn the server, initialize the session, and cache tools/list."""
        if not self.command:
            raise MCPError("MCP command is empty")
        self.process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self._drain_stderr()
        self._request(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "orangecode", "version": "0.2.0"},
            },
        )
        self._notify("notifications/initialized", {})
        listed = self._request("tools/list", {})
        self._remember_tools(listed.get("tools") or [])

    def schemas(self) -> list[dict[str, Any]]:
        """Return OpenAI tool definitions for the connected server."""
        return list(self._schemas)

    def owns(self, name: str) -> bool:
        """Return True when name belongs to this MCP server."""
        return name in self._tools

    def call(self, name: str, arguments: dict[str, Any] | None) -> str:
        """Call a tool by its prefixed name and return text content."""
        if name not in self._tools:
            return f"Error: unknown MCP tool '{name}'"
        try:
            result = self._request(
                "tools/call",
                {"name": self._tools[name], "arguments": arguments or {}},
            )
        except MCPError as exc:
            return f"Error: {exc}"
        return _format_tool_result(result)

    def close(self) -> None:
        """Stop the server process."""
        process = self.process
        self.process = None
        if process is None:
            return
        if process.stdin:
            process.stdin.close()
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)

    def _remember_tools(self, tools: list[dict[str, Any]]) -> None:
        self._tools.clear()
        self._schemas.clear()
        used: set[str] = set()
        for tool in tools:
            original = str(tool.get("name") or "")
            if not original:
                continue
            prefixed = _unique_name(_prefix(original), used)
            used.add(prefixed)
            self._tools[prefixed] = original
            parameters = tool.get("inputSchema") or {"type": "object", "properties": {}}
            self._schemas.append(
                {
                    "type": "function",
                    "function": {
                        "name": prefixed,
                        "description": tool.get("description") or original,
                        "parameters": parameters,
                    },
                }
            )

    def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        self._next_id += 1
        request_id = self._next_id
        self._write({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        deadline = time.monotonic() + self.timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self.close()
                raise MCPError(f"MCP server timed out after {self.timeout:g} seconds")
            incoming = self._read(remaining)
            if incoming.get("id") != request_id:
                continue
            if "error" in incoming:
                error = incoming["error"] or {}
                message = error.get("message") if isinstance(error, dict) else str(error)
                raise MCPError(message or "MCP request failed")
            result = incoming.get("result")
            if isinstance(result, dict):
                return result
            return {"value": result}

    def _notify(self, method: str, params: dict[str, Any]) -> None:
        self._write({"jsonrpc": "2.0", "method": method, "params": params})

    def _write(self, payload: dict[str, Any]) -> None:
        process = self._require_process()
        if process.stdin is None:
            raise MCPError("MCP server stdin is not available")
        process.stdin.write(encode_message(payload))
        process.stdin.flush()

    def _read(self, timeout: float) -> dict[str, Any]:
        process = self._require_process()
        stdout = process.stdout
        if stdout is None:
            raise MCPError("MCP server stdout is not available")
        outcome: dict[str, Any] = {}

        def target() -> None:
            try:
                outcome["message"] = read_message(stdout)
            except Exception as exc:
                outcome["error"] = exc

        worker = threading.Thread(target=target, daemon=True)
        worker.start()
        worker.join(timeout)
        if worker.is_alive():
            self.close()
            raise MCPError(f"MCP server timed out after {self.timeout:g} seconds")
        if "error" in outcome:
            error = outcome["error"]
            if isinstance(error, MCPError):
                raise error
            raise MCPError(str(error)) from error
        message = outcome.get("message")
        if not isinstance(message, dict):
            raise MCPError("MCP message was not a JSON object")
        return message

    def _drain_stderr(self) -> None:
        """Keep the stderr pipe from filling and stalling the server."""
        process = self.process
        if process is None or process.stderr is None:
            return
        stderr = process.stderr

        def drain() -> None:
            try:
                while stderr.read(4096):
                    continue
            except (OSError, ValueError):
                return

        threading.Thread(target=drain, daemon=True).start()

    def _require_process(self) -> subprocess.Popen[bytes]:
        if self.process is None:
            raise MCPError("MCP server is not running")
        return self.process


def _prefix(name: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_]", "_", name)
    if not sanitized:
        sanitized = "tool"
    return f"mcp_{sanitized}"


def _unique_name(name: str, used: set[str]) -> str:
    if name not in used:
        return name
    index = 2
    while f"{name}_{index}" in used:
        index += 1
    return f"{name}_{index}"


def _format_tool_result(result: dict[str, Any]) -> str:
    parts: list[str] = []
    for block in result.get("content") or []:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(str(block.get("text") or ""))
        else:
            parts.append(json.dumps(block))
    text = "\n".join(parts) if parts else json.dumps(result)
    if result.get("isError"):
        return f"Error: {text}"
    return text
