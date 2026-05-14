from __future__ import annotations

import unittest

from src.agent.tools import (
    GET_CURRENT_DATE_DESCRIPTION,
    GET_CURRENT_LOCATION_CITY_DESCRIPTION,
    QUERY_WEATHER_DESCRIPTION,
    SEARCH_KNOWLEDGE_BASE_DESCRIPTION,
    GENERATE_DOCUMENT_DESCRIPTION,
    READ_UPLOADED_DOCUMENT_DESCRIPTION,
    AgentToolContext,
    create_agent_tools,
)
from src.agent.weather import WeatherResult
from src.vector_store import SearchResult


class FakeVectorService:
    def __init__(self) -> None:
        self.search_requests = []

    def search(self, query, *, k=2, filter=None):
        self.search_requests.append({"query": query, "k": k, "filter": filter})
        return [SearchResult(page_content="知识库段落", metadata={"source": "doc.md"}, score=0.12)]


class FakeWeatherService:
    def __init__(self) -> None:
        self.requests = []

    def get_weather(self, *, city, target_date):
        self.requests.append({"city": city, "target_date": target_date})
        return WeatherResult(
            city=city,
            country="中国",
            date=target_date,
            summary="晴",
            temperature_min=18,
            temperature_max=26,
            precipitation_probability=10,
            wind_speed_max=12,
        )


class FakeDocumentGenerator:
    def __init__(self) -> None:
        self.requests = []

    def generate(self, *, content, document_type, filename=None):
        from src.document_generator import DocumentAttachment

        self.requests.append({"content": content, "document_type": document_type, "filename": filename})
        return DocumentAttachment(
            file_id="doc123",
            filename=filename or "generated.md",
            document_type=document_type,
            mime_type="text/markdown",
            download_url="/generated-documents/doc123/download",
            size=10,
            created_at="2026-05-14T00:00:00+00:00",
        )


class FakeChatFileService:
    def __init__(self) -> None:
        self.requests = []

    def read(self, *, file_ids, file_id=None, query=None, max_chars=None):
        self.requests.append({"file_ids": file_ids, "file_id": file_id, "query": query, "max_chars": max_chars})
        return "文件：demo.md\n\n[片段 1]\n上传文件内容"


class AgentToolTests(unittest.TestCase):
    def test_search_knowledge_base_tool_uses_explicit_description(self):
        context = AgentToolContext(references=[])
        tools = create_agent_tools(vector_service=FakeVectorService(), context=context, default_k=2)

        tool_by_name = {tool.name: tool for tool in tools}
        self.assertEqual(tool_by_name["search_knowledge_base"].description, SEARCH_KNOWLEDGE_BASE_DESCRIPTION.strip())
        self.assertEqual(tool_by_name["get_current_date"].description, GET_CURRENT_DATE_DESCRIPTION.strip())
        self.assertEqual(tool_by_name["get_current_location_city"].description, GET_CURRENT_LOCATION_CITY_DESCRIPTION.strip())
        self.assertEqual(tool_by_name["query_weather"].description, QUERY_WEATHER_DESCRIPTION.strip())
        self.assertEqual(tool_by_name["generate_document"].description, GENERATE_DOCUMENT_DESCRIPTION.strip())
        self.assertEqual(tool_by_name["read_uploaded_document"].description, READ_UPLOADED_DOCUMENT_DESCRIPTION.strip())
        self.assertIn("工具能力", tool_by_name["query_weather"].description)
        self.assertIn("参数说明", tool_by_name["query_weather"].description)
        self.assertIn("结果输出说明", tool_by_name["query_weather"].description)

    def test_search_knowledge_base_tool_collects_references(self):
        vector_service = FakeVectorService()
        context = AgentToolContext(references=[])
        tool = create_agent_tools(vector_service=vector_service, context=context, default_k=2)[0]

        output = tool.invoke({"query": "检索知识库", "k": 1})

        self.assertIn("知识库段落", output)
        self.assertTrue(context.used_rag)
        self.assertEqual(context.references[0].page_content, "知识库段落")
        self.assertEqual(vector_service.search_requests[0], {"query": "检索知识库", "k": 1, "filter": None})

    def test_weather_tools(self):
        weather_service = FakeWeatherService()
        context = AgentToolContext(references=[])
        tools = {
            tool.name: tool
            for tool in create_agent_tools(
                vector_service=FakeVectorService(),
                context=context,
                weather_service=weather_service,
                default_k=2,
            )
        }

        date_output = tools["get_current_date"].invoke({})
        city_output = tools["get_current_location_city"].invoke({})
        weather_output = tools["query_weather"].invoke({"city": "上海", "date": "2026-05-14"})

        self.assertIn("当前日期", date_output)
        self.assertIn("默认城市", city_output)
        self.assertIn("城市：上海，中国", weather_output)
        self.assertIn("天气：晴", weather_output)
        self.assertEqual(weather_service.requests[0], {"city": "上海", "target_date": "2026-05-14"})

    def test_generate_document_tool_collects_attachments(self):
        generator = FakeDocumentGenerator()
        context = AgentToolContext(references=[])
        tools = {
            tool.name: tool
            for tool in create_agent_tools(
                vector_service=FakeVectorService(),
                context=context,
                document_generator=generator,
                default_k=2,
            )
        }

        output = tools["generate_document"].invoke({"content": "# 报告", "document_type": "markdown", "filename": "报告.md"})

        self.assertIn("文档已生成", output)
        self.assertEqual(generator.requests[0], {"content": "# 报告", "document_type": "markdown", "filename": "报告.md"})
        self.assertEqual(context.attachments[0]["file_id"], "doc123")
        self.assertEqual(context.attachments[0]["filename"], "报告.md")

    def test_read_uploaded_document_tool_uses_context_file_ids(self):
        chat_files = FakeChatFileService()
        context = AgentToolContext(references=[], file_ids=["file123"])
        tools = {
            tool.name: tool
            for tool in create_agent_tools(
                vector_service=FakeVectorService(),
                context=context,
                chat_file_service=chat_files,
                default_k=2,
            )
        }

        output = tools["read_uploaded_document"].invoke({"query": "摘要", "max_chars": 1200})

        self.assertIn("上传文件内容", output)
        self.assertEqual(chat_files.requests[0], {"file_ids": ["file123"], "file_id": None, "query": "摘要", "max_chars": 1200})


if __name__ == "__main__":
    unittest.main()
