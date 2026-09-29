"""Checks that the minimal agent modules are importable."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from llm import normalize_base_url


def test_core_files_exist() -> None:
    for name in ("agent.py", "llm.py", "tools.py", "mcp_client.py", "orangecode.py"):
        assert (ROOT / name).is_file(), name


def test_requests_import() -> None:
    import requests

    assert requests.__version__


def test_ollama_host_maps_to_openai_base_url() -> None:
    assert normalize_base_url("http://127.0.0.1:11434") == "http://127.0.0.1:11434/v1"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
