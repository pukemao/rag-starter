"""Factory and convenience functions for document splitters."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any

from langchain_core.documents import Document

from src.loader import load_documents
from src.config import settings

from .base import SplitterConfig, SplitterDependencyError
from .excel import split_excel_file
from .word import build_word_sections, ensure_word_heading_context

DEFAULT_SPLITTER = settings.splitter.default_type

_SPLITTERS: dict[str, str] = {
    "recursive": "RecursiveCharacterTextSplitter",
    "character": "CharacterTextSplitter",
    "token": "TokenTextSplitter",
    "markdown": "MarkdownTextSplitter",
    "python": "PythonCodeTextSplitter",
}

_MARKDOWN_EXTENSIONS = {".md", ".markdown", ".mdx"}
_EXCEL_EXTENSIONS = {".xls", ".xlsx"}
_WORD_EXTENSIONS = {".doc", ".docx"}
_MARKDOWN_HEADERS = (
    ("#", "h1"),
    ("##", "h2"),
    ("###", "h3"),
    ("####", "h4"),
    ("#####", "h5"),
    ("######", "h6"),
)


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


def split_markdown_file(
    file_path: str | Path,
    *,
    splitter: Any | None = None,
    chunk_size: int = settings.splitter.default_chunk_size,
    chunk_overlap: int = settings.splitter.default_chunk_overlap,
    encoding: str = "utf-8",
    headers_to_split_on: tuple[tuple[str, str], ...] = _MARKDOWN_HEADERS,
    **splitter_kwargs: Any,
) -> list[Any]:
    """Split Markdown by headers first, then enforce chunk size recursively."""

    path = Path(file_path)
    text = path.read_text(encoding=encoding)
    header_splitter_cls = _import_markdown_header_splitter()
    header_splitter = header_splitter_cls(
        headers_to_split_on=list(headers_to_split_on),
        strip_headers=False,
    )
    sections = header_splitter.split_text(text)
    documents = [
        Document(
            page_content=section.page_content,
            metadata={
                "source": str(path),
                "filename": path.name,
                "filetype": "text/markdown",
                **dict(section.metadata),
            },
        )
        for section in sections
    ]
    return split_documents(
        documents,
        splitter=splitter,
        splitter_type="recursive",
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        **splitter_kwargs,
    )


def split_word_file(
    file_path: str | Path,
    *,
    splitter: Any | None = None,
    chunk_size: int = settings.splitter.default_chunk_size,
    chunk_overlap: int = settings.splitter.default_chunk_overlap,
    loader_kwargs: dict[str, Any] | None = None,
    **splitter_kwargs: Any,
) -> list[Any]:
    """Split Word documents by heading-aware sections first."""

    sections = build_word_sections(file_path, loader_kwargs=loader_kwargs)
    chunks = split_documents(
        sections,
        splitter=splitter,
        splitter_type="recursive",
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        **splitter_kwargs,
    )
    return [ensure_word_heading_context(chunk) for chunk in chunks]


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

    path = Path(file_path)
    if path.suffix.lower() in _MARKDOWN_EXTENSIONS and splitter is None:
        return split_markdown_file(
            path,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            **(splitter_kwargs or {}),
        )
    if path.suffix.lower() in _EXCEL_EXTENSIONS and splitter is None:
        return split_excel_file(
            path,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
    if path.suffix.lower() in _WORD_EXTENSIONS and splitter is None:
        return split_word_file(
            path,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            loader_kwargs=loader_kwargs,
            **(splitter_kwargs or {}),
        )

    documents = load_documents(file_path, **(loader_kwargs or {}))
    return split_documents(
        documents,
        splitter=splitter,
        splitter_type=splitter_type,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        **(splitter_kwargs or {}),
    )


def _import_markdown_header_splitter() -> type[Any]:
    try:
        module = import_module("langchain_text_splitters")
    except ImportError as exc:
        raise SplitterDependencyError(
            "无法导入 langchain_text_splitters。请安装依赖: pip install langchain-text-splitters"
        ) from exc

    splitter_cls = getattr(module, "MarkdownHeaderTextSplitter", None)
    if splitter_cls is None:
        raise SplitterDependencyError("langchain_text_splitters 中未找到 MarkdownHeaderTextSplitter")
    return splitter_cls
