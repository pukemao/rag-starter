"""DashScope embedding client through OpenAI-compatible LangChain embeddings."""

from __future__ import annotations

from typing import Any

from langchain_core.embeddings import Embeddings

from src.config import settings


class EmbeddingConfigurationError(RuntimeError):
    """Raised when embedding settings are missing or invalid."""


class DashScopeEmbeddings(Embeddings):
    """Aliyun Bailian DashScope embeddings using the OpenAI-compatible endpoint."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = settings.embedding.base_url,
        model: str = settings.embedding.model,
        dimension: int = settings.embedding.dimension,
        timeout: float = settings.embedding.timeout_seconds,
        embeddings: Embeddings | None = None,
    ) -> None:
        if dimension <= 0:
            raise ValueError("dimension 必须大于 0")

        self.api_key = api_key if api_key is not None else settings.embedding.api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.dimension = dimension
        self.timeout = timeout
        self.embeddings = embeddings or self._create_embeddings()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple documents."""

        return self.embeddings.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        """Embed one query."""

        return self.embeddings.embed_query(text)

    def _create_embeddings(self) -> Embeddings:
        if not self.api_key:
            raise EmbeddingConfigurationError("缺少 DashScope API Key，请设置 DASHSCOPE_API_KEY")

        try:
            from langchain_openai import OpenAIEmbeddings
        except ImportError as exc:
            raise EmbeddingConfigurationError("无法导入 langchain_openai。请安装依赖: pip install langchain-openai") from exc

        return OpenAIEmbeddings(
            model=self.model,
            api_key=self.api_key,
            base_url=self.base_url,
            dimensions=self.dimension,
            timeout=self.timeout,
            tiktoken_enabled=False,
            check_embedding_ctx_length=False,
            model_kwargs=self._model_kwargs(),
        )

    def _model_kwargs(self) -> dict[str, Any]:
        return {"encoding_format": "float"}
