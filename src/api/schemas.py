"""Request and response schemas for the FastAPI service."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.config import settings


class AddDocumentRequest(BaseModel):
    path: str = Field(..., description="Local file path to load, split, and add")
    loader_kwargs: dict[str, Any] = Field(default_factory=dict)
    splitter_type: str = settings.splitter.default_type
    chunk_size: int = Field(default=settings.splitter.default_chunk_size, gt=0)
    chunk_overlap: int = Field(default=settings.splitter.default_chunk_overlap, ge=0)
    splitter_kwargs: dict[str, Any] = Field(default_factory=dict)


class AddDocumentResponse(BaseModel):
    ids: list[str]
    count: int
    input_count: int | None = None
    skipped_duplicates: int = 0


class IndexFileResponse(BaseModel):
    filename: str
    source_id: str
    ids: list[str]
    count: int
    input_count: int
    skipped_duplicates: int


class IndexResponse(BaseModel):
    files: list[IndexFileResponse]
    total_files: int
    total_chunks: int
    total_input_chunks: int
    total_skipped_duplicates: int


class DeleteDocumentRequest(BaseModel):
    ids: list[str] | None = None
    source: str | None = None
    source_id: str | None = None


class DeleteDocumentResponse(BaseModel):
    deleted: int | None = None


class KnowledgeFileResponse(BaseModel):
    filename: str
    source: str
    source_id: str | None = None
    file_hash: str | None = None
    chunk_count: int
    chunk_ids: list[str] = Field(default_factory=list)


class ListDocumentsResponse(BaseModel):
    files: list[KnowledgeFileResponse]
    total_files: int
    total_chunks: int


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    k: int = Field(default=settings.rag.default_top_k, gt=0)
    filter: dict[str, Any] | None = None
    rerank: bool = True


class SearchResultResponse(BaseModel):
    page_content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    score: float | None = None
    rerank_score: float | None = None


class SearchResponse(BaseModel):
    results: list[SearchResultResponse]


class ChatMessageRequest(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(..., min_length=1)
    history: list[ChatMessageRequest] = Field(default_factory=list)
    system_prompt: str | None = None
    temperature: float | None = None
    max_tokens: int | None = Field(default=None, gt=0)


class RagChatRequest(BaseModel):
    session_id: str | None = None
    question: str = Field(..., min_length=1)
    k: int = Field(default=settings.rag.default_top_k, gt=0)
    filter: dict[str, Any] | None = None
    history: list[ChatMessageRequest] = Field(default_factory=list)
    system_prompt: str | None = None
    temperature: float | None = None
    max_tokens: int | None = Field(default=None, gt=0)


class AgentChatRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(..., min_length=1)
    k: int = Field(default=settings.rag.default_top_k, gt=0)
    history: list[ChatMessageRequest] = Field(default_factory=list)
    file_ids: list[str] = Field(default_factory=list)


class ChatFileResponse(BaseModel):
    file_id: str
    filename: str
    size: int
    content_type: str = ""
    status: str
    created_at: str
    chunk_count: int
    error: str = ""


class RagReferenceResponse(BaseModel):
    index: int
    page_content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    score: float | None = None


class GeneratedDocumentAttachmentResponse(BaseModel):
    file_id: str
    filename: str
    document_type: str
    mime_type: str
    download_url: str
    size: int
    created_at: str


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    mode: str | None = None
    references: list[RagReferenceResponse] = Field(default_factory=list)
    attachments: list[GeneratedDocumentAttachmentResponse] = Field(default_factory=list)
    uploaded_files: list[ChatFileResponse] = Field(default_factory=list)
    created_at: str


class ChatSessionResponse(BaseModel):
    id: str
    title: str
    messages: list[ChatMessageResponse] = Field(default_factory=list)
    created_at: str
    updated_at: str


class ChatSessionListResponse(BaseModel):
    sessions: list[ChatSessionResponse]


class ChatResponse(BaseModel):
    answer: str
    prompt: str
    model: str
    usage: dict[str, Any] = Field(default_factory=dict)
    session: ChatSessionResponse | None = None


class RagChatResponse(BaseModel):
    answer: str
    question: str
    prompt: str
    references: list[RagReferenceResponse]
    model: str
    usage: dict[str, Any] = Field(default_factory=dict)
    session: ChatSessionResponse | None = None


class AgentChatResponse(BaseModel):
    answer: str
    question: str
    prompt: str
    used_rag: bool
    references: list[RagReferenceResponse]
    attachments: list[GeneratedDocumentAttachmentResponse] = Field(default_factory=list)
    model: str
    usage: dict[str, Any] = Field(default_factory=dict)
    session: ChatSessionResponse | None = None


class UserSettingsResponse(BaseModel):
    show_rag_references: bool
    chat_background_image: str = ""
    chat_background_opacity: float
    updated_at: str


class UpdateUserSettingsRequest(BaseModel):
    show_rag_references: bool | None = None
    chat_background_image: str | None = None
    chat_background_opacity: float | None = Field(default=None, ge=0.05, le=1.0)
