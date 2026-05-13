"""Service layer for adding, deleting, and searching vectorized documents."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from src.splitter import load_and_split_documents

from .base import SearchResult, VectorStoreConfig
from .chroma import create_chroma_vector_store


class VectorStoreService:
    """High-level API over a LangChain vector store."""

    def __init__(
        self,
        *,
        vector_store: Any | None = None,
        config: VectorStoreConfig | None = None,
        embedding: Embeddings | None = None,
    ) -> None:
        self.config = config or VectorStoreConfig()
        self.vector_store = vector_store or create_chroma_vector_store(config=self.config, embedding=embedding)

    def add_documents(self, documents: list[Document], *, ids: list[str] | None = None) -> list[str]:
        """Add pre-loaded and pre-split documents to the vector database."""

        if not documents:
            return []

        document_ids = ids or [self._document_id(document, index) for index, document in enumerate(documents)]
        self.vector_store.add_documents(documents, ids=document_ids)
        return document_ids

    def add_file(
        self,
        file_path: str | Path,
        *,
        loader_kwargs: dict[str, Any] | None = None,
        splitter_type: str = "recursive",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        splitter_kwargs: dict[str, Any] | None = None,
    ) -> list[str]:
        """Load, split, and add one local file."""

        chunks = load_and_split_documents(
            file_path,
            loader_kwargs=loader_kwargs,
            splitter_type=splitter_type,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            splitter_kwargs=splitter_kwargs,
        )
        return self.add_documents(chunks)

    def delete(self, *, ids: list[str] | None = None, source: str | None = None) -> int | None:
        """Delete documents by ids or by ``metadata.source``."""

        if ids:
            self.vector_store.delete(ids=ids)
            return len(ids)

        if source:
            collection = getattr(self.vector_store, "_collection", None)
            if collection is None or not hasattr(collection, "delete"):
                raise NotImplementedError("当前 vector store 不支持按 source 删除")
            collection.delete(where={"source": source})
            return None

        raise ValueError("删除文档时必须提供 ids 或 source")

    def search(
        self,
        query: str,
        *,
        k: int = 4,
        filter: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Search similar chunks from the vector database."""

        if not query.strip():
            raise ValueError("query 不能为空")
        if k <= 0:
            raise ValueError("k 必须大于 0")

        if hasattr(self.vector_store, "similarity_search_with_score"):
            results = self.vector_store.similarity_search_with_score(query, k=k, filter=filter)
            return [
                SearchResult(page_content=document.page_content, metadata=dict(document.metadata), score=float(score))
                for document, score in results
            ]

        documents = self.vector_store.similarity_search(query, k=k, filter=filter)
        return [SearchResult(page_content=document.page_content, metadata=dict(document.metadata)) for document in documents]

    @staticmethod
    def _document_id(document: Document, index: int) -> str:
        source = str(document.metadata.get("source", "unknown"))
        payload = f"{source}:{index}:{document.page_content}".encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()
        return f"doc-{digest[:32]}"
