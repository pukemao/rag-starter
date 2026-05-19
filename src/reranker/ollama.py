"""Ollama-backed reranker."""

from __future__ import annotations

from dataclasses import replace
import json
import math
import urllib.error
import urllib.request
from typing import Any

from src.config import settings
from src.vector_store import SearchResult

from .base import RerankerConfigurationError


class OllamaReranker:
    """Rerank chunks by calling a local Ollama model.

    The local ``dengcao/bge-reranker-v2-m3`` model currently exposes embeddings
    through ``/api/embed``. When Ollama returns explicit ``scores`` this class
    uses them directly; otherwise it embeds the query and each candidate passage
    and uses cosine similarity as the ranking score.
    """

    def __init__(
        self,
        *,
        base_url: str = settings.reranker.ollama_base_url,
        model: str = settings.reranker.ollama_model,
        batch_size: int = settings.reranker.ollama_batch_size,
        timeout: float = settings.reranker.ollama_timeout_seconds,
        max_passage_chars: int = settings.reranker.max_passage_chars,
    ) -> None:
        if batch_size <= 0:
            raise ValueError("Ollama reranker batch_size 必须大于 0")
        if max_passage_chars <= 0:
            raise ValueError("Ollama reranker max_passage_chars 必须大于 0")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.batch_size = batch_size
        self.timeout = timeout
        self.max_passage_chars = max_passage_chars
        self.name = model

    def rerank(self, query: str, results: list[SearchResult]) -> list[SearchResult]:
        if not results:
            return []

        pair_scores = self._score_pairs(query, results)
        scored = [replace(result, rerank_score=pair_scores[index]) for index, result in enumerate(results)]
        return sorted(scored, key=lambda result: result.rerank_score if result.rerank_score is not None else float("-inf"), reverse=True)

    def _score_pairs(self, query: str, results: list[SearchResult]) -> list[float]:
        pair_inputs = [self._pair_input(query, result.page_content) for result in results]
        pair_response = self._embed(pair_inputs)
        raw_scores = pair_response.get("scores")
        if isinstance(raw_scores, list) and len(raw_scores) == len(results):
            return [float(score) for score in raw_scores]

        query_vector = self._embed([query]).get("embeddings", [[]])[0]
        passage_vectors = self._embed([self._truncate(result.page_content) for result in results]).get("embeddings")
        if not isinstance(passage_vectors, list):
            raise RerankerConfigurationError("Ollama reranker 未返回 passage embeddings")
        return [self._cosine_similarity(query_vector, vector) for vector in passage_vectors]

    def _embed(self, inputs: list[str]) -> dict[str, Any]:
        merged: dict[str, Any] = {"embeddings": []}
        scores: list[float] = []
        for index in range(0, len(inputs), self.batch_size):
            data = self._embed_batch(inputs[index : index + self.batch_size])
            if isinstance(data.get("scores"), list):
                scores.extend(float(score) for score in data["scores"])
            embeddings = data.get("embeddings")
            if isinstance(embeddings, list):
                merged["embeddings"].extend(embeddings)
        if scores:
            merged["scores"] = scores
        return merged

    def _embed_batch(self, inputs: list[str]) -> dict[str, Any]:
        payload = json.dumps({"model": self.model, "input": inputs}).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/api/embed",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RerankerConfigurationError(
                f"无法连接 Ollama reranker 服务：{self.base_url}。请确认 Ollama 已运行，并已拉取模型 {self.model}。"
            ) from exc

    def _pair_input(self, query: str, passage: str) -> str:
        return f"query: {query}\npassage: {self._truncate(passage)}"

    def _truncate(self, text: str) -> str:
        normalized = str(text or "").strip()
        return normalized[: self.max_passage_chars]

    @staticmethod
    def _cosine_similarity(left: Any, right: Any) -> float:
        if not isinstance(left, list) or not isinstance(right, list) or not left or not right:
            raise RerankerConfigurationError("Ollama reranker 返回了无效 embedding")
        size = min(len(left), len(right))
        left_values = [float(value) for value in left[:size]]
        right_values = [float(value) for value in right[:size]]
        dot = sum(a * b for a, b in zip(left_values, right_values, strict=False))
        left_norm = math.sqrt(sum(value * value for value in left_values))
        right_norm = math.sqrt(sum(value * value for value in right_values))
        if left_norm == 0 or right_norm == 0:
            return float("-inf")
        return dot / (left_norm * right_norm)
