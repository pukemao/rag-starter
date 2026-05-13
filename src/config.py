"""Centralized application configuration.

All runtime defaults should live here. Modules may still accept explicit
arguments, but their default values should be sourced from this file.
"""

from __future__ import annotations

from dataclasses import dataclass
from os import getenv


def _get_int(name: str, default: int) -> int:
    raw = getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"环境变量 {name} 必须是整数") from exc


@dataclass(frozen=True, slots=True)
class ApiSettings:
    title: str = getenv("RAG_API_TITLE", "RAG Starter API")
    version: str = getenv("RAG_API_VERSION", "0.1.0")


@dataclass(frozen=True, slots=True)
class SplitterSettings:
    default_type: str = getenv("RAG_SPLITTER_TYPE", "recursive")
    default_chunk_size: int = _get_int("RAG_CHUNK_SIZE", 1000)
    default_chunk_overlap: int = _get_int("RAG_CHUNK_OVERLAP", 200)


@dataclass(frozen=True, slots=True)
class EmbeddingSettings:
    dimension: int = _get_int("RAG_EMBEDDING_DIMENSION", 384)


@dataclass(frozen=True, slots=True)
class VectorStoreSettings:
    persist_directory: str = getenv("RAG_CHROMA_PERSIST_DIRECTORY", "storage/chroma")
    collection_name: str = getenv("RAG_CHROMA_COLLECTION_NAME", "documents")


@dataclass(frozen=True, slots=True)
class AppSettings:
    api: ApiSettings = ApiSettings()
    splitter: SplitterSettings = SplitterSettings()
    embedding: EmbeddingSettings = EmbeddingSettings()
    vector_store: VectorStoreSettings = VectorStoreSettings()


settings = AppSettings()
