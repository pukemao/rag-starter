from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import patch

from src.splitter import SplitterConfig, create_splitter, split_documents, supported_splitters


class FakeRecursiveCharacterTextSplitter:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def split_documents(self, documents):
        return [{"content": document["content"], "kwargs": self.kwargs} for document in documents]


class SplitterTests(unittest.TestCase):
    def test_supported_splitters_include_default_aliases(self):
        self.assertEqual(
            supported_splitters(),
            ("character", "markdown", "python", "recursive", "token"),
        )

    def test_config_validates_overlap_smaller_than_size(self):
        with self.assertRaises(ValueError):
            SplitterConfig(chunk_size=100, chunk_overlap=100)

    def test_create_splitter_imports_langchain_text_splitters_lazily(self):
        fake_module = types.ModuleType("langchain_text_splitters")
        fake_module.RecursiveCharacterTextSplitter = FakeRecursiveCharacterTextSplitter

        with patch.dict(sys.modules, {"langchain_text_splitters": fake_module}):
            splitter = create_splitter(chunk_size=512, chunk_overlap=64, separators=["\n\n"])

        self.assertIsInstance(splitter, FakeRecursiveCharacterTextSplitter)
        self.assertEqual(splitter.kwargs["chunk_size"], 512)
        self.assertEqual(splitter.kwargs["chunk_overlap"], 64)
        self.assertEqual(splitter.kwargs["separators"], ["\n\n"])

    def test_split_documents_accepts_injected_splitter(self):
        splitter = FakeRecursiveCharacterTextSplitter(chunk_size=10, chunk_overlap=2)

        chunks = split_documents([{"content": "hello"}], splitter=splitter)

        self.assertEqual(chunks, [{"content": "hello", "kwargs": {"chunk_size": 10, "chunk_overlap": 2}}])


if __name__ == "__main__":
    unittest.main()
