from __future__ import annotations

import sys
import types
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from src.splitter import SplitterConfig, create_splitter, load_and_split_documents, split_documents, supported_splitters
from src.splitter.excel import ExcelSheet, _build_excel_documents


class FakeRecursiveCharacterTextSplitter:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def split_documents(self, documents):
        return [{"content": document["content"], "kwargs": self.kwargs} for document in documents]


class FakeRecursiveDocumentSplitter:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def split_documents(self, documents):
        return documents


class FakeMarkdownHeaderTextSplitter:
    def __init__(self, *, headers_to_split_on, strip_headers):
        self.headers_to_split_on = headers_to_split_on
        self.strip_headers = strip_headers

    def split_text(self, text):
        from langchain_core.documents import Document

        sections = []
        current_header = ""
        current_body = []
        for line in text.splitlines():
            if line.startswith("# "):
                if current_header:
                    sections.append(Document(page_content="\n".join([current_header, *current_body]).strip()))
                current_header = line
                current_body = []
            else:
                current_body.append(line)
        if current_header:
            sections.append(Document(page_content="\n".join([current_header, *current_body]).strip()))
        return sections


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

    def test_markdown_load_and_split_keeps_heading_with_body(self):
        fake_module = types.ModuleType("langchain_text_splitters")
        fake_module.MarkdownHeaderTextSplitter = FakeMarkdownHeaderTextSplitter
        fake_module.RecursiveCharacterTextSplitter = FakeRecursiveDocumentSplitter

        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "note.md"
            path.write_text("# 标题一\n\n正文一\n\n# 标题二\n\n正文二", encoding="utf-8")

            with patch.dict(sys.modules, {"langchain_text_splitters": fake_module}):
                chunks = load_and_split_documents(path, chunk_size=100, chunk_overlap=0)

        self.assertEqual(len(chunks), 2)
        self.assertIn("# 标题一", chunks[0].page_content)
        self.assertIn("正文一", chunks[0].page_content)
        self.assertIn("# 标题二", chunks[1].page_content)
        self.assertIn("正文二", chunks[1].page_content)
        self.assertEqual(chunks[0].metadata["filename"], "note.md")

    def test_excel_split_keeps_header_sheet_and_row_together(self):
        chunks = _build_excel_documents(
            Path("sales.xlsx"),
            [
                ExcelSheet(
                    name="订单",
                    index=0,
                    rows=[
                        ["订单明细"],
                        ["订单号", "客户", "金额"],
                        ["A001", "张三", 120],
                        ["A002", "李四", 300],
                    ],
                )
            ],
            chunk_size=1000,
            chunk_overlap=0,
        )

        self.assertEqual(len(chunks), 1)
        self.assertIn("文件: sales.xlsx", chunks[0].page_content)
        self.assertIn("工作表: 订单", chunks[0].page_content)
        self.assertIn("表格说明: 订单明细", chunks[0].page_content)
        self.assertIn("表头: 订单号 | 客户 | 金额", chunks[0].page_content)
        self.assertIn("第3行: 订单号=A001；客户=张三；金额=120", chunks[0].page_content)
        self.assertEqual(chunks[0].metadata["sheet_name"], "订单")
        self.assertEqual(chunks[0].metadata["start_row"], 3)
        self.assertEqual(chunks[0].metadata["end_row"], 4)
        self.assertEqual(chunks[0].metadata["chunk_type"], "excel_table")

    def test_excel_split_chunks_by_complete_rows_and_repeats_header(self):
        chunks = _build_excel_documents(
            Path("inventory.xls"),
            [
                ExcelSheet(
                    name="库存",
                    index=0,
                    rows=[
                        ["SKU", "商品", "库存"],
                        ["P001", "超长商品名称" * 8, 15],
                        ["P002", "另一个商品名称" * 8, 8],
                    ],
                )
            ],
            chunk_size=95,
            chunk_overlap=0,
        )

        self.assertEqual(len(chunks), 2)
        for chunk in chunks:
            self.assertIn("工作表: 库存", chunk.page_content)
            self.assertIn("表头: SKU | 商品 | 库存", chunk.page_content)
        self.assertIn("SKU=P001", chunks[0].page_content)
        self.assertNotIn("SKU=P002", chunks[0].page_content)
        self.assertIn("SKU=P002", chunks[1].page_content)
        self.assertEqual(chunks[0].metadata["filetype"], "application/vnd.ms-excel")

    def test_excel_load_and_split_uses_excel_specific_path(self):
        expected = _build_excel_documents(
            Path("table.xlsx"),
            [ExcelSheet(name="Sheet1", index=0, rows=[["名称", "数量"], ["苹果", 2]])],
            chunk_size=1000,
            chunk_overlap=0,
        )

        with patch("src.splitter.excel._load_workbook") as load_workbook:
            load_workbook.return_value = [
                ExcelSheet(name="Sheet1", index=0, rows=[["名称", "数量"], ["苹果", 2]])
            ]
            chunks = load_and_split_documents(Path("table.xlsx"), chunk_size=1000, chunk_overlap=0)

        self.assertEqual(chunks[0].page_content, expected[0].page_content)
        self.assertIn("名称=苹果；数量=2", chunks[0].page_content)


if __name__ == "__main__":
    unittest.main()
