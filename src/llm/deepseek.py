"""DeepSeek chat completion client."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

from src.config import settings


class LLMConfigurationError(RuntimeError):
    """Raised when the LLM client is missing required runtime configuration."""


@dataclass(frozen=True, slots=True)
class LLMResponse:
    """Normalized LLM response returned by chat clients."""

    content: str
    model: str
    usage: dict[str, Any] = field(default_factory=dict)


class DeepSeekClient:
    """Minimal DeepSeek client using the OpenAI-compatible chat completions API."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = settings.llm.base_url,
        model: str = settings.llm.model,
        temperature: float = settings.llm.temperature,
        max_tokens: int = settings.llm.max_tokens,
        timeout: float = settings.llm.timeout_seconds,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.llm.api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.http_client = http_client or httpx.Client(timeout=timeout)

    def chat(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Send a prompt to DeepSeek and return normalized response content."""

        if not self.api_key:
            raise LLMConfigurationError("缺少 DeepSeek API Key，请设置 DEEPSEEK_API_KEY")

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.http_client.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature if temperature is None else temperature,
                "max_tokens": self.max_tokens if max_tokens is None else max_tokens,
            },
        )
        response.raise_for_status()
        payload = response.json()

        choices = payload.get("choices") or []
        if not choices:
            raise RuntimeError("DeepSeek 响应中缺少 choices")

        message = choices[0].get("message") or {}
        content = message.get("content")
        if not isinstance(content, str):
            raise RuntimeError("DeepSeek 响应中缺少 message.content")

        return LLMResponse(
            content=content,
            model=str(payload.get("model") or self.model),
            usage=dict(payload.get("usage") or {}),
        )
