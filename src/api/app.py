"""FastAPI application for local RAG document indexing and retrieval."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile

from src.vector_store import VectorStoreService

from .schemas import (
    AddDocumentRequest,
    AddDocumentResponse,
    DeleteDocumentRequest,
    DeleteDocumentResponse,
    IndexFileResponse,
    IndexResponse,
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
            result = active_service.index_file(
                request.path,
                loader_kwargs=request.loader_kwargs,
                splitter_type=request.splitter_type,
                chunk_size=request.chunk_size,
                chunk_overlap=request.chunk_overlap,
                splitter_kwargs=request.splitter_kwargs,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return AddDocumentResponse(
            ids=result.ids,
            count=result.added_count,
            input_count=result.input_count,
            skipped_duplicates=result.skipped_duplicates,
        )

    @app.post("/index", response_model=IndexResponse)
    async def index_knowledge_base(
        files: list[UploadFile] = File(..., description="Knowledge base files to index"),
        splitter_type: str = Form("recursive"),
        chunk_size: int = Form(1000),
        chunk_overlap: int = Form(200),
        active_service: VectorStoreService = Depends(get_service),
    ) -> IndexResponse:
        indexed_files: list[IndexFileResponse] = []
        total_chunks = 0
        total_input_chunks = 0
        total_skipped_duplicates = 0

        try:
            with TemporaryDirectory() as tmpdir:
                temp_root = Path(tmpdir)
                for upload in files:
                    try:
                        filename = Path(upload.filename or "upload.bin").name
                        source_id = uuid4().hex
                        temp_path = temp_root / f"{source_id}_{filename}"
                        content = await upload.read()
                        temp_path.write_bytes(content)

                        result = active_service.index_file(
                            temp_path,
                            splitter_type=splitter_type,
                            chunk_size=chunk_size,
                            chunk_overlap=chunk_overlap,
                            source_label=filename,
                            source_id=source_id,
                        )
                        indexed_files.append(
                            IndexFileResponse(
                                filename=filename,
                                source_id=source_id,
                                ids=result.ids,
                                count=result.added_count,
                                input_count=result.input_count,
                                skipped_duplicates=result.skipped_duplicates,
                            )
                        )
                        total_chunks += result.added_count
                        total_input_chunks += result.input_count
                        total_skipped_duplicates += result.skipped_duplicates
                    finally:
                        await upload.close()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        return IndexResponse(
            files=indexed_files,
            total_files=len(indexed_files),
            total_chunks=total_chunks,
            total_input_chunks=total_input_chunks,
            total_skipped_duplicates=total_skipped_duplicates,
        )

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
