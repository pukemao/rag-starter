from __future__ import annotations

import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from src.loader import get_loader, loader_for_extension, supported_extensions
from src.loader.directory import iter_supported_files
from src.loader.utils import UnsupportedFormatError, normalize_extension


class FakeTextLoader:
    def __init__(self, file_path: str, **kwargs):
        self.file_path = file_path
        self.kwargs = kwargs

    def load(self):
        return [{"page_content": Path(self.file_path).read_text(), "metadata": self.kwargs}]


class LoaderRegistryTests(unittest.TestCase):
    def test_supported_extensions_include_common_formats(self):
        extensions = supported_extensions()
        for extension in (
            ".txt",
            ".pdf",
            ".csv",
            ".json",
            ".md",
            ".docx",
            ".pptx",
            ".xlsx",
            ".mhtml",
            ".chm",
            ".srt",
        ):
            self.assertIn(extension, extensions)

    def test_loader_for_extension_normalizes_case_and_paths(self):
        self.assertEqual(loader_for_extension("REPORT.PDF").key, "pdf")
        self.assertEqual(loader_for_extension(".CSV").key, "csv")

    def test_unsupported_extension_raises_clear_error(self):
        with self.assertRaises(UnsupportedFormatError):
            loader_for_extension("archive.unknown")

    def test_normalize_extension_rejects_missing_suffix(self):
        with self.assertRaises(UnsupportedFormatError):
            normalize_extension("README")

    def test_get_loader_uses_langchain_loader_lazily(self):
        package = types.ModuleType("langchain_community")
        package.__path__ = []
        loaders = types.ModuleType("langchain_community.document_loaders")
        loaders.TextLoader = FakeTextLoader

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "note.txt"
            path.write_text("hello", encoding="utf-8")

            with patch.dict(
                sys.modules,
                {
                    "langchain_community": package,
                    "langchain_community.document_loaders": loaders,
                },
            ):
                loader = get_loader(path)

        self.assertIsInstance(loader, FakeTextLoader)
        self.assertEqual(loader.kwargs["encoding"], "utf-8")

    def test_iter_supported_files_filters_unknown_formats(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "a.txt").write_text("a", encoding="utf-8")
            (root / "b.unknown").write_text("b", encoding="utf-8")
            nested = root / "nested"
            nested.mkdir()
            (nested / "c.md").write_text("c", encoding="utf-8")

            files = [path.relative_to(root).as_posix() for path in iter_supported_files(root)]

        self.assertEqual(files, ["a.txt", "nested/c.md"])


if __name__ == "__main__":
    unittest.main()
