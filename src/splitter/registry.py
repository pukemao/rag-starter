"""Factory and convenience functions for document splitters."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any

from src.loader import load_documents
from src.config import settings

from .base import SplitterConfig, SplitterDependencyError

DEFAULT_SPLITTER = settings.splitter.default_type

_SPLITTERS: dict[str, str] = {
    "recursive": "RecursiveCharacterTextSplitter",
    "character": "CharacterTextSplitter",
    "token": "TokenTextSplitter",
    "markdown": "MarkdownTextSplitter",
    "python": "PythonCodeTextSplitter",
}


def supported_splitters() -> tuple[str, ...]:
    """Return supported splitter aliases."""

    return tuple(sorted(_SPLITTERS))


def _import_splitter_class(splitter_type: str) -> type[Any]:
    try:
        class_name = _SPLITTERS[splitter_type]
    except KeyError as exc:
        supported = ", ".join(supported_splitters())
        raise ValueError(f"暂不支持分割器 {splitter_type!r}。已支持: {supported}") from exc

    try:
        module = import_module("langchain_text_splitters")
    except ImportError as exc:
        raise SplitterDependencyError(
            "无法导入 langchain_text_splitters。请安装依赖: pip install langchain-text-splitters"
        ) from exc

    splitter_cls = getattr(module, class_name, None)
    if splitter_cls is None:
        raise SplitterDependencyError(f"langchain_text_splitters 中未找到 {class_name}")
    return splitter_cls


def create_splitter(
    splitter_type: str = DEFAULT_SPLITTER,
    *,
    chunk_size: int = settings.splitter.default_chunk_size,
    chunk_overlap: int = settings.splitter.default_chunk_overlap,
    **kwargs: Any,
) -> Any:
    """Create a LangChain text splitter by alias."""

    config = SplitterConfig(
        splitter_type=splitter_type,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        kwargs=kwargs,
    )
    splitter_cls = _import_splitter_class(config.splitter_type)
    return splitter_cls(
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
        **config.kwargs,
    )


def split_documents(
    documents: list[Any],
    *,
    splitter: Any | None = None,
    splitter_type: str = DEFAULT_SPLITTER,
    chunk_size: int = settings.splitter.default_chunk_size,
    chunk_overlap: int = settings.splitter.default_chunk_overlap,
    **splitter_kwargs: Any,
) -> list[Any]:
    """Split LangChain ``Document`` objects into chunks."""

    active_splitter = splitter or create_splitter(
        splitter_type,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        **splitter_kwargs,
    )
    return list(active_splitter.split_documents(documents))


def load_and_split_documents(
    file_path: str | Path,
    *,
    splitter: Any | None = None,
    splitter_type: str = DEFAULT_SPLITTER,
    chunk_size: int = settings.splitter.default_chunk_size,
    chunk_overlap: int = settings.splitter.default_chunk_overlap,
    loader_kwargs: dict[str, Any] | None = None,
    splitter_kwargs: dict[str, Any] | None = None,
) -> list[Any]:
    """Load one file with ``src.loader`` and split the resulting documents."""

    documents = load_documents(file_path, **(loader_kwargs or {}))
    return split_documents(
        documents,
        splitter=splitter,
        splitter_type=splitter_type,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        **(splitter_kwargs or {}),
    )
