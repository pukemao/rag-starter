"""Shared vector store types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.config import settings


class VectorStoreDependencyError(ImportError):
    """Raised when vector database dependencies are unavailable."""


class DuplicateFileError(ValueError):
    """Raised when a file has already been indexed."""

    def __init__(self, filename: str, file_hash: str) -> None:
        self.filename = filename
        self.file_hash = file_hash
        self.message = f"文件 {filename} 已存在，不允许重复上传"
        super().__init__(self.message)


@dataclass(frozen=True, slots=True)
class VectorStoreConfig:
    """Configuration for the local vector database."""

    persist_directory: str = settings.vector_store.persist_directory
    collection_name: str = settings.vector_store.collection_name
    embedding_dimension: int = settings.embedding.active_dimension


@dataclass(frozen=True, slots=True)
class SearchResult:
    """Serializable search result returned by the service layer."""

    page_content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float | None = None
    rerank_score: float | None = None


@dataclass(frozen=True, slots=True)
class IndexResult:
    """Result returned after indexing chunks into the vector database."""

    ids: list[str]
    input_count: int
    added_count: int
    skipped_duplicates: int


@dataclass(frozen=True, slots=True)
class KnowledgeFile:
    """Indexed file summary built from vector store metadata."""

    filename: str
    source: str
    source_id: str | None
    file_hash: str | None
    chunk_count: int
    chunk_ids: list[str] = field(default_factory=list)
