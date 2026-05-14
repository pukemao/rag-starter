from __future__ import annotations

import tempfile
import unittest

from src.chat_files import ChatFileService


class ChatFileServiceTests(unittest.TestCase):
    def test_save_and_read_markdown_upload(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = ChatFileService(upload_directory=tmpdir)

            result = service.save_upload(
                filename="../note.md",
                content="# 项目背景\n\n这是上传文档内容。\n\n## 付款条款\n\n付款在验收后完成。".encode(),
                content_type="text/markdown",
            )
            output = service.read(file_ids=[result.file_id], query="付款", max_chars=1200)

            self.assertEqual(result.filename, "note.md")
            self.assertEqual(result.status, "ready")
            self.assertGreater(result.chunk_count, 0)
            self.assertIn("付款条款", output)
            self.assertIn(result.file_id, output)

    def test_multiple_files_require_file_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = ChatFileService(upload_directory=tmpdir)
            first = service.save_upload(filename="a.md", content=b"# A", content_type="text/markdown")
            second = service.save_upload(filename="b.md", content=b"# B", content_type="text/markdown")

            output = service.read(file_ids=[first.file_id, second.file_id], query="A")

            self.assertIn("当前对话包含多个上传文件", output)
            self.assertIn(first.file_id, output)
            self.assertIn(second.file_id, output)


if __name__ == "__main__":
    unittest.main()
