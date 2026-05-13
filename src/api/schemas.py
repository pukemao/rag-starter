"""Request and response schemas for the FastAPI service."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AddDocumentRequest(BaseModel):
    path: str = Field(..., description="Local file path to load, split, and add")
    loader_kwargs: dict[str, Any] = Field(default_factory=dict)
    splitter_type: str = "recursive"
    chunk_size: int = Field(default=1000, gt=0)
    chunk_overlap: int = Field(default=200, ge=0)
    splitter_kwargs: dict[str, Any] = Field(default_factory=dict)


class AddDocumentResponse(BaseModel):
    ids: list[str]
    count: int


class IndexFileResponse(BaseModel):
    filename: str
    source_id: str
    ids: list[str]
    count: int


class IndexResponse(BaseModel):
    files: list[IndexFileResponse]
    total_files: int
    total_chunks: int


class DeleteDocumentRequest(BaseModel):
    ids: list[str] | None = None
    source: str | None = None


class DeleteDocumentResponse(BaseModel):
    deleted: int | None = None


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    k: int = Field(default=4, gt=0)
    filter: dict[str, Any] | None = None


class SearchResultResponse(BaseModel):
    page_content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    score: float | None = None


class SearchResponse(BaseModel):
    results: list[SearchResultResponse]
