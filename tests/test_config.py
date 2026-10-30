"""Tests for orangecode.toml."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from agent import Agent
from config import load_project_config
from orangecode import print_config


def _clear_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "MODEL",
        "OLLAMA_MODEL",
        "BASE_URL",
        "OLLAMA_HOST",
        "API_KEY",
        "OPENAI_API_KEY",
        "MAX_STEPS",
        "CHECK_COMMAND",
        "MCP_COMMAND",
        "CONFIRM_SHELL",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("SHELL", "/bin/bash")


def test_file_settings_apply_until_the_environment_overrides(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (tmp_path / "orangecode.toml").write_text(
        '\n'.join(
            [
                'model = "from-file"',
                'base_url = "http://127.0.0.1:9"',
                "max_steps = 4",
                'check_command = "python3 -m pytest"',
                'shell = "allow"',
                'mcp_command = ""',
                'api_key = "secret-token"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    _clear_overrides(monkeypatch)
    agent = Agent.from_env(interactive=False)
    try:
        assert agent.llm.model == "from-file"
        assert agent.llm.base_url == "http://127.0.0.1:9/v1"
        assert agent.llm.api_key == "ollama"
        assert agent.max_steps == 4
        assert agent.check_command == "python3 -m pytest"
        assert agent.registry.shell_policy == "allow"
        print_config(agent)
        assert "Model: from-file" in capsys.readouterr().out
    finally:
        agent.close()

    monkeypatch.setenv("MODEL", "from-env")
    monkeypatch.setenv("MAX_STEPS", "2")
    overridden = Agent.from_env(interactive=False)
    try:
        assert overridden.llm.model == "from-env"
        assert overridden.max_steps == 2
        print_config(overridden)
        assert "Model: from-env" in capsys.readouterr().out
    finally:
        overridden.close()


def test_loader_ignores_comments_and_unknown_keys(tmp_path: Path) -> None:
    (tmp_path / "orangecode.toml").write_text(
        'model = "demo" # local name\napi_key = "nope"\n',
        encoding="utf-8",
    )
    assert load_project_config(tmp_path) == {"model": "demo"}


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
