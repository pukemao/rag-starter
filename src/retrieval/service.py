"""Unified retrieval service with vector recall and optional reranking."""

from __future__ import annotations

from typing import Any

from src.config import settings
from src.reranker import Reranker, create_reranker
from src.vector_store import SearchResult, VectorStoreService

from .normalization import dedupe_candidates


class RetrievalService:
    """Two-stage retrieval: vector recall, cross-encoder rerank, top-n return."""

    def __init__(
        self,
        *,
        vector_service: VectorStoreService | None = None,
        reranker: Reranker | None = None,
    ) -> None:
        self.vector_service = vector_service or VectorStoreService()
        self.reranker = reranker or create_reranker()

    def retrieve(
        self,
        query: str,
        *,
        k: int = settings.rag.default_top_k,
        filter: dict[str, Any] | None = None,
        candidate_k: int | None = None,
    ) -> list[SearchResult]:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("query 不能为空")
        if k <= 0:
            raise ValueError("k 必须大于 0")

        active_candidate_k = candidate_k or self.candidate_k_for(k)
        candidates = self.vector_service.search(normalized_query, k=active_candidate_k, filter=filter)
        unique_candidates = dedupe_candidates(candidates)
        reranked = self.reranker.rerank(normalized_query, unique_candidates)
        return reranked[:k]

    @staticmethod
    def candidate_k_for(k: int) -> int:
        return max(
            k,
            settings.reranker.min_candidate_k,
            min(k * settings.reranker.candidate_multiplier, settings.reranker.max_candidate_k),
        )
