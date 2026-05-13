from __future__ import annotations

import unittest

from src.vector_store import SearchResult


class FakeService:
    def __init__(self) -> None:
        self.add_requests = []
        self.delete_requests = []
        self.search_requests = []

    def add_file(self, path, **kwargs):
        self.add_requests.append((path, kwargs))
        return ["id-1", "id-2"]

    def delete(self, *, ids=None, source=None):
        self.delete_requests.append({"ids": ids, "source": source})
        return len(ids or [])

    def search(self, query, *, k=4, filter=None):
        self.search_requests.append({"query": query, "k": k, "filter": filter})
        return [SearchResult(page_content="hello", metadata={"source": "a.txt"}, score=0.5)]


class ApiTests(unittest.TestCase):
    def setUp(self):
        try:
            from fastapi.testclient import TestClient
        except ImportError as exc:
            self.skipTest(f"FastAPI 未安装: {exc}")

        from src.api import create_app

        self.service = FakeService()
        self.client = TestClient(create_app(service=self.service))

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
        self.assertEqual(response.json(), {"ids": ["id-1", "id-2"], "count": 2})
        self.assertEqual(self.service.add_requests[0][0], "data/a.md")
        self.assertEqual(self.service.add_requests[0][1]["chunk_size"], 500)

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
        self.assertEqual([item["filename"] for item in payload["files"]], ["note.md", "notes.txt"])
        self.assertEqual(len(self.service.add_requests), 2)
        first_call = self.service.add_requests[0][1]
        self.assertEqual(first_call["splitter_type"], "recursive")
        self.assertEqual(first_call["chunk_size"], 512)
        self.assertEqual(first_call["chunk_overlap"], 32)
        self.assertEqual(first_call["source_label"], "note.md")
        self.assertTrue(first_call["source_id"])

    def test_delete_document(self):
        response = self.client.request("DELETE", "/documents", json={"ids": ["id-1"]})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"deleted": 1})

    def test_search(self):
        response = self.client.post("/search", json={"query": "hello", "k": 1})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"results": [{"page_content": "hello", "metadata": {"source": "a.txt"}, "score": 0.5}]},
        )


if __name__ == "__main__":
    unittest.main()
