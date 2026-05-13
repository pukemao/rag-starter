"""Shared splitter types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class SplitterDependencyError(ImportError):
    """Raised when LangChain text splitter dependencies are unavailable."""


@dataclass(frozen=True, slots=True)
class SplitterConfig:
    """Configuration for creating a LangChain text splitter."""

    splitter_type: str = "recursive"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    kwargs: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.chunk_size <= 0:
            raise ValueError("chunk_size 必须大于 0")
        if self.chunk_overlap < 0:
            raise ValueError("chunk_overlap 不能小于 0")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap 必须小于 chunk_size")
