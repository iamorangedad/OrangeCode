"""Tests for the OpenAI-compatible chat client."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from llm import LLMClient, LLMError, normalize_base_url, parse_chat_response


def test_normalize_base_url_appends_v1() -> None:
    assert normalize_base_url("http://127.0.0.1:11434") == "http://127.0.0.1:11434/v1"
    assert normalize_base_url("https://example.com/v1/") == "https://example.com/v1"


def test_parse_tool_call_arguments_from_json_string() -> None:
    result = parse_chat_response(
        {
            "choices": [
                {
                    "message": {
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "function": {
                                    "name": "read_file",
                                    "arguments": '{"path": "a.py"}',
                                },
                            }
                        ],
                    }
                }
            ]
        }
    )
    assert result.content is None
    assert result.tool_calls[0].name == "read_file"
    assert result.tool_calls[0].arguments == {"path": "a.py"}


def test_chat_retries_retryable_status_then_succeeds() -> None:
    session = _ScriptedSession(
        [
            _Response(503, {"error": "unavailable"}),
            _Response(200, {"choices": [{"message": {"content": "done", "tool_calls": []}}]}),
        ]
    )
    delays: list[float] = []
    client = LLMClient(base_url="http://models.example/v1", session=session, sleeper=delays.append)
    result = client.chat([{"role": "user", "content": "hi"}])
    assert result.content == "done"
    assert len(session.calls) == 2
    assert delays


def test_chat_does_not_retry_authentication_errors() -> None:
    session = _ScriptedSession([_Response(401, {"error": "no"})])
    client = LLMClient(
        base_url="http://models.example/v1",
        session=session,
        sleeper=lambda _seconds: pytest.fail("sleep should not be called"),
    )
    with pytest.raises(LLMError, match="401"):
        client.chat([{"role": "user", "content": "hi"}])
    assert len(session.calls) == 1


def test_environment_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BASE_URL", "http://10.0.0.8:11434")
    monkeypatch.setenv("MODEL", "demo-model")
    monkeypatch.setenv("API_KEY", "secret")
    client = LLMClient()
    assert client.base_url == "http://10.0.0.8:11434/v1"
    assert client.model == "demo-model"
    assert client.api_key == "secret"


class _Response:
    def __init__(self, status_code: int, payload: dict) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self) -> dict:
        return self._payload


class _ScriptedSession:
    def __init__(self, responses: list[_Response]) -> None:
        self.responses = list(responses)
        self.calls: list[dict] = []

    def post(self, url: str, json: dict, headers: dict, timeout: float) -> _Response:
        self.calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        return self.responses.pop(0)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
