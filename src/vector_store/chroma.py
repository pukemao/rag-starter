"""Chroma vector store factory."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from langchain_core.embeddings import Embeddings

from src.embedding import HashEmbeddings

from .base import VectorStoreConfig, VectorStoreDependencyError


def create_chroma_vector_store(
    *,
    config: VectorStoreConfig | None = None,
    embedding: Embeddings | None = None,
    **kwargs: Any,
) -> Any:
    """Create a persistent local Chroma vector store."""

    active_config = config or VectorStoreConfig()
    active_embedding = embedding or HashEmbeddings(dimension=active_config.embedding_dimension)

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
        persist_directory=active_config.persist_directory,
        **kwargs,
    )
