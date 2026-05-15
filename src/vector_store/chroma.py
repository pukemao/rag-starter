"""Chroma vector store factory."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any

from langchain_core.embeddings import Embeddings

from src.embedding import create_embeddings

from .base import VectorStoreConfig, VectorStoreDependencyError


def create_chroma_vector_store(
    *,
    config: VectorStoreConfig | None = None,
    embedding: Embeddings | None = None,
    **kwargs: Any,
) -> Any:
    """Create a persistent local Chroma vector store."""

    active_config = config or VectorStoreConfig()
    persist_directory = Path(active_config.persist_directory)
    persist_directory.mkdir(parents=True, exist_ok=True)
    active_embedding = embedding or create_embeddings(dimension=active_config.embedding_dimension)

    try:
        module = import_module("langchain_chroma")
    except ImportError as exc:
        raise VectorStoreDependencyError(
            "无法导入 langchain_chroma。请安装依赖: pip install langchain-chroma chromadb"
        ) from exc

    chroma_cls = getattr(module, "Chroma", None)
    if chroma_cls is None:
        raise VectorStoreDependencyError("langchain_chroma 中未找到 Chroma")

    return chroma_cls(
        collection_name=active_config.collection_name,
        embedding_function=active_embedding,
        persist_directory=str(persist_directory),
        **kwargs,
    )
