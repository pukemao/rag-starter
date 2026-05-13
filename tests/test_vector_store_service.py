from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from langchain_core.documents import Document

from src.vector_store import SearchResult, VectorStoreConfig, VectorStoreService


class FakeCollection:
    def __init__(self) -> None:
        self.deleted_where = None

    def delete(self, *, where):
        self.deleted_where = where


class FakeVectorStore:
    def __init__(self) -> None:
        self.documents = []
        self.ids = []
        self.deleted_ids = []
        self._collection = FakeCollection()

    def add_documents(self, documents, *, ids):
        self.documents.extend(documents)
        self.ids.extend(ids)

    def delete(self, *, ids):
        self.deleted_ids.extend(ids)

    def similarity_search_with_score(self, query, *, k, filter=None):
        return [(document, 0.12) for document in self.documents[:k]]


class VectorStoreServiceTests(unittest.TestCase):
    def test_add_documents_generates_stable_ids(self):
        store = FakeVectorStore()
        service = VectorStoreService(vector_store=store)
        documents = [Document(page_content="hello", metadata={"source": "a.txt"})]

        ids = service.add_documents(documents)

        self.assertEqual(ids, store.ids)
        self.assertEqual(len(ids), 1)
        self.assertTrue(ids[0].startswith("doc-"))

    def test_delete_by_ids(self):
        store = FakeVectorStore()
        service = VectorStoreService(vector_store=store)

        deleted = service.delete(ids=["a", "b"])

        self.assertEqual(deleted, 2)
        self.assertEqual(store.deleted_ids, ["a", "b"])

    def test_delete_by_source(self):
        store = FakeVectorStore()
        service = VectorStoreService(vector_store=store)

        deleted = service.delete(source="a.txt")

        self.assertIsNone(deleted)
        self.assertEqual(store._collection.deleted_where, {"source": "a.txt"})

    def test_search_returns_serializable_results(self):
        store = FakeVectorStore()
        service = VectorStoreService(vector_store=store)
        service.add_documents([Document(page_content="hello", metadata={"source": "a.txt"})])

        results = service.search("hello", k=1)

        self.assertEqual(results, [SearchResult(page_content="hello", metadata={"source": "a.txt"}, score=0.12)])

    def test_add_file_runs_full_indexing_pipeline(self):
        with TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "kb.txt"
            file_path.write_text(
                "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu",
                encoding="utf-8",
            )

            service = VectorStoreService(
                config=VectorStoreConfig(persist_directory=tmpdir, collection_name="integration")
            )
            ids = service.add_file(
                file_path,
                chunk_size=20,
                chunk_overlap=0,
                source_label="kb.txt",
                source_id="upload-1",
            )
            results = service.search("alpha", k=1)

        self.assertGreaterEqual(len(ids), 2)
        self.assertEqual(results[0].metadata["source"], "kb.txt")
        self.assertEqual(results[0].metadata["source_id"], "upload-1")


if __name__ == "__main__":
    unittest.main()
