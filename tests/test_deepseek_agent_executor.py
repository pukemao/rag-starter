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


class FakeLoopingToolCompletions:
    def __init__(self) -> None:
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        if "tools" not in kwargs:
            return SimpleNamespace(
                model="deepseek-test",
                usage=SimpleNamespace(model_dump=lambda exclude_none=True: {"total_tokens": 10}),
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            model_dump=lambda exclude_none=True: {
                                "role": "assistant",
                                "content": "已根据工具结果给出最终回答。",
                            }
                        )
                    )
                ],
            )
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
                                    "id": f"call-{len(self.requests)}",
                                    "type": "function",
                                    "function": {"name": "loop_tool", "arguments": "{}"},
                                }
                            ],
                        }
                    )
                )
            ],
        )


class FakeLoopingToolOpenAI:
    completions = FakeLoopingToolCompletions()

    def __init__(self, **kwargs):
        self.chat = SimpleNamespace(completions=self.completions)


class FakeStreamChunk:
    def __init__(self, content: str = "", *, model: str = "deepseek-test", usage: dict | None = None) -> None:
        self.model = model
        self.usage = SimpleNamespace(model_dump=lambda exclude_none=True: usage or {}) if usage is not None else None
        self.choices = [SimpleNamespace(delta=SimpleNamespace(content=content))]


class FakeStreamingCompletions:
    def __init__(self) -> None:
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        if kwargs.get("stream"):
            return iter(
                [
                    FakeStreamChunk("最终", usage={"completion_tokens": 1}),
                    FakeStreamChunk("回答", usage={"completion_tokens": 1}),
                ]
            )
        return SimpleNamespace(
            model="deepseek-test",
            usage=SimpleNamespace(model_dump=lambda exclude_none=True: {"prompt_tokens": 3}),
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        model_dump=lambda exclude_none=True: {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [
                                {
                                    "id": "call-stream",
                                    "type": "function",
                                    "function": {"name": "search_knowledge_base", "arguments": '{"query":"项目背景","k":1}'},
                                }
                            ],
                        }
                    )
                )
            ],
        )


class FakeStreamingOpenAI:
    completions = FakeStreamingCompletions()

    def __init__(self, **kwargs):
        self.chat = SimpleNamespace(completions=self.completions)


class DeepSeekAgentExecutorTests(unittest.TestCase):
    @staticmethod
    def _assert_tool_calls_are_followed_by_tool_messages(messages):
        for index, message in enumerate(messages):
            tool_calls = message.get("tool_calls") or []
            if not tool_calls:
                continue
            following = messages[index + 1 : index + 1 + len(tool_calls)]
            expected_ids = [tool_call["id"] for tool_call in tool_calls]
            actual_ids = [item.get("tool_call_id") for item in following if item.get("role") == "tool"]
            if actual_ids != expected_ids:
                raise AssertionError(f"tool_calls {expected_ids} were not followed by matching tool messages: {actual_ids}")

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

    def test_forces_final_answer_when_tool_iterations_reach_limit(self):
        @tool("loop_tool", description="循环工具")
        def loop_tool() -> str:
            return "工具结果"

        executor = DeepSeekToolCallingAgentExecutor(
            llm_client=DeepSeekClient(api_key="sk-test", model="deepseek-test", chat_model=object()),
            tools=[loop_tool],
            system_prompt="系统提示词",
            max_iterations=2,
        )

        FakeLoopingToolOpenAI.completions = FakeLoopingToolCompletions()
        with patch.dict("sys.modules", {"openai": SimpleNamespace(OpenAI=FakeLoopingToolOpenAI)}):
            result = executor.invoke({"messages": [SimpleNamespace(type="human", content="请连续调用工具")]})

        self.assertEqual(result["messages"][0].content, "已根据工具结果给出最终回答。")
        self.assertEqual(len(FakeLoopingToolOpenAI.completions.requests), 3)
        self.assertNotIn("tools", FakeLoopingToolOpenAI.completions.requests[-1])
        self.assertTrue(any(message.get("role") == "system" and "停止调用工具" in message.get("content", "") for message in result["raw_messages"]))
        self._assert_tool_calls_are_followed_by_tool_messages(FakeLoopingToolOpenAI.completions.requests[-1]["messages"])

    def test_streams_final_answer_tokens_after_tool_calls(self):
        @tool("search_knowledge_base", description="检索知识库")
        def search_knowledge_base(query: str, k: int = 1) -> str:
            return f"参考段落: {query}, k={k}"

        executor = DeepSeekToolCallingAgentExecutor(
            llm_client=DeepSeekClient(api_key="sk-test", model="deepseek-test", chat_model=object()),
            tools=[search_knowledge_base],
            system_prompt="系统提示词",
        )

        FakeStreamingOpenAI.completions = FakeStreamingCompletions()
        with patch.dict("sys.modules", {"openai": SimpleNamespace(OpenAI=FakeStreamingOpenAI)}):
            stream = executor.invoke_stream({"messages": [SimpleNamespace(type="human", content="项目背景是什么？")]})
            chunks = []
            try:
                while True:
                    chunks.append(next(stream))
            except StopIteration as stop:
                result = stop.value

        self.assertEqual(chunks, ["最终", "回答"])
        self.assertEqual(result["messages"][0].content, "最终回答")
        self.assertEqual(result["messages"][0].response_metadata["token_usage"]["prompt_tokens"], 12)
        self.assertEqual(result["messages"][0].response_metadata["token_usage"]["completion_tokens"], 2)
        self.assertTrue(FakeStreamingOpenAI.completions.requests[-1]["stream"])
        self.assertNotIn("tools", FakeStreamingOpenAI.completions.requests[-1])


if __name__ == "__main__":
    unittest.main()
