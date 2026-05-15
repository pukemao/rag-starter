from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from src.embedding import DashScopeEmbeddings, HashEmbeddings, OllamaEmbeddings


class HashEmbeddingsTests(unittest.TestCase):
    def test_embeddings_are_deterministic_and_normalized(self):
        embeddings = HashEmbeddings(dimension=16)

        first = embeddings.embed_query("hello world")
        second = embeddings.embed_query("hello world")

        self.assertEqual(first, second)
        self.assertEqual(len(first), 16)
        self.assertAlmostEqual(sum(item * item for item in first), 1.0)


class FakeEmbeddings:
    def embed_documents(self, texts):
        return [[float(index), 1.0] for index, _ in enumerate(texts)]

    def embed_query(self, text):
        return [1.0, 2.0]


class DashScopeEmbeddingsTests(unittest.TestCase):
    def test_delegates_to_langchain_embeddings(self):
        embeddings = DashScopeEmbeddings(api_key="sk-test", dimension=2048, embeddings=FakeEmbeddings())

        self.assertEqual(embeddings.model, "text-embedding-v4")
        self.assertEqual(embeddings.dimension, 2048)
        self.assertEqual(embeddings.batch_size, 10)
        self.assertEqual(embeddings.embed_query("hello"), [1.0, 2.0])
        self.assertEqual(embeddings.embed_documents(["a", "b"]), [[0.0, 1.0], [1.0, 1.0]])

    def test_rejects_batch_size_larger_than_dashscope_limit(self):
        with self.assertRaisesRegex(ValueError, "1 到 10"):
            DashScopeEmbeddings(api_key="sk-test", batch_size=11, embeddings=FakeEmbeddings())


class FakeOllamaResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps({"embeddings": [[1, 2], [3, 4]]}).encode()


class OllamaEmbeddingsTests(unittest.TestCase):
    def test_calls_ollama_embed_api(self):
        captured = {}

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["body"] = json.loads(request.data.decode())
            captured["timeout"] = timeout
            return FakeOllamaResponse()

        embeddings = OllamaEmbeddings(base_url="http://localhost:11434/", model="qwen3-embedding:4b", dimension=2, batch_size=2, timeout=5)
        with patch("urllib.request.urlopen", fake_urlopen):
            vectors = embeddings.embed_documents(["hello", "world"])

        self.assertEqual(vectors, [[1.0, 2.0], [3.0, 4.0]])
        self.assertEqual(captured["url"], "http://localhost:11434/api/embed")
        self.assertEqual(captured["body"], {"model": "qwen3-embedding:4b", "input": ["hello", "world"]})
        self.assertEqual(captured["timeout"], 5)


if __name__ == "__main__":
    unittest.main()
