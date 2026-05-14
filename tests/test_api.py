from __future__ import annotations

import unittest
from unittest.mock import patch

from src.vector_store import KnowledgeFile
from src.agent import AgentAnswer
from src.rag import RagAnswer, RagReference
from src.vector_store import IndexResult, SearchResult


class FakeService:
    def __init__(self) -> None:
        self.add_requests = []
        self.delete_requests = []
        self.search_requests = []
        self.existing_file_hashes = set()

    def add_file(self, path, **kwargs):
        self.add_requests.append((path, kwargs))
        return ["id-1", "id-2"]

    def index_file(self, path, **kwargs):
        self.add_requests.append((path, kwargs))
        return IndexResult(ids=["id-1", "id-2"], input_count=3, added_count=2, skipped_duplicates=1)

    def file_exists(self, file_hash):
        return file_hash in self.existing_file_hashes

    @staticmethod
    def compute_content_hash(content):
        from hashlib import sha256

        return sha256(content).hexdigest()

    def delete(self, *, ids=None, source=None, source_id=None):
        self.delete_requests.append({"ids": ids, "source": source, "source_id": source_id})
        return len(ids or [])

    def list_files(self):
        return [
            KnowledgeFile(
                filename="a.txt",
                source="a.txt",
                source_id="source-a",
                file_hash="hash-a",
                chunk_count=2,
                chunk_ids=["id-1", "id-2"],
            )
        ]

    def search(self, query, *, k=4, filter=None):
        self.search_requests.append({"query": query, "k": k, "filter": filter})
        return [SearchResult(page_content="hello", metadata={"source": "a.txt"}, score=0.5)]


class FakeRagService:
    def __init__(self) -> None:
        self.answer_requests = []

    def answer(self, question, *, k=4, filter=None, history=None, system_prompt=None, temperature=None, max_tokens=None):
        self.answer_requests.append(
            {
                "question": question,
                "k": k,
                "filter": filter,
                "history": history,
                "system_prompt": system_prompt,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        return RagAnswer(
            answer="rag answer",
            question=question,
            prompt="prompt with references",
            references=[RagReference(index=1, page_content="hello", metadata={"source": "a.txt"}, score=0.5)],
            model="deepseek-test",
            usage={"total_tokens": 8},
        )


class FakeAgentService:
    def __init__(self) -> None:
        self.answer_requests = []

    def answer(self, question, *, k=2, history=None):
        self.answer_requests.append({"question": question, "k": k, "history": history})
        return AgentAnswer(
            answer="agent answer",
            question=question,
            prompt="agent prompt",
            used_rag=True,
            references=[RagReference(index=1, page_content="hello", metadata={"source": "a.txt"}, score=0.5)],
            attachments=[
                {
                    "file_id": "doc123",
                    "filename": "报告.md",
                    "document_type": "markdown",
                    "mime_type": "text/markdown; charset=utf-8",
                    "download_url": "/generated-documents/doc123/download",
                    "size": 12,
                    "created_at": "2026-05-14T00:00:00+00:00",
                }
            ],
            model="deepseek-test",
            usage={"total_tokens": 9},
        )


class ApiTests(unittest.TestCase):
    def setUp(self):
        try:
            from fastapi.testclient import TestClient
        except ImportError as exc:
            self.skipTest(f"FastAPI 未安装: {exc}")

        from src.api import create_app
        from src.storage import StorageService, create_session_factory

        self.service = FakeService()
        self.rag_service = FakeRagService()
        self.agent_service = FakeAgentService()
        self.storage_service = StorageService(create_session_factory("sqlite:///:memory:"))
        self.client = TestClient(
            create_app(
                service=self.service,
                rag_service=self.rag_service,
                agent_service=self.agent_service,
                storage_service=self.storage_service,
            )
        )

    def test_health(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_add_document(self):
        response = self.client.post(
            "/documents",
            json={"path": "data/a.md", "chunk_size": 500, "chunk_overlap": 50},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"ids": ["id-1", "id-2"], "count": 2, "input_count": 3, "skipped_duplicates": 1},
        )
        self.assertEqual(self.service.add_requests[0][0], "data/a.md")
        self.assertEqual(self.service.add_requests[0][1]["chunk_size"], 500)

    def test_list_documents(self):
        response = self.client.get("/documents")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "files": [
                    {
                        "filename": "a.txt",
                        "source": "a.txt",
                        "source_id": "source-a",
                        "file_hash": "hash-a",
                        "chunk_count": 2,
                        "chunk_ids": ["id-1", "id-2"],
                    }
                ],
                "total_files": 1,
                "total_chunks": 2,
            },
        )

    def test_index_upload(self):
        response = self.client.post(
            "/index",
            data={"splitter_type": "recursive", "chunk_size": "512", "chunk_overlap": "32"},
            files=[
                ("files", ("note.md", b"# title\n\nbody", "text/markdown")),
                ("files", ("notes.txt", b"alpha beta", "text/plain")),
            ],
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total_files"], 2)
        self.assertEqual(payload["total_chunks"], 4)
        self.assertEqual(payload["total_input_chunks"], 6)
        self.assertEqual(payload["total_skipped_duplicates"], 2)
        self.assertEqual([item["filename"] for item in payload["files"]], ["note.md", "notes.txt"])
        self.assertEqual(payload["files"][0]["input_count"], 3)
        self.assertEqual(payload["files"][0]["skipped_duplicates"], 1)
        self.assertEqual(len(self.service.add_requests), 2)
        first_call = self.service.add_requests[0][1]
        self.assertEqual(first_call["splitter_type"], "recursive")
        self.assertEqual(first_call["chunk_size"], 512)
        self.assertEqual(first_call["chunk_overlap"], 32)
        self.assertEqual(first_call["source_label"], "note.md")
        self.assertTrue(first_call["source_id"])
        self.assertTrue(first_call["file_hash"])

    def test_index_upload_rejects_duplicate_file_in_same_request(self):
        response = self.client.post(
            "/index",
            files=[
                ("files", ("first.txt", b"same content", "text/plain")),
                ("files", ("second.txt", b"same content", "text/plain")),
            ],
        )

        self.assertEqual(response.status_code, 409)
        self.assertIn("不允许重复上传", response.json()["detail"]["message"])
        self.assertEqual(response.json()["detail"]["filename"], "second.txt")
        self.assertEqual(len(self.service.add_requests), 0)

    def test_index_upload_rejects_existing_file_hash(self):
        file_content = b"already indexed"
        self.service.existing_file_hashes.add(self.service.compute_content_hash(file_content))

        response = self.client.post(
            "/index",
            files=[("files", ("exists.txt", file_content, "text/plain"))],
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"]["filename"], "exists.txt")
        self.assertIn("message", response.json()["detail"])
        self.assertEqual(len(self.service.add_requests), 0)

    def test_delete_document(self):
        response = self.client.request("DELETE", "/documents", json={"ids": ["id-1"], "source_id": "source-a"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"deleted": 1})
        self.assertEqual(self.service.delete_requests[0], {"ids": ["id-1"], "source": None, "source_id": "source-a"})

    def test_search(self):
        response = self.client.post("/search", json={"query": "hello", "k": 1})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"results": [{"page_content": "hello", "metadata": {"source": "a.txt"}, "score": 0.5}]},
        )

    def test_chat(self):
        from src.llm import LLMResponse

        class FakeDeepSeekClient:
            def chat(self, prompt, *, system_prompt=None, temperature=None, max_tokens=None):
                self.prompt = prompt
                self.system_prompt = system_prompt
                self.temperature = temperature
                self.max_tokens = max_tokens
                return LLMResponse(content="chat answer", model="deepseek-test", usage={"total_tokens": 6})

        fake_client = FakeDeepSeekClient()
        with patch("src.api.app.DeepSeekClient", return_value=fake_client):
            response = self.client.post(
                "/chat",
                json={
                    "message": "继续说明",
                    "history": [{"role": "user", "content": "前面的问题"}],
                    "temperature": 0.1,
                    "max_tokens": 128,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["answer"], "chat answer")
        self.assertEqual(response.json()["session"]["messages"][0]["content"], "继续说明")
        self.assertEqual(response.json()["session"]["messages"][1]["content"], "chat answer")
        self.assertIn("前面的问题", response.json()["prompt"])
        self.assertIn("继续说明", response.json()["prompt"])
        self.assertEqual(fake_client.temperature, 0.1)
        self.assertEqual(fake_client.max_tokens, 128)

    def test_rag_chat(self):
        response = self.client.post(
            "/rag/chat",
            json={
                "question": "hello?",
                "k": 1,
                "filter": {"source": "a.txt"},
                "history": [{"role": "user", "content": "上一个问题"}],
                "temperature": 0.1,
                "max_tokens": 128,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "answer": "rag answer",
                "question": "hello?",
                "prompt": "prompt with references",
                "references": [{"index": 1, "page_content": "hello", "metadata": {"source": "a.txt"}, "score": 0.5}],
                "model": "deepseek-test",
                "usage": {"total_tokens": 8},
                "session": response.json()["session"],
            },
        )
        self.assertEqual(response.json()["session"]["messages"][0]["content"], "hello?")
        self.assertEqual(response.json()["session"]["messages"][1]["references"][0]["page_content"], "hello")
        self.assertEqual(
            self.rag_service.answer_requests[0],
            {
                "question": "hello?",
                "k": 1,
                "filter": {"source": "a.txt"},
                "history": [{"role": "user", "content": "上一个问题"}],
                "system_prompt": None,
                "temperature": 0.1,
                "max_tokens": 128,
            },
        )

    def test_agent_chat(self):
        response = self.client.post(
            "/agent/chat",
            json={
                "message": "根据知识库说明 hello",
                "k": 2,
                "history": [{"role": "user", "content": "前面聊到了 a.txt"}],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["answer"], "agent answer")
        self.assertTrue(response.json()["used_rag"])
        self.assertEqual(response.json()["references"][0]["page_content"], "hello")
        self.assertEqual(response.json()["session"]["messages"][0]["content"], "根据知识库说明 hello")
        self.assertEqual(response.json()["session"]["messages"][1]["mode"], "rag")
        self.assertEqual(response.json()["session"]["messages"][1]["references"][0]["page_content"], "hello")
        self.assertEqual(response.json()["attachments"][0]["filename"], "报告.md")
        self.assertEqual(response.json()["session"]["messages"][1]["attachments"][0]["download_url"], "/generated-documents/doc123/download")
        self.assertEqual(
            self.agent_service.answer_requests[0],
            {
                "question": "根据知识库说明 hello",
                "k": 2,
                "history": [{"role": "user", "content": "前面聊到了 a.txt"}],
            },
        )

    def test_chat_sessions_and_settings(self):
        saved = self.storage_service.save_completed_turn(user_content="你好", assistant_content="你好呀", mode="normal")

        response = self.client.get("/chat/sessions")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["sessions"][0]["id"], saved.id)
        self.assertEqual(response.json()["sessions"][0]["messages"], [])

        detail_response = self.client.get(f"/chat/sessions/{saved.id}")
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(len(detail_response.json()["messages"]), 2)

        settings_response = self.client.put(
            "/settings",
            json={"show_rag_references": False, "chat_background_image": "data:image/png;base64,abc", "chat_background_opacity": 0.7},
        )
        self.assertEqual(settings_response.status_code, 200)
        self.assertFalse(settings_response.json()["show_rag_references"])
        self.assertEqual(settings_response.json()["chat_background_opacity"], 0.7)

        delete_response = self.client.delete(f"/chat/sessions/{saved.id}")
        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(delete_response.json(), {"deleted": True})


if __name__ == "__main__":
    unittest.main()
