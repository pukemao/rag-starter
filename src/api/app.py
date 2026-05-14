"""FastAPI application for local RAG document indexing and retrieval."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.llm import DeepSeekClient, LLMConfigurationError
from src.rag import RagService
from src.storage import StorageService
from src.storage.service import StoredChatMessage, StoredChatSession, StoredUserSettings
from src.vector_store import DuplicateFileError, VectorStoreService

from .schemas import (
    AddDocumentRequest,
    AddDocumentResponse,
    ChatRequest,
    ChatResponse,
    ChatMessageResponse,
    ChatSessionListResponse,
    ChatSessionResponse,
    DeleteDocumentRequest,
    DeleteDocumentResponse,
    IndexFileResponse,
    IndexResponse,
    KnowledgeFileResponse,
    ListDocumentsResponse,
    RagChatRequest,
    RagChatResponse,
    RagReferenceResponse,
    SearchRequest,
    SearchResponse,
    SearchResultResponse,
    UpdateUserSettingsRequest,
    UserSettingsResponse,
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


def _build_chat_prompt(message: str, history: list[dict[str, str]]) -> str:
    history_lines = []
    for item in history[-12:]:
        role = "用户" if item.get("role") == "user" else "助手"
        content = str(item.get("content") or "").strip()
        if content:
            history_lines.append(f"{role}: {content}")
    conversation = "\n".join(history_lines) if history_lines else "无"
    return (
        "请根据用户当前输入和历史对话进行自然、准确的回答。\n\n"
        f"历史对话：\n{conversation}\n\n"
        f"用户当前输入：\n{message.strip()}"
    )


def _dt(value) -> str:
    return value.isoformat()


def _message_response(message: StoredChatMessage) -> ChatMessageResponse:
    return ChatMessageResponse(
        id=message.id,
        role=message.role,
        content=message.content,
        mode=message.mode,
        references=[RagReferenceResponse(**reference) for reference in message.references],
        created_at=_dt(message.created_at),
    )


def _session_response(session: StoredChatSession, *, include_messages: bool = True) -> ChatSessionResponse:
    return ChatSessionResponse(
        id=session.id,
        title=session.title,
        messages=[_message_response(message) for message in session.messages] if include_messages else [],
        created_at=_dt(session.created_at),
        updated_at=_dt(session.updated_at),
    )


def _settings_response(user_settings: StoredUserSettings) -> UserSettingsResponse:
    return UserSettingsResponse(
        show_rag_references=user_settings.show_rag_references,
        chat_background_image=user_settings.chat_background_image,
        chat_background_opacity=user_settings.chat_background_opacity,
        updated_at=_dt(user_settings.updated_at),
    )


def create_app(
    service: VectorStoreService | None = None,
    rag_service: RagService | None = None,
    storage_service: StorageService | None = None,
) -> FastAPI:
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
    active_storage_service = storage_service or StorageService()

    def get_service() -> VectorStoreService:
        return vector_service

    def get_rag_service() -> RagService:
        return active_rag_service

    def get_storage_service() -> StorageService:
        return active_storage_service

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

    @app.get("/documents", response_model=ListDocumentsResponse)
    def list_documents(
        active_service: VectorStoreService = Depends(get_service),
    ) -> ListDocumentsResponse:
        try:
            files = active_service.list_files()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return ListDocumentsResponse(
            files=[
                KnowledgeFileResponse(
                    filename=file.filename,
                    source=file.source,
                    source_id=file.source_id,
                    file_hash=file.file_hash,
                    chunk_count=file.chunk_count,
                    chunk_ids=file.chunk_ids,
                )
                for file in files
            ],
            total_files=len(files),
            total_chunks=sum(file.chunk_count for file in files),
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
            deleted = active_service.delete(ids=request.ids, source=request.source, source_id=request.source_id)
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

    @app.post("/chat", response_model=ChatResponse)
    def chat(request: ChatRequest, active_storage: StorageService = Depends(get_storage_service)) -> ChatResponse:
        try:
            prompt = _build_chat_prompt(
                request.message,
                [{"role": item.role, "content": item.content} for item in request.history],
            )
            result = DeepSeekClient().chat(
                prompt,
                system_prompt=request.system_prompt or "你是一个严谨、清晰的中文对话助手。",
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )
            session = active_storage.save_completed_turn(
                session_id=request.session_id,
                user_content=request.message,
                assistant_content=result.content,
                mode="normal",
            )
        except LLMConfigurationError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return ChatResponse(answer=result.content, prompt=prompt, model=result.model, usage=result.usage, session=_session_response(session))

    @app.post("/rag/chat", response_model=RagChatResponse)
    def rag_chat(
        request: RagChatRequest,
        active_service: RagService = Depends(get_rag_service),
        active_storage: StorageService = Depends(get_storage_service),
    ) -> RagChatResponse:
        try:
            result = active_service.answer(
                request.question,
                k=request.k,
                filter=request.filter,
                history=[{"role": item.role, "content": item.content} for item in request.history],
                system_prompt=request.system_prompt,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )
            references = [
                {
                    "index": reference.index,
                    "page_content": reference.page_content,
                    "metadata": reference.metadata,
                    "score": reference.score,
                }
                for reference in result.references
            ]
            session = active_storage.save_completed_turn(
                session_id=request.session_id,
                user_content=request.question,
                assistant_content=result.answer,
                mode="rag",
                references=references,
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
            session=_session_response(session),
        )

    @app.get("/chat/sessions", response_model=ChatSessionListResponse)
    def list_chat_sessions(active_storage: StorageService = Depends(get_storage_service)) -> ChatSessionListResponse:
        return ChatSessionListResponse(sessions=[_session_response(session, include_messages=False) for session in active_storage.list_sessions()])

    @app.get("/chat/sessions/{session_id}", response_model=ChatSessionResponse)
    def get_chat_session(session_id: str, active_storage: StorageService = Depends(get_storage_service)) -> ChatSessionResponse:
        session = active_storage.get_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="会话不存在")
        return _session_response(session)

    @app.delete("/chat/sessions/{session_id}", response_model=dict)
    def delete_chat_session(session_id: str, active_storage: StorageService = Depends(get_storage_service)) -> dict[str, bool]:
        return {"deleted": active_storage.delete_session(session_id)}

    @app.get("/settings", response_model=UserSettingsResponse)
    def get_user_settings(active_storage: StorageService = Depends(get_storage_service)) -> UserSettingsResponse:
        return _settings_response(active_storage.get_settings())

    @app.put("/settings", response_model=UserSettingsResponse)
    def update_user_settings(
        request: UpdateUserSettingsRequest,
        active_storage: StorageService = Depends(get_storage_service),
    ) -> UserSettingsResponse:
        return _settings_response(
            active_storage.update_settings(
                show_rag_references=request.show_rag_references,
                chat_background_image=request.chat_background_image,
                chat_background_opacity=request.chat_background_opacity,
            )
        )

    return app
