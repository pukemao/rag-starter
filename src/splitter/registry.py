"""Factory and convenience functions for document splitters."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
import re
from typing import Any

from langchain_core.documents import Document

from src.loader import load_documents
from src.config import settings

from .base import SplitterConfig, SplitterDependencyError
from .excel import split_excel_file
from .pdf import split_pdf_file
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
_PDF_EXTENSIONS = {".pdf"}
_MARKDOWN_HEADERS = (
    ("#", "h1"),
    ("##", "h2"),
    ("###", "h3"),
    ("####", "h4"),
    ("#####", "h5"),
    ("######", "h6"),
)
_MARKDOWN_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


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
    documents = _build_markdown_sections(path, text, headers_to_split_on=headers_to_split_on)
    return split_documents(
        documents,
        splitter=splitter,
        splitter_type="recursive",
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        **splitter_kwargs,
    )


def _build_markdown_sections(
    path: Path,
    text: str,
    *,
    headers_to_split_on: tuple[tuple[str, str], ...] = _MARKDOWN_HEADERS,
) -> list[Document]:
    supported_levels = {len(marker) for marker, _ in headers_to_split_on}
    heading_stack: dict[int, str] = {}
    current_lines: list[str] = []
    current_has_body = False
    current_heading_level: int | None = None
    sections: list[Document] = []

    def reset_current() -> None:
        nonlocal current_lines, current_has_body, current_heading_level
        current_lines = _markdown_heading_lines(heading_stack)
        current_has_body = False
        current_heading_level = max(heading_stack) if heading_stack else None

    def flush() -> None:
        nonlocal current_lines, current_has_body, current_heading_level
        content = "\n\n".join(_dedupe_consecutive_lines(line for line in current_lines if line.strip())).strip()
        if content:
            sections.append(
                Document(
                    page_content=content,
                    metadata=_markdown_metadata(path, heading_stack),
                )
            )
        current_lines = []
        current_has_body = False
        current_heading_level = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        match = _MARKDOWN_HEADING_PATTERN.match(line.strip())
        if match and len(match.group(1)) in supported_levels:
            if current_lines and current_has_body:
                flush()
            level = len(match.group(1))
            heading = _plain_markdown_heading(match.group(2))
            _apply_markdown_heading(
                heading_stack,
                level,
                heading,
                previous_level=current_heading_level,
                previous_has_body=current_has_body,
            )
            reset_current()
            continue

        if not current_lines:
            reset_current()
        if line.strip():
            current_has_body = True
        current_lines.append(line)

    if current_lines:
        flush()

    if sections:
        return sections
    return [
        Document(
            page_content=text.strip(),
            metadata={
                "source": str(path),
                "filename": path.name,
                "filetype": "text/markdown",
            },
        )
    ]


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
    if path.suffix.lower() in _PDF_EXTENSIONS and splitter is None:
        return split_pdf_file(
            path,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
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


def _markdown_heading_lines(heading_stack: dict[int, str]) -> list[str]:
    return [f"{'#' * level} {heading_stack[level]}" for level in sorted(heading_stack)]


def _markdown_metadata(path: Path, heading_stack: dict[int, str]) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "source": str(path),
        "filename": path.name,
        "filetype": "text/markdown",
    }
    heading_lines = _markdown_heading_lines(heading_stack)
    if heading_lines:
        metadata["heading_context"] = "\n".join(heading_lines)
    for level, heading in heading_stack.items():
        metadata[f"h{level}"] = heading
    return metadata


def _apply_markdown_heading(
    heading_stack: dict[int, str],
    level: int,
    heading: str,
    *,
    previous_level: int | None,
    previous_has_body: bool,
) -> None:
    if previous_level == level and not previous_has_body and heading_stack.get(level):
        level = min(level + 1, 6)
    for existing_level in list(heading_stack):
        if existing_level >= level:
            heading_stack.pop(existing_level)
    heading_stack[level] = heading


def _plain_markdown_heading(text: str) -> str:
    return re.sub(r"[*_`]+", "", text).strip()


def _dedupe_consecutive_lines(lines: list[str] | tuple[str, ...] | Any) -> list[str]:
    deduped: list[str] = []
    previous: str | None = None
    for line in lines:
        current = str(line).strip()
        if not current:
            continue
        if current == previous:
            continue
        deduped.append(current)
        previous = current
    return deduped
