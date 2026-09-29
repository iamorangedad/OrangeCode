"""Tests for the stdio MCP client."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from mcp_client import MCPClient, encode_message, read_message


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


def test_encode_message_sets_content_length() -> None:
    framed = encode_message({"jsonrpc": "2.0", "method": "ping"})
    assert framed.startswith(b"Content-Length:")
    assert json.loads(framed.split(b"\r\n\r\n", 1)[1])["method"] == "ping"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
