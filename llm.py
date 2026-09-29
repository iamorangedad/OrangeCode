"""OpenAI-compatible chat client for local or remote models."""

from __future__ import annotations

import json
import os
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable

import requests


RETRYABLE_STATUS_CODES = {408, 409, 429, 500, 502, 503, 504}


class LLMError(Exception):
    """Raised when a chat request fails after retryable errors are exhausted."""


@dataclass
class ToolCall:
    """One tool call returned by the model."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ChatResult:
    """Parsed chat completion."""

    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)


def normalize_base_url(url: str) -> str:
    """Return an OpenAI-compatible base URL ending in /v1.

    Ollama's native host does not include /v1. Appending it lets the same
    client talk to Ollama and to external OpenAI-compatible gateways.
    """
    cleaned = url.strip().rstrip("/")
    if cleaned.endswith("/v1"):
        return cleaned
    return cleaned + "/v1"


class LLMClient:
    """Chat client that posts to /v1/chat/completions."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 120.0,
        max_retries: int = 3,
        session: requests.Session | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        raw_url = (
            base_url
            or os.getenv("BASE_URL")
            or os.getenv("OLLAMA_HOST")
            or "http://127.0.0.1:11434"
        )
        self.base_url = normalize_base_url(raw_url)
        self.api_key = api_key or os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY") or "ollama"
        self.model = model or os.getenv("MODEL") or os.getenv("OLLAMA_MODEL") or "qwen2.5-coder:3b"
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = session or requests.Session()
        self._sleep = sleeper

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> ChatResult:
        """Send one chat completion and return text plus any tool calls."""
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        attempts = self.max_retries + 1
        last_error: Exception | None = None

        for attempt in range(attempts):
            try:
                response = self.session.post(url, json=payload, headers=headers, timeout=self.timeout)
            except requests.RequestException as exc:
                last_error = exc
                if attempt < attempts - 1:
                    self._sleep(self._delay(attempt))
                    continue
                raise LLMError(f"LLM request failed: {exc}") from exc

            if response.status_code in RETRYABLE_STATUS_CODES and attempt < attempts - 1:
                self._sleep(self._delay(attempt))
                continue

            if response.status_code >= 400:
                detail = response.text[:500]
                raise LLMError(f"LLM request failed with status {response.status_code}: {detail}")

            try:
                body = response.json()
            except ValueError as exc:
                raise LLMError(f"LLM response was not JSON: {exc}") from exc

            return parse_chat_response(body)

        raise LLMError(f"LLM request failed: {last_error}")

    def _delay(self, attempt: int) -> float:
        delay = min(30.0, 1.0 * (2**attempt))
        return delay + delay * 0.1 * random.random()


def parse_chat_response(body: dict[str, Any]) -> ChatResult:
    """Convert a chat-completions JSON body into a ChatResult."""
    choices = body.get("choices") or []
    if not choices:
        raise LLMError("LLM response did not include any choices")

    message = choices[0].get("message") or {}
    content = message.get("content")
    tool_calls: list[ToolCall] = []

    for index, raw in enumerate(message.get("tool_calls") or []):
        function = raw.get("function") or {}
        name = function.get("name") or ""
        arguments = _parse_arguments(function.get("arguments"))
        call_id = raw.get("id") or f"call_{index}"
        tool_calls.append(ToolCall(id=str(call_id), name=name, arguments=arguments))

    return ChatResult(content=content, tool_calls=tool_calls)


def _parse_arguments(raw: Any) -> dict[str, Any]:
    if raw is None or raw == "":
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {"_raw": raw}
        if isinstance(parsed, dict):
            return parsed
        return {"_raw": raw}
    return {"_raw": str(raw)}
