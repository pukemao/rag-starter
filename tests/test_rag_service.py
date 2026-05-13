from __future__ import annotations

import unittest

from src.llm import LLMResponse
from src.rag import RagService
from src.vector_store import SearchResult


class FakeVectorService:
    def __init__(self) -> None:
        self.search_requests = []

    def search(self, query, *, k=4, filter=None):
        self.search_requests.append({"query": query, "k": k, "filter": filter})
        return [
            SearchResult(page_content="第一段知识库内容", metadata={"source": "a.md"}, score=0.12),
            SearchResult(page_content="第二段知识库内容", metadata={"source_id": "source-2"}, score=0.34),
        ]


class FakeLlmClient:
    model = "deepseek-test"

    def __init__(self) -> None:
        self.chat_requests = []

    def chat(self, prompt, *, system_prompt=None, temperature=None, max_tokens=None):
        self.chat_requests.append(
            {
                "prompt": prompt,
                "system_prompt": system_prompt,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        return LLMResponse(content="模型回答", model=self.model, usage={"total_tokens": 10})


class RagServiceTests(unittest.TestCase):
    def test_answer_retrieves_context_and_calls_llm(self):
        vector_service = FakeVectorService()
        llm_client = FakeLlmClient()
        service = RagService(vector_service=vector_service, llm_client=llm_client, system_prompt="系统提示词")

        result = service.answer(" 原始问题是什么？ ", k=2, filter={"source": "a.md"}, temperature=0.1, max_tokens=256)

        self.assertEqual(result.answer, "模型回答")
        self.assertEqual(result.question, "原始问题是什么？")
        self.assertEqual(result.model, "deepseek-test")
        self.assertEqual(result.usage, {"total_tokens": 10})
        self.assertEqual(len(result.references), 2)
        self.assertIn("原始问题是什么？", result.prompt)
        self.assertIn("第一段知识库内容", result.prompt)
        self.assertIn("[1] source=a.md，score=0.12", result.prompt)
        self.assertEqual(vector_service.search_requests[0], {"query": "原始问题是什么？", "k": 2, "filter": {"source": "a.md"}})
        self.assertEqual(llm_client.chat_requests[0]["system_prompt"], "系统提示词")
        self.assertEqual(llm_client.chat_requests[0]["temperature"], 0.1)
        self.assertEqual(llm_client.chat_requests[0]["max_tokens"], 256)

    def test_answer_rejects_empty_question(self):
        service = RagService(vector_service=FakeVectorService(), llm_client=FakeLlmClient())

        with self.assertRaisesRegex(ValueError, "question 不能为空"):
            service.answer(" ")


if __name__ == "__main__":
    unittest.main()
