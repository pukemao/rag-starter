"""FastAPI application for local RAG document indexing and retrieval."""

from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException

from src.vector_store import VectorStoreService

from .schemas import (
    AddDocumentRequest,
    AddDocumentResponse,
    DeleteDocumentRequest,
    DeleteDocumentResponse,
    SearchRequest,
    SearchResponse,
    SearchResultResponse,
)


def create_app(service: VectorStoreService | None = None) -> FastAPI:
    """Create the FastAPI app.

    Passing ``service`` is mainly useful for tests. When omitted, the app uses
    the default persistent local Chroma database under ``storage/chroma``.
    """

    app = FastAPI(title="RAG Starter API", version="0.1.0")
    vector_service = service or VectorStoreService()

    def get_service() -> VectorStoreService:
        return vector_service

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/documents", response_model=AddDocumentResponse)
    def add_document(
        request: AddDocumentRequest,
        active_service: VectorStoreService = Depends(get_service),
    ) -> AddDocumentResponse:
        try:
            ids = active_service.add_file(
                request.path,
                loader_kwargs=request.loader_kwargs,
                splitter_type=request.splitter_type,
                chunk_size=request.chunk_size,
                chunk_overlap=request.chunk_overlap,
                splitter_kwargs=request.splitter_kwargs,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return AddDocumentResponse(ids=ids, count=len(ids))

    @app.delete("/documents", response_model=DeleteDocumentResponse)
    def delete_document(
        request: DeleteDocumentRequest,
        active_service: VectorStoreService = Depends(get_service),
    ) -> DeleteDocumentResponse:
        try:
            deleted = active_service.delete(ids=request.ids, source=request.source)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return DeleteDocumentResponse(deleted=deleted)

    @app.post("/search", response_model=SearchResponse)
    def search(
        request: SearchRequest,
        active_service: VectorStoreService = Depends(get_service),
    ) -> SearchResponse:
        try:
            results = active_service.search(request.query, k=request.k, filter=request.filter)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return SearchResponse(
            results=[
                SearchResultResponse(
                    page_content=result.page_content,
                    metadata=result.metadata,
                    score=result.score,
                )
                for result in results
            ]
        )

    return app
