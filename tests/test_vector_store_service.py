from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from src.vector_store.chroma import create_chroma_vector_store
from src.vector_store import VectorStoreConfig, VectorStoreService


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

    def get(self, *, where=None, limit=None, include=None):
        ids = []
        metadatas = []
        for doc_id, document in zip(self.ids, self.documents):
            if where is None or all(document.metadata.get(key) == value for key, value in where.items()):
                ids.append(doc_id)
                metadatas.append(document.metadata)
                if limit is not None and len(ids) >= limit:
                    break
        return {"ids": ids, "metadatas": metadatas}

    def delete(self, *, ids):
        self.deleted_ids.extend(ids)

    def similarity_search_with_score(self, query, *, k, filter=None):
        return [(document, 0.12) for document in self.documents[:k]]


class FakeEmbeddings(Embeddings):
    def embed_documents(self, texts):
        return [[float(index), 1.0] for index, _ in enumerate(texts)]

    def embed_query(self, text):
        return [1.0, 1.0]


class VectorStoreServiceTests(unittest.TestCase):
    def test_add_documents_generates_stable_ids(self):
        store = FakeVectorStore()
        service = VectorStoreService(vector_store=store)
        documents = [Document(page_content="hello", metadata={"source": "a.txt"})]

        ids = service.add_documents(documents)

        self.assertEqual(ids, store.ids)
        self.assertEqual(len(ids), 1)
        self.assertTrue(ids[0].startswith("doc-"))
        self.assertIn("chunk_hash", store.documents[0].metadata)
        self.assertEqual(store.documents[0].metadata["chunk_index"], 0)

    def test_file_exists_checks_file_hash_metadata(self):
        store = FakeVectorStore()
        service = VectorStoreService(vector_store=store)

        service.add_documents([Document(page_content="hello", metadata={"source": "a.txt", "file_hash": "hash-1"})])

        self.assertTrue(service.file_exists("hash-1"))
        self.assertFalse(service.file_exists("missing"))

    def test_index_documents_deduplicates_within_one_batch_only(self):
        store = FakeVectorStore()
        service = VectorStoreService(vector_store=store)
        documents = [
            Document(page_content="hello   world", metadata={"source_id": "file-a"}),
            Document(page_content="hello world", metadata={"source_id": "file-a"}),
            Document(page_content="hello world", metadata={"source_id": "file-b"}),
        ]

        result = service.index_documents(documents)

        self.assertEqual(result.added_count, 2)
        self.assertEqual(result.skipped_duplicates, 1)
        self.assertEqual(len(store.documents), 2)
        self.assertNotEqual(store.ids[0], store.ids[1])

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

    def test_delete_by_source_id(self):
        store = FakeVectorStore()
        service = VectorStoreService(vector_store=store)

        deleted = service.delete(source_id="source-a")

        self.assertIsNone(deleted)
        self.assertEqual(store._collection.deleted_where, {"source_id": "source-a"})

    def test_search_returns_serializable_results(self):
        store = FakeVectorStore()
        service = VectorStoreService(vector_store=store)
        service.add_documents([Document(page_content="hello", metadata={"source": "a.txt"})])

        results = service.search("hello", k=1)

        self.assertEqual(results[0].page_content, "hello")
        self.assertEqual(results[0].metadata["source"], "a.txt")
        self.assertIn("chunk_hash", results[0].metadata)
        self.assertEqual(results[0].score, 0.12)

    def test_list_files_groups_documents_by_source_id(self):
        store = FakeVectorStore()
        service = VectorStoreService(vector_store=store)
        service.add_documents(
            [
                Document(page_content="chunk 1", metadata={"source": "a.md", "source_id": "source-a", "file_hash": "hash-a"}),
                Document(page_content="chunk 2", metadata={"source": "a.md", "source_id": "source-a", "file_hash": "hash-a"}),
                Document(page_content="chunk 3", metadata={"source": "b.md", "source_id": "source-b", "file_hash": "hash-b"}),
            ]
        )

        files = service.list_files()

        self.assertEqual([file.filename for file in files], ["a.md", "b.md"])
        self.assertEqual(files[0].source, "a.md")
        self.assertEqual(files[0].source_id, "source-a")
        self.assertEqual(files[0].file_hash, "hash-a")
        self.assertEqual(files[0].chunk_count, 2)
        self.assertEqual(len(files[0].chunk_ids), 2)

    def test_add_file_runs_full_indexing_pipeline(self):
        with TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "kb.txt"
            file_path.write_text(
                "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu",
                encoding="utf-8",
            )

            service = VectorStoreService(
                config=VectorStoreConfig(persist_directory=tmpdir, collection_name="integration", embedding_dimension=2),
                embedding=FakeEmbeddings(),
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
        self.assertIn("file_hash", results[0].metadata)

    def test_index_file_rejects_duplicate_file_hash(self):
        with TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "same.txt"
            file_path.write_text("same file", encoding="utf-8")
            store = FakeVectorStore()
            service = VectorStoreService(vector_store=store)

            first = service.index_file(file_path, source_label="same.txt", reject_duplicate_file=True)

            with self.assertRaises(Exception) as error:
                service.index_file(file_path, source_label="same.txt", reject_duplicate_file=True)

        self.assertEqual(first.added_count, 1)
        self.assertIn("不允许重复上传", str(error.exception))

    def test_chroma_factory_creates_missing_persist_directory(self):
        with TemporaryDirectory() as tmpdir:
            persist_directory = Path(tmpdir) / "missing" / "chroma"

            create_chroma_vector_store(
                config=VectorStoreConfig(
                    persist_directory=str(persist_directory), collection_name="mkdir-test", embedding_dimension=2
                ),
                embedding=FakeEmbeddings(),
            )

            self.assertTrue(persist_directory.is_dir())


if __name__ == "__main__":
    unittest.main()
