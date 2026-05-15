"""Embedding provider factory."""

from __future__ import annotations

from langchain_core.embeddings import Embeddings

from src.config import settings

from .dashscope import DashScopeEmbeddings, EmbeddingConfigurationError
from .hash import HashEmbeddings
from .ollama import OllamaEmbeddings


def create_embeddings(*, dimension: int | None = None) -> Embeddings:
    provider = settings.embedding.provider.strip().lower()
    if provider in {"dashscope", "bailian", "aliyun"}:
        return DashScopeEmbeddings(dimension=dimension or settings.embedding.dimension)
    if provider == "ollama":
        return OllamaEmbeddings(dimension=dimension or settings.embedding.ollama_dimension)
    if provider == "hash":
        return HashEmbeddings(dimension=dimension or settings.embedding.dimension)
    raise EmbeddingConfigurationError(f"不支持的 embedding provider：{settings.embedding.provider}")
