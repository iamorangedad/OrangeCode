"""Tests for the coding-agent tool loop."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from agent import Agent, build_system_prompt
from llm import ChatResult, ToolCall
from tools import ToolRegistry


def test_loop_returns_file_contents_to_the_model(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("value = 1\n", encoding="utf-8")
    llm = _ScriptedLLM(
        [
            ChatResult(
                content=None,
                tool_calls=[ToolCall(id="call_1", name="read_file", arguments={"path": "main.py"})],
            ),
            ChatResult(content="The file sets value to 1.", tool_calls=[]),
        ]
    )
    agent = Agent(llm, ToolRegistry(tmp_path), max_steps=4)
    answer = agent.run("What is in main.py?")
    assert answer == "The file sets value to 1."
    tool_messages = [message for message in llm.calls[1] if message["role"] == "tool"]
    assert tool_messages[0]["content"] == "value = 1\n"


def test_loop_stops_at_max_steps(tmp_path: Path) -> None:
    llm = _ScriptedLLM(
        [
            ChatResult(
                content=None,
                tool_calls=[ToolCall(id=f"call_{index}", name="list_files", arguments={"path": "."})],
            )
            for index in range(3)
        ]
    )
    agent = Agent(llm, ToolRegistry(tmp_path), max_steps=2)
    answer = agent.run("Keep listing")
    assert "maximum of 2" in answer
    assert len(llm.calls) == 2


def test_model_error_is_returned_as_text(tmp_path: Path) -> None:
    from llm import LLMError

    class _FailingLLM:
        def chat(self, messages, tools=None):
            raise LLMError("connection refused")

    agent = Agent(_FailingLLM(), ToolRegistry(tmp_path))
    assert agent.run("hello") == "Error: connection refused"


def test_one_shot_from_env_denies_shell(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MCP_COMMAND", raising=False)
    monkeypatch.delenv("CONFIRM_SHELL", raising=False)
    monkeypatch.setenv("SHELL", "/bin/bash")
    agent = Agent.from_env(interactive=False)
    try:
        assert agent.registry.shell_policy == "deny"
    finally:
        agent.close()


def test_system_prompt_includes_agents_md(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("Use Python 3.11.", encoding="utf-8")
    prompt = build_system_prompt(tmp_path)
    assert "Use Python 3.11." in prompt
    assert str(tmp_path) in prompt


class _ScriptedLLM:
    def __init__(self, results: list[ChatResult]) -> None:
        self.results = list(results)
        self.calls: list[list[dict]] = []

    def chat(self, messages, tools=None):
        self.calls.append(list(messages))
        return self.results.pop(0)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
