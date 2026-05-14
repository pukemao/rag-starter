from __future__ import annotations

import unittest

from src.agent.tools import SEARCH_KNOWLEDGE_BASE_DESCRIPTION, AgentToolContext, create_agent_tools
from src.vector_store import SearchResult


class FakeVectorService:
    def __init__(self) -> None:
        self.search_requests = []

    def search(self, query, *, k=2, filter=None):
        self.search_requests.append({"query": query, "k": k, "filter": filter})
        return [SearchResult(page_content="知识库段落", metadata={"source": "doc.md"}, score=0.12)]


class AgentToolTests(unittest.TestCase):
    def test_search_knowledge_base_tool_uses_explicit_description(self):
        context = AgentToolContext(references=[])
        tools = create_agent_tools(vector_service=FakeVectorService(), context=context, default_k=2)

        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0].name, "search_knowledge_base")
        self.assertEqual(tools[0].description, SEARCH_KNOWLEDGE_BASE_DESCRIPTION.strip())
        self.assertIn("工具能力", tools[0].description)
        self.assertIn("参数说明", tools[0].description)
        self.assertIn("结果输出说明", tools[0].description)
        self.assertIn("不应调用的场景", tools[0].description)

    def test_search_knowledge_base_tool_collects_references(self):
        vector_service = FakeVectorService()
        context = AgentToolContext(references=[])
        tool = create_agent_tools(vector_service=vector_service, context=context, default_k=2)[0]

        output = tool.invoke({"query": "检索知识库", "k": 1})

        self.assertIn("知识库段落", output)
        self.assertTrue(context.used_rag)
        self.assertEqual(context.references[0].page_content, "知识库段落")
        self.assertEqual(vector_service.search_requests[0], {"query": "检索知识库", "k": 1, "filter": None})


if __name__ == "__main__":
    unittest.main()
