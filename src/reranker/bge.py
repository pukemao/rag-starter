"""BGE reranker backed by FlagEmbedding."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from src.config import settings
from src.vector_store import SearchResult

from .base import RerankerConfigurationError


class BGEReranker:
    """Rerank query/chunk pairs with BAAI BGE reranker models."""

    def __init__(
        self,
        *,
        model: str = settings.reranker.model,
        device: str = settings.reranker.device,
        use_fp16: bool = settings.reranker.use_fp16,
        normalize: bool = settings.reranker.normalize,
        model_client: Any | None = None,
    ) -> None:
        self.model = model
        self.device = device
        self.use_fp16 = use_fp16
        self.normalize = normalize
        self._client = model_client
        self.name = model

    def rerank(self, query: str, results: list[SearchResult]) -> list[SearchResult]:
        if not results:
            return []

        client = self._get_client()
        pairs = [[query, result.page_content] for result in results]
        scores = client.compute_score(pairs, normalize=self.normalize)
        if isinstance(scores, (int, float)):
            normalized_scores = [float(scores)]
        else:
            normalized_scores = [float(score) for score in scores]

        scored = [
            replace(result, rerank_score=normalized_scores[index] if index < len(normalized_scores) else None)
            for index, result in enumerate(results)
        ]
        return sorted(scored, key=lambda result: result.rerank_score if result.rerank_score is not None else float("-inf"), reverse=True)

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        try:
            from FlagEmbedding import FlagReranker
        except ImportError as exc:
            raise RerankerConfigurationError(
                "无法导入 FlagEmbedding。请安装重排序依赖: pip install -e '.[reranker]'，"
                "或设置 RAG_RERANKER_PROVIDER=disabled 关闭重排序。"
            ) from exc

        kwargs: dict[str, Any] = {"use_fp16": self.use_fp16}
        if self.device:
            kwargs["devices"] = [self.device]
        self._client = FlagReranker(self.model, **kwargs)
        return self._client
