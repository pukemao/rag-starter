from __future__ import annotations

import unittest

from src.embedding import HashEmbeddings


class HashEmbeddingsTests(unittest.TestCase):
    def test_embeddings_are_deterministic_and_normalized(self):
        embeddings = HashEmbeddings(dimension=16)

        first = embeddings.embed_query("hello world")
        second = embeddings.embed_query("hello world")

        self.assertEqual(first, second)
        self.assertEqual(len(first), 16)
        self.assertAlmostEqual(sum(item * item for item in first), 1.0)


if __name__ == "__main__":
    unittest.main()
