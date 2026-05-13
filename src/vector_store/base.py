"""Shared vector store types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class VectorStoreDependencyError(ImportError):
    """Raised when vector database dependencies are unavailable."""


@dataclass(frozen=True, slots=True)
class VectorStoreConfig:
    """Configuration for the local vector database."""

    persist_directory: str = "storage/chroma"
    collection_name: str = "documents"
    embedding_dimension: int = 384


@dataclass(frozen=True, slots=True)
class SearchResult:
    """Serializable search result returned by the service layer."""

    page_content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float | None = None
