"""Service layer for adding, deleting, and searching vectorized documents."""

from __future__ import annotations

import hashlib
from pathlib import Path
import re
from typing import Any

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from src.splitter import load_and_split_documents

from .base import DuplicateFileError, IndexResult, SearchResult, VectorStoreConfig
from .chroma import create_chroma_vector_store

_WHITESPACE_PATTERN = re.compile(r"\s+")


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

        return self.index_documents(documents, ids=ids).ids

    def index_documents(self, documents: list[Document], *, ids: list[str] | None = None) -> IndexResult:
        """Deduplicate one batch of chunks and add unique chunks to the vector database."""

        if not documents:
            return IndexResult(ids=[], input_count=0, added_count=0, skipped_duplicates=0)

        if ids is not None and len(ids) != len(documents):
            raise ValueError("ids 数量必须与 documents 数量一致")

        unique_documents: list[Document] = []
        unique_ids: list[str] = []
        seen_hashes_by_source: dict[str, set[str]] = {}

        for index, document in enumerate(documents):
            source_key = self._source_key(document)
            chunk_hash = self._chunk_hash(document.page_content)
            seen_hashes = seen_hashes_by_source.setdefault(source_key, set())
            if chunk_hash in seen_hashes:
                continue
            seen_hashes.add(chunk_hash)

            metadata = dict(document.metadata)
            metadata.setdefault("chunk_hash", chunk_hash)
            metadata.setdefault("chunk_index", len(unique_documents))
            unique_document = Document(page_content=document.page_content, metadata=metadata)
            unique_documents.append(unique_document)
            unique_ids.append(ids[index] if ids is not None else self._document_id(unique_document))

        if unique_documents:
            self.vector_store.add_documents(unique_documents, ids=unique_ids)

        return IndexResult(
            ids=unique_ids,
            input_count=len(documents),
            added_count=len(unique_documents),
            skipped_duplicates=len(documents) - len(unique_documents),
        )

    def add_file(
        self,
        file_path: str | Path,
        *,
        loader_kwargs: dict[str, Any] | None = None,
        splitter_type: str = "recursive",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        splitter_kwargs: dict[str, Any] | None = None,
        source_label: str | None = None,
        source_id: str | None = None,
    ) -> list[str]:
        """Load, split, and add one local file."""

        return self.index_file(
            file_path,
            loader_kwargs=loader_kwargs,
            splitter_type=splitter_type,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            splitter_kwargs=splitter_kwargs,
            source_label=source_label,
            source_id=source_id,
        ).ids

    def index_file(
        self,
        file_path: str | Path,
        *,
        loader_kwargs: dict[str, Any] | None = None,
        splitter_type: str = "recursive",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        splitter_kwargs: dict[str, Any] | None = None,
        source_label: str | None = None,
        source_id: str | None = None,
        file_hash: str | None = None,
        reject_duplicate_file: bool = False,
    ) -> IndexResult:
        """Load, split, deduplicate within one file, and add it to the vector database."""

        path = Path(file_path)
        active_file_hash = file_hash or self.compute_file_hash(path)
        if reject_duplicate_file and self.file_exists(active_file_hash):
            raise DuplicateFileError(source_label or path.name, active_file_hash)

        chunks = load_and_split_documents(
            path,
            loader_kwargs=loader_kwargs,
            splitter_type=splitter_type,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            splitter_kwargs=splitter_kwargs,
        )
        chunks = [
            Document(
                page_content=chunk.page_content,
                metadata=self._rewrite_metadata(
                    chunk.metadata,
                    source_label=source_label,
                    source_id=source_id,
                    file_hash=active_file_hash,
                ),
            )
            for chunk in chunks
        ]
        return self.index_documents(chunks)

    def file_exists(self, file_hash: str) -> bool:
        """Return whether a file hash already exists in the vector database."""

        if not file_hash:
            return False

        stores = [self.vector_store, getattr(self.vector_store, "_collection", None)]
        for store in stores:
            if store is None or not hasattr(store, "get"):
                continue
            try:
                result = store.get(where={"file_hash": file_hash}, limit=1)
            except TypeError:
                result = store.get(where={"file_hash": file_hash})
            ids = result.get("ids") if isinstance(result, dict) else None
            if ids:
                return True
        return False

    @staticmethod
    def compute_file_hash(file_path: str | Path) -> str:
        """Compute SHA-256 for a local file."""

        digest = hashlib.sha256()
        with Path(file_path).open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def compute_content_hash(content: bytes) -> str:
        """Compute SHA-256 for uploaded file bytes."""

        return hashlib.sha256(content).hexdigest()

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
    def _document_id(document: Document) -> str:
        source = VectorStoreService._source_key(document)
        chunk_hash = str(document.metadata.get("chunk_hash") or VectorStoreService._chunk_hash(document.page_content))
        payload = f"{source}:{chunk_hash}".encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()
        return f"doc-{digest[:32]}"

    @staticmethod
    def _source_key(document: Document) -> str:
        return str(document.metadata.get("source_id") or document.metadata.get("source", "unknown"))

    @staticmethod
    def _rewrite_metadata(
        metadata: dict[str, Any],
        *,
        source_label: str | None = None,
        source_id: str | None = None,
        file_hash: str | None = None,
    ) -> dict[str, Any]:
        updated = dict(metadata)
        if source_label is not None:
            updated["source"] = source_label
        if source_id is not None:
            updated["source_id"] = source_id
        if file_hash is not None:
            updated["file_hash"] = file_hash
        return updated

    @staticmethod
    def _chunk_hash(page_content: str) -> str:
        normalized = _WHITESPACE_PATTERN.sub(" ", page_content).strip()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
