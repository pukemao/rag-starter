from __future__ import annotations

import unittest

from src.llm import DeepSeekClient, LLMConfigurationError


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "model": "deepseek-test",
            "choices": [{"message": {"content": "回答内容"}}],
            "usage": {"total_tokens": 6},
        }


class FakeHttpClient:
    def __init__(self) -> None:
        self.requests = []

    def post(self, url, *, headers=None, json=None):
        self.requests.append({"url": url, "headers": headers, "json": json})
        return FakeResponse()


class DeepSeekClientTests(unittest.TestCase):
    def test_chat_calls_openai_compatible_endpoint(self):
        http_client = FakeHttpClient()
        client = DeepSeekClient(
            api_key="sk-test",
            base_url="https://api.deepseek.com/",
            model="deepseek-test",
            http_client=http_client,
        )

        response = client.chat("用户提示词", system_prompt="系统提示词", temperature=0.1, max_tokens=128)

        self.assertEqual(response.content, "回答内容")
        self.assertEqual(response.model, "deepseek-test")
        self.assertEqual(response.usage, {"total_tokens": 6})
        request = http_client.requests[0]
        self.assertEqual(request["url"], "https://api.deepseek.com/chat/completions")
        self.assertEqual(request["headers"]["Authorization"], "Bearer sk-test")
        self.assertEqual(request["json"]["messages"][0], {"role": "system", "content": "系统提示词"})
        self.assertEqual(request["json"]["messages"][1], {"role": "user", "content": "用户提示词"})
        self.assertEqual(request["json"]["temperature"], 0.1)
        self.assertEqual(request["json"]["max_tokens"], 128)

    def test_chat_requires_api_key(self):
        client = DeepSeekClient(api_key="", http_client=FakeHttpClient())

        with self.assertRaisesRegex(LLMConfigurationError, "DEEPSEEK_API_KEY"):
            client.chat("hello")


if __name__ == "__main__":
    unittest.main()
