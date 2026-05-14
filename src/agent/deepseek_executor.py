"""DeepSeek tool-calling executor that preserves thinking-mode fields."""

from __future__ import annotations

import json
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
        for _ in range(self.max_iterations):
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
        else:
            raise RuntimeError("Agent 工具调用超过最大轮数")

        content = "" if final_message is None else str(final_message.get("content") or "")
        return {
            "messages": [
                AIMessage(
                    content=content,
                    response_metadata={
                        "model_name": getattr(response, "model", self.llm_client.model),
                        "token_usage": self._usage(response),
                    },
                )
            ],
            "raw_messages": messages,
        }

    def _chat(self, messages: list[dict[str, Any]]) -> Any:
        if not self.llm_client.api_key:
            raise LLMConfigurationError("缺少 DeepSeek API Key，请设置 DEEPSEEK_API_KEY")

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMConfigurationError("无法导入 openai。请安装依赖: pip install openai") from exc

        client = OpenAI(api_key=self.llm_client.api_key, base_url=self.llm_client.base_url)
        request_messages = [dict(message) for message in messages]
        return client.chat.completions.create(
            model=self.llm_client.model,
            messages=request_messages,
            tools=[self._tool_schema(tool) for tool in self.tools.values()],
            temperature=self.llm_client.temperature,
            max_tokens=self.llm_client.max_tokens,
        )

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
        usage = getattr(response, "usage", None)
        if usage is None:
            return {}
        if hasattr(usage, "model_dump"):
            return usage.model_dump(exclude_none=True)
        if isinstance(usage, dict):
            return dict(usage)
        return {}
