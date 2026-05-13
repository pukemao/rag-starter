from __future__ import annotations

import unittest

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.llm import DeepSeekClient, LLMConfigurationError


class FakeChatModel:
    def __init__(self) -> None:
        self.messages = []
        self.bound_kwargs = []

    def bind(self, **kwargs):
        self.bound_kwargs.append(kwargs)
        return self

    def invoke(self, messages):
        self.messages.append(messages)
        return AIMessage(
            content="回答内容",
            response_metadata={"model_name": "deepseek-test", "token_usage": {"total_tokens": 6}},
        )


class DeepSeekClientTests(unittest.TestCase):
    def test_chat_uses_langchain_chat_model(self):
        chat_model = FakeChatModel()
        client = DeepSeekClient(
            api_key="sk-test",
            base_url="https://api.deepseek.com/",
            model="deepseek-test",
            chat_model=chat_model,
        )

        response = client.chat("用户提示词", system_prompt="系统提示词", temperature=0.1, max_tokens=128)

        self.assertEqual(response.content, "回答内容")
        self.assertEqual(response.model, "deepseek-test")
        self.assertEqual(response.usage, {"total_tokens": 6})
        self.assertIsInstance(chat_model.messages[0][0], SystemMessage)
        self.assertIsInstance(chat_model.messages[0][1], HumanMessage)
        self.assertEqual(chat_model.messages[0][0].content, "系统提示词")
        self.assertEqual(chat_model.messages[0][1].content, "用户提示词")
        self.assertEqual(chat_model.bound_kwargs[0], {"temperature": 0.1, "max_tokens": 128})

    def test_chat_requires_api_key(self):
        with self.assertRaisesRegex(LLMConfigurationError, "DEEPSEEK_API_KEY"):
            DeepSeekClient(api_key="")


if __name__ == "__main__":
    unittest.main()
