"""Tests for the stdio MCP client."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from mcp_client import MCPClient, MCPError, encode_message, read_message, resolve_mcp_timeout


FAKE_SERVER = r"""
import json
import sys

def read_message():
    headers = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n"):
            break
        key, value = line.decode().split(":", 1)
        headers[key.strip().lower()] = value.strip()
    length = int(headers["content-length"])
    return json.loads(sys.stdin.buffer.read(length))

def write_message(payload):
    body = json.dumps(payload).encode()
    sys.stdout.buffer.write(f"Content-Length: {len(body)}\r\n\r\n".encode() + body)
    sys.stdout.buffer.flush()

while True:
    message = read_message()
    if message is None:
        break
    method = message.get("method")
    if method == "initialize":
        write_message({
            "jsonrpc": "2.0",
            "id": message["id"],
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "fake", "version": "0"},
            },
        })
    elif method == "notifications/initialized":
        continue
    elif method == "tools/list":
        write_message({
            "jsonrpc": "2.0",
            "id": message["id"],
            "result": {
                "tools": [{
                    "name": "echo",
                    "description": "Echo text",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"text": {"type": "string"}},
                        "required": ["text"],
                    },
                }]
            },
        })
    elif method == "tools/call":
        text = (message.get("params") or {}).get("arguments", {}).get("text", "")
        write_message({
            "jsonrpc": "2.0",
            "id": message["id"],
            "result": {"content": [{"type": "text", "text": text}], "isError": False},
        })
"""


def test_framing_round_trip() -> None:
    payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    process = subprocess.Popen(
        [sys.executable, "-c", "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    assert process.stdin is not None and process.stdout is not None
    process.stdin.write(encode_message(payload))
    process.stdin.close()
    assert read_message(process.stdout) == payload
    process.wait(timeout=5)


def test_client_lists_and_calls_a_tool() -> None:
    client = MCPClient([sys.executable, "-c", FAKE_SERVER])
    client.start()
    try:
        names = [item["function"]["name"] for item in client.schemas()]
        assert names == ["mcp_echo"]
        assert client.call("mcp_echo", {"text": "ping"}) == "ping"
    finally:
        client.close()


def test_silent_server_times_out_and_closes() -> None:
    silent = "import sys, time\nsys.stderr.write('waiting\\n')\nsys.stderr.flush()\ntime.sleep(30)\n"
    client = MCPClient([sys.executable, "-c", silent], timeout=0.3)
    started = time.monotonic()
    try:
        with pytest.raises(MCPError, match="timed out"):
            client.start()
    finally:
        client.close()
    assert time.monotonic() - started < 2
    assert client.process is None


def test_stalled_tool_call_returns_an_error() -> None:
    stalled = FAKE_SERVER.replace("import json\nimport sys\n", "import json\nimport sys\nimport time\n")
    stalled = stalled.replace(
        'elif method == "tools/call":\n',
        'elif method == "tools/call":\n'
        '        sys.stderr.buffer.write(b"x" * 200000)\n'
        '        sys.stderr.buffer.flush()\n'
        '        time.sleep(30)\n',
    )
    client = MCPClient([sys.executable, "-c", stalled], timeout=0.3)
    client.start()
    try:
        started = time.monotonic()
        result = client.call("mcp_echo", {"text": "ping"})
        assert result.startswith("Error:")
        assert "timed out" in result
        assert time.monotonic() - started < 2
    finally:
        client.close()
    assert client.process is None


def test_stderr_flood_does_not_block_initialize() -> None:
    noisy = FAKE_SERVER.replace(
        "while True:\n    message = read_message()",
        "sys.stderr.buffer.write(b'x' * 200000)\n"
        "sys.stderr.buffer.flush()\n"
        "while True:\n"
        "    message = read_message()",
    )
    client = MCPClient([sys.executable, "-c", noisy], timeout=2)
    client.start()
    try:
        assert client.call("mcp_echo", {"text": "ping"}) == "ping"
    finally:
        client.close()


def test_mcp_timeout_uses_thirty_seconds_and_caps_at_two_minutes() -> None:
    assert resolve_mcp_timeout("") == 30
    assert resolve_mcp_timeout("nope") == 30
    assert resolve_mcp_timeout("500") == 120
    assert resolve_mcp_timeout("15") == 15


def test_encode_message_sets_content_length() -> None:
    framed = encode_message({"jsonrpc": "2.0", "method": "ping"})
    assert framed.startswith(b"Content-Length:")
    assert json.loads(framed.split(b"\r\n\r\n", 1)[1])["method"] == "ping"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
