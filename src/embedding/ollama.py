"""Local Ollama embedding client."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from langchain_core.embeddings import Embeddings

from src.config import settings
from src.embedding.dashscope import EmbeddingConfigurationError


class OllamaEmbeddings(Embeddings):
    """Embeddings served by local Ollama through ``/api/embed``."""

    def __init__(
        self,
        *,
        base_url: str = settings.embedding.ollama_base_url,
        model: str = settings.embedding.ollama_model,
        dimension: int = settings.embedding.ollama_dimension,
        batch_size: int = settings.embedding.ollama_batch_size,
        timeout: float = settings.embedding.ollama_timeout_seconds,
    ) -> None:
        if dimension <= 0:
            raise ValueError("dimension 必须大于 0")
        if batch_size <= 0:
            raise ValueError("Ollama embedding batch_size 必须大于 0")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.dimension = dimension
        self.batch_size = batch_size
        self.timeout = timeout

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        results: list[list[float]] = []
        for index in range(0, len(texts), self.batch_size):
            results.extend(self._embed_batch(texts[index : index + self.batch_size]))
        return results

    def embed_query(self, text: str) -> list[float]:
        return self._embed_batch([text])[0]

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        payload = json.dumps({"model": self.model, "input": texts}).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/api/embed",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise EmbeddingConfigurationError(
                f"无法连接 Ollama embedding 服务：{self.base_url}。请确认已启动 ollama serve，并已拉取模型 {self.model}。"
            ) from exc

        embeddings = data.get("embeddings")
        if not isinstance(embeddings, list):
            raise EmbeddingConfigurationError(f"Ollama embedding 响应格式异常：{data}")
        vectors = [self._normalize_vector(vector) for vector in embeddings]
        if len(vectors) != len(texts):
            raise EmbeddingConfigurationError("Ollama embedding 返回向量数量与输入文本数量不一致")
        return vectors

    @staticmethod
    def _normalize_vector(vector: Any) -> list[float]:
        if not isinstance(vector, list):
            raise EmbeddingConfigurationError("Ollama embedding 返回了非数组向量")
        return [float(item) for item in vector]
