from __future__ import annotations

import unittest

from src.embedding import DashScopeEmbeddings, HashEmbeddings


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
        self.assertEqual(embeddings.embed_query("hello"), [1.0, 2.0])
        self.assertEqual(embeddings.embed_documents(["a", "b"]), [[0.0, 1.0], [1.0, 1.0]])


if __name__ == "__main__":
    unittest.main()
