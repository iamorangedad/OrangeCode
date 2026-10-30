"""Tests for the coding-agent tool loop."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from agent import Agent, build_system_prompt, trim_messages
from session import load_session
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


_FAIL_CHECK = 'python3 -c "import sys; sys.exit(1)"'
_PASS_CHECK = 'python3 -c "print(1)"'


def _write_then_answer(final: str) -> list[ChatResult]:
    return [
        ChatResult(
            content=None,
            tool_calls=[
                ToolCall(
                    id="call_write",
                    name="write_file",
                    arguments={"path": "app.py", "content": "print(1)\n"},
                )
            ],
        ),
        ChatResult(content=final, tool_calls=[]),
    ]


def test_failed_check_is_sent_back_to_the_model(tmp_path: Path) -> None:
    llm = _ScriptedLLM(
        [
            *_write_then_answer("done"),
            ChatResult(content="fixed", tool_calls=[]),
        ]
    )
    agent = Agent(llm, ToolRegistry(tmp_path), max_steps=3, check_command=_FAIL_CHECK)
    answer = agent.run("add app.py")
    assert answer.startswith("Stopped:")
    assert len(llm.calls) == 3
    assert any("exit_code: 1" in str(message.get("content")) for message in llm.calls[2])


def test_passing_check_returns_the_model_text(tmp_path: Path) -> None:
    llm = _ScriptedLLM(_write_then_answer("all good"))
    agent = Agent(llm, ToolRegistry(tmp_path), max_steps=4, check_command=_PASS_CHECK)
    assert agent.run("add app.py") == "all good"
    assert len(llm.calls) == 2


def test_missing_check_command_does_not_run(tmp_path: Path) -> None:
    llm = _ScriptedLLM(_write_then_answer("all good"))
    agent = Agent(llm, ToolRegistry(tmp_path), max_steps=4, check_command="")
    assert agent.run("add app.py") == "all good"
    assert len(llm.calls) == 2


def test_new_request_clears_written_paths(tmp_path: Path) -> None:
    registry = ToolRegistry(tmp_path)
    registry.written_paths.add("stale.py")
    llm = _ScriptedLLM([ChatResult(content="hello", tool_calls=[])])
    agent = Agent(llm, registry, check_command=_FAIL_CHECK)
    assert agent.run("hi") == "hello"
    assert len(llm.calls) == 1


def test_interrupt_fills_missing_tool_results(tmp_path: Path) -> None:
    class _InterruptRegistry(ToolRegistry):
        def execute(self, name: str, arguments: dict) -> str:
            raise KeyboardInterrupt()

    llm = _ScriptedLLM(
        [
            ChatResult(
                content=None,
                tool_calls=[
                    ToolCall(id="call_1", name="list_files", arguments={}),
                    ToolCall(id="call_2", name="read_file", arguments={"path": "a.py"}),
                ],
            )
        ]
    )
    agent = Agent(llm, _InterruptRegistry(tmp_path), max_steps=4)
    assert agent.run("edit the file") == "Interrupted."
    tool_messages = [message for message in agent.messages if message["role"] == "tool"]
    assert [message["tool_call_id"] for message in tool_messages] == ["call_1", "call_2"]
    assert all(message["content"] == "Error: interrupted" for message in tool_messages)


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


def test_tool_trace_is_written_to_stderr(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    llm = _ScriptedLLM(
        [
            ChatResult(
                content=None,
                tool_calls=[ToolCall(id="call_1", name="list_files", arguments={"path": "."})],
            ),
            ChatResult(content="listed", tool_calls=[]),
        ]
    )
    agent = Agent(llm, ToolRegistry(tmp_path), max_steps=2)
    assert agent.run("list") == "listed"
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "→ list_files" in captured.err
    assert "← list_files" in captured.err


def test_trace_can_be_disabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("TRACE", "0")
    llm = _ScriptedLLM(
        [
            ChatResult(
                content=None,
                tool_calls=[ToolCall(id="call_1", name="list_files", arguments={"path": "."})],
            ),
            ChatResult(content="listed", tool_calls=[]),
        ]
    )
    agent = Agent(llm, ToolRegistry(tmp_path), max_steps=2)
    assert agent.run("list") == "listed"
    captured = capsys.readouterr()
    assert "list_files" not in captured.err
    assert captured.out == ""


def test_saved_session_reloads_on_a_new_agent(tmp_path: Path) -> None:
    path = tmp_path / ".orangecode" / "sessions" / "demo.jsonl"
    llm = _ScriptedLLM([ChatResult(content="ok", tool_calls=[])])
    agent = Agent(llm, ToolRegistry(tmp_path), session_path=path)
    assert agent.run("remember this") == "ok"
    restored = Agent(_ScriptedLLM([]), ToolRegistry(tmp_path))
    restored.messages = load_session(path)
    assert any(message.get("content") == "remember this" for message in restored.messages)


def test_trim_messages_fits_the_budget_and_keeps_the_last_user() -> None:
    original = [
        {"role": "system", "content": "instructions"},
        {"role": "user", "content": "older"},
        {"role": "assistant", "content": "A" * 80},
        {"role": "tool", "tool_call_id": "call_1", "content": "B" * 120},
        {"role": "user", "content": "latest question"},
    ]
    trimmed = trim_messages(original, 160)
    non_system = sum(
        len(message.get("content") or "")
        for message in trimmed
        if message["role"] != "system"
    )
    assert non_system <= 160
    assert trimmed[0]["content"] == "instructions"
    assert trimmed[-1]["content"] == "latest question"
    assert original[3]["content"] == "B" * 120
    tool = next(message for message in trimmed if message["role"] == "tool")
    assert tool["role"] == "tool"
    assert "120 characters" in tool["content"]


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
