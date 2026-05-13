from __future__ import annotations

import unittest

from src.config import settings
from src.splitter import DEFAULT_SPLITTER
from src.vector_store import VectorStoreConfig


class ConfigTests(unittest.TestCase):
    def test_defaults_are_centralized(self):
        self.assertEqual(settings.api.title, "RAG Starter API")
        self.assertIn("http://localhost:5173", settings.api.cors_origins)
        self.assertEqual(settings.splitter.default_type, DEFAULT_SPLITTER)
        self.assertEqual(settings.rag.default_top_k, 4)
        self.assertEqual(settings.llm.provider, "deepseek")

        config = VectorStoreConfig()
        self.assertEqual(config.persist_directory, settings.vector_store.persist_directory)
        self.assertEqual(config.collection_name, settings.vector_store.collection_name)
        self.assertEqual(config.embedding_dimension, settings.embedding.dimension)


if __name__ == "__main__":
    unittest.main()
