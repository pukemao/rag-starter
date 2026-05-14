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

    def test_pdf_wraps_long_chinese_lines(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = DocumentGeneratorService(output_directory=tmpdir)
            long_content = (
                "# 洛龙湖社区残联工作总结报告\n\n"
                "2021年，洛龙湖社区在区残联和龙城街道办事处残联的领导下，"
                "社区残联各项工作取得了阶段性成效。本报告对年度重点工作、活动组织、"
                "需求走访和后续改进方向进行系统总结，便于快速了解社区残联工作全貌。"
            )

            attachment = service.generate(content=long_content, document_type="pdf", filename="wrap.pdf")
            path = service.get_file_path(attachment.file_id)

            self.assertIsNotNone(path)
            raw = path.read_bytes().decode("latin-1", errors="ignore")
            text_lines = [line for line in raw.splitlines() if line.startswith("<") and line.endswith("> Tj")]
            self.assertGreater(len(text_lines), 3)
            self.assertLess(max(len(line) for line in text_lines), 190)


if __name__ == "__main__":
    unittest.main()
