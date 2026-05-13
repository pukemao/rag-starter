"""Unified document splitting helpers."""

from .base import SplitterConfig, SplitterDependencyError
from .registry import (
    DEFAULT_SPLITTER,
    create_splitter,
    load_and_split_documents,
    split_documents,
    supported_splitters,
)

__all__ = [
    "DEFAULT_SPLITTER",
    "SplitterConfig",
    "SplitterDependencyError",
    "create_splitter",
    "load_and_split_documents",
    "split_documents",
    "supported_splitters",
]
