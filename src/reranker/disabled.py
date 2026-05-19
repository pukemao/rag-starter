"""No-op reranker implementation."""

from __future__ import annotations

from src.vector_store import SearchResult


class DisabledReranker:
    """Keep vector-store order when reranking is disabled."""

    name = "disabled"

    def rerank(self, query: str, results: list[SearchResult]) -> list[SearchResult]:
        return list(results)
