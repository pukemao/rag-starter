"""Shared reranker interfaces and errors."""

from __future__ import annotations

from typing import Protocol

from src.vector_store import SearchResult


class RerankerConfigurationError(RuntimeError):
    """Raised when the configured reranker cannot be created."""


class Reranker(Protocol):
    """Rank candidate chunks for a query."""

    name: str

    def rerank(self, query: str, results: list[SearchResult]) -> list[SearchResult]:
        """Return candidates ordered from most relevant to least relevant."""
