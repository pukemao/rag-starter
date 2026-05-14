from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from langchain_core.tools import tool

from src.agent.deepseek_executor import DeepSeekToolCallingAgentExecutor
from src.llm import DeepSeekClient


class FakeCompletions:
    def __init__(self) -> None:
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        if len(self.requests) == 1:
            return SimpleNamespace(
                model="deepseek-test",
                usage=SimpleNamespace(model_dump=lambda exclude_none=True: {"total_tokens": 3}),
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            model_dump=lambda exclude_none=True: {
                                "role": "assistant",
                                "content": "",
                                "reasoning_content": "需要查询知识库",
                                "tool_calls": [
                                    {
                                        "id": "call-1",
                                        "type": "function",
                                        "function": {"name": "search_knowledge_base", "arguments": '{"query":"项目背景","k":1}'},
                                    }
                                ],
                            }
                        )
                    )
                ],
            )
        return SimpleNamespace(
            model="deepseek-test",
            usage=SimpleNamespace(model_dump=lambda exclude_none=True: {"total_tokens": 8}),
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        model_dump=lambda exclude_none=True: {
                            "role": "assistant",
                            "content": "最终回答",
                        }
                    )
                )
            ],
        )


class FakeOpenAI:
    completions = FakeCompletions()

    def __init__(self, **kwargs):
        self.chat = SimpleNamespace(completions=self.completions)


class FakeInvalidToolCompletions:
    def __init__(self) -> None:
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        if len(self.requests) == 1:
            return SimpleNamespace(
                model="deepseek-test",
                usage=SimpleNamespace(model_dump=lambda exclude_none=True: {"total_tokens": 3}),
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            model_dump=lambda exclude_none=True: {
                                "role": "assistant",
                                "content": "",
                                "tool_calls": [
                                    {
                                        "id": "call-2",
                                        "type": "function",
                                        "function": {"name": "strict_tool", "arguments": "{}"},
                                    }
                                ],
                            }
                        )
                    )
                ],
            )
        return SimpleNamespace(
            model="deepseek-test",
            usage=SimpleNamespace(model_dump=lambda exclude_none=True: {"total_tokens": 8}),
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        model_dump=lambda exclude_none=True: {
                            "role": "assistant",
                            "content": "参数缺失，请补充内容。",
                        }
                    )
                )
            ],
        )


class FakeInvalidToolOpenAI:
    completions = FakeInvalidToolCompletions()

    def __init__(self, **kwargs):
        self.chat = SimpleNamespace(completions=self.completions)


class DeepSeekAgentExecutorTests(unittest.TestCase):
    def test_preserves_reasoning_content_when_sending_tool_result(self):
        @tool("search_knowledge_base", description="检索知识库")
        def search_knowledge_base(query: str, k: int = 1) -> str:
            return f"参考段落: {query}, k={k}"

        executor = DeepSeekToolCallingAgentExecutor(
            llm_client=DeepSeekClient(api_key="sk-test", model="deepseek-test", chat_model=object()),
            tools=[search_knowledge_base],
            system_prompt="系统提示词",
        )

        with patch.dict("sys.modules", {"openai": SimpleNamespace(OpenAI=FakeOpenAI)}):
            result = executor.invoke({"messages": [SimpleNamespace(type="human", content="项目背景是什么？")]})

        self.assertEqual(result["messages"][0].content, "最终回答")
        self.assertEqual(FakeOpenAI.completions.requests[0]["tools"][0]["function"]["name"], "search_knowledge_base")
        self.assertIn("parameters", FakeOpenAI.completions.requests[0]["tools"][0]["function"])
        second_messages = FakeOpenAI.completions.requests[1]["messages"]
        assistant_payload = next(message for message in second_messages if message.get("reasoning_content") == "需要查询知识库")
        tool_payload = next(message for message in second_messages if message.get("role") == "tool")
        self.assertEqual(assistant_payload["role"], "assistant")
        self.assertEqual(assistant_payload["reasoning_content"], "需要查询知识库")
        self.assertEqual(assistant_payload["tool_calls"][0]["id"], "call-1")
        self.assertEqual(tool_payload["role"], "tool")
        self.assertEqual(tool_payload["tool_call_id"], "call-1")
        self.assertIn("参考段落: 项目背景", tool_payload["content"])

    def test_returns_tool_validation_error_to_model(self):
        @tool("strict_tool", description="严格参数工具")
        def strict_tool(content: str) -> str:
            return content

        executor = DeepSeekToolCallingAgentExecutor(
            llm_client=DeepSeekClient(api_key="sk-test", model="deepseek-test", chat_model=object()),
            tools=[strict_tool],
            system_prompt="系统提示词",
        )

        FakeInvalidToolOpenAI.completions = FakeInvalidToolCompletions()
        with patch.dict("sys.modules", {"openai": SimpleNamespace(OpenAI=FakeInvalidToolOpenAI)}):
            result = executor.invoke({"messages": [SimpleNamespace(type="human", content="生成文档")]})

        self.assertEqual(result["messages"][0].content, "参数缺失，请补充内容。")
        second_messages = FakeInvalidToolOpenAI.completions.requests[1]["messages"]
        tool_payload = next(message for message in second_messages if message.get("role") == "tool")
        self.assertIn("调用参数无效", tool_payload["content"])
        self.assertIn("strict_tool", tool_payload["content"])


if __name__ == "__main__":
    unittest.main()
