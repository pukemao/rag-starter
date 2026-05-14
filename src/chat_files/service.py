"""Manage temporary files uploaded from the chat input."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from src.config import settings
from src.splitter import load_and_split_documents


@dataclass(frozen=True, slots=True)
class ChatFileChunk:
    index: int
    content: str
    metadata: dict


@dataclass(frozen=True, slots=True)
class ChatFile:
    file_id: str
    filename: str
    size: int
    content_type: str
    status: str
    created_at: str
    chunk_count: int
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class ChatFileService:
    """Persist and read chat-scoped uploads without indexing them into Chroma."""

    def __init__(self, upload_directory: str | Path | None = None) -> None:
        self.upload_directory = Path(upload_directory or settings.chat_uploads.directory)
        self.upload_directory.mkdir(parents=True, exist_ok=True)

    def save_upload(self, *, filename: str, content: bytes, content_type: str = "") -> ChatFile:
        max_bytes = settings.chat_uploads.max_size_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise ValueError(f"文件大小不能超过 {settings.chat_uploads.max_size_mb} MB")
        safe_name = self._safe_filename(filename)
        file_id = uuid4().hex
        stored_path = self.upload_directory / f"{file_id}_{safe_name}"
        stored_path.write_bytes(content)

        status = "ready"
        error = ""
        chunks: list[ChatFileChunk] = []
        try:
            chunks = self._extract_chunks(stored_path, safe_name)
        except Exception as exc:
            status = "error"
            error = str(exc)
        metadata = ChatFile(
            file_id=file_id,
            filename=safe_name,
            size=len(content),
            content_type=content_type,
            status=status,
            created_at=datetime.now(timezone.utc).isoformat(),
            chunk_count=len(chunks),
            error=error,
        )
        self._metadata_path(file_id).write_text(json.dumps(metadata.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        self._chunks_path(file_id).write_text(
            json.dumps([asdict(chunk) for chunk in chunks], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return metadata

    def get_file(self, file_id: str) -> ChatFile | None:
        if not self._valid_file_id(file_id):
            return None
        path = self._metadata_path(file_id)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return ChatFile(**payload)

    def list_files(self, file_ids: list[str]) -> list[ChatFile]:
        return [item for file_id in file_ids if (item := self.get_file(file_id)) is not None]

    def read(self, *, file_ids: list[str], file_id: str | None = None, query: str | None = None, max_chars: int | None = None) -> str:
        allowed_ids = [item for item in file_ids if self._valid_file_id(item)]
        if not allowed_ids:
            return "当前对话没有可读取的上传文件。"
        target_id = file_id.strip() if file_id else ""
        if target_id:
            if target_id not in allowed_ids:
                return "无法读取该文件：file_id 不属于当前对话可访问附件。"
            active_ids = [target_id]
        elif len(allowed_ids) == 1:
            active_ids = allowed_ids
        else:
            files = self.list_files(allowed_ids)
            listing = "\n".join(f"- file_id: {item.file_id}, filename: {item.filename}, status: {item.status}" for item in files)
            return f"当前对话包含多个上传文件，请指定 file_id 后再读取：\n{listing}"

        limit = max(500, min(max_chars or settings.chat_uploads.default_max_chars, 20000))
        query_terms = _tokenize(query or "")
        chunks = self._load_chunks(active_ids[0])
        if not chunks:
            item = self.get_file(active_ids[0])
            if item and item.error:
                return f"文件读取失败：{item.error}"
            return "文件没有可读取文本内容。"
        ranked = sorted(chunks, key=lambda chunk: _score_chunk(chunk.content, query_terms), reverse=True) if query_terms else chunks

        output_parts: list[str] = []
        total = 0
        file_info = self.get_file(active_ids[0])
        output_parts.append(f"文件：{file_info.filename if file_info else active_ids[0]}")
        output_parts.append(f"file_id：{active_ids[0]}")
        output_parts.append("")
        for chunk in ranked:
            block = f"[片段 {chunk.index}]\n{chunk.content.strip()}"
            if total + len(block) > limit:
                remaining = limit - total
                if remaining > 120:
                    output_parts.append(block[:remaining].rstrip())
                break
            output_parts.append(block)
            output_parts.append("")
            total += len(block)
        return "\n".join(output_parts).strip()

    def _extract_chunks(self, path: Path, filename: str) -> list[ChatFileChunk]:
        docs = load_and_split_documents(path, chunk_size=1200, chunk_overlap=150)
        chunks: list[ChatFileChunk] = []
        for index, document in enumerate(docs, start=1):
            content = str(getattr(document, "page_content", "") or "").strip()
            if not content:
                continue
            metadata = dict(getattr(document, "metadata", {}) or {})
            metadata.setdefault("filename", filename)
            chunks.append(ChatFileChunk(index=index, content=content, metadata=metadata))
        return chunks

    def _metadata_path(self, file_id: str) -> Path:
        return self.upload_directory / f"{file_id}.json"

    def _chunks_path(self, file_id: str) -> Path:
        return self.upload_directory / f"{file_id}.chunks.json"

    @staticmethod
    def _safe_filename(filename: str) -> str:
        raw_name = Path(filename or "upload.bin").name
        raw_name = re.sub(r"[\\/:*?\"<>|]+", "-", raw_name)
        raw_name = re.sub(r"\s+", " ", raw_name).strip(" .")
        return raw_name[:180] or "upload.bin"

    @staticmethod
    def _valid_file_id(file_id: str) -> bool:
        return bool(re.fullmatch(r"[a-f0-9]{32}", file_id))

    def _load_chunks(self, file_id: str) -> list[ChatFileChunk]:
        if not self._valid_file_id(file_id):
            return []
        path = self._chunks_path(file_id)
        if not path.exists():
            return []
        payload = json.loads(path.read_text(encoding="utf-8"))
        return [ChatFileChunk(**item) for item in payload if isinstance(item, dict)]


def _tokenize(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text.lower()).strip()
    if not normalized:
        return []
    words = re.findall(r"[a-z0-9_]{2,}|[\u4e00-\u9fff]{2,}", normalized)
    if words:
        return words
    return [normalized]


def _score_chunk(content: str, query_terms: list[str]) -> int:
    haystack = content.lower()
    return sum(haystack.count(term) for term in query_terms)
