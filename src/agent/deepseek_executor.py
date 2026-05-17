"""DeepSeek tool-calling executor that preserves thinking-mode fields."""

from __future__ import annotations

import json
from collections.abc import Generator
from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.tools import BaseTool
from pydantic import ValidationError

from src.config import settings
from src.llm import DeepSeekClient, LLMConfigurationError


class DeepSeekToolCallingAgentExecutor:
    """Run a tool-calling loop through DeepSeek's OpenAI-compatible API.

    DeepSeek thinking mode requires assistant messages containing tool calls to
    be passed back with provider-specific fields such as ``reasoning_content``.
    LangChain message abstractions can drop those fields, so this executor keeps
    the raw assistant payload in the request history.
    """

    def __init__(
        self,
        *,
        llm_client: DeepSeekClient,
        tools: list[BaseTool],
        system_prompt: str,
        max_iterations: int = 4,
    ) -> None:
        self.llm_client = llm_client
        self.tools = {tool.name: tool for tool in tools}
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations

    def invoke(self, input: dict[str, Any]) -> dict[str, Any]:
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(self._convert_messages(input.get("messages", [])))

        final_message: dict[str, Any] | None = None
        response: Any | None = None
        for iteration in range(self.max_iterations):
            response = self._chat(messages)
            choice = response.choices[0]
            assistant_message = choice.message
            assistant_payload = self._assistant_payload(assistant_message)
            messages.append(assistant_payload)
            final_message = assistant_payload

            tool_calls = assistant_payload.get("tool_calls") or []
            if not tool_calls:
                break

            for tool_call in tool_calls:
                messages.append(self._run_tool_call(tool_call))

            if iteration == self.max_iterations - 1:
                messages.append(
                    {
                        "role": "system",
                        "content": "你已经达到工具调用上限。请停止调用工具，直接根据以上工具结果给出最终中文回答；如果信息不足，请说明缺少哪些信息。",
                    }
                )
                response = self._chat(messages, include_tools=False)
                final_message = self._assistant_payload(response.choices[0].message)
                messages.append(final_message)
                break

        content = "" if final_message is None else str(final_message.get("content") or "").strip()
        if not content:
            content = self._fallback_answer(messages)
        return {
            "messages": [
                AIMessage(
                    content=content,
                    response_metadata={
                        "model_name": getattr(response, "model", self.llm_client.model) if response is not None else self.llm_client.model,
                        "token_usage": self._usage(response),
                    },
                )
            ],
            "raw_messages": messages,
        }

    def invoke_stream(self, input: dict[str, Any]) -> Generator[str, None, dict[str, Any]]:
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(self._convert_messages(input.get("messages", [])))

        total_usage: dict[str, Any] = {}
        for iteration in range(self.max_iterations):
            response = self._chat(messages)
            self._merge_usage(total_usage, self._usage(response))
            assistant_payload = self._assistant_payload(response.choices[0].message)
            tool_calls = assistant_payload.get("tool_calls") or []

            if not tool_calls:
                result = yield from self._stream_final_answer(messages, total_usage=total_usage)
                return result

            messages.append(assistant_payload)

            for tool_call in tool_calls:
                messages.append(self._run_tool_call(tool_call))

            if iteration == self.max_iterations - 1:
                messages.append(
                    {
                        "role": "system",
                        "content": "你已经达到工具调用上限。请停止调用工具，直接根据以上工具结果给出最终中文回答；如果信息不足，请说明缺少哪些信息。",
                    }
                )
                result = yield from self._stream_final_answer(messages, total_usage=total_usage)
                return result

        result = yield from self._stream_final_answer(messages, total_usage=total_usage)
        return result

    def _chat(self, messages: list[dict[str, Any]], *, include_tools: bool = True, stream: bool = False) -> Any:
        if not self.llm_client.api_key:
            raise LLMConfigurationError("缺少 DeepSeek API Key，请设置 DEEPSEEK_API_KEY")

        client = self._client()
        request_messages = [dict(message) for message in messages]
        kwargs: dict[str, Any] = {
            "model": self.llm_client.model,
            "messages": request_messages,
            "temperature": self.llm_client.temperature,
            "max_tokens": self.llm_client.max_tokens,
            "stream": stream,
        }
        if include_tools:
            kwargs["tools"] = [self._tool_schema(tool) for tool in self.tools.values()]
        return client.chat.completions.create(**kwargs)

    def _client(self) -> Any:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMConfigurationError("无法导入 openai。请安装依赖: pip install openai") from exc
        return OpenAI(api_key=self.llm_client.api_key, base_url=self.llm_client.base_url)

    @staticmethod
    def _convert_messages(messages: list[Any]) -> list[dict[str, str]]:
        converted: list[dict[str, str]] = []
        for message in messages:
            message_type = getattr(message, "type", "")
            role = "assistant" if message_type == "ai" else "user"
            converted.append({"role": role, "content": DeepSeekClient._content_to_text(getattr(message, "content", ""))})
        return converted

    @staticmethod
    def _assistant_payload(message: Any) -> dict[str, Any]:
        if hasattr(message, "model_dump"):
            raw = message.model_dump(exclude_none=True)
        else:
            raw = dict(message)
        payload = {key: value for key, value in raw.items() if key in {"role", "content", "tool_calls", "reasoning_content"}}
        payload["role"] = "assistant"
        payload.setdefault("content", "")
        return payload

    def _run_tool_call(self, tool_call: dict[str, Any]) -> dict[str, str]:
        function = tool_call.get("function") or {}
        tool_name = function.get("name")
        tool = self.tools.get(str(tool_name))
        if tool is None:
            content = f"工具 {tool_name} 不存在。"
        else:
            try:
                content = tool.invoke(self._parse_tool_arguments(function.get("arguments")))
            except (ValidationError, ValueError, TypeError) as exc:
                content = f"工具 {tool_name} 调用参数无效：{exc}。请根据工具描述补齐必要参数后重新调用。"
        return {
            "role": "tool",
            "tool_call_id": str(tool_call.get("id") or ""),
            "content": DeepSeekClient._content_to_text(content),
        }

    @staticmethod
    def _parse_tool_arguments(raw_arguments: Any) -> dict[str, Any]:
        if isinstance(raw_arguments, dict):
            return raw_arguments
        if not raw_arguments:
            return {}
        try:
            parsed = json.loads(str(raw_arguments))
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _tool_schema(tool: BaseTool) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.args_schema.model_json_schema() if tool.args_schema is not None else {"type": "object", "properties": {}},
            },
        }

    @staticmethod
    def _usage(response: Any) -> dict[str, Any]:
        if response is None:
            return {}
        usage = getattr(response, "usage", None)
        if usage is None:
            return {}
        if hasattr(usage, "model_dump"):
            return usage.model_dump(exclude_none=True)
        if isinstance(usage, dict):
            return dict(usage)
        return {}

    def _stream_final_answer(
        self,
        messages: list[dict[str, Any]],
        *,
        total_usage: dict[str, Any] | None = None,
    ) -> Generator[str, None, dict[str, Any]]:
        final_messages = [dict(message) for message in messages]
        final_messages.append(
            {
                "role": "system",
                "content": "请基于以上上下文直接给出最终中文回答，不要继续调用工具，也不要输出内部推理过程。",
            }
        )
        stream = self._chat(final_messages, include_tools=False, stream=True)
        content_parts: list[str] = []
        usage = dict(total_usage or {})
        model_name = self.llm_client.model

        for chunk in stream:
            chunk_model = getattr(chunk, "model", None)
            if chunk_model:
                model_name = str(chunk_model)
            self._merge_usage(usage, self._usage(chunk))
            piece = self._stream_chunk_text(chunk)
            if piece:
                content_parts.append(piece)
                yield piece

        content = "".join(content_parts).strip()
        if not content:
            content = self._fallback_answer(messages)
        return {
            "messages": [
                AIMessage(
                    content=content,
                    response_metadata={
                        "model_name": model_name,
                        "token_usage": usage,
                    },
                )
            ],
            "raw_messages": messages + [{"role": "assistant", "content": content}],
        }

    @staticmethod
    def _stream_chunk_text(chunk: Any) -> str:
        choices = getattr(chunk, "choices", None) or []
        if not choices:
            return ""
        delta = getattr(choices[0], "delta", None)
        if delta is None and isinstance(choices[0], dict):
            delta = choices[0].get("delta")
        if delta is None:
            return ""
        content = getattr(delta, "content", None)
        if content is None and isinstance(delta, dict):
            content = delta.get("content")
        return DeepSeekClient._content_to_text(content) if content else ""

    @staticmethod
    def _merge_usage(target: dict[str, Any], source: dict[str, Any]) -> None:
        for key, value in source.items():
            if isinstance(value, (int, float)) and isinstance(target.get(key), (int, float)):
                target[key] = target[key] + value
            elif isinstance(value, (int, float)) and key not in target:
                target[key] = value
            else:
                target[key] = value

    @staticmethod
    def _fallback_answer(messages: list[dict[str, Any]]) -> str:
        tool_contents = [str(message.get("content") or "").strip() for message in messages if message.get("role") == "tool" and str(message.get("content") or "").strip()]
        if tool_contents:
            latest = tool_contents[-1]
            return f"工具调用已达到上限，未能继续生成完整回答。最近一次工具结果如下：\n\n{latest}"
        return "工具调用已达到上限，未能生成完整回答。请补充更明确的需求后重试。"
