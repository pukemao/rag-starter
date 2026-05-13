"""FastAPI application for local RAG document indexing and retrieval."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.llm import LLMConfigurationError
from src.rag import RagService
from src.vector_store import DuplicateFileError, VectorStoreService

from .schemas import (
    AddDocumentRequest,
    AddDocumentResponse,
    DeleteDocumentRequest,
    DeleteDocumentResponse,
    IndexFileResponse,
    IndexResponse,
    RagChatRequest,
    RagChatResponse,
    RagReferenceResponse,
    SearchRequest,
    SearchResponse,
    SearchResultResponse,
)


def _duplicate_file_response(exc: DuplicateFileError) -> HTTPException:
    return HTTPException(
        status_code=409,
        detail={
            "message": exc.message,
            "filename": exc.filename,
            "file_hash": exc.file_hash,
        },
    )


def create_app(service: VectorStoreService | None = None, rag_service: RagService | None = None) -> FastAPI:
    """Create the FastAPI app.

    Passing services is mainly useful for tests. When omitted, the app uses the
    default persistent local Chroma database and configured LLM from ``src.config``.
    """

    app = FastAPI(title=settings.api.title, version=settings.api.version)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    vector_service = service or VectorStoreService()
    active_rag_service = rag_service or RagService(vector_service=vector_service)

    def get_service() -> VectorStoreService:
        return vector_service

    def get_rag_service() -> RagService:
        return active_rag_service

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
                reject_duplicate_file=True,
            )
        except DuplicateFileError as exc:
            raise _duplicate_file_response(exc) from exc
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
        splitter_type: str = Form(settings.splitter.default_type),
        chunk_size: int = Form(settings.splitter.default_chunk_size),
        chunk_overlap: int = Form(settings.splitter.default_chunk_overlap),
        active_service: VectorStoreService = Depends(get_service),
    ) -> IndexResponse:
        indexed_files: list[IndexFileResponse] = []
        total_chunks = 0
        total_input_chunks = 0
        total_skipped_duplicates = 0

        try:
            with TemporaryDirectory() as tmpdir:
                temp_root = Path(tmpdir)
                prepared_files: list[tuple[str, str, str, bytes]] = []
                seen_hashes: dict[str, str] = {}
                for upload in files:
                    try:
                        filename = Path(upload.filename or "upload.bin").name
                        source_id = uuid4().hex
                        content = await upload.read()
                        file_hash = active_service.compute_content_hash(content)

                        if file_hash in seen_hashes:
                            raise DuplicateFileError(filename, file_hash)
                        if active_service.file_exists(file_hash):
                            raise DuplicateFileError(filename, file_hash)

                        seen_hashes[file_hash] = filename
                        prepared_files.append((filename, source_id, file_hash, content))
                    finally:
                        await upload.close()

                for filename, source_id, file_hash, content in prepared_files:
                    temp_path = temp_root / f"{source_id}_{filename}"
                    temp_path.write_bytes(content)

                    result = active_service.index_file(
                        temp_path,
                        splitter_type=splitter_type,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                        source_label=filename,
                        source_id=source_id,
                        file_hash=file_hash,
                        reject_duplicate_file=False,
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
        except DuplicateFileError as exc:
            raise _duplicate_file_response(exc) from exc
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

    @app.post("/rag/chat", response_model=RagChatResponse)
    def rag_chat(
        request: RagChatRequest,
        active_service: RagService = Depends(get_rag_service),
    ) -> RagChatResponse:
        try:
            result = active_service.answer(
                request.question,
                k=request.k,
                filter=request.filter,
                system_prompt=request.system_prompt,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )
        except LLMConfigurationError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return RagChatResponse(
            answer=result.answer,
            question=result.question,
            prompt=result.prompt,
            references=[
                RagReferenceResponse(
                    index=reference.index,
                    page_content=reference.page_content,
                    metadata=reference.metadata,
                    score=reference.score,
                )
                for reference in result.references
            ],
            model=result.model,
            usage=result.usage,
        )

    return app
