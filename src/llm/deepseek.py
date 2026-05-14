"""DeepSeek chat model client backed by LangChain."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

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
    """DeepSeek chat client using LangChain's OpenAI-compatible ChatModel."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = settings.llm.base_url,
        model: str = settings.llm.model,
        thinking_type: str = settings.llm.thinking_type,
        temperature: float = settings.llm.temperature,
        max_tokens: int = settings.llm.max_tokens,
        timeout: float = settings.llm.timeout_seconds,
        chat_model: Any | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.llm.api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.thinking_type = thinking_type
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.chat_model = chat_model or self._create_chat_model(timeout=timeout)

    def chat(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Send a prompt to DeepSeek through LangChain and return normalized content."""

        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        runtime_kwargs: dict[str, Any] = {}
        if temperature is not None:
            runtime_kwargs["temperature"] = temperature
        if max_tokens is not None:
            runtime_kwargs["max_tokens"] = max_tokens

        chat_model = self.chat_model.bind(**runtime_kwargs) if runtime_kwargs else self.chat_model
        message = chat_model.invoke(messages)

        return LLMResponse(
            content=self._content_to_text(getattr(message, "content", "")),
            model=self._response_model(message),
            usage=self._response_usage(message),
        )

    def _create_chat_model(self, *, timeout: float) -> Any:
        if not self.api_key:
            raise LLMConfigurationError("缺少 DeepSeek API Key，请设置 DEEPSEEK_API_KEY")

        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise LLMConfigurationError("无法导入 langchain_openai。请安装依赖: pip install langchain-openai") from exc

        extra_body: dict[str, Any] = {}
        if self.thinking_type:
            extra_body["thinking"] = {"type": self.thinking_type}

        return ChatOpenAI(
            model=self.model,
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            timeout=timeout,
            extra_body=extra_body or None,
        )

    @staticmethod
    def _content_to_text(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict) and isinstance(item.get("text"), str):
                    parts.append(item["text"])
                else:
                    parts.append(str(item))
            return "".join(parts)
        return str(content)

    def _response_model(self, message: Any) -> str:
        metadata = getattr(message, "response_metadata", {}) or {}
        return str(metadata.get("model_name") or metadata.get("model") or self.model)

    @staticmethod
    def _response_usage(message: Any) -> dict[str, Any]:
        usage_metadata = getattr(message, "usage_metadata", None)
        if isinstance(usage_metadata, dict):
            return dict(usage_metadata)

        response_metadata = getattr(message, "response_metadata", {}) or {}
        token_usage = response_metadata.get("token_usage") or response_metadata.get("usage")
        return dict(token_usage) if isinstance(token_usage, dict) else {}
