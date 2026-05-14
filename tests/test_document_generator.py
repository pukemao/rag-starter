from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.document_generator import DocumentGeneratorService


class DocumentGeneratorServiceTests(unittest.TestCase):
    def test_generates_supported_documents(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = DocumentGeneratorService(output_directory=tmpdir)

            markdown = service.generate(content="# 标题\n\n正文", document_type="markdown", filename="测试报告")
            word = service.generate(content="# 标题\n\n- 条目", document_type="word", filename="word-name")
            excel = service.generate(content="| 名称 | 数量 |\n| --- | --- |\n| A | 2 |", document_type="excel", filename="表格.xlsx")
            pdf = service.generate(content="# 标题\n\nPDF 正文", document_type="pdf", filename="../bad/name")

            for attachment in [markdown, word, excel, pdf]:
                path = service.get_file_path(attachment.file_id)
                self.assertIsNotNone(path)
                self.assertTrue(Path(path).exists())
                self.assertGreater(attachment.size, 0)
                self.assertTrue(attachment.download_url.endswith(f"/{attachment.file_id}/download"))

            self.assertEqual(markdown.filename, "测试报告.md")
            self.assertEqual(word.filename, "word-name.docx")
            self.assertEqual(excel.filename, "表格.xlsx")
            self.assertEqual(pdf.filename, "name.pdf")

    def test_rejects_empty_content_and_unsupported_type(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = DocumentGeneratorService(output_directory=tmpdir)

            with self.assertRaises(ValueError):
                service.generate(content=" ", document_type="markdown")
            with self.assertRaises(ValueError):
                service.generate(content="content", document_type="ppt")


if __name__ == "__main__":
    unittest.main()
