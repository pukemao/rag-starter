"""Reranker factory."""

from __future__ import annotations

from src.config import settings

from .base import Reranker
from .bge import BGEReranker
from .disabled import DisabledReranker
from .ollama import OllamaReranker


def create_reranker() -> Reranker:
    provider = settings.reranker.provider.strip().lower()
    if provider in {"", "none", "disabled", "off", "false"}:
        return DisabledReranker()
    if provider in {"bge", "local", "flagembedding"}:
        return BGEReranker()
    if provider == "ollama":
        return OllamaReranker()
    raise ValueError(f"不支持的重排序模型 provider: {settings.reranker.provider}")
